// app/ui/pages/gamepad/GamepadStatusCard.qml
// =============================================
// Карточка статуса ViGEm: target index, controller type, кнопки Start/Stop.
// Перенесено из GamepadPage.qml секция "Status".
// =============================================
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../../components" as C

C.Card {
    id: root

    // Properties (bind к main GamepadPage)
    property var vigemStatus: ({})
    property bool running: vigemStatus.running || false

    signal startRequested()
    signal stopRequested()

    title: "Status"
    description: "Текущее состояние виртуального геймпада"

    ColumnLayout {
        spacing: 12
        anchors.fill: parent

        // ─── Status indicator ────────────────────────
        RowLayout {
            spacing: 8

            Rectangle {
                width: 12; height: 12; radius: 6
                color: root.running ? "#7CFC00" : "#FF4444"
            }

            Text {
                text: root.running ? "Running" : "Stopped"
                color: root.running ? "#7CFC00" : "#FF4444"
                font.family: "Consolas"
                font.bold: true
            }
        }

        // ─── Info row ────────────────────────────────
        GridLayout {
            columns: 2
            columnSpacing: 12
            rowSpacing: 6

            Text { text: "Controller:"; color: "#A0A0A0" }
            Text { text: vigemStatus.controller_type || "Xbox 360"; color: "white" }

            Text { text: "Target index:"; color: "#A0A0A0" }
            Text { text: (vigemStatus.target_index || 0).toString(); color: "white" }

            Text { text: "Vendor ID:"; color: "#A0A0A0" }
            Text { text: "0x" + ((vigemStatus.vendor_id || 0).toString(16).toUpperCase().padStart(4, '0')); color: "white" }
        }

        // ─── Action buttons ──────────────────────────
        RowLayout {
            spacing: 8
            Layout.fillWidth: true

            C.TermButton {
                text: root.running ? "Stop" : "Start"
                enabled: vigemStatus.ok !== false
                onClicked: root.running ? root.stopRequested() : root.startRequested()
                ToolTip.text: root.running ? "Остановить виртуальный геймпад" : "Запустить виртуальный геймпад"
                ToolTip.visible: hovered
                ToolTip.delay: 500
            }

            C.TermButton {
                text: "Refresh"
                onClicked: root.refreshRequested && root.refreshRequested()
                ToolTip.text: "Пересканировать цели ViGEm"
                ToolTip.visible: hovered
                ToolTip.delay: 500
            }
        }

        Item { Layout.fillHeight: true } // spacer
    }
}
