"""Migration pushes permit one exact new branch or direct-child correction."""

import os
import subprocess

from helper_support import GitFixture, ROOT


class MigrationGuardTests(GitFixture):
    def setUp(self):
        super().setUp()
        self.guard = ROOT / ".github/migration-hooks/pre-push"
        self.migration_ref = "refs/heads/miyako-simplify-tz-workflows"
        self.values = {**self.env, "MIGRATION_SHA": self.sha,
                       "MIGRATION_REF": self.migration_ref}

    def invoke(self, rows, env=None):
        return subprocess.run([str(self.guard)], cwd=self.local, input=rows,
                              env=self.values if env is None else env, text=True,
                              capture_output=True)

    def test_exact_record_executable_and_literal_zero_old(self):
        self.assertTrue(os.access(self.guard, os.X_OK))
        row = f"{self.sha} {self.sha} {self.migration_ref} {'0' * 40}\n"
        self.assertEqual(self.invoke(row).returncode, 0)
        self.assertEqual(self.invoke(row.replace(self.sha + " ", "HEAD ", 1)).returncode, 0)
        for invalid in ("", row * 2, row.replace("0" * 40, self.ancestor),
                        row.replace(self.migration_ref, "refs/tags/v2.0.8"),
                        row.replace(self.sha + " ", "refs/heads/selected ", 1)):
            self.assertNotEqual(self.invoke(invalid).returncode, 0)
        self.assertNotEqual(self.invoke(row, self.env).returncode, 0)

    def test_actual_one_new_ref_push_and_second_push_rejected(self):
        command = ["git", "-c", f"core.hooksPath={self.guard.parent}", "-c",
                   "push.followTags=false", "push", "--no-follow-tags", "--porcelain",
                   "origin", f"{self.sha}:{self.migration_ref}"]
        result = subprocess.run(command, cwd=self.local, env=self.values,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        again = subprocess.run(command, cwd=self.local, env=self.values,
                               text=True, capture_output=True)
        self.assertNotEqual(again.returncode, 0, again.stderr)
        self.assertEqual(self.git("--git-dir=" + str(self.bare), "rev-parse",
                                  self.migration_ref), self.sha)
        self.assertEqual(self.git("--git-dir=" + str(self.bare), "tag", "--list"), "")

    def test_actual_direct_child_update_requires_exact_advertised_old(self):
        self.git("-c", "push.followTags=false", "push", "--quiet", "--no-follow-tags",
                 "origin", f"{self.sha}:{self.migration_ref}")
        self.git("commit", "--quiet", "--allow-empty", "-m", "correction fixture")
        child = self.git("rev-parse", "HEAD")
        self.values.update(MIGRATION_SHA=child, MIGRATION_OLD_SHA=self.sha)
        row = f"{child} {child} {self.migration_ref} {self.sha}\n"
        self.assertEqual(self.invoke(row).returncode, 0)
        for invalid in ("", row * 2, row.replace(self.sha, self.ancestor),
                        row.replace(self.sha, "0" * 40)):
            self.assertNotEqual(self.invoke(invalid).returncode, 0)
        command = ["git", "-c", f"core.hooksPath={self.guard.parent}", "-c",
                   "push.followTags=false", "push", "--no-follow-tags", "--porcelain",
                   "origin", f"{child}:{self.migration_ref}"]
        self.git("--git-dir=" + str(self.bare), "update-ref", self.migration_ref, self.ancestor)
        rejected = subprocess.run(command, cwd=self.local, env=self.values,
                                  text=True, capture_output=True)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(self.git("--git-dir=" + str(self.bare), "rev-parse",
                                  self.migration_ref), self.ancestor)
        self.git("--git-dir=" + str(self.bare), "update-ref", self.migration_ref, self.sha)
        result = subprocess.run(command, cwd=self.local, env=self.values,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        again = subprocess.run(command, cwd=self.local, env=self.values,
                               text=True, capture_output=True)
        self.assertNotEqual(again.returncode, 0)
        self.assertEqual(self.git("--git-dir=" + str(self.bare), "rev-parse",
                                  self.migration_ref), child)
        self.assertEqual(self.git("--git-dir=" + str(self.bare), "tag", "--list"), "")
