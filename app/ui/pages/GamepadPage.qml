// GamepadPage.qml -- terminal-style page with ASCII banner + rule-based cards
// v1.0.0 i18n: all labels, buttons, combos, tooltips, status texts use mainWindow.tr()
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    id: page
    color: mainWindow.termBg
    Layout.fillWidth: true
    Layout.fillHeight: true

    property var currentControllerType: "X360"
    property var currentTargetIndex: 0
    property var isVigemConnected: false
    property var physicalGamepads: []


    // v1.0.0 i18n: Rebuild models on language change
    Connections {
        target: Bridge
        function onLangChanged() {
            rebuildControllerTypes()
            rebuildGamepadButtonsModel()
            rebuildTestButtonsModel()
            rebuildTargetIndexModel()
            refreshWindows()
        }
    }

    // --- Rebuildable models for i18n ---
    function rebuildControllerTypes() {
        controllerTypeCombo.model = [
            { text: mainWindow.tr("gamepad.type_xbox360"), value: "X360" },
            { text: mainWindow.tr("gamepad.type_ds4"), value: "DS4" }
        ]
    }

    function rebuildGamepadButtonsModel() {
        gamepadButtonsModel.clear()
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_a"), value: "A" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_b"), value: "B" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_x"), value: "X" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_y"), value: "Y" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_lb"), value: "LB" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_rb"), value: "RB" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_lt"), value: "LT" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_rt"), value: "RT" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_back"), value: "BACK" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_start"), value: "START" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_ls"), value: "LS" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_rs"), value: "RS" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_dpad_up"), value: "DPAD_UP" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_dpad_down"), value: "DPAD_DOWN" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_dpad_left"), value: "DPAD_LEFT" })
        gamepadButtonsModel.append({ text: mainWindow.tr("gamepad.btn_dpad_right"), value: "DPAD_RIGHT" })
    }

    function rebuildTestButtonsModel() {
        testButtonsModel.clear()
        testButtonsModel.append({ text: mainWindow.tr("gamepad.btn_a") })
        testButtonsModel.append({ text: mainWindow.tr("gamepad.btn_b") })
        testButtonsModel.append({ text: mainWindow.tr("gamepad.btn_x") })
        testButtonsModel.append({ text: mainWindow.tr("gamepad.btn_y") })
        testButtonsModel.append({ text: mainWindow.tr("gamepad.btn_lb") })
        testButtonsModel.append({ text: mainWindow.tr("gamepad.btn_rb") })
        testButtonsModel.append({ text: mainWindow.tr("gamepad.btn_back") })
        testButtonsModel.append({ text: mainWindow.tr("gamepad.btn_start") })
        testButtonsModel.append({ text: mainWindow.tr("gamepad.btn_ls") })
        testButtonsModel.append({ text: mainWindow.tr("gamepad.btn_rs") })
        testButtonsModel.append({ text: mainWindow.tr("gamepad.btn_dpad") })
    }

    function rebuildTargetIndexModel() {
        targetIndexCombo.model = [
            { text: mainWindow.tr("gamepad.controller_n").replace("{}", "0"), value: 0 },
            { text: mainWindow.tr("gamepad.controller_n").replace("{}", "1"), value: 1 },
            { text: mainWindow.tr("gamepad.controller_n").replace("{}", "2"), value: 2 },
            { text: mainWindow.tr("gamepad.controller_n").replace("{}", "3"), value: 3 }
        ]
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
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && currentIndex < model.length) {
                                Bridge.setModuleTargetWindow("gamepad", model[currentIndex].value)
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

            // --- ViGEm Status Card ------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("gamepad.vigem_status")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text { text: mainWindow.tr("lbl.status"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 11; Layout.preferredWidth: 100 }
                        Text {
                            text: isVigemConnected ? mainWindow.tr("gamepad.connected") : mainWindow.tr("gamepad.disconnected")
                            color: isVigemConnected ? mainWindow.termSuccess : mainWindow.termDanger
                            font.family: "Consolas"
                            font.pixelSize: 11
                            font.bold: true
                        }
                        Item { Layout.fillWidth: true }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text { text: mainWindow.tr("lbl.controller"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 11; Layout.preferredWidth: 100 }
                        Text { id: ctrlTypeLabel; text: currentControllerType; color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 11 }
                        Item { Layout.fillWidth: true }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text { text: mainWindow.tr("lbl.target_index"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 11; Layout.preferredWidth: 100 }
                        Text { id: targetIdxLabel; text: String(currentTargetIndex || 0); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 11 }
                        Item { Layout.fillWidth: true }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: isVigemConnected ? mainWindow.tr("btn.disconnect") : mainWindow.tr("btn.connect")
                            tooltip: isVigemConnected ? mainWindow.tr("tip.gamepad_disconnect") : mainWindow.tr("tip.gamepad_connect")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: {
                                if (isVigemConnected) {
                                    var res = Bridge.stopVigem()
                                    refreshStatus()
                                } else {
                                    var res = Bridge.startVigem()
                                    refreshStatus()
                                }
                            }
                        }
                        TermButton {
                            text: mainWindow.tr("btn.refresh_targets")
                            tooltip: mainWindow.tr("tip.gamepad_refresh_tgt")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: {
                                var res = Bridge.refreshVigemTargets()
                                refreshStatus()
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
            }

            // --- Controller Config Card (merged: Type + Index + Bg Method) ----
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("gamepad.config")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: mainWindow.tr("lbl.type"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: controllerTypeCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        font.pixelSize: 11
                        model: []
                        textRole: "text"
                        currentIndex: currentControllerType === "X360" ? 0 : 1
                        tooltip: mainWindow.tr("tip.gamepad_type")
                        onCurrentIndexChanged: {
                            var val = (currentIndex === 0) ? "X360" : "DS4"
                            var res = Bridge.setVigemControllerType(val)
                            refreshStatus()
                        }
                    }

                    Text { text: mainWindow.tr("lbl.target_index_max"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: targetIndexCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        font.pixelSize: 11
                        model: [
                            { text: mainWindow.tr("gamepad.controller_n").replace("{}", "0"), value: 0 },
                            { text: mainWindow.tr("gamepad.controller_n").replace("{}", "1"), value: 1 },
                            { text: mainWindow.tr("gamepad.controller_n").replace("{}", "2"), value: 2 },
                            { text: mainWindow.tr("gamepad.controller_n").replace("{}", "3"), value: 3 }
                        ]
                        textRole: "text"
                        valueRole: "value"
                        currentIndex: currentTargetIndex
                        tooltip: mainWindow.tr("tip.gamepad_target_idx")
                        onActivated: function(index) {
                            var res = Bridge.setVigemTargetIndex(index)
                            refreshStatus()
                        }
                    }

                    Text { text: mainWindow.tr("lbl.background_method"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: gamepadBackgroundMethod
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
                        tooltip: mainWindow.tr("tip.gamepad_bg_method")
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("btn.apply_bg_method")
                            tooltip: mainWindow.tr("tip.gamepad_apply_bg")
                            Layout.preferredWidth: 160
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { Bridge.setGamepadBackgroundMethod(gamepadBackgroundMethod.currentValue); }
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
            }

            // --- Physical Gamepads Card --------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("gamepad.physical")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("btn.detect_gamepads")
                            tooltip: mainWindow.tr("tip.gamepad_detect")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: detectPhysicalGamepads()
                        }
                        TermButton {
                            text: mainWindow.tr("btn.refresh")
                            tooltip: mainWindow.tr("tip.gamepad_refresh")
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: detectPhysicalGamepads()
                        }
                        Item { Layout.fillWidth: true }
                    }

                    ColumnLayout {
                        id: physicalGamepadList
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: physicalGamepads
                            delegate: Card {
                                Layout.fillWidth: true
                                property var pad: modelData
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 6

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10
                                        Text { text: mainWindow.tr("gamepad.index") + ": " + pad.user_index; color: mainWindow.termAcc; font.family: "Consolas"; font.pixelSize: 11; font.bold: true; Layout.preferredWidth: 85 }
                                        Text { text: pad.connected ? mainWindow.tr("gamepad.connected") : mainWindow.tr("gamepad.disconnected"); color: pad.connected ? mainWindow.termSuccess : mainWindow.termDanger; font.family: "Consolas"; font.pixelSize: 11; font.bold: true }
                                        Text { text: pad.controller_type; color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                                        Item { Layout.fillWidth: true }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10
                                        Text { text: mainWindow.tr("gamepad.user_id") + ": " + pad.user_index; color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10; Layout.preferredWidth: 95 }
                                        Text { text: mainWindow.tr("gamepad.battery") + ": " + (pad.battery_level >= 0 ? pad.battery_level + "%" : mainWindow.tr("gamepad.na")); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10; Layout.preferredWidth: 110 }
                                        Text { text: mainWindow.tr("gamepad.subtype") + ": " + pad.sub_type; color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10 }
                                        Item { Layout.fillWidth: true }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10
                                        Text { text: mainWindow.tr("gamepad.buttons") + ": 0x" + pad.buttons.toString(16).toUpperCase().padStart(4, "0"); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10 }
                                        Text { text: mainWindow.tr("gamepad.lt") + ": " + pad.left_trigger; color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10; Layout.preferredWidth: 70 }
                                        Text { text: mainWindow.tr("gamepad.rt") + ": " + pad.right_trigger; color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 10; Layout.preferredWidth: 70 }
                                        Item { Layout.fillWidth: true }
                                    }
                                }
                            }
                        }

                        // Placeholder when no gamepads
                        Item {
                            Layout.fillWidth: true
                            Layout.preferredHeight: physicalGamepads.length === 0 ? 55 : 0
                            visible: physicalGamepads.length === 0
                            Text {
                                anchors.centerIn: parent
                                text: mainWindow.tr("gamepad.no_gamepads")
                                color: mainWindow.termMuted
                                font.family: "Consolas"
                                font.pixelSize: 11
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
                }
            }

            // --- Button Mapping Card ----------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.gamepad_mapping")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    // Header
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Text { text: mainWindow.tr("lbl.hotkey_key"); color: mainWindow.termAcc; font.family: "Consolas"; font.pixelSize: 11; font.bold: true; Layout.preferredWidth: 110 }
                        Text { text: mainWindow.tr("lbl.arrow_right"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 11; Layout.preferredWidth: 18 }
                        Text { text: mainWindow.tr("gamepad.btn_label"); color: mainWindow.termAcc; font.family: "Consolas"; font.pixelSize: 11; font.bold: true; Layout.preferredWidth: 160 }
                        Item { Layout.fillWidth: true }
                        TermButton {
                            text: mainWindow.tr("btn.apply_mapping")
                            tooltip: mainWindow.tr("tip.gamepad_map_apply")
                            Accessible.name: mainWindow.tr("btn.apply_mapping")
                            Layout.preferredWidth: 140
                            Layout.preferredHeight: 32
                            font.pixelSize: 11
                            onClicked: applyMapping()
                        }
                    }

                    Repeater {
                        model: buttonMappingModel
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Text { text: model.key; color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 11; Layout.preferredWidth: 110 }
                            Text { text: "->"; color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 11; Layout.preferredWidth: 18 }
                            TermComboBox {
                                Layout.fillWidth: true
                                Layout.maximumWidth: 200
                                Layout.preferredHeight: 32
                                font.pixelSize: 11
                                model: gamepadButtonsModel
                                textRole: "text"
                                currentIndex: findButtonIndex(model.button)
                                tooltip: mainWindow.tr("tip.gamepad_key_combo")
                                Accessible.name: mainWindow.tr("gamepad.btn_label") + ": " + model.key
                                onActivated: function(idx) {
                                    if (idx >= 0) {
                                        var item = gamepadButtonsModel.get(idx)
                                        if (item && item.value !== undefined) {
                                            buttonMappingModel.setProperty(index, "button", item.value)
                                        }
                                    }
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }
                }
            }

            // --- Test Controls Card -----------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.gamepad_test")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 14

                    // Buttons grid
                    Text { text: mainWindow.tr("lbl.buttons"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    GridLayout {
                        columns: 6
                        columnSpacing: 8
                        rowSpacing: 8
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignHCenter

                        Repeater {
                            model: testButtonsModel
                            delegate: TermButton {
                                Layout.preferredWidth: 68
                                Layout.preferredHeight: 34
                                text: model.text
                                font.pixelSize: 11
                                checkable: true
                                checked: false
                                tooltip: mainWindow.tr("tip.gamepad_test_buttons")
                                Accessible.name: model.text
                                onCheckedChanged: sendTestState()
                            }
                        }
                    }

                    // Left Stick
                    Text { text: mainWindow.tr("lbl.left_stick"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    GridLayout {
                        columns: 4
                        columnSpacing: 10
                        rowSpacing: 10
                        Layout.fillWidth: true

                        Text { text: mainWindow.tr("lbl.x_axis"); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 11; Layout.preferredWidth: 24 }
                        TermSlider {
                            id: lsX
                            from: -32768; to: 32767; value: 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: 20
                            tooltip: mainWindow.tr("tip.gamepad_test_lstick")
                            Accessible.name: mainWindow.tr("lbl.left_stick") + " " + mainWindow.tr("lbl.x_axis")
                        }
                        Text { text: mainWindow.tr("lbl.y_axis"); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 11; Layout.preferredWidth: 24 }
                        TermSlider {
                            id: lsY
                            from: -32768; to: 32767; value: 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: 20
                            tooltip: mainWindow.tr("tip.gamepad_test_lstick")
                            Accessible.name: mainWindow.tr("lbl.left_stick") + " " + mainWindow.tr("lbl.y_axis")
                        }
                    }

                    // Right Stick
                    Text { text: mainWindow.tr("lbl.right_stick"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    GridLayout {
                        columns: 4
                        columnSpacing: 10
                        rowSpacing: 10
                        Layout.fillWidth: true

                        Text { text: mainWindow.tr("lbl.x_axis"); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 11; Layout.preferredWidth: 24 }
                        TermSlider {
                            id: rsX
                            from: -32768; to: 32767; value: 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: 20
                            tooltip: mainWindow.tr("tip.gamepad_test_rstick")
                            Accessible.name: mainWindow.tr("lbl.right_stick") + " " + mainWindow.tr("lbl.x_axis")
                        }
                        Text { text: mainWindow.tr("lbl.y_axis"); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 11; Layout.preferredWidth: 24 }
                        TermSlider {
                            id: rsY
                            from: -32768; to: 32767; value: 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: 20
                            tooltip: mainWindow.tr("tip.gamepad_test_rstick")
                            Accessible.name: mainWindow.tr("lbl.right_stick") + " " + mainWindow.tr("lbl.y_axis")
                        }
                    }

                    // Triggers
                    Text { text: mainWindow.tr("lbl.triggers"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    GridLayout {
                        columns: 4
                        columnSpacing: 10
                        rowSpacing: 10
                        Layout.fillWidth: true

                        Text { text: mainWindow.tr("lbl.lt_trigger"); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 11; Layout.preferredWidth: 24 }
                        TermSlider {
                            id: triggerL
                            from: 0; to: 255; value: 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: 20
                            tooltip: mainWindow.tr("tip.gamepad_test_lt")
                            Accessible.name: mainWindow.tr("lbl.lt_trigger")
                        }
                        Text { text: mainWindow.tr("lbl.rt_trigger"); color: mainWindow.termFg; font.family: "Consolas"; font.pixelSize: 11; Layout.preferredWidth: 24 }
                        TermSlider {
                            id: triggerR
                            from: 0; to: 255; value: 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: 20
                            tooltip: mainWindow.tr("tip.gamepad_test_rt")
                            Accessible.name: mainWindow.tr("lbl.rt_trigger")
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        TermButton {
                            text: mainWindow.tr("btn.send_test_state")
                            tooltip: mainWindow.tr("tip.gamepad_send_test")
                            Accessible.name: mainWindow.tr("btn.send_test_state")
                            Layout.preferredWidth: 160
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: sendTestState()
                        }
                        TermButton {
                            text: mainWindow.tr("btn.reset_all")
                            tooltip: mainWindow.tr("tip.gamepad_reset_all")
                            Accessible.name: mainWindow.tr("btn.reset_all")
                            Layout.preferredWidth: 120
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: resetAll()
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
            }

            // Bottom spacer
            Item { Layout.fillHeight: true; Layout.fillWidth: true; Layout.minimumHeight: 16 }
        }
    }

    // --- Models ----------------------------------------------------------
    ListModel {
        id: buttonMappingModel
        Component.onCompleted: {
        rebuildControllerTypes()
            var defaults = [
                { key: "space", button: "A" },
                { key: "shift", button: "LB" },
                { key: "ctrl", button: "RB" },
                { key: "q", button: "X" },
                { key: "e", button: "Y" },
                { key: "r", button: "B" },
                { key: "tab", button: "BACK" },
                { key: "escape", button: "START" },
                { key: "w", button: "DPAD_UP" },
                { key: "s", button: "DPAD_DOWN" },
                { key: "a", button: "DPAD_LEFT" },
                { key: "d", button: "DPAD_RIGHT" }
            ]
            for (var i = 0; i < defaults.length; i++) {
                append(defaults[i])
            }
        }
    }

    ListModel {
        id: gamepadButtonsModel
    }

    ListModel {
        id: testButtonsModel
    }

    // --- Functions ---------------------------------------------------------
    function refreshStatus() {
        var data = Bridge.getVigemStatus()
        try {
            if (data && data.ok) {
                isVigemConnected = data.connected || false
                currentControllerType = data.controller_type || "X360"
                currentTargetIndex = data.target_index || 0
                if (ctrlTypeLabel) ctrlTypeLabel.text = currentControllerType
                if (targetIdxLabel) targetIdxLabel.text = String(currentTargetIndex)
                if (controllerTypeCombo) controllerTypeCombo.currentIndex = (currentControllerType === "X360") ? 0 : 1
                if (targetIndexCombo) targetIndexCombo.currentIndex = currentTargetIndex
            }
        } catch (e) {
            console.error("Parse vigem status error:", e)
        }
    }

    function applyMapping() {
        var mapping = {}
        for (var i = 0; i < buttonMappingModel.count; i++) {
            var item = buttonMappingModel.get(i)
            mapping[item.key] = item.button
        }
        // Convert to JS object and pass directly
        var res = Bridge.setVigemButtonMap(mapping)
    }

    function sendTestState() {
        var buttons = 0
        var res = Bridge.sendVigemTestState({
            buttons: buttons,
            lt: triggerL.value,
            rt: triggerR.value,
            lx: lsX.value,
            ly: lsY.value,
            rx: rsX.value,
            ry: rsY.value
        })
        if (res && !res.ok) {
            console.warn("sendVigemTestState failed:", res.error)
        }
    }

    function resetAll() {
        triggerL.value = 0
        triggerR.value = 0
        lsX.value = 0
        lsY.value = 0
        rsX.value = 0
        rsY.value = 0
        sendTestState()
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

    function loadTargetWindow() {
        var r = Bridge.getModuleTargetWindow("gamepad")
        var targetHwnd = r.hwnd || 0
        // Find index in model by value (currentValue is read-only in Qt 6)
        for (var i = 0; i < targetWindowCombo.model.length; i++) {
            if (targetWindowCombo.model[i].value === targetHwnd) {
                targetWindowCombo.currentIndex = i
                break
            }
        }
        targetWindowLabel.text = mainWindow.tr("lbl.target") + ": " + r.name + (r.hwnd ? " (hwnd: " + r.hwnd + ")" : "")
    }

    function loadBackgroundMethod() {
        var r = Bridge.getVigemStatus()
        if (r.gamepad_background_method) {
            for (var i = 0; i < gamepadBackgroundMethod.model.length; i++) {
                if (gamepadBackgroundMethod.model[i].value === r.gamepad_background_method) {
                    gamepadBackgroundMethod.currentIndex = i
                    break
                }
            }
        }
    }

    function detectPhysicalGamepads() {
        var data = Bridge.detectPhysicalGamepads()
        if (data.ok) {
            physicalGamepads = data.gamepads
        }
    }

    function findButtonIndex(btn) {
        for (var i = 0; i < gamepadButtonsModel.count; i++) {
            if (gamepadButtonsModel.get(i).value === btn) return i
        }
        return 0
    }

    Connections {
        target: Bridge
        function onSettingsChanged() {
            loadBackgroundMethod()
        }
    }

    // Initialize
    Component.onCompleted: {
        rebuildTargetIndexModel()
        refreshStatus()
        refreshWindows()
        loadBackgroundMethod()
        detectPhysicalGamepads()
    }
}
