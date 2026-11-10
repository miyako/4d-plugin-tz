"""Narrow TZ outputs and the explicitly approved immutable tzdata copy."""

import argparse
from functools import lru_cache
from pathlib import Path
import re
import shutil

import repository
import source_version


PRODUCT = "TZ"
BASE = Path("test/Plugins")
BUNDLE = BASE / "TZ.bundle"
FILES = tuple(BUNDLE / relative for relative in (
    "Contents/MacOS/TZ", "Contents/Info.plist",
    "Contents/Resources/English.lproj/InfoPlist.strings",
    "Contents/Resources/constants.xlf", "Contents/Resources/manifest.json",
    "Contents/_CodeSignature/CodeResources",
))
WINDOWS_BINARY = BUNDLE / "Contents/Windows64/TZ.4DX"
DOWNLOADS = (Path("winbuild/TZ.4DX"),)
WINDOWS_SOURCE = Path("TZ.4dbase/plugins/TZ.bundle/contents/windows64/TZ.4DX")
TZ_SOURCE = Path("TZ.4dbase/Plugins/TZ.bundle/Contents/Resources/tzdata")
TZ_DEST = BUNDLE / "Contents/Resources/tzdata"
INTERMEDIATES = Path("TZ.4dbase/Plugins")
XCODE_DATA = INTERMEDIATES / "XCBuildData"
DIRECTORIES = tuple(INTERMEDIATES / path for path in (
    "TZ.build/Default", "SwiftExplicitPrecompiledModules", "ExplicitPrecompiledModules",
    "EagerLinkingTBDs/Default", "SharedPrecompiledHeaders",
))
UNIT = (r"(?:4DPlugin(?:API)?|ARRAY_(?:BOOLEAN|DATE|INTEGER|LONGINT|REAL|TEXT|TIME)|"
        r"C_(?:BLOB|DATE|INTEGER|LONGINT|PICTURE|POINTER|REAL|TEXT|TIME))")
INTERMEDIATE_FILE = re.compile(
    re.escape(str(INTERMEDIATES)) + r"/(?:"
    r"TZ\.build/Default/(?:TZ-[0-9a-f]{32}-VFS/all-product-headers\.yaml|TZ\.build/(?:"
    r"TZ(?:-(?:all-non-framework-target-headers|all-target-headers|generated-files|"
    r"own-target-headers|project-headers))?\.hmap|"
    r"TZ\.Dependency(?:Static)?MetadataFileList|"
    r"Objects-normal/(?:arm64|x86_64)/(?:" + UNIT + r"\.(?:o|d|dia)|"
    r"[0-9a-f]{32}-common-args\.resp|TZ\.LinkFileList|TZ_dependency_info\.dat|Binary/TZ)))|"
    r"SharedPrecompiledHeaders/SharedPrecompiledHeaders/[0-9]+/"
    r"4D Plugin_Prefix\.pch\.(?:gch|d|dia))\Z"
)


@lru_cache(maxsize=32)
def database_entries(root, sha):
    entries = repository.entries(repository.run(
        "git", "-C", root, "ls-tree", "-r", "-z", sha, "--", str(TZ_SOURCE)))
    if not entries or any(mode not in ("100644", "100755") for mode, _ in entries.values()):
        raise ValueError("tzdata requires a nonempty immutable regular tracked source set")
    return {str(Path(path).relative_to(TZ_SOURCE)): entry for path, entry in entries.items()}


def database():
    return database_entries(str(Path.cwd()), repository.run("git", "rev-parse", "HEAD"))


def generated(path, *, database_paths=None):
    if path.startswith(str(TZ_DEST) + "/"):
        return str(Path(path).relative_to(TZ_DEST)) in (
            database() if database_paths is None else database_paths)
    return (path in set(map(str, (*FILES, WINDOWS_BINARY, *DOWNLOADS)))
            or bool(re.fullmatch(
                re.escape(str(XCODE_DATA)) + r"/(?:build\.db(?:-wal|-shm)?|"
                r"[0-9a-f]{32}\.xcbuilddata/.+)", path)
                and not re.search(r"\.(?:c|cc|cpp|h|hpp|m|mm|swift)$", path))
            or bool(INTERMEDIATE_FILE.fullmatch(path)))


def validate_paths(paths):
    root = Path.cwd().resolve()
    for path in map(Path, paths):
        for parent in (path, *path.parents):
            if parent == Path("."):
                break
            if repository.is_link(parent):
                raise ValueError(f"Refusing symlink/reparse output: {parent}")
            if parent.name == ".git" or (parent.is_dir() and (
                    (parent / ".git").exists() or repository.is_link(parent / ".git"))):
                raise ValueError(f"Refusing nested Git output: {parent}")
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"Output escapes checkout: {path}")
        if path.exists():
            paths_to_check = (path, *path.rglob("*")) if path.is_dir() else (path,)
            for descendant in paths_to_check:
                if descendant.name == ".git":
                    raise ValueError(f"Refusing nested Git output: {descendant}")
                if repository.is_link(descendant):
                    raise ValueError(f"Refusing symlink/reparse output: {descendant}")
                if not (descendant.is_file() or descendant.is_dir()):
                    raise ValueError(f"Refusing nonregular output: {descendant}")


def require_file(path):
    validate_paths((path,))
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Missing or empty native output: {path}")


def tree(root, expected, *, optional=False):
    validate_paths((root,))
    if not root.exists() and optional:
        return
    if not root.is_dir():
        raise ValueError(f"Missing database directory: {root}")
    leaves = set()
    directories = {str(Path(path).parent) for path in expected}
    directories |= {str(parent) for path in expected for parent in Path(path).parents}
    for path in root.rglob("*"):
        relative = str(path.relative_to(root))
        if path.is_dir():
            if relative not in directories:
                raise ValueError(f"Unexpected database directory: {path}")
        else:
            leaves.add(relative)
            if relative not in expected or repository.actual_blob(path) != expected[relative]:
                raise ValueError(f"Database path/bytes/mode differs: {path}")
    if leaves != set(expected):
        raise ValueError(f"Incomplete database pathset: {root}")


def copy_database():
    expected = database()
    tree(TZ_SOURCE, expected)
    tree(TZ_DEST, expected, optional=True)
    for relative, (mode, _) in expected.items():
        source, destination = TZ_SOURCE / relative, TZ_DEST / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        destination.chmod(0o755 if mode == "100755" else 0o644)
    tree(TZ_DEST, expected)


def prepare():
    validate_paths((*FILES, *DIRECTORIES, XCODE_DATA, TZ_SOURCE, TZ_DEST))
    for path in FILES:
        if path.exists() and not path.is_file():
            raise ValueError(f"Expected regular cleanup leaf: {path}")
    for path in (*DIRECTORIES, XCODE_DATA):
        if path.exists() and not path.is_dir():
            raise ValueError(f"Expected cleanup directory: {path}")
    for directory in DIRECTORIES:
        if directory.is_dir():
            for path in directory.rglob("*"):
                if path.is_file() and not generated(str(path)):
                    raise ValueError(f"Unexpected cleanup intermediate: {path}")
    for path in FILES:
        path.unlink(missing_ok=True)
    for path in DIRECTORIES:
        if path.exists():
            shutil.rmtree(path)


def verify_resources():
    for name in ("manifest.json", "constants.xlf"):
        source, copied = Path(name), BUNDLE / "Contents/Resources" / name
        require_file(source)
        require_file(copied)
        if repository.actual_blob(copied) != repository.actual_blob(source):
            raise ValueError(f"Copied resource differs from source: {copied}")
    expected = database()
    tree(TZ_SOURCE, expected)
    tree(TZ_DEST, expected)


def merge_windows():
    validate_paths((*DOWNLOADS, WINDOWS_BINARY))
    require_file(DOWNLOADS[0])
    WINDOWS_BINARY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DOWNLOADS[0], WINDOWS_BINARY)


def verify_windows():
    for path in (*DOWNLOADS, WINDOWS_BINARY):
        require_file(path)
    if DOWNLOADS[0].read_bytes() != WINDOWS_BINARY.read_bytes():
        raise ValueError("Merged Windows payload differs from downloaded artifact")


def validate_unsigned():
    validate_paths((*FILES, WINDOWS_BINARY, *DOWNLOADS, *DIRECTORIES, XCODE_DATA,
                    TZ_SOURCE, TZ_DEST))
    for path in FILES[:-1]:
        require_file(path)
    verify_resources()
    verify_windows()
    source_version.verify_bundle(BUNDLE)


def validate_final():
    validate_unsigned()
    require_file(FILES[-1])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=(
        "clean-macos", "verify-resources", "copy-database", "merge-windows",
        "verify-unsigned", "verify-final",
    ))
    phase = parser.parse_args().phase
    {"clean-macos": prepare, "verify-resources": verify_resources,
     "copy-database": copy_database, "merge-windows": merge_windows,
     "verify-unsigned": validate_unsigned, "verify-final": validate_final}[phase]()
