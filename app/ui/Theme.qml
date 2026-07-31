// Theme.qml — общие стили и палитры
import QtQuick

QtObject {
    // Палитры берутся из Bridge.getPalettes() — runtime_state.TERMINAL_PALETTES (single source of truth)
    property var palettes: {}

    // Общие размеры
    readonly property int chromeBarHeight: 32
    readonly property int navRowHeight: 40
    readonly property int cardPadding: 14
    readonly property int cardRadius: 0
    readonly property int cornerAccentSize: 8

    // Шрифт
    readonly property string fontFamily: "Consolas, Courier New, monospace"
    readonly property int fontSize: 11
    readonly property int fontSizeSmall: 10
    readonly property int fontSizeTiny: 9
}
