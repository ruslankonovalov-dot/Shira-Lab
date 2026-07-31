// HomePage.qml -- Dashboard layout
// Logo on top (centered) + scrollable changelog cards (from UpdateData.qml)
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    id: homeRoot
    color: mainWindow.termBg

    // UpdateData component -- contains all changelog entries
    UpdateData {
        id: updateData
    }

    // v1.0.0: System status refresh
    function refreshStatus() {
        // Get performance profile
        try {
            var p = Bridge.getPerformanceProfile()
            if (p.ok) {
                homeCpuLabel.text = mainWindow.tr("home.cpu") + ": " + p.cpu_percent.toFixed(1) + "%"
                homeMemLabel.text = mainWindow.tr("home.mem") + ": " + p.memory_mb.toFixed(1) + " MB"
            }
        } catch(e) {}

        // Get crash count
        try {
            var c = Bridge.listCrashReports()
            if (c.ok) {
                var count = (c.crashes || []).length
                homeCrashLabel.text = mainWindow.tr("home.crashes") + ": " + count
                homeCrashLabel.color = count > 0 ? mainWindow.termDanger : mainWindow.termFg
            }
        } catch(e) {}
    }

    // v1.0.0 i18n: Rebuild models on language change
    Connections {
        target: Bridge
        function onLangChanged() {
            // Update UPDATE banner text if visible
            if (homeUpdateBanner.visible && homeUpdateBanner.downloadUrl.length > 0) {
                homeUpdateLabel.text = mainWindow.tr("home.update_banner") + ": v" + homeUpdateBanner.newVersion
            }
            // Refresh status labels with new translations
            refreshStatus()
        }
    }

    // v1.0.0: Listen for update check results
    Connections {
        target: Bridge
        function onUpdateCheckResult(r) {
            if (r.ok && r.update_available) {
                homeUpdateBanner.newVersion = r.latest_version
                homeUpdateBanner.downloadUrl = r.download_url || ""
                homeUpdateLabel.text = mainWindow.tr("home.update_banner") + ": v" + r.latest_version
                homeUpdateLabel.color = mainWindow.termAcc
            } else if (r.ok) {
                homeUpdateLabel.text = mainWindow.tr("home.update") + ": " + mainWindow.tr("update.up_to_date")
                homeUpdateLabel.color = mainWindow.termFg
            } else {
                homeUpdateLabel.text = mainWindow.tr("home.update") + ": --"
                homeUpdateLabel.color = mainWindow.termMuted
            }
        }
    }

    // Refresh status every 5 seconds
    Timer {
        interval: 5000
        repeat: true
        running: true
        onTriggered: homeRoot.refreshStatus()
    }

    Component.onCompleted: refreshStatus()

    // --- Vertical layout: logo top, cards bottom ---------------------
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 180
            Layout.minimumHeight: 140
            Layout.maximumHeight: 220
            color: "transparent"

            Column {
                anchors.centerIn: parent
                spacing: 8

                // Canvas for pixel-perfect logo rendering
                Canvas {
                    id: logoCanvas
                    width: 420
                    height: 9 * 13
                    anchors.horizontalCenter: parent.horizontalCenter
                    property string logoText: mainWindow.settings.logo_shira || ""
                    property string paletteTrigger: mainWindow.termAcc

                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)
                        ctx.font = "12px Consolas"
                        ctx.fillStyle = mainWindow.termAcc
                        ctx.textBaseline = "top"

                        var lines = logoText.split("\n")
                        var lineHeight = 13

                        var maxWidth = 0
                        for (var i = 0; i < lines.length; i++) {
                            var metrics = ctx.measureText(lines[i])
                            if (metrics.width > maxWidth) maxWidth = metrics.width
                        }

                        var startX = (width - maxWidth) / 2
                        for (var i = 0; i < lines.length; i++) {
                            ctx.fillText(lines[i], startX, i * lineHeight)
                        }
                    }

                    Component.onCompleted: requestPaint()
                    onLogoTextChanged: requestPaint()
                    onPaletteTriggerChanged: requestPaint()
                }

                // Version + status row
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 16

                    Text {
                        text: "v" + (mainWindow.appVersion || "1.0.0")
                        color: mainWindow.termAcc
                        font.family: "Consolas"
                        font.pixelSize: 13
                        font.bold: true
                    }

                    Text {
                        text: mainWindow.tr("lbl.nav_sep")
                        color: mainWindow.termMuted
                        font.family: "Consolas"
                        font.pixelSize: 13
                    }

                    Text {
                        text: mainWindow.tr("home.system_verified")
                        color: mainWindow.termMuted
                        font.family: "Consolas"
                        font.pixelSize: 11
                    }
                }
            }
        }

        // --- Separator line ------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            color: mainWindow.termMuted
        }

        // --- BOTTOM SECTION: Update Cards (scrollable) ----------------
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.topMargin: 16
            Layout.bottomMargin: 16
            clip: true

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
                width: 8
            }

            Column {
                id: updatesColumn
                width: parent.width
                spacing: 14

                // Section header
                Text {
                    text: "> " + mainWindow.tr("home.changelog")
                    color: mainWindow.termAcc
                    font.family: "Consolas"
                    font.pixelSize: 11
                    font.bold: true
                    width: parent.width
                }

                // --- NEW v1.0.0: Quick System Status Row ------------------
                Rectangle {
                    width: parent.width
                    height: 40
                    color: Qt.darker(mainWindow.termBg, 1.3)
                    border.color: mainWindow.termMuted
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 24

                        Text {
                            text: "> " + mainWindow.tr("home.system_status")
                            color: mainWindow.termAcc
                            font.family: "Consolas"
                            font.pixelSize: 10
                            font.bold: true
                        }

                        Text {
                            id: homeCpuLabel
                            text: mainWindow.tr("home.cpu") + ": --"
                            color: mainWindow.termFg
                            font.family: "Consolas"
                            font.pixelSize: 10
                        }

                        Text {
                            id: homeMemLabel
                            text: mainWindow.tr("home.mem") + ": --"
                            color: mainWindow.termFg
                            font.family: "Consolas"
                            font.pixelSize: 10
                        }

                        Text {
                            id: homeCrashLabel
                            text: mainWindow.tr("home.crashes") + ": --"
                            color: mainWindow.termFg
                            font.family: "Consolas"
                            font.pixelSize: 10
                        }

                        Text {
                            id: homeUpdateLabel
                            text: mainWindow.tr("home.update") + ": --"
                            color: mainWindow.termFg
                            font.family: "Consolas"
                            font.pixelSize: 10
                            Layout.fillWidth: true
                        }

                        TermButton {
                            text: mainWindow.tr("btn.refresh")
                            tooltip: mainWindow.tr("tip.refresh_status")
                            Layout.preferredWidth: 32
                            Layout.preferredHeight: 24
                            font.pixelSize: 11
                            onClicked: homeRoot.refreshStatus()
                        }
                    }
                }

                // --- NEW v1.0.0: Update banner (inline, when update available) ---
                Rectangle {
                    id: homeUpdateBanner
                    property string newVersion: ""
                    property string downloadUrl: ""
                    visible: newVersion.length > 0
                    width: parent.width
                    height: visible ? 56 : 0
                    color: Qt.rgba(0.2, 0.8, 0.2, 0.2)
                    border.color: mainWindow.termAcc
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12

                        Text {
                            text: "> " + mainWindow.tr("home.update_banner") + ": v" + homeUpdateBanner.newVersion
                            color: mainWindow.termAcc
                            font.family: "Consolas"
                            font.pixelSize: 12
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        TermButton {
                            text: mainWindow.tr("btn.download")
                            tooltip: mainWindow.tr("tip.open_download_url")
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 28
                            font.pixelSize: 11
                            enabled: homeUpdateBanner.downloadUrl.length > 0
                            opacity: enabled ? 1.0 : 0.5
                            onClicked: {
                                if (homeUpdateBanner.downloadUrl) {
                                    Qt.openUrlExternally(homeUpdateBanner.downloadUrl)
                                }
                            }
                        }
                        TermButton {
                            text: mainWindow.tr("btn.dismiss")
                            tooltip: mainWindow.tr("tip.dismiss_banner")
                            Layout.preferredWidth: 80
                            Layout.preferredHeight: 28
                            font.pixelSize: 11
                            onClicked: homeUpdateBanner.newVersion = ""
                        }
                    }
                }

                // Render update cards from UpdateData
                Repeater {
                    model: updateData.updates
                    delegate: Card {
                        width: updatesColumn.width
                        title: modelData.date + " -- " + modelData.title

                        Column {
                            spacing: 4
                            width: parent.width

                            Repeater {
                                model: modelData.items
                                delegate: Text {
                                    text: "  > " + modelData
                                    color: mainWindow.termFg
                                    font.family: "Consolas"
                                    font.pixelSize: 10
                                    width: parent.width
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                }

                // Bottom padding
                Item {
                    width: 1
                    height: 16
                }
            }
        }
    }
}
