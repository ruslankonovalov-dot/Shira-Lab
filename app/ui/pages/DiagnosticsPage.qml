// DiagnosticsPage.qml -- v1.0.0 Production upgrade
// Features added:
//   [OK] Crash Reports viewer (list + detail dialog)
//   [OK] Performance Profiler (CPU/MEM/Threads/Uptime)
//   [OK] Multi-monitor info (list of monitors)
//   [OK] Structured diagnostics (parsed JSON instead of raw text)
//   [OK] Tooltips on all buttons
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    color: mainWindow.termBg

    property var diagData: ({})
    property var perfData: ({})
    property var crashList: []
    property var monitorsList: []

    Component.onCompleted: {
        refreshAll()
    }

    // v1.0.0 i18n: Rebuild content on language change
    Connections {
        target: Bridge
        function onLangChanged() {
            refreshAll()
        }
    }

    function refreshAll() {
        refreshDiagnostics()
        refreshPerformance()
        refreshCrashes()
        refreshMonitors()
    }

    function refreshDiagnostics() {
        var r = Bridge.getDiagnostics()
        diagData = r
        diagText.text = JSON.stringify(r, null, 2)
    }

    function refreshPerformance() {
        var r = Bridge.getPerformanceProfile()
        perfData = r
        if (r.ok) {
            perfLabel.text = mainWindow.tr("diag.cpu") + " " + r.cpu_percent.toFixed(1) + "%  |  "
                + mainWindow.tr("diag.memory") + " " + r.memory_mb.toFixed(1) + " MB  |  "
                + mainWindow.tr("diag.threads") + " " + r.threads + "  |  "
                + mainWindow.tr("diag.uptime") + " " + r.uptime_sec + "s"
        } else {
            perfLabel.text = "// " + mainWindow.tr("diag.perf_unavailable")
        }
    }

    function refreshCrashes() {
        var r = Bridge.listCrashReports()
        crashList = r.crashes || []
        crashCountLabel.text = mainWindow.tr("diag.crash_count_prefix") + crashList.length
    }

    function refreshMonitors() {
        var r = Bridge.getMonitors()
        monitorsList = r.monitors || []
        monitorCountLabel.text = mainWindow.tr("diag.monitors_count") + monitorsList.length
    }

    ScrollView {
        id: scrollView
        anchors.fill: parent
        clip: true
        contentWidth: scrollView.width

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AlwaysOn
            width: 10
        }

        ColumnLayout {
            id: contentLayout
            width: scrollView.width
            spacing: 16

            // --- Action Bar ------------------------------------------------
            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                TermButton {
                    text: mainWindow.tr("btn.refresh_all")
                    tooltip: mainWindow.tr("tip.diag_refresh_all")
                    Layout.preferredWidth: 140
                    Layout.preferredHeight: 34
                    font.pixelSize: 11
                    onClicked: refreshAll()
                }
                TermButton {
                    text: mainWindow.tr("btn.panic_stop")
                    tooltip: mainWindow.tr("tip.diag_panic_stop")
                    Layout.preferredWidth: 140
                    Layout.preferredHeight: 34
                    font.pixelSize: 11
                    onClicked: {
                        var r = Bridge.panicStop()
                        consoleLog.addLog("WARN", "DIAG", "PANIC STOP triggered from Diagnostics")
                    }
                }
                Item { Layout.fillWidth: true }
            }

            // --- Performance Profiler Card ---------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("diagnostics.perf_profiler")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text {
                        id: perfLabel
                        text: "// " + mainWindow.tr("home.click_refresh")
                        color: mainWindow.termAcc
                        font.family: "Consolas"
                        font.pixelSize: 11
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TermButton {
                            text: mainWindow.tr("btn.measure_now")
                            tooltip: mainWindow.tr("tip.diag_measure_now")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: refreshPerformance()
                        }
                        Item { Layout.fillWidth: true }
                    }

                    // Detailed metrics grid
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 4
                        columnSpacing: 16
                        rowSpacing: 6
                        visible: perfData.ok || false

                        Text { text: mainWindow.tr("diag.cpu"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                        Text { text: (perfData.cpu_percent || 0).toFixed(1) + "%"; color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10 }

                        Text { text: mainWindow.tr("diag.memory"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                        Text { text: (perfData.memory_mb || 0).toFixed(1) + " MB"; color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10 }

                        Text { text: mainWindow.tr("diag.threads"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                        Text { text: (perfData.threads || 0).toString(); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10 }

                        Text { text: mainWindow.tr("diag.uptime"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                        Text { text: (perfData.uptime_sec || 0) + " " + mainWindow.tr("common.sec"); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10 }

                        Text { text: mainWindow.tr("diag.clicker_cps"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                        Text { text: (perfData.clicker_cps || 0).toFixed(1); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10 }

                        Text { text: mainWindow.tr("diag.aim_fps"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                        Text { text: (perfData.aim_fps || 0).toFixed(1); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10 }

                        Text { text: mainWindow.tr("diag.app_hwnd"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                        Text { text: (diagData.app_hwnd || 0).toString(); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10 }

                        Text { text: mainWindow.tr("diag.overlay_hwnd"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                        Text { text: (diagData.overlay_hwnd || 0).toString(); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10 }
                    }
                }
            }

            // --- Crash Reports Card ----------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("diagnostics.crash_reports")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text {
                        id: crashCountLabel
                        text: mainWindow.tr("diag.crash_count") + ": " + crashList.length
                        color: mainWindow.termAcc
                        font.family: "Consolas"
                        font.pixelSize: 11
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TermButton {
                            text: mainWindow.tr("btn.refresh")
                            tooltip: mainWindow.tr("tip.refresh_crashes")
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: refreshCrashes()
                        }
                        TermButton {
                            text: mainWindow.tr("btn.clear_all")
                            tooltip: mainWindow.tr("tip.clear_all_crashes_diag")
                            Layout.preferredWidth: 120
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            enabled: crashList.length > 0
                            opacity: enabled ? 1.0 : 0.3
                            onClicked: {
                                var r = Bridge.clearAllCrashReports()
                                if (r.ok) {
                                    consoleLog.addLog("OK", "DIAG", "Cleared " + r.deleted + " crash report(s)")
                                    refreshCrashes()
                                }
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    // Crash list
                    ListView {
                        id: crashListView
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(crashList.length * 60, 240)
                        model: crashList
                        clip: true
                        spacing: 4
                        visible: crashList.length > 0

                        delegate: Rectangle {
                            width: crashListView.width
                            height: 56
                            color: Qt.rgba(1, 0, 0, 0.05)
                            border.color: mainWindow.termDanger
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 8

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Text {
                                        text: mainWindow.tr("diag.exception_prefix") + modelData.exception_type + ": " + modelData.exception_message
                                        color: mainWindow.termDanger
                                        font.family: "Consolas"
                                        font.pixelSize: 10
                                        font.bold: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        text: modelData.timestamp + "  |  " + modelData.file
                                        color: mainWindow.termMuted
                                        font.family: "Consolas"
                                        font.pixelSize: 9
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }

                                TermButton {
                                    text: mainWindow.tr("btn.view")
                                    tooltip: mainWindow.tr("tip.view_crash")
                                    Layout.preferredWidth: 60
                                    Layout.preferredHeight: 24
                                    font.pixelSize: 10
                                    onClicked: {
                                        var r = Bridge.readCrashReport(modelData.file)
                                        if (r.ok) {
                                            crashDetailDialog.report = r.report
                                            crashDetailDialog.visible = true
                                        }
                                    }
                                }
                                TermButton {
                                    text: mainWindow.tr("lbl.delete_btn")
                                    tooltip: mainWindow.tr("tip.clear_crash")
                                    Layout.preferredWidth: 32
                                    Layout.preferredHeight: 24
                                    font.pixelSize: 10
                                    onClicked: {
                                        var r = Bridge.deleteCrashReport(modelData.file)
                                        refreshCrashes()
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        text: "// " + mainWindow.tr("diag.no_crashes")
                        color: mainWindow.termMuted
                        font.family: "Consolas"
                        font.pixelSize: 10
                        Layout.fillWidth: true
                        visible: crashList.length === 0
                    }
                }
            }

            // --- Multi-Monitor Card ----------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("diagnostics.multi_monitor")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text {
                        id: monitorCountLabel
                        text: mainWindow.tr("diag.monitors_count") + ": " + monitorsList.length
                        color: mainWindow.termAcc
                        font.family: "Consolas"
                        font.pixelSize: 11
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TermButton {
                            text: mainWindow.tr("btn.refresh")
                            tooltip: mainWindow.tr("tip.refresh_monitors_diag")
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: refreshMonitors()
                        }
                        Item { Layout.fillWidth: true }
                    }

                    // Monitors list
                    Repeater {
                        model: monitorsList

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 36
                            color: modelData.is_primary ? Qt.rgba(0.2, 1.0, 0.2, 0.08) : "transparent"
                            border.color: modelData.is_primary ? mainWindow.termAcc : mainWindow.termMuted
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 12

                                Text {
                                    text: (modelData.is_primary ? "* " : "  ") + mainWindow.tr("diag.monitor_n").replace("{}", (index + 1).toString())
                                    color: (modelData.is_primary || false) ? mainWindow.termAcc : mainWindow.termFg
                                    font.family: "Consolas"
                                    font.pixelSize: 11
                                    font.bold: (modelData.is_primary || false)
                                    Layout.preferredWidth: 120
                                }
                                Text {
                                    text: modelData.w + mainWindow.tr("diag.resolution_sep") + modelData.h
                                    color: mainWindow.termFg
                                    font.family: "Consolas"
                                    font.pixelSize: 11
                                    Layout.preferredWidth: 120
                                }
                                Text {
                                    text: mainWindow.tr("diag.position_prefix") + modelData.x + ", " + modelData.y + mainWindow.tr("diag.position_suffix")
                                    color: mainWindow.termMuted
                                    font.family: "Consolas"
                                    font.pixelSize: 10
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }
            }

            // --- Raw Diagnostics JSON Card ---------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("diagnostics.raw_diag")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TermButton {
                            text: mainWindow.tr("btn.refresh")
                            tooltip: mainWindow.tr("tip.refresh_diag_json")
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: refreshDiagnostics()
                        }
                        TermButton {
                            text: mainWindow.tr("btn.copy_clipboard")
                            tooltip: mainWindow.tr("tip.copy_diag_json")
                            Layout.preferredWidth: 160
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: {
                                diagText.selectAll()
                                diagText.copy()
                                diagText.deselect()
                                consoleLog.addLog("OK", "DIAG", "Diagnostics copied to clipboard")
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 300
                        clip: true

                        TextArea {
                            id: diagText
                            text: mainWindow.tr("diag.click_refresh")
                            color: mainWindow.termFg
                            font.family: "Consolas"
                            font.pixelSize: 10
                            wrapMode: Text.WrapAnywhere
                            readOnly: true
                            background: Rectangle {
                                color: Qt.darker(mainWindow.termBg, 1.3)
                                border.color: mainWindow.termMuted
                                border.width: 1
                            }
                        }
                    }
                }
            }

            // Bottom spacer
            Item { Layout.fillHeight: true; Layout.fillWidth: true; Layout.minimumHeight: 16 }
        }
    }

    // --- Crash Report Detail Dialog -------------------------------------
    Rectangle {
        id: crashDetailDialog
        property var report: ({})
        visible: false
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.8)
        z: 1000

        MouseArea {
            anchors.fill: parent
            onClicked: crashDetailDialog.visible = false
        }

        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.8
            height: parent.height * 0.8
            color: Qt.darker(mainWindow.termBg, 1.2)
            border.color: mainWindow.termDanger
            border.width: 2

            MouseArea {
                anchors.fill: parent
                onClicked: function(mouse) { mouse.accepted = true }  // Prevent close on inner click
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true

                    Text {
                        text: mainWindow.tr("diag.crash_report_title")
                        color: mainWindow.termDanger
                        font.family: "Consolas"
                        font.pixelSize: 14
                        font.bold: true
                        Layout.fillWidth: true
                    }
                    TermButton {
                        text: mainWindow.tr("diag.close")
                        tooltip: mainWindow.tr("tip.close_diag")
                        Layout.preferredWidth: 80
                        Layout.preferredHeight: 28
                        font.pixelSize: 10
                        onClicked: crashDetailDialog.visible = false
                    }
                }

                // Crash metadata
                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 4

                    Text { text: mainWindow.tr("diag.timestamp"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                    Text { text: crashDetailDialog.report.timestamp || ""; color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10 }

                    Text { text: mainWindow.tr("diag.app_version"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                    Text { text: crashDetailDialog.report.app_version || ""; color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10 }

                    Text { text: mainWindow.tr("diag.python"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                    Text { text: crashDetailDialog.report.python_version || ""; color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10 }

                    Text { text: mainWindow.tr("diag.platform"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                    Text { text: crashDetailDialog.report.platform || ""; color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10 }

                    Text { text: mainWindow.tr("diag.exception"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                    Text {
                        text: (crashDetailDialog.report.exception_type || "") + ": " + (crashDetailDialog.report.exception_message || "")
                        color: mainWindow.termDanger
                        font.family: "Consolas"
                        font.pixelSize: 10
                        font.bold: true
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                // Separator
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: mainWindow.termMuted
                    opacity: 0.3
                }

                Text {
                    text: mainWindow.tr("diag.traceback")
                    color: mainWindow.termMuted
                    font.family: "Consolas"
                    font.pixelSize: 10
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    TextArea {
                        text: crashDetailDialog.report.traceback || ""
                        color: mainWindow.termDanger
                        font.family: "Consolas"
                        font.pixelSize: 10
                        wrapMode: Text.WrapAnywhere
                        readOnly: true
                        background: Rectangle {
                            color: Qt.rgba(0, 0, 0, 0.5)
                            border.color: mainWindow.termDanger
                            border.width: 1
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    TermButton {
                        text: mainWindow.tr("diag.copy_traceback")
                        tooltip: mainWindow.tr("tip.copy_traceback_diag")
                        Layout.preferredWidth: 140
                        Layout.preferredHeight: 32
                        font.pixelSize: 11
                        onClicked: {
                            // Set text into a temporary TextArea for copy
                            var tb = crashDetailDialog.report.traceback || ""
                            // Use Qt clipboard directly
                            // Simple workaround: use the visible TextArea
                            tracebackCopyHelper.text = tb
                            tracebackCopyHelper.selectAll()
                            tracebackCopyHelper.copy()
                            tracebackCopyHelper.deselect()
                            consoleLog.addLog("OK", "DIAG", "Traceback copied to clipboard")
                        }
                    }
                    Item { Layout.fillWidth: true }
                }
            }
        }

        // Hidden helper for clipboard copy
        TextArea {
            id: tracebackCopyHelper
            visible: false
            text: ""
        }
    }
}
