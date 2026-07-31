// AimPage.qml -- professional aim assist with visual debug
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    color: mainWindow.termBg

    property var status: ({})

        // v1.0.0 i18n: Detection modes (rebuilt on language change)
        property var detectionModes: []
        function rebuildDetectionModes() {
            var _ = Bridge.currentLang
            detectionModes = [
                { text: mainWindow.tr("combo.mode_auto"), value: "auto" },
                { text: mainWindow.tr("combo.mode_multi"), value: "multi" },
                { text: mainWindow.tr("combo.mode_circles"), value: "circles" },
                { text: mainWindow.tr("combo.mode_color"), value: "color" },
                { text: mainWindow.tr("combo.mode_calibrate"), value: "calibrate" }
            ]
        }
        // v1.0.0 i18n: Target colors (rebuilt on language change)
        property var targetColors: []
        function rebuildTargetColors() {
            var _ = Bridge.currentLang
            targetColors = [
                { text: mainWindow.tr("combo.color_red"), value: "red" },
                { text: mainWindow.tr("combo.color_blue"), value: "blue" },
                { text: mainWindow.tr("combo.color_green"), value: "green" },
                { text: mainWindow.tr("combo.color_purple"), value: "purple" },
                { text: mainWindow.tr("combo.color_yellow"), value: "yellow" },
                { text: mainWindow.tr("combo.color_cyan"), value: "cyan" },
                { text: mainWindow.tr("combo.color_orange"), value: "orange" },
                { text: mainWindow.tr("combo.color_pink"), value: "pink" }
            ]
        }


    // HSV -> RGB converter (for pipette color display)
    function hsvToRgb(h, s, v) {
        h = h / 180.0; s = s / 255.0; v = v / 255.0
        var i = Math.floor(h * 6)
        var f = h * 6 - i
        var p = v * (1 - s)
        var q = v * (1 - f * s)
        var t = v * (1 - (1 - f) * s)
        var r, g, b
        switch (i % 6) {
            case 0: r = v; g = t; b = p; break
            case 1: r = q; g = v; b = p; break
            case 2: r = p; g = v; b = t; break
            case 3: r = p; g = q; b = v; break
            case 4: r = t; g = p; b = v; break
            case 5: r = v; g = p; b = q; break
        }
        return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)]
    }

    // Timer to auto-hide pipette overlay after showing result
    Timer {
        id: hidePipetteTimer
        interval: 2500
        repeat: false
        onTriggered: pipetteOverlay.visible = false
    }

    function updateStatus(s) {
        status = s
        statusLabel.text = mainWindow.tr("aim.title") + ": " + (s.is_running ? mainWindow.tr("aim.running") : mainWindow.tr("aim.idle")) + " | " + (s.last_log || mainWindow.tr("aim.ready"))
    }

    function loadTargetWindow() {
        var r = Bridge.getModuleTargetWindow("aim")
        var targetHwnd = r.hwnd || 0
        for (var i = 0; i < targetWindowCombo.model.length; i++) {
            if (targetWindowCombo.model[i].value === targetHwnd) {
                targetWindowCombo.currentIndex = i
                break
            }
        }
        targetWindowLabel.text = mainWindow.tr("target.current") + " " + r.name + (r.hwnd ? " (hwnd: " + r.hwnd + ")" : "")
    }

    function refreshWindows() {
        var r = Bridge.getWindows()
        var model = [{ text: mainWindow.tr("combo.global_screen"), value: 0 }]
        for (var i = 0; i < r.windows.length; i++) {
            model.push({ text: r.windows[i].title, value: r.windows[i].hwnd })
        }
        targetWindowCombo.model = model
        loadTargetWindow()
    }

    function loadSettings() {
        var r = Bridge.aimStatus()
        if (r.background_method) {
            for (var i = 0; i < aimBackgroundMethod.model.length; i++) {
                if (aimBackgroundMethod.model[i].value === r.background_method) {
                    aimBackgroundMethod.currentIndex = i
                    break
                }
            }
        }
        if (r.detection_mode) {
            for (var i = 0; i < detectionModeCombo.model.length; i++) {
                if (detectionModeCombo.model[i].value === r.detection_mode) {
                    detectionModeCombo.currentIndex = i
                    break
                }
            }
        }
        if (r.target_color) {
            for (var i = 0; i < targetColorCombo.model.length; i++) {
                if (targetColorCombo.model[i].value === r.target_color) {
                    targetColorCombo.currentIndex = i
                    break
                }
            }
        }
        if (r.aim_speed !== undefined) aimSpeedField.text = r.aim_speed
        if (r.fov_radius !== undefined) fovField.text = r.fov_radius
        if (r.min_area !== undefined) minAreaField.text = r.min_area
        if (r.max_area !== undefined) maxAreaField.text = r.max_area
        if (r.brightness_threshold !== undefined) brightnessField.text = r.brightness_threshold
        if (r.saturation_threshold !== undefined) saturationField.text = r.saturation_threshold
    }

    Component.onCompleted: {
        rebuildDetectionModes()
        rebuildTargetColors()
        refreshWindows()
        loadSettings()
    }

    // Modern QML Connections syntax (function-based, avoids deprecation warning)
    Connections {
        target: Bridge
        function onSettingsChanged() {
            loadSettings()
        }
    }


    // v1.0.0 i18n: Rebuild models on language change
    Connections {
        target: Bridge
        function onLangChanged() {
            rebuildDetectionModes()
            rebuildTargetColors()
            refreshWindows()
        }
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

// --- Target Window Card -------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.target_window")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: mainWindow.tr("lbl.select_window"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: targetWindowCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        model: [{ text: mainWindow.tr("combo.global_screen"), value: 0 }]
                        textRole: "text"
                        valueRole: "value"
                        tooltip: mainWindow.tr("tip.gamepad_target")
                        Accessible.name: mainWindow.tr("lbl.select_window")
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && currentIndex < model.length) {
                                Bridge.setModuleTargetWindow("aim", model[currentIndex].value)
                            }
                            loadTargetWindow()
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("btn.refresh")
                            tooltip: mainWindow.tr("tip.gamepad_refresh")
                            Accessible.name: mainWindow.tr("btn.refresh")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: refreshWindows()
                        }
                        Item { Layout.fillWidth: true }
                    }
                    Text { id: targetWindowLabel; text: mainWindow.tr("target.current") + " " + mainWindow.tr("combo.global_screen"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                }
            }

            // --- Detection Mode Card -----------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.aim_detect")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: mainWindow.tr("lbl.mode"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: detectionModeCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        model: detectionModes
                        textRole: "text"
                        valueRole: "value"
                        tooltip: mainWindow.tr("tip.aim_detect_mode")
                        Accessible.name: mainWindow.tr("lbl.mode")
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && currentIndex < model.length) {
                                Bridge.setAimDetectionMode(model[currentIndex].value)
                            }
                        }
                    }

                    Text { text: mainWindow.tr("lbl.color"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: targetColorCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        model: targetColors
                        textRole: "text"
                        valueRole: "value"
                        tooltip: mainWindow.tr("tip.aim_target_color")
                        Accessible.name: mainWindow.tr("lbl.color")
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && currentIndex < model.length) {
                                Bridge.setAimTargetColor(model[currentIndex].value)
                            }
                        }
                    }

                    // Pipette
                    Text { text: mainWindow.tr("aim.pipette_hint"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("aim.open_pipette")
                            tooltip: mainWindow.tr("tip.aim_pipette")
                            Accessible.name: mainWindow.tr("aim.open_pipette")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: {
                                pipetteOverlay.onSample = function(x, y) {
                                    var r = Bridge.aimSampleColor(x, y)
                                    if (r.ok) {
                                        var rgb = hsvToRgb(r.hsv[0], r.hsv[1], r.hsv[2])
                                        pipetteOverlay.sampledColor = Qt.rgba(rgb[0]/255, rgb[1]/255, rgb[2]/255, 1)
                                        pipetteOverlay.sampledText = "H=" + r.hsv[0] + " S=" + r.hsv[1] + " V=" + r.hsv[2]
                                        pipetteOverlay.showResult = true

                                        pipetteInfo.text = "H=" + r.hsv[0] + " S=" + r.hsv[1] + " V=" + r.hsv[2] + " | std H=" + r.std[0] + " S=" + r.std[1] + " V=" + r.std[2]
                                        pipetteInfo.color = mainWindow.termSuccess
                                        // Find index for 'calibrate' value (currentValue is read-only in Qt 6)
                                        for (var i = 0; i < detectionModeCombo.model.length; i++) {
                                            if (detectionModeCombo.model[i].value === "calibrate") {
                                                detectionModeCombo.currentIndex = i
                                                break
                                            }
                                        }

                                        hidePipetteTimer.start()
                                    } else {
                                        pipetteInfo.text = "Error: " + (r.error || "unknown")
                                        pipetteInfo.color = mainWindow.termDanger
                                        pipetteOverlay.visible = false
                                    }
                                }
                                pipetteOverlay.showResult = false
                                pipetteOverlay.visible = true
                            }
                        }
                        Text {
                            id: pipetteInfo
                            text: "// " + mainWindow.tr("aim.not_calibrated")
                            color: mainWindow.termMuted
                            font.family: "Consolas"
                            font.pixelSize: 9
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            // --- Filters Card ------------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.aim_filters")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: mainWindow.tr("lbl.area"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermTextField { id: minAreaField; Layout.fillWidth: true; text: "20"; tooltip: mainWindow.tr("tip.aim_filters"); Accessible.name: mainWindow.tr("lbl.area") + " " + mainWindow.tr("lbl.min") }
                        TermTextField { id: maxAreaField; Layout.fillWidth: true; text: "50000"; tooltip: mainWindow.tr("tip.aim_filters"); Accessible.name: mainWindow.tr("lbl.area") + " " + mainWindow.tr("lbl.max") }
                    }

                    Text { text: mainWindow.tr("lbl.brightness"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermTextField { id: brightnessField; Layout.fillWidth: true; text: "80"; tooltip: mainWindow.tr("tip.aim_filters"); Accessible.name: mainWindow.tr("lbl.brightness") }

                    Text { text: mainWindow.tr("lbl.saturation"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermTextField { id: saturationField; Layout.fillWidth: true; text: "50"; tooltip: mainWindow.tr("tip.aim_filters"); Accessible.name: mainWindow.tr("lbl.saturation") }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("aim.apply_filters")
                            tooltip: mainWindow.tr("tip.aim_apply")
                            Accessible.name: mainWindow.tr("aim.apply_filters")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: {
                                Bridge.setAimFilters(
                                    parseInt(minAreaField.text) || 20,
                                    parseInt(maxAreaField.text) || 50000,
                                    30, 200,
                                    parseInt(brightnessField.text) || 80,
                                    parseInt(saturationField.text) || 50
                                )
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
            }

            // --- Aim Settings Card -------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.aim_settings")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: mainWindow.tr("lbl.aim_speed"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermTextField { id: aimSpeedField; Layout.fillWidth: true; text: "0.3"; tooltip: mainWindow.tr("tip.aim_smoothing"); Accessible.name: mainWindow.tr("lbl.aim_speed") }

                    Text { text: mainWindow.tr("lbl.fov_radius"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermTextField { id: fovField; Layout.fillWidth: true; text: "300"; tooltip: mainWindow.tr("tip.aim_fov"); Accessible.name: mainWindow.tr("lbl.fov_radius") }

                    Text { text: mainWindow.tr("lbl.smooth"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermTextField { id: aimSmooth; Layout.fillWidth: true; text: "5"; tooltip: mainWindow.tr("tip.aim_smoothing"); Accessible.name: mainWindow.tr("lbl.smooth") + " " + mainWindow.tr("lbl.aim_speed") }
                        TermTextField { id: aimReset; Layout.fillWidth: true; text: "0.005"; tooltip: mainWindow.tr("tip.aim_smoothing"); Accessible.name: mainWindow.tr("lbl.smooth") + " " + mainWindow.tr("lbl.reset") }
                    }

                    Text { text: mainWindow.tr("lbl.background_method"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: aimBackgroundMethod
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        model: [
                            { text: mainWindow.tr("combo.method_sendinput"), value: "sendinput" },
                            { text: mainWindow.tr("combo.method_postmessage"), value: "postmessage" },
                            { text: mainWindow.tr("combo.method_vigem"), value: "vigem" },
                            { text: mainWindow.tr("combo.method_pico"), value: "pico" }
                        ]
                        textRole: "text"
                        valueRole: "value"
                        tooltip: mainWindow.tr("tip.aim_bg_method")
                        Accessible.name: mainWindow.tr("lbl.background_method")
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("btn.apply_all")
                            tooltip: mainWindow.tr("tip.aim_apply")
                            Accessible.name: mainWindow.tr("btn.apply_all")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: {
                                Bridge.aimSetConfig(0.5, parseInt(aimSmooth.text)||5, parseFloat(aimReset.text)||0.005)
                                Bridge.setAimSpeed(parseFloat(aimSpeedField.text)||0.3)
                                Bridge.setAimFov(parseInt(fovField.text)||300)
                                Bridge.setAimBackgroundMethod(aimBackgroundMethod.currentValue)
                                var r = Bridge.aimStatus()
                                updateStatus(r)
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("btn.start")
                            tooltip: mainWindow.tr("tip.aim_start")
                            Accessible.name: mainWindow.tr("btn.start")
                            Layout.preferredWidth: 120
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { var r = Bridge.aimStart(); updateStatus(r); }
                        }
                        TermButton {
                            text: mainWindow.tr("btn.stop")
                            tooltip: mainWindow.tr("tip.aim_stop")
                            Accessible.name: mainWindow.tr("btn.stop")
                            Layout.preferredWidth: 120
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { var r = Bridge.aimStop(); updateStatus(r); }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Text { id: statusLabel; text: mainWindow.tr("aim.running") + ": " + mainWindow.tr("aim.idle"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 11; Layout.fillWidth: true }
                }
            }

            // --- Debug Info Card ---------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.debug")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Text {
                        text: mainWindow.tr("aim.debug_screenshots")
                        color: mainWindow.termMuted
                        font.family: "Consolas"
                        font.pixelSize: 9
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        text: mainWindow.tr("aim.debug_legend")
                        color: mainWindow.termFg
                        font.family: "Consolas"
                        font.pixelSize: 9
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }
                }
            }

            // Bottom spacer
            Item { Layout.fillHeight: true; Layout.fillWidth: true; Layout.minimumHeight: 16 }
        }
    }
}
