# REFACTORING_GUIDE.md — Правила безопасного рефакторинга Shira Lab

> **Цель:** Превратить God Objects (qml_bridge.py 2077 LOC, hotkey_service.py 1031 LOC)
> в модульную архитектуру без потери функциональности и без regressions.
>
> **Главный принцип:** **Strangler Fig Pattern** — постепенно "душим" старый код новым,
> пока от старого не останется только тонкая обёртка, которую можно безопасно удалить.

---

## 🎯 Золотые правила

### 1. ✅ Никогда не ломай QML API

Все @Slot-методы, которые вызывает QML, **ОБЯЗАНЫ** сохранить:
- Имя метода (точно)
- Сигнатуру (типы аргументов, порядок, результат)
- Возвращаемый JSON-формат

```python
# Было (в qml_bridge.py):
@Slot(int, int, str, int, str, result=str)
def setClickerConfig(self, interval_ms, hold_ms, button, limit, background_method):
    status = self.clicker.update_config(...)
    return json.dumps(status)

# Стало (в clicker_bridge.py):
@Slot(int, int, str, int, str, result=str)
def setClickerConfig(self, interval_ms, hold_ms, button, limit, background_method):
    # ← Точная копия сигнатуры!
    status = self.clicker.update_config(...)
    self._schedule_save()
    self.clickerStatusChanged.emit()  # ← доп. signal — ОК, QML это любит
    return json.dumps(status)
```

### 2. ✅ Один коммит — один шаг

| Коммит | Что меняется | Что НЕ меняется |
|--------|-------------|-----------------|
| #1 | Создать `bridges/__init__.py` (пустой) | Всё остальное |
| #2 | Создать `bridge_base.py` + `settings_bridge.py` | QmlBridge остаётся монолитом |
| #3 | Перенести методы Settings в `SettingsBridge` | QmlBridge делегирует через наследование |
| #4 | Удалить перенесённые методы из `qml_bridge.py` | QML работает без изменений |
| ... | ... | ... |

### 3. ✅ Тест перед удалением

```bash
# 1. Перед удалением метода из qml_bridge.py:
pytest tests/unit/test_settings_bridge.py -v

# 2. Запустить smoke-test приложения:
python run.py

# 3. Вручную проверить: открыть Settings → сменить палитру → проверить
# 4. Только после этого — git rm и коммит
```

### 4. ✅ Worklog обязателен

Каждый коммит рефакторинга описывается в `/home/z/my-project/worklog.md`:
```markdown
---
Task ID: 1.3-settings
Agent: main
Task: Перенос Settings методов из qml_bridge.py в SettingsBridge

Work Log:
- Создан app/backend/bridges/settings_bridge.py (248 LOC)
- Перенесено 12 @Slot-методов
- QmlBridge теперь наследует SettingsBridge
- Запущены тесты — все зелёные
- Smoke-test: запуск → Settings → смена палитры → ОК

Stage Summary:
- qml_bridge.py: 2077 → 1829 LOC (-248)
- bridges/settings_bridge.py: 248 LOC (новый)
- QML API не изменился, регрессий нет
```

---

## 🔄 Процесс: разделение qml_bridge.py

### Шаг 0: Подготовка (готово в этом запуске)

- [x] Создать `app/backend/bridges/` директорию
- [x] Создать скелеты 12 файлов (`bridge_base.py`, `settings_bridge.py`, ...)
- [x] Создать `__init__.py` с `QmlBridge`-фасадом

### Шаг 1: Перенос BridgeBase

**Цель:** Вынести общую инфраструктуру (signals, _schedule_save, log, __init__ с сервисами).

```bash
# 1. Скопировать в bridge_base.py:
#    - Все Signal declarations (statusChanged, clickerStatusChanged, ...)
#    - __init__ с созданием сервисов (clicker, macro, aim, ...)
#    - _schedule_save, _flush_save, saveProfileNow
#    - log, logMessageSlot
#    - set_app_hwnd, set_overlay_hwnd

# 2. Проверить, что bridge_base.py компилируется:
python -c "from app.backend.bridges.bridge_base import BridgeBase; print('OK')"

# 3. ВАЖНО: НЕ удалять эти методы из qml_bridge.py ещё!
```

### Шаг 2: Перенос SettingsBridge

```bash
# 1. Скопировать в settings_bridge.py:
#    - getSettings, setTerminalPalette, setUiLang
#    - setGlobalTransparency, setInterfaceTransparency
#    - setGlobalBlurEnabled, setInterfaceBlurEnabled
#    - setBgFitMode, chooseBackgroundImage, clearBackgroundImage
#    - saveGameProfile, loadGameProfile, listGameProfiles, deleteGameProfile

# 2. В settings_bridge.py класс наследует BridgeBase:
class SettingsBridge(BridgeBase):
    ...

# 3. В qml_bridge.pyclass QmlBridge заменить на:
class QmlBridge(SettingsBridge, BridgeBase):  # ← добавили SettingsBridge
    pass  # ← пустое тело, всё наследовано

# 4. Удалить из qml_bridge.py дубликаты перенесённых методов

# 5. Тест:
python -c "from app.backend.qml_bridge import QmlBridge; b = QmlBridge(); print(b.getSettings())"
# Должен вернуть JSON с настройками
```

### Шаг 3: Перенос остальных доменов

Повторить шаг 2 для каждого моста:
- `WindowBridge` → window management методы
- `ClickerBridge` → clicker методы
- `MacroBridge` → macro методы
- `RecorderBridge` → recorder методы
- `AimBridge` → aim методы
- `HotkeysBridge` → hotkey методы
- `GamepadBridge` → vigem методы
- `PicoBridge` → pico методы
- `OverlayBridge` → overlay методы
- `DiagnosticsBridge` → diagnostics методы

### Шаг 4: Удаление старого qml_bridge.py

Когда все методы перенесены:
```bash
# 1. qml_bridge.py должен быть пустым (только docstring)
wc -l app/backend/qml_bridge.py  # должно быть < 20 строк

# 2. Заменить содержимое на thin re-export:
cat > app/backend/qml_bridge.py << 'EOF'
"""qml_bridge.py — Thin re-export для обратной совместимости.

Реальная реализация: app/backend/bridges/
"""
from app.backend.bridges import QmlBridge  # noqa: F401
EOF

# 3. Обновить main.py (если нужно):
# from app.backend.qml_bridge import QmlBridge → from app.backend.bridges import QmlBridge

# 4. Полный smoke-test всех модулей
```

---

## 🔄 Процесс: разделение hotkey_service.py

Аналогично bridges, но с одним отличием: **HotkeyService не QObject**,
поэтому нет проблемы с множественным наследованием сигналов.

### Шаг 1: Перенос dispatcher.py

Перенести класс `HotkeyDispatcher` + `default_hotkeys()` (это уже готово в скелете).

### Шаг 2: Перенос bindings.py + validators.py

- `BindingStore` — простой класс, потокобезопасный (с lock)
- `KeyValidator` — статические методы

Это чистые функции/классы, легко тестируются unit-тестами.

### Шаг 3: Перенос keyboard_hotkeys.py + mouse_hotkeys.py

- `KeyboardHotkeyManager` — обёртка над `pynput.keyboard`
- `MouseHotkeyManager` — обёртка над `pynput.mouse` (clicks + wheel)

### Шаг 4: Перенос handlers.py

Все `_action_handler`, `_action_start_handler`, `_action_stop_handler` методы
становятся методами класса `ActionHandlers`.

### Шаг 5: Сборка фасада HotkeyService

```python
# app/backend/services/hotkeys/service.py
class HotkeyService:
    def __init__(self, api):
        self._dispatcher = HotkeyDispatcher()
        self._bindings = BindingStore()
        self._keyboard = KeyboardHotkeyManager(self._dispatcher)
        self._mouse = MouseHotkeyManager(self._dispatcher)
        self._handlers = ActionHandlers(api)
        # ...
```

### Шаг 6: Удаление старого hotkey_service.py

```bash
# Заменить на thin re-export:
cat > app/backend/services/hotkey_service.py << 'EOF'
"""hotkey_service.py — Thin re-export для обратной совместимости."""
from app.backend.services.hotkeys import HotkeyService, default_hotkeys  # noqa: F401
EOF
```

---

## 🧪 Тестирование рефакторинга

### Unit-тесты на каждый новый модуль

```python
# tests/unit/test_bindings.py
def test_set_and_get(binding_store):
    binding_store.set("clicker_toggle", "f6", "TOGGLE")
    b = binding_store.get("clicker_toggle")
    assert b == {"key": "f6", "mode": "TOGGLE"}

def test_reset(binding_store):
    binding_store.set("clicker_toggle", "x", "TOGGLE")
    result = binding_store.reset("clicker_toggle")
    assert result["ok"]
    assert result["binding"]["key"] == "f6"  # дефолт

def test_reset_all(binding_store):
    result = binding_store.reset_all()
    assert result["ok"]
    assert "clicker_toggle" in result["bindings"]

# tests/unit/test_validators.py
def test_parse_simple_key():
    p = KeyValidator.parse_key_string("a")
    assert p["main"] == "a"
    assert p["modifiers"] == []
    assert p["type"] == "keyboard"

def test_parse_combo():
    p = KeyValidator.parse_key_string("ctrl+shift+a")
    assert p["modifiers"] == ["ctrl", "shift"]
    assert p["main"] == "a"
    assert p["type"] == "keyboard"

def test_parse_mouse():
    p = KeyValidator.parse_key_string("mouse4")
    assert p["type"] == "mouse"
    assert p["main"] == "mouse4"

def test_parse_wheel():
    p = KeyValidator.parse_key_string("wheel_up")
    assert p["type"] == "wheel"

def test_validate_invalid():
    r = KeyValidator.validate_key("", "TOGGLE")
    assert not r["ok"]
    r = KeyValidator.validate_key("ctrl", "TOGGLE")
    assert not r["ok"]
    r = KeyValidator.validate_key("xyz_invalid", "TOGGLE")
    assert not r["ok"]
```

### Bridge regression tests

```python
# tests/integration/test_bridge_regression.py
"""Проверка, что все @Slot-методы, которые вызывает QML, на месте."""

import inspect
from app.backend.bridges import QmlBridge

EXPECTED_SLOTS = [
    "getSettings", "setTerminalPalette", "setUiLang",
    "getClickerStatus", "startClicker", "stopClicker",
    "getMacroStatus", "addMacroAction", "startMacro", "stopMacro",
    "recorderStatus", "recorderStart", "recorderStop", "recorderPlay",
    "aimStatus", "aimStart", "aimStop", "aimSetConfig",
    "getHotkeys", "setHotkey", "resetHotkey", "resetAllHotkeys",
    "getVigemStatus", "startVigem", "stopVigem", "vigemSetGamepadState",
    "getPicoStatus", "picoSendKey", "picoSendMouse",
    "getHwnd", "toggleWindowPin", "windowMinimize", "windowClose",
    "getDiagnostics", "panicStop",
    # ... полный список
]

def test_all_slots_exist():
    for slot_name in EXPECTED_SLOTS:
        assert hasattr(QmlBridge, slot_name), f"Missing @Slot: {slot_name}"

def test_slot_signatures_unchanged():
    """Проверка сигнатур через inspect."""
    sig = inspect.signature(QmlBridge.startClicker)
    # ... assertions
```

---

## ⚠️ Подводные камни

### 1. MRO (Method Resolution Order) при множественном наследовании

```python
# ❌ Плохо — конфликт __init__:
class QmlBridge(SettingsBridge, WindowBridge, ...):
    pass

# Если каждый мост имеет свой __init__, Python вызовет только первый!
# Решение: ВСЕ мосты наследуют BridgeBase, и только BridgeBase имеет __init__.
# Мосты — это просто наборы @Slot-методов, без состояния.
```

### 2. Signal declarations

```python
# ❌ Плохо — signals в каждом мосту:
class SettingsBridge(BridgeBase):
    settingsChanged = Signal()  # ← конфликтует с BridgeBase.settingsChanged!

# ✅ Хорошо — все signals в BridgeBase:
class BridgeBase(QObject):
    settingsChanged = Signal()
    clickerStatusChanged = Signal()
    # ... все signals здесь

class SettingsBridge(BridgeBase):
    # нет своих signals
    @Slot(result=str)
    def getSettings(self):
        ...
        self.settingsChanged.emit()  # ← emit сигнал из BridgeBase
```

### 3. Доступ к self.state, self.clicker, etc.

```python
# ✅ Хорошо — BridgeBase.__init__ создаёт все сервисы:
class BridgeBase(QObject):
    def __init__(self):
        self.clicker = ClickerService()
        self.macro = MacroService()
        # ...
        self.state = RuntimeState()

# Все мосты автоматически имеют доступ:
class ClickerBridge(BridgeBase):
    @Slot(result=str)
    def startClicker(self):
        # self.clicker доступен!
        return json.dumps(self.clicker.start())
```

### 4. DWM Acrylic и platform-specific код

`dwm_acrylic.py` импортирует `ctypes.windll` — на Linux это упадёт.
**Решение:** Lazy import внутри метода, не на уровне модуля.

```python
# ❌ Плохо — упадёт на Linux при import:
from app.backend.services.dwm_acrylic import enable_acrylic_blur

# ✅ Хорошо — lazy import:
def _apply_transparency(self):
    try:
        from app.backend.services.dwm_acrylic import enable_acrylic_blur
        enable_acrylic_blur(self._hwnd, ...)
    except Exception:
        pass
```

### 5. Tests на non-Windows

```python
# conftest.py уже мокает ctypes.windll на Linux/macOS.
# Но если в коде есть `import ctypes; ctypes.windll.user32.X` напрямую
# (без try/except) — тесты упадут.

# ✅ Хорошо:
try:
    ctypes.windll.user32.GetCursorPos(...)
except (AttributeError, OSError):
    # на non-Windows
    return default
```

---

## 📊 Чек-лист готовности к коммиту рефакторинга

- [ ] Все @Slot-методы на месте (проверено regression тестом)
- [ ] Сигнатуры @Slot не изменились (типы аргументов, результат)
- [ ] JSON-формат ответов не изменился
- [ ] Все signals испускаются в тех же случаях, что и раньше
- [ ] Smoke-test: launch → clicker start/stop → aim start/stop → macro → recorder → quit
- [ ] Hotkeys: F6 toggle clicker, F7 toggle aim, F8/F9 macro, F10 recorder — все работают
- [ ] `pytest --cov=app --cov-fail-under=85` проходит
- [ ] `ruff check .` без ошибок
- [ ] Worklog обновлён
- [ ] qml_bridge.py уменьшился (или стал thin re-export)
- [ ] Ни одного TODO без описания issue

---

## 🎯 Метрики успеха рефакторинга

| Метрика | До | После |
|---------|----|----|
| `qml_bridge.py` LOC | 2077 | < 50 (thin re-export) |
| `hotkey_service.py` LOC | 1031 | < 50 (thin re-export) |
| Макс. LOC в одном bridge файле | 2077 | < 300 |
| Макс. LOC в одном hotkeys файле | 1031 | < 350 |
| Количество файлов backend | 18 | 32 |
| Test coverage на bridges | 0% | > 85% |
| Количество @Slot на файл | 95 (в одном) | 5–15 (на мост) |
| Import time приложения | ~2.5s | < 2s (ленивая инициализация) |

---

## 🆘 Что делать, если что-то сломалось

### Сценарий 1: QML падает с "TypeError: Property 'startClicker' of object QmlBridge(...) is not a function"

**Причина:** Метод `startClicker` не наследовался (забыли добавить в наследование).

**Решение:**
```python
# app/backend/bridges/__init__.py
class QmlBridge(
    SettingsBridge,
    WindowBridge,
    ClickerBridge,  # ← добавьте, если забыли
    ...
):
    pass
```

### Сценарий 2: "AttributeError: 'QmlBridge' object has no attribute 'clicker'"

**Причина:** `BridgeBase.__init__` не вызывается (super().__init__ потерян).

**Решение:**
```python
class BridgeBase(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)  # ← обязательно для QObject
        self.clicker = ClickerService()
        # ...
```

### Сценарий 3: Hotkeys не работают после рефакторинга

**Причина:** `set_bindings` вызывает `_register_action`, который не находит handlers.

**Решение:** Проверить, что `ActionHandlers` правильно инициализирован с api (bridge).

### Сценарий 4: Coverage упала

**Причина:** Новый код не покрыт тестами.

**Решение:** Запустить `pytest --cov=app --cov-report=html` и посмотреть
непокрытые строки в `tests/_coverage_html/index.html`.

---

## 📚 Полезные ссылки

- [Strangler Fig Pattern (Martin Fowler)](https://martinfowler.com/bliki/StranglerFigApplication.html)
- [Python MRO documentation](https://docs.python.org/3/tutorial/classes.html#multiple-inheritance)
- [PySide6 Signals & Slots](https://doc.qt.io/qtforpython-6/signals-slots.html)
- [pytest-qt documentation](https://pytest-qt.readthedocs.io/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)

---

**Удачи в огранке алмаза! 💎**
