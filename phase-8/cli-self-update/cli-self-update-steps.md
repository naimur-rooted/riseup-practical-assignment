# CLI Self-Update Runbook — mycli

> Source of truth: `cli-self-update.xmind` ("CLI Self-Update System Design"). Replace `OWNER`/`REPO` with actual values before use. Sequence: Check → Compare → Download → Verify → Stage → Smoke Test → Swap → Restart → Cleanup → Rollback.

1. Check
   - What happens: Probe the locally installed version and confirm the update endpoint is reachable before doing anything else. Entry points are `mycli --update`, a startup probe, or the scheduled check (`0 3 * * * /usr/bin/mycli --background-check`).
   - Command/API: `python -c "import mycli; print(mycli.__version__)"`, then `mycli --background-check` and `curl --fail https://api.github.com`.
   - What can go wrong: the import raises `ModuleNotFoundError`; curl exits nonzero on DNS or timeout; the check endpoint is unavailable.
   - Recovery: inspect `python -m pip show mycli`; retry with exponential backoff — 3 retries at 1s, 2s, 4s, 8s — and leave the current install unchanged. Fallback version read is `python -m tomllib pyproject.toml` (fail closed if the file is missing).

2. Compare
   - What happens: Fetch the latest GitHub release metadata, extract its tag, and semver-compare it against the local version. Policy: auto-apply minor/patch, prompt for major; ignore prereleases unless `--include-prerelease` is set.
   - Command/API: `curl -s https://api.github.com/repos/OWNER/REPO/releases/latest | jq -r .tag_name`, then `semver.compare(local, remote)`.
   - What can go wrong: GitHub API returns HTTP 403 rate limit; `jq` outputs `null`; the tag is not valid `vX.Y.Z`; lexical comparison ranks `1.10.0 < 1.9.0`.
   - Recovery: skip the update and retry after `Retry-After`; treat the release metadata as invalid and abort; normalize `v1.2.3` to `1.2.3`, otherwise abort; use numeric `semver.compare`. A major bump requires `mycli --update --yes-major`.

3. Download
   - What happens: Download the matching release asset over HTTPS into `/tmp` without touching the installed program. Wheel path `/tmp/mycli-1.2.3.whl`; Linux binary path `/tmp/mycli-linux-amd64.tar.gz`.
   - Command/API: `curl --fail --location --retry 3 -L -o /tmp/mycli-1.2.3.whl "https://github.com/OWNER/REPO/releases/download/v1.2.3/mycli-1.2.3-py3-none-any.whl"` — or for the binary: `curl -L -o /tmp/mycli-linux-amd64.tar.gz https://github.com/OWNER/REPO/releases/download/v1.2.3/mycli-1.2.3-linux-amd64.tar.gz`.
   - What can go wrong: a network failure leaves a partial `/tmp/mycli-1.2.3.whl`; a proxy blocks GitHub; the release asset is unavailable.
   - Recovery: resume via `/tmp/mycli-1.2.3.whl.part` with `curl -C - -H "Range: bytes=START-" -o artifact.part URL`, then rename atomically; honor `HTTPS_PROXY` or abort without changing the installation; keep the current version and retry later.

4. Verify
   - What happens: Gate the download on integrity: compare the SHA-256 digest against the release's `SHA256SUMS`, optionally validate the GPG signature, and confirm the repo owner matches `OWNER`.
   - Command/API: `sha256sum /tmp/mycli-1.2.3.whl`; fetch `https://github.com/OWNER/REPO/releases/download/v1.2.3/SHA256SUMS`; verify with `sha256sum -c SHA256SUMS --ignore-missing`; optional GPG: `gpg --verify mycli-1.2.3.whl.asc mycli-1.2.3.whl` plus `gpg --fingerprint RELEASE_KEY_ID`.
   - What can go wrong: the digest differs from the release digest; `SHA256SUMS` is missing; GPG reports `BAD signature`; TLS certificate validation fails; a redirect targets a fork.
   - Recovery: abort, `rm -f /tmp/mycli-1.2.3.whl`, keep `/opt/mycli.bak`, notify the user, and re-download once before giving up; require a signed digest or abort; remove the staged artifact; abort and never use `--insecure`; owner check `curl -s https://api.github.com/repos/OWNER/REPO | jq -r .owner.login` must equal `OWNER`.

5. Stage
   - What happens: Stage the artifact under `/tmp/mycli-update/v1.2.3/`, extract the archive, and install into a staging location (`/opt/mycli.new`) without touching the live install.
   - Command/API: `mkdir -p /tmp/mycli-update/v1.2.3/ && chmod 700 /tmp/mycli-update/v1.2.3/`, then `tar -xzf /tmp/mycli-linux-amd64.tar.gz -C /tmp/mycli-update/v1.2.3/` (inspect with `tar -tzf` first); venv strategy `python -m pip install --upgrade --target /opt/mycli/venv/lib/pythonX/site-packages /tmp/mycli-1.2.3.whl`, or user strategy `pip install --user /tmp/mycli-1.2.3.whl`.
   - What can go wrong: staging write returns `ENOSPC` (disk full); the archive has path traversal or is malformed; the temporary path is world-readable; stale files linger from a previous Windows attempt.
   - Recovery: check `df -Pk /tmp /opt | awk 'NR>1 && $4<10240 {exit 1}'`, free space, and retry; inspect `tar -tzf` and reject unsafe entries; `chmod 700 /tmp/mycli-update/v1.2.3/`; on Windows clear stale files with `Remove-Item -Recurse -Force "$env:TEMP\mycli-update\v1.2.3"`.

6. Smoke Test
   - What happens: Validate the staged build before it goes live: probe the staged executable, run the migration dry-run, and run the health check. Success means `mycli --health` exits 0 with healthy output; anything else is a failure.
   - Command/API: `/opt/mycli.new/bin/mycli --version` (validate before swap), then `mycli migrate --dry-run`, then `mycli --health`.
   - What can go wrong: the staged executable exits nonzero; the dry run reports an incompatible schema; the health check exits nonzero.
   - Recovery: delete `/opt/mycli.new` and preserve the current install; do not swap and restore `/opt/mycli.bak`; on health failure auto-rollback with `mv /opt/mycli.bak /opt/mycli`, notify the user, and open an issue at `https://github.com/OWNER/REPO/issues/new?template=bug_report.yml`.

7. Swap
   - What happens: Atomically move the current installation to a backup and promote the staged build into place.
   - Command/API: `mv /opt/mycli /opt/mycli.bak && mv /opt/mycli.new /opt/mycli`.
   - What can go wrong: the second `mv` fails after the backup move; the rename is denied by permissions.
   - Recovery: restore immediately with `mv /opt/mycli.bak /opt/mycli`; request elevation or restore the backup.

8. Restart
   - What happens: Replace the running process with the new binary (or restart the Windows service) and apply any required database migration.
   - Command/API: Unix: `exec /usr/local/bin/mycli "$@"`; Windows: `Restart-Service MyCliService`; migration apply: `python -m mycli.db migrate`.
   - What can go wrong: the new binary is not executable; the service restart times out; the migration exits nonzero.
   - Recovery: `chmod 755 /usr/local/bin/mycli` and retry; run `Get-Service MyCliService` and roll back; roll back the binary and restore the database backup.

9. Cleanup
   - What happens: Clear the application cache so the new version starts fresh, and remove temporary staging leftovers.
   - Command/API: `rm -rf ~/.cache/mycli/*`.
   - What can go wrong: the cache path is misconfigured, so the wrong directory gets wiped.
   - Recovery: print `mycli config get cache_dir` and delete only that directory; delete `/tmp/mycli-update/v1.2.3/` leftovers only after a successful swap.

10. Rollback
   - What happens: Restore the previous installation whenever Swap, Restart, Cleanup, or a later check fails; keep the evidence trail.
   - Command/API: `mv /opt/mycli.bak /opt/mycli`.
   - What can go wrong: the backup `/opt/mycli.bak` is missing.
   - Recovery: reinstall the pinned, verified release asset for `v1.2.3`. Log the failure to `/var/log/mycli-update.log` and open an issue using the template `https://github.com/OWNER/REPO/issues/new?template=bug_report.yml`; if the issue endpoint requires authentication, print the diagnostic bundle for manual submission.

## Postconditions

- Current active version file path updated: `src/mycli/__init__.py` holds `__version__ = "1.2.3"`, matching the runtime probe `python -c "import mycli; print(mycli.__version__)"`.
- Backup location retained for 24 hours: `/opt/mycli.bak`.
- Temp files removed: `/tmp/mycli-update/v1.2.3/` and `/tmp/mycli-1.2.3.whl` are deleted after a successful swap.

