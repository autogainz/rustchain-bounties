#!/usr/bin/env python3
"""Generate shields.io endpoint JSON badges from XP_TRACKER.md (v2).

New features in v2:
- Weekly growth badge
- Top 3 hunters summary badge
- Category badges (docs/outreach/bug)
- Improved per-hunter badge JSON with collision-safe slugs
- README snippets for copying badges

Outputs:
- badges/hunter-stats.json
- badges/top-hunter.json
- badges/active-hunters.json
- badges/legendary-hunters.json
- badges/updated-at.json
- badges/weekly-growth.json (NEW)
- badges/top-3-hunters.json (NEW)
- badges/categories/ (NEW)
- badges/hunters/<hunter>.json (per hunter - IMPROVED slugs)
- badges/README_SNIPPETS.md (NEW)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracker", default="bounties/XP_TRACKER.md")
    parser.add_argument("--out-dir", default="badges")
    parser.add_argument("--previous-xp", type=int, default=0,
                        help="Total XP from previous week for growth calculation")
    return parser.parse_args()


def parse_int(value: str) -> int:
    match = re.search(r"\d+", value or "")
    return int(match.group(0)) if match else 0


def extract_badges_earned(badges_cell: str) -> List[str]:
    """Extract badge names from the markdown cell."""
    badges = []
    # Match alt text in markdown images
    pattern = r'!\[([^\]]+)\]\([^)]+\)'
    matches = re.findall(pattern, badges_cell)
    for match in matches:
        badges.append(match.strip())
    return badges


def categorize_badges(badges: List[str]) -> Dict[str, int]:
    """Categorize badges into docs, outreach, bug based on badge names."""
    categories = {
        "docs": 0,
        "outreach": 0,
        "bug": 0,
        "other": 0
    }
    
    badge_categories = {
        "docs": ["tutorial", "guide", "documentation", "writer"],
        "outreach": ["star", "fork", "share", "follow", "social", "community"],
        "bug": ["bug", "slayer", "fix", "issue"]
    }
    
    for badge in badges:
        badge_lower = badge.lower()
        categorized = False
        for category, keywords in badge_categories.items():
            if any(keyword in badge_lower for keyword in keywords):
                categories[category] += 1
                categorized = True
                break
        if not categorized:
            categories["other"] += 1
    
    return categories


def parse_rows(md_text: str) -> List[Dict[str, object]]:
    lines = md_text.splitlines()
    header_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("| Rank | Hunter"):
            header_idx = i
            break

    if header_idx < 0:
        return []

    rows: List[Dict[str, object]] = []
    i = header_idx + 2
    while i < len(lines) and lines[i].strip().startswith("|"):
        line = lines[i].strip()
        if line.startswith("|---"):
            i += 1
            continue

        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) < 9:
            i += 1
            continue

        hunter = cells[1]
        if hunter == "_TBD_":
            i += 1
            continue

        # Extract badges and categorize them
        badges_earned = extract_badges_earned(cells[6])
        category_counts = categorize_badges(badges_earned)

        row = {
            "rank": parse_int(cells[0]),
            "hunter": hunter,
            "wallet": cells[2],
            "xp": parse_int(cells[3]),
            "level": parse_int(cells[4]),
            "title": cells[5],
            "badges_earned": badges_earned,
            "category_counts": category_counts,
            "last_action": cells[7],
            "notes": cells[8] if len(cells) > 8 else "",
        }
        rows.append(row)
        i += 1

    rows.sort(key=lambda item: (-int(item["xp"]), str(item["hunter"]).lower()))
    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx
    return rows


def color_for_level(level: int) -> str:
    if level >= 10:
        return "gold"
    if level >= 7:
        return "purple"
    if level >= 5:
        return "yellow"
    if level >= 4:
        return "orange"
    return "blue"


def slugify_hunter(hunter: str) -> str:
    """Create collision-safe slug from hunter name.
    
    Rules:
    - Remove @ prefix
    - Lowercase
    - Replace non-alphanumeric with single hyphen
    - Collapse multiple hyphens
    - Strip leading/trailing hyphens
    - Max 50 chars
    """
    value = hunter.lstrip("@").strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value)  # Collapse multiple hyphens
    value = value.strip("-")
    return value[:50] or "unknown"


def write_badge(path: Path, label: str, message: str, color: str,
                named_logo: str = "github", logo_color: str = "white") -> None:
    payload = {
        "schemaVersion": 1,
        "label": label,
        "message": message,
        "color": color,
        "namedLogo": named_logo,
        "logoColor": logo_color,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def generate_readme_snippets(out_dir: Path, hunter_slugs: Dict[str, str]) -> str:
    """Generate README snippets for copying badges."""
    snippets = """# Badge Snippets for README

Copy and paste these snippets into your README files.

## Global Stats Badges

```markdown
![Hunter Stats](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Scottcjn/rustchain-bounties/main/badges/hunter-stats.json)
![Top Hunter](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Scottcjn/rustchain-bounties/main/badges/top-hunter.json)
![Active Hunters](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Scottcjn/rustchain-bounties/main/badges/active-hunters.json)
![Legendary Hunters](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Scottcjn/rustchain-bounties/main/badges/legendary-hunters.json)
![Weekly Growth](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Scottcjn/rustchain-bounties/main/badges/weekly-growth.json)
![Updated](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Scottcjn/rustchain-bounties/main/badges/updated-at.json)
```

## Category Badges

```markdown
![Docs Bounties](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Scottcjn/rustchain-bounties/main/badges/categories/docs.json)
![Outreach Bounties](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Scottcjn/rustchain-bounties/main/badges/categories/outreach.json)
![Bug Bounties](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Scottcjn/rustchain-bounties/main/badges/categories/bug.json)
```

## Top 3 Hunters Badge

```markdown
![Top 3 Hunters](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Scottcjn/rustchain-bounties/main/badges/top-3-hunters.json)
```

## Per-Hunter Badges
"""
    
    for hunter, slug in sorted(hunter_slugs.items()):
        clean_name = hunter.lstrip("@")
        snippets += f"""
### {clean_name}

```markdown
![{clean_name} XP](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Scottcjn/rustchain-bounties/main/badges/hunters/{slug}.json)
```
"""
    
    return snippets


def main() -> None:
    args = parse_args()
    tracker_path = Path(args.tracker)
    out_dir = Path(args.out_dir)

    if not tracker_path.exists():
        raise SystemExit(f"tracker not found: {tracker_path}")

    md_text = tracker_path.read_text(encoding="utf-8")
    rows = parse_rows(md_text)

    total_xp = sum(int(row["xp"]) for row in rows)
    active_hunters = len(rows)
    legendary = sum(1 for row in rows if int(row["level"]) >= 10)
    
    # Calculate weekly growth
    weekly_growth = total_xp - args.previous_xp if args.previous_xp > 0 else 0
    growth_percent = round((weekly_growth / args.previous_xp) * 100, 1) if args.previous_xp > 0 else 0
    
    # Aggregate category counts across all hunters
    total_categories = {"docs": 0, "outreach": 0, "bug": 0, "other": 0}
    for row in rows:
        cats = row.get("category_counts", {})
        for key in total_categories:
            total_categories[key] += cats.get(key, 0)

    if rows:
        top = rows[0]
        top_name = str(top["hunter"]).lstrip("@")
        top_msg = f"{top_name} ({top['xp']} XP)"
    else:
        top_msg = "none yet"

    # Write standard badges
    write_badge(
        out_dir / "hunter-stats.json",
        label="Bounty Hunter XP",
        message=f"{total_xp} total",
        color="orange" if total_xp > 0 else "blue",
    )

    write_badge(
        out_dir / "top-hunter.json",
        label="Top Hunter",
        message=top_msg,
        color="gold" if rows else "lightgrey",
    )

    write_badge(
        out_dir / "active-hunters.json",
        label="Active Hunters",
        message=str(active_hunters),
        color="success",
    )

    write_badge(
        out_dir / "legendary-hunters.json",
        label="Legendary Hunters",
        message=str(legendary),
        color="gold" if legendary > 0 else "lightgrey",
    )

    # Write weekly growth badge (NEW)
    if weekly_growth > 0:
        growth_color = "brightgreen" if growth_percent > 50 else "green" if growth_percent > 10 else "yellow"
        growth_message = f"+{weekly_growth} XP ({growth_percent}%)"
    else:
        growth_color = "lightgrey"
        growth_message = "no change" if args.previous_xp > 0 else "baseline"
    
    write_badge(
        out_dir / "weekly-growth.json",
        label="Weekly Growth",
        message=growth_message,
        color=growth_color,
    )

    # Write top 3 hunters summary badge (NEW)
    top_3_names = []
    for row in rows[:3]:
        name = str(row["hunter"]).lstrip("@")
        xp = row["xp"]
        top_3_names.append(f"{name} ({xp})")
    
    top_3_message = " | ".join(top_3_names) if top_3_names else "No hunters yet"
    write_badge(
        out_dir / "top-3-hunters.json",
        label="Top 3 Hunters",
        message=top_3_message[:100],  # Keep it reasonably short
        color="gold",
    )

    # Write category badges (NEW)
    categories = [
        ("docs", "Documentation", "blue", total_categories["docs"]),
        ("outreach", "Outreach", "green", total_categories["outreach"]),
        ("bug", "Bug Reports", "red", total_categories["bug"]),
        ("other", "Other", "lightgrey", total_categories["other"]),
    ]
    
    for cat_id, cat_label, cat_color, cat_count in categories:
        cat_message = f"{cat_count} badges" if cat_count > 0 else "0 badges"
        write_badge(
            out_dir / "categories" / f"{cat_id}.json",
            label=cat_label,
            message=cat_message,
            color=cat_color,
        )

    # Write updated-at badge
    now = dt.datetime.now(dt.timezone.utc)
    write_badge(
        out_dir / "updated-at.json",
        label="Badges Updated",
        message=now.strftime("%Y-%m-%d %H:%M UTC"),
        color="informational",
    )

    # Write per-hunter badges (IMPROVED with collision-safe slugs)
    hunter_slugs: Dict[str, str] = {}
    seen_slugs: Dict[str, int] = {}
    
    for row in rows:
        hunter_name = str(row["hunter"])
        base_slug = slugify_hunter(hunter_name)
        
        # Handle collisions
        if base_slug in seen_slugs:
            seen_slugs[base_slug] += 1
            slug = f"{base_slug}-{seen_slugs[base_slug]}"
        else:
            seen_slugs[base_slug] = 0
            slug = base_slug
        
        hunter_slugs[hunter_name] = slug
        
        hunter_path = out_dir / "hunters" / f"{slug}.json"
        write_badge(
            hunter_path,
            label=hunter_name.lstrip("@"),
            message=f"{row['xp']} XP (Lv{row['level']})",
            color=color_for_level(int(row["level"])),
        )

    # Write README snippets file (NEW)
    snippets = generate_readme_snippets(out_dir, hunter_slugs)
    snippets_path = out_dir / "README_SNIPPETS.md"
    snippets_path.write_text(snippets, encoding="utf-8")

    # Summary output
    print(f"Generated badges for {len(rows)} hunters")
    print(f"Total XP: {total_xp}")
    print(f"Weekly Growth: {weekly_growth} XP ({growth_percent}%)")
    print(f"Categories: docs={total_categories['docs']}, outreach={total_categories['outreach']}, bug={total_categories['bug']}")
    print(f"Output directory: {out_dir}")
    print(f"\nHunter slugs (collision-safe):")
    for hunter, slug in sorted(hunter_slugs.items()):
        print(f"  {hunter} -> {slug}")


if __name__ == "__main__":
    main()
