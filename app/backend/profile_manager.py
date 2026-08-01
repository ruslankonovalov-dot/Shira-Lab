"""
profile_manager.py -- Game profiles/presets for Shira Lab.

Allows saving/loading complete module configurations as named profiles.
Each profile stores: clicker config, aim config, macro actions, recorder settings,
target windows, and hotkeys.

Usage:
    ProfileManager.save("Minecraft Auto-Farm")
    ProfileManager.load("Minecraft Auto-Farm")
    ProfileManager.list_profiles()
    ProfileManager.delete("Minecraft Auto-Farm")
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROFILES_DIR = Path(__file__).resolve().parents[3] / "data" / "profiles"


class ProfileManager:
    """Manages game profiles/presets."""

    def __init__(self, bridge: Any = None) -> None:
        self._bridge = bridge
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    def _sanitize_name(self, name: str) -> str:
        """Sanitize profile name to safe filename."""
        safe = "".join(c for c in name if c.isalnum() or c in "-_ ")
        safe = safe.replace(" ", "_")
        return safe

    def save_profile(self, name: str) -> dict[str, Any]:
        """Save current configuration as a named profile."""
        if not name or not name.strip():
            return {"ok": False, "error": "Profile name cannot be empty"}

        name = name.strip()
        safe_name = self._sanitize_name(name)
        if not safe_name:
            return {"ok": False, "error": "Invalid profile name"}

        profile_path = PROFILES_DIR / f"{safe_name}.json"

        try:
            profile_data = {
                "name": name,
                "clicker": self._bridge.clicker.get_status() if self._bridge else {},
                "aim": self._bridge.aim.get_status() if self._bridge else {},
                "macro": self._bridge.macro.get_status() if self._bridge else {},
                "recorder": self._bridge.recorder.status() if self._bridge else {},
                "state": {
                    "terminal_palette": (
                        self._bridge.state.terminal_palette if self._bridge else "matrix"
                    ),
                    "is_pinned": (self._bridge.state.is_pinned if self._bridge else False),
                    "hotkeys": self._bridge.state.hotkeys if self._bridge else {},
                },
            }

            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)

            logger.info("Profile saved: %s", name)
            return {"ok": True, "name": name, "path": str(profile_path)}
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to save profile %s: %s", name, e)
            return {"ok": False, "error": str(e)}

    def load_profile(self, name: str) -> dict[str, Any]:
        """Load a named profile and apply its configuration."""
        if not name:
            return {"ok": False, "error": "Profile name required"}

        safe_name = self._sanitize_name(name)
        profile_path = PROFILES_DIR / f"{safe_name}.json"

        if not profile_path.exists():
            return {"ok": False, "error": f"Profile '{name}' not found"}

        try:
            with open(profile_path, encoding="utf-8") as f:
                data = json.load(f)

            # Apply clicker config
            c = data.get("clicker", {})
            if c and self._bridge:
                self._bridge.clicker.update_config(
                    c.get("interval_ms", 100),
                    c.get("hold_ms", 0),
                    c.get("button", "L"),
                    c.get("limit", 0),
                    c.get("background_method", "sendinput"),
                )

            # Apply aim config
            a = data.get("aim", {})
            if a and self._bridge:
                self._bridge.aim.update_config(
                    a.get("confidence", 0.5),
                    a.get("smooth_steps", 5),
                    a.get("reset_delay", 0.005),
                )
                if a.get("detection_mode"):
                    self._bridge.aim.set_detection_mode(a["detection_mode"])
                if a.get("target_color"):
                    self._bridge.aim.set_target_color(a["target_color"])
                if a.get("fov_radius"):
                    self._bridge.aim.set_fov(a["fov_radius"])
                if a.get("aim_speed"):
                    self._bridge.aim.set_aim_speed(a["aim_speed"])

            # Apply macro config
            m = data.get("macro", {})
            if m and self._bridge:
                self._bridge.macro.set_run_mode(m.get("run_mode", "SEQUENTIAL"))
                self._bridge.macro.set_background_method(m.get("background_method", "sendinput"))
                self._bridge.macro.clear_actions()
                for action in m.get("actions", []):
                    self._bridge.macro.add_action(
                        action.get("key", "space"),
                        action.get("delay", 0.5),
                        action.get("hold", 0.05),
                    )

            # Apply recorder config
            r = data.get("recorder", {})
            if r and self._bridge:
                self._bridge.recorder.set_background_method(r.get("background_method", "sendinput"))

            # Apply state
            s = data.get("state", {})
            if s and self._bridge and s.get("terminal_palette"):
                self._bridge.setTerminalPalette(s["terminal_palette"])

            logger.info("Profile loaded: %s", name)
            return {"ok": True, "name": name}
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to load profile %s: %s", name, e)
            return {"ok": False, "error": str(e)}

    def list_profiles(self) -> dict[str, Any]:
        """List all saved profiles."""
        try:
            profiles: list[dict[str, str]] = []
            for f in sorted(PROFILES_DIR.glob("*.json")):
                try:
                    with open(f, encoding="utf-8") as fh:
                        data = json.load(fh)
                    profiles.append(
                        {
                            "name": data.get("name", f.stem),
                            "filename": f.name,
                        }
                    )
                except (OSError, json.JSONDecodeError, ValueError):
                    profiles.append({"name": f.stem, "filename": f.name})
            return {"ok": True, "profiles": profiles}
        except OSError as e:
            return {"ok": False, "error": str(e), "profiles": []}

    def delete_profile(self, name: str) -> dict[str, Any]:
        """Delete a named profile."""
        safe_name = self._sanitize_name(name)
        profile_path = PROFILES_DIR / f"{safe_name}.json"

        if not profile_path.exists():
            return {"ok": False, "error": f"Profile '{name}' not found"}

        try:
            profile_path.unlink()
            logger.info("Profile deleted: %s", name)
            return {"ok": True, "name": name}
        except OSError as e:
            return {"ok": False, "error": str(e)}
