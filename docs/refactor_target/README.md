# Refactor Target — Документация для будущего рефакторинга

> **Важно:** Файлы в этом каталоге — это **скелеты для будущего рефакторинга**.
> Они НЕ используются приложением напрямую.
>
> Текущее приложение работает с оригинальными файлами:
> - `app/backend/qml_bridge.py` (2077 LOC) — рабочий мост QML↔Python
> - `app/backend/services/hotkey_service.py` (1031 LOC) — рабочий сервис горячих клавиш
> - `app/ui/pages/GamepadPage.qml` (686 LOC) — рабочая страница геймпада

## 📁 Содержимое

### `bridges/` — скелет разделения qml_bridge.py

Цель: разбить God Object 2077 LOC на 12 файлов × 100-250 LOC.

| Файл | Описание |
|------|----------|
| `__init__.py` | QmlBridge фасад (множественное наследование миксинов) |
| `bridge_base.py` | Базовый класс: signals, _schedule_save, сервисы |
| `settings_bridge.py` | Settings методы (248 LOC) |
| `window_bridge.py` | Window + DWM acrylic методы |
| `clicker_bridge.py` | Clicker методы |
| `macro_bridge.py` | Macro методы + undo/redo (NEW) |
| `recorder_bridge.py` | Recorder методы |
| `aim_bridge.py` | Aim методы |
| `hotkeys_bridge.py` | Hotkeys методы |
| `gamepad_bridge.py` | ViGEm методы |
| `pico_bridge.py` | Pico HID методы |
| `overlay_bridge.py` | Overlay HUD методы |
| `diagnostics_bridge.py` | Diagnostics + Profiler методы |

### `hotkeys/` — скелет разделения hotkey_service.py

Цель: разбить 1031 LOC на 6 файлов × 150-250 LOC.

| Файл | Описание |
|------|----------|
| `__init__.py` | Экспорт HotkeyService фасада |
| `dispatcher.py` | HotkeyDispatcher + default_hotkeys |
| `bindings.py` | BindingStore (CRUD, потокобезопасный) |
| `validators.py` | KeyValidator (parse/validate) |
| `keyboard_hotkeys.py` | KeyboardHotkeyManager (pynput.keyboard) |
| `mouse_hotkeys.py` | MouseHotkeyManager (pynput.mouse) |
| `handlers.py` | ActionHandlers (toggle/start/stop) |
| `service.py` | Главный фасад HotkeyService |

### `gamepad_qml/` — скелет разделения GamepadPage.qml

Цель: разбить 686 LOC на 5 файлов × 100-200 LOC.

| Файл | Описание |
|------|----------|
| `GamepadPage.qml` | Главный контейнер (Flickable + ColumnLayout) |
| `GamepadStatusCard.qml` | Статус ViGEm + кнопки Start/Stop |
| `GamepadConfigCard.qml` | Выбор типа + target index |
| `GamepadMappingCard.qml` | Mapping keyboard→gamepad |
| `GamepadTestCard.qml` | Ручной тест sticks/triggers/buttons |

## 📖 Документы

- `PLAN.md` — Детальный 4-этапный план S→SSS
- `REFACTORING_GUIDE.md` — Правила безопасного рефакторинга (Strangler Fig Pattern)

## ⚠️ Статус готовности

| Компонент | Статус | Что осталось |
|-----------|--------|--------------|
| `bridges/bridge_base.py` | 🟡 80% | Перенести `_regenerate_palette_icon` (80 LOC) |
| `bridges/settings_bridge.py` | ✅ 100% | Готов к миграции |
| `bridges/window_bridge.py` | 🟡 90% | Протестировать DWM acrylic на Windows |
| `bridges/clicker_bridge.py` | ✅ 100% | Готов |
| `bridges/macro_bridge.py` | ✅ 100% | Готов (включая undo/redo — нужно реализовать в MacroService) |
| `bridges/recorder_bridge.py` | ✅ 100% | Готов |
| `bridges/aim_bridge.py` | ✅ 100% | Готов |
| `bridges/hotkeys_bridge.py` | ✅ 100% | Готов |
| `bridges/gamepad_bridge.py` | ✅ 100% | Готов |
| `bridges/pico_bridge.py` | ✅ 100% | Готов |
| `bridges/overlay_bridge.py` | ✅ 100% | Готов |
| `bridges/diagnostics_bridge.py` | ✅ 100% | Готов |
| `hotkeys/dispatcher.py` | ✅ 100% | Готов |
| `hotkeys/bindings.py` | ✅ 100% | Готов |
| `hotkeys/validators.py` | ✅ 100% | Готов |
| `hotkeys/keyboard_hotkeys.py` | 🟡 60% | Реализовать pynput listeners (60 LOC) |
| `hotkeys/mouse_hotkeys.py` | 🟡 70% | Реализовать mouse hook (40 LOC) |
| `hotkeys/handlers.py` | ✅ 100% | Готов |
| `hotkeys/service.py` | ✅ 100% | Готов |
| `gamepad_qml/*.qml` | ✅ 100% | Готовы (нужна интеграция в main.qml) |

## 🚀 Как активировать рефакторинг

### Этап 1: Активация bridges/

```bash
# 1. Скопировать скелеты в app/backend/bridges/
cp -r docs/refactor_target/bridges app/backend/

# 2. Заполнить TODO в bridge_base.py (перенести _regenerate_palette_icon из qml_bridge.py)

# 3. Обновить импорт в main.py:
# Было: from app.backend.qml_bridge import QmlBridge
# Стало: from app.backend.bridges import QmlBridge

# 4. Smoke-test
python run.py
# → приложение должно работать без изменений!

# 5. Заменить qml_bridge.py на thin re-export:
cat > app/backend/qml_bridge.py << 'EOF'
"""qml_bridge.py — Thin re-export for backward compatibility."""
from app.backend.bridges import QmlBridge  # noqa: F401
EOF
```

### Этап 2: Активация hotkeys/

```bash
# 1. Скопировать скелеты в app/backend/services/hotkeys/
cp -r docs/refactor_target/hotkeys app/backend/services/

# 2. Заполнить TODO в keyboard_hotkeys.py и mouse_hotkeys.py

# 3. Заменить hotkey_service.py на thin re-export:
cat > app/backend/services/hotkey_service.py << 'EOF'
"""hotkey_service.py — Thin re-export."""
from app.backend.services.hotkeys import HotkeyService, default_hotkeys  # noqa: F401
EOF

# 4. Smoke-test горячих клавиш (F6, F7, F8, F9, F10)
python run.py
```

### Этап 3: Активация gamepad_qml/

```bash
# 1. Скопировать в app/ui/pages/gamepad/
cp -r docs/refactor_target/gamepad_qml app/ui/pages/gamepad

# 2. Обновить import в main.qml (если GamepadPage импортируется через путь)

# 3. Smoke-test геймпада
python run.py
# → проверить все 4 карточки на вкладке Gamepad
```

См. `REFACTORING_GUIDE.md` для детальных инструкций и подводных камней.
