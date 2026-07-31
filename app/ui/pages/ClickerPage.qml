// ClickerPage.qml -- terminal-style page with ASCII banner + rule-based cards
// v1.0.0 i18n: all labels, buttons, combos, tooltips, status texts use mainWindow.tr()
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    color: mainWindow.termBg

    property var status: ({})

        // v1.0.0 i18n: Mouse buttons (rebuilt on language change)
        property var buttonOptions: []
        function rebuildButtonOptions() {
            var _ = Bridge.currentLang
            buttonOptions = [
                { text: mainWindow.tr("clicker.left") + " (L)", value: "L" },
                { text: mainWindow.tr("clicker.right") + " (R)", value: "R" },
                { text: mainWindow.tr("clicker.middle") + " (M)", value: "M" },
                { text: mainWindow.tr("clicker.x1") + " (X1)", value: "X1" },
                { text: mainWindow.tr("clicker.x2") + " (X2)", value: "X2" }
            ]
        }


    function updateStatus(s) {
        status = s
        statusLabel.text = mainWindow.tr("clicker.status") + (s.is_running ? mainWindow.tr("clicker.running") : mainWindow.tr("clicker.idle")) + " | " + (s.click_count || 0) + " " + mainWindow.tr("common.clicks") + " | " + (s.interval_ms || 100) + "ms"
    }

    function loadTargetWindow() {
        var r = Bridge.getModuleTargetWindow("clicker")
        var targetHwnd = r.hwnd || 0
        // Find index in model by value (currentValue is read-only in Qt 6)
        for (var i = 0; i < targetWindowCombo.model.length; i++) {
            if (targetWindowCombo.model[i].value === targetHwnd) {
                targetWindowCombo.currentIndex = i
                break
            }
        }
        targetWindowLabel.text = mainWindow.tr("lbl.target") + ": " + r.name + (r.hwnd ? " (hwnd: " + r.hwnd + ")" : "")
    }

    function refreshWindows() {
        var r = Bridge.getWindows()
        var model = [{ text: mainWindow.tr("combo.global_screen"), value: 0 }]
        for (var i = 0; i < r.windows.length; i++) {
            model.push({ text: r.windows[i].title, value: r.windows[i].hwnd })
        }
        targetWindowCombo.model = model
        loadTargetWindow()
    }

    function loadBackgroundMethod() {
        var r = Bridge.getClickerStatus()
        if (r.background_method) {
            for (var i = 0; i < clickBackgroundMethod.model.length; i++) {
                if (clickBackgroundMethod.model[i].value === r.background_method) {
                    clickBackgroundMethod.currentIndex = i
                    break
                }
            }
        }
    }

    function loadButton() {
        var r = Bridge.getClickerStatus()
        if (r.button) {
            for (var i = 0; i < clickButton.model.length; i++) {
                if (clickButton.model[i].value === r.button) {
                    clickButton.currentIndex = i
                    break
                }
            }
        }
    }

    Component.onCompleted: {
        rebuildButtonOptions()
        refreshWindows()
        loadBackgroundMethod()
        loadButton()
    }

    Connections {
        target: Bridge
        function onSettingsChanged() {
            loadBackgroundMethod()
            loadButton()
        }
    }


    // v1.0.0 i18n: Rebuild models on language change
    Connections {
        target: Bridge
        function onLangChanged() {
            rebuildButtonOptions()
            // Also refresh background method model
            rebuildBackgroundMethodModel()
            // Refresh target window list
            refreshWindows()
        }
    }

    function rebuildBackgroundMethodModel() {
        clickBackgroundMethod.model = [
            { text: mainWindow.tr("combo.method_sendinput"), value: "sendinput" },
            { text: mainWindow.tr("combo.method_postmessage"), value: "postmessage" },
            { text: mainWindow.tr("combo.method_vigem"), value: "vigem" },
            { text: mainWindow.tr("combo.method_pico"), value: "pico" }
        ]
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

// --- Target Window Card -------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.target_window")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: mainWindow.tr("lbl.select_window"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: targetWindowCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        model: [{ text: mainWindow.tr("combo.global_screen"), value: 0 }]
                        textRole: "text"
                        valueRole: "value"
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && currentIndex < model.length) {
                                Bridge.setModuleTargetWindow("clicker", model[currentIndex].value)
                            }
                            loadTargetWindow()
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("btn.refresh")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: refreshWindows()
                        }
                        Item { Layout.fillWidth: true }
                    }
                    Text { id: targetWindowLabel; text: mainWindow.tr("target.current") + " " + mainWindow.tr("combo.global_screen"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                }
            }

            // --- Clicker Config Card ------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("clicker.title")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: mainWindow.tr("lbl.interval"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermTextField { id: clickInterval; Layout.fillWidth: true; text: "100"; tooltip: mainWindow.tr("tip.click_interval"); Accessible.name: mainWindow.tr("lbl.interval") }

                    Text { text: mainWindow.tr("lbl.hold"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermTextField { id: clickHold; Layout.fillWidth: true; text: "0"; tooltip: mainWindow.tr("tip.click_hold"); Accessible.name: mainWindow.tr("lbl.hold") }

                    Text { text: mainWindow.tr("lbl.button"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: clickButton
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        model: buttonOptions
                        textRole: "text"
                        valueRole: "value"
                        tooltip: mainWindow.tr("tip.click_button")
                        Accessible.name: mainWindow.tr("lbl.button")
                    }

                    Text { text: mainWindow.tr("lbl.limit"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermTextField { id: clickLimit; Layout.fillWidth: true; text: "0"; tooltip: mainWindow.tr("tip.click_limit"); Accessible.name: mainWindow.tr("lbl.limit") }

                    Text { text: mainWindow.tr("lbl.background_method"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: clickBackgroundMethod
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        model: [
                            { text: mainWindow.tr("combo.method_sendinput"), value: "sendinput" },
                            { text: mainWindow.tr("combo.method_postmessage"), value: "postmessage" },
                            { text: mainWindow.tr("combo.method_vigem"), value: "vigem" },
                            { text: mainWindow.tr("combo.method_pico"), value: "pico" }
                        ]
                        textRole: "text"
                        valueRole: "value"
                        tooltip: mainWindow.tr("tip.click_bg_method")
                        Accessible.name: mainWindow.tr("lbl.background_method")
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("btn.apply_all")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            tooltip: mainWindow.tr("tip.click_apply")
                            Accessible.name: mainWindow.tr("btn.apply_all")
                            onClicked: { var r = Bridge.setClickerConfig(parseInt(clickInterval.text) || 100, parseInt(clickHold.text) || 0, clickButton.currentValue, parseInt(clickLimit.text) || 0, clickBackgroundMethod.currentValue); updateStatus(r); }
                        }
                        TermButton {
                            text: mainWindow.tr("clicker.start")
                            Layout.preferredWidth: 120
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            tooltip: mainWindow.tr("tip.click_start")
                            Accessible.name: mainWindow.tr("clicker.start")
                            onClicked: { var r = Bridge.startClicker(); updateStatus(r); }
                        }
                        TermButton {
                            text: mainWindow.tr("clicker.stop")
                            Layout.preferredWidth: 120
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            tooltip: mainWindow.tr("tip.click_stop")
                            Accessible.name: mainWindow.tr("clicker.stop")
                            onClicked: { var r = Bridge.stopClicker(); updateStatus(r); }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Text { id: statusLabel; text: mainWindow.tr("clicker.idle") + " | 0 " + mainWindow.tr("common.clicks") + " | 100ms"; color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 11; Layout.fillWidth: true }
                }
            }

            // Bottom spacer
            Item { Layout.fillHeight: true; Layout.fillWidth: true; Layout.minimumHeight: 16 }
        }
    }
}
