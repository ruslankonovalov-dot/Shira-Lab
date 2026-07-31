# Shira Lab v1.0.0 — Путь к SSS (Perfect Diamond)

> **Цель:** Превратить `rebuild_v016` из A+ (высокий Senior) в SSS (Google X / Moonshot).
> **Метод:** Поэтапная огранка — каждый этап поднимает рейтинг на полступени.
> **Срок:** 10–14 рабочих часов при фокусированной работе.

---

## 📊 Текущий аудит (фактическое состояние `rebuild_v016`)

| Файл | LOC | Проблема |
|------|-----|----------|
| `app/backend/qml_bridge.py` | **2077** | God Object, 95 @Slot, смешаны 7 доменов |
| `app/backend/services/hotkey_service.py` | **1031** | 62 метода, смешаны keyboard/mouse/wheel/global |
| `app/ui/pages/GamepadPage.qml` | **686** | Один файл: status + config + mapping + test |
| `app/backend/services/pico_service.py` | 662 | Нормально, но нет unit-тестов |
| `app/backend/services/aim_service.py` | 611 | `_worker` ~120 строк, нет отдельного detection thread |
| `app/backend/system_tray.py` | 431 | Опрашивает все сервисы каждую секунду |
| Тестов | 4 файла | Нет coverage метрики, нет QML тестов |
| CI/CD | отсутствует | — |
| `dwm_acrylic.py` | жив | Должен быть уже удалён (но импортируется) |

---

## 🗺️ Этап 1 — Критическая огранка (S → SS)

**Цель:** Уничтожить God Objects. Поднимает Архитектуру S→SSS, Качество S→SSS.
**Время:** 3–4 часа.

### 1.1. Разбить `qml_bridge.py` (2077 → 8 файлов × 200–300 LOC)

Создать пакет `app/backend/bridges/` со следующей структурой:

```
app/backend/bridges/
├── __init__.py                 # экспорт QmlBridge (главный фасад)
├── bridge_base.py              # BaseBridge(QObject) с общими: _schedule_save, log, signals
├── settings_bridge.py          # SettingsBridge: getSettings, setTerminalPalette, setUiLang, ...
├── window_bridge.py            # WindowBridge: getHwnd, windowDragMove, toggleWindowPin, ...
├── clicker_bridge.py           # ClickerBridge: getClickerStatus, startClicker, stopClicker, ...
├── macro_bridge.py             # MacroBridge: getMacroStatus, addMacroAction, startMacro, ...
├── recorder_bridge.py          # RecorderBridge: recorderStatus, recorderStart, recorderPlay, ...
├── aim_bridge.py               # AimBridge: aimStatus, aimStart, aimStop, aimSetConfig, ...
├── hotkeys_bridge.py           # HotkeysBridge: getHotkeys, setHotkey, resetHotkey, ...
├── gamepad_bridge.py           # GamepadBridge: getVigemStatus, vigemSetGamepadState, ...
├── pico_bridge.py              # PicoBridge: getPicoStatus, picoSendKey, picoSendMouse, ...
├── overlay_bridge.py           # OverlayBridge: toggleOverlayHUD, clampOverlayPosition, ...
└── diagnostics_bridge.py       # DiagnosticsBridge: getDiagnostics, panicStop, ...
```

`QmlBridge` (главный класс) остаётся тонким фасадом, который наследует все миксины:

```python
# app/backend/bridges/__init__.py
class QmlBridge(
    SettingsBridge, WindowBridge, ClickerBridge, MacroBridge,
    RecorderBridge, AimBridge, HotkeysBridge, GamepadBridge,
    PicoBridge, OverlayBridge, DiagnosticsBridge, BridgeBase,
):
    """Фасад: собирает все bridge-миксины в один QObject для QML."""
    pass
```

**Принципы:**
- Каждый миксин ≤ 250 LOC.
- Все сигналы — в `BridgeBase` (один источник правды).
- Все @Slot-методы сохраняют сигнатуры (QML не ломается).
- `_schedule_save`, `_suppress_save`, `_save_timer` — в `BridgeBase`, наследуются.
- Сервисы (`clicker`, `macro`, `aim`, ...) инициализируются в `QmlBridge.__init__` и доступны через `self.clicker`, `self.macro` и т.д.

**Файлы-скелеты уже подготовлены** в `/home/z/my-project/rebuild_v016/app/backend/bridges/`.

### 1.2. Разбить `hotkey_service.py` (1031 → 4 файла × 200–300 LOC)

```
app/backend/services/hotkeys/
├── __init__.py                 # экспорт HotkeyService (фасад)
├── dispatcher.py               # HotkeyDispatcher(QObject) + default_hotkeys()
├── keyboard_hotkeys.py         # KeyboardHotkeyManager: register/unregister keyboard bindings
├── mouse_hotkeys.py            # MouseHotkeyManager: hooks for click + wheel events
├── bindings.py                 # BindingStore: CRUD для bindings (set/get/reset)
├── validators.py               # validate_key, _parse_key_string, _is_modifier, ...
└── handlers.py                 # _action_handler, _action_start_handler, _action_stop_handler
```

`HotkeyService` становится фасадом, делегирующим вызовы менеджерам.

### 1.3. Разбить `GamepadPage.qml` (686 → 4 файла × 150–200 LOC)

```
app/ui/pages/gamepad/
├── GamepadPage.qml             # главный контейнер (Flickable + ColumnLayout)
├── GamepadStatusCard.qml       # статус ViGEm, target index, кнопка Start/Stop
├── GamepadConfigCard.qml       # выбор типа контроллера, target index
├── GamepadMappingCard.qml      # mapping keyboard→gamepad buttons
└── GamepadTestCard.qml         # ручной тест: sticks, triggers, buttons
```

### 1.4. Разбить функции >50 строк

| Функция | Файл | LOC | Что извлечь |
|---------|------|-----|-------------|
| `_worker` | `aim_service.py` | ~120 | `_detect_targets()`, `_smooth_aim()`, `_apply_mouse_move()` |
| `main` | `app/main.py` | 343 | `_create_app()`, `_load_qml()`, `_init_window()` |
| `_update_menu_states` | `system_tray.py` | ~50 | Разбить по сервисам |
| `_setup_tray` | `system_tray.py` | ~80 | `_build_clicker_menu()`, `_build_aim_menu()`, ... |
| `_flush_save` | `qml_bridge.py` | — | Уже маленькая, оставить |

### 1.5. Удалить `dwm_acrylic.py` (если действительно dead code)

```bash
# 1. Проверить, что ничего не импортирует после рефакторинга
rg "from.*dwm_acrylic|import.*dwm_acrylic" app/ --type py
# 2. Если пусто — удалить
rm app/backend/services/dwm_acrylic.py
```

⚠️ **Проверить**: в текущем `qml_bridge.py` есть `from ...dwm_acrylic import enable_acrylic_blur, disable_acrylic_blur`. Если acrylic реально используется для прозрачности окна — НЕ удалять, а вынести в отдельный модуль `app/backend/services/window_effects.py`.

---

## 🧪 Этап 2 — Тестовая огранка (SS → SS+)

**Цель:** Coverage >90%, QML тесты, integration/perf/stress.
**Время:** 2–3 часа.

### 2.1. Test infrastructure (УЖЕ ПОДГОТОВЛЕНО)

Файлы готовы в `rebuild_v016/`:
- `pytest.ini` — конфиг pytest с markers + addopts
- `conftest.py` — общие fixtures: `bridge`, `tmp_profile`, `mock_service`
- `.coveragerc` — coverage конфиг (branch coverage, omit tests/ui)
- `tests/__init__.py`, `tests/conftest.py`

Запуск:
```bash
cd rebuild_v016
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### 2.2. Unit-тесты (цель: 90% coverage на services)

| Модуль | Тест-файл | Что покрывать |
|--------|-----------|---------------|
| `clicker_service` | `tests/unit/test_clicker.py` | start/stop/config/burst/limit |
| `macro_service` | `tests/unit/test_macro.py` | add_action/clear/parallel/sequential |
| `recorder_service` | `tests/unit/test_recorder.py` | record/play/delete/list |
| `aim_service` | `tests/unit/test_aim.py` | config/region/detection modes (mock CV) |
| `hotkey_service` | `tests/unit/test_hotkeys.py` | validate_key/parse/normalize |
| `persistence` | `tests/unit/test_persistence.py` | save/load/roundtrip |
| `input_validation` | `tests/unit/test_input_validation.py` | sanitize/validate ranges |

### 2.3. Bridge tests (после рефакторинга)

```python
# tests/unit/test_bridges.py
def test_settings_bridge_set_palette(qtbot, bridge):
    bridge.setTerminalPalette("cyberpunk")
    assert bridge.state.terminal_palette == "cyberpunk"

def test_clicker_bridge_start_stop(qtbot, bridge, mock_clicker):
    bridge.startClicker()
    assert mock_clicker.start.called
```

### 2.4. QML тесты (QtTest)

```
tests/qml/
├── tst_TermButton.qml       # click signal, enabled state
├── tst_Card.qml             # title/text binding
├── tst_ToggleSwitch.qml     # checked state, toggled signal
├── tst_HotkeyRow.qml        # display binding, clear button
└── run_qml_tests.py         # pytest-qt wrapper
```

### 2.5. Integration тесты

```python
# tests/integration/test_clicker_cycle.py
def test_clicker_full_cycle(qtbot, bridge):
    """Start → action → stop без ошибок."""
    bridge.setClickerConfig(100, 30, "left", 0, "sendinput")
    status = json.loads(bridge.startClicker())
    assert status["ok"]
    qtbot.wait(500)
    status = json.loads(bridge.stopClicker())
    assert status["ok"]
```

### 2.6. Performance & stress тесты

```python
# tests/perf/test_clicker_stress.py
def test_1000_clicks_benchmark(benchmark, clicker):
    benchmark(clicker.burst, count=1000)

def test_macro_1000_actions(macro):
    for i in range(1000):
        macro.add_action("a", 0.05, 0.03)
    assert len(macro.actions) == 1000
```

---

## 🎨 Этап 3 — UX огранка (SS+ → SSS)

**Цель:** Топовые UX-фичи уровня Google/Apple.
**Время:** 3–4 часа.

### 3.1. Tooltips на всех кнопках

```qml
// TermButton.qml
TermButton {
    text: "Start"
    ToolTip.text: "Запустить авто-кликер (F6)"
    ToolTip.visible: hovered
    ToolTip.delay: 500
}
```

Прогнать все .qml файлы и добавить `ToolTip.text` к каждому `TermButton`, `ToggleSwitch`, `HotkeyRow`.

### 3.2. Keyboard navigation

```qml
// main.qml
Window {
   Shortcut { sequence: "Tab"; onActivated: focusNextChild() }
    Shortcut { sequence: "Escape"; onActivated: windowClose() }
    Shortcut { sequence: "Ctrl+1"; onActivated: navRow.selectTab(0) }
    // ... Ctrl+2..7 для каждой вкладки
}
```

Каждая страница должна иметь `focus: true` и `activeFocusOnTab: true` на ключевых элементах.

### 3.3. Undo/Redo в Macro

```python
# app/backend/services/macro_service.py
class MacroService:
    def __init__(self):
        self._undo_stack = []
        self._redo_stack = []

    def add_action(self, key, delay, hold):
        action = {"key": key, "delay": delay, "hold": hold}
        self.actions.append(action)
        self._undo_stack.append(("add", action))
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack: return {"ok": False}
        op, action = self._undo_stack.pop()
        if op == "add":
            self.actions.remove(action)
            self._redo_stack.append(("add", action))
        return {"ok": True}

    def redo(self):
        if not self._redo_stack: return {"ok": False}
        op, action = self._redo_stack.pop()
        if op == "add":
            self.actions.append(action)
            self._undo_stack.append(("add", action))
        return {"ok": True}
```

В QML добавить кнопки Undo/Redo + горячие клавиши `Ctrl+Z` / `Ctrl+Y`.

### 3.4. Drag & Drop в Recorder

```qml
// RecorderPage.qml
ListView {
    model: records
    delegate: Rectangle {
        Drag.active: dragArea.drag.active
        Drag.hotSpot.x: width / 2
        Drag.hotSpot.y: height / 2
        MouseArea {
            id: dragArea
            anchors.fill: parent
            drag.target: parent
        }
    }
    DropArea {
        anchors.fill: parent
        onDropped: bridge.recorderReorder(drag.source.index, drop.target.index)
    }
}
```

### 3.5. Анимации перехода между вкладками

```qml
// main.qml
StackLayout {
    currentIndex: navRow.activeIndex
    Behavior on currentIndex {
        NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
    }
    // или использовать StackView с push/pop
}
```

### 3.6. Auto dark/light detection

```python
# app/backend/services/theme_detector.py
import winreg
def detect_windows_theme() -> str:
    """Возвращает 'dark' или 'light'."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "light" if value == 1 else "dark"
    except OSError:
        return "dark"
```

В SettingsPage добавить опцию "Auto (по системе)".

### 3.7. Export/Import JSON настроек

```python
# app/backend/profile_io.py
def export_profile(bridge, path: str) -> dict:
    data = {
        "version": "1.0",
        "terminal_palette": bridge.state.terminal_palette,
        "hotkeys": bridge.state.hotkeys,
        "clicker": bridge.clicker.get_status(),
        "macro": bridge.macro.get_status(),
        # ...
    }
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return {"ok": True}

def import_profile(bridge, path: str) -> dict:
    data = json.loads(Path(path).read_text())
    # применить данные к bridge.state и сервисам
    ...
```

### 3.8. Scheduled tasks

```python
# app/backend/services/scheduler_service.py
from apscheduler.schedulers.background import BackgroundScheduler
class SchedulerService:
    def __init__(self):
        self._sched = BackgroundScheduler()
        self._sched.start()

    def add_clicker_task(self, hour: int, minute: int, config: dict):
        self._sched.add_job(
            self._fire_clicker, 'cron',
            hour=hour, minute=minute, args=[config]
        )
```

---

## 🚀 Этап 4 — Production (SSS)

**Цель:** CI/CD, auto-update, crash reporting, i18n, plugin system.
**Время:** 4–5 часов.

### 4.1. CI/CD (УЖЕ ПОДГОТОВЛЕНО)

`.github/workflows/ci.yml` готов в `rebuild_v016/.github/workflows/`.

Воркфлоу включает:
- `lint` — `ruff check .` + `black --check`
- `test` — `pytest --cov=app --cov-report=xml` (pytest 3.10/3.11/3.12)
- `qmllint` — проверка QML файлов
- `build` — сборка .exe через PyInstaller (только на tag push)
- `release` — создание GitHub Release с .exe артефактом

### 4.2. Auto-update checker

```python
# app/backend/services/update_checker.py
import urllib.request, json, packaging.version
class UpdateChecker:
    LATEST_URL = "https://api.github.com/repos/shira/shira-lab/releases/latest"
    def check(self, current_version: str) -> dict:
        try:
            with urllib.request.urlopen(self.LATEST_URL, timeout=5) as r:
                data = json.loads(r.read())
            latest = data["tag_name"].lstrip("v")
            if packaging.version.parse(latest) > packaging.version.parse(current_version):
                return {"update_available": True, "version": latest, "url": data["html_url"]}
        except Exception:
            pass
        return {"update_available": False}
```

При старте: проверять в фоне, если есть обновление — показать баннер в HomePage.

### 4.3. Crash report sender

```python
# app/backend/services/crash_reporter.py
import sys, traceback, urllib.request, json
def install_crash_handler(version: str):
    def handler(exc_type, exc_value, tb):
        report = {
            "version": version,
            "platform": platform.platform(),
            "traceback": "".join(traceback.format_exception(exc_type, exc_value, tb)),
        }
        try:
            urllib.request.urlopen(
                urllib.request.Request(
                    "https://api.shira.lab/crash",
                    data=json.dumps(report).encode(),
                    headers={"Content-Type": "application/json"},
                ),
                timeout=5,
            )
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, tb)
    sys.excepthook = handler
```

⚠️ **Важно:** получить согласие пользователя (Privacy checkbox в Settings).

### 4.4. Performance profiler в Diagnostics

```python
# DiagnosticsPage.qml — добавить вкладку "Profiler"
// Показывает: FPS aim detection, clicker CPS actual, hotkey latency, memory usage
```

### 4.5. Multi-monitor support в overlay

```python
# app/backend/services/overlay_positioner.py
import ctypes
def get_monitor_rects() -> list[dict]:
    rects = []
    def callback(hMonitor, hdc, lprcMonitor, lParam):
        r = lprcMonitor.contents
        rects.append({"x": r.left, "y": r.top, "w": r.right - r.left, "h": r.bottom - r.top})
        return True
    ctypes.windll.user32.EnumDisplayMonitors(0, 0, ctypes.WINFUNCTYPE(...)(callback), 0)
    return rects
```

Overlay должен привязываться к монитору целевого окна, а не к primary.

### 4.6. i18n (RU + EN)

```python
# app/backend/i18n.py
TRANSLATIONS = {
    "RU": {"clicker.start": "Запустить", "clicker.stop": "Остановить", ...},
    "EN": {"clicker.start": "Start", "clicker.stop": "Stop", ...},
}
def tr(key: str, lang: str = "RU") -> str:
    return TRANSLATIONS.get(lang, {}).get(key, key)
```

В QML:
```qml
text: Bridge.tr("clicker.start")
```

### 4.7. API reference (sphinx autodoc)

```
docs/
├── conf.py
├── index.rst
└── api/
    ├── bridges.rst
    ├── services.rst
    └── models.rst
```

Запуск: `sphinx-build docs/ docs/_build/`

### 4.8. UML diagrams (PlantUML)

```
docs/diagrams/
├── architecture.puml       # компонентная диаграмма
├── bridges_class.puml      # диаграмма классов bridges
├── clicker_sequence.puml   # sequence: user → bridge → service → win32
└── hotkey_flow.puml        # statechart: hotkey press → dispatch → action
```

### 4.9. Plugin system

```python
# app/backend/plugins/
├── __init__.py
├── plugin_manager.py       # загрузка плагинов из ~/.shira/plugins/
├── plugin_api.py           # API для плагинов (hooks: on_click, on_aim, ...)
└── example_plugin.py       # пример: logging plugin
```

---

## ✅ Готовые артефакты (подготовлены в этом запуске)

| Артефакт | Путь | Готовность |
|----------|------|------------|
| **PLAN.md** (этот документ) | `download/shira_sss_plan/PLAN.md` | 100% |
| **REFACTORING_GUIDE.md** | `download/shira_sss_plan/REFACTORING_GUIDE.md` | 100% |
| **pytest.ini** | `rebuild_v016/pytest.ini` | 100% |
| **conftest.py** | `rebuild_v016/conftest.py` | 100% |
| **.coveragerc** | `rebuild_v016/.coveragerc` | 100% |
| **tests/conftest.py** | `rebuild_v016/tests/conftest.py` | 100% |
| **CI workflow** | `rebuild_v016/.github/workflows/ci.yml` | 100% |
| **PR template** | `rebuild_v016/.github/PULL_REQUEST_TEMPLATE.md` | 100% |
| **Bug report template** | `rebuild_v016/.github/ISSUE_TEMPLATE/bug_report.md` | 100% |
| **Feature request template** | `rebuild_v016/.github/ISSUE_TEMPLATE/feature_request.md` | 100% |
| **Bridges skeleton** | `rebuild_v016/app/backend/bridges/` | Скелеты 12 файлов |
| **Hotkeys skeleton** | `rebuild_v016/app/backend/services/hotkeys/` | Скелеты 6 файлов |
| **Gamepad QML skeleton** | `rebuild_v016/app/ui/pages/gamepad/` | Скелеты 4 карточек |
| **Theme detector** | `rebuild_v016/app/backend/services/theme_detector.py` | 100% |
| **Profile I/O** | `rebuild_v016/app/backend/profile_io.py` | 100% |
| **Update checker** | `rebuild_v016/app/backend/services/update_checker.py` | 100% |
| **Crash reporter** | `rebuild_v016/app/backend/services/crash_reporter.py` | 100% |
| **i18n module** | `rebuild_v016/app/backend/i18n.py` | 100% |
| **requirements-dev.txt** | `rebuild_v016/requirements-dev.txt` | 100% |

---

## 🎯 Порядок внедрения (рекомендация)

```
День 1 (4 ч):
  09:00–11:00  Этап 1.1 — Разбить qml_bridge.py (использовать скелеты)
  11:00–12:00  Этап 1.2 — Разбить hotkey_service.py
  14:00–15:00  Этап 1.3 — Разбить GamepadPage.qml
  15:00–16:00  Этап 1.4 — Разбить длинные функции

День 2 (4 ч):
  09:00–11:00  Этап 2.1–2.3 — Unit-тесты (использовать conftest.py)
  11:00–12:00  Этап 2.4 — QML тесты
  14:00–15:00  Этап 2.5 — Integration тесты
  15:00–16:00  Этап 2.6 — Perf + stress тесты

День 3 (4 ч):
  09:00–11:00  Этап 3.1–3.4 — Tooltips, keyboard nav, undo/redo, drag&drop
  11:00–12:00  Этап 3.5–3.6 — Анимации, auto dark/light
  14:00–16:00  Этап 3.7–3.8 — Export/Import, scheduled tasks

День 4 (4 ч):
  09:00–10:00  Этап 4.1 — Подключить CI (push → check)
  10:00–11:00  Этап 4.2–4.3 — Auto-update, crash reporter
  11:00–12:00  Этап 4.4–4.5 — Profiler, multi-monitor
  14:00–16:00  Этап 4.6–4.9 — i18n, sphinx, UML, plugins
```

**Итого:** ~16 рабочих часов → SSS.

---

## 🚨 Чек-лист перед каждым коммитом

- [ ] `pytest --cov=app --cov-fail-under=85` проходит
- [ ] `ruff check .` без ошибок
- [ ] `black --check .` без diff
- [ ] `qmllint-qt6 app/ui/**/*.qml` без критических ошибок
- [ ] Ручной smoke-test: launch → clicker → aim → macro → recorder → quit
- [ ] Worklog обновлён в `/home/z/my-project/worklog.md`
