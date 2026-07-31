// PicoButtonMapRow.qml — Pico button mapping row with i18n support
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    property string keyName: ""
    property string buttonValue: ""
    property bool readOnly: false
    Layout.fillWidth: true
    Layout.preferredHeight: 34

    // Button options model — rebuilt on langChanged
    property var buttonOptions: []

    Rectangle {
        id: bg
        anchors.fill: parent
        color: mainWindow.termBg
        border.color: mainWindow.termMuted
        border.width: 1
        radius: 2
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 4
        spacing: 8

        // Key label
        Text {
            text: mainWindow.tr("pico.key_" + keyName.toLowerCase())
            color: mainWindow.termFg
            font.family: "Consolas"
            font.pixelSize: 11
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
        }

        // Button mapping combo
        TermComboBox {
            id: mapCombo
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            model: buttonOptions
            textRole: "text"
            valueRole: "value"
            enabled: !root.readOnly

            Component.onCompleted: {
                // Set initial selection
                for (var i = 0; i < model.length; i++) {
                    if (model[i].value === root.buttonValue) {
                        currentIndex = i
                        break
                    }
                }
            }

            onCurrentIndexChanged: {
                if (currentIndex >= 0 && currentIndex < model.length) {
                    var newValue = model[currentIndex].value
                    if (newValue !== root.buttonValue) {
                        Bridge.setPicoButtonMap(keyName, newValue)
                    }
                }
            }
        }

        // Save button
        TermButton {
            text: mainWindow.tr("btn.save")
            Layout.preferredWidth: 60
            Layout.preferredHeight: 30
            font.pixelSize: 10
            enabled: !root.readOnly
            onClicked: {
                if (mapCombo.currentIndex >= 0 && mapCombo.currentIndex < mapCombo.model.length) {
                    var newValue = mapCombo.model[mapCombo.currentIndex].value
                    Bridge.setPicoButtonMap(keyName, newValue)
                }
            }
        }
    }

    // Rebuild button options on language change
    Connections {
        target: Bridge
        function onLangChanged() {
            root.rebuildButtonOptions()
        }
    }

    function rebuildButtonOptions() {
        buttonOptions = [
            { text: mainWindow.tr("gamepad.btn_a"), value: "A" },
            { text: mainWindow.tr("gamepad.btn_b"), value: "B" },
            { text: mainWindow.tr("gamepad.btn_x"), value: "X" },
            { text: mainWindow.tr("gamepad.btn_y"), value: "Y" },
            { text: mainWindow.tr("gamepad.btn_lb"), value: "LB" },
            { text: mainWindow.tr("gamepad.btn_rb"), value: "RB" },
            { text: mainWindow.tr("gamepad.btn_back"), value: "BACK" },
            { text: mainWindow.tr("gamepad.btn_start"), value: "START" },
            { text: mainWindow.tr("gamepad.btn_up"), value: "UP" },
            { text: mainWindow.tr("gamepad.btn_down"), value: "DOWN" },
            { text: mainWindow.tr("gamepad.btn_left"), value: "LEFT" },
            { text: mainWindow.tr("gamepad.btn_right"), value: "RIGHT" },
            { text: mainWindow.tr("gamepad.btn_lt"), value: "LT" },
            { text: mainWindow.tr("gamepad.btn_rt"), value: "RT" }
        ]
    }

    Component.onCompleted: {
        rebuildButtonOptions()
    }
}
