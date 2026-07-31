// PicoPage.qml -- terminal-style page with ASCII banner + rule-based cards
// v1.0.0 i18n: all labels, buttons, combos, tooltips, status texts use mainWindow.tr()
// Refactored to use static Repeater with PicoButtonMapRow component (Phase 2.4)
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    color: mainWindow.termBg

    property var status: ({})
    property var devices: []
    property string statePicoPort: ""

    function updateStatus(s) {
        status = s
        statusLabel.text = mainWindow.tr("pico.status_prefix") + (s.connected ? mainWindow.tr("pico.connected") : mainWindow.tr("pico.disconnected")) +
            (s.fw_version ? ", " + mainWindow.tr("pico.fw_version") + s.fw_version : "") +
            (s.caps !== undefined ? ", " + mainWindow.tr("pico.caps") + "0x" + s.caps.toString(16) : "") +
            (s.port ? ", " + mainWindow.tr("pico.port") + s.port : "")
    }

    function refreshDevices() {
        var r = Bridge.listPicoDevices()
        if (r.ok) {
            devices = r.devices
            var model = [{ text: mainWindow.tr("combo.pico_auto"), value: "" }]
            for (var i = 0; i < devices.length; i++) {
                var d = devices[i]
                model.push({
                    text: d.port + " - " + d.description + (d.fw_version ? " [" + d.fw_version + "]" : ""),
                    value: d.port
                })
            }
            portCombo.model = model
            if (statePicoPort) {
                // Find index by value (currentValue is read-only in Qt 6)
                for (var i = 0; i < portCombo.model.length; i++) {
                    if (portCombo.model[i].value === statePicoPort) {
                        portCombo.currentIndex = i
                        break
                    }
                }
            }
        }
    }

    function connectPico() {
        var portVal = ""
        if (portCombo.currentIndex >= 0 && portCombo.currentIndex < portCombo.model.length) {
            portVal = portCombo.model[portCombo.currentIndex].value
        }
        var r = Bridge.startPico(portVal)
        if (r.ok) {
            statusLabel.text = mainWindow.tr("pico.connecting") + (r.port || mainWindow.tr("combo.pico_auto")) + "..."
            refreshStatus()
        } else {
            statusLabel.text = mainWindow.tr("pico.error_prefix") + r.error
        }
    }

    function refreshStatus() {
        var r = Bridge.getPicoStatus()
        if (r.ok) {
            updateStatus(r)
        }
    }

    function setMode(mode) {
        var r = Bridge.setPicoMode(mode)
        if (r.ok) {
            refreshStatus()
        }
    }

    Component.onCompleted: {
        refreshDevices()
        Qt.callLater(function() { refreshStatus(); })
    }

    // v1.0.0 i18n: Rebuild models on language change
    Connections {
        target: Bridge
        function onLangChanged() {
            refreshDevices()
            btnMapModel.rebuildModel()
        }
    }

    // Button mapping model for Repeater
    ListModel {
        id: btnMapModel

        function rebuildModel() {
            clear()
            var defaultMap = {
                "space": "A", "enter": "A", "shift": "LB", "ctrl": "RB",
                "q": "X", "e": "Y", "r": "B", "tab": "BACK", "escape": "START",
                "w": "UP", "s": "DOWN", "a": "LEFT", "d": "RIGHT",
                "mouse1": "LT", "mouse2": "RT"
            }
            for (var k in defaultMap) {
                append({ key: k, button: defaultMap[k] })
            }
        }

        Component.onCompleted: rebuildModel()
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

// --- Connection Card ----------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.pico_connection")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: mainWindow.tr("lbl.select_port"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: portCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        model: [{ text: mainWindow.tr("combo.pico_auto"), value: "" }]
                        textRole: "text"
                        valueRole: "value"
                        tooltip: mainWindow.tr("tip.pico_port")
                        Accessible.name: mainWindow.tr("lbl.select_port")
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("btn.refresh")
                            tooltip: mainWindow.tr("tip.pico_refresh")
                            Accessible.name: mainWindow.tr("btn.refresh")
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: refreshDevices()
                        }
                        TermButton {
                            text: mainWindow.tr("pico.connect")
                            tooltip: mainWindow.tr("tip.pico_connect")
                            Accessible.name: mainWindow.tr("pico.connect")
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: connectPico()
                        }
                        TermButton {
                            text: mainWindow.tr("pico.disconnect")
                            tooltip: mainWindow.tr("tip.pico_disconnect")
                            Accessible.name: mainWindow.tr("pico.disconnect")
                            Layout.preferredWidth: 120
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { var r = Bridge.stopPico(); refreshStatus(); }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Text { id: statusLabel; text: mainWindow.tr("pico.scanning"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 11; Layout.fillWidth: true }
                }
            }

            // --- USB Mode Card ------------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.pico_mode")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: mainWindow.tr("lbl.device_mode"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: modeCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        model: [
                            { text: mainWindow.tr("combo.usb_composite"), value: "COMPOSITE" },
                            { text: mainWindow.tr("combo.usb_keyboard"), value: "KEYBOARD" },
                            { text: mainWindow.tr("combo.usb_mouse"), value: "MOUSE" },
                            { text: mainWindow.tr("combo.usb_gamepad"), value: "GAMEPAD" }
                        ]
                        textRole: "text"
                        valueRole: "value"
                        tooltip: mainWindow.tr("tip.pico_mode")
                        Accessible.name: mainWindow.tr("lbl.device_mode")
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && currentIndex < model.length) {
                                setMode(model[currentIndex].value)
                            }
                        }
                    }
                }
            }

            // --- Button Mapping Card ------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.pico_mapping")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: mainWindow.tr("lbl.map_keys_to_btns"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }

                    // Static Repeater with PicoButtonMapRow component
                    Repeater {
                        model: btnMapModel
                        delegate: PicoButtonMapRow {
                            keyName: model.key
                            buttonValue: model.button
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            // --- Test Controls Card -------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.pico_test")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    // Keyboard test
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text { text: mainWindow.tr("lbl.keyboard"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.preferredWidth: 100 }
                        TermButton { text: mainWindow.tr("pico.tap_space_a"); tooltip: mainWindow.tr("tip.pico_test_buttons"); Accessible.name: mainWindow.tr("pico.tap_space_a"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSendKey("space", "tap", 50) } }
                        TermButton { text: mainWindow.tr("pico.tap_enter"); tooltip: mainWindow.tr("tip.pico_test_buttons"); Accessible.name: mainWindow.tr("pico.tap_enter"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSendKey("enter", "tap", 50) } }
                        TermButton { text: mainWindow.tr("pico.hold_shift"); tooltip: mainWindow.tr("tip.pico_test_buttons"); Accessible.name: mainWindow.tr("pico.hold_shift"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSendKey("shift", "press", 0) } }
                        TermButton { text: mainWindow.tr("pico.release_shift"); tooltip: mainWindow.tr("tip.pico_test_buttons"); Accessible.name: mainWindow.tr("pico.release_shift"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSendKey("shift", "release", 0) } }
                        Item { Layout.fillWidth: true }
                    }

                    // Mouse test
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text { text: mainWindow.tr("lbl.mouse"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.preferredWidth: 100 }
                        TermButton { text: mainWindow.tr("pico.move"); tooltip: mainWindow.tr("tip.pico_test_buttons"); Accessible.name: mainWindow.tr("pico.move"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSendMouse(10, 10, 0, 0) } }
                        TermButton { text: mainWindow.tr("pico.left_click"); tooltip: mainWindow.tr("tip.pico_test_buttons"); Accessible.name: mainWindow.tr("pico.left_click"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSendMouse(0, 0, 1, 50) } }
                        TermButton { text: mainWindow.tr("pico.right_click"); tooltip: mainWindow.tr("tip.pico_test_buttons"); Accessible.name: mainWindow.tr("pico.right_click"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSendMouse(0, 0, 2, 50) } }
                        Item { Layout.fillWidth: true }
                    }

                    // Gamepad test
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text { text: mainWindow.tr("lbl.gamepad"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.preferredWidth: 100 }
                        TermButton { text: mainWindow.tr("pico.a_press"); tooltip: mainWindow.tr("tip.pico_test_buttons"); Accessible.name: mainWindow.tr("pico.a_press"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSendGamepad(0x1000, 0, 0, 0, 0, 0, 0) } }
                        TermButton { text: mainWindow.tr("pico.b_press"); tooltip: mainWindow.tr("tip.pico_test_buttons"); Accessible.name: mainWindow.tr("pico.b_press"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSendGamepad(0x2000, 0, 0, 0, 0, 0, 0) } }
                        TermButton { text: mainWindow.tr("pico.lt_255"); tooltip: mainWindow.tr("tip.pico_test_axes"); Accessible.name: mainWindow.tr("pico.lt_255"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSendGamepad(0, 255, 0, 0, 0, 0, 0) } }
                        TermButton { text: mainWindow.tr("pico.rt_255"); tooltip: mainWindow.tr("tip.pico_test_axes"); Accessible.name: mainWindow.tr("pico.rt_255"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSendGamepad(0, 0, 255, 0, 0, 0, 0) } }
                        TermButton { text: mainWindow.tr("pico.reset_all"); tooltip: mainWindow.tr("tip.pico_reset"); Accessible.name: mainWindow.tr("pico.reset_all"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoReset() } }
                        Item { Layout.fillWidth: true }
                    }

                    // Sticks test
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text { text: mainWindow.tr("lbl.sticks"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.preferredWidth: 100 }
                        TermButton { text: mainWindow.tr("pico.lstick_center"); tooltip: mainWindow.tr("tip.pico_test_axes"); Accessible.name: mainWindow.tr("pico.lstick_center"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSetStick(0, 0, 0) } }
                        TermButton { text: mainWindow.tr("pico.lstick_up"); tooltip: mainWindow.tr("tip.pico_test_axes"); Accessible.name: mainWindow.tr("pico.lstick_up"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSetStick(0, 0, -32767) } }
                        TermButton { text: mainWindow.tr("pico.rstick_right"); tooltip: mainWindow.tr("tip.pico_test_axes"); Accessible.name: mainWindow.tr("pico.rstick_right"); Layout.preferredHeight: 32; font.pixelSize: 11; onClicked: { Bridge.picoSetStick(1, 32767, 0) } }
                        Item { Layout.fillWidth: true }
                    }
                }
            }

            // Bottom spacer
            Item { Layout.fillHeight: true; Layout.fillWidth: true; Layout.minimumHeight: 16 }
        }
    }
}
