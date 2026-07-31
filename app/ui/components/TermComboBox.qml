// TermComboBox.qml — выпадающий список консольного стиля
import QtQuick
import QtQuick.Controls

ComboBox {
    id: control
    property string tooltip: ""
    ToolTip.visible: tooltip.length > 0 && control.hovered
    ToolTip.delay: 500
    ToolTip.text: tooltip

    property string itemTextRole: ""
    property string itemValueRole: ""

    font.family: "Consolas"
    font.pixelSize: 11

    // ─── Text/Value Role Resolution ───
    property string resolvedTextRole: itemTextRole || textRole || "text"
    property string resolvedValueRole: itemValueRole || valueRole || "value"

    // ─── selectedValue (computed from currentIndex + resolvedValueRole) ───
    readonly property var selectedValue: {
        if (currentIndex >= 0 && model) {
            var item = null
            if (model.get) {
                item = model.get(currentIndex)
            } else if (model.length !== undefined) {
                item = model[currentIndex]
            }
            if (item) {
                var role = resolvedValueRole
                if (role && item[role] !== undefined) return item[role]
                if (typeof item === "string") return item
            }
        }
        return ""
    }

    // ─── Standard ComboBox popup (styled) ───
    // Не переопределяем popup полностью — стилизуем стандартный
    // Это гарантирует что open/close работает из коробки

    delegate: ItemDelegate {
        width: control.width
        height: 28
        padding: 0

        contentItem: Text {
            text: {
                var role = control.resolvedTextRole
                if (role && model && model[role] !== undefined) {
                    return model[role]
                }
                if (typeof modelData === "string") return modelData
                if (modelData && typeof modelData === "object") {
                    var r = control.resolvedTextRole
                    if (r && modelData[r] !== undefined) return modelData[r]
                }
                return String(modelData || "")
            }
            color: control.highlightedIndex === index ? mainWindow.termAcc : mainWindow.termFg
            font: control.font
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
            leftPadding: 10
            rightPadding: 10
        }

        background: Rectangle {
            color: control.highlightedIndex === index ? mainWindow.termMuted : mainWindow.termBg
        }

        onClicked: control.currentIndex = index
    }

    // ─── Display Text (Selected Item) ───
    displayText: {
        if (currentIndex >= 0 && model) {
            var item = null
            if (model.get) {
                item = model.get(currentIndex)
            } else if (model.length !== undefined) {
                item = model[currentIndex]
            }
            if (item) {
                var role = resolvedTextRole
                if (role && item[role] !== undefined) return item[role]
                if (typeof item === "string") return item
            }
        }
        return ""
    }

    // ─── Content Item (Button Area) ───
    contentItem: Text {
        text: control.displayText
        color: mainWindow.termFg
        font: control.font
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignLeft
        leftPadding: 10
        rightPadding: 28
        elide: Text.ElideRight
    }

    // ─── Background ───
    background: Rectangle {
        color: Qt.darker(mainWindow.termBg, 1.5)
        border.color: control.hovered || control.popup.visible ? mainWindow.termAcc : mainWindow.termMuted
        border.width: 1
        radius: 0

        // Dropdown arrow (ASCII)
        Text {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.margins: 10
            text: "▼"
            color: control.hovered || control.popup.visible ? mainWindow.termAcc : mainWindow.termMuted
            font.family: "Consolas"
            font.pixelSize: 9
        }
    }

    // ─── Popup styling (standard popup, styled) ───
    popup.background: Rectangle {
        color: mainWindow.termBg
        border.color: mainWindow.termAcc
        border.width: 1
    }
}
