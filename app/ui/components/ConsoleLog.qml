// ConsoleLog.qml — terminal-style log console
// Shows real-time logs from backend: clicks sent, macros executed, errors, etc.
// Auto-scrolls to bottom, color-coded by log level, timestamped.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: consoleRoot
    color: Qt.darker(mainWindow.termBg, 1.3)
    border.color: mainWindow.termMuted
    border.width: 1

    // Log entries model — appended from Bridge.logMessage signal
    property var logModel: []

    // Max entries to keep (prevents memory leak)
    property int maxEntries: 500

    // Sources allowed to show in this console (empty = show nothing)
    // Set dynamically by main.qml based on current tab
    property var allowedSources: []

    // Rate limiting: max 10 log entries per second
    property int maxLogsPerSecond: 10
    property var _logTimestamps: []
    property int _droppedCount: 0

    // Add a log entry — called from main.qml when Bridge.logMessage is emitted
    function addLog(level, source, message) {
        // Filter by allowedSources — if empty, don't show anything
        if (allowedSources.length === 0) return
        if (allowedSources.indexOf(source) === -1) return

        // Rate limiting: max N entries per second
        var now = Date.now()
        _logTimestamps = _logTimestamps.filter(function(ts) { return now - ts < 1000 })
        if (_logTimestamps.length >= maxLogsPerSecond) {
            _droppedCount++
            // Log dropped count every 5 seconds
            if (_droppedCount % 50 === 1) {
                console.log("ConsoleLog: dropped " + _droppedCount + " entries (rate limit)")
            }
            return
        }
        _logTimestamps.push(now)

        var timestamp = new Date().toLocaleTimeString(Qt.locale(), "HH:mm:ss.zzz")
        var entry = {
            timestamp: timestamp,
            level: level,
            source: source,
            message: message
        }
        logModel.push(entry)
        // Trim if too many entries
        if (logModel.length > maxEntries) {
            logModel = logModel.slice(logModel.length - maxEntries)
        }
        // Trigger ListView refresh
        logList.model = logModel
        // Auto-scroll to bottom
        Qt.callLater(function() {
            logList.positionViewAtEnd()
        })
    }

    // Clear all logs
    function clearLogs() {
        logModel = []
        logList.model = logModel
    }

    // Re-filter logs when allowedSources changes
    onAllowedSourcesChanged: {
        // Don't clear — just re-render. New logs will be filtered by addLog.
        logList.model = logModel
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 4
        spacing: 2

        // Header row
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Text {
                text: mainWindow.tr("lbl.console")
                color: mainWindow.termAcc
                font.family: "Consolas"
                font.pixelSize: 11
                font.bold: true
                Layout.fillWidth: true
            }

            Text {
                text: mainWindow.tr("lbl.clear")
                color: mainWindow.termDanger
                font.family: "Consolas"
                font.pixelSize: 9
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: consoleRoot.clearLogs()
                }
            }
        }

        // Separator
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: mainWindow.termMuted
        }

        // Log list
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ListView {
                id: logList
                model: consoleRoot.logModel
                spacing: 0
                cacheBuffer: 5000

                delegate: Rectangle {
                    width: logList.width
                    height: 18
                    color: "transparent"

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 4
                        spacing: 6

                        Text {
                            text: modelData.timestamp
                            color: mainWindow.termMuted
                            font.family: "Consolas"
                            font.pixelSize: 9
                            width: 70
                        }

                        Text {
                            text: "[" + modelData.source + "]"
                            color: modelData.level === "ERROR" ? mainWindow.termDanger :
                                   modelData.level === "WARN" ? mainWindow.termWarning :
                                   modelData.level === "OK" ? mainWindow.termSuccess :
                                   mainWindow.termAcc
                            font.family: "Consolas"
                            font.pixelSize: 9
                            font.bold: true
                            width: 80
                            elide: Text.ElideRight
                        }

                        Text {
                            text: modelData.message
                            color: modelData.level === "ERROR" ? mainWindow.termDanger :
                                   modelData.level === "WARN" ? mainWindow.termWarning :
                                   modelData.level === "OK" ? mainWindow.termSuccess :
                                   mainWindow.termFg
                            font.family: "Consolas"
                            font.pixelSize: 9
                            width: parent.width - 160 - 4
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }
}
