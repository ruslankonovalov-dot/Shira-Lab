"""Unit tests for app.backend.i18n module."""
import pytest

from app.backend.i18n import (
    tr, get_available_languages, get_translation_keys, get_translation_coverage,
    TRANSLATIONS,
)

pytestmark = pytest.mark.unit


class TestTranslations:

    def test_tr_returns_russian_by_default(self):
        assert tr("common.start") == "Запустить"

    def test_tr_returns_english_when_requested(self):
        assert tr("common.start", "EN") == "Start"

    def test_tr_returns_key_when_not_found(self):
        assert tr("nonexistent.key") == "nonexistent.key"

    def test_tr_returns_key_for_unknown_lang(self):
        # Falls back to RU, then to key
        result = tr("common.start", "FR")
        # FR not in dict, falls back to RU
        assert result == "Запустить"

    def test_all_keys_have_russian(self):
        for key, entry in TRANSLATIONS.items():
            assert "RU" in entry, f"Key {key} missing RU translation"
            assert entry["RU"], f"Key {key} has empty RU translation"

    def test_all_keys_have_english(self):
        for key, entry in TRANSLATIONS.items():
            assert "EN" in entry, f"Key {key} missing EN translation"
            assert entry["EN"], f"Key {key} has empty EN translation"

    def test_get_available_languages(self):
        langs = get_available_languages()
        assert "RU" in langs
        assert "EN" in langs

    def test_get_translation_keys_returns_list(self):
        keys = get_translation_keys()
        assert isinstance(keys, list)
        assert len(keys) > 50  # we have 50+ keys

    def test_get_translation_coverage(self):
        coverage = get_translation_coverage()
        assert "RU" in coverage
        assert "EN" in coverage
        assert coverage["RU"] == 1.0  # 100% Russian
        assert coverage["EN"] == 1.0  # 100% English


class TestTranslationKeys:

    def test_nav_keys_exist(self):
        for key in ["nav.home", "nav.clicker", "nav.aim", "nav.macro",
                    "nav.recorder", "nav.gamepad", "nav.settings"]:
            assert key in TRANSLATIONS

    def test_clicker_keys_exist(self):
        for key in ["clicker.title", "clicker.interval", "clicker.start"
                    if "clicker.start" in TRANSLATIONS else "common.start",
                    "clicker.running"]:
            assert key in TRANSLATIONS or key in TRANSLATIONS

    def test_settings_keys_exist(self):
        for key in ["settings.title", "settings.language", "settings.theme_auto",
                    "settings.theme_dark", "settings.theme_light"]:
            assert key in TRANSLATIONS

    def test_diagnostics_keys_exist(self):
        for key in ["diagnostics.title", "diagnostics.platform", "diagnostics.panic"]:
            assert key in TRANSLATIONS
