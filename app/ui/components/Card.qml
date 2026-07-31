// Card.qml — terminal section with Markdown-style horizontal rules (---)
// No border, no background — just thin rules above and below with side margins
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: card
    default property alias content: contentColumn.children
    property string title: ""
    property bool wide: false

    color: "transparent"
    border.width: 0

    // Auto-size height:
    // topRule(1) + gap(8) + title(20 if visible) + gap(8) + content + gap(8) + bottomRule(1)
    implicitHeight: 1 + 8 + (title.length > 0 ? 20 : 0) + 8 + contentColumn.implicitHeight + 8 + 1

    // Top horizontal rule (Markdown --- style, 16px side margins)
    Rectangle {
        id: topRule
        x: 16
        y: 0
        width: parent.width - 32
        height: 1
        color: mainWindow.termAcc
    }

    // Title — left-aligned with ▸ marker
    Text {
        id: titleLabel
        visible: card.title.length > 0
        x: 16
        y: 9   // topRule.y(0) + topRule.height(1) + gap(8)
        text: mainWindow.tr("card_title_prefix").replace("{}", card.title)
        color: mainWindow.termAcc
        font.family: "Consolas"
        font.pixelSize: 11
        font.bold: true
    }

    // Content — ColumnLayout (children are injected here via default property)
    ColumnLayout {
        id: contentColumn
        x: 16
        y: titleLabel.visible ? 29 : 9
        width: parent.width - 32
        spacing: 8
    }

    // Bottom horizontal rule
    Rectangle {
        id: bottomRule
        x: 16
        y: contentColumn.y + contentColumn.implicitHeight + 8
        width: parent.width - 32
        height: 1
        color: mainWindow.termAcc
    }
}
