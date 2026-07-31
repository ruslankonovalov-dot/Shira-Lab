// RecorderPage.qml -- terminal-style page with ASCII banner + rule-based cards
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    color: mainWindow.termBg

    property var status: ({})

    function updateStatus(s) {
        status = s
        statusLabel.text = mainWindow.tr("recorder.rec") + "=" + (s.is_recording ? mainWindow.tr("common.on") : mainWindow.tr("common.off")) + ", " + mainWindow.tr("recorder.play") + "=" + (s.is_playing ? mainWindow.tr("common.on") : mainWindow.tr("common.off")) + ", " + mainWindow.tr("recorder.events") + "=" + s.events_count
    }

    function loadTargetWindow() {
        var r = Bridge.getModuleTargetWindow("recorder")
        var targetHwnd = r.hwnd || 0
        for (var i = 0; i < targetWindowCombo.model.length; i++) {
            if (targetWindowCombo.model[i].value === targetHwnd) {
                targetWindowCombo.currentIndex = i
                break
            }
        }
        targetWindowLabel.text = mainWindow.tr("target.current") + " " + r.name + (r.hwnd ? " (hwnd: " + r.hwnd + ")" : "")
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
        var r = Bridge.recorderStatus()
        if (r.background_method) {
            for (var i = 0; i < recorderBackgroundMethod.model.length; i++) {
                if (recorderBackgroundMethod.model[i].value === r.background_method) {
                    recorderBackgroundMethod.currentIndex = i
                    break
                }
            }
        }
    }

    function refreshRecords() {
        var r = Bridge.recorderList()
        var records = r.records || []
        recList.model = records
    }

    Component.onCompleted: {
        refreshWindows()
        refreshRecords()
        loadBackgroundMethod()
    }

    // Modern QML Connections syntax (function-based, avoids deprecation warning)
    Connections {
        target: Bridge
        function onSettingsChanged() {
            loadBackgroundMethod()
        }
        function onLangChanged() {
            refreshWindows()
            loadBackgroundMethod()
        }
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
                                Bridge.setModuleTargetWindow("recorder", model[currentIndex].value)
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

            // --- Playback Settings Card ---------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.playback")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: mainWindow.tr("lbl.background_method"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: recorderBackgroundMethod
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
                        tooltip: mainWindow.tr("tip.recorder_bg_method")
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("btn.apply_bg_method")
                            tooltip: mainWindow.tr("tip.recorder_apply")
                            Layout.preferredWidth: 160
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { var r = Bridge.setRecorderBackgroundMethod(recorderBackgroundMethod.currentValue); updateStatus(r); }
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
            }

            // --- Recorder Card ------------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("recorder.title")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("recorder.start_record")
                            tooltip: mainWindow.tr("tip.recorder_start")
                            Accessible.name: mainWindow.tr("recorder.start_record")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { var r = Bridge.recorderStart(); updateStatus(r) }
                        }
                        TermButton {
                            text: mainWindow.tr("recorder.stop_record")
                            tooltip: mainWindow.tr("tip.recorder_stop")
                            Accessible.name: mainWindow.tr("recorder.stop_record")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { var r = Bridge.recorderStop(); updateStatus(r); refreshRecords() }
                        }
                        TermButton {
                            text: mainWindow.tr("btn.refresh")
                            tooltip: mainWindow.tr("tip.recorder_refresh")
                            Accessible.name: mainWindow.tr("btn.refresh")
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: refreshRecords()
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Text { text: mainWindow.tr("lbl.saved_records"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: recList
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("recorder.play")
                            tooltip: mainWindow.tr("tip.recorder_play")
                            Accessible.name: mainWindow.tr("recorder.play")
                            Layout.preferredWidth: 120
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { if (recList.currentText) { var r = Bridge.recorderPlay(recList.currentText, 1); updateStatus(r) } }
                        }
                        TermButton {
                            text: mainWindow.tr("recorder.stop")
                            tooltip: mainWindow.tr("tip.recorder_stop_play")
                            Accessible.name: mainWindow.tr("recorder.stop")
                            Layout.preferredWidth: 120
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { var r = Bridge.recorderStopPlay(); updateStatus(r) }
                        }
                        TermButton {
                            text: mainWindow.tr("btn.delete")
                            tooltip: mainWindow.tr("tip.recorder_delete")
                            Accessible.name: mainWindow.tr("btn.delete")
                            Layout.preferredWidth: 120
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { if (recList.currentText) { Bridge.recorderDelete(recList.currentText); refreshRecords() } }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Text { id: statusLabel; text: mainWindow.tr("recorder.rec") + "=" + mainWindow.tr("common.off") + ", " + mainWindow.tr("recorder.play") + "=" + mainWindow.tr("common.off") + ", " + mainWindow.tr("recorder.events") + "=0"; color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 11; Layout.fillWidth: true }
                }
            }

            // Bottom spacer
            Item { Layout.fillHeight: true; Layout.fillWidth: true; Layout.minimumHeight: 16 }
        }
    }
}
