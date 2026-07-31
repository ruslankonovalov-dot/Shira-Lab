"""app/backend/services/update_checker.py -- Check for updates via GitHub Releases.

Checks for new version at app startup (in background).
If available -- shows banner in HomePage.
"""
from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

GITHUB_API_LATEST = "https://api.github.com/repos/shira/shira-lab/releases/latest"
TIMEOUT_SEC = 5


def check_for_updates(current_version: str, repo_url: str = GITHUB_API_LATEST) -> Dict[str, Any]:
    """Check for new version on GitHub.

    Args:
        current_version: Current app version (e.g., "0.16.0").
        repo_url: GitHub API endpoint for latest release.

    Returns:
        {
            "ok": True,
            "update_available": bool,
            "current_version": str,
            "latest_version": str | None,
            "download_url": str | None,
            "release_notes": str | None,
            "release_html_url": str | None
        }
        or {"ok": False, "error": str}
    """
    try:
        req = urllib.request.Request(
            repo_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "ShiraLab-UpdateChecker/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as response:
            data = json.loads(response.read().decode("utf-8"))

        latest_tag = data.get("tag_name", "").lstrip("v")
        if not latest_tag:
            return {"ok": False, "error": "Invalid release response: no tag_name"}

        update_available = _compare_versions(latest_tag, current_version) > 0

        # Find .exe asset for Windows
        download_url: Optional[str] = None
        for asset in data.get("assets", []):
            if asset.get("name", "").endswith(".exe"):
                download_url = asset.get("browser_download_url")
                break

        return {
            "ok": True,
            "update_available": update_available,
            "current_version": current_version,
            "latest_version": latest_tag,
            "download_url": download_url,
            "release_notes": data.get("body", "")[:500],  # truncate long descriptions
            "release_html_url": data.get("html_url"),
        }

    except urllib.error.URLError as e:
        logger.warning("Network error checking updates: %s", e)
        return {"ok": False, "error": f"Network error: {e}"}
    except Exception as e:
        logger.exception("Failed to check for updates")
        return {"ok": False, "error": str(e)}


def _compare_versions(v1: str, v2: str) -> int:
    """Compare two semver strings.

    Returns:
        1 if v1 > v2
        0 if v1 == v2
        -1 if v1 < v2

    Note: prerelease suffixes (-rc1, -beta) are stripped before comparison,
    so '1.0.0-rc1' compares as equal to '1.0.0'.
    """
    def parse(v: str) -> tuple[int, ...]:
        # Strip prerelease suffix (everything after -)
        v = v.split("-")[0]
        parts = []
        for p in v.split("."):
            # Extract only digits
            digits = "".join(c for c in p if c.isdigit())
            parts.append(int(digits) if digits else 0)
        return tuple(parts)

    p1 = parse(v1)
    p2 = parse(v2)
    # Pad with zeros to same length
    max_len = max(len(p1), len(p2))
    p1 = p1 + (0,) * (max_len - len(p1))
    p2 = p2 + (0,) * (max_len - len(p2))

    if p1 > p2:
        return 1
    elif p1 < p2:
        return -1
    return 0


# ─── Async wrapper for Qt use ──────────────────────

def check_for_updates_async(current_version: str, callback: Callable[[str], None]) -> None:
    """Run check in background thread, call callback with JSON result.

    Usage from QmlBridge:
        def _on_update_checked(self, result_json):
            result = json.loads(result_json)
            if result.get("ok") and result.get("update_available"):
                self.updateAvailable.emit(result)

        def check_updates(self):
            from app.backend.services.update_checker import check_for_updates_async
            check_for_updates_async("0.16.0", self._on_update_checked)
    """
    import threading

    def worker() -> None:
        result = check_for_updates(current_version)
        try:
            callback(json.dumps(result))
        except Exception:
            logger.exception("Update check callback failed")

    t = threading.Thread(target=worker, daemon=True)
    t.start()
