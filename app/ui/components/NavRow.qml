// NavRow.qml — v1.0.0 Production upgrade
// Added: i18n support (Bridge.tr()), tooltips, keyboard shortcut hints
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Rectangle {
    color: mainWindow.termBg

    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: mainWindow.termAcc
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        spacing: 12

        Repeater {
            // v1.0.0: Use i18n keys — labels will be translated by Bridge.tr()
            model: [
                { "tab": "home",        "key": "nav.home",        "shortcut": "Ctrl+1" },
                { "tab": "aim",         "key": "nav.aim",         "shortcut": "Ctrl+2" },
                { "tab": "clicker",     "key": "nav.clicker",     "shortcut": "Ctrl+3" },
                { "tab": "macro",       "key": "nav.macro",       "shortcut": "Ctrl+4" },
                { "tab": "recorder",    "key": "nav.recorder",    "shortcut": "Ctrl+5" },
                { "tab": "gamepad",     "key": "nav.gamepad",     "shortcut": "Ctrl+6" },
                { "tab": "pico",        "key": "nav.pico",        "shortcut": "Ctrl+7" },
                { "tab": "settings",    "key": "nav.settings",    "shortcut": "Ctrl+8" }
            ]

            Item {
                id: tabItem
                width: tabText.implicitWidth + 32  // 16px left + 16px right for bars
                height: 26

                // v1.0.0: Tooltip with shortcut hint
                ToolTip {
                    text: mainWindow.tr(modelData.key)
                        + "  (" + modelData.shortcut + ")"
                    delay: 500
                    timeout: 2000
                    visible: tabMouseArea.containsMouse
                }

                Timer {
                    id: blinkTimer
                    interval: 500
                    running: mainWindow.currentTab === modelData.tab
                    repeat: true
                    onTriggered: blinkVisible = !blinkVisible
                }

                property bool blinkVisible: true

                Row {
                    anchors.centerIn: parent
                    spacing: 4

                    // Left bar (reserved space, visible only when active+blinking)
                    Text {
                        id: leftBar
                        text: mainWindow.tr("lbl.nav_sep")
                        color: mainWindow.currentTab === modelData.tab && blinkVisible ? mainWindow.termAcc : "transparent"
                        font.family: "Consolas"
                        font.pixelSize: 11
                        font.bold: true
                    }

                    Text {
                        id: tabText
                        anchors.verticalCenter: parent.verticalCenter
                        // v0.16.6 fix: Use mainWindow.tr() (not Bridge.tr()) so QML re-evaluates on language change
                        // mainWindow.tr() references Bridge.currentLang which has notify=langChanged
                        text: mainWindow.tr(modelData.key)
                        color: mainWindow.currentTab === modelData.tab ? mainWindow.termAcc : mainWindow.termFg
                        font.family: "Consolas"
                        font.pixelSize: 11
                        font.bold: mainWindow.currentTab === modelData.tab
                    }

                    // Right bar (reserved space, visible only when active+blinking)
                    Text {
                        id: rightBar
                        text: mainWindow.tr("lbl.nav_sep")
                        color: mainWindow.currentTab === modelData.tab && blinkVisible ? mainWindow.termAcc : "transparent"
                        font.family: "Consolas"
                        font.pixelSize: 11
                        font.bold: true
                    }
                }

                MouseArea {
                    id: tabMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: mainWindow.switchTab(modelData.tab)
                }
            }
        }
    }
}
