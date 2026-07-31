// SettingsPage.qml -- terminal-style page with ASCII banner + rule-based cards
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    color: mainWindow.termBg

    // v0.16.6 fix: Language names don't need translation (they're proper nouns)
    // "Русский (RU)" is always "Русский (RU)" regardless of current language
    // This prevents the circular dependency: rebuildLangModel -> onCurrentValueChanged -> setUiLang -> rebuildLangModel
    function rebuildLangModel() {
        langCombo.model = [
            { text: mainWindow.tr("combo.lang_ru"), value: "RU" },
            { text: mainWindow.tr("combo.lang_en"), value: "EN" }
        ]
    }

    readonly property var langModel: [
        { text: "Русский (RU)", value: "RU" },
        { text: "English (EN)", value: "EN" }
    ]

    // Modern QML Connections syntax (function-based, avoids deprecation warning)
    Connections {
        target: Bridge
        function onSettingsChanged() {
            mainWindow.loadSettings()
            // Update langCombo selection when settings change (e.g. after import)
            var cur = mainWindow.settings.ui_lang || "RU"
            for (var i = 0; i < langCombo.model.length; i++) {
                if (langCombo.model[i].value === cur) {
                    langCombo.currentIndex = i
                    break
                }
            }
        }
        // NOTE: Do NOT rebuild langModel on langChanged — it causes circular dependency
        // Language names are proper nouns and don't need translation
    }


    ScrollView {
        id: scrollView
        anchors.fill: parent
        clip: true
        contentWidth: scrollView.width

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AlwaysOn
            width: 10
        }

        ColumnLayout {
            id: contentLayout
            width: scrollView.width
            spacing: 16

// --- Terminal Palette Card ----------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.terminal_palette")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: "// " + mainWindow.tr("settings.color_scheme"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }

                    GridLayout {
                        columns: 3
                        Layout.fillWidth: true
                        columnSpacing: 8
                        rowSpacing: 8

                        Repeater {
                            model: Object.keys(mainWindow.settings.palettes || {})

                            Rectangle {
                                property string paletteId: modelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: 50
                                color: mainWindow.termBg
                                border.color: mainWindow.settings.terminal_palette === paletteId ? mainWindow.termAcc : mainWindow.termMuted
                                border.width: 1

                                Column {
                                    anchors.centerIn: parent
                                    spacing: 2

                                    Text {
                                        text: (mainWindow.settings.terminal_palette === paletteId ? "> " : "") + (mainWindow.settings.palettes[paletteId].name || paletteId)
                                        color: mainWindow.termFg
                                        font.family: "Consolas"
                                        font.pixelSize: 10
                                    }

                                    Row {
                                        spacing: 2
                                        Repeater {
                                            model: ["bg", "fg", "acc", "muted", "danger"]
                                            Rectangle { width: 16; height: 6; color: mainWindow.settings.palettes[paletteId] ? mainWindow.settings.palettes[paletteId][modelData] || "#000" : "#000" }
                                        }
                                    }
                                }

                                MouseArea {
                                    id: paletteMouseArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: {
                                        Bridge.setTerminalPalette(paletteId)
                                        mainWindow.applyPalette(paletteId)
                                        mainWindow.loadSettings()
                                    }
                                    ToolTip.visible: tooltip.length > 0 && paletteMouseArea.containsMouse
                                    ToolTip.delay: 500
                                    ToolTip.text: tooltip
                                    property string tooltip: mainWindow.tr("tip.palette_select")
                                }
                            }
                        }
                    }
                }
            }

            // --- v1.0.0 NEW: Language Card ------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.language")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text {
                        text: mainWindow.tr("settings.language")
                        color: mainWindow.termMuted
                        font.family: "Consolas"
                        font.pixelSize: 10
                        Layout.fillWidth: true
                    }

                    TermComboBox {
                        id: langCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        // v0.16.6 fix: Static model — language names are proper nouns
                        model: langModel
                        textRole: "text"
                        valueRole: "value"
                        tooltip: mainWindow.tr("tip.lang_select")
                        Accessible.name: mainWindow.tr("settings.language")

                        // Set initial value from settings
                        Component.onCompleted: {
                            var cur = mainWindow.settings.ui_lang || "RU"
                            for (var i = 0; i < model.length; i++) {
                                if (model[i].value === cur) {
                                    currentIndex = i
                                    break
                                }
                            }
                        }

                        // v0.16.6 fix: Use onActivated instead of onCurrentValueChanged
                        // onActivated ONLY fires on user interaction, NOT on programmatic changes
                        // This prevents the circular dependency
                        onActivated: function(index) {
                            var val = model[index].value
                            if (val && val !== (mainWindow.settings.ui_lang || "RU")) {
                                Bridge.setUiLang(val)
                                // Bridge.setUiLang emits langChanged which triggers re-eval
                                // Do NOT call mainWindow.langChanged() — redundant and causes issues
                            }
                        }
                    }

                    Text {
                        text: "// " + mainWindow.tr("btn.refresh") + " -- " + mainWindow.tr("settings.lang_hint")
                        color: mainWindow.termMuted
                        font.family: "Consolas"
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            // --- Hotkeys Card -------------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.hotkeys")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: "// " + mainWindow.tr("settings.global_hotkeys") + " -- " + mainWindow.tr("settings.hotkeys_hint"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Repeater {
                            model: [
                                { "action": "clicker_toggle", "label": mainWindow.tr("settings.hotkey_clicker") },
                                { "action": "aim_toggle", "label": mainWindow.tr("settings.hotkey_aim") },
                                { "action": "macro_start", "label": mainWindow.tr("settings.hotkey_macro_start") },
                                { "action": "macro_stop", "label": mainWindow.tr("settings.hotkey_macro_stop") },
                                { "action": "recorder_start", "label": mainWindow.tr("settings.hotkey_recorder_start") },
                                { "action": "recorder_stop", "label": mainWindow.tr("settings.hotkey_recorder_stop") },
                                { "action": "app_show", "label": mainWindow.tr("settings.hotkey_app_show") }
                            ]

                            HotkeyRow {
                                Layout.fillWidth: true
                                actionName: modelData.action
                                actionLabel: modelData.label
                                currentKey: (mainWindow.settings.hotkeys || {})[modelData.action] ? mainWindow.settings.hotkeys[modelData.action].key : ""
                                currentMode: (mainWindow.settings.hotkeys || {})[modelData.action] ? mainWindow.settings.hotkeys[modelData.action].mode : "TOGGLE"
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("btn.reset_all")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { Bridge.resetAllHotkeys(); mainWindow.loadSettings() }
                        }
                        TermButton {
                            text: mainWindow.tr("btn.debug")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { debugBox.text = Bridge.hotkeysDebugStatus() }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Text { id: debugBox; text: ""; color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
            }


            // --- v1.0.0 NEW: Advanced Settings Card -------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.advanced")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: mainWindow.tr("lbl.profile_export_import"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TermButton {
                            text: mainWindow.tr("btn.export_profile")
                            tooltip: mainWindow.tr("tip.export_profile")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: {
                                var r = Bridge.exportProfileDialog()
                                if (r.ok) {
                                    consoleLog.addLog("OK", "SYSTEM", "Profile exported: " + (r.path || ""))
                                } else if (!r.cancelled) {
                                    consoleLog.addLog("ERROR", "SYSTEM", "Export failed: " + (r.error || ""))
                                }
                            }
                        }
                        TermButton {
                            text: mainWindow.tr("btn.import_profile")
                            tooltip: mainWindow.tr("tip.import_profile")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: {
                                var r = Bridge.importProfileDialog()
                                if (r.ok) {
                                    consoleLog.addLog("OK", "SYSTEM", "Profile imported -- applying...")
                                    mainWindow.loadSettings()
                                } else if (!r.cancelled) {
                                    consoleLog.addLog("ERROR", "SYSTEM", "Import failed: " + (r.error || ""))
                                }
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    // Separator
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: mainWindow.termMuted
                        opacity: 0.3
                    }

                    Text { text: "// " + mainWindow.tr("settings.auto_theme"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TermButton {
                            text: mainWindow.tr("btn.auto_detect_theme")
                            tooltip: mainWindow.tr("tip.auto_theme")
                            Layout.preferredWidth: 180
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: {
                                var r = Bridge.detectSystemTheme()
                                if (r.ok) {
                                    consoleLog.addLog("INFO", "SYSTEM", "System theme: " + r.theme)
                                    themeResult.text = mainWindow.tr("settings.theme_detected") + r.theme.toUpperCase()
                                }
                            }
                        }
                        Text {
                            id: themeResult
                            text: ""
                            color: mainWindow.termAcc
                            font.family: "Consolas"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                        }
                    }

                    // Separator
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: mainWindow.termMuted
                        opacity: 0.3
                    }

                    Text { text: "// " + mainWindow.tr("settings.privacy_crash"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    Text {
                        text: "// " + mainWindow.tr("settings.crash_privacy_hint")
                        color: mainWindow.termMuted
                        font.family: "Consolas"
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        ToggleSwitch {
                            id: crashReportsToggle
                            checked: false
                            label: mainWindow.tr("settings.send_crash_reports")
                            tooltip: mainWindow.tr("tip.send_crash_reports")
                            onToggled: function(checked) {
                                Bridge.setCrashReportSending(checked)
                                consoleLog.addLog("INFO", "SYSTEM", "Crash report sending: " + (checked ? "ON" : "OFF"))
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TermButton {
                            text: mainWindow.tr("btn.view_crash_logs")
                            tooltip: mainWindow.tr("tip.view_crash")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: {
                                var r = Bridge.listCrashReports()
                                if (r.ok) {
                                    var count = (r.crashes || []).length
                                    consoleLog.addLog("INFO", "SYSTEM", "Crash logs: " + count + " file(s)")
                                    if (count > 0) {
                                        for (var i = 0; i < r.crashes.length; i++) {
                                            var c = r.crashes[i]
                                            consoleLog.addLog("WARN", "CRASH", c.file + " -- " + c.exception_type + ": " + c.exception_message)
                                        }
                                    }
                                }
                            }
                        }
                        TermButton {
                            text: mainWindow.tr("btn.clear_all")
                            tooltip: mainWindow.tr("tip.clear_all_crashes")
                            Layout.preferredWidth: 160
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: {
                                var r = Bridge.clearAllCrashReports()
                                if (r.ok) {
                                    consoleLog.addLog("OK", "SYSTEM", "Cleared " + r.deleted + " crash report(s)")
                                }
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    // Separator
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: mainWindow.termMuted
                        opacity: 0.3
                    }

                    Text { text: "// " + mainWindow.tr("settings.perf_profiler_label"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TermButton {
                            text: mainWindow.tr("btn.get_perf_profile")
                            tooltip: mainWindow.tr("tip.measure_now")
                            Layout.preferredWidth: 200
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: {
                                var r = Bridge.getPerformanceProfile()
                                if (r.ok) {
                                    perfResult.text = "CPU: " + r.cpu_percent.toFixed(1) + "% | "
                                        + "MEM: " + r.memory_mb.toFixed(1) + " MB | "
                                        + "Threads: " + r.threads + " | "
                                        + "Uptime: " + r.uptime_sec + "s"
                                    consoleLog.addLog("INFO", "SYSTEM", perfResult.text)
                                }
                            }
                        }
                        Text {
                            id: perfResult
                            text: ""
                            color: mainWindow.termAcc
                            font.family: "Consolas"
                            font.pixelSize: 10
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            // Version info
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.about")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Text {
                        text: "Shira Lab v" + (mainWindow.appVersion || "1.0.0")  // version is universal
                        color: mainWindow.termAcc
                        font.family: "Consolas"
                        font.pixelSize: 13
                        font.bold: true
                        Layout.fillWidth: true
                    }
                    Text {
                        text: "// " + mainWindow.tr("about.description")
                        color: mainWindow.termMuted
                        font.family: "Consolas"
                        font.pixelSize: 10
                        Layout.fillWidth: true
                    }
                    Text {
                        text: "// " + mainWindow.tr("about.built_with")
                        color: mainWindow.termMuted
                        font.family: "Consolas"
                        font.pixelSize: 10
                        Layout.fillWidth: true
                    }
                }
            }

            // --- Game Profiles Card ------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.game_profiles")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: "// " + mainWindow.tr("settings.save_load_hint"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }

                    // Profile name input
                    Text { text: "// " + mainWindow.tr("settings.profile_name"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermTextField { id: profileNameField; Layout.fillWidth: true; text: ""; placeholderText: mainWindow.tr("settings.profile_placeholder") }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("btn.save")
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: {
                                if (profileNameField.text.length > 0) {
                                    var r = Bridge.saveGameProfile(profileNameField.text)
                                    if (r.ok) { profileNameField.text = ""; refreshProfiles() }
                                }
                            }
                        }
                        TermButton {
                            text: mainWindow.tr("btn.load")
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: {
                                if (profileCombo.currentIndex >= 0) {
                                    var name = profileCombo.model[profileCombo.currentIndex].name
                                    var r = Bridge.loadGameProfile(name)
                                    if (r.ok) { mainWindow.loadSettings() }
                                }
                            }
                        }
                        TermButton {
                            text: mainWindow.tr("btn.delete")
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: {
                                if (profileCombo.currentIndex >= 0) {
                                    var name = profileCombo.model[profileCombo.currentIndex].name
                                    var r = Bridge.deleteGameProfile(name)
                                    refreshProfiles()
                                }
                            }
                        }
                        TermButton {
                            text: mainWindow.tr("btn.refresh")
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: refreshProfiles()
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Text { text: "// " + mainWindow.tr("settings.saved_profiles"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: profileCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        model: []
                        textRole: "name"
                    }

                    function refreshProfiles() {
                        var r = Bridge.listGameProfiles()
                        profileCombo.model = r.profiles || []
                    }
                    Component.onCompleted: refreshProfiles()
                }
            }

            // Bottom spacer
            Item { Layout.fillHeight: true; Layout.fillWidth: true; Layout.minimumHeight: 16 }
        }
    }
}
