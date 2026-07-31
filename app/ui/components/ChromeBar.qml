// ChromeBar.qml — кастомный тайтл-бар с нативным drag и кнопкой pin
// Кнопки: PIN (topmost), MINIMIZE, CLOSE. Maximize убран (не используется).
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: chromeBar
    color: mainWindow.termBg
    height: 32

    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: mainWindow.termAcc
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 6
        spacing: 10

        Text {
            text: mainWindow.tr("lbl.chrome_title")
            color: mainWindow.termAcc
            font.family: "Consolas"
            font.pixelSize: 12
            font.bold: true
            Layout.fillWidth: true
        }

        Row {
            spacing: 2
            Layout.alignment: Qt.AlignRight

            // ── Кнопка PIN / UNPIN (app topmost) ──
            Rectangle {
                width: 36
                height: 24
                color: pinArea.containsMouse ? Qt.rgba(0.2, 0.8, 0.2, 0.15) : (mainWindow.isPinned ? Qt.rgba(0.2, 0.8, 0.2, 0.1) : "transparent")
                border.color: pinArea.containsMouse ? mainWindow.termBorder : (mainWindow.isPinned ? mainWindow.termAcc : "transparent")
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: mainWindow.isPinned ? mainWindow.tr("lbl.chrome_pin") : mainWindow.tr("lbl.chrome_pin")
                    color: mainWindow.isPinned ? mainWindow.termSuccess : mainWindow.termFg
                    font.family: "Consolas"
                    font.pixelSize: 10
                    font.bold: true
                }
                MouseArea {
                    id: pinArea
                    anchors.fill: parent
                    hoverEnabled: true
                    z: 100  // ensure above drag area
                    onClicked: {
                        var newPin = Bridge.toggleWindowPin()
                        mainWindow.isPinned = newPin
                    }
                }
            }

            // ── Minimize button ──
            Rectangle {
                width: 28
                height: 24
                color: minArea.containsMouse ? Qt.rgba(0.2, 0.8, 0.2, 0.15) : "transparent"
                border.color: minArea.containsMouse ? mainWindow.termBorder : "transparent"
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: mainWindow.tr("lbl.chrome_min")
                    color: mainWindow.termFg
                    font.family: "Consolas"
                    font.pixelSize: 12
                }
                MouseArea {
                    id: minArea
                    anchors.fill: parent
                    hoverEnabled: true
                    z: 100  // ensure above drag area
                    onClicked: {
                        Bridge.windowMinimize()
                    }
                }
            }

            // ── Close button ──
            Rectangle {
                width: 28
                height: 24
                color: closeArea.containsMouse ? Qt.rgba(1, 0, 0, 0.2) : "transparent"
                border.color: closeArea.containsMouse ? mainWindow.termDanger : "transparent"
                border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: mainWindow.tr("lbl.chrome_close")
                    color: mainWindow.termDanger
                    font.family: "Consolas"
                    font.pixelSize: 12
                }
                MouseArea {
                    id: closeArea
                    anchors.fill: parent
                    hoverEnabled: true
                    z: 100  // ensure above drag area
                    onClicked: {
                        Bridge.windowClose()
                    }
                }
            }
        }
    }

    // Нативный drag — плавный, без прыжков.
    // This MouseArea is BEHIND the buttons (lower z-order). It covers the
    // left part of the bar but NOT the button area on the right.
    // rightMargin 150 ensures no overlap with buttons (PIN 36 + min 28 + close 28 + spacing 4 + margin 6 = 102, 150 gives extra safety).
    MouseArea {
        anchors.fill: parent
        anchors.rightMargin: 150
        z: 1  // below buttons (z=100)
        onPressed: mainWindow.startSystemMove()
    }
}
