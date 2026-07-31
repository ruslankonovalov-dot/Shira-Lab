// TermSlider.qml — terminal-style slider with tooltip support
import QtQuick
import QtQuick.Controls

Slider {
    id: control
    font.family: "Consolas"
    font.pixelSize: 11

    // Tooltip support
    property string tooltip: ""

    ToolTip.visible: tooltip.length > 0 && hovered
    ToolTip.delay: 500
    ToolTip.text: tooltip
    ToolTip.timeout: 3000

    background: Rectangle {
        implicitHeight: 18
        color: mainWindow.termBg
        border.color: mainWindow.termMuted
        border.width: 1
    }

    contentItem: Rectangle {
        implicitHeight: 18
        color: mainWindow.termAcc
    }

    handle: Rectangle {
        implicitWidth: 14
        implicitHeight: 18
        color: mainWindow.termFg
        border.color: mainWindow.termMuted
        border.width: 1
        radius: 2
    }
}
