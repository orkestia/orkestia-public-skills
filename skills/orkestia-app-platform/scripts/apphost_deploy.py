#!/usr/bin/env python3
"""Publish a static build to an AppHost site (https://<slug>.app.orkestia.dev) in one process.

    # token: console -> Settings -> API Tokens; save it to ~/.orkestia/api-token
    # (or export ORKESTIA_API_TOKEN)
    python3 apphost_deploy.py --slug crm dist/
    python3 apphost_deploy.py --site-uuid <uuid> bundle.zip

Runs apphost.release.create -> S3 upload -> apphost.release.publish -> live check
against workflow-api. The presigned upload form (policy, signature, session
token) goes straight from the API response into the upload request, so no
agent ever has to copy it: one changed character in those ~3 KB makes S3
answer SignatureDoesNotMatch or InvalidToken.

Python 3.8+, standard library only. --check validates the bundle and stops.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_API = "https://workflow-api.orkestia.dev"
TOKEN_FILE = Path.home() / ".orkestia" / "api-token"
USER_AGENT = "orkestia-apphost-deploy/1"
# A production bundle that still points at a dev server breaks login
# ("redirect_uri is not registered") or API calls for every visitor.
DEV_URL = re.compile(rb"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0)(?::\d+)?[^\s\"'`)]*")
SCANNED_SUFFIXES = (".html", ".js", ".mjs", ".json")


class DeployError(Exception):
    pass


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# --- workflow-api ------------------------------------------------------------

class Api:
    def __init__(self, base: str, token: str, timeout: float = 300.0):
        self.base = base.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            if exc.code in (401, 403):
                raise DeployError(
                    f"workflow-api refused the token (HTTP {exc.code}). Create a new one in the "
                    f"console (Settings -> API Tokens) for the organization that owns the site. {detail}"
                ) from None
            raise DeployError(f"{method} {path}: HTTP {exc.code}: {detail}") from None

    def run(self, workflow_type: str, initial_data: dict) -> dict:
        """Start a workflow, wait for it to finish, return its state_data."""
        state = self._call("POST", "/api/workflows/start", {
            "workflow_type": workflow_type,
            "initial_data": initial_data,
            "triggered_by": "apphost_deploy.py",
        })
        deadline = time.monotonic() + self.timeout
        delay = 0.5
        while not state.get("is_terminal"):
            if time.monotonic() > deadline:
                raise DeployError(f"{workflow_type} ({state.get('workflow_id')}) did not finish in {self.timeout:.0f}s")
            time.sleep(delay)
            delay = min(delay * 2, 3.0)
            state = self._call("GET", f"/api/workflows/{state['workflow_id']}")
        data = state.get("state_data") or {}
        if state.get("terminal_status") != "success":
            reason = data.get("failure_reason") or data.get("error") or state.get("state_name")
            raise DeployError(f"{workflow_type} failed ({state.get('workflow_id')}): {reason}")
        return data


# --- bundle ------------------------------------------------------------------

def build_bundle(source: Path) -> bytes:
    """Zip a build directory (index.html at the archive root) or read an existing zip."""
    if source.is_dir():
        if not (source / "index.html").is_file():
            raise DeployError(f"{source}/index.html not found: point at the build output (e.g. dist/)")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(source.rglob("*")):
                if path.is_file() and path.name != ".DS_Store":
                    zf.write(path, path.relative_to(source).as_posix())
        return buf.getvalue()
    if source.suffix.lower() == ".zip" and source.is_file():
        return source.read_bytes()
    raise DeployError(f"{source} is neither a build directory nor a .zip file")


def check_bundle(bundle: bytes, allow_dev_urls: bool) -> tuple[bytes, int]:
    """Validate the archive; return (index.html bytes, file count)."""
    with zipfile.ZipFile(io.BytesIO(bundle)) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        if "index.html" not in names:
            nested = [n for n in names if n.endswith("/index.html")]
            hint = f" (found {nested[0]}: zip the contents of that folder, not the folder)" if nested else ""
            raise DeployError(f"bundle has no index.html at the archive root{hint}")
        for name in names:
            if name.startswith("/") or ".." in name.split("/"):
                raise DeployError(f"bundle path {name!r} is not allowed")
        hits = []
        for name in names:
            if name.lower().endswith(SCANNED_SUFFIXES) and not name.endswith(".map"):
                for match in DEV_URL.finditer(zf.read(name)):
                    hits.append(f"{name}: {match.group().decode('utf-8', 'replace')}")
        if hits and not allow_dev_urls:
            listed = "\n  ".join(sorted(set(hits))[:10])
            raise DeployError(
                "the build still points at a local dev server:\n  " + listed +
                "\nRebuild with the production values (for example the app's redirect URI must be "
                "https://<slug>.app.orkestia.dev/callback), or pass --allow-dev-urls if this is intended."
            )
        return zf.read("index.html"), len(names)


# --- upload ------------------------------------------------------------------

def check_ticket(fields: dict) -> None:
    """Every x-amz-* condition in the signed policy must equal the form field we send."""
    required = ("key", "policy", "x-amz-algorithm", "x-amz-credential", "x-amz-date", "x-amz-signature")
    missing = [k for k in required if not fields.get(k)]
    if missing:
        raise DeployError(f"apphost.release.create returned no {', '.join(missing)}: platform bug, report it")
    policy = json.loads(base64.b64decode(fields["policy"]))
    lowered = {k.lower(): v for k, v in fields.items()}
    for cond in policy.get("conditions", []):
        if not isinstance(cond, dict):
            continue
        for key, value in cond.items():
            if key.lower() == "bucket":
                continue
            if lowered.get(key.lower()) != value:
                raise DeployError(f"upload ticket is inconsistent: field {key!r} does not match the signed policy")


def upload(url: str, fields: dict, bundle: bytes) -> None:
    boundary = "----orkestia" + secrets.token_hex(12)
    parts = []
    for key, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="bundle.zip"\r\n'
        f"Content-Type: application/zip\r\n\r\n".encode() + bundle + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(url, data=b"".join(parts), method="POST", headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": USER_AGENT,
    })
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            if resp.status not in (200, 201, 204):
                raise DeployError(f"S3 upload returned HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        code = re.search(r"<Code>([^<]+)</Code>", body)
        raise DeployError(f"S3 upload failed: HTTP {exc.code} {code.group(1) if code else body[:300]}") from None


# --- main --------------------------------------------------------------------

def resolve_site(api: Api, site_uuid: str | None, slug: str | None) -> dict:
    if site_uuid:
        data = api.run("apphost.site.get", {"site_uuid": site_uuid})
        if not data.get("found"):
            raise DeployError(f"site {site_uuid} not found in this token's organization")
        return data["site"]
    offset = 0
    while True:
        page = api.run("apphost.site.list", {"limit": 50, "offset": offset})
        for site in page.get("items") or []:
            if site.get("slug") == slug:
                return site
        offset += 50
        if offset >= (page.get("total") or 0):
            raise DeployError(f"no site with slug {slug!r} in this token's organization")


def verify_live(url: str, index_html: bytes, release_uuid: str) -> bool:
    """The public URL serves this release's index.html (retries while the edge catches up)."""
    for _ in range(12):
        req = urllib.request.Request(f"{url.rstrip('/')}/?v={release_uuid}", headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.read() == index_html:
                    return True
        except urllib.error.URLError:
            pass
        time.sleep(5)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    target = ap.add_mutually_exclusive_group()
    target.add_argument("--site-uuid")
    target.add_argument("--slug", help="the <slug> of <slug>.app.orkestia.dev")
    ap.add_argument("source", type=Path, help="build directory (with index.html) or bundle .zip")
    ap.add_argument("--api", default=os.environ.get("ORKESTIA_API_URL", DEFAULT_API))
    ap.add_argument("--check", action="store_true", help="validate the bundle only; touch nothing")
    ap.add_argument("--allow-dev-urls", action="store_true", help="publish even if localhost URLs are in the build")
    args = ap.parse_args()

    try:
        bundle = build_bundle(args.source)
        index_html, count = check_bundle(bundle, args.allow_dev_urls)
        log(f"bundle ok: {count} files, {len(bundle)} bytes, index.html at root, no localhost URLs")
        if args.check:
            return 0
        if not (args.site_uuid or args.slug):
            raise DeployError("pass --slug or --site-uuid")
        token = os.environ.get("ORKESTIA_API_TOKEN", "").strip()
        if not token and TOKEN_FILE.is_file():
            token = TOKEN_FILE.read_text().strip()
        if not token:
            raise DeployError(
                f"no API token: create one in the console (Settings -> API Tokens), then save it to "
                f"{TOKEN_FILE} or export ORKESTIA_API_TOKEN. Never paste it into a chat."
            )
        api = Api(args.api, token)

        site = resolve_site(api, args.site_uuid, args.slug)
        log(f"site: {site['slug']} ({site['site_uuid']}) -> {site['url']}")

        created = api.run("apphost.release.create", {"site_uuid": site["site_uuid"]})
        release_uuid = created["release_uuid"]
        if len(bundle) > int(created.get("max_bundle_bytes") or len(bundle)):
            raise DeployError(f"bundle is {len(bundle)} bytes; the limit is {created['max_bundle_bytes']}")
        fields = created.get("upload_fields") or {}
        check_ticket(fields)
        log(f"release {release_uuid} opened; uploading")

        upload(created["upload_url"], fields, bundle)
        log("upload accepted by S3; publishing")

        published = api.run("apphost.release.publish", {"release_uuid": release_uuid})
        log(f"published {published.get('uploaded_count')} files; /callback registered: "
            f"{published.get('callback_registered')}")

        site_now = api.run("apphost.site.get", {"site_uuid": site["site_uuid"]})["site"]
        if site_now.get("active_release_uuid") != release_uuid:
            raise DeployError(f"publish finished but the active release is {site_now.get('active_release_uuid')}")
        live = verify_live(site_now["url"], index_html, release_uuid)
        log("live: the URL serves this build" if live else
            "warning: the URL does not serve this index.html yet (edge cache); recheck in a minute")
        print(json.dumps({
            "url": site_now["url"],
            "release_uuid": release_uuid,
            "bundle_sha256": published.get("bundle_sha256"),
            "live_verified": live,
            "login_redirect_uri": site_now["url"].rstrip("/") + "/callback",
        }, indent=2))
        return 0
    except DeployError as exc:
        log(f"error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
