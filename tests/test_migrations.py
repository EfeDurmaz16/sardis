"""Tests for database migration file integrity.

Verifies migration files follow sequential numbering, contain valid SQL,
and match the expected naming pattern.
"""

import os
import re

import pytest

MIGRATION_DIR = os.path.join(
    os.path.dirname(__file__), "..", "packages", "sardis-api", "migrations"
)


def _get_migration_files():
    """Get sorted list of .sql migration files, excluding rollback files."""
    if not os.path.isdir(MIGRATION_DIR):
        pytest.skip(f"Migration directory not found: {MIGRATION_DIR}")
    files = sorted(
        f
        for f in os.listdir(MIGRATION_DIR)
        if f.endswith(".sql") and "_rollback" not in f
    )
    return files


def test_migration_directory_exists():
    """Migration directory must exist."""
    assert os.path.isdir(MIGRATION_DIR), f"Missing migration directory: {MIGRATION_DIR}"


def test_migration_files_exist():
    """There should be at least one migration file."""
    files = _get_migration_files()
    assert len(files) > 0, "No migration files found"


def test_migration_filename_pattern():
    """All migration files must follow NNN_description.sql pattern."""
    files = _get_migration_files()
    pattern = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$")

    for f in files:
        assert pattern.match(f), (
            f"Migration '{f}' does not follow NNN_description.sql pattern "
            f"(lowercase alphanumeric + underscores)"
        )


def test_migration_sequential_numbering():
    """Verify migrations are numbered sequentially with no duplicates."""
    files = _get_migration_files()
    numbers = []
    for f in files:
        match = re.match(r"^(\d+)_", f)
        assert match, f"Migration {f} does not follow NNN_name.sql pattern"
        numbers.append(int(match.group(1)))

    # Check no duplicates
    duplicates = [n for n in numbers if numbers.count(n) > 1]
    assert len(numbers) == len(set(numbers)), (
        f"Duplicate migration numbers found: {sorted(set(duplicates))}"
    )

    # Check monotonically increasing (strictly)
    for i in range(1, len(numbers)):
        assert numbers[i] > numbers[i - 1], (
            f"Migration ordering broken: {numbers[i - 1]:03d} -> {numbers[i]:03d} "
            f"(must be strictly increasing)"
        )


def test_migration_no_large_gaps():
    """Warn if there are gaps larger than 5 in migration numbering.

    Small gaps are acceptable (deleted/merged migrations), but large gaps
    suggest missing files.
    """
    files = _get_migration_files()
    numbers = []
    for f in files:
        match = re.match(r"^(\d+)_", f)
        if match:
            numbers.append(int(match.group(1)))

    max_allowed_gap = 5
    for i in range(1, len(numbers)):
        gap = numbers[i] - numbers[i - 1]
        assert gap <= max_allowed_gap, (
            f"Large gap in migration numbering: {numbers[i - 1]:03d} -> {numbers[i]:03d} "
            f"(gap of {gap}, max allowed {max_allowed_gap})"
        )


def test_migration_valid_sql():
    """Basic check that migration files contain SQL."""
    files = _get_migration_files()
    sql_keywords = [
        "CREATE",
        "ALTER",
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "SELECT",
        "BEGIN",
        "GRANT",
        "SET",
        "DO",
        "COMMENT",
        "INDEX",
    ]

    for f in files:
        path = os.path.join(MIGRATION_DIR, f)
        with open(path) as fh:
            content = fh.read().strip()
        assert len(content) > 0, f"Empty migration: {f}"

        # Strip SQL comments for keyword check
        lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped.startswith("--"):
                lines.append(stripped)
        content_no_comments = " ".join(lines).upper()

        has_sql = any(kw in content_no_comments for kw in sql_keywords)
        assert has_sql, (
            f"Migration {f} doesn't appear to contain SQL "
            f"(no recognized SQL keywords found)"
        )


def test_migration_no_empty_files():
    """No migration file should be empty or contain only comments."""
    files = _get_migration_files()

    for f in files:
        path = os.path.join(MIGRATION_DIR, f)
        with open(path) as fh:
            content = fh.read().strip()

        # Remove all comment lines and check if anything remains
        non_comment_lines = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and not line.strip().startswith("--")
        ]
        assert len(non_comment_lines) > 0, (
            f"Migration {f} contains only comments or whitespace"
        )


def test_migration_no_syntax_red_flags():
    """Check for common SQL syntax issues that indicate broken migrations."""
    files = _get_migration_files()

    for f in files:
        path = os.path.join(MIGRATION_DIR, f)
        with open(path) as fh:
            content = fh.read()

        # Check for unmatched BEGIN/COMMIT (basic transaction safety)
        upper = content.upper()
        begins = upper.count("BEGIN;") + upper.count("BEGIN ")
        commits = upper.count("COMMIT;") + upper.count("COMMIT ")

        # If a migration has BEGIN, it should have COMMIT
        if begins > 0:
            assert commits > 0, (
                f"Migration {f} has BEGIN without COMMIT "
                f"(unclosed transaction)"
            )


def test_migration_rollback_files_match():
    """If a rollback file exists, it should have a matching forward migration."""
    if not os.path.isdir(MIGRATION_DIR):
        pytest.skip("Migration directory not found")

    all_files = os.listdir(MIGRATION_DIR)
    rollback_files = [f for f in all_files if "_rollback" in f and f.endswith(".sql")]

    for rollback in rollback_files:
        forward = rollback.replace("_rollback", "")
        assert forward in all_files, (
            f"Rollback file '{rollback}' has no matching forward migration '{forward}'"
        )


def test_migration_starts_at_001():
    """First migration should be numbered 001."""
    files = _get_migration_files()
    if not files:
        pytest.skip("No migration files found")

    match = re.match(r"^(\d+)_", files[0])
    assert match, f"First file doesn't match pattern: {files[0]}"
    first_num = int(match.group(1))
    assert first_num == 1, (
        f"First migration should be 001, got {first_num:03d}"
    )
