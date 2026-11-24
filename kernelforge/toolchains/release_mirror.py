"""Reviewed GitHub Release asset adapter for the existing ToolchainManager.

No new installer, cache, downloader or extraction path. All provenance fields
are reviewed input data; no Release tag, URL or GitHub-produced digest alone
is an authorization to use bytes. The existing manager hashes *all* downloaded
archives against the independently configured expected SHA256 before extract.
"""
from __future__ import annotations

import json
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request
from ..http_safety import open_metadata, require_https_host, MetadataURLerror


def urlopen(request, timeout):
    return open_metadata(request, host='api.github.com', timeout=timeout)

from .download import DownloadError


class ReleaseMirrorError(ValueError):
    """Untrusted or mismatched provenance. Never fall back from this error."""


class MirrorUnavailable(ReleaseMirrorError):
    """Transient GitHub metadata/transport outage; pinned fallback may be used."""


_REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")
_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
_ASSET = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,254}$")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_LICENSE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]{1,79}$")
_RELEASE_FIELDS = frozenset({
    "repository", "release_id", "asset_id", "tag", "asset_name", "asset_size",
    "uploader_id", "sha256", "license", "license_reviewed",
})
_FALLBACK_FIELDS = frozenset({"url", "sha256", "source_commit", "repository"})


def _require(value: bool, message: str) -> None:
    if not value:
        raise ReleaseMirrorError(message)


def _number(value: object) -> bool:
    return type(value) is int and value > 0


def _safe_https(url: object) -> bool:
    if not isinstance(url, str):
        return False
    try:
        p = urlsplit(url)
        return (p.scheme == "https" and bool(p.hostname) and p.port in (None, 443)
                and not p.username and not p.password and not p.query and not p.fragment
                and not any(c in url for c in ("\r", "\n", "\t", "\\")))
    except ValueError:
        return False


def verify_release_spec(spec: dict) -> dict:
    """Pure offline gate, including exact upstream-fallback identity."""
    _require(type(spec) is dict, "reviewed Release spec must be an object")
    kind = spec.get("kind")
    source_type = spec.get("source_type")
    _require(kind in ("llvm", "gcc"), "reviewed Release supports LLVM/GCC only")
    _require(source_type in ("llvm-release", "gcc-release", "reviewed-github-release"),
             "not a reviewed GitHub Release source type")
    if source_type != "reviewed-github-release":
        _require(source_type == f"{kind}-release", "Release alias/toolchain family mismatch")
    lock = spec.get("release_lock")
    _require(type(lock) is dict and set(lock).issuperset(_RELEASE_FIELDS)
             and not set(lock).difference(_RELEASE_FIELDS | {"fallback", "require_immutable"}),
             "incomplete or unexpected reviewed Release lock fields")
    repo, tag, name = lock["repository"], lock["tag"], lock["asset_name"]
    _require(isinstance(repo, str) and bool(_REPO.fullmatch(repo)), "invalid GitHub Release repository")
    _require(isinstance(tag, str) and bool(_TAG.fullmatch(tag)) and ".." not in tag,
             "invalid or ambiguous GitHub Release tag")
    _require(isinstance(name, str) and bool(_ASSET.fullmatch(name)) and ".." not in name,
             "invalid GitHub Release asset name")
    for field in ("release_id", "asset_id", "asset_size", "uploader_id"):
        _require(_number(lock[field]), f"release lock {field} must be positive integer")
    _require(isinstance(lock["sha256"], str) and _HEX.fullmatch(lock["sha256"]) is not None
             and isinstance(spec.get("sha256"), str)
             and lock["sha256"] == spec["sha256"].lower(),
             "reviewed Release digest must match independently pinned archive SHA256")
    _require(isinstance(lock["license"], str) and _LICENSE.fullmatch(lock["license"]) is not None
             and lock["license_reviewed"] is True,
             "explicit license identifier and positive human review are required")
    if "require_immutable" in lock:
        _require(type(lock["require_immutable"]) is bool,
                 "release immutability gate must be boolean")
    if "expected_size" in spec:
        _require(spec["expected_size"] == lock["asset_size"],
                 "expected archive size differs from reviewed Release asset size")
    expected = f"https://github.com/{repo}/releases/download/{tag}/{name}"
    _require(spec.get("url") == expected, "reviewed Release URL does not match asset identity")
    _require(spec.get("archive_format") in {"zip", "tar", "tar.gz", "tgz", "tar.xz", "tar.bz2"},
             "unsupported reviewed Release archive format")
    if "fallback" in lock:
        fb = lock["fallback"]
        _require(type(fb) is dict and set(fb) == _FALLBACK_FIELDS,
                 "pinned fallback identity incomplete or contains extra fields")
        _require(_safe_https(fb["url"]) and fb["url"] != expected,
                 "fallback source must be an independent credential-free HTTPS URL")
        _require(fb["sha256"] == lock["sha256"],
                 "fallback must have the exact same SHA256 as the reviewed Release bytes")
        _require(type(fb["source_commit"]) is str and _COMMIT.fullmatch(fb["source_commit"]) is not None,
                 "fallback requires fixed upstream source Commit")
        _require(_safe_https(fb["repository"]) and not fb["repository"].endswith("/"),
                 "fallback upstream repository must be an HTTPS identity")
    return lock


def github_api_json(url: str) -> dict:
    """Only controlled GitHub API endpoints are passed by this adapter."""
    try:
        require_https_host(url, "api.github.com")
    except MetadataURLerror as exc:
        raise ReleaseMirrorError("unexpected GitHub metadata API origin") from exc
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "KernelForge-reviewed-release-adapter/1",
    })
    try:
        with urlopen(request, timeout=12) as r:
            final = urlsplit(r.geturl())
            _require(final.scheme == "https" and final.hostname == "api.github.com"
                     and final.port in (None, 443) and not final.username and not final.password,
                     "GitHub metadata request redirected outside authenticated HTTPS API")
            raw = r.read(2 * 1024 * 1024 + 1)
    except MetadataURLerror as exc:
        raise ReleaseMirrorError("GitHub metadata request outside authenticated HTTPS API") from exc
    except HTTPError as exc:
        if exc.code == 429 or 500 <= exc.code <= 599:
            raise MirrorUnavailable("GitHub Release metadata temporarily unavailable") from exc
        raise ReleaseMirrorError("GitHub Release identity cannot be verified via API") from exc
    except (URLError, TimeoutError, socket.timeout, OSError) as exc:
        raise MirrorUnavailable("GitHub Release metadata network unavailable") from exc
    _require(len(raw) <= 2 * 1024 * 1024, "oversized GitHub Release metadata rejected")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ReleaseMirrorError("GitHub Release API returned invalid metadata") from exc
    _require(type(value) is dict, "GitHub Release metadata is not an object")
    return value


class ReviewedGithubReleaseAdapter:
    """Read-only reviewed GitHub metadata, isolated downloaded archive.

    Fallback only on transient metadata or transport failures, never when
    metadata identities or *downloaded bytes* are inconsistent with the lock.
    The manager's archive SHA256 check happens after download(), for either
    mirror or fallback, before any extraction or cache installation.
    """
    requires_archive_format = True
    version = "reviewed-github-release-v1"

    def __init__(self, metadata_fetch=github_api_json):
        self.metadata_fetch = metadata_fetch

    def validate(self, spec: dict) -> None:
        verify_release_spec(spec)

    def resolve(self, spec: dict) -> tuple[str, str, str]:
        verify_release_spec(spec)
        return spec["url"], spec["archive_format"], spec.get("layout_root", "")

    def _validate_online(self, spec: dict, lock: dict) -> dict:
        repo = lock["repository"]
        rel = self.metadata_fetch(f"https://api.github.com/repos/{repo}/releases/{lock['release_id']}")
        asset = self.metadata_fetch(f"https://api.github.com/repos/{repo}/releases/assets/{lock['asset_id']}")
        _require(type(rel) is dict and type(asset) is dict, "invalid Release/Asset API object")
        _require(rel.get("id") == lock["release_id"]
                 and rel.get("tag_name") == lock["tag"]
                 and rel.get("draft") is False,
                 "GitHub release ID/tag/draft changed")
        if lock.get("require_immutable", False):
            _require(rel.get("immutable") is True, "locked GitHub Release is not immutable")
        assets = rel.get("assets")
        _require(isinstance(assets, list)
                 and sum(type(a) is dict and a.get("id") == lock["asset_id"] for a in assets) == 1,
                 "reviewed Asset ID not found exactly once in Release")
        _require(asset.get("id") == lock["asset_id"]
                 and asset.get("name") == lock["asset_name"]
                 and asset.get("size") == lock["asset_size"]
                 and asset.get("state") == "uploaded",
                 "reviewed GitHub Asset identity/size changed")
        _require(asset.get("digest") == "sha256:" + lock["sha256"],
                 "GitHub Asset published digest differs from reviewed SHA256")
        uploader = asset.get("uploader")
        _require(type(uploader) is dict and uploader.get("id") == lock["uploader_id"],
                 "reviewed GitHub Asset uploader identity changed")
        _require(asset.get("browser_download_url") == spec["url"],
                 "GitHub asset download URL differs from reviewed Release lock")
        _require(asset.get("url") ==
                 f"https://api.github.com/repos/{repo}/releases/assets/{lock['asset_id']}",
                 "GitHub Asset API repository identity changed")
        return {"repository": repo, "release_id": lock["release_id"],
                "asset_id": lock["asset_id"], "asset_size": lock["asset_size"],
                "uploader_id": lock["uploader_id"], "digest": lock["sha256"],
                "release_immutable": rel.get("immutable") is True}

    def download(self, manager, spec: dict, destination) -> dict:
        lock = verify_release_spec(spec)
        fallback = lock.get("fallback")
        failure = None
        provenance = None
        try:
            provenance = self._validate_online(spec, lock)
            info = manager.downloader(spec["url"], destination,
                                      timeout=spec.get("download_timeout_seconds", 60),
                                      retries=spec.get("retries", 2),
                                      expected_size=lock["asset_size"])
            return {**info, "source_url": spec["url"],
                    "source_route": "reviewed-github-release",
                    "mirror_provenance": provenance,
                    "mirror_fallback": False}
        except MirrorUnavailable:
            failure = "metadata_unavailable"
        except DownloadError:
            failure = "mirror_download_unavailable"
        if fallback is None:
            raise MirrorUnavailable("mirror unavailable and no pinned upstream fallback")
        # Independent pinned fallback. Any archive SHA mismatch remains fatal
        # in the manager and is never retried as an unreviewed alternative.
        info = manager.downloader(fallback["url"], destination,
                                  timeout=spec.get("download_timeout_seconds", 60),
                                  retries=spec.get("retries", 2),
                                  expected_size=lock["asset_size"])
        return {**info, "source_url": fallback["url"],
                "source_route": "pinned-upstream-fallback",
                "mirror_provenance": provenance,
                "fallback_source_commit": fallback["source_commit"],
                "mirror_failure_class": failure,
                "mirror_fallback": True}

    def extract(self, manager, spec: dict, archive, destination) -> None:
        manager.extractor(archive, destination, spec["archive_format"])
