// HotkeyRow.qml — v1.0.0 UX upgrade
// Added: tooltips per action, key recording (press any key to capture)
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    id: hotkeyRow
    property string actionName: ""
    property string actionLabel: ""
    property string currentKey: ""
    property string currentMode: "TOGGLE"

    // NEW: Tooltip descriptions per action
    property string actionTooltip: {
        var tips = {
            "clicker_toggle": mainWindow.tr("tip.clicker_toggle"),
            "aim_toggle": mainWindow.tr("tip.aim_toggle"),
            "macro_start": mainWindow.tr("tip.macro_start"),
            "macro_stop": mainWindow.tr("tip.macro_stop"),
            "recorder_start": mainWindow.tr("tip.recorder_start"),
            "recorder_stop": mainWindow.tr("tip.recorder_stop"),
            "app_show": mainWindow.tr("tip.app_show"),
            "panic_stop": mainWindow.tr("tip.panic_stop")
        }
        return tips[actionName] || mainWindow.tr("tip.bind_hotkey") + " " + actionLabel
    }

    width: parent ? parent.width : 600
    height: 36
    color: Qt.darker(mainWindow.termBg, 1.2)
    border.color: mainWindow.termMuted
    border.width: 1

    ToolTip {
        text: hotkeyRow.actionTooltip
        delay: 500
        timeout: 5000
        visible: mouseArea.containsMouse
        parent: hotkeyRow
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        propagateComposedEvents: true
        onClicked: function(mouse) { mouse.accepted = false }
        onPressed: function(mouse) { mouse.accepted = false }
        onReleased: function(mouse) { mouse.accepted = false }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 6
        spacing: 8

        Text {
            text: actionLabel
            color: mainWindow.termFg
            font.family: "Consolas"
            font.pixelSize: 11
            Layout.preferredWidth: 180
        }

        TermTextField {
            id: keyInput
            text: currentKey
            Layout.fillWidth: true
            placeholderText: mainWindow.tr("lbl.hotkey_hint")

            // NEW: Key recording mode — click to focus, then press any key
            MouseArea {
                anchors.fill: parent
                onClicked: keyInput.forceActiveFocus()
            }

            // Capture key presses for binding
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Escape) {
                    keyInput.text = currentKey
                    keyInput.focus = false
                    event.accepted = true
                    return
                }
                if (event.key === Qt.Key_Backspace) {
                    keyInput.text = ""
                    event.accepted = true
                    return
                }

                // Build key string from event
                var parts = []
                if (event.modifiers & Qt.ControlModifier) parts.push("ctrl")
                if (event.modifiers & Qt.AltModifier) parts.push("alt")
                if (event.modifiers & Qt.ShiftModifier) parts.push("shift")

                // Map Qt key code to key name
                var keyName = ""
                switch (event.key) {
                    case Qt.Key_F1: keyName = "f1"; break
                    case Qt.Key_F2: keyName = "f2"; break
                    case Qt.Key_F3: keyName = "f3"; break
                    case Qt.Key_F4: keyName = "f4"; break
                    case Qt.Key_F5: keyName = "f5"; break
                    case Qt.Key_F6: keyName = "f6"; break
                    case Qt.Key_F7: keyName = "f7"; break
                    case Qt.Key_F8: keyName = "f8"; break
                    case Qt.Key_F9: keyName = "f9"; break
                    case Qt.Key_F10: keyName = "f10"; break
                    case Qt.Key_F11: keyName = "f11"; break
                    case Qt.Key_F12: keyName = "f12"; break
                    case Qt.Key_Space: keyName = "space"; break
                    case Qt.Key_Return: keyName = "enter"; break
                    case Qt.Key_Tab: keyName = "tab"; break
                    case Qt.Key_Escape: keyName = "escape"; break
                    case Qt.Key_Insert: keyName = "insert"; break
                    case Qt.Key_Delete: keyName = "delete"; break
                    case Qt.Key_Home: keyName = "home"; break
                    case Qt.Key_End: keyName = "end"; break
                    case Qt.Key_PageUp: keyName = "pageup"; break
                    case Qt.Key_PageDown: keyName = "pagedown"; break
                    case Qt.Key_Left: keyName = "left"; break
                    case Qt.Key_Right: keyName = "right"; break
                    case Qt.Key_Up: keyName = "up"; break
                    case Qt.Key_Down: keyName = "down"; break
                    default:
                        var text = event.text.toLowerCase()
                        if (text.length === 1 && /[a-z0-9]/.test(text)) {
                            keyName = text
                        }
                }

                if (keyName.length > 0) {
                    parts.push(keyName)
                    keyInput.text = parts.join("+")
                }
                event.accepted = true
            }
        }

        TermComboBox {
            id: modeSelect
            model: [mainWindow.tr("common.toggle"), mainWindow.tr("common.hold")]
            currentIndex: currentMode === "HOLD" ? 1 : 0
            Layout.preferredWidth: 100
            tooltip: mainWindow.tr("tip.hold_mode")
        }

        TermButton {
            text: mainWindow.tr("lbl.hotkey_save")
            tooltip: mainWindow.tr("tip.hotkey_save") + " (" + actionName + ")"
            Layout.preferredWidth: 60
            onClicked: {
                var r = Bridge.setHotkey(actionName, keyInput.text, modeSelect.currentText)
                if (r.ok) {
                    mainWindow.statusText = "Hotkey " + actionName + ": " + keyInput.text
                    mainWindow.loadSettings()
                } else {
                    mainWindow.statusText = "Error: " + (r.error || "unknown")
                    keyInput.text = currentKey
                }
            }
        }

        TermButton {
            text: mainWindow.tr("lbl.hotkey_reset")
            tooltip: mainWindow.tr("tip.hotkey_reset")
            Layout.preferredWidth: 60
            onClicked: {
                var r = Bridge.resetHotkey(actionName)
                if (r && r.bindings) {
                    var b = r.bindings[actionName]
                    if (b) {
                        keyInput.text = b.key || ""
                        modeSelect.currentIndex = b.mode === "HOLD" ? 1 : 0
                        mainWindow.loadSettings()
                    }
                }
            }
        }
    }
}
