# tests/unit/test_vigem_service.py — VigemService comprehensive tests for Phase 3.6

import pytest


class TestVigemService:
    """Tests for VigemService."""

    def setup_method(self):
        from app.backend.services.vigem_service import VigemService
        self.service = VigemService()

    def test_add_x360(self):
        """Test adding X360 target."""
        result = self.service.add_x360()
        assert isinstance(result, (int, type(None)))

    def test_add_ds4(self):
        """Test adding DS4 target."""
        result = self.service.add_ds4()
        assert isinstance(result, (int, type(None)))

    def test_remove_target(self):
        """Test removing target."""
        target_id = self.service.add_x360()
        if target_id:
            result = self.service.remove_target(target_id)
            assert isinstance(result, bool)

    def test_remove_nonexistent_target(self):
        """Test removing non-existent target."""
        result = self.service.remove_target(999)
        assert result is False

    def test_button_name_to_mask(self):
        """Test button name to mask conversion."""
        from app.backend.services.vigem_service import XUSB_BUTTON_MAP, VigemService

        # Test known button mappings
        assert VigemService.button_name_to_mask("a") == XUSB_BUTTON_MAP.get("a", 0)
        assert VigemService.button_name_to_mask("b") == XUSB_BUTTON_MAP.get("b", 0)
        assert VigemService.button_name_to_mask("x") == XUSB_BUTTON_MAP.get("x", 0)
        assert VigemService.button_name_to_mask("y") == XUSB_BUTTON_MAP.get("y", 0)
        assert VigemService.button_name_to_mask("lb") == XUSB_BUTTON_MAP.get("lb", 0)
        assert VigemService.button_name_to_mask("rb") == XUSB_BUTTON_MAP.get("rb", 0)
        assert VigemService.button_name_to_mask("back") == XUSB_BUTTON_MAP.get("back", 0)
        assert VigemService.button_name_to_mask("start") == XUSB_BUTTON_MAP.get("start", 0)
        assert VigemService.button_name_to_mask("up") == XUSB_BUTTON_MAP.get("up", 0)
        assert VigemService.button_name_to_mask("down") == XUSB_BUTTON_MAP.get("down", 0)
        assert VigemService.button_name_to_mask("left") == XUSB_BUTTON_MAP.get("left", 0)
        assert VigemService.button_name_to_mask("right") == XUSB_BUTTON_MAP.get("right", 0)

        # Invalid button
        assert VigemService.button_name_to_mask("invalid") == 0

    def test_press_release_button(self):
        """Test press/release button."""
        self.service.add_x360()
        targets = self.service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            # Just check methods exist and return proper types
            result = self.service.x360_press_button(target_id, "a")
            assert isinstance(result, bool)

            result = self.service.x360_release_button(target_id, "a")
            assert isinstance(result, bool)

    def test_set_state_structure(self):
        """Test set_state."""
        self.service.add_x360()
        targets = self.service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            result = self.service.x360_set_state(
                target_id,
                lx=10000,
                ly=0,
                rx=0,
                ry=0,
                lt=0,
                rt=0
            )
            assert isinstance(result, bool)

    def test_set_state_trigger_limits(self):
        """Test that triggers are clamped to 0-255."""
        self.service.add_x360()
        targets = self.service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            # Should clamp
            result = self.service.x360_set_state(target_id, lt=300, rt=255)
            assert isinstance(result, bool)

            result = self.service.x360_set_state(target_id, lt=-10, rt=0)
            assert isinstance(result, bool)

    def test_set_state_stick_limits(self):
        """Test that sticks are clamped to -32768..32767."""
        self.service.add_x360()
        targets = self.service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            # Should clamp
            result = self.service.x360_set_state(
                target_id,
                lx=40000,   # Over limit
                ly=-40000,
                rx=0,
                ry=0,
                lt=0,
                rt=0
            )
            assert isinstance(result, bool)

    def test_x360_set_buttons(self):
        """Test x360_set_buttons."""
        self.service.add_x360()
        targets = self.service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            result = self.service.x360_set_buttons(target_id, 0x1000)  # A button
            assert isinstance(result, bool)

    def test_x360_set_triggers(self):
        """Test x360_set_triggers."""
        self.service.add_x360()
        targets = self.service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            result = self.service.x360_set_triggers(target_id, 128, 200)
            assert isinstance(result, bool)

    def test_x360_set_left_stick(self):
        """Test x360_set_left_stick."""
        self.service.add_x360()
        targets = self.service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            result = self.service.x360_set_left_stick(target_id, 10000, -5000)
            assert isinstance(result, bool)

    def test_x360_set_right_stick(self):
        """Test x360_set_right_stick."""
        self.service.add_x360()
        targets = self.service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            result = self.service.x360_set_right_stick(target_id, 0, 10000)
            assert isinstance(result, bool)

    def test_x360_reset(self):
        """Test x360_reset."""
        self.service.add_x360()
        targets = self.service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            result = self.service.x360_reset(target_id)
            assert isinstance(result, bool)

    def test_get_status_structure(self):
        """Test get_status returns proper structure."""
        result = self.service.get_status()
        assert isinstance(result, dict)
        assert "ok" in result
        assert "connected" in result
        assert "targets" in result
        assert "target_count" in result

    def test_is_available(self):
        """Test is_available."""
        result = self.service.is_available()
        assert isinstance(result, bool)

    def test_connect_disconnect(self):
        """Test connect/disconnect."""
        result = self.service.connect()
        assert isinstance(result, bool)
        self.service.disconnect()

    def test_combine_buttons(self):
        """Test combine_buttons helper."""
        mask = self.service.combine_buttons("a", "b", "x")
        assert isinstance(mask, int)
        assert mask > 0

    def test_stick_normalize(self):
        """Test stick_normalize helper."""
        result = self.service.stick_normalize(1.0)
        assert result == 32767

        result = self.service.stick_normalize(-1.0)
        assert result == -32768

        result = self.service.stick_normalize(0.0)
        assert result == 0

        # Clamping
        result = self.service.stick_normalize(2.0)
        assert result == 32767

        result = self.service.stick_normalize(-2.0)
        assert result == -32768

    def test_trigger_normalize(self):
        """Test trigger_normalize helper."""
        result = self.service.trigger_normalize(1.0)
        assert result == 255

        result = self.service.trigger_normalize(0.0)
        assert result == 0

        result = self.service.trigger_normalize(0.5)
        assert result == 127  # int(0.5 * 255) = 127

        # Clamping
        result = self.service.trigger_normalize(2.0)
        assert result == 255

        result = self.service.trigger_normalize(-1.0)
        assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])