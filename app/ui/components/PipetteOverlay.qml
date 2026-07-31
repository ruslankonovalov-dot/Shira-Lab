// PipetteOverlay.qml — small top panel with countdown for color sampling
// Does NOT cover the screen — user can see the game target clearly.
import QtQuick
import QtQuick.Window

Window {
    id: pipetteOverlay
    objectName: "pipetteOverlay"
    title: "PipetteOverlay"
    // Always on top, no taskbar, but accepts input (for cancel button)
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    color: "#000000"
    visible: false
    width: 360
    height: 120
    x: (Screen.width - width) / 2
    y: 40

    // Sampled color info
    property color sampledColor: "transparent"
    property string sampledText: ""
    property bool showResult: false

    // Callback when sampling fires
    property var onSample: null

    // Countdown
    property int countdown: 3
    property bool sampling: false

    // Mouse position (read at sample time)
    property int mouseX: 0
    property int mouseY: 0

    // Track mouse position continuously
    Timer {
        id: mouseTracker
        interval: 16  // ~60 FPS
        repeat: true
        onTriggered: {
            try {
                var pos = Bridge.getMousePosition()
                pipetteOverlay.mouseX = pos.x
                pipetteOverlay.mouseY = pos.y
                mousePosText.text = mainWindow.tr("lbl.cursor_pos") + pos.x + ", " + pos.y
            } catch(e) {}
        }
    }

    // Countdown timer
    Timer {
        id: countdownTimer
        interval: 1000
        repeat: true
        onTriggered: {
            pipetteOverlay.countdown--
            if (pipetteOverlay.countdown <= 0) {
                countdownTimer.stop()
                pipetteOverlay.doSample()
            }
        }
    }

    function startCountdown() {
        pipetteOverlay.sampling = true
        pipetteOverlay.countdown = 3
        pipetteOverlay.showResult = false
        countdownTimer.start()
    }

    function doSample() {
        pipetteOverlay.sampling = false
        if (pipetteOverlay.onSample) {
            pipetteOverlay.onSample(pipetteOverlay.mouseX, pipetteOverlay.mouseY)
        }
    }

    onVisibleChanged: {
        if (visible) {
            mouseTracker.start()
            showResult = false
            sampling = false
            countdown = 0
        } else {
            mouseTracker.stop()
            countdownTimer.stop()
        }
    }

    // Border
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: pipetteOverlay.sampling ? "#ffee00" : "#00ff41"
        border.width: 2
    }

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4

        // Title
        Text {
            text: pipetteOverlay.sampling
                ? mainWindow.tr("pipette.title") + " — " + mainWindow.tr("pipette.sampling_in") + " " + pipetteOverlay.countdown + "..."
                : (pipetteOverlay.showResult ? mainWindow.tr("pipette.sampled") : mainWindow.tr("pipette.ready"))
            color: pipetteOverlay.sampling ? "#ffee00" : "#00ff41"
            font.family: "Consolas"
            font.pixelSize: 13
            font.bold: true
            anchors.horizontalCenter: parent.horizontalCenter
        }

        // Mouse position or result
        Text {
            id: mousePosText
            text: mainWindow.tr("lbl.cursor_pos") + "--, --"
            color: pipetteOverlay.sampling ? "#ffee00" : "#888888"
            font.family: "Consolas"
            font.pixelSize: 10
            anchors.horizontalCenter: parent.horizontalCenter
            visible: !pipetteOverlay.showResult
        }

        // Result row (color swatch + HSV text)
        Row {
            visible: pipetteOverlay.showResult
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8

            Rectangle {
                width: 30
                height: 16
                color: pipetteOverlay.sampledColor
                border.color: "#ffffff"
                border.width: 1
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: pipetteOverlay.sampledText
                color: "#00ff41"
                font.family: "Consolas"
                font.pixelSize: 10
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Buttons
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8

            // Start countdown
            Rectangle {
                width: 100
                height: 26
                color: startArea.containsMouse ? "#555500" : "#333300"
                border.color: "#ffee00"
                border.width: 1
                visible: !pipetteOverlay.sampling && !pipetteOverlay.showResult

                Text {
                    anchors.centerIn: parent
                    text: mainWindow.tr("pipette.countdown")
                    color: "#ffee00"
                    font.family: "Consolas"
                    font.pixelSize: 10
                    font.bold: true
                }
                MouseArea {
                    id: startArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: pipetteOverlay.startCountdown()
                }
            }

            // Sample now
            Rectangle {
                width: 100
                height: 26
                color: nowArea.containsMouse ? "#005500" : "#003300"
                border.color: "#00ff41"
                border.width: 1
                visible: !pipetteOverlay.sampling && !pipetteOverlay.showResult

                Text {
                    anchors.centerIn: parent
                    text: mainWindow.tr("pipette.now")
                    color: "#00ff41"
                    font.family: "Consolas"
                    font.pixelSize: 10
                    font.bold: true
                }
                MouseArea {
                    id: nowArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: pipetteOverlay.doSample()
                }
            }

            // Cancel / Close
            Rectangle {
                width: 100
                height: 26
                color: cancelArea.containsMouse ? "#550000" : "#330000"
                border.color: "#ff0040"
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: pipetteOverlay.sampling ? mainWindow.tr("pipette.cancel") : mainWindow.tr("pipette.close")
                    color: "#ff0040"
                    font.family: "Consolas"
                    font.pixelSize: 10
                    font.bold: true
                }
                MouseArea {
                    id: cancelArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        countdownTimer.stop()
                        pipetteOverlay.sampling = false
                        pipetteOverlay.visible = false
                    }
                }
            }
        }
    }
}
