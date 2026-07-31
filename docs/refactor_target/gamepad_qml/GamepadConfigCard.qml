// app/ui/pages/gamepad/GamepadConfigCard.qml
// ============================================
// Конфигурация ViGEm: тип контроллера (Xbox 360 / DS4), target index.
// ============================================
import QtQuick
import QtQuick.Layouts
import "../../components" as C

C.Card {
    id: root

    property string controllerType: "xbox360"
    property int targetIndex: 0
    property var availableTypes: [
        { value: "xbox360", label: "Xbox 360 Controller" },
        { value: "ds4",     label: "DualShock 4 (PS4)" }
    ]

    signal controllerTypeChanged(string type)
    signal targetIndexChanged(int index)

    title: "Configuration"
    description: "Тип и индекс виртуального контроллера"

    ColumnLayout {
        spacing: 12
        anchors.fill: parent

        // ─── Controller type ─────────────────────────
        Text { text: "Controller type"; color: "#A0A0A0" }
        C.TermComboBox {
            model: root.availableTypes
            textRole: "label"
            valueRole: "value"
            currentIndex: root.availableTypes.findIndex(t => t.value === root.controllerType)
            onActivated: root.controllerTypeChanged(root.availableTypes[index].value)
            Layout.fillWidth: true
            ToolTip.text: "Xbox 360 — стандарт для большинства игр. DS4 — для PS4-эксклюзивов."
            ToolTip.visible: hovered
            ToolTip.delay: 500
        }

        // ─── Target index ────────────────────────────
        Text { text: "Target index (0–3)"; color: "#A0A0A0" }
        RowLayout {
            spacing: 8

            C.TermButton {
                text: "−"
                enabled: root.targetIndex > 0
                onClicked: root.targetIndexChanged(root.targetIndex - 1)
                ToolTip.text: "Уменьшить индекс целевого контроллера"
                ToolTip.visible: hovered
            }

            Text {
                text: root.targetIndex.toString()
                color: "white"
                font.family: "Consolas"
                font.bold: true
                font.pixelSize: 18
                Layout.preferredWidth: 40
                horizontalAlignment: Text.AlignHCenter
            }

            C.TermButton {
                text: "+"
                enabled: root.targetIndex < 3
                onClicked: root.targetIndexChanged(root.targetIndex + 1)
                ToolTip.text: "Увеличить индекс целевого контроллера"
                ToolTip.visible: hovered
            }
        }

        Item { Layout.fillHeight: true }
    }
}
