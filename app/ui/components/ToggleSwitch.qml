// ToggleSwitch.qml -- v1.0.0 UX upgrade (fixed)
// Added: tooltip support, keyboard activation (Space when focused), hover effect
import QtQuick
import QtQuick.Controls

Row {
    id: control
    property bool checked: false
    property string label: ""
    property string tooltip: ""  // NEW: tooltip text
    signal toggled(bool checked)

    spacing: 8

    Rectangle {
        id: track
        width: 36
        height: 18
        anchors.verticalCenter: parent.verticalCenter
        color: checked ? mainWindow.termMuted : Qt.darker(mainWindow.termBg, 1.5)
        border.color: checked ? mainWindow.termAcc : mainWindow.termMuted
        border.width: 1

        Rectangle {
            id: thumb
            width: 14; height: 14
            x: checked ? 19 : 1
            y: 1
            color: checked ? mainWindow.termAcc : mainWindow.termMuted
            Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: 150 } }
        }

        MouseArea {
            id: trackMouse
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                checked = !checked
                toggled(checked)
            }
            hoverEnabled: true
            onEntered: if (control.tooltip.length > 0) toolTip.show(control.tooltip)
            onExited: toolTip.hide()
        }

        // Keyboard accessibility
        focus: true
        Keys.onSpacePressed: {
            checked = !checked
            toggled(checked)
        }
        Keys.onReturnPressed: {
            checked = !checked
            toggled(checked)
        }
    }

    Text {
        text: label
        color: mainWindow.termFg
        font.family: "Consolas"
        font.pixelSize: 11
        anchors.verticalCenter: parent.verticalCenter

        MouseArea {
            id: labelMouse
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                checked = !checked
                toggled(checked)
            }
            hoverEnabled: true
            onEntered: if (control.tooltip.length > 0) toolTip.show(control.tooltip)
            onExited: toolTip.hide()
        }
    }

    // Tooltip
    ToolTip {
        id: toolTip
        parent: control
        delay: 500
        timeout: 3000
        text: control.tooltip
        visible: control.tooltip.length > 0 && (trackMouse.containsMouse || labelMouse.containsMouse)
    }
}
