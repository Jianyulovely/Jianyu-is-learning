"""Find and optionally remove byte-identical image files with SHA-256.

The default mode is a non-destructive dry run. Pass ``--delete`` to keep the
lexicographically first path in every duplicate group and delete the others.
A CSV report is written for both modes.

Examples (activate ``llm_sft`` first, then run from the repository root):

    python dataprocess/sha256_deduplicate.py \
        dataprocess/data/raw/color/Apple___Apple_scab

    python dataprocess/sha256_deduplicate.py \
        dataprocess/data/raw/color/Apple___Apple_scab --delete
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


IMAGE_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}
CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class DuplicateRecord:
    sha256: str
    kept_path: Path
    duplicate_path: Path
    size_bytes: int


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of *path* without loading it all into RAM."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_images(target: Path) -> Iterable[Path]:
    """Yield supported image files below *target* in deterministic order."""
    paths = (
        path
        for path in target.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    yield from sorted(paths, key=lambda path: path.as_posix().casefold())


def find_duplicates(target: Path) -> tuple[list[DuplicateRecord], int, int]:
    """Find exact duplicates, hashing only files whose byte sizes collide."""
    images = list(iter_images(target))
    by_size: dict[int, list[Path]] = defaultdict(list)
    for path in images:
        by_size[path.stat().st_size].append(path)

    by_digest: dict[str, list[Path]] = defaultdict(list)
    hashed_files = 0
    for same_size_paths in by_size.values():
        if len(same_size_paths) < 2:
            continue
        for path in same_size_paths:
            by_digest[sha256_file(path)].append(path)
            hashed_files += 1

    records: list[DuplicateRecord] = []
    for sha256, same_digest_paths in sorted(by_digest.items()):
        if len(same_digest_paths) < 2:
            continue
        ordered = sorted(
            same_digest_paths, key=lambda path: path.as_posix().casefold()
        )
        kept_path = ordered[0]
        size_bytes = kept_path.stat().st_size
        records.extend(
            DuplicateRecord(
                sha256=sha256,
                kept_path=kept_path,
                duplicate_path=duplicate_path,
                size_bytes=size_bytes,
            )
            for duplicate_path in ordered[1:]
        )

    return records, len(images), hashed_files


def write_report(
    report_path: Path,
    target: Path,
    records: list[DuplicateRecord],
    deleted_paths: set[Path],
    delete_requested: bool,
) -> None:
    """Write one row for every removable duplicate."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "sha256",
                "size_bytes",
                "action",
                "kept_path",
                "duplicate_path",
            ),
        )
        writer.writeheader()
        for record in records:
            if record.duplicate_path in deleted_paths:
                action = "deleted"
            elif delete_requested:
                action = "delete_failed"
            else:
                action = "would_delete"
            writer.writerow(
                {
                    "sha256": record.sha256,
                    "size_bytes": record.size_bytes,
                    "action": action,
                    "kept_path": record.kept_path.relative_to(target).as_posix(),
                    "duplicate_path": record.duplicate_path.relative_to(
                        target
                    ).as_posix(),
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="用 SHA-256 查找并移除内容完全相同的图片。默认仅预览。"
    )
    parser.add_argument("target", type=Path, help="需要递归扫描的图片目录")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="实际删除重复文件；每组保留路径排序后的第一张",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="CSV 报告路径；默认写入 dataprocess/data/reports/",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = args.target.expanduser().resolve()
    if not target.is_dir():
        raise SystemExit(f"目标目录不存在或不是目录: {target}")

    report_path = args.report
    if report_path is None:
        report_path = (
            Path(__file__).resolve().parent
            / "data"
            / "reports"
            / f"sha256_dedup_{target.name}.csv"
        )
    else:
        report_path = report_path.expanduser().resolve()

    records, image_count, hashed_files = find_duplicates(target)
    duplicate_groups = len({record.sha256 for record in records})

    deleted_paths: set[Path] = set()
    failures: list[tuple[Path, OSError]] = []
    if args.delete:
        for record in records:
            try:
                record.duplicate_path.unlink()
                deleted_paths.add(record.duplicate_path)
            except OSError as error:
                failures.append((record.duplicate_path, error))

    write_report(
        report_path=report_path,
        target=target,
        records=records,
        deleted_paths=deleted_paths,
        delete_requested=args.delete,
    )

    mode = "删除" if args.delete else "预览"
    print(f"模式: {mode}")
    print(f"目标: {target}")
    print(f"图片总数: {image_count}")
    print(f"参与 SHA-256 计算: {hashed_files}")
    print(f"重复组数: {duplicate_groups}")
    print(f"可移除文件数: {len(records)}")
    print(f"已删除文件数: {len(deleted_paths)}")
    print(f"报告: {report_path}")

    for path, error in failures:
        print(f"删除失败: {path}: {error}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
