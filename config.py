# config.py

LOGO_SHIRA = r"""███████╗██╗  ██╗██╗██████╗  █████╗
██╔════╝██║  ██║██║██╔══██╗██╔══██╗
███████╗███████║██║██████╔╝███████║
╚════██║██╔══██║██║██╔══██╗██╔══██║
███████║██║  ██║██║██║  ██║██║  ██║
╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝"""

LOGO_AIM = """╔════════════════════════════════════════╗
║   S H I R A   A I M   M O D U L E   ║
╚════════════════════════════════════════╝"""

DEFAULT_LANG = "RU"
DEFAULT_FONT = "Consolas"

FONTS = [DEFAULT_FONT, "Courier New"]

RU_LANGUAGE = {
    "tab_home": "ГЛАВНАЯ",
    "tab_aim": "БОЕВАЯ СИСТЕМА",
    "tab_clicker": "КЛИКЕР",
    "tab_settings": "НАСТРОЙКИ",
    "btn_run": "[ ЗАПУСТИТЬ ПРОТОКОЛ ]",
    "btn_stop": "[ АВАРИЙНАЯ ОСТАНОВКА ]",
    "conf_label": "ПОРОГ СРАБАТЫВАНИЯ",
    "smooth_label": "ИНЕРЦИЯ КУРСОРА",
    "reset_label": "ЗАДЕРЖКА СБРОСА",
    "lang_select": "ЯЗЫКОВОЙ ПАКЕТ",
    "theme_select": "ЦВЕТОВАЯ СХЕМА",
    "click_speed": "ИНТЕРВАЛ ЦИКЛА (ms)",
    "btn_click_run": "[ ЗАПУСТИТЬ КЛИКЕР ]",
    "btn_click_stop": "[ ОСТАНОВИТЬ КЛИКЕР ]",
    "status_ready": "СИСТЕМА ГОТОВА",
    "tab_recorder": "ЗАПИСЬ",
    "tab_macro": "МАКРОСЫ",
    "target_section": "ЦЕЛЕВОЕ ОКНО (ФОНОВЫЙ ВВОД)",
    "target_hint": "Куда направлять клики и клавиши.",
    "target_btn": "[ ВЫБРАТЬ ОКНО ]",
    "target_current": "Сейчас:",
}

EN_LANGUAGE = {
    "tab_home": "HOME",
    "tab_aim": "AIM MODULE",
    "tab_clicker": "CLICKER",
    "tab_settings": "SETTINGS",
    "btn_run": "[ RUN PROTOCOL ]",
    "btn_stop": "[ EMERGENCY STOP ]",
    "conf_label": "CONFIDENCE THRESHOLD",
    "smooth_label": "CURSOR INERTIA",
    "reset_label": "RESET DELAY",
    "lang_select": "LANGUAGE PACK",
    "theme_select": "COLOR SCHEME",
    "click_speed": "LOOP INTERVAL (ms)",
    "btn_click_run": "[ START CLICKER ]",
    "btn_click_stop": "[ STOP CLICKER ]",
    "status_ready": "SYSTEM READY",
    "tab_recorder": "RECORDER",
    "tab_macro": "MACROS",
    "target_section": "TARGET WINDOW (BACKGROUND INPUT)",
    "target_hint": "Where to send clicks/keys.",
    "target_btn": "[ SELECT WINDOW ]",
    "target_current": "Current:",
}

LANGUAGES = {"RU": RU_LANGUAGE, "EN": EN_LANGUAGE}
