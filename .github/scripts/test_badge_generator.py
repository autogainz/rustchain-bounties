#!/usr/bin/env python3
"""Tests for badge_generator_v2.py - Validates badge generation edge cases."""

import json
import tempfile
from pathlib import Path
from generate_dynamic_badges import (
    parse_xp_tracker,
    slugify_hunter,
    get_level_color,
    write_badge,
    parse_int,
)


def test_slugify_hunter():
    """Test collision-safe slug generation."""
    test_cases = [
        ("@user123", "user123"),
        ("User-Name", "user-name"),
        ("user.name", "user.name"),
        ("user/name", "user-name"),
        ("  spaced  ", "spaced"),
        ("--user--", "user"),
        ("u$er@na#me!", "u-er-na-me"),
        ("", "unknown"),
        ("🚀emoji👾test", "emoji-test"),
    ]
    
    for input_val, expected in test_cases:
        result = slugify_hunter(input_val)
        assert result == expected, f"slugify_hunter({input_val!r}) = {result!r}, expected {expected!r}"
    
    print("✅ test_slugify_hunter passed")


def test_parse_int():
    """Test integer parsing from strings."""
    test_cases = [
        ("123", 123),
        ("  456  ", 456),
        ("Level 42", 42),
        ("XP: 999 points", 999),
        ("", 0),
        ("abc", 0),
        ("abc123xyz", 123),
    ]
    
    for input_val, expected in test_cases:
        result = parse_int(input_val)
        assert result == expected, f"parse_int({input_val!r}) = {result}, expected {expected}"
    
    print("✅ test_parse_int passed")


def test_parse_xp_tracker():
    """Test parsing XP tracker markdown."""
    sample_md = """
# XP Tracker

| Rank | Hunter | Wallet | XP | Level | Title |
|------|--------|--------|-----|-------|-------|
| 1 | @alice | alice.eth | 1500 | 5 | Hunter |
| 2 | @bob | bob.sol | 1200 | 4 | Bug Hunter |
| 3 | @charlie | charlie.btc | 900 | 3 | Docs Scribe |

_Other data_
"""
    
    rows = parse_xp_tracker(sample_md)
    
    assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"
    
    # Check first row
    assert rows[0]["hunter"] == "@alice"
    assert rows[0]["xp"] == 1500
    assert rows[0]["level"] == 5
    assert rows[0]["slug"] == "alice"
    
    # Check sorting (by XP descending)
    assert rows[0]["xp"] >= rows[1]["xp"] >= rows[2]["xp"]
    
    # Check rank assignment
    assert rows[0]["rank"] == 1
    assert rows[1]["rank"] == 2
    assert rows[2]["rank"] == 3
    
    print("✅ test_parse_xp_tracker passed")


def test_parse_xp_tracker_no_rank_column():
    """Test parsing XP tracker without Rank column."""
    sample_md = """
| Hunter | Wallet | XP | Level |
|--------|--------|-----|-------|
| @alice | addr1 | 1500 | 5 |
| @bob | addr2 | 1200 | 4 |
"""
    
    rows = parse_xp_tracker(sample_md)
    
    assert len(rows) == 2
    assert rows[0]["hunter"] == "@alice"
    assert rows[0]["xp"] == 1500
    assert rows[0]["rank"] == 1  # Auto-assigned
    
    print("✅ test_parse_xp_tracker_no_rank_column passed")


def test_get_level_color():
    """Test level-to-color mapping."""
    color_map = {
        1: "lightgrey",
        5: "orange",
        10: "gold",
        15: "blue",  # Clamped to 10
    }
    
    for level, expected in color_map.items():
        result = get_level_color(level)
        assert result == expected, f"get_level_color({level}) = {result}, expected {expected}"
    
    print("✅ test_get_level_color passed")


def test_write_badge():
    """Test badge JSON generation and schema validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        badge_path = Path(tmpdir) / "test-badge.json"
        
        write_badge(
            badge_path,
            label="Test",
            message="Hello",
            color="green",
            named_logo="github",
        )
        
        # Verify file exists and is valid JSON
        assert badge_path.exists()
        
        with open(badge_path, "r") as f:
            data = json.load(f)
        
        # Validate schema
        assert data["schemaVersion"] == 1
        assert data["label"] == "Test"
        assert data["message"] == "Hello"
        assert data["color"] == "green"
        assert data["style"] == "flat"
        assert data["namedLogo"] == "github"
        assert data["cacheSeconds"] == 3600
    
    print("✅ test_write_badge passed")


def test_write_badge_minimal():
    """Test badge generation with minimal parameters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        badge_path = Path(tmpdir) / "minimal-badge.json"
        
        write_badge(
            badge_path,
            label="Minimal",
            message="Test",
        )
        
        with open(badge_path, "r") as f:
            data = json.load(f)
        
        assert data["label"] == "Minimal"
        assert data["message"] == "Test"
        assert data["color"] == "blue"  # Default
        assert "namedLogo" not in data  # Optional
    
    print("✅ test_write_badge_minimal passed")


def test_slug_collision():
    """Test that different hunters don't get the same slug."""
    hunters = [
        "@user-one",
        "@user_one",
        "@user one",
        "@user--one",
    ]
    
    slugs = [slugify_hunter(h) for h in hunters]
    
    # All should normalize to the same slug
    assert len(set(slugs)) == 1, f"Expected collision handling, got: {slugs}"
    assert slugs[0] == "user-one"
    
    print("✅ test_slug_collision passed")


def test_empty_tracker():
    """Test handling of empty or malformed tracker."""
    empty_md = "# Empty\n\nNo table here."
    rows = parse_xp_tracker(empty_md)
    assert rows == []
    
    print("✅ test_empty_tracker passed")


def test_tbd_placeholder():
    """Test that _TBD_ placeholders are skipped."""
    sample_md = """
| Hunter | XP |
|--------|-----|
| @alice | 100 |
| _TBD_ | 0 |
| @bob | 200 |
"""
    
    rows = parse_xp_tracker(sample_md)
    assert len(rows) == 2
    assert all(r["hunter"] != "_TBD_" for r in rows)
    
    print("✅ test_tbd_placeholder passed")


def run_all_tests():
    """Run all test cases."""
    print("Running badge generator tests...\n")
    
    tests = [
        test_slugify_hunter,
        test_parse_int,
        test_parse_xp_tracker,
        test_parse_xp_tracker_no_rank_column,
        test_get_level_color,
        test_write_badge,
        test_write_badge_minimal,
        test_slug_collision,
        test_empty_tracker,
        test_tbd_placeholder,
    ]
    
    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} ERROR: {e}")
            failed += 1
    
    print(f"\n{'=' * 40}")
    if failed == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ {failed}/{len(tests)} tests failed")
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
