"""Narrow macOS cleanup and final-only output retention."""

import shutil
from unittest import mock

from helper_support import Fixture, GitFixture, HOSTED, HOSTED_FILES, cwd
import native
import repository


class NativePreparationTests(Fixture):
    def setUp(self):
        super().setUp()
        self.initialize_database_git(self.root)

    def test_selective_cleanup_preserves_resources_dependencies_and_default_siblings(self):
        self.assertEqual(tuple(map(str, native.DIRECTORIES)), tuple(HOSTED["directory_roots"]))
        self.assertEqual(str(native.XCODE_DATA), HOSTED["xcode_data_root"])
        protected = (
            native.BUNDLE / "Contents/QuickLook/Thumbnail.png",
            native.BUNDLE / "Contents/MacOS/runtime.dylib",
            native.BUNDLE / "Contents/Resources/custom.txt",
            native.BASE / "Default/TZ.bundle/Contents/Info.plist",
            native.BASE / "Default/keep", native.BASE / "Other.bundle/keep",
            "build/unrelated/keep", "a/libjsoncpp.a", "lib/windows64/jsoncpp.lib",
        )
        for path in protected:
            self.write(path, b"preserved")
        for path in native.FILES:
            self.write(path, b"stale")
        for path in native.DIRECTORIES:
            (self.root / path).mkdir(parents=True, exist_ok=True)
        for path in HOSTED["observed_files"]:
            self.write(path, b"stale")
        originals = self.build_inputs(self.root)
        original_bytes = {path: (self.root / path).read_bytes() for path in originals}
        original_modes = {path: (self.root / path).stat().st_mode for path in originals}
        with cwd(self.root):
            native.prepare()
            native.prepare()
        for path in protected:
            self.assertEqual((self.root / path).read_bytes(), b"preserved")
        for path in (*native.FILES, *native.DIRECTORIES):
            self.assertFalse((self.root / path).exists(), path)
        for path, raw in original_bytes.items():
            self.assertEqual((self.root / path).read_bytes(), raw)
            self.assertEqual((self.root / path).stat().st_mode, original_modes[path])

    def test_symlink_anywhere_prevalidated_before_first_deletion(self):
        for where in (native.FILES[-1], native.DIRECTORIES[-1], native.BUNDLE,
                      native.DIRECTORIES[0] / "nested/link"):
            with self.subTest(where=where):
                first = self.write(native.FILES[0], b"must remain")
                destination = self.write("outside/keep", b"untouched")
                link = self.root / where
                if link.is_dir():
                    shutil.rmtree(link)
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(destination)
                with cwd(self.root), self.assertRaisesRegex(ValueError, "symlink"):
                    native.prepare()
                if where != native.BUNDLE:
                    self.assertEqual(first.read_bytes(), b"must remain")
                self.assertEqual(destination.read_bytes(), b"untouched")
                link.unlink()

    def test_cleanup_io_error_is_fatal(self):
        self.write(native.FILES[0], b"stale")
        with cwd(self.root), mock.patch("pathlib.Path.unlink", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                native.prepare()
        self.write(HOSTED["observed_files"][0], b"stale")
        with cwd(self.root), mock.patch("shutil.rmtree", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                native.prepare()

    def test_late_wrong_types_nested_git_and_unexpected_source_preserve_first_leaf(self):
        first = self.write(native.FILES[0], b"must remain")
        cases = (
            (native.FILES[-1], "directory"),
            (native.DIRECTORIES[-1], "file"),
            (native.XCODE_DATA, "file"),
            (native.DIRECTORIES[-1] / "nested/.git", "file"),
            (native.DIRECTORIES[-1] / "nested/.git", "directory"),
            (native.DIRECTORIES[0].parent / ".git", "file"),
            (native.DIRECTORIES[0] / "unexpected-source.cpp", "file"),
        )
        for relative, kind in cases:
            with self.subTest(relative=relative, kind=kind):
                path = self.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                if kind == "directory":
                    path.mkdir()
                else:
                    path.write_bytes(b"must remain too")
                with cwd(self.root), self.assertRaises(ValueError):
                    native.prepare()
                self.assertEqual(first.read_bytes(), b"must remain")
                self.assertTrue(path.exists())
                shutil.rmtree(path) if path.is_dir() else path.unlink()
        with cwd(self.root):
            native.prepare()
        self.assertFalse(first.exists())

    def test_resources_must_be_fresh_exact_source_copies(self):
        for name in ("constants.xlf", "manifest.json"):
            self.write(name, b"source")
            self.write(native.BUNDLE / "Contents/Resources" / name, b"source")
        with cwd(self.root):
            native.copy_database()
            native.verify_resources()
            (native.BUNDLE / "Contents/Resources/constants.xlf").write_bytes(b"stale")
            with self.assertRaisesRegex(ValueError, "differs"):
                native.verify_resources()

    def test_databases_and_unsupported_old_build_roots_are_not_recursively_cleaned(self):
        paths = (
            "build/XCBuildData/build.db",
            "build/XCBuildData/unexpected-source.cpp",
            "build/XCBuildData/evil.xcbuilddata/keep",
            str(native.XCODE_DATA / "build.db"),
            str(native.XCODE_DATA / "build.db-wal"),
            str(native.XCODE_DATA / "build.db-shm"),
        )
        for path in paths:
            self.write(path, b"preserve original bytes")
        with cwd(self.root):
            native.prepare()
        for path in paths:
            self.assertEqual((self.root / path).read_bytes(), b"preserve original bytes")


class GeneratedRetentionTests(GitFixture):
    def test_actual_xcode_database_wal_and_outputs_are_final_only(self):
        for relative in (
            *native.FILES,
            *HOSTED_FILES,
        ):
            target = self.local / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"fresh native output")
        with cwd(self.local):
            with self.assertRaises(ValueError):
                repository.verify_checkout(self.sha, generated=native.generated)
            repository.verify_checkout(self.sha, generated=native.generated, final=True)

    def test_evil_siblings_and_protected_resource_never_gain_final_exemption(self):
        for relative in (
            "build/XCBuildData-evil/build.db",
            "build/XCBuildData/build.db",
            "build/XCBuildData/unexpected-source.cpp",
            "build/XCBuildData/build.db-evil",
            "build/XCBuildData/evil.xcbuilddata/build-request.json",
            "build/TZ.build-evil/main.o",
            "build/TZ.build/Default/TZ.build/Objects-normal/arm64/4DPlugin.o",
            "build/Default/TZ.build/main.o",
            "test/Plugins/TZ.build/main.o",
            "TZ.4dbase/Plugins/XCBuildData/unexpected-source.cpp",
            "TZ.4dbase/Plugins/XCBuildData/build.db-evil",
            "TZ.4dbase/Plugins/XCBuildData/evil.xcbuilddata/build-request.json",
            "TZ.4dbase/Plugins/XCBuildData/f5f9cc94a5e6fff3f9379ac38c18e8df.xcbuilddata/source.cpp",
            "TZ.4dbase/Plugins/TZ.build/Deployment/TZ.build/TZ.hmap",
            "build/unexpected-source.cpp",
            "Objs/Release-evil/main.obj",
            "Objs/Debug/main.obj",
            "winbuild/nested/TZ.4DX",
            "test/Plugins/Default/TZ.bundle/Contents/Info.plist",
            str(native.BUNDLE / "Contents/QuickLook/Thumbnail.png"),
            str(native.BUNDLE / "Contents/MacOS/runtime.dylib"),
            str(native.BUNDLE / "Contents/Resources/custom.txt"),
            str(native.BUNDLE / "Contents/_CodeSignature/evil"),
        ):
            with self.subTest(relative=relative):
                target = self.local / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"unexpected")
                with cwd(self.local), self.assertRaises(ValueError):
                    repository.verify_checkout(self.sha, generated=native.generated, final=True)
                target.unlink()
