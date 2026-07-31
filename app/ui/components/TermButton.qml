// TermButton.qml — terminal-style button with tooltip support
import QtQuick
import QtQuick.Controls

Button {
    id: control
    font.family: "Consolas"
    font.pixelSize: 11
    flat: true

    // Tooltip support — set tooltip property on any TermButton
    property string tooltip: ""
    
    ToolTip.visible: tooltip.length > 0 && hovered
    ToolTip.delay: 500
    ToolTip.text: tooltip
    ToolTip.timeout: 3000

    contentItem: Text {
        text: control.text
        color: control.hovered ? mainWindow.termAcc : mainWindow.termFg
        font: control.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        color: control.hovered ? Qt.rgba(0.2, 0.8, 0.2, 0.15) : "transparent"
        border.color: control.hovered ? mainWindow.termMuted : "transparent"
        border.width: 1
        implicitHeight: 24
        implicitWidth: 60
    }
}
