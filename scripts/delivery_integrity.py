#!/usr/bin/env python3
"""Build or verify a content-addressed delivery manifest without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

CHUNK_SIZE = 1024 * 1024
DISCLAIMER = (
    "SHA-256 checks content against this manifest only; it is not a digital signature "
    "and does not prove authorship, origin, accuracy, or authenticity."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_entries(entries: list[dict[str, object]]) -> bytes:
    return json.dumps(
        entries,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def entries_sha256(entries: list[dict[str, object]]) -> str:
    return hashlib.sha256(canonical_entries(entries)).hexdigest()


def safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe manifest path: {value!r}")
    return path


def resolve_delivery_file(root: Path, value: str) -> tuple[Path, str]:
    relative = safe_relative_path(value)
    candidate = root.joinpath(*relative.parts)
    if candidate.is_symlink():
        raise ValueError(f"symlinks are not accepted in delivery manifests: {value!r}")
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(f"delivery path escapes root: {value!r}") from error
    return resolved_candidate, relative.as_posix()


def build_manifest(root: Path, files: list[str]) -> dict[str, object]:
    if not files:
        raise ValueError("at least one delivery file is required")
    if not root.is_dir():
        raise ValueError(f"delivery root is not a directory: {root}")

    normalized: dict[str, Path] = {}
    for value in files:
        candidate, relative = resolve_delivery_file(root, value)
        if relative in normalized:
            raise ValueError(f"duplicate delivery path: {relative!r}")
        if not candidate.is_file():
            raise ValueError(f"delivery file does not exist: {relative!r}")
        normalized[relative] = candidate

    entries = [
        {"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for relative, path in sorted(normalized.items())
    ]
    return {
        "schema_version": 1,
        "hash_algorithm": "sha256",
        "purpose": "content-integrity verification",
        "limitations": DISCLAIMER,
        "file_count": len(entries),
        "files": entries,
        "entries_sha256": entries_sha256(entries),
    }


def verify_manifest(root: Path, manifest_path: Path, strict_extras: bool = False) -> dict[str, object]:
    if not root.is_dir():
        raise ValueError(f"delivery root is not a directory: {root}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[dict[str, object]] = []
    entries = manifest.get("files")
    if manifest.get("schema_version") != 1:
        errors.append({"error": "unsupported_schema_version"})
    if manifest.get("hash_algorithm") != "sha256":
        errors.append({"error": "unsupported_hash_algorithm"})
    if not isinstance(entries, list):
        return {
            "verified": False,
            "strict_extras": strict_extras,
            "counts": {},
            "files": [],
            "extra_files": [],
            "errors": errors + [{"error": "files_must_be_a_list"}],
            "limitations": DISCLAIMER,
        }
    if manifest.get("entries_sha256") != entries_sha256(entries):
        errors.append({"error": "manifest_entries_digest_mismatch"})
    if manifest.get("file_count") != len(entries):
        errors.append({"error": "manifest_file_count_mismatch"})

    seen: set[str] = set()
    expected: set[str] = set()
    results: list[dict[str, object]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append({"entry": index, "error": "file_entry_must_be_an_object"})
            continue
        value = entry.get("path")
        if not isinstance(value, str):
            errors.append({"entry": index, "error": "file_path_must_be_a_string"})
            continue
        try:
            candidate, relative = resolve_delivery_file(root, value)
        except ValueError as error:
            errors.append({"entry": index, "error": "unsafe_file_path", "detail": str(error)})
            continue
        if relative in seen:
            errors.append({"entry": index, "error": "duplicate_file_path", "path": relative})
            continue
        seen.add(relative)
        expected.add(relative)

        if not candidate.is_file():
            results.append({"path": relative, "status": "missing"})
            continue
        actual_bytes = candidate.stat().st_size
        actual_hash = sha256_file(candidate)
        expected_bytes = entry.get("bytes")
        expected_hash = entry.get("sha256")
        issues = []
        if actual_bytes != expected_bytes:
            issues.append("size_mismatch")
        if actual_hash != expected_hash:
            issues.append("hash_mismatch")
        results.append(
            {
                "path": relative,
                "status": "verified" if not issues else "changed",
                "issues": issues,
                "actual_bytes": actual_bytes,
                "actual_sha256": actual_hash,
            }
        )

    manifest_resolved = manifest_path.resolve()
    extras: list[str] = []
    for candidate in root.rglob("*"):
        if candidate.is_symlink():
            extras.append(candidate.relative_to(root).as_posix() + " [symlink]")
            continue
        if not candidate.is_file() or candidate.resolve() == manifest_resolved:
            continue
        relative = candidate.resolve().relative_to(root.resolve()).as_posix()
        if relative not in expected:
            extras.append(relative)
    extras.sort()

    counts: dict[str, int] = {}
    for status in ("verified", "changed", "missing"):
        count = sum(result["status"] == status for result in results)
        if count:
            counts[status] = count
    verified = not errors and not any(result["status"] != "verified" for result in results)
    if strict_extras and extras:
        verified = False
    return {
        "verified": verified,
        "strict_extras": strict_extras,
        "counts": counts,
        "files": results,
        "extra_files": extras,
        "errors": errors,
        "limitations": DISCLAIMER,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Create a deterministic manifest")
    build_parser.add_argument("--root", type=Path, required=True)
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.add_argument("files", nargs="+")

    verify_parser = subparsers.add_parser("verify", help="Verify files against a manifest")
    verify_parser.add_argument("--root", type=Path, required=True)
    verify_parser.add_argument("--manifest", type=Path, required=True)
    verify_parser.add_argument("--strict-extras", action="store_true")

    args = parser.parse_args()
    if args.command == "build":
        input_paths = {resolve_delivery_file(args.root, value)[0] for value in args.files}
        if args.output.resolve() in input_paths:
            parser.error("output must not overwrite a delivery file")
        result = build_manifest(args.root, args.files)
        if args.output.is_symlink():
            parser.error("output must not be a symlink")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    result = verify_manifest(args.root, args.manifest, args.strict_extras)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
