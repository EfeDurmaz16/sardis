#!/usr/bin/env python3
"""Generate protocol conformance report from pytest results."""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = Path(os.getenv("SARDIS_REPORT_DIR", str(ROOT / "reports")))
REPORT_PATH = REPORT_DIR / "protocol-conformance-report.md"


def get_git_sha() -> str:
    """Get current git commit SHA (short form)."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, cwd=str(ROOT)
        ).strip()[:12]
    except Exception:
        return "unknown"


def _pytest_supports_json_report() -> bool:
    """Return True if current pytest environment supports --json-report."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        return "--json-report" in (result.stdout or "")
    except Exception:
        return False


def _build_fallback_report(pytest_output: str, returncode: int) -> dict:
    """
    Build a minimal report structure when pytest-json-report is unavailable.

    This keeps report generation resilient in local/dev environments.
    """
    test_line = re.compile(r"^(?P<nodeid>\S+::\S+)\s+(?P<outcome>PASSED|FAILED|SKIPPED)\b", re.MULTILINE)
    tests = []
    for match in test_line.finditer(pytest_output):
        tests.append(
            {
                "nodeid": match.group("nodeid"),
                "outcome": match.group("outcome").lower(),
            }
        )

    output_lower = pytest_output.lower()

    # Prefer pytest summary line counts when available (more reliable than line-level parsing).
    summary_line = ""
    for line in output_lower.splitlines():
        stripped = line.strip()
        if stripped.startswith("=") and "passed" in stripped:
            summary_line = stripped

    source = summary_line or output_lower

    def extract_count(label: str) -> int:
        match = re.search(rf"(\d+)\s+{label}\b", source)
        return int(match.group(1)) if match else 0

    passed = extract_count("passed")
    failed = extract_count("failed")
    skipped = extract_count("skipped")
    errors = extract_count("error")
    if errors == 0:
        errors = extract_count("errors")
    if errors == 0 and returncode not in (0, 1, 5):
        errors = 1

    return {
        "summary": {
            "total": passed + failed + skipped + errors,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "error": errors,
        },
        "tests": tests,
    }


def run_tests() -> dict:
    """Run protocol conformance tests and return JSON report."""
    report_file = "/tmp/protocol-report.json"
    supports_json_report = _pytest_supports_json_report()
    env = os.environ.copy()
    env.setdefault("SARDIS_ENVIRONMENT", "dev")
    env.setdefault("SARDIS_SECRET_KEY", "test-secret-key-for-ci-only-32chars")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        "protocol_conformance",
        "tests/",
        "--ignore=tests/integration",
        "--ignore=tests/e2e",
        "--strict-markers",
        "-v",
        "--tb=short",
    ]
    if supports_json_report:
        cmd.extend(["--json-report", f"--json-report-file={report_file}"])

    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    output = f"{result.stdout}\n{result.stderr}"

    if supports_json_report and Path(report_file).exists():
        with open(report_file) as f:
            return json.load(f)

    return _build_fallback_report(output, result.returncode)


def classify_protocol(test_name: str) -> str:
    """Classify test by protocol based on test name or markers."""
    test_lower = test_name.lower()
    if "tap" in test_lower:
        return "TAP"
    elif "ap2" in test_lower or "mandate" in test_lower or "security_lock" in test_lower:
        return "AP2"
    elif "ucp" in test_lower or "checkout" in test_lower:
        return "UCP"
    elif "x402" in test_lower or "erc3009" in test_lower:
        return "x402"
    elif (
        "reason_code" in test_lower
        or "bypass" in test_lower
        or "tenant" in test_lower
        or "protocol_stack" in test_lower
        or "protocol_version" in test_lower
    ):
        return "Cross-Protocol"
    return "Other"


def generate_report(data: dict) -> str:
    """Generate markdown report from pytest JSON data."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    git_sha = get_git_sha()

    # Extract summary
    summary = data.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    errors = summary.get("error", 0)

    # Classify tests by protocol
    protocol_stats = {
        "TAP": {"passed": 0, "failed": 0, "skipped": 0},
        "AP2": {"passed": 0, "failed": 0, "skipped": 0},
        "UCP": {"passed": 0, "failed": 0, "skipped": 0},
        "x402": {"passed": 0, "failed": 0, "skipped": 0},
        "Cross-Protocol": {"passed": 0, "failed": 0, "skipped": 0},
        "Other": {"passed": 0, "failed": 0, "skipped": 0},
    }

    failing_tests = []

    for test in data.get("tests", []):
        nodeid = test.get("nodeid", "")
        outcome = test.get("outcome", "unknown")
        protocol = classify_protocol(nodeid)

        if outcome == "passed":
            protocol_stats[protocol]["passed"] += 1
        elif outcome == "failed":
            protocol_stats[protocol]["failed"] += 1
            failing_tests.append(
                {
                    "nodeid": nodeid,
                    "protocol": protocol,
                    "error": test.get("call", {}).get("longrepr", "No error details"),
                }
            )
        elif outcome == "skipped":
            protocol_stats[protocol]["skipped"] += 1

    # Build markdown report
    lines = [
        "# Protocol Conformance Report",
        "",
        f"**Generated:** {timestamp}",
        f"**Git SHA:** {git_sha}",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"| Total | Passed | Failed | Skipped | Errors |",
        f"|-------|--------|--------|---------|--------|",
        f"| {total} | {passed} | {failed} | {skipped} | {errors} |",
        "",
    ]

    # Overall status
    if failed > 0 or errors > 0:
        lines.append("**Status:** ❌ FAILED")
    elif skipped > 0:
        lines.append("**Status:** ⚠️  PASSED WITH SKIPS")
    else:
        lines.append("**Status:** ✅ PASSED")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Per-Protocol Breakdown",
            "",
            "| Protocol | Passed | Failed | Skipped | Total |",
            "|----------|--------|--------|---------|-------|",
        ]
    )

    for protocol in ["TAP", "AP2", "UCP", "x402", "Cross-Protocol", "Other"]:
        stats = protocol_stats[protocol]
        p = stats["passed"]
        f = stats["failed"]
        s = stats["skipped"]
        t = p + f + s
        if t > 0:  # Only show protocols with tests
            lines.append(f"| {protocol} | {p} | {f} | {s} | {t} |")

    # Failing tests section
    if failing_tests:
        lines.extend(
            [
                "",
                "---",
                "",
                "## Failing Tests",
                "",
            ]
        )

        for test in failing_tests:
            lines.extend(
                [
                    f"### {test['nodeid']}",
                    "",
                    f"**Protocol:** {test['protocol']}",
                    "",
                    "**Error:**",
                    "```",
                    str(test["error"])[:500],  # Truncate long errors
                    "```",
                    "",
                ]
            )

    # Coverage section (if available)
    if "coverage" in data:
        lines.extend(
            [
                "---",
                "",
                "## Coverage Summary",
                "",
                f"**Total Coverage:** {data['coverage'].get('percent_covered', 'N/A')}%",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            f"_Report generated by `scripts/generate_protocol_conformance_report.py` at {timestamp}_",
            "",
        ]
    )

    return "\n".join(lines)


def main():
    """Main entry point."""
    print("Running protocol conformance tests...")
    data = run_tests()

    print("Generating report...")
    report = generate_report(data)

    output_path = REPORT_PATH
    try:
        REPORT_DIR.mkdir(exist_ok=True, parents=True)
    except PermissionError:
        fallback_dir = Path("/tmp/sardis-reports")
        fallback_dir.mkdir(exist_ok=True, parents=True)
        output_path = fallback_dir / "protocol-conformance-report.md"
        print(f"Warning: cannot write to {REPORT_DIR}; using fallback {fallback_dir}")

    output_path.write_text(report)
    print(f"Report written to {output_path}")

    # Exit with appropriate code
    summary = data.get("summary", {})
    if summary.get("failed", 0) > 0 or summary.get("error", 0) > 0:
        print("\n❌ Protocol conformance tests FAILED")
        sys.exit(1)
    else:
        print("\n✅ Protocol conformance tests PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
