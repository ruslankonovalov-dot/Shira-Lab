// TermTextField.qml — terminal-style text input with placeholder + tooltip
import QtQuick
import QtQuick.Controls

TextField {
    id: control
    font.family: "Consolas"
    font.pixelSize: 11
    color: mainWindow.termFg
    placeholderTextColor: mainWindow.termMuted
    selectByMouse: true
    
    property string tooltip: ""
    ToolTip.visible: tooltip.length > 0 && hovered
    ToolTip.delay: 800
    ToolTip.text: tooltip

    background: Rectangle {
        color: Qt.darker(mainWindow.termBg, 1.5)
        border.color: control.activeFocus ? mainWindow.termAcc : mainWindow.termMuted
        border.width: 1
        implicitHeight: 28
    }
}
