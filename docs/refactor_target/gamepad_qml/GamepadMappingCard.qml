// app/ui/pages/gamepad/GamepadMappingCard.qml
// =============================================
// Mapping: keyboard → gamepad buttons.
// Список mappings + редактирование через HotkeyRow.
// ============================================
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../../components" as C

C.Card {
    id: root

    // model: [{key: "a", gamepad_btn: "A"}, {key: "s", gamepad_btn: "B"}, ...]
    property var mappings: []
    property var availableGamepadButtons: [
        "A", "B", "X", "Y",
        "LB", "RB", "LT", "RT",
        "Back", "Start", "Guide",
        "D-Up", "D-Down", "D-Left", "D-Right",
        "L-Stick", "R-Stick", "L-Stick-Click", "R-Stick-Click"
    ]

    signal mappingChanged(string key, string gamepadBtn)
    signal mappingAdded(string key, string gamepadBtn)
    signal mappingRemoved(string key)

    title: "Button mapping"
    description: "Назначьте клавиши клавиатуры на кнопки геймпада"

    ColumnLayout {
        spacing: 8
        anchors.fill: parent

        // ─── Header ──────────────────────────────────
        RowLayout {
            Layout.fillWidth: true
            Text { text: "Key"; color: "#A0A0A0"; Layout.preferredWidth: 80 }
            Text { text: "Gamepad button"; color: "#A0A0A0"; Layout.fillWidth: true }
            Text { text: ""; Layout.preferredWidth: 30 }
        }

        // ─── List of mappings ────────────────────────
        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.mappings
            clip: true
            spacing: 4

            delegate: RowLayout {
                width: listView.width
                spacing: 8

                Text {
                    text: modelData.key
                    color: "white"
                    Layout.preferredWidth: 80
                    font.family: "Consolas"
                }

                C.TermComboBox {
                    model: root.availableGamepadButtons
                    currentText: modelData.gamepad_btn
                    onActivated: root.mappingChanged(modelData.key, root.availableGamepadButtons[index])
                    Layout.fillWidth: true
                }

                C.TermButton {
                    text: "✕"
                    onClicked: root.mappingRemoved(modelData.key)
                    Layout.preferredWidth: 30
                    ToolTip.text: "Удалить mapping"
                    ToolTip.visible: hovered
                }
            }
        }

        // ─── Add new mapping ─────────────────────────
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            C.TermTextField {
                id: newKeyField
                placeholderText: "Press key..."
                Layout.preferredWidth: 80
                Keys.onPressed: (event) => {
                    if (event.key !== Qt.Key_Escape) {
                        text = event.text.toLowerCase()
                    }
                    event.accepted = true
                }
            }

            C.TermComboBox {
                id: newBtnCombo
                model: root.availableGamepadButtons
                Layout.fillWidth: true
            }

            C.TermButton {
                text: "+ Add"
                enabled: newKeyField.text.length > 0
                onClicked: {
                    root.mappingAdded(newKeyField.text, newBtnCombo.currentText)
                    newKeyField.text = ""
                }
                ToolTip.text: "Добавить новый mapping (key → gamepad button)"
                ToolTip.visible: hovered
            }
        }
    }
}
