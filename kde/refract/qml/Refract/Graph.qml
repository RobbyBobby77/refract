import QtQuick
import QtQuick.Shapes

// History graph: smooth monotone curve with a gradient fill, optional second
// series, grid, and a hover readout. Rendered on the GPU via Shape's curve
// renderer.
Item {
    id: g

    property var series: null
    property var series2: null
    property color color: Theme.blue
    property color color2: Theme.alpha(color, 0.9)
    property real maxValue: 100          // <= 0: autoscale
    property real minScale: 1            // floor for autoscaling
    property int points: Prefs.graphPoints
    property real lineWidth: 2
    property real fillOpacity: 0.42
    property bool showGrid: true
    property bool interactive: true
    property bool smooth: Prefs.smoothGraphs
    property var format: function (v) { return Fmt.percent(v) }
    property string label1: ""
    property string label2: ""

    // Copy the Python list into a JS value once: slicing the property directly
    // re-reads (and re-converts) the whole history for every element touched.
    readonly property var history: series ? series.values : []
    readonly property var history2: series2 ? series2.values : []
    readonly property var values: history.slice(-points)
    readonly property var values2: history2.slice(-points)
    readonly property real scaleMax: {
        if (maxValue > 0) return maxValue
        let m = minScale
        for (const v of values) if (v === v) m = Math.max(m, v)
        for (const v of values2) if (v === v) m = Math.max(m, v)
        return Fmt.niceMax(m)
    }

    function yFor(v) {
        const pad = lineWidth
        const t = Math.max(0, Math.min(1, v / scaleMax))
        return (height - pad) - t * (height - 2 * pad)
    }

    // Index of the first sample that exists; older history is NaN and is
    // left blank so a fresh graph fills in from the right.
    function firstSample(vals) {
        let i = 0
        while (i < vals.length && vals[i] !== vals[i]) ++i
        return i
    }

    readonly property string linePath: buildPath(values)
    readonly property string linePath2: series2 ? buildPath(values2) : ""
    function closed(path) {
        if (path === "") return ""
        const x0 = path.slice(1, path.indexOf(" "))
        return path + " L" + width.toFixed(2) + " " + height.toFixed(2) + " L" + x0 + " " + height.toFixed(2) + " Z"
    }

    function buildPath(all) {
        const start = firstSample(all)
        const vals = all.slice(start).map(v => (v === v ? v : 0))
        const n = vals.length
        if (all.length < 2 || n < 2 || width <= 0 || height <= 0) return ""
        const dx = width / (all.length - 1)
        const x0 = start * dx
        const ys = vals.map(v => yFor(v))
        let d = "M" + x0.toFixed(2) + " " + ys[0].toFixed(2)
        if (!smooth) {
            for (let i = 1; i < n; ++i) d += " L" + (x0 + i * dx).toFixed(2) + " " + ys[i].toFixed(2)
        } else {
            // Fritsch–Carlson monotone cubic: smooth without overshooting.
            const sl = []
            for (let i = 0; i < n - 1; ++i) sl.push((ys[i + 1] - ys[i]) / dx)
            const m = new Array(n)
            m[0] = sl[0]
            m[n - 1] = sl[n - 2]
            for (let i = 1; i < n - 1; ++i) m[i] = sl[i - 1] * sl[i] <= 0 ? 0 : (sl[i - 1] + sl[i]) / 2
            for (let i = 0; i < n - 1; ++i) {
                if (sl[i] === 0) { m[i] = 0; m[i + 1] = 0; continue }
                const a = m[i] / sl[i], b = m[i + 1] / sl[i]
                const s = a * a + b * b
                if (s > 9) { const t = 3 / Math.sqrt(s); m[i] = t * a * sl[i]; m[i + 1] = t * b * sl[i] }
            }
            for (let i = 0; i < n - 1; ++i) {
                const xa = x0 + i * dx, xb = xa + dx
                d += " C" + (xa + dx / 3).toFixed(2) + " " + (ys[i] + m[i] * dx / 3).toFixed(2)
                   + " " + (xb - dx / 3).toFixed(2) + " " + (ys[i + 1] - m[i + 1] * dx / 3).toFixed(2)
                   + " " + xb.toFixed(2) + " " + ys[i + 1].toFixed(2)
            }
        }
        return d
    }

    // grid
    Repeater {
        model: g.showGrid ? 3 : 0
        Rectangle {
            required property int index
            y: Math.round(g.height * (index + 1) / 4)
            width: g.width
            height: 1
            color: Theme.separator
        }
    }
    Repeater {
        model: g.showGrid ? 5 : 0
        Rectangle {
            required property int index
            x: Math.round(g.width * (index + 1) / 6)
            width: 1
            height: g.height
            color: Theme.alpha(Theme.separator, Theme.separator.a * 0.6)
        }
    }

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            strokeColor: "transparent"
            strokeWidth: 0
            fillGradient: LinearGradient {
                x1: 0; y1: 0; x2: 0; y2: g.height
                GradientStop { position: 0; color: Theme.alpha(g.color2, g.series2 ? g.fillOpacity * 0.55 : 0) }
                GradientStop { position: 1; color: Theme.alpha(g.color2, 0) }
            }
            PathSvg { path: g.closed(g.linePath2) }
        }
        ShapePath {
            strokeColor: "transparent"
            strokeWidth: 0
            fillGradient: LinearGradient {
                x1: 0; y1: 0; x2: 0; y2: g.height
                GradientStop { position: 0; color: Theme.alpha(g.color, g.fillOpacity) }
                GradientStop { position: 1; color: Theme.alpha(g.color, 0.02) }
            }
            PathSvg { path: g.closed(g.linePath) }
        }
        ShapePath {
            strokeColor: g.series2 ? g.color2 : "transparent"
            strokeWidth: g.lineWidth * 0.85
            fillColor: "transparent"
            joinStyle: ShapePath.RoundJoin
            capStyle: ShapePath.RoundCap
            dashPattern: [3, 2.2]
            strokeStyle: ShapePath.DashLine
            PathSvg { path: g.linePath2 }
        }
        ShapePath {
            strokeColor: g.color
            strokeWidth: g.lineWidth
            fillColor: "transparent"
            joinStyle: ShapePath.RoundJoin
            capStyle: ShapePath.RoundCap
            PathSvg { path: g.linePath }
        }
    }

    // live dot at the leading edge
    Rectangle {
        visible: g.values.length > 1 && !hover.hovered && g.interactive && Fmt.isNum(g.values[g.values.length - 1])
        width: 7; height: 7; radius: 3.5
        x: g.width - width / 2
        y: g.yFor(g.values[g.values.length - 1] || 0) - height / 2
        color: g.color
        border.width: 1.5
        border.color: Theme.dark ? "#1c1c1e" : "#ffffff"
    }

    // hover readout
    HoverHandler {
        id: hover
        enabled: g.interactive && !StartupOptions.screenshot
    }
    Item {
        id: readout
        visible: hover.hovered && g.values.length > 1
        readonly property int idx: Math.max(0, Math.min(g.values.length - 1,
            Math.round(hover.point.position.x / Math.max(g.width, 1) * (g.values.length - 1))))
        readonly property real xPos: g.values.length > 1 ? idx * g.width / (g.values.length - 1) : 0
        anchors.fill: parent

        Rectangle {
            x: readout.xPos
            width: 1
            height: g.height
            color: Theme.alpha(Theme.label, 0.28)
        }
        Rectangle {
            width: 9; height: 9; radius: 4.5
            visible: Fmt.isNum(g.values[readout.idx])
            x: readout.xPos - 4.5
            y: g.yFor(g.values[readout.idx] || 0) - 4.5
            color: g.color
            border.width: 2
            border.color: Theme.dark ? "#1c1c1e" : "#ffffff"
        }
        Rectangle {
            id: bubble
            readonly property real secondsAgo: (g.values.length - 1 - readout.idx) * Monitor.interval / 1000
            function describe() {
                const dim = t => "<font color='" + Theme.secondaryLabel + "'>" + t + "</font>"
                let t = (g.label1 ? g.label1 + " " : "") + g.format(g.values[readout.idx])
                if (g.series2)
                    t += "  " + dim("·") + "  " + (g.label2 ? g.label2 + " " : "") + g.format(g.values2[readout.idx])
                return t + "  " + dim(secondsAgo < 0.5 ? "now" : Math.round(secondsAgo) + "s ago")
            }
            width: bubbleText.implicitWidth + 20
            height: bubbleText.implicitHeight + 12
            radius: height / 2
            x: Math.max(0, Math.min(g.width - width, readout.xPos - width / 2))
            y: 6
            color: Theme.dark ? Qt.rgba(0.17, 0.17, 0.19, 0.94) : Qt.rgba(1, 1, 1, 0.96)
            border.width: 1
            border.color: Theme.separator
            Text {
                id: bubbleText
                anchors.centerIn: parent
                font.family: Theme.fontFamily
                font.pixelSize: 12
                font.weight: Font.DemiBold
                font.features: Theme.tabular
                color: Theme.label
                textFormat: Text.StyledText
                // only evaluated while hovering, so idle graphs stay cheap
                text: readout.visible ? bubble.describe() : ""
            }
        }
    }
}
