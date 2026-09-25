import QtQuick

DeviceView {
    id: v

    readonly property var mem: Monitor.memory
    readonly property color tint: Theme.deviceColor("purple")
    readonly property real total: mem.total || 0
    readonly property real cachedPart: Math.max(0, (mem.available || 0) - (mem.free || 0))

    title: "Memory"
    subtitle: Fmt.bytes(v.total, 0) + " installed"

    GraphCard {
        width: parent.width
        height: v.graphHeight
        title: "Memory Usage"
        trailing: Fmt.bytes(v.total, 1)
        series: Monitor.series("mem")
        color: v.tint
        format: function (pct) { return Fmt.bytes(pct / 100 * v.total, 1) }
    }

    Row {
        width: parent.width
        spacing: 14

        Card {
            width: (Monitor.memory.swap_total || 0) > 0 ? (parent.width - parent.spacing) * 0.58 : parent.width
            height: 118
            Column {
                anchors.fill: parent
                spacing: 12
                Text {
                    text: "Memory Composition"
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    color: Theme.label
                }
                UsageBar {
                    width: parent.width
                    total: v.total
                    segments: [
                        { value: v.mem.used || 0, color: v.tint, label: "In use" },
                        { value: v.cachedPart, color: Theme.alpha(v.tint, 0.45), label: "Cached" },
                        { value: v.mem.free || 0, color: "transparent", label: "Free" }
                    ]
                }
            }
        }

        GraphCard {
            visible: (Monitor.memory.swap_total || 0) > 0
            width: (parent.width - parent.spacing) * 0.42
            height: 118
            padding: 14
            title: "Swap"
            trailing: Fmt.bytes(v.mem.swap_used, 1) + " of " + Fmt.bytes(v.mem.swap_total, 0)
            series: Monitor.series("mem.swap")
            color: Theme.mix(v.tint, Theme.pink, 0.5)
            graph.showGrid: false
            format: function (pct) { return Fmt.bytes(pct / 100 * (v.mem.swap_total || 0), 1) }
        }
    }

    TileGrid {
        tiles: [
            { caption: "In Use", text: Fmt.bytes(v.mem.used, 1), accent: v.tint,
              footnote: Fmt.isNum(v.mem.compressed) && v.mem.compressed > 1e6 ? Fmt.bytes(v.mem.compressed, 1) + " compressed" : "" },
            { caption: "Available", text: Fmt.bytes(v.mem.available, 1) },
            { caption: "Committed", text: Fmt.bytes(v.mem.committed, 1), footnote: "of " + Fmt.bytes(v.mem.commit_limit, 1) },
            { caption: "Cached", text: Fmt.bytes(v.mem.cached, 1) },
            { caption: "Swap Used", text: Fmt.bytes(v.mem.swap_used, 1), footnote: "of " + Fmt.bytes(v.mem.swap_total, 1) }
        ]
    }

    InfoCard {
        width: parent.width
        title: "Details"
        rows: [
            ["Total", Fmt.bytes(v.mem.total, 2)],
            ["Free", Fmt.bytes(v.mem.free, 2)],
            ["Buffers", Fmt.bytes(v.mem.buffers, 1)],
            ["Dirty", Fmt.bytes(v.mem.dirty, 1)],
            ["Shared", Fmt.bytes(v.mem.shared, 1)],
            ["Commit limit", Fmt.bytes(v.mem.commit_limit, 1)],
            ["Swap total", Fmt.bytes(v.mem.swap_total, 1)],
            ["Compressed (zram)", Fmt.isNum(v.mem.compressed) ? Fmt.bytes(v.mem.compressed, 1) : ""]
        ]
    }
}
