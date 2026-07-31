# Shira Lab Architecture (PySide6)

## Runtime

- `run.py` — точка входа
- `app/main.py` — PySide6 QApplication + QQmlApplicationEngine, прозрачное окно через Qt
- `app/backend/qml_bridge.py` — мост QML↔Python (замена api.py)
- `app/backend/services/` — вся бизнес-логика (чистый Python, не зависит от UI)

## Folder Layout

```
shira_lab_qt/
├── run.py                      # точка входа
├── requirements.txt            # pip install -r requirements.txt
├── config.py                   # логотипы, шрифты, языки
├── utils.py                    # Win32 PostMessageW helpers
├── window_utils.py             # enum окон, topmost
├── app/
│   ├── main.py                 # PySide6 запуск
│   ├── backend/
│   │   ├── qml_bridge.py       # мост QML-Python
│   │   ├── persistence.py      # save/load profile.json
│   │   ├── models/
│   │   │   └── runtime_state.py
│   │   └── services/
│   │       ├── aim_service.py
│   │       ├── clicker_service.py
│   │       ├── dwm_acrylic.py  # DWM acrylic для Qt HWND
│   │       ├── hotkey_service.py
│   │       ├── macro_service.py
│   │       ├── recorder_service.py
│   │       └── stealth_input.py
│   └── ui/
│       ├── main.qml            # главное окно
│       ├── Theme.qml           # палитры
│       ├── components/
│       │   ├── ChromeBar.qml   # верхняя шапка
│       │   ├── NavRow.qml      # навигация
│       │   ├── Card.qml        # карточка с vignette
│       │   ├── ToggleSwitch.qml
│       │   └── HotkeyRow.qml
│       └── pages/
│           ├── HomePage.qml
│           ├── AimPage.qml
│           ├── ClickerPage.qml
│           ├── MacroPage.qml
│           ├── RecorderPage.qml
│           ├── SettingsPage.qml
│           └── DiagnosticsPage.qml
├── data/profile.json
├── screenshots/                # шаблоны для aim
└── records/                    # записи recorder
```

## Запуск

```bash
pip install -r requirements.txt
python run.py
```

## Прозрачность

- Qt окно: `color: "transparent"` + `Qt.FramelessWindowHint`
- DWM Acrylic: `SetWindowCompositionAttribute(ACCENT_ENABLE_ACRYLICBLURBEHIND)` на Qt HWND
- Per-card vignette: QML Canvas с `createRadialGradient`
- Global blur: DWM acrylic с tint
- Interface blur: QML `layer.effect` с `GaussianBlur` (будущее улучшение)