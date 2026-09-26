import QtQuick

// One device in the sidebar: live sparkline, name and a one-line summary.
Item {
    id: item

    required property string key
    required property string kind
    required property string title
    required property string detail
    required property var usage
    required property var v1
    required property var v2
    required property string series
    required property string series2
    required property string colorName
    required property real maxValue
    required property string devId

    property bool selected: false
    signal activated()

    readonly property color tint: Theme.deviceColor(colorName)
    height: 62

    function summary() {
        switch (kind) {
        case "cpu": return Fmt.percent(usage) + "  " + Fmt.freq(v1)
        case "memory": return Fmt.bytes(v1, 1) + " / " + Fmt.bytes(v2, 0) + "  (" + Fmt.percent(usage) + ")"
        case "disk": return detail + "  " + Fmt.percent(usage)
        case "network": return "↓ " + Fmt.netRate(v1, 0) + "   ↑ " + Fmt.netRate(v2, 0)
        case "gpu": return Fmt.percent(usage) + (Fmt.isNum(v1) ? "  " + Fmt.temp(v1) : "")
        case "fan": return Fmt.rpm(v1) + (Fmt.isNum(usage) ? "  " + Fmt.percent(usage) : "")
        case "battery": return Fmt.percent(usage) + "  " + detail
        }
        return ""
    }

    function subtitleTitle() {
        if (kind === "disk") return title + " (" + devId + ")"
        return title
    }

    Rectangle {
        id: bg
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        radius: 13
        color: item.selected ? (Theme.dark ? Qt.rgba(1, 1, 1, 0.13) : Qt.rgba(0, 0, 0, 0.075))
             : hover.hovered ? Theme.hoverFill : "transparent"
        border.width: item.selected ? 1 : 0
        border.color: Theme.dark ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(1, 1, 1, 0.8)
        Behavior on color { ColorAnimation { duration: Theme.quick } }
    }

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 18
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12

        Rectangle {
            id: spark
            width: 54; height: 38
            radius: 9
            color: Theme.alpha(item.tint, Theme.dark ? 0.12 : 0.10)
            border.width: 1
            border.color: Theme.alpha(item.tint, 0.38)
            clip: true
            Graph {
                anchors.fill: parent
                anchors.margins: 1
                series: Monitor.series(item.series)
                series2: item.series2 !== "" ? Monitor.series(item.series2) : null
                color: item.tint
                color2: Theme.mix(item.tint, Theme.label, 0.35)
                maxValue: item.maxValue
                points: Math.min(Prefs.graphPoints, 40)
                lineWidth: 1.4
                fillOpacity: 0.5
                showGrid: false
                interactive: false
            }
        }

        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - spark.width - parent.spacing
            spacing: 2
            Text {
                width: parent.width
                text: item.subtitleTitle()
                font.pixelSize: 14
                font.weight: Font.DemiBold
                color: Theme.label
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                text: item.summary()
                font.pixelSize: 12
                font.weight: Font.Medium
                font.features: Theme.tabular
                color: Theme.secondaryLabel
                elide: Text.ElideRight
            }
        }
    }

    HoverHandler { id: hover }
    TapHandler { onTapped: item.activated() }
}
