"""Read-only inspection helpers for the independent DNSTunnel2026 archive."""

from __future__ import annotations

import hashlib
import json
import shutil
import stat
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from training.colab import require_owned_workspace, sha256_file

ZENODO_RECORD_ID = "20137065"
ZENODO_DOI = "10.5281/zenodo.20137065"
ZENODO_ARCHIVE_URL = (
    "https://zenodo.org/records/20137065/files/DNSTunnel2026.zip?download=1"
)
ZENODO_ARCHIVE_NAME = "DNSTunnel2026.zip"
ZENODO_REPORTED_MD5 = "e2a4c675b480f9c10b8629494d9ae7dc"
MAX_DOWNLOAD_BYTES = 600 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 8 * 1024 * 1024 * 1024
MAX_MEMBERS = 100
RAW_REQUIRED_COLUMNS = {
    "Domain",
    "FQDN",
    "DNS Type Name",
    "Date",
    "Is Tunnel Data",
    "Company_uid",
}


def _md5_file(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member_name(name: str) -> PurePosixPath:
    member = PurePosixPath(name.replace("\\", "/"))
    if member.is_absolute() or ".." in member.parts or not member.parts:
        raise ValueError(f"unsafe archive member path: {name!r}")
    return member


def inspect_zip(path: Path) -> list[dict[str, object]]:
    """Validate archive structure without extracting or executing any member."""

    if not path.is_file() or not zipfile.is_zipfile(path):
        raise ValueError(f"not a valid ZIP archive: {path}")
    records = []
    total_size = 0
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > MAX_MEMBERS:
            raise ValueError(f"archive has too many members: {len(members)}")
        for member in members:
            safe_name = _safe_member_name(member.filename)
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"archive symlink is forbidden: {member.filename}")
            if member.flag_bits & 0x1:
                raise ValueError(f"encrypted archive member is forbidden: {member.filename}")
            total_size += member.file_size
            if total_size > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("archive exceeds the declared uncompressed-size limit")
            if member.compress_size and member.file_size / member.compress_size > 250:
                raise ValueError(f"suspicious compression ratio: {member.filename}")
            records.append(
                {
                    "name": safe_name.as_posix(),
                    "size_bytes": member.file_size,
                    "compressed_bytes": member.compress_size,
                    "is_directory": member.is_dir(),
                }
            )
    return records


def download_for_inspection(workspace: Path) -> tuple[Path, dict[str, object]]:
    """Download the published archive into the dedicated hosted-Colab workspace."""

    workspace = require_owned_workspace(workspace)
    destination = workspace / "data" / "independent" / ZENODO_ARCHIVE_NAME
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        request = urllib.request.Request(
            ZENODO_ARCHIVE_URL,
            headers={"User-Agent": "Custodian-Dataset-Inspection/1.0"},
        )
        with urllib.request.urlopen(request, timeout=60) as response, destination.open(
            "xb"
        ) as output:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
                raise ValueError("published archive exceeds the download-size limit")
            copied = 0
            while chunk := response.read(1024 * 1024):
                copied += len(chunk)
                if copied > MAX_DOWNLOAD_BYTES:
                    raise ValueError("download exceeded the configured size limit")
                output.write(chunk)
    size = destination.stat().st_size
    if size <= 0 or size > MAX_DOWNLOAD_BYTES:
        raise ValueError("downloaded archive has an invalid size")
    md5 = _md5_file(destination)
    if md5 != ZENODO_REPORTED_MD5:
        raise ValueError("Zenodo MD5 does not match the published record")
    members = inspect_zip(destination)
    report = {
        "record_id": ZENODO_RECORD_ID,
        "doi": ZENODO_DOI,
        "download_url": ZENODO_ARCHIVE_URL,
        "archive_name": ZENODO_ARCHIVE_NAME,
        "size_bytes": size,
        "published_md5": ZENODO_REPORTED_MD5,
        "verified_md5": md5,
        "sha256": sha256_file(destination),
        "members": members,
        "extracted": False,
        "executed": False,
    }
    report_path = destination.parent / "DNSTunnel2026-inspection.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return destination, report


def copy_nested_zip_for_inspection(outer_path: Path, member_name: str, destination: Path) -> Path:
    """Copy one validated nested ZIP; never extract arbitrary archive contents."""

    _safe_member_name(member_name)
    records = {record["name"]: record for record in inspect_zip(outer_path)}
    record = records.get(member_name)
    if not record or record["is_directory"] or not member_name.casefold().endswith(".zip"):
        raise ValueError("requested nested member is not a reviewed ZIP file")
    if int(record["size_bytes"]) > MAX_DOWNLOAD_BYTES:
        raise ValueError("nested ZIP exceeds the configured size limit")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(outer_path) as archive, archive.open(member_name) as source:
        with destination.open("xb") as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
    inspect_zip(destination)
    return destination
