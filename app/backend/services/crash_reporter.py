"""app/backend/services/crash_reporter.py -- Global crash handler.

Sets sys.excepthook to catch unhandled exceptions:
1. Builds report (traceback + system info)
2. Logs locally to data/crash_logs/
3. (Optional) Sends to server if user consented

IMPORTANT: Server reporting MUST be explicitly enabled by user
in Settings -> Privacy -> "Send crash reports to help improve Shira Lab".
"""

from __future__ import annotations

import datetime
import json
import logging
import platform
import sys
import traceback
import urllib.request
from pathlib import Path
from types import TracebackType
from typing import Any

logger = logging.getLogger(__name__)

CRASH_LOG_DIR = Path("data/crash_logs")
CRASH_SERVER_URL = "https://api.shira.lab/crash"  # Replace with real endpoint


def install_crash_handler(app_version: str, send_reports: bool = False) -> None:
    """Install global unhandled exception handler.

    Args:
        app_version: Current application version (for report context).
        send_reports: If True -- send report to server (after explicit consent).
    """
    CRASH_LOG_DIR.mkdir(parents=True, exist_ok=True)
    original_excepthook = sys.excepthook

    def handler(
        exc_type: type[BaseException],
        exc_value: BaseException,
        tb: TracebackType | None,
    ) -> None:
        try:
            # traceback.format_exception requires non-None exc_type, but we handle the Optional case
            report = _build_report(exc_type, exc_value, tb, app_version)
            _save_local(report)

            if send_reports:
                _send_to_server(report)
        except Exception:  # noqa: BLE001,S110 - crash handler must never crash
            # Crash handler must never crash -- otherwise it hangs
            pass
        finally:
            # Call original hook for default stderr output
            original_excepthook(exc_type, exc_value, tb)

    sys.excepthook = handler
    logger.info("Crash handler installed (send_reports=%s)", send_reports)


def _build_report(
    exc_type: type[BaseException],
    exc_value: BaseException | None,
    tb: TracebackType | None,
    app_version: str,
) -> dict[str, Any]:
    """Build structured crash report."""
    return {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "app_version": app_version,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "exception_type": exc_type.__name__ if exc_type else "Unknown",
        "exception_message": str(exc_value) if exc_value else "",
        "traceback": (
            "".join(traceback.format_exception(exc_type, exc_value, tb))
            if exc_type
            else ""
        ),
        # NOT collected: path to profile.json, record contents, screenshots
        # User may manually attach if needed
    }


def _save_local(report: dict[str, Any]) -> Path:
    """Save report locally to data/crash_logs/."""
    CRASH_LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    exc_type = report.get("exception_type", "Unknown")
    filename = f"crash_{timestamp}_{exc_type}.json"
    path = CRASH_LOG_DIR / filename

    try:
        path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.error("Crash report saved to %s", path)
    except OSError as e:
        logger.error("Failed to save crash report: %s", e)
    return path


def _send_to_server(report: dict[str, Any]) -> bool:
    """Send report to server (best-effort, non-blocking)."""
    try:
        req = urllib.request.Request(
            CRASH_SERVER_URL,
            data=json.dumps(report).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": f"ShiraLab-CrashReporter/{report.get('app_version', '1.0')}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                logger.info("Crash report sent to server")
                return True
            else:
                logger.warning("Crash report server returned %s", response.status)
                return False
    except (OSError, ValueError) as e:
        logger.warning("Failed to send crash report: %s", e)
        return False


def list_local_crashes() -> list[dict[str, Any]]:
    """Return list of local crash logs (for Diagnostics display)."""
    if not CRASH_LOG_DIR.exists():
        return []

    crashes: list[dict[str, Any]] = []
    for path in sorted(CRASH_LOG_DIR.glob("crash_*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            crashes.append(
                {
                    "file": path.name,
                    "timestamp": data.get("timestamp", ""),
                    "exception_type": data.get("exception_type", "Unknown"),
                    "exception_message": data.get("exception_message", ""),
                    "size_bytes": path.stat().st_size,
                }
            )
        except (OSError, json.JSONDecodeError, ValueError):
            continue

    return crashes


def read_local_crash(filename: str) -> dict[str, Any] | None:
    """Read content of specific crash log."""
    path = CRASH_LOG_DIR / filename
    if not path.exists() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    return None


def delete_local_crash(filename: str) -> bool:
    """Delete a crash log."""
    path = CRASH_LOG_DIR / filename
    try:
        if path.exists():
            path.unlink()
            return True
    except OSError:
        pass
    return False


def clear_all_crashes() -> int:
    """Delete all crash logs. Returns count deleted."""
    if not CRASH_LOG_DIR.exists():
        return 0
    count = 0
    for path in CRASH_LOG_DIR.glob("crash_*.json"):
        try:
            path.unlink()
            count += 1
        except OSError:
            pass
    return count
