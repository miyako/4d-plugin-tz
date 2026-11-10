# Manual source maintenance and publication

**Bump version** has exactly one required `mode`: `patch` (default), `minor`, or
`major`. Select a branch with GitHub's built-in ref selector. It validates the
immutable dispatch SHA, then makes one source-only direct-child commit with
explicit Actions bot author/committer and the literal ending Copilot App trailer.
It never creates a tag, release, build, or dispatch. The executable pre-push guard
is revalidated against its committed `100755` raw blob on every use, including
after the last remote read. It checks exactly one advertised old/new/ref record.
Advance, rewind, deletion, and same-result races stop; ordinary nonforce alone is
not enough. Both `push.followTags=false` and `--no-follow-tags` suppress incidental
annotated tags. A failure retains local state; inspect it rather than retrying.

**Build** is a separate manual workflow with **zero custom inputs**. Select the
desired source ref in GitHub's selector. Every checkout uses `github.sha`.
Publication uses a constant repository-wide concurrency group, without cancelling
an active run. This serializes publication across refs but promises no FIFO order.
The original repository had only these two release-related workflows, with a tag
push trigger; this migration introduces no push/PR native CI.

## TZ version authority

Intake: `d87f18f63e30925c3fdc03c4b03efec6b71c59e7`, canonical API identity
`miyako/4d-plugin-tz`, default/symbolic/advertised branch `master`.
The explicit coordinated header at
`73add414867fa7ba3d068f5ac14fc3b7bd3f7b42` supersedes the older marketing/current
fallback header at `a829a5a4ff5dda39695a255a33196e44ab892b52`. Its buggy
marketing-only body does not override the stated coordination contract.

There is **no intake increment**: source `Info.plist` remains `1.0.9`;
six `MARKETING_VERSION` values remain `1.0.9`; six stale `CURRENT_PROJECT_VERSION`
values align from `1.0.7` to `1.0.9`. These are the target and project
Development/Deployment/Default configurations with their exact identities.
The copied source `English.lproj/InfoPlist.strings` aligns its short and get-info
versions from `1.0` to `1.0.9`, preserving UTF-8 BOM, CR endings, and copyright.
The required short-version key, absent optional build key, product references,
unrelated bytes, and modes remain intact. Later bumps validate everything before
writing only version token spans, preserving UTF-8/UTF-16 encodings, BOMs, mixed
line endings, and variable references. Duplicate keys, including quoted inline
project assignments, missing fields, configuration drift, bad versions,
unresolved references, and cycles fail before writes.

The prebuilt `TZ.4dbase` plist/localization (including UTF-16LE stale `1.0`)
are not source authority and are untouched. `manifest.json`, `constants.xlf`,
native project layout, SDKs, prebuilt libraries, runtime code, and 4D data are
also unchanged.

## Preserved native policy and narrowly approved resource repair

Windows remains Release/x64 with the **original CMD MSBuild command unchanged**.
Its exact project output is
`TZ.4dbase/plugins/TZ.bundle/contents/windows64/TZ.4DX` (NTFS aliases the tracked
uppercase directory names). Only this fresh nonempty regular file is collected
into `test/Plugins/TZ.bundle/Contents/Windows64/TZ.4DX`; recursive first-match
discovery is forbidden. Git's scoped inherited `core.autocrlf=false` is present
before every Build checkout, without changing global configuration.
Only actual Windows regular-file executable-bit differences are tolerated when
raw blobs match. Selected/index modes stay exact; links/reparse points never
qualify.

macOS remains Xcode `Default`, `ARCHS="arm64 x86_64"`, `ONLY_ACTIVE_ARCH=NO`,
deployment override **11.0**, **both** `CODE_SIGNING_ALLOWED=NO` and
`CONFIGURATION_BUILD_DIR="$PWD/$BASE_DIR/Plugins"` with **BASE_DIR=test**.
No native project/output-root change or dependency rebuild was introduced.
The exact downloaded Windows file is merged and compared again before release.
The exact `arm64` and `x86_64` architecture tokens are required, without inventing
an i386 ban or runtime-dylib policy.

**TZ-only user approval (2026-11-10, coordinator 13:58 JST):** the old intentional
`test` output lacked the timezone database required by `4DPlugin.cpp` and the
root README. Packaging now copies only the immutable tracked
`TZ.4dbase/Plugins/TZ.bundle/Contents/Resources/tzdata` to
`test/Plugins/TZ.bundle/Contents/Resources/tzdata`. All 34 tracked paths, raw
bytes, and path modes are required at unsigned and final gates. Partial,
missing, modified, extra, linked, nonregular, or escaping database trees fail
closed. The source and other prebuilt resources remain untouched. This is not
permission for downloads, database refreshes, runtime changes, or broad copying.

Cleanup prevalidates every affected path before deleting only generated leaves
and exact intermediate roots. It never removes entire bundles, `Default`
packages, lowercase plugin directories, or `build/`. Tracked
`build/XCBuildData/build.db` and Deployment-unknown intermediates were inspected
at intake. The final gate retains generated bytes instead of resetting them.
XCBuildData permits only `build.db`, `build.db-wal`, `build.db-shm`, and
32-lowercase-hex `.xcbuilddata` descendants, not arbitrary source siblings.
Initial checkout must be clean, including ignored files; the final guard checks
unchanged HEAD/index and raw nongenerated bytes independently of stat caches,
clean filters, and **both** `git ls-files -v` and `-f` hidden flags.

Unsigned validation does not require a signature. Final validation requires every
nonempty regular packaged leaf, correct XML/binary plist and localization, exact
manifest/constants/database copies, signature, and byte-identical Windows merge.
Signing still uses Developer ID, deep/timestamp/runtime options and strict deep
verification. Both ZIP and DMG notarizations require exit zero **and** strict JSON
`Accepted`; stapling and post-staple strict verification must succeed.

## Authenticated create-only publication and recovery

Before native work and after all build/sign/notary/staple steps, explicit nonempty
`GH_TOKEN`, exact case-sensitive canonical repository identity, immutable SHA,
source and checkout integrity are required. Draft-inclusive release pagination
continues until an **empty** page. Duplicate JSON keys, nonfinite numbers,
malformed schema/IDs, 404/auth/network/later-page errors abort; no absence fallback.
Both matching-refs API and exact `ls-remote` must report the canonical tag absent.

Publication separately POSTs a new tag ref at the selected SHA, verifies API and
remote advertisement, then POSTs a fresh public nonprerelease release with exact
tag/name/target, empty body, and generated notes disabled (the original softprops
configuration supplied only tag/name/files). A positive release ID must not be a
prior ID. Only `TZ-X.Y.Z.zip` and `TZ-X.Y.Z.dmg` upload to that new ID; exact remote
names, integer sizes and uploaded state are verified. No update, DELETE, PATCH,
clobber, reuse, rollback or automatic retry is performed.

**Partial failures are intentionally retained.** A lost response can leave a tag,
release, or uploaded asset even when the local operation fails. Read the reported
tag/release ID and inspect GitHub manually; do not rerun or automate cleanup.
An authorized human must decide recovery, or use a new source version.

## Offline validation and migration handoff

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
actionlint .github/workflows/*.yml
```

Tests use local bare Git, fake `gh`, closed-PATH native/credential doubles, and
actual Bash/PowerShell extracted workflow programs. No real native build,
signing, notarization, 4D, production push/tag/release, Actions dispatch or secrets
are used. CMD is preserved and static-tested, not emulated. PowerShell, PyYAML,
and actionlint must already be available; tests have no skip path.
An actual local clone/checkout regression starts with hostile `autocrlf=true`
in a fixture-only HOME/global file, inherits the workflow's scoped false setting
before clone and detached checkout, and independently checks every raw blob and
index entry. A late-setting negative control retains converted bytes and fails
before API access. The cloned checkout also exercises Windows-only executable
mode tolerance and raw/index/type/reparse failures, then restores a passing
preflight without changing the fixture global file or any host/global config.

Adapted immutable donor code/tests were actually read and raw-blob verified:
UTI `5decf4be07f8297d256dfb559ef9466525fe9045` (source model, workflow/native
scaffold and adversarial tests), STOMP
`ab9f5e51dba5b8b6ec1a1b70e191082fcb73fb41` (guarded bump, Windows raw-mode guard
and race tests), libarchive `9547d09522fc422ddd754fb088165b3d1d1d3073`
(strict create-only publication and BOTH hidden-flag checks), and RTF2TEXT
`4a8c89677515cd5c71c162e0b296e63bee374cdd` (Windows merge/final leaf context).
Product-specific donor dependencies/output exceptions were not imported.

The executable `.github/migration-hooks/pre-push` is ready for the coordinator's
one-ref nonforce migration push, using `MIGRATION_SHA`, exact
`MIGRATION_REF=refs/heads/miyako-simplify-tz-workflows`, and optional exact
`MIGRATION_OLD_SHA` for a direct-child correction. Both no-follow-tags protections
are mandatory. Production push and PR creation belong to the coordinator.
