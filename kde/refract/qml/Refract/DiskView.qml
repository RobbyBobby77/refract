import QtQuick

DeviceView {
    id: v

    required property string devId
    property int ordinal: 0
    readonly property var disks: Monitor.disks      // one detached copy per sample
    readonly property var disk: disks.find(d => d.id === devId) || ({})
    readonly property color tint: Theme.deviceColor("green")

    title: "Disk " + ordinal + " (" + devId + ")"
    subtitle: disk.model || ""

    Row {
        width: parent.width
        spacing: 14
        GraphCard {
            width: (parent.width - parent.spacing) / 2
            height: v.graphHeight
            title: "Active Time"
            trailing: "100%"
            series: Monitor.series("disk." + v.devId + ".busy")
            color: v.tint
        }
        GraphCard {
            width: (parent.width - parent.spacing) / 2
            height: v.graphHeight
            title: "Transfer Rate"
            series: Monitor.series("disk." + v.devId + ".read")
            series2: Monitor.series("disk." + v.devId + ".write")
            color: v.tint
            color2: Theme.deviceColor("teal")
            maxValue: 0
            minScale: 1024 * 1024
            legend1: "Read"
            legend2: "Write"
            format: function (b) { return Fmt.rate(b, 1) }
        }
    }

    TileGrid {
        tiles: [
            { caption: "Active Time", value: Fmt.num(v.disk.busy_percent), unit: "%", accent: v.tint },
            { caption: "Response Time", text: Fmt.isNum(v.disk.avg_response_ms) ? Fmt.num(v.disk.avg_response_ms, 2) + " ms" : Fmt.dash },
            { caption: "Read Speed", text: Fmt.rate(v.disk.read_bps, 1) },
            { caption: "Write Speed", text: Fmt.rate(v.disk.write_bps, 1) },
            { caption: "Temperature", text: Fmt.temp(v.disk.temperature_c) }
        ]
    }

    Card {
        width: parent.width
        visible: (v.disk.partitions || []).length > 0
        height: partCol.implicitHeight + 36
        Column {
            id: partCol
            width: parent.width
            spacing: 14
            Text {
                text: "Volumes"
                font.pixelSize: 13
                font.weight: Font.DemiBold
                color: Theme.label
            }
            Repeater {
                model: (v.disk.partitions || []).length
                Item {
                    id: part
                    required property int index
                    readonly property var p: (v.disk.partitions || [])[index] || ({})
                    width: partCol.width
                    height: 44
                    Row {
                        id: partHeader
                        width: parent.width
                        spacing: 8
                        Text {
                            text: part.p.mountpoint || ""
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                            color: Theme.label
                        }
                        Text {
                            text: (part.p.device || "") + " · " + (part.p.fstype || "")
                            font.pixelSize: 12
                            color: Theme.tertiaryLabel
                        }
                    }
                    Text {
                        anchors.right: parent.right
                        text: Fmt.bytes(part.p.used, 1) + " of " + Fmt.bytes(part.p.total, 1) + " used"
                        font.pixelSize: 12
                        font.weight: Font.Medium
                        font.features: Theme.tabular
                        color: Theme.secondaryLabel
                    }
                    UsageBar {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        barHeight: 8
                        showLegend: false
                        total: part.p.total || 1
                        segments: [{ value: part.p.used || 0, color: v.tint }]
                    }
                    TapHandler { onDoubleTapped: Monitor.launch("xdg-open", [part.p.mountpoint]) }
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                }
            }
        }
    }

    InfoCard {
        width: parent.width
        title: "Drive"
        rows: [
            ["Model", v.disk.model],
            ["Type", v.disk.type],
            ["Capacity", Fmt.bytes(v.disk.capacity, 2)],
            ["Formatted", Fmt.bytes(v.disk.formatted, 2)],
            ["System disk", v.disk.system_disk ? "Yes" : "No"],
            ["Removable", v.disk.removable ? "Yes" : "No"],
            ["Serial number", v.disk.serial],
            ["Total read", Fmt.bytes(v.disk.read_total, 1)],
            ["Total written", Fmt.bytes(v.disk.write_total, 1)],
            ["Rotation", Fmt.isNum(v.disk.rotation_rpm) && v.disk.rotation_rpm > 0 ? v.disk.rotation_rpm + " RPM" : ""]
        ]
    }
}
