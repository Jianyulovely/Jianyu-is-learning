"""PlantVillage(color) 划分脚本。

按"叶片"分组做分层划分,避免同一片叶子的多张照片跨 train/val/test 泄漏。

用法(在仓库根目录):
    python plantvillage_split.py                      # 80/10/10, 按叶片分组
    python plantvillage_split.py --val-ratio 0        # 只要 train/test 80/20
    python plantvillage_split.py --group image        # 退化为按图片随机划分(不推荐)

输出到 data/splits/:
    train.txt / val.txt / test.txt   每行一个相对路径
    metadata.csv                     image_path,class,crop,disease,leaf_id,split
    stats.json                       各类别 × split 的统计
"""

import argparse
import csv
import json
import os
import random
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
COLOR_DIR = os.path.join(ROOT, "data", "raw", "color")
LEAF_MAP = os.path.join(ROOT, "leaf-map.json")
OUT_DIR = os.path.join(ROOT, "data", "splits")

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def leaf_key(filename: str) -> str:
    """和 plant_village.py 里一致: 从文件名推出 leaf-map 的查找键。"""
    ident = filename.replace("_final_masked", "")
    if "___" in ident:
        ident = ident.split("___")[-1]
    ident = ident.split("copy")[0]
    ident = os.path.splitext(ident)[0]
    return ident.strip().lower()


def build_groups(use_leaf_map: bool):
    """返回 {class: [(group_id, [relative_path, ...]), ...]} 以及覆盖率信息。"""
    leaf_map = {}
    if use_leaf_map and os.path.exists(LEAF_MAP):
        with open(LEAF_MAP, encoding="utf-8") as f:
            leaf_map = json.load(f)

    groups = defaultdict(list)
    hit = miss = ambiguous = 0
    hit_images = miss_images = 0

    for cls in sorted(os.listdir(COLOR_DIR)):
        cdir = os.path.join(COLOR_DIR, cls)
        if not os.path.isdir(cdir):
            continue
        buckets = defaultdict(list)
        for fn in sorted(os.listdir(cdir)):
            if os.path.splitext(fn)[1].lower() not in EXTS:
                continue
            rel = "/".join(["data", "raw", "color", cls, fn])
            gid = None
            if use_leaf_map:
                suggestions = leaf_map.get(leaf_key(fn))
                if suggestions:
                    hit += 1
                    hit_images += 1
                    if len(suggestions) > 1:
                        ambiguous += 1
                        gid = next((s for s in suggestions if cls in s), None)
                    else:
                        gid = suggestions[0]
                if gid is None:
                    miss += 1
                    miss_images += 1
                    gid = f"fallback::{cls}/{fn}"   # 没映射到叶片 => 自己一组(仍然安全)
            else:
                gid = f"image::{rel}"
            buckets[gid].append(rel)
        groups[cls] = sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    cov = {
        "leaf_map_entries": len(leaf_map),
        "lookup_hit": hit,
        "lookup_miss": miss,
        "ambiguous_keys": ambiguous,
        "hit_rate": round(hit / max(hit + miss, 1), 4),
    }
    return groups, cov


def split_class(groups, ratios, rng):
    """类内贪心: 打乱组顺序,每组放进"相对缺口"最大的 split。

    用相对缺口而不是绝对缺口,可以避免大组先把 train 填满、
    小组尾部长尾全部落进 val/test 导致各 split 的组大小分布不一致。
    """
    names = [k for k, v in ratios.items() if v > 0]
    total = sum(len(p) for _, p in groups)
    target = {k: ratios[k] * total for k in names}
    filled = {k: 0 for k in names}
    out = {k: [] for k in names}

    ordered = list(groups)
    rng.shuffle(ordered)

    for gid, paths in ordered:
        k = max(names, key=lambda s: (target[s] - filled[s]) / target[s])
        out[k].extend(paths)
        filled[k] += len(paths)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--val-ratio", type=float, default=0.1)
    ap.add_argument("--test-ratio", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--group", choices=["leaf", "image"], default="leaf")
    ap.add_argument("--out", default=OUT_DIR)
    args = ap.parse_args()

    if args.val_ratio + args.test_ratio >= 1:
        raise SystemExit("val + test 之和必须 < 1")
    ratios = {
        "train": 1 - args.val_ratio - args.test_ratio,
        "val": args.val_ratio,
        "test": args.test_ratio,
    }

    groups, cov = build_groups(use_leaf_map=(args.group == "leaf"))
    if not groups:
        raise SystemExit(f"没找到图片: {COLOR_DIR}")

    rng = random.Random(args.seed)
    per_split_paths = defaultdict(list)
    rows = []
    for cls, cls_groups in groups.items():
        crop, _, disease = cls.partition("___")
        disease = disease or "unknown"
        path2gid = {p: gid for gid, paths in cls_groups for p in paths}
        cls_split = split_class(cls_groups, ratios, rng)
        for split, paths in cls_split.items():
            per_split_paths[split].extend(paths)
            for p in paths:
                gid = path2gid[p]
                rows.append({
                    "image_path": p,
                    "class": cls,
                    "crop": crop,
                    "disease": disease,
                    "leaf_id": gid,
                    "split": split,
                })

    os.makedirs(args.out, exist_ok=True)
    for split, paths in per_split_paths.items():
        with open(os.path.join(args.out, f"{split}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(paths)) + "\n")

    rows.sort(key=lambda r: (r["class"], r["image_path"]))
    with open(os.path.join(args.out, "metadata.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["image_path", "class", "crop", "disease", "leaf_id", "split"])
        w.writeheader()
        w.writerows(rows)

    # ---- 自检: 数量 / 类别覆盖 / 叶片是否跨 split ----
    split_of_leaf = defaultdict(set)
    for r in rows:
        split_of_leaf[r["leaf_id"]].add(r["split"])
    leak = sum(1 for s in split_of_leaf.values() if len(s) > 1)

    stats = {
        "config": vars(args),
        "leaf_map_coverage": cov,
        "totals": {s: len(p) for s, p in per_split_paths.items()},
        "leaf_counts": {s: len({r["leaf_id"] for r in rows if r["split"] == s}) for s in per_split_paths},
        "images_total": len(rows),
        "classes": len(groups),
        "leaking_leaves": leak,
    }
    with open(os.path.join(args.out, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # ---- 打印 ----
    print(f"图片总数 {len(rows)} | 类别 {len(groups)} | 叶片组 {len(split_of_leaf)}")
    print(f"leaf-map 覆盖率 {cov['hit_rate']:.1%} (命中 {cov['lookup_hit']} / 未命中 {cov['lookup_miss']})")
    print(f"跨 split 的叶片: {leak}  <-- 必须是 0")
    print("\nsplit      images    leaves")
    for s in ("train", "val", "test"):
        if s in per_split_paths:
            print(f"{s:<8} {len(per_split_paths[s]):>7} {stats['leaf_counts'][s]:>8}")
    print("\n各类别分布(前 3 类):")
    by_cls = defaultdict(Counter)
    for r in rows:
        by_cls[r["class"]][r["split"]] += 1
    for cls in list(by_cls)[:3]:
        print(f"  {cls:<42} " + "  ".join(f"{s}={by_cls[cls][s]}" for s in ("train", "val", "test")))
    print(f"\n输出目录: {args.out}")


if __name__ == "__main__":
    main()
