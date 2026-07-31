// app/ui/pages/gamepad/GamepadTestCard.qml
// ==========================================
// Ручной тест: sticks, triggers, buttons.
// Виртуальные стики и триггеры для проверки работы ViGEm.
// ============================================
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../../components" as C

C.Card {
    id: root

    property int targetId: 0

    signal setButtonsRequested(int targetId, int buttonMask)
    signal setTriggersRequested(int targetId, int lt, int rt)
    signal setLeftStickRequested(int targetId, int x, int y)
    signal setRightStickRequested(int targetId, int x, int y)
    signal resetRequested(int targetId)

    title: "Test gamepad"
    description: "Ручная проверка: кнопки, стики, триггеры"

    ColumnLayout {
        spacing: 12
        anchors.fill: parent

        // ─── Buttons grid ────────────────────────────
        Text { text: "Buttons"; color: "#A0A0A0" }
        GridLayout {
            columns: 6
            columnSpacing: 4
            rowSpacing: 4

            Repeater {
                model: [
                    { label: "A",     mask: 0x1000 },
                    { label: "B",     mask: 0x2000 },
                    { label: "X",     mask: 0x4000 },
                    { label: "Y",     mask: 0x8000 },
                    { label: "LB",    mask: 0x0100 },
                    { label: "RB",    mask: 0x0200 },
                    { label: "Back",  mask: 0x0020 },
                    { label: "Start", mask: 0x0010 },
                    { label: "Guide", mask: 0x0004 },
                    { label: "L3",    mask: 0x0040 },
                    { label: "R3",    mask: 0x0080 },
                    { label: "D-Up",  mask: 0x0001 }
                ]

                delegate: C.TermButton {
                    text: modelData.label
                    checkable: true
                    Layout.preferredWidth: 50
                    Layout.preferredHeight: 30
                    onCheckedChanged: {
                        // TODO: собрать все активные кнопки и вызвать setButtonsRequested
                    }
                }
            }
        }

        // ─── Triggers ────────────────────────────────
        Text { text: "Triggers (0–255)"; color: "#A0A0A0" }
        RowLayout {
            spacing: 16

            ColumnLayout {
                spacing: 4
                Text { text: "LT: " + Math.round(ltSlider.value); color: "white" }
                Slider {
                    id: ltSlider
                    from: 0; to: 255; value: 0
                    onValueChanged: root.setTriggersRequested(root.targetId, Math.round(value), Math.round(rtSlider.value))
                }
            }

            ColumnLayout {
                spacing: 4
                Text { text: "RT: " + Math.round(rtSlider.value); color: "white" }
                Slider {
                    id: rtSlider
                    from: 0; to: 255; value: 0
                    onValueChanged: root.setTriggersRequested(root.targetId, Math.round(ltSlider.value), Math.round(value))
                }
            }
        }

        // ─── Sticks (visual) ─────────────────────────
        Text { text: "Sticks"; color: "#A0A0A0" }
        RowLayout {
            spacing: 16

            // Left stick
            Rectangle {
                width: 100; height: 100
                color: "transparent"
                border.color: "#404040"
                radius: 50

                Rectangle {
                    id: leftStickDot
                    width: 14; height: 14; radius: 7
                    color: "#00FF00"
                    x: 50 - 7
                    y: 50 - 7
                }

                MouseArea {
                    anchors.fill: parent
                    drag.target: leftStickDot
                    drag.axis: Drag.XAndYAxis
                    drag.minimumX: 0; drag.maximumX: 100 - 14
                    drag.minimumY: 0; drag.maximumY: 100 - 14
                    onPositionChanged: {
                        var x = ((leftStickDot.x + 7) - 50) * 327.67
                        var y = (50 - (leftStickDot.y + 7)) * 327.67
                        root.setLeftStickRequested(root.targetId, Math.round(x), Math.round(y))
                    }
                    onReleased: {
                        leftStickDot.x = 50 - 7
                        leftStickDot.y = 50 - 7
                        root.setLeftStickRequested(root.targetId, 0, 0)
                    }
                }
            }

            // Right stick
            Rectangle {
                width: 100; height: 100
                color: "transparent"
                border.color: "#404040"
                radius: 50

                Rectangle {
                    id: rightStickDot
                    width: 14; height: 14; radius: 7
                    color: "#FF6600"
                    x: 50 - 7
                    y: 50 - 7
                }

                MouseArea {
                    anchors.fill: parent
                    drag.target: rightStickDot
                    drag.axis: Drag.XAndYAxis
                    drag.minimumX: 0; drag.maximumX: 100 - 14
                    drag.minimumY: 0; drag.maximumY: 100 - 14
                    onPositionChanged: {
                        var x = ((rightStickDot.x + 7) - 50) * 327.67
                        var y = (50 - (rightStickDot.y + 7)) * 327.67
                        root.setRightStickRequested(root.targetId, Math.round(x), Math.round(y))
                    }
                    onReleased: {
                        rightStickDot.x = 50 - 7
                        rightStickDot.y = 50 - 7
                        root.setRightStickRequested(root.targetId, 0, 0)
                    }
                }
            }
        }

        // ─── Reset ───────────────────────────────────
        RowLayout {
            Layout.fillWidth: true

            C.TermButton {
                text: "Reset all"
                onClicked: {
                    ltSlider.value = 0
                    rtSlider.value = 0
                    leftStickDot.x = 50 - 7; leftStickDot.y = 50 - 7
                    rightStickDot.x = 50 - 7; rightStickDot.y = 50 - 7
                    root.resetRequested(root.targetId)
                }
                ToolTip.text: "Сбросить все в нейтральное положение"
                ToolTip.visible: hovered
            }

            Item { Layout.fillWidth: true }
        }
    }
}
