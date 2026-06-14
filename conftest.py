import json
import time
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--json-report",
        action="store",
        default=None,
        help="Write a JSON pytest summary to this path.",
    )


def pytest_configure(config):
    config._json_report_started_at = time.time()
    config._json_report_results = {}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return

    item.config._json_report_results[report.nodeid] = {
        "nodeid": report.nodeid,
        "name": item.name,
        "outcome": report.outcome,
        "duration_seconds": round(report.duration, 4),
        "location": {
            "file": str(report.location[0]),
            "line": report.location[1] + 1,
            "test": report.location[2],
        },
        "failure": report.longreprtext if report.failed else None,
    }


def pytest_sessionfinish(session, exitstatus):
    output_path = session.config.getoption("--json-report")
    if not output_path:
        return

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    results = list(session.config._json_report_results.values())
    payload = {
        "exitstatus": exitstatus,
        "duration_seconds": round(time.time() - session.config._json_report_started_at, 4),
        "summary": {
            "total": len(results),
            "passed": sum(1 for result in results if result["outcome"] == "passed"),
            "failed": sum(1 for result in results if result["outcome"] == "failed"),
            "skipped": sum(1 for result in results if result["outcome"] == "skipped"),
        },
        "tests": results,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
