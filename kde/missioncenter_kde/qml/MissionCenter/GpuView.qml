import QtQuick

DeviceView {
    id: v

    required property string devId
    property int ordinal: 0
    readonly property var gpus: Monitor.gpus
    readonly property var gpu: gpus.find(g => g.id === devId) || ({})
    readonly property color tint: Theme.deviceColor("pink")
    readonly property bool hasVideo: Fmt.isNum(gpu.encode) || Fmt.isNum(gpu.decode)
    readonly property bool hasGtt: Fmt.isNum(gpu.gtt_total) && gpu.gtt_total > 0

    title: "GPU " + ordinal
    subtitle: gpu.name || ""

    GraphCard {
        width: parent.width
        height: v.graphHeight
        title: "Utilization"
        trailing: "100%"
        series: Monitor.series("gpu." + v.devId + ".usage")
        color: v.tint
    }

    Row {
        width: parent.width
        spacing: 14
        readonly property int cards: 1 + (v.hasGtt ? 1 : 0) + (v.hasVideo ? 1 : 0)
        readonly property real cardWidth: (width - (cards - 1) * spacing) / cards

        GraphCard {
            width: parent.cardWidth
            height: 170
            padding: 14
            title: v.gpu.integrated ? "Dedicated Memory (carve-out)" : "Dedicated Memory"
            trailing: Fmt.bytes(v.gpu.vram_total, 1)
            series: Monitor.series("gpu." + v.devId + ".vram")
            color: Theme.deviceColor("purple")
            graph.showGrid: false
            format: function (p) { return Fmt.bytes(p / 100 * (v.gpu.vram_total || 0), 1) }
        }
        GraphCard {
            visible: v.hasGtt
            width: parent.cardWidth
            height: 170
            padding: 14
            title: "Shared Memory"
            trailing: Fmt.bytes(v.gpu.gtt_total, 1)
            series: Monitor.series("gpu." + v.devId + ".gtt")
            color: Theme.deviceColor("indigo")
            graph.showGrid: false
            format: function (p) { return Fmt.bytes(p / 100 * (v.gpu.gtt_total || 0), 1) }
        }
        GraphCard {
            visible: v.hasVideo
            width: parent.cardWidth
            height: 170
            padding: 14
            title: "Video Encode / Decode"
            trailing: "100%"
            series: Monitor.series("gpu." + v.devId + ".encode")
            series2: Monitor.series("gpu." + v.devId + ".decode")
            color: Theme.deviceColor("orange")
            color2: Theme.deviceColor("yellow")
            legend1: "Enc"
            legend2: "Dec"
            graph.showGrid: false
        }
    }

    TileGrid {
        tiles: [
            { caption: "Utilization", value: Fmt.num(v.gpu.usage), unit: "%", accent: v.tint },
            { caption: "Dedicated Memory", text: Fmt.bytes(v.gpu.vram_used, 1), footnote: "of " + Fmt.bytes(v.gpu.vram_total, 1) },
            { caption: "Shared Memory", text: Fmt.bytes(v.gpu.gtt_used, 1), footnote: v.hasGtt ? "of " + Fmt.bytes(v.gpu.gtt_total, 1) : "" },
            { caption: "Clock Speed", text: Fmt.freq(v.gpu.clock_mhz), footnote: Fmt.isNum(v.gpu.clock_max_mhz) ? "max " + Fmt.freq(v.gpu.clock_max_mhz) : "" },
            { caption: "Power Draw", text: Fmt.watts(v.gpu.power_w), footnote: Fmt.isNum(v.gpu.power_cap_w) ? "cap " + Fmt.watts(v.gpu.power_cap_w) : "" },
            { caption: "Temperature", text: Fmt.temp(v.gpu.temperature_c) }
        ]
    }

    InfoCard {
        width: parent.width
        title: "Graphics"
        rows: [
            ["Name", v.gpu.name],
            ["Vendor", v.gpu.vendor],
            ["Type", v.gpu.integrated ? "Integrated" : "Discrete"],
            ["Driver", v.gpu.driver],
            ["Driver version", v.gpu.driver_version],
            ["Bus", v.gpu.pcie],
            ["Maximum clock", Fmt.freq(v.gpu.clock_max_mhz)],
            ["Memory clock", Fmt.isNum(v.gpu.mem_clock_mhz) ? Fmt.freq(v.gpu.mem_clock_mhz) : Fmt.freq(v.gpu.mem_clock_max_mhz)],
            ["Power cap", Fmt.watts(v.gpu.power_cap_w)]
        ]
    }
}
