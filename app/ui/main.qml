import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "pages"

ApplicationWindow {
    id: mainWindow
    title: "Shira Lab"
    width: 1100
    height: 700
    minimumWidth: 800
    minimumHeight: 500
    visible: true
    flags: Qt.Window | Qt.FramelessWindowHint

    // Терминальная палитра
    property string termBg: "#000000"
    property string termFg: "#00ff41"
    property string termAcc: "#39ff14"
    property string termMuted: "#008f11"
    property string termSuccess: "#00ff41"
    property string termDanger: "#ff0040"
    property string termWarning: "#ffee00"
    property string termBorder: "#008f11"
    property string currentTab: "home"
    property var settings: ({})
    property string statusText: "READY"
    property string appVersion: "0.17.0"

    // App pin state
    property bool isPinned: false

    // Overlay HUD properties
    property bool overlayVisible: true

    // v1.0.0 i18n: signal emitted when UI language changes
    // All pages should connect to this to refresh their translated strings
    signal langChanged

    // Current page banner art (updated on tab change)
    property string currentBannerArt: ""

    // --- Banner art per tab --------------------------------------------
    property var bannerArtMap: ({
        "home": "",
        "aim": "    _    ___ __  __ \n   / \\  |_ _|  \\/  |\n  / _ \\  | || |\\/| |\n / ___ \\ | || |  | |\n/_/   \\_\\___|_|  |_|",
        "clicker": "  ____ _     ___ ____ _  _______ ____  \n / ___| |   |_ _/ ___| |/ / ____|  _ \\ \n| |   | |    | | |   | ' /|  _| | |_) |\n| |___| |___ | | |___| . \\| |___|  _ < \n \\____|_____|___\\____|_|\\_\\_____|_| \\_\\",
        "macro": " __  __    _    ____ ____   ___  \n|  \\/  |  / \\  / ___|  _ \\ / _ \\ \n| |\\/| | / _ \\| |   | |_) | | | |\n| |  | |/ ___ \\ |___|  _ <| |_| |\n|_|  |_/_/   \\_\\____|_| \\_\\___/ ",
        "recorder": " ____  _____ ____ ___  ____  ____  _____ ____  \n|  _ \\| ____/ ___/ _ \\|  _ \\|  _ \\| ____|  _ \\ \n| |_) |  _|| |  | | | | |_) | | | |  _| | |_) |\n|  _ <| |__| |__| |_| |  _ <| |_| | |___|  _ < \n|_| \\_\\_____\\____\\___/|_| \\_\\____/|_____|_| \\_\\",
        "gamepad": "  ____    _    __  __ _____ ____   _    ____  \n / ___|  / \\  |  \\/  | ____|  _ \\ / \\  |  _ \\ \n| |  _  / _ \\ | |\\/| |  _| | |_) / _ \\ | | | |\n| |_| |/ ___ \\| |  | | |___|  __/ ___ \\| |_| |\n \\____/_/   \\_\\_|  |_|_____|_| /_/   \\_\\____/ ",
        "pico": " ____ ___ ____ ___  \n|  _ \\_ _/ ___/ _ \\ \n| |_) | | |  | | | |\n|  __/| | |__| |_| |\n|_|  |___\\____\\___/ ",
        "settings": " ____  _____ _____ _____ ___ _   _  ____ ____  \n/ ___|| ____|_   _|_   _|_ _| \\ | |/ ___/ ___| \n\\___ \\|  _|   | |   | |  | ||  \\| | |  _\\___ \\ \n ___) | |___  | |   | |  | || |\\  | |_| |___) |\n|____/|_____| |_|   |_| |___|_| \\_|\\____|____/ ",
        "diagnostics": " ____ ___    _    ____ _   _  ___  ____ _____ ___ ____ ____  \n|  _ \\_ _|  / \\  / ___| \\ | |/ _ \\/ ___|_   _|_ _/ ___/ ___| \n| | | | |  / _ \\| |  _|  \\| | | | \\___ \\ | |  | | |   \\___ \\ \n| |_| | | / ___ \\ |_| | |\\  | |_| |___) || |  | | |___ ___) |\n|____/___/_/   \\_\\____|_| \\_|\\___/|____/ |_| |___\\____|____/ "
    })

    // --- Log sources per tab (empty array = no console for this tab) ---
    property var logSourcesMap: ({
        "home": [],
        "aim": ["AIM", "SYSTEM"],
        "clicker": ["CLICKER", "SYSTEM"],
        "macro": ["MACRO", "SYSTEM"],
        "recorder": ["RECORDER", "SYSTEM"],
        "gamepad": ["GAMEPAD", "SYSTEM"],
        "pico": ["PICO", "SYSTEM"],
        "settings": ["SYSTEM"],
        "diagnostics": ["SYSTEM", "DIAG"]
    })

    Component.onCompleted: {
        loadSettings()
        statusTimer.start()
        updateBannerForTab(currentTab)
        consoleLog.addLog("OK", "SYSTEM", "Shira Lab initialized")
    }

    // --- Bridge log signal connection ----------------------------------
    Connections {
        target: Bridge
        function onLogMessage(level, source, message) {
            consoleLog.addLog(level, source, message)
        }
        function onOverlayVisibilityChanged() {
            overlayVisible = Bridge.overlayVisible
        }
        function onLangChanged() {
            // Force re-evaluation of all tr() bindings
            loadSettings()
        }
    }

    // v1.0.0 i18n: Global translation function.
    // References Bridge.currentLang so QML re-evaluates when language changes.
    function tr(key) {
        var _lang = Bridge.currentLang  // trigger re-evaluation
        return Bridge.trKey(key)
    }

    function loadSettings() {
        settings = Bridge.getSettings()
        applyPalette(settings.terminal_palette || "matrix")
        isPinned = settings.is_pinned || false
    }

    function toggleOverlay() {
        overlayVisible = !overlayVisible
        Bridge.toggleOverlayHUD(overlayVisible)
    }

    function hideOverlayOnly() {
        overlayVisible = false
        Bridge.toggleOverlayHUD(false)
    }

    function applyPalette(paletteId) {
        var p = (settings.palettes || {})[paletteId]
        if (!p) return
        termBg = p.bg
        termFg = p.fg
        termAcc = p.acc
        termMuted = p.muted
        termSuccess = p.success
        termDanger = p.danger
        termWarning = p.warning
        termBorder = p.muted
    }

    function switchTab(tabName) {
        currentTab = tabName
    }

    function updateBannerForTab(tabName) {
        currentBannerArt = bannerArtMap[tabName] || ""
        var sources = logSourcesMap[tabName] || []
        consoleLog.allowedSources = sources
        var hasBanner = currentBannerArt.length > 0
        var hasConsole = sources.length > 0
        rightPanel.visible = hasBanner || hasConsole
        bannerContainer.visible = hasBanner
    }

    color: termBg


    // ═════════════════════════════════════════════════════════════════
    // v1.0.0 UX UPGRADE: Keyboard shortcuts
    // ═════════════════════════════════════════════════════════════════

    // Ctrl+1..9: switch tabs
    Shortcut {
        sequence: "Ctrl+1"
        onActivated: switchTab("home")
    }
    Shortcut {
        sequence: "Ctrl+2"
        onActivated: switchTab("aim")
    }
    Shortcut {
        sequence: "Ctrl+3"
        onActivated: switchTab("clicker")
    }
    Shortcut {
        sequence: "Ctrl+4"
        onActivated: switchTab("macro")
    }
    Shortcut {
        sequence: "Ctrl+5"
        onActivated: switchTab("recorder")
    }
    Shortcut {
        sequence: "Ctrl+6"
        onActivated: switchTab("gamepad")
    }
    Shortcut {
        sequence: "Ctrl+7"
        onActivated: switchTab("pico")
    }
    Shortcut {
        sequence: "Ctrl+8"
        onActivated: switchTab("settings")
    }
    Shortcut {
        sequence: "Ctrl+9"
        onActivated: switchTab("diagnostics")
    }

    // Panic stop: Ctrl+Shift+P (matches default hotkey)
    Shortcut {
        sequence: "Ctrl+Shift+P"
        onActivated: {
            Bridge.panicStop()
            consoleLog.addLog("WARN", "SYSTEM", "PANIC STOP triggered (Ctrl+Shift+P)")
        }
    }

    // Toggle overlay: Ctrl+O
    Shortcut {
        sequence: "Ctrl+O"
        onActivated: toggleOverlay()
    }

    // Toggle pin: Ctrl+P (avoid conflict with Ctrl+Shift+P panic)
    Shortcut {
        sequence: "Ctrl+L"
        onActivated: {
            isPinned = Bridge.toggleWindowPin()
            consoleLog.addLog("INFO", "SYSTEM", isPinned ? "Window pinned (always on top)" : "Window unpinned")
        }
    }

    // Refresh window list on current tab: F5
    Shortcut {
        sequence: "F5"
        onActivated: {
            consoleLog.addLog("INFO", "SYSTEM", "Refresh triggered")
            loadSettings()
        }
    }

    // ═════════════════════════════════════════════════════════════════
    // v1.0.0 UX UPGRADE: Update check result handler
    // ═════════════════════════════════════════════════════════════════
    Connections {
        target: Bridge
        function onUpdateCheckResult(r) {
            if (r.ok && r.update_available) {
                updateBanner.version = r.latest_version
                updateBanner.url = r.release_html_url || ""
                updateBanner.downloadUrl = r.download_url || ""
                updateBanner.notes = r.release_notes || ""
                updateBanner.visible = true
                consoleLog.addLog("INFO", "SYSTEM", "Update available: v" + r.latest_version)
            } else if (r.ok && !r.update_available) {
                consoleLog.addLog("OK", "SYSTEM", "You're running the latest version")
            }
        }
    }

    // Update banner (hidden by default, shown when update is available)
    Rectangle {
        id: updateBanner
        property string version: ""
        property string url: ""
        property string downloadUrl: ""
        property string notes: ""
        visible: false
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 8
        width: 280
        height: 60
        color: Qt.rgba(0.2, 0.8, 0.2, 0.95)
        border.color: mainWindow.termAcc
        border.width: 1
        radius: 4
        z: 1000

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 2

            Text {
                text: mainWindow.tr("home.update_banner") + " v" + updateBanner.version
                color: "white"
                font.family: "Consolas"
                font.pixelSize: 11
                font.bold: true
                Layout.fillWidth: true
            }
            Text {
                text: updateBanner.notes.substring(0, 60) + (updateBanner.notes.length > 60 ? "..." : "")
                color: "white"
                font.family: "Consolas"
                font.pixelSize: 9
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 4

                TermButton {
                    text: mainWindow.tr("btn.download")
                    tooltip: updateBanner.downloadUrl || "No download URL"
                    Layout.preferredHeight: 18
                    font.pixelSize: 9
                    enabled: updateBanner.downloadUrl.length > 0
                    onClicked: {
                        if (updateBanner.downloadUrl) {
                            Qt.openUrlExternally(updateBanner.downloadUrl)
                        }
                    }
                }
                TermButton {
                    text: mainWindow.tr("update.later")
                    Layout.preferredHeight: 18
                    font.pixelSize: 9
                    onClicked: updateBanner.visible = false
                }
            }
        }
    }


    // Timer обновления статусов
    Timer {
        id: statusTimer
        interval: 500
        repeat: true
        onTriggered: {
            try {
                if (currentTab === "clicker") {
                    var cs = Bridge.getClickerStatus()
                    clickerPage.updateStatus(cs)
                }
                if (currentTab === "aim") {
                    var as = Bridge.aimStatus()
                    aimPage.updateStatus(as)
                }
                if (currentTab === "macro") {
                    var ms = Bridge.getMacroStatus()
                    macroPage.updateStatus(ms)
                }
                if (currentTab === "recorder") {
                    var rs = Bridge.recorderStatus()
                    recorderPage.updateStatus(rs)
                }
            } catch(e) {
                console.warn("Status update failed:", e)
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ChromeBar {
            id: chromeBar
            Layout.fillWidth: true
            Layout.preferredHeight: 32
        }

        NavRow {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
        }

        // --- MAIN SPLIT: functional (left) + console (right) ---
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // LEFT: functional pages (flexible width)
            // v1.0.0 UX: Animated tab transitions
            StackLayout {
                id: pageStack
                objectName: "pageStack"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 400
                currentIndex: 0

                HomePage { id: homePage }
                AimPage { id: aimPage }
                ClickerPage { id: clickerPage }
                MacroPage { id: macroPage }
                RecorderPage { id: recorderPage }
                GamepadPage { id: gamepadPage }
                PicoPage { id: picoPage }
                SettingsPage { id: settingsPage }
                DiagnosticsPage { id: diagnosticsPage }
            }

            // RIGHT: ASCII banner + console (fixed ~30%)
            ColumnLayout {
                id: rightPanel
                Layout.fillHeight: true
                Layout.preferredWidth: 340
                Layout.minimumWidth: 280
                Layout.maximumWidth: 400
                spacing: 0
                visible: true

                // ASCII banner (hidden if no art for this tab)
                Rectangle {
                    id: bannerContainer
                    Layout.fillWidth: true
                    Layout.preferredHeight: 100
                    color: Qt.darker(mainWindow.termBg, 1.15)
                    border.color: mainWindow.termMuted
                    border.width: 1
                    visible: mainWindow.currentBannerArt.length > 0

                    AsciiBanner {
                        anchors.centerIn: parent
                        width: parent.width - 16
                        height: parent.height - 8
                        art: mainWindow.currentBannerArt
                        drawColor: mainWindow.termAcc
                        pixelSize: 10
                    }
                }

                // Console log (fills remaining space)
                ConsoleLog {
                    id: consoleLog
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }
            }
        }
    }

    // Синхронизация табов со StackLayout
    onCurrentTabChanged: {
        var tabs = ["home", "aim", "clicker", "macro", "recorder", "gamepad", "pico", "settings", "diagnostics"]
        var idx = tabs.indexOf(currentTab)
        if (idx >= 0) pageStack.currentIndex = idx
        updateBannerForTab(currentTab)
    }

    // Overlay HUD
    OverlayHUD {
        id: overlayHUD
        visible: mainWindow.overlayVisible

        termBg: mainWindow.termBg
        termFg: mainWindow.termFg
        termAcc: mainWindow.termAcc
        termMuted: mainWindow.termMuted
        termSuccess: mainWindow.termSuccess
        termDanger: mainWindow.termDanger
        termWarning: mainWindow.termWarning
    }

    // Pipette overlay
    PipetteOverlay {
        id: pipetteOverlay
    }

    Item {
        id: pipetteKeyHandler
        focus: pipetteOverlay.visible
        Keys.onEscapePressed: {
            if (pipetteOverlay.visible) {
                pipetteOverlay.visible = false
            }
        }
    }

    onClosing: function(close) {
        overlayHUD.visible = false
        Bridge.toggleOverlayHUD(false)
        close.accepted = true
    }
}
