import QtQuick
import QtQuick.Shapes

// Refract's history graph, trimmed for the widget: a smooth monotone curve
// over a gradient fill, with an optional dashed second series.
Item {
    id: g

    property var values: []
    property var values2: []
    property color color: "#0A84FF"
    property color color2: color
    property real maxValue: 100          // <= 0: autoscale
    property real minScale: 1            // floor for autoscaling
    property real lineWidth: 1.4
    property real fillOpacity: 0.5

    readonly property bool hasSecond: values2.length > 0
    readonly property real scaleMax: {
        if (maxValue > 0) return maxValue
        let m = minScale
        for (const v of values) if (v === v) m = Math.max(m, v)
        for (const v of values2) if (v === v) m = Math.max(m, v)
        return m * 1.15
    }

    function alpha(c, a) { return Qt.rgba(c.r, c.g, c.b, a) }

    function yFor(v) {
        const pad = lineWidth
        const t = Math.max(0, Math.min(1, v / scaleMax))
        return (height - pad) - t * (height - 2 * pad)
    }

    // Older history is NaN and stays blank, so a new graph fills in from the right.
    function firstSample(vals) {
        let i = 0
        while (i < vals.length && vals[i] !== vals[i]) ++i
        return i
    }

    function buildPath(all) {
        const start = firstSample(all)
        const vals = all.slice(start).map(v => (v === v ? v : 0))
        const n = vals.length
        if (all.length < 2 || n < 2 || width <= 0 || height <= 0) return ""
        const dx = width / (all.length - 1)
        const x0 = start * dx
        const ys = vals.map(v => yFor(v))
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
        let d = "M" + x0.toFixed(2) + " " + ys[0].toFixed(2)
        for (let i = 0; i < n - 1; ++i) {
            const xa = x0 + i * dx, xb = xa + dx
            d += " C" + (xa + dx / 3).toFixed(2) + " " + (ys[i] + m[i] * dx / 3).toFixed(2)
               + " " + (xb - dx / 3).toFixed(2) + " " + (ys[i + 1] - m[i + 1] * dx / 3).toFixed(2)
               + " " + xb.toFixed(2) + " " + ys[i + 1].toFixed(2)
        }
        return d
    }

    function closed(path) {
        if (path === "") return ""
        const x0 = path.slice(1, path.indexOf(" "))
        return path + " L" + width.toFixed(2) + " " + height.toFixed(2) + " L" + x0 + " " + height.toFixed(2) + " Z"
    }

    readonly property string linePath: buildPath(values)
    readonly property string linePath2: hasSecond ? buildPath(values2) : ""

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            strokeColor: "transparent"
            strokeWidth: 0
            fillGradient: LinearGradient {
                x1: 0; y1: 0; x2: 0; y2: g.height
                GradientStop { position: 0; color: g.alpha(g.color2, g.hasSecond ? g.fillOpacity * 0.55 : 0) }
                GradientStop { position: 1; color: g.alpha(g.color2, 0) }
            }
            PathSvg { path: g.closed(g.linePath2) }
        }
        ShapePath {
            strokeColor: "transparent"
            strokeWidth: 0
            fillGradient: LinearGradient {
                x1: 0; y1: 0; x2: 0; y2: g.height
                GradientStop { position: 0; color: g.alpha(g.color, g.fillOpacity) }
                GradientStop { position: 1; color: g.alpha(g.color, 0.02) }
            }
            PathSvg { path: g.closed(g.linePath) }
        }
        ShapePath {
            strokeColor: g.hasSecond ? g.color2 : "transparent"
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
}
