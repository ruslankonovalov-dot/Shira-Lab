// OverlayHUD.qml -- compact overlay showing active script
// Always-on-top (highest priority, above everything including the app).
// Position: bottom-left of work area (never overlaps taskbar).
// Has movement lock (LOC/MOV) + minimize/expand toggle.
// NO close button -- overlay disable is in tray settings.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: overlayRoot
    objectName: "overlayHUD"
    title: "ShiraOverlay"  // unique title -- prevents find_app_hwnd from matching this window
    width: 360
    height: minimized ? 24 : 72  // compact mode: title bar only
    visible: false

    // NO Qt.Tool flag -- that causes overlay to hide when app minimizes.
    // WS_EX_TOOLWINDOW (set from Python) replaces it: keeps overlay off taskbar
    // and Alt+Tab without the parent-minimize-hide behavior.
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint
    color: "transparent"

    // --- Movement lock (overlay's own "pin" -- completely independent from app pin) ---
    property bool movementLocked: true

    // --- Minimized state: when true, overlay shrinks to just title bar ---
    property bool minimized: false

    // --- NEW: Multi-monitor support (v1.0.0) -----------------
    // -1 = auto (use monitor where the app window is located)
    // 0..N = specific monitor index
    property int monitorIndex: -1
    property var monitors: []

    // --- Palette -- bound from mainWindow (theme sync) ---
    property color termBg: "#000000"
    property color termFg: "#00ff41"
    property color termAcc: "#39ff14"
    property color termMuted: "#008f11"
    property color termSuccess: "#00ff41"
    property color termDanger: "#ff0040"
    property color termWarning: "#ffee00"

    // --- Active module tracking ---
    property var activeModule: null
    property string cpsText: "--"
    property string timeText: "00:00"

    onVisibleChanged: {
        if (visible) {
            // v1.0.0: Refresh monitors list first (needed for multi-monitor positioning)
            refreshMonitors()
            // Position using Win32 work area (excludes taskbar) -- most reliable
            positionOverlay()
        } else {
            // Sync hide with Python bridge so sync_overlay() doesn't re-show us
            if (typeof Bridge !== 'undefined' && Bridge.overlayVisible) {
                Bridge.toggleOverlayHUD(false)
            }
        }
    }

    // Re-position when minimized state changes (height changes, so y must adjust)
    onMinimizedChanged: {
        positionOverlay()
    }

    // --- Position overlay at bottom-left of work area ---
    // v1.0.0: Multi-monitor support -- if monitorIndex >= 0, position on
    // that specific monitor; if -1, auto-detect via app window's monitor.
    function positionOverlay() {
        try {
            var area = null

            if (overlayRoot.monitorIndex >= 0 && overlayRoot.monitors.length > overlayRoot.monitorIndex) {
                // Use specific monitor — get_monitors returns "width"/"height" keys
                var m = overlayRoot.monitors[overlayRoot.monitorIndex]
                area = { x: m.x, y: m.y, width: m.width, height: m.height }
            } else if (overlayRoot.monitorIndex === -1) {
                // Auto: use monitor where the app window is located
                try {
                    var appHwnd = Bridge.getHwnd()
                    if (appHwnd > 0) {
                        var r = Bridge.getMonitorForWindow(appHwnd)
                        if (r && r.ok && r.monitor) {
                            var mon = r.monitor
                            // Monitor dict uses "width"/"height" keys
                            area = { x: mon.x, y: mon.y, width: mon.width, height: mon.height }
                        }
                    }
                } catch(e) {
                    console.warn("Auto-monitor detection failed:", e)
                }
            }

            if (!area) {
                // Fallback: use default work area
                // getWorkArea returns {"ok": true, "x": ..., "y": ..., "width": ..., "height": ...}
                var wa = Bridge.getWorkArea()
                if (wa && wa.ok !== undefined) {
                    area = { x: wa.x, y: wa.y, width: wa.width, height: wa.height }
                } else {
                    area = wa  // might already be in the right format
                }
            }

            // Position at BOTTOM-LEFT of work area
            overlayRoot.x = (area.x || 0) + 16
            overlayRoot.y = (area.y || 0) + (area.height || 1080) - overlayRoot.height - 8
        } catch(e) {
            // Final fallback: use Screen attached property
            var sh = Screen.desktopAvailableHeight
            var sy = Screen.virtualY
            if (sh > 0) {
                overlayRoot.x = 16
                overlayRoot.y = sy + sh - overlayRoot.height - 8
            }
        }
    }

    // --- NEW: Refresh monitors list ------------------------------------
    function refreshMonitors() {
        try {
            var r = Bridge.getMonitors()
            if (r.ok) {
                overlayRoot.monitors = r.monitors || []
            }
        } catch(e) {
            console.warn("Failed to get monitors:", e)
        }
    }

    // NOTE: refreshMonitors() is called from onVisibleChanged above (merged handler).

    // --- Clamp position to work area after drag (debounced) ---
    // Uses a debounce timer: fires 300ms after the LAST position change.
    // During active drag, position changes continuously, so the timer keeps
    // resetting. Only when drag stops (no changes for 300ms) does the clamp fire.
    Timer {
        id: clampTimer
        interval: 300
        repeat: false
        onTriggered: {
            if (!overlayRoot.visible) return
            try {
                var result = Bridge.clampOverlayPosition(overlayRoot.x, overlayRoot.y, overlayRoot.width, overlayRoot.height)
                if (result.x !== overlayRoot.x || result.y !== overlayRoot.y) {
                    overlayRoot.x = result.x
                    overlayRoot.y = result.y
                }
            } catch(e) {}
        }
    }

    // Start debounce timer on position change (fires after 300ms of no changes)
    onXChanged: clampTimer.restart()
    onYChanged: clampTimer.restart()

    // --- Background ---
    Rectangle {
        id: overlayBg
        anchors.fill: parent
        color: termBg
        border.color: termAcc
        border.width: 1

        // Top accent line
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: termAcc
        }

        // Bottom accent line (hidden in minimized mode)
        Rectangle {
            visible: !minimized
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: termAcc
        }
    }

    // --- Drag area (only when movement is unlocked) ---
    MouseArea {
        id: dragArea
        anchors.fill: parent
        enabled: !movementLocked
        hoverEnabled: true
        z: 1  // below buttons (z=100)

        onPressed: function(mouse) {
            if (!movementLocked) {
                overlayRoot.startSystemMove()
            }
        }
    }

    // --- Content ---
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 4
        spacing: 2

        // --- Row 1: SHIRA + ACTIVE MODULE + BUTTONS (always visible) ---
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            // Status dot
            Text {
                text: activeModule ? "*" : "o"
                color: activeModule ? termSuccess : termMuted
                font.family: "Consolas"
                font.pixelSize: 12
                font.bold: true
            }

            // SHIRA label
            Text {
                text: mainWindow.tr("lbl.overlay_shira")
                color: termAcc
                font.family: "Consolas"
                font.pixelSize: 11
                font.bold: true
            }

            // Separator
            Text {
                text: mainWindow.tr("lbl.overlay_sep")
                color: termMuted
                font.family: "Consolas"
                font.pixelSize: 11
            }

            // Active module name or IDLE
            Text {
                text: activeModule ? activeModule.label + " [" + activeModule.key + "]" : mainWindow.tr("overlay.idle")
                color: activeModule ? termAcc : termMuted
                font.family: "Consolas"
                font.pixelSize: 11
                font.bold: true
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            // -- LOC/MOV button (movement lock -- independent from app pin) --
            Rectangle {
                width: 28
                height: 18
                color: pinMouseArea.containsMouse ? Qt.rgba(0.2, 0.8, 0.2, 0.2) : "transparent"
                border.color: pinMouseArea.containsMouse ? termAcc : (movementLocked ? termAcc : "transparent")
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: movementLocked ? "LOC" : "MOV"
                    color: movementLocked ? termSuccess : termWarning
                    font.family: "Consolas"
                    font.pixelSize: 9
                    font.bold: true
                }

                MouseArea {
                    id: pinMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    z: 100  // above drag area
                    onClicked: {
                        movementLocked = !movementLocked
                    }
                }
            }

            // -- MINIMIZE/EXPAND toggle button --
            // When expanded: [_] (minimize to title bar only)
            // When minimized: [□] (expand to full overlay)
            Rectangle {
                width: 28
                height: 18
                color: minToggleMouseArea.containsMouse ? Qt.rgba(0.2, 0.8, 0.2, 0.2) : "transparent"
                border.color: minToggleMouseArea.containsMouse ? termAcc : "transparent"
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: minimized ? "[+]" : "[-]"
                    color: minimized ? termWarning : termFg
                    font.family: "Consolas"
                    font.pixelSize: 10
                    font.bold: true
                }

                MouseArea {
                    id: minToggleMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    z: 100  // above drag area
                    onClicked: {
                        minimized = !minimized
                    }
                }
            }
        }

        // --- Row 2: Detail line (hidden in minimized mode) ---
        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            visible: !minimized

            Text {
                text: activeModule ? activeModule.detail : mainWindow.tr("overlay.no_active")
                color: activeModule ? termFg : termMuted
                font.family: "Consolas"
                font.pixelSize: 9
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            // CPS + Time (right-aligned)
            Text {
                text: mainWindow.tr("lbl.cps_timer") + cpsText + " | " + timeText
                color: termMuted
                font.family: "Consolas"
                font.pixelSize: 9
            }
        }
    }

    // --- Status Polling -- uses Bridge.overlayStatusUpdate signal (thread-safe) ---
    Connections {
        target: Bridge
        function onOverlayStatusUpdate(status) {
            try {
                // status is now a native QVariantMap (JS object), no JSON parsing needed
                var modules = [
                    { mod: "clicker", label: mainWindow.tr("gamepad.clicker"), key: "F6", status: status.clicker || {}, isRunning: false, detail: "" },
                    { mod: "aim", label: mainWindow.tr("gamepad.aim"), key: "F9", status: status.aim || {}, isRunning: false, detail: "" },
                    { mod: "macro", label: mainWindow.tr("gamepad.macro"), key: "RCtrl", status: status.macro || {}, isRunning: false, detail: "" },
                    { mod: "recorder", label: mainWindow.tr("gamepad.rec"), key: "F7", status: status.recorder || {}, isRunning: false, detail: "" }
                ]

                for (var i = 0; i < modules.length; i++) {
                    var m = modules[i]
                    if (m.mod === "recorder") {
                        m.isRunning = m.status.is_recording || m.status.is_playing || false
                    } else {
                        m.isRunning = m.status.is_running || false
                    }

                    if (m.isRunning) {
                        if (m.mod === "clicker")
                            m.detail = (m.status.click_count || 0) + " " + mainWindow.tr("common.clicks") + " | " + (m.status.interval_ms || 100) + "ms"
                        else if (m.mod === "aim")
                            m.detail = mainWindow.tr("gamepad.conf") + ": " + (m.status.confidence || 0.6) + " | " + (m.status.last_log || "tracking")
                        else if (m.mod === "macro")
                            m.detail = mainWindow.tr("gamepad.mode") + ": " + (m.status.run_mode || "SEQ") + " | " + (m.status.actions_count || 0) + " " + mainWindow.tr("gamepad.acts")
                        else if (m.mod === "recorder") {
                            if (m.status.is_recording) m.detail = mainWindow.tr("gamepad.rec") + ": " + (m.status.events_count || 0) + " " + mainWindow.tr("gamepad.evt")
                            else if (m.status.is_playing) m.detail = mainWindow.tr("gamepad.play") + ": " + (m.status.events_count || 0) + " " + mainWindow.tr("gamepad.evt")
                        }
                    }
                }

                // Find first active module
                var active = null
                for (var i = 0; i < modules.length; i++) {
                    if (modules[i].isRunning) {
                        active = modules[i]
                        break
                    }
                }
                activeModule = active

                // CPS + elapsed time from clicker
                var cs = status.clicker || {}
                if (cs.cps !== undefined) {
                    cpsText = cs.cps.toFixed(1)
                }
                if (cs.elapsed !== undefined) {
                    var mn = Math.floor(cs.elapsed / 60)
                    var sc = Math.floor(cs.elapsed % 60)
                    timeText = (mn < 10 ? "0" + mn : mn) + ":" + (sc < 10 ? "0" + sc : sc)
                }
            } catch(e) {}
        }
    }

    // --- Status Timer -- polls module statuses every 300ms (REPLACED BY THREAD-SAFE SIGNAL) ---
    // Timer {
    //     id: statusTimer
    //     interval: 300
    //     running: false
    //     repeat: true
    //     onTriggered: { ... }
    // }
}
