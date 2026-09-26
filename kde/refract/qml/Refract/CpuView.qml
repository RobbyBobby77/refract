import QtQuick

DeviceView {
    id: v

    readonly property var cpu: Monitor.cpu
    readonly property var info: Monitor.staticInfo
    readonly property color tint: Theme.deviceColor("blue")
    readonly property int cores: (cpu.per_core || []).length

    title: "CPU"
    subtitle: info.cpu_name || ""

    accessories: [
        PillSegmented {
            model: [{ key: "overall", title: "Overall" }, { key: "cores", title: "Logical Processors" }]
            current: Prefs.cpuPerCore ? "cores" : "overall"
            onActivated: key => Prefs.cpuPerCore = key === "cores"
        }
    ]

    GraphCard {
        visible: !Prefs.cpuPerCore
        width: parent.width
        height: v.graphHeight
        title: "Utilization"
        trailing: "100%"
        series: Monitor.series("cpu")
        series2: Prefs.showKernelTime ? Monitor.series("cpu.kernel") : null
        color: v.tint
        color2: Theme.mix(v.tint, Theme.label, 0.4)
        legend1: Prefs.showKernelTime ? "Total" : ""
        legend2: Prefs.showKernelTime ? "Kernel" : ""
    }

    Card {
        visible: Prefs.cpuPerCore
        width: parent.width
        height: v.graphHeight + 60
        padding: 14

        // 32 live graphs are only worth their cost while they're on screen.
        Loader {
            anchors.fill: parent
            active: Prefs.cpuPerCore
            sourceComponent: coreGridComponent
        }
    }

    Component {
        id: coreGridComponent

        Grid {
            id: coreGrid
            spacing: 8
            // Cells roughly as wide as they are tall, preferring a column count
            // that divides the core count so the rows come out even.
            columns: {
                const n = Math.max(1, v.cores)
                const ideal = Math.sqrt(n * width / Math.max(height, 1))
                let divisor = 1
                for (let c = 1; c <= n; ++c)
                    if (n % c === 0 && Math.abs(c - ideal) < Math.abs(divisor - ideal)) divisor = c
                return Math.abs(divisor - ideal) <= ideal * 0.35 ? divisor : Math.max(1, Math.round(ideal))
            }
            readonly property int rowCount: Math.ceil(v.cores / Math.max(columns, 1))
            readonly property real cellW: (width - (columns - 1) * spacing) / Math.max(columns, 1)
            readonly property real cellH: (height - (rowCount - 1) * spacing) / Math.max(rowCount, 1)

            Repeater {
                model: v.cores
                Rectangle {
                    id: coreCell
                    required property int index
                    width: coreGrid.cellW
                    height: coreGrid.cellH
                    radius: 10
                    color: Theme.alpha(v.tint, Theme.dark ? 0.07 : 0.06)
                    border.width: 1
                    border.color: Theme.alpha(v.tint, 0.22)
                    clip: true
                    Graph {
                        anchors.fill: parent
                        anchors.topMargin: 16
                        series: Monitor.series("cpu.core." + coreCell.index)
                        color: v.tint
                        lineWidth: 1.4
                        fillOpacity: 0.45
                        showGrid: false
                        interactive: false
                    }
                    Text {
                        x: 8; y: 5
                        text: "CPU " + coreCell.index
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        color: Theme.secondaryLabel
                    }
                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        y: 5
                        text: Fmt.percent((v.cpu.per_core || [])[coreCell.index])
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        font.features: Theme.tabular
                        color: Theme.label
                    }
                }
            }
        }
    }

    TileGrid {
        tiles: {
            const t = [
                { caption: "Utilization", value: Fmt.num(v.cpu.usage), unit: "%", accent: v.tint },
                { caption: "Speed", text: Fmt.freq(v.cpu.freq_mhz) },
                { caption: "Processes", text: Fmt.num(v.cpu.processes) },
                { caption: "Threads", text: Fmt.num(v.cpu.threads) },
                { caption: "Handles", text: Fmt.num(v.cpu.handles) },
                { caption: "Up Time", text: Fmt.duration(v.cpu.uptime_s) },
                { caption: "Temperature", text: Fmt.temp(v.cpu.temperature_c) }
            ]
            if (Fmt.isNum(v.cpu.power_w))
                t.push({ caption: "Power Draw", text: Fmt.watts(v.cpu.power_w) })
            return t
        }
    }

    InfoCard {
        width: parent.width
        title: "Processor"
        rows: {
            const c = v.info.cache || {}
            const l1 = (c.L1d || 0) + (c.L1i || 0)
            return [
                ["Base speed", Fmt.freq(v.info.base_mhz)],
                ["Maximum speed", Fmt.freq(v.info.max_mhz)],
                ["Sockets", v.info.sockets],
                ["Cores", v.info.cores],
                ["Logical processors", v.info.logical],
                ["Virtualization", v.info.virtualization ? v.info.virtualization + " (enabled)" : "Unsupported"],
                ["Virtual machine", v.info.is_vm === undefined ? "" : (v.info.is_vm ? "Yes" : "No")],
                ["L1 cache", l1 ? Fmt.bytes(l1, 1) : ""],
                ["L2 cache", c.L2 ? Fmt.bytes(c.L2, 1) : ""],
                ["L3 cache", c.L3 ? Fmt.bytes(c.L3, 1) : ""],
                ["Scaling driver", v.info.cpu_driver],
                ["Governor", v.cpu.governor || v.info.governor],
                ["Energy preference", v.info.energy_preference]
            ]
        }
    }
}
