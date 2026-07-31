// MacroPage.qml -- v1.0.0 UX upgrade
// Features added:
//   [OK] Undo/Redo buttons (Ctrl+Z / Ctrl+Y)
//   [OK] Delete action per-row (X button)
//   [OK] Drag & Drop reorder (drag handle =)
//   [OK] Tooltips on all buttons
//   [OK] Action list panel (separate card)
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Rectangle {
    color: mainWindow.termBg

    property var status: ({})

        // v1.0.0 i18n: Run modes (rebuilt on language change)
        property var runModes: []
        function rebuildRunModes() {
            var _ = Bridge.currentLang
            runModes = [
                { text: mainWindow.tr("macro.mode_sequential"), value: "SEQUENTIAL" },
                { text: mainWindow.tr("macro.mode_parallel"), value: "PARALLEL" }
            ]
        }

    property var actions: []
    property bool canUndo: false
    property bool canRedo: false

    function updateStatus(s) {
        status = s
        actions = s.actions || []
        canUndo = s.can_undo || false
        canRedo = s.can_redo || false
        var runningText = s.is_running ? mainWindow.tr("macro.running") : mainWindow.tr("macro.idle")
        var modeText = s.run_mode || "SEQUENTIAL"
        var actionsText = s.actions_count || 0
        statusLabel.text = mainWindow.tr("status.macro_idle").replace("{}", runningText).replace("{}", modeText).replace("{}", actionsText)
            + (canUndo ? " | [U] " + mainWindow.tr("macro.undo") + "(" + s.undo_count + ")" : "")
            + (canRedo ? " | [R] " + mainWindow.tr("macro.redo") + "(" + s.redo_count + ")" : "")
    }

    function refreshWindows() {
        var r = Bridge.getWindows()
        var model = [{ text: mainWindow.tr("combo.global_screen"), value: 0 }]
        for (var i = 0; i < r.windows.length; i++) {
            model.push({ text: r.windows[i].title, value: r.windows[i].hwnd })
        }
        macroTargetWindow.model = model
        loadTargetWindow()
    }

    function loadTargetWindow() {
        var r = Bridge.getModuleTargetWindow("macro")
        var targetHwnd = r.hwnd || 0
        for (var i = 0; i < macroTargetWindow.model.length; i++) {
            if (macroTargetWindow.model[i].value === targetHwnd) {
                macroTargetWindow.currentIndex = i
                break
            }
        }
        targetWindowLabel.text = mainWindow.tr("target.current") + " " + r.name + (r.hwnd ? " (hwnd: " + r.hwnd + ")" : "")
    }

    function loadBackgroundMethod() {
        var r = Bridge.getMacroStatus()
        if (r.background_method) {
            for (var i = 0; i < macroBackgroundMethod.model.length; i++) {
                if (macroBackgroundMethod.model[i].value === r.background_method) {
                    macroBackgroundMethod.currentIndex = i
                    break
                }
            }
        }
    }

    Component.onCompleted: {
        rebuildRunModes()
        refreshWindows()
        loadBackgroundMethod()
    }

    Connections {
        target: Bridge
        function onSettingsChanged() {
            loadBackgroundMethod()
        }
    }

    // --- Keyboard shortcuts for undo/redo -------------------------
    Shortcut {
        sequence: "Ctrl+Z"
        onActivated: {
            var r = Bridge.macroUndo()
            updateStatus(r)
        }
        enabled: canUndo
    }
    Shortcut {
        sequence: "Ctrl+Y"
        onActivated: {
            var r = Bridge.macroRedo()
            updateStatus(r)
        }
        enabled: canRedo
    }
    Shortcut {
        sequence: "Ctrl+Shift+Z"
        onActivated: {
            var r = Bridge.macroRedo()
            updateStatus(r)
        }
        enabled: canRedo
    }


    // v1.0.0 i18n: Rebuild models on language change
    Connections {
        target: Bridge
        function onLangChanged() {
            rebuildRunModes()
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
                        id: macroTargetWindow
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        model: [{ text: mainWindow.tr("combo.global_screen"), value: 0 }]
                        textRole: "text"
                        valueRole: "value"
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && currentIndex < model.length) {
                                Bridge.setModuleTargetWindow("macro", model[currentIndex].value)
                            }
                            loadTargetWindow()
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("btn.refresh")
                            tooltip: mainWindow.tr("tip.refresh_windows")
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

            // --- Macro Config Card --------------------------------------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("card.macro_config")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text { text: mainWindow.tr("lbl.run_mode"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: macroMode
                        Layout.fillWidth: true
                        Layout.preferredHeight: 34
                        model: runModes
                        textRole: "text"
                        valueRole: "value"
                        tooltip: mainWindow.tr("tip.macro_run_mode")
                        onCurrentValueChanged: {
                            if (currentValue) {
                                var r = Bridge.setMacroMode(currentValue)
                                updateStatus(r)
                            }
                        }
                    }

                    Text { text: mainWindow.tr("lbl.background_method"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermComboBox {
                        id: macroBackgroundMethod
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
                        tooltip: mainWindow.tr("tip.macro_bg_method")
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TermButton {
                            text: mainWindow.tr("btn.apply_bg_method")
                            tooltip: mainWindow.tr("tip.apply_bg_method")
                            Layout.preferredWidth: 160
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { var r = Bridge.setMacroBackgroundMethod(macroBackgroundMethod.currentValue); updateStatus(r); }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Text { text: mainWindow.tr("lbl.target_keys"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                    TermTextField { id: macroKey; Layout.fillWidth: true; text: mainWindow.tr("lbl.macro_default_key") }

                    // Delay + Hold side by side
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Text { text: mainWindow.tr("lbl.delay_sec"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                            TermTextField { id: macroDelay; Layout.fillWidth: true; text: mainWindow.tr("lbl.macro_default_delay") }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Text { text: mainWindow.tr("lbl.hold_sec"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 10; Layout.fillWidth: true }
                            TermTextField { id: macroHold; Layout.fillWidth: true; text: mainWindow.tr("lbl.macro_default_hold") }
                        }
                    }

                    // --- Action buttons row with UNDO/REDO ---------------------
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TermButton {
                            text: mainWindow.tr("lbl.macro_add")
                            tooltip: mainWindow.tr("tip.macro_add")
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: {
                                var r = Bridge.addMacroAction(macroKey.text, parseFloat(macroDelay.text)||0.5, parseFloat(macroHold.text)||0.05)
                                updateStatus(r)
                            }
                        }
                        TermButton {
                            text: mainWindow.tr("lbl.macro_undo")
                            tooltip: mainWindow.tr("tip.macro_undo")
                            Layout.preferredWidth: 90
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            enabled: canUndo
                            opacity: enabled ? 1.0 : 0.3
                            onClicked: {
                                var r = Bridge.macroUndo()
                                updateStatus(r)
                            }
                        }
                        TermButton {
                            text: mainWindow.tr("lbl.macro_redo")
                            tooltip: mainWindow.tr("tip.macro_redo")
                            Layout.preferredWidth: 90
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            enabled: canRedo
                            opacity: enabled ? 1.0 : 0.3
                            onClicked: {
                                var r = Bridge.macroRedo()
                                updateStatus(r)
                            }
                        }
                        TermButton {
                            text: mainWindow.tr("lbl.macro_clear")
                            tooltip: mainWindow.tr("tip.macro_clear")
                            Layout.preferredWidth: 90
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { var r = Bridge.clearMacroActions(); updateStatus(r) }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    // --- Run/Stop row -------------------------------------------
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        TermButton {
                            text: mainWindow.tr("lbl.macro_start")
                            tooltip: mainWindow.tr("tip.macro_start")
                            Layout.preferredWidth: 110
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { var r = Bridge.startMacro(); updateStatus(r) }
                        }
                        TermButton {
                            text: mainWindow.tr("lbl.macro_stop")
                            tooltip: mainWindow.tr("tip.macro_stop")
                            Layout.preferredWidth: 110
                            Layout.preferredHeight: 34
                            font.pixelSize: 11
                            onClicked: { var r = Bridge.stopMacro(); updateStatus(r) }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Text { id: statusLabel; text: mainWindow.tr("status.macro_idle").replace("{}", "SEQUENTIAL").replace("{}", "0"); color: mainWindow.termMuted; font.family: "Consolas"; font.pixelSize: 11; Layout.fillWidth: true }
                }
            }

            // --- NEW: Actions List Card (with drag&drop + delete) -------------
            Card {
                Layout.fillWidth: true
                title: mainWindow.tr("macro.actions_label").replace("()", " (" + actions.length + ")")

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Text {
                        text: mainWindow.tr("lbl.drag_hint")
                        color: mainWindow.termMuted
                        font.family: "Consolas"
                        font.pixelSize: 10
                        Layout.fillWidth: true
                        visible: actions.length > 0
                    }

                    // Empty state
                    Text {
                        text: mainWindow.tr("lbl.no_actions")
                        color: mainWindow.termMuted
                        font.family: "Consolas"
                        font.pixelSize: 10
                        Layout.fillWidth: true
                        visible: actions.length === 0
                    }

                    // Action list
                    ListView {
                        id: actionsList
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(actions.length * 36, 250)
                        model: actions
                        clip: true
                        spacing: 2
                        interactive: true

                        property int dragIndex: -1

                        delegate: Rectangle {
                            id: actionRow
                            width: actionsList.width
                            height: 32
                            color: dragArea.drag.active ? Qt.rgba(0.2, 1.0, 0.2, 0.15) : (index % 2 === 0 ? "transparent" : Qt.rgba(1, 1, 1, 0.02))
                            border.color: dragArea.drag.active ? mainWindow.termAcc : "transparent"
                            border.width: 1

                            property int visualIndex: index
                            property var actionData: modelData

                            Drag.active: dragArea.drag.active
                            Drag.source: actionRow
                            Drag.hotSpot.x: width / 2
                            Drag.hotSpot.y: height / 2

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 8

                                // Drag handle
                                Text {
                                    text: mainWindow.tr("lbl.drag_handle")
                                    color: mainWindow.termMuted
                                    font.family: "Consolas"
                                    font.pixelSize: 14
                                    Layout.preferredWidth: 16
                                    Layout.alignment: Qt.AlignVCenter

                                    MouseArea {
                                        id: dragArea
                                        anchors.fill: parent
                                        cursorShape: Qt.SizeAllCursor
                                        drag.target: actionRow
                                        drag.axis: Drag.YAxis

                                        onReleased: {
                                            if (actionRow.Drag.target) {
                                                var to = actionRow.Drag.target.visualIndex
                                                if (to !== undefined && to !== index) {
                                                    var r = Bridge.macroMoveAction(index, to)
                                                    updateStatus(r)
                                                }
                                            }
                                            actionRow.Drag.cancel()
                                        }
                                    }
                                }

                                // Action number
                                Text {
                                    text: mainWindow.tr("lbl.action_num") + (index + 1)
                                    color: mainWindow.termMuted
                                    font.family: "Consolas"
                                    font.pixelSize: 11
                                    Layout.preferredWidth: 30
                                    Layout.alignment: Qt.AlignVCenter
                                }

                                // Key
                                Text {
                                    text: modelData.key
                                    color: mainWindow.termFg
                                    font.family: "Consolas"
                                    font.pixelSize: 11
                                    font.bold: true
                                    Layout.preferredWidth: 80
                                    Layout.alignment: Qt.AlignVCenter
                                }

                                // Type
                                Text {
                                    text: modelData.hold > 0 ? mainWindow.tr("gamepad.hold").replace("{}", (modelData.hold * 1000).toFixed(0) + "ms") : mainWindow.tr("gamepad.tap")
                                    color: modelData.hold > 0 ? mainWindow.termWarning : mainWindow.termMuted
                                    font.family: "Consolas"
                                    font.pixelSize: 10
                                    Layout.preferredWidth: 100
                                    Layout.alignment: Qt.AlignVCenter
                                }

                                // Delay
                                Text {
                                    text: mainWindow.tr("lbl.delay") + " " + modelData.delay.toFixed(2) + "s"
                                    color: mainWindow.termMuted
                                    font.family: "Consolas"
                                    font.pixelSize: 10
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignVCenter
                                }

                                // Delete button
                                TermButton {
                                    text: mainWindow.tr("lbl.delete_btn")
                                    tooltip: mainWindow.tr("tip.macro_delete_action")
                                    Layout.preferredWidth: 32
                                    Layout.preferredHeight: 24
                                    font.pixelSize: 11
                                    onClicked: {
                                        var r = Bridge.macroDeleteAction(index)
                                        updateStatus(r)
                                    }
                                }
                            }

                            // Drop target area
                            DropArea {
                                anchors.fill: parent
                                anchors.margins: 4
                                onEntered: {
                                    var src = drag.source
                                    var dst = actionRow
                                    if (src && src.visualIndex !== dst.visualIndex) {
                                        // Visual feedback only -- actual move on drop
                                    }
                                }
                                onDropped: {
                                    var src = drag.source
                                    if (src && src.visualIndex !== actionRow.visualIndex) {
                                        var r = Bridge.macroMoveAction(src.visualIndex, actionRow.visualIndex)
                                        updateStatus(r)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Bottom spacer
            Item { Layout.fillHeight: true; Layout.fillWidth: true; Layout.minimumHeight: 16 }
        }
    }
}
