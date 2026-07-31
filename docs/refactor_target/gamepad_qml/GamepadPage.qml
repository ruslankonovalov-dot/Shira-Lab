// app/ui/pages/gamepad/GamepadPage.qml
// =======================================
// Главный контейнер для gamepad вкладки.
// Заменяет монолитный GamepadPage.qml (686 LOC) композицией из 4 карточек.
// ============================================
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../../components" as C

Item {
    id: root

    // Состояние из Bridge
    property var vigemStatus: ({})
    property var mappings: []
    property int targetId: 0

    // Bridge (будет установлен из main.qml)
    property var bridge: null

    Component.onCompleted: {
        if (bridge) refresh()
    }

    function refresh() {
        if (!bridge) return
        try {
            var r = JSON.parse(bridge.getVigemStatus())
            if (r.ok) root.vigemStatus = r
        } catch(e) {}
    }

    // ─── Layout ────────────────────────────────────
    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 16

            // ─── Status Card ─────────────────────────
            gamepad.GamepadStatusCard {
                Layout.fillWidth: true
                vigemStatus: root.vigemStatus
                onStartRequested: {
                    var r = JSON.parse(bridge.startVigem())
                    if (r.ok) root.refresh()
                }
                onStopRequested: {
                    var r = JSON.parse(bridge.stopVigem())
                    if (r.ok) root.refresh()
                }
            }

            // ─── Config Card ─────────────────────────
            gamepad.GamepadConfigCard {
                Layout.fillWidth: true
                controllerType: root.vigemStatus.controller_type || "xbox360"
                targetIndex: root.vigemStatus.target_index || 0
                onControllerTypeChanged: (type) => {
                    bridge.setVigemControllerType(type)
                    root.refresh()
                }
                onTargetIndexChanged: (idx) => {
                    bridge.setVigemTargetIndex(idx)
                    root.refresh()
                }
            }

            // ─── Mapping Card ────────────────────────
            gamepad.GamepadMappingCard {
                Layout.fillWidth: true
                mappings: root.mappings
                onMappingChanged: (key, btn) => {
                    bridge.setVigemButtonMap(key, btn)
                }
                onMappingAdded: (key, btn) => {
                    bridge.setVigemButtonMap(key, btn)
                }
                onMappingRemoved: (key) => {
                    bridge.setVigemButtonMap(key, "")
                }
            }

            // ─── Test Card ───────────────────────────
            gamepad.GamepadTestCard {
                Layout.fillWidth: true
                targetId: root.targetId
                onSetButtonsRequested: (tid, mask) => bridge.vigemSetButtons(tid, mask)
                onSetTriggersRequested: (tid, lt, rt) => bridge.vigemSetTriggers(tid, lt, rt)
                onSetLeftStickRequested: (tid, x, y) => bridge.vigemSetLeftStick(tid, x, y)
                onSetRightStickRequested: (tid, x, y) => bridge.vigemSetRightStick(tid, x, y)
                onResetRequested: (tid) => bridge.vigemReset(tid)
            }
        }
    }
}
