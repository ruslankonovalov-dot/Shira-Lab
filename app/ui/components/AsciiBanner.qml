// AsciiBanner.qml — renders multi-line ASCII art centered via Canvas
// Used for the big page-title banners (like the SHIRA logo on HomePage)
import QtQuick

Canvas {
    id: canvas

    property string art: ""
    property string drawColor: "#00ff41"
    property int pixelSize: 11
    property int lineHeight: pixelSize + 2

    // Height = number of lines * lineHeight
    height: {
        var lines = art.split("\n").filter(function(l) { return l.length > 0 })
        return lines.length * lineHeight
    }

    onPaint: {
        var ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        ctx.font = pixelSize + "px Consolas"
        ctx.fillStyle = drawColor
        ctx.textBaseline = "top"

        var lines = art.split("\n").filter(function(l) { return l.length > 0 })

        // Find max width for centering
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
    onArtChanged: requestPaint()
    onDrawColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onPixelSizeChanged: requestPaint()
}
