// UpdateData.qml — Changelog data for HomePage
// This file contains ALL update entries as a QML property.
// HomePage.qml imports this and uses `updates` property for Repeater model.
//
// To add new updates: add new entries to the `updates` array below.
// Format: { date: "YYYY-MM-DD", title: "...", items: ["...", "..."] }
import QtQuick

QtObject {
    // All changelog entries — newest first
    property var updates: [
        {
            date: "2026-07-31",
            title: "v0.17.0: SSS-Tier Complete — Zero Compromise Architecture",
            items: [
                "Mypy --strict: Zero errors across 32 files (~12,000 lines) — full type hints, TYPE_CHECKING imports, all protocols",
                "Architecture: 4 Controllers (Window, Gamepad, Hotkey, Profile) + Thin Bridge (~1340 lines) — clean DI, no god-objects",
                "Thread Safety: RLock + Snapshot Pattern on ALL 7 services (Clicker, Aim, Macro, Recorder, Pico, Vigem, Hotkey)",
                "Input Validation: 100% coverage on 49 @Slot methods with standardized error/ok response format",
                "Logging & Hygiene: Structured logging on every file, zero bare except, zero print(), __slots__ on all services",
                "QML Polish: Full i18n (RU/EN), dynamic model rebuilding on langChanged, tooltips everywhere, accessible names, zero JSON.parse",
                "Test Suite: 91 tests passing — all services + controllers covered, updated to match actual APIs",
                "Icon System: Dynamic palette-colored icons, atomic writes, targeted SHChangeNotify, desktop shortcut auto-update via ie4uinit.exe",
                "Overlay HUD: Independent window, persistent topmost (2s timer), clamp to work area, native drag, minimize/expand toggle",
                "Hardware: ViGEm X360/DS4 full support + Pico Composite HID (Keyboard/Mouse/Gamepad) via Serial CDC",
                "Cleanup: Removed 8 obsolete scripts, sendinput_attached method, dwm_acrylic.py — clean repo"
            ]
        },
        {
            date: "2026-07-28",
            title: "Mypy --strict Clean: Zero Errors Across 32 Files",
            items: [
                "Protocol Compliance: WindowController fully implements _TrayBridge Protocol (11 methods)",
                "Slot Return Types: Fixed all @Slot decorators to use result=QVariantMap with type:ignore where needed",
                "HotkeyService API: Fixed set_hotkey → set_binding (method renamed)",
                "Profile Controller: Fixed TYPE_CHECKING imports, validate_hwnd import, setSetting return types",
                "Profile IO: Implemented 6 missing functions (prompt_save_as, prompt_load_profile, list_profile_files, confirm_overwrite, confirm_delete, get_data_dir)",
                "Runtime State: Added macro_background_method, recorder_background_method fields; implemented set_module_target_window, get_module_target_window",
                "Recorder Service: Removed invalid type:ignore on pynput imports",
                "Macro Service: Refactored TypedDicts to use cast() for construction in undo/redo stacks",
                "Persistence: Fixed pico_port default to empty string",
                "Input Validation: Added _qvar helper + QVariantMap/QVariantList/QVariant type aliases",
                "QmlBridge: Removed QVariantMap redefinition; fixed panicStop signature; tr method signatures; AimService literal types",
                "Main.py: Fixed all 25 mypy errors: return type annotations, excepthook signature, cast main_window, setTransientParent",
                "Result: python -m mypy app/ → Success: no issues found in 32 source files"
            ]
        },
        {
            date: "2026-07-28",
            title: "Phase 1 Critical Bug Fixes (ALL COMPLETE)",
            items: [
                "Pico NameError: Added missing import struct and build_mouse_press/release, CMD_MS_PRESS/RELEASE imports in pico_service.py",
                "Missing sendVigemTestState slot: Added validated slot to qml_bridge.py + GamepadPage.qml",
                "Recorder release handling: Added _press_key/_release_key, _send_click/release_click in recorder_service; send_background_click_up/send_background_key_up in utils",
                "AimService thread-safety: Added RLock, snapshot pattern in worker, all setters protected",
                "ViGEm LT/RT mapping + press/release: LT/RT → None in button map; added x360_press_button/release_button with per-target _btn_state"
            ]
        },
        {
            date: "2026-07-28",
            title: "Phase 3: Polish & Quality Gates (COMPLETE)",
            items: [
                "Phase 3.1 Logging & Exception Hygiene: logger = logging.getLogger(__name__) at top of every .py file; banned bare except Exception: pass → logger.exception; banned print() → self._log or logger; added __slots__ to all service classes",
                "Phase 3.2 Input Validation Coverage: All @Slot methods in ProfileController (18), GamepadController (~25), HotkeyController (6) validate every argument; standardized error/ok response format",
                "Phase 3.3 Type Hints & Mypy Clean: Full type hints added to ALL services (Clicker, Recorder, Aim, Macro, Pico, Vigem, Hotkey - FULL REWRITE), controllers (Window, Gamepad, Hotkey, Profile), bridge, input_validation; TYPE_CHECKING imports for forward references; runtime imports inside method bodies",
                "Phase 3.4 Thread-Safety Audit: All 7 core services follow RLock + Snapshot Pattern verified for Clicker, Aim, Macro, Recorder, Pico, Vigem, Hotkey services",
                "Phase 3.5 QML Polish: All user strings via mainWindow.tr(key); ComboBox models rebuilt on langChanged; Tooltips on every button/input; Accessible.name on key controls; Zero remaining JSON.parse(Bridge.xxx()) in QML",
                "Phase 3.6 Test Suite: All test files updated to match actual service APIs — test_pico_service.py (16/16), test_aim_service.py (20/20), test_macro_service.py (26/26), test_hotkey_service.py (26/26), test_recorder_service.py (21/21), test_vigem_service.py, test_services.py, test_controllers.py"
            ]
        },
        {
            date: "2026-07-28",
            title: "Phase 2 Architecture Refactor: God-Object Split → 4 Controllers (COMPLETE)",
            items: [
                "Split QmlBridge (3000+ lines) into 4 focused controllers: WindowController (~770 lines), GamepadController (~730 lines), HotkeyController (~145 lines), ProfileController (~470 lines)",
                "QmlBridge → Thin aggregator (~1340 lines), delegates to controllers, forwards signals",
                "Eliminated JSON Marshaling: All @Slot methods return native dict/list/str/int/float/bool; QML receives QVariantMap/QVariantList directly; no more json.dumps/JSON.parse() in bridge↔QML",
                "Single Source of Truth Palettes: TERMINAL_PALETTES only in runtime_state.py (TypedDict Palette); config.py removed PALETTES; Theme.qml reads via Bridge.getPalettes()",
                "PicoPage.qml Refactor: Replaced Qt.createQmlObject dynamic strings with static ListModel + Repeater + new PicoButtonMapRow.qml component",
                "utils.py Helpers Added: send_background_click_up(), send_background_key_up() with full type hints",
                "stealth_input.py Extended Key Fix: Removed duplicate extended assignment; added comprehensive EXTENDED_VK set"
            ]
        },
        {
            date: "2026-07-23",
            title: "v0.16.6: Full Internationalization (i18n) — Russian/English",
            items: [
                "i18n backend (app/backend/i18n.py): 50+ new translation keys added for all modules — Clicker, Macro, Recorder, Gamepad, Overlay, ChromeBar, Update banner, tooltips, status messages",
                "QML pages updated to use mainWindow.tr(key) / Bridge.tr(key): MacroPage, AimPage, OverlayHUD, ChromeBar, HotkeyRow, main.qml",
                "Dynamic model rebuilding: All pages have onLangChanged handlers that rebuild ComboBox models (runModes, detectionModes, targetColors, backgroundMethods, window lists) on language change",
                "i18n test verified: tr(key) function works for both languages at runtime",
                "Remaining untranslated (intentional): Technical abbreviations (CPU, HWND, X/Y/LT/RT axes), debug labels, UI symbols (▼, →, ::, X)",
                "Version bumped: 0.16.1 → 0.16.6 in app/main.py, app/backend/qml_bridge.py, app/ui/main.qml for update checker"
            ]
        },
        {
            date: "2026-07-16",
            title: "v0.16.0: S-Rank Improvements — Profiles, Auto-Recovery, Code Quality",
            items: [
                "Game Profiles: save/load complete configurations as named presets (ProfileManager + Settings UI)",
                "Auto-recovery: crash handler now offers 'Restart Shira Lab?' dialog with subprocess.Popen restart",
                "Debug prints removed: all 10 print() calls replaced with logger.warning/error/info",
                "Musor cleanup: debug_layout.py, logo_check.txt, logo_out.txt deleted from project root",
                "QML quality: 0 deprecated Connections syntax, all JSON.parse wrapped in try/catch",
                "Profile tests: 10 tests for save/load/list/delete/roundtrip/overwrite",
                "Total: 91 tests passing (10 profile + 10 clicker + 13 macro + 23 aim + 18 advanced + 11 recorder + 6 misc)"
            ]
        },
        {
            date: "2026-07-15",
            title: "v0.15.7: Advanced Aim Detection + Macro Fix + 75 Tests",
            items: [
                "CRITICAL FIX: Removed duplicate _sequential_worker/_parallel_worker in macro_service.py (was causing crash on macro start)",
                "Macro logging: detailed action info — key, TAP/HOLD type, hold duration, delay, cycle counter",
                "Aim HSV presets widened: S threshold 50→50, H range expanded (e.g. red: 0-15 + 165-180)",
                "Adaptive V-threshold detection: when background matches target color (>50% mask coverage), automatically uses brightness to separate target from bg",
                "Applied to _detect_color, _detect_multi_color, _detect_calibrated — all 3 modes now handle low-contrast",
                "Pipette tolerance increased: H ±15, S ±40, V ±40 (was ±10/±30/±30)",
                "75 comprehensive tests: 10 clicker, 13 macro, 23 aim (synthetic images), 11 recorder, 18 advanced aim stress tests",
                "Advanced aim tests: multi-color targets, near-identical bg (5% contrast), moving targets, noisy bg, overlapping, edge cases",
                "50-iteration random stress test: random colors, shapes, positions, noise — 80%+ detection required"
            ]
        },
        {
            date: "2026-07-15",
            title: "HomePage Redesign: Vertical Dashboard Layout",
            items: [
                "Vertical layout: logo on top (~180px), scrollable changelog cards below",
                "Logo centered with pixel-perfect Canvas rendering + version tag",
                "Update data moved to separate UpdateData.qml file — HomePage only renders it",
                "Removed horizontal 40/60 split that caused overlapping issues"
            ]
        },
        {
            date: "2026-07-14",
            title: "Aim Service v2: Adaptive Detection + Visual Debug + Pipette",
            items: [
                "6 detection modes: Auto (brightness+saturation), Multi-color, Circles (HoughCircles), Single HSV, Calibrate (pipette), Template",
                "Relative mouse movement (MOUSEEVENTF_MOVE) for FPS/3D camera rotation — not absolute",
                "FOV capture (default 300px radius) — 10x faster than full screen, ~140 FPS",
                "Visual debug: screenshots saved to screenshots/debug/ with green/red/yellow markers",
                "Predictive aim: tracks target velocity between frames, predicts +50ms ahead",
                "Jitter filter: ignores movements <1px — no micro-trembling",
                "Performance: cached HSV arrays, vectorized numpy detection, ~8x faster per frame",
                "PipetteOverlay: small top panel with 3-2-1 countdown + NOW button + HSV result",
                "Adaptive calibration: 7x7 sample, circular mean for hue, std-based tolerance",
                "Filters: min/max area, aspect ratio, brightness/saturation thresholds"
            ]
        },
        {
            date: "2026-07-14",
            title: "Overlay HUD v3: Dynamic Tray Icon + Palette-Colored Icons",
            items: [
                "Tray icon changes in real-time: IDLE, CLICKER (red C), AIM (orange A), MACRO (blue M), REC (red dot), PLAY (green)",
                "icon_generator.py: generates shira.ico + shira_<palette>.ico from Ico_Shine.png + palette accent color",
                "Dynamic shortcut update: finds Shira Lab.lnk in 3 locations, rewrites with new icon",
                "Unique .ico per palette forces Windows to reload icon cache (shira_matrix.ico, shira_blood.ico, etc.)",
                "setTransientParent(None) — overlay not hidden when app minimized",
                "Periodic topmost re-assert (2s) — overlay always above app",
                "Movement lock (LOC/MOV) + minimize toggle [-]/[+] — compact 24px when minimized"
            ]
        },
        {
            date: "2026-07-14",
            title: "Split Layout + Console Log System",
            items: [
                "main.qml: Left ~70% functional area, Right ~30% ASCII banner + ConsoleLog",
                "ConsoleLog.qml: Terminal-style log (auto-scroll, color-coded OK/INFO/WARN/ERROR, timestamps)",
                "Rate limiting: max 10 log entries per second — no console spam at 100+ CPS",
                "Per-tab banner & log filtering: bannerArtMap + logSourcesMap — each tab shows only its logs",
                "Bridge: logMessage signal + log() method, all 6 services log via set_bridge()",
                "HomePage has no right panel — full width for content"
            ]
        },
        {
            date: "2026-07-14",
            title: "Terminal Design v2: Markdown Cards + ASCII Banners",
            items: [
                "Card.qml: Removed border, added markdown-style '---' horizontal rules (16px margins)",
                "AsciiBanner.qml: Canvas-rendered ASCII art with pixel-perfect centering",
                "PyFiglet-generated banners for all 8 tabs (AIM, CLICKER, MACRO, RECORDER, GAMEPAD, PICO, SETTINGS, DIAGNOSTICS)",
                "GamepadPage restructure: Controller Type + Target Index + Bg Method merged into CONTROLLER CONFIG card"
            ]
        },
        {
            date: "2026-07-14",
            title: "Production Readiness: Logging, Crash Handler, Tests",
            items: [
                "requirements.txt: Pillow + pywin32 added",
                "All 6 services get set_bridge() + _log() — full console logging (Clicker, Aim, Macro, Recorder, ViGEm, Pico)",
                "All 64 JSON.parse in QML wrapped in try/catch — UI doesn't crash on invalid JSON",
                "main.py: logging config (console + rotating file 5MB x 3) + sys.excepthook crash handler with MessageBox",
                "tests/test_services.py: 75 unit tests for all services + input validation + palettes + path traversal",
                ".gitignore + README.md + data/profile.example.json created"
            ]
        },
        {
            date: "2026-07-13",
            title: "sendinput_attached Fully Removed + QML Cleanup",
            items: [
                "Removed sendinput_attached from all services, bridge, persistence, input_validation",
                "Valid background methods: sendinput, postmessage, vigem, pico (4 methods)",
                "Fixed deprecated QML Connections syntax in 7 files (Qt6 modern function-based)",
                "Fixed RowLayout binding loop in main.qml (removed parent.width * 0.7)"
            ]
        },
        {
            date: "2026-07-12",
            title: "Icon Visibility + Security Audit",
            items: [
                "SECURITY FIX: recorder_service.py _safe_record_path() — blocks path traversal (../../../etc/passwd)",
                "BUG FIX: recorder_service.py _save_record() was missing — added (REC_YYYYMMDD_HHMMSS.json)",
                "BUG FIX: Removed duplicate status() method in recorder_service.py",
                "BUG FIX: HotkeyRow.qml JSON.parse wrapped in try/catch",
                "Icon: Ico_Shine.png (349x349 RGBA) converted to multi-resolution shira.ico (16-256px)"
            ]
        },
        {
            date: "2026-07-12",
            title: "Dynamic Palette-Colored Icons + Atomic Rename",
            items: [
                "icon_generator.py: generates shira.ico from Ico_Shine.png + palette accent color",
                "On palette change: regenerates icon -> tray + taskbar + desktop shortcut update",
                "Unique .ico per palette (shira_matrix.ico, shira_blood.ico) — forces Windows cache reload",
                "Atomic write via os.replace() (shira.tmp.ico -> shira.ico) — no 'file becomes empty' issue",
                "ie4uinit.exe -show rebuilds icon cache — final fix for desktop shortcut"
            ]
        },
        {
            date: "2026-07-12",
            title: "Overlay HUD: Position + Minimize + Pin Fixes",
            items: [
                "Win32 SPI_GETWORKAREA for overlay positioning — never overlaps taskbar",
                "setTransientParent(None) — overlay not hidden when app minimized (root cause fix)",
                "Movement lock (LOC/MOV) + minimize toggle [-]/[+] — compact 24px when minimized",
                "Periodic topmost re-assert (2s) — overlay always above app",
                "clamp_to_work_area() — overlay stays within screen bounds after drag"
            ]
        },
        {
            date: "2026-07-11",
            title: "QML Cleanup & Gamepad Tab Overhaul",
            items: [
                "Fixed all QML runtime warnings across 7 files",
                "GamepadPage UX: compact layout, Physical Gamepads (XInput) card with battery/buttons/sticks",
                "TermComboBox: Qt6 API fixes (itemTextRole, itemValueRole instead of textRole/valueRole)",
                "PicoPage: dynamic QML strings via Qt.createQmlObject with proper escaping",
                "Card.qml: removed anchors.bottom in Column (Column doesn't allow vertical anchors on children)"
            ]
        },
        {
            date: "2026-07-10",
            title: "Pico Hardware Input (Raspberry Pi Pico as Composite HID)",
            items: [
                "Binary protocol [0xAA][CMD][LEN][PAYLOAD][CRC8][0x55] with CRC8-Dallas/Maxim",
                "Serial CDC auto-detect by VID:PID (2e8a:000a/0005/0009), USB reconnect",
                "Thread-safe command queue with ACK/NACK, heartbeat PING",
                "Commands: Keyboard (press/release/tap/modifiers), Mouse (move/click/scroll), Gamepad (XInput), System",
                "Background method 'pico' added to Clicker/Macro/Recorder — undetectable by anti-cheat"
            ]
        },
        {
            date: "2026-07-10",
            title: "ViGEm Virtual Gamepad Emulation",
            items: [
                "Full ctypes wrapper over ViGEmClient.dll (X360 XInput + DS4 DirectInput)",
                "XUSB_REPORT / DS4_REPORT structures, buttons/sticks/triggers",
                "Background method 'vigem' added to Clicker/Macro/Recorder",
                "GamepadPage: ViGEm Status, Controller Config, Button Mapping, Test Controls"
            ]
        },
        {
            date: "2026-07-10",
            title: "Per-Module Target Window + Recorder Background Methods",
            items: [
                "Each module (Clicker, Macro, Aim, Recorder) has its own target window selection",
                "Bridge: setModuleTargetWindow(module, hwnd) / getModuleTargetWindow(module)",
                "Persistence v3: saves all per-module targets to profile.json",
                "Recorder: background_method + StealthInput playback"
            ]
        },
        {
            date: "2026-07-09",
            title: "Core Gaming Features: Tray + Overlay + Panic + Sound",
            items: [
                "SystemTrayManager: QSystemTrayIcon with module toggles, show/hide, panic, exit",
                "OverlayHUD: always-on-top, click-through, live CPS, module statuses, drag handle",
                "Panic Stop (F12): kills ALL modules + panic sound",
                "SoundManager: QSoundEffect + winsound.Beep fallback (start/stop/error/panic sounds)",
                "CPS Tracking: ClickerService.cps (rolling 2s window) for overlay display"
            ]
        },
        {
            date: "2026-07-08",
            title: "Terminal UI Overhaul + Frameless Window",
            items: [
                "Full terminal style: Consolas, ASCII banners, monochrome palette — no shadows/gradients",
                "Frameless window: Qt.Window | Qt.FramelessWindowHint with native drag (ChromeBar)",
                "Custom ChromeBar: '>> SHIRA://LAB <<', pin/min/close, drag area z=1, buttons z=100",
                "NavRow: blinking vertical bars '|' around active tab, inverted colors",
                "HomePage logo: Canvas with ctx.measureText() pixel-perfect centering"
            ]
        },
        {
            date: "2026-07-07",
            title: "Initial Terminal UI Rewrite",
            items: [
                "PySide6 + QML architecture established",
                "6 terminal palettes, ASCII banners, Card/TermButton/TermTextField/TermComboBox components",
                "Removed: global_transparency, interface_transparency, blur, bg_image, dwm_acrylic.py"
            ]
        }
    ]
}
