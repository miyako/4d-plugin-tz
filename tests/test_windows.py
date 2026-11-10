"""Actual extracted PowerShell under a closed PATH; CMD remains static-only."""

from pathlib import Path
import shutil
import subprocess

import yaml

from helper_support import Fixture, ROOT, original
import native


class WindowsScriptTests(Fixture):
    def setUp(self):
        super().setUp()
        self.checkout = self.root / "checkout"
        self.checkout.mkdir()
        shutil.copytree(ROOT / ".github/scripts", self.checkout / ".github/scripts")
        self.tools = self.root / "closed-path"
        self.tools.mkdir()
        self.env = {
            "PATH": str(self.tools), "HOME": str(self.root), "PRODUCT_NAME": "TZ",
            "BASE_DIR": "test", "POWERSHELL_TELEMETRY_OPTOUT": "1",
            "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        }
        workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
        self.steps = workflow["jobs"]["build-windows"]["steps"]
        self.pwsh = "/usr/local/bin/pwsh" if Path("/usr/local/bin/pwsh").exists() else shutil.which("pwsh")
        self.assertIsNotNone(self.pwsh, "PowerShell is required; this suite never skips")
        self.protected = {}
        for relative in (
            "TZ.4dbase/Plugins/TZ.bundle/Contents/Resources/tzdata/africa",
            "TZ.4dbase/Plugins/TZ.bundle/Contents/QuickLook/Thumbnail.png",
            "test/Plugins/Default/keep", "test/plugins/keep",
            "Objs/Debug/keep", "Objs/Release-evil/keep",
        ):
            target = self.checkout / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"untouched")
            self.protected[target] = b"untouched"

    def put(self, path, raw):
        target = self.checkout / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        return target

    def phase(self, name, success=True):
        step = next(step for step in self.steps if step.get("name") == name)
        self.assertEqual(step["shell"], "pwsh")
        self.assertNotIn("${{", step["run"])
        result = subprocess.run(
            [self.pwsh, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", step["run"]],
            cwd=self.checkout, env=self.env, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def test_exact_fresh_output_copy_not_recursive_first_match_and_preserve_every_sibling(self):
        self.put(native.WINDOWS_SOURCE, b"stale source")
        self.put(native.WINDOWS_BINARY, b"stale destination")
        self.put("Objs/Release/intermediate.obj", b"stale")
        self.phase("clean stale outputs")
        self.assertFalse((self.checkout / native.WINDOWS_SOURCE).exists())
        self.assertFalse((self.checkout / native.WINDOWS_BINARY).exists())
        self.assertFalse((self.checkout / "Objs/Release").exists())
        self.put("other/Plugins/TZ.4DX", b"recursive decoy")
        self.phase("normalize windows output to canonical case", success=False)
        source = self.put(native.WINDOWS_SOURCE, b"fresh exact binary")
        self.phase("normalize windows output to canonical case")
        self.assertEqual((self.checkout / native.WINDOWS_BINARY).read_bytes(), source.read_bytes())
        for path, raw in self.protected.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_empty_directory_symlink_and_symlink_ancestor_never_collect(self):
        source = self.put(native.WINDOWS_SOURCE, b"")
        self.phase("normalize windows output to canonical case", success=False)
        source.unlink()
        source.mkdir()
        self.phase("normalize windows output to canonical case", success=False)
        source.rmdir()
        outside = self.root / "outside.4DX"
        outside.write_bytes(b"samebytes")
        source.symlink_to(outside)
        self.phase("normalize windows output to canonical case", success=False)
        source.unlink()
        source.write_bytes(b"fresh")
        destination = self.checkout / native.WINDOWS_BINARY
        destination.parent.mkdir(parents=True)
        moved = self.root / "moved-Windows64"
        destination.parent.rename(moved)
        destination.parent.symlink_to(moved, target_is_directory=True)
        self.phase("normalize windows output to canonical case", success=False)
        self.assertEqual(source.read_bytes(), b"fresh")
        self.assertFalse((moved / "TZ.4DX").exists())

    def test_cleanup_prevalidates_all_paths_before_any_delete(self):
        source = self.put(native.WINDOWS_SOURCE, b"must remain")
        destination = self.checkout / native.WINDOWS_BINARY
        destination.mkdir(parents=True)
        self.phase("clean stale outputs", success=False)
        self.assertEqual(source.read_bytes(), b"must remain")
        destination.rmdir()
        outside = self.root / "outside"
        outside.mkdir()
        release = self.checkout / "Objs/Release"
        release.symlink_to(outside, target_is_directory=True)
        self.phase("clean stale outputs", success=False)
        self.assertEqual(source.read_bytes(), b"must remain")
        release.unlink()
        for relative, kind in (
            ("Objs/Release", "file"),
            ("Objs/Release/nested/.git", "file"),
            ("Objs/Release/nested/.git", "directory"),
            ("Objs/.git", "file"),
            ("test/Plugins/.git", "file"),
            ("test/Plugins/.git", "symlink"),
            (str(native.WINDOWS_BINARY), "symlink"),
        ):
            with self.subTest(relative=relative, kind=kind):
                path = self.checkout / relative
                if path.is_dir():
                    shutil.rmtree(path)
                path.parent.mkdir(parents=True, exist_ok=True)
                if kind == "directory":
                    path.mkdir()
                elif kind == "symlink":
                    path.symlink_to(self.root / "missing-link-target")
                else:
                    path.write_bytes(b"protected")
                self.phase("clean stale outputs", success=False)
                self.assertEqual(source.read_bytes(), b"must remain")
                self.assertTrue(path.exists() or path.is_symlink())
                shutil.rmtree(path) if path.is_dir() else path.unlink()
        self.phase("clean stale outputs")
        self.assertFalse(source.exists())

    def test_original_cmd_and_project_output_contract_static_only(self):
        before = yaml.safe_load(original(".github/workflows/release.yml"))
        original_step = next(step for step in before["jobs"]["build-windows"]["steps"]
                             if step.get("name") == "build x64")
        step = next(step for step in self.steps if step.get("name") == "build x64")
        self.assertEqual(step, original_step)
        self.assertEqual(step["shell"], "cmd")
        self.assertIn('msbuild "%PRODUCT_NAME%.sln" /p:Configuration=Release /p:Platform=x64',
                      step["run"])
        self.assertIn(b'$(ProjectDir)$(ProjectName).4dbase\\plugins\\$(ProjectName).bundle\\contents\\windows64\\',
                      original("TZ.vcxproj"))
        for name in ("TZ.vcxproj", "TZ.sln"):
            self.assertEqual((ROOT / name).read_bytes(), original(name))
        workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
        self.assertEqual({key: value for key, value in workflow["env"].items()
                          if key.startswith("GIT_CONFIG_")}, {
            "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.autocrlf",
            "GIT_CONFIG_VALUE_0": "false",
        })
        self.assertNotIn("--global", (ROOT / ".github/workflows/release.yml").read_text())
