"""Real CLI negatives must precede every API call, followed by restored positives."""

import shutil
import subprocess
import sys

import yaml

from helper_support import ROOT, cwd, source
from test_release import PublicationCLIBase
import native


class FinalGateTests(PublicationCLIBase):
    def test_every_packaged_leaf_missing_empty_directory_and_samebytes_symlink_before_api(self):
        expected = self.build()
        leaves = (*native.FILES, native.WINDOWS_BINARY, *native.DOWNLOADS)
        for relative in leaves:
            target = self.local / relative
            raw, mode = target.read_bytes(), target.stat().st_mode & 0o777
            outside = self.root / "same-bytes-leaf"
            outside.write_bytes(raw)
            for kind in ("missing", "empty", "directory", "symlink"):
                with self.subTest(path=relative, kind=kind):
                    target.unlink()
                    if kind == "empty":
                        target.touch()
                    elif kind == "directory":
                        target.mkdir()
                    elif kind == "symlink":
                        target.symlink_to(outside)
                    result = self.command("publish")
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertEqual(self.calls(), [], result.stderr)
                    if kind == "directory":
                        target.rmdir()
                    elif target.exists() or target.is_symlink():
                        target.unlink()
                    target.write_bytes(raw)
                    target.chmod(mode)
        with cwd(self.local):
            native.FILES[-1].unlink()
            native.validate_unsigned()
            with self.assertRaises(ValueError):
                native.validate_final()
            native.FILES[-1].write_bytes(expected[str(native.FILES[-1])])
        self.assertEqual(self.command("publish").returncode, 0)
        for path, raw in expected.items():
            self.assertEqual((self.local / path).read_bytes(), raw)

    def test_late_windows_byte_change_rejected_and_restored_positive(self):
        expected = self.build()
        target = self.local / native.WINDOWS_BINARY
        target.write_bytes(b"different nonempty Windows bytes")
        self.assertNotEqual(self.command("publish").returncode, 0)
        self.assertEqual(self.calls(), [])
        target.write_bytes(expected[str(native.WINDOWS_BINARY)])
        self.assertEqual(self.command("publish").returncode, 0)

    def test_complete_real_database_missing_modified_extra_mode_symlink_and_partial_tree(self):
        expected = self.build()
        entries = native.database_entries(str(self.local), self.sha)
        self.assertEqual(len(entries), 34)
        name = "africa"
        target = self.local / native.TZ_DEST / name
        raw, mode = target.read_bytes(), target.stat().st_mode & 0o777
        outside = self.root / "same-database-bytes"
        outside.write_bytes(raw)
        for kind in ("missing", "modified", "empty", "symlink", "directory", "mode", "extra"):
            with self.subTest(kind=kind):
                target.unlink()
                if kind not in ("missing", "directory", "symlink"):
                    target.write_bytes(raw if kind in ("mode", "extra") else b"modified")
                    target.chmod(mode ^ 0o111 if kind == "mode" else mode)
                elif kind == "directory":
                    target.mkdir()
                elif kind == "symlink":
                    target.symlink_to(outside)
                extra = self.local / native.TZ_DEST / "unexpected"
                if kind == "extra":
                    extra.write_bytes(b"extra")
                for operation in ("publish", "check"):
                    self.assertNotEqual(self.command(operation).returncode, 0)
                    self.assertEqual(self.calls(), [])
                if kind == "directory":
                    target.rmdir()
                elif target.exists() or target.is_symlink():
                    target.unlink()
                extra.unlink(missing_ok=True)
                target.write_bytes(raw)
                target.chmod(mode)
        shutil.rmtree(self.local / native.TZ_DEST)
        target.parent.mkdir()
        target.write_bytes(raw)
        with cwd(self.local), self.assertRaises(ValueError):
            native.copy_database()
        self.assertNotEqual(self.command("publish").returncode, 0)
        self.assertEqual(self.calls(), [])
        shutil.rmtree(self.local / native.TZ_DEST)
        with cwd(self.local):
            native.copy_database()
            native.validate_unsigned()
        result = self.command("publish")
        self.assertEqual(result.returncode, 0, result.stderr)
        for path, raw in expected.items():
            self.assertEqual((self.local / path).read_bytes(), raw)

    def test_database_source_modified_extra_and_symlink_are_zero_write_and_before_api(self):
        self.build()
        root = self.local / native.TZ_SOURCE
        target = root / "africa"
        raw, mode = target.read_bytes(), target.stat().st_mode & 0o777
        destination = self.local / native.TZ_DEST / "africa"
        outside = self.root / "external-database"
        outside.write_bytes(raw)
        for kind in ("modified", "extra", "symlink"):
            if kind == "modified":
                target.write_bytes(b"bad")
            elif kind == "extra":
                (root / "extra").write_bytes(b"bad")
            else:
                target.unlink()
                target.symlink_to(outside)
            with cwd(self.local), self.assertRaises(ValueError):
                native.copy_database()
            self.assertEqual(destination.read_bytes(), raw)
            self.assertNotEqual(self.command("publish").returncode, 0)
            self.assertEqual(self.calls(), [])
            if target.is_symlink():
                target.unlink()
            target.write_bytes(raw)
            target.chmod(mode)
            (root / "extra").unlink(missing_ok=True)
        self.assertEqual(self.command("publish").returncode, 0)

    def test_actual_real_git_fsmonitor_v_H_f_h_preflight_and_generated_final(self):
        for phase, path in (("preflight", str(source.PLIST)),
                            ("publish", self.generated[0])):
            if phase == "publish":
                self.build()
            self.reset_api()
            self.git("config", "core.fsmonitor", "true")
            self.git("update-index", "--fsmonitor-valid", "--", path)
            self.assertEqual(self.git("ls-files", "-v", "--", path), "H " + path)
            self.assertEqual(self.git("ls-files", "-f", "--", path), "h " + path)
            result = self.command(phase)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Hidden index/stat", result.stderr)
            self.assertEqual(self.calls(), [])
            self.git("config", "core.fsmonitor", "false")
            self.git("update-index", "--no-fsmonitor")
            self.git("update-index", "--no-fsmonitor-valid", "--", path)
            self.assertEqual(self.git("ls-files", "-f", "--", path), "H " + path)
            result = self.command(phase)
            self.assertEqual(result.returncode, 0, result.stderr)


class WindowsModeTests(PublicationCLIBase):
    def setup_windows(self):
        self.git("update-index", "--chmod=+x", "--", "native.cpp")
        (self.local / "native.cpp").chmod(0o755)
        self.git("commit", "--quiet", "-m", "committed executable source")
        self.sha = self.git("rev-parse", "HEAD")
        self.env["GITHUB_SHA"] = self.sha
        self.git("config", "core.filemode", "false")
        for name in self.git("ls-files").splitlines():
            (self.local / name).chmod(0o644)
        self.bootstrap = self.root / "windows-bootstrap.py"
        self.bootstrap.write_text('''
import os, pathlib, runpy, sys, types
sys.path.insert(0, ".github/scripts")
import repository, native, release
sys.platform = os.environ.get("TEST_PLATFORM", "win32")
real = pathlib.Path.lstat
def lstat(path, *args, **kwargs):
    result = real(path, *args, **kwargs)
    if str(path) == os.environ.get("TEST_REPARSE"):
        return types.SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
    return result
pathlib.Path.lstat = lstat
sys.argv = [".github/scripts/release.py", "preflight", "--sha", os.environ["GITHUB_SHA"]]
runpy.run_path(sys.argv[0], run_name="__main__")
''')

    def windows(self, **env):
        return subprocess.run([sys.executable, str(self.bootstrap)], cwd=self.local,
                              env={**self.env, **env}, text=True, capture_output=True, timeout=60)

    def test_win32_only_raw_equal_regular_executable_mode_tolerance(self):
        self.setup_windows()
        result = self.windows()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.reset_api()
        self.assertNotEqual(self.windows(TEST_PLATFORM="darwin").returncode, 0)
        self.assertEqual(self.calls(), [])
        raw = (self.local / "native.cpp").read_bytes()
        for stage in ("raw", "staged", "reversed", "indexmode"):
            with self.subTest(stage=stage):
                target = self.local / "native.cpp"
                target.write_bytes(raw + b"bad")
                if stage in ("staged", "reversed"):
                    self.git("add", "--", "native.cpp")
                if stage == "reversed":
                    target.write_bytes(raw)
                if stage == "indexmode":
                    target.write_bytes(raw)
                    self.git("update-index", "--chmod=-x", "--", "native.cpp")
                self.assertNotEqual(self.windows().returncode, 0)
                self.assertEqual(self.calls(), [])
                target.write_bytes(raw)
                self.git("add", "--", "native.cpp")
                self.git("update-index", "--chmod=+x", "--", "native.cpp")
        self.assertEqual(self.windows().returncode, 0)

    def test_windows_types_reparse_leaf_and_ancestors_are_never_normalized(self):
        self.setup_windows()
        target = self.local / "native.cpp"
        raw = target.read_bytes()
        outside = self.root / "same-bytes"
        outside.write_bytes(raw)
        target.unlink()
        target.symlink_to(outside)
        self.assertNotEqual(self.windows().returncode, 0)
        self.assertEqual(self.calls(), [])
        target.unlink()
        target.mkdir()
        self.assertNotEqual(self.windows().returncode, 0)
        self.assertEqual(self.calls(), [])
        target.rmdir()
        target.write_bytes(raw)
        for marker in ("native.cpp", "."):
            self.assertNotEqual(self.windows(TEST_REPARSE=marker).returncode, 0)
            self.assertEqual(self.calls(), [])
        result = self.windows()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_extracted_pwsh_preflight_scoped_config_executes_actual_windows_simulated_cli(self):
        self.setup_windows()
        workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
        step = next(step for step in workflow["jobs"]["build-windows"]["steps"]
                    if step.get("name") == "Check clean selected checkout before native work")
        python = self.tools / "python"
        python.write_text(
            f"#!{sys.executable}\nimport os,sys\n"
            "assert sys.argv[1:] == ['.github/scripts/release.py', 'preflight', '--sha', os.environ['GITHUB_SHA']]\n"
            "assert os.environ['GIT_CONFIG_COUNT'] == '1'\n"
            "assert os.environ['GIT_CONFIG_KEY_0'] == 'core.autocrlf'\n"
            "assert os.environ['GIT_CONFIG_VALUE_0'] == 'false'\n"
            f"os.execv({sys.executable!r}, [{sys.executable!r}, {str(self.bootstrap)!r}])\n"
        )
        python.chmod(0o755)
        env = {**self.env, **workflow["env"], "TEST_PLATFORM": "win32",
               "POWERSHELL_TELEMETRY_OPTOUT": "1", "DOTNET_CLI_TELEMETRY_OPTOUT": "1"}
        pwsh = "/usr/local/bin/pwsh" if (ROOT / "/usr/local/bin/pwsh").exists() else shutil.which("pwsh")
        self.assertIsNotNone(pwsh)
        command = [pwsh, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", step["run"]]
        result = subprocess.run(command, cwd=self.local, env=env, text=True,
                                capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.reset_api()
        (self.local / "native.cpp").write_bytes(b"bad raw bytes")
        result = subprocess.run(command, cwd=self.local, env=env, text=True,
                                capture_output=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preflight failed", result.stderr)
        self.assertEqual(self.calls(), [])
