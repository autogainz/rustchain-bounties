#!/usr/bin/env python3
"""Dynamic Shields Badges v2 - Generate shields.io endpoint JSON badges from XP_TRACKER.md.

Enhanced version with:
- Weekly growth badge
- Top 3 hunters summary badges
- Category badges (docs/outreach/bug)
- Collision-safe per-hunter slugs
- README snippets for badge usage

Usage:
    python .github/scripts/generate_dynamic_badges.py --tracker XP_TRACKER.md --out-dir badges
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate dynamic shields.io badges from XP tracker"
    )
    parser.add_argument(
        "--tracker", 
        default="bounties/XP_TRACKER.md",
        help="Path to XP_TRACKER.md file"
    )
    parser.add_argument(
        "--out-dir", 
        default="badges",
        help="Output directory for badge JSON files"
    )
    parser.add_argument(
        "--generate-readme",
        action="store_true",
        help="Generate README snippet with badge URLs"
    )
    return parser.parse_args()


def parse_int(value: str) -> int:
    """Extract integer from string."""
    match = re.search(r"\d+", value or "")
    return int(match.group(0)) if match else 0


def slugify_hunter(hunter: str) -> str:
    """Create collision-safe slug from hunter name."""
    value = hunter.lstrip("@").strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    value = value.strip("-.")
    return value or "unknown"


def parse_xp_tracker(md_text: str) -> List[Dict[str, object]]:
    """Parse hunter data from XP_TRACKER.md table."""
    lines = md_text.splitlines()
    header_idx = -1
    
    for i, line in enumerate(lines):
        if "| Hunter" in line or "| Rank | Hunter" in line:
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
        if len(cells) < 4:
            i += 1
            continue

        hunter = cells[1] if "Rank" in lines[header_idx] else cells[0]
        if hunter == "_TBD_" or not hunter or hunter.startswith("--"):
            i += 1
            continue

        xp_idx = 3 if "Rank" in lines[header_idx] else 2
        level_idx = 4 if "Rank" in lines[header_idx] else 3
        
        row = {
            "rank": parse_int(cells[0]) if "Rank" in lines[header_idx] else 0,
            "hunter": hunter,
            "wallet": cells[2] if len(cells) > 2 else "",
            "xp": parse_int(cells[xp_idx]) if len(cells) > xp_idx else 0,
            "level": parse_int(cells[level_idx]) if len(cells) > level_idx else 1,
            "title": cells[5] if len(cells) > 5 else "Hunter",
            "slug": slugify_hunter(hunter),
        }
        rows.append(row)
        i += 1

    rows.sort(key=lambda item: (-int(item["xp"]), str(item["hunter"]).lower()))
    
    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx
    
    return rows


def parse_ledger_for_weekly_data(md_text: str) -> Dict[str, int]:
    """Extract weekly bounty completions from ledger format."""
    weekly_counts = defaultdict(int)
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    
    for line in md_text.splitlines():
        match = date_pattern.search(line)
        if match:
            date_str = match.group(1)
            date = dt.datetime.strptime(date_str, "%Y-%m-%d")
            week_key = date.strftime("%Y-W%W")
            weekly_counts[week_key] += 1
    
    return dict(weekly_counts)


def write_badge(
    path: Path,
    label: str,
    message: str,
    color: str = "blue",
    style: str = "flat",
    is_error: bool = False,
    named_logo: Optional[str] = None,
    cache_seconds: int = 3600,
) -> None:
    """Write a shields.io endpoint badge JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    badge = {
        "schemaVersion": 1,
        "label": label,
        "message": message,
        "color": color,
        "style": style,
        "isError": is_error,
        "cacheSeconds": cache_seconds,
    }
    
    if named_logo:
        badge["namedLogo"] = named_logo
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(badge, f, indent=2)


def get_level_color(level: int) -> str:
    """Get color based on hunter level."""
    colors = {
        1: "lightgrey",
        2: "green",
        3: "yellowgreen",
        4: "yellow",
        5: "orange",
        6: "red",
        7: "brightgreen",
        8: "blue",
        9: "purple",
        10: "gold",
    }
    return colors.get(min(level, 10), "blue")


def generate_hunter_badges(rows: List[Dict], out_dir: Path) -> None:
    """Generate per-hunter XP badges."""
    for row in rows:
        slug = str(row["slug"])
        badge_path = out_dir / "hunters" / f"{slug}.json"
        
        write_badge(
            badge_path,
            label=f"@{str(row['hunter']).lstrip('@')[:12]}",
            message=f"{row['xp']} XP",
            color=get_level_color(int(row.get("level", 1))),
            named_logo="github" if "github" in str(row.get("wallet", "")).lower() else None,
        )


def generate_top_hunters_badges(rows: List[Dict], out_dir: Path) -> None:
    """Generate top 3 hunters summary badges."""
    sorted_rows = sorted(rows, key=lambda x: -int(x["xp"]))[:3]
    
    for idx, row in enumerate(sorted_rows, start=1):
        badge_path = out_dir / f"top-{idx}.json"
        medals = ["🥇", "🥈", "🥉"]
        
        write_badge(
            badge_path,
            label=f"#{idx} Hunter",
            message=f"@{str(row['hunter']).lstrip('@')[:12]} • {row['xp']} XP",
            color="gold" if idx == 1 else "silver" if idx == 2 else "orange",
            named_logo="trophy" if idx == 1 else None,
        )
    
    # Combined top 3 badge
    if len(sorted_rows) >= 3:
        names = [str(r["hunter"]).lstrip("@")[:8] for r in sorted_rows]
        combined_path = out_dir / "top-3-summary.json"
        write_badge(
            combined_path,
            label="Top 3 Hunters",
            message=" • ".join(names),
            color="success",
        )


def generate_category_badges(rows: List[Dict], out_dir: Path) -> None:
    """Generate category-based badges (requires category data)."""
    categories = {
        "docs": 0,
        "outreach": 0,
        "bug": 0,
    }
    
    for row in rows:
        title = str(row.get("title", "")).lower()
        if "doc" in title or "scribe" in title:
            categories["docs"] += 1
        if "outreach" in title or "advocate" in title or "ambassador" in title:
            categories["outreach"] += 1
        if "bug" in title or "hunter" in title and "bug" in title:
            categories["bug"] += 1
    
    for cat, count in categories.items():
        badge_path = out_dir / f"category-{cat}.json"
        color_map = {"docs": "informational", "outreach": "blueviolet", "bug": "critical"}
        write_badge(
            badge_path,
            label=f"{cat.title()}",
            message=f"{count} hunters",
            color=color_map.get(cat, "blue"),
        )


def generate_weekly_growth_badge(rows: List[Dict], out_dir: Path) -> None:
    """Generate weekly growth indicator badge."""
    current_week = dt.datetime.utcnow().strftime("%Y-W%W")
    new_hunters_this_week = sum(1 for r in rows if r.get("level", 1) == 1)
    
    badge_path = out_dir / "weekly-growth.json"
    write_badge(
        badge_path,
        label="Weekly Growth",
        message=f"+{new_hunters_this_week} new",
        color="success" if new_hunters_this_week > 0 else "lightgrey",
    )
    
    # Week identifier badge
    week_path = out_dir / "current-week.json"
    write_badge(
        week_path,
        label="Week",
        message=current_week,
        color="blue",
    )


def generate_readme_snippet(rows: List[Dict], out_dir: Path) -> str:
    """Generate README snippet with badge embed examples."""
    readme_path = out_dir / "README.md"
    
    repo_url = "https://github.com/Scottcjn/rustchain-bounties"
    
    content = f"""# 🏆 RustChain Bounties Badges

Auto-generated shields.io badges from XP tracker data.

## Global Badges

### Total Hunters
```markdown
![Total Hunters](https://img.shields.io/endpoint?url={repo_url}/raw/main/badges/total-hunters.json)
```

### Weekly Growth
```markdown
![Weekly Growth](https://img.shields.io/endpoint?url={repo_url}/raw/main/badges/weekly-growth.json)
```

### Top Hunter
```markdown
![Top Hunter](https://img.shields.io/endpoint?url={repo_url}/raw/main/badges/top-hunter.json)
```

## Top 3 Hunters

| Rank | Badge |
|------|-------|
| 🥇 #1 | `![#1 Hunter](https://img.shields.io/endpoint?url={repo_url}/raw/main/badges/top-1.json)` |
| 🥈 #2 | `![#2 Hunter](https://img.shields.io/endpoint?url={repo_url}/raw/main/badges/top-2.json)` |
| 🥉 #3 | `![#3 Hunter](https://img.shields.io/endpoint?url={repo_url}/raw/main/badges/top-3.json)` |

## Per-Hunter Badges

### Your Personal Badge
```markdown
![My XP](https://img.shields.io/endpoint?url={repo_url}/raw/main/badges/hunters/YOUR_USERNAME.json)
```

**Available hunter slugs:**
"""
    
    for row in rows[:20]:
        content += f"- `{row['slug']}` — @{row['hunter']}\n"
    
    if len(rows) > 20:
        content += f"- ...and {len(rows) - 20} more (see `badges/hunters/` directory)\n"
    
    content += f"""

## Category Badges

```markdown
![Docs Hunters](https://img.shields.io/endpoint?url={repo_url}/raw/main/badges/category-docs.json)
![Outreach Hunters](https://img.shields.io/endpoint?url={repo_url}/raw/main/badges/category-outreach.json)
![Bug Hunters](https://img.shields.io/endpoint?url={repo_url}/raw/main/badges/category-bug.json)
```

## Embedding in Your Profile

Add badges to your GitHub profile README or external sites:

```markdown
## My RustChain Bounty Stats

![My XP](https://img.shields.io/endpoint?url={repo_url}/raw/main/badges/hunters/YOUR_SLUG.json)
![Top Hunter](https://img.shields.io/endpoint?url={repo_url}/raw/main/badges/top-hunter.json)
```

---

*Last updated: {dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*
"""
    
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return str(readme_path)


def main() -> None:
    args = parse_args()
    tracker_path = Path(args.tracker)
    out_dir = Path(args.out_dir)
    
    if not tracker_path.exists():
        print(f"Error: Tracker file not found: {tracker_path}")
        return
    
    md_text = tracker_path.read_text(encoding="utf-8")
    rows = parse_xp_tracker(md_text)
    
    if not rows:
        print("Warning: No hunter data found in tracker file")
        return
    
    print(f"📊 Found {len(rows)} hunters")
    
    # Global badges
    total_xp = sum(int(r["xp"]) for r in rows)
    active_hunters = len([r for r in rows if int(r["xp"]) > 0])
    legendary = len([r for r in rows if int(r.get("level", 1)) >= 10])
    
    write_badge(
        out_dir / "total-xp.json",
        label="Total XP",
        message=f"{total_xp:,}",
        color="brightgreen",
    )
    
    write_badge(
        out_dir / "total-hunters.json",
        label="Hunters",
        message=f"{len(rows)}",
        color="blue",
    )
    
    write_badge(
        out_dir / "active-hunters.json",
        label="Active Hunters",
        message=f"{active_hunters}",
        color="success" if active_hunters > 0 else "inactive",
    )
    
    write_badge(
        out_dir / "legendary-hunters.json",
        label="Legendary Hunters",
        message=f"{legendary}",
        color="gold" if legendary > 0 else "lightgrey",
    )
    
    write_badge(
        out_dir / "updated-at.json",
        label="Updated",
        message=dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        color="blue",
        cache_seconds=300,
    )
    
    # Top hunter badge
    if rows:
        top = rows[0]
        top_name = str(top["hunter"]).lstrip("@")[:12]
        write_badge(
            out_dir / "top-hunter.json",
            label="Top Hunter",
            message=f"@{top_name} ({top['xp']} XP)",
            color="gold",
            named_logo="trophy",
        )
    
    # V2 badges
    generate_weekly_growth_badge(rows, out_dir)
    generate_top_hunters_badges(rows, out_dir)
    generate_category_badges(rows, out_dir)
    generate_hunter_badges(rows, out_dir)
    
    # Generate README
    if args.generate_readme or True:
        readme = generate_readme_snippet(rows, out_dir)
        print(f"📝 Generated README at {readme}")
    
    print(f"✅ Generated {len(rows) + 9} badges in {out_dir}/")
    print(f"   - Global badges: 7")
    print(f"   - Per-hunter badges: {len(rows)}")
    print(f"   - Category badges: up to 4")


if __name__ == "__main__":
    main()
