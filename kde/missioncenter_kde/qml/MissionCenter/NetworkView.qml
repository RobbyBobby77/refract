import QtQuick

DeviceView {
    id: v

    required property string devId
    readonly property var interfaces: Monitor.network
    readonly property var net: interfaces.find(n => n.id === devId) || ({})
    readonly property color tint: Theme.deviceColor("orange")
    readonly property bool wifi: net.kind === "wifi"

    title: net.name || devId
    subtitle: net.device_name || devId

    accessories: [
        PillButton {
            text: "Network Settings…"
            iconName: "configure"
            onClicked: Monitor.launch("systemsettings", ["kcm_networkmanagement"])
        }
    ]

    GraphCard {
        width: parent.width
        height: v.graphHeight
        title: "Throughput"
        series: Monitor.series("net." + v.devId + ".rx")
        series2: Monitor.series("net." + v.devId + ".tx")
        color: v.tint
        color2: Theme.deviceColor("pink")
        maxValue: 0
        minScale: 16 * 1024
        legend1: "Receive"
        legend2: "Send"
        format: function (b) { return Fmt.netRate(b, 1) }
    }

    TileGrid {
        tiles: {
            const t = [
                { caption: "Receive", text: Fmt.netRate(v.net.rx_bps, 1), accent: v.tint },
                { caption: "Send", text: Fmt.netRate(v.net.tx_bps, 1), accent: Theme.deviceColor("pink") },
                { caption: "Total Received", text: Fmt.bytes(v.net.rx_total, 1) },
                { caption: "Total Sent", text: Fmt.bytes(v.net.tx_total, 1) }
            ]
            if (v.wifi)
                t.push({ caption: "Signal", value: Fmt.num(v.net.signal_percent), unit: "%", footnote: v.net.ssid || "" })
            else
                t.push({ caption: "Link Speed", text: Fmt.isNum(v.net.link_speed_mbps) ? Fmt.num(v.net.link_speed_mbps) + " Mbps" : Fmt.dash })
            return t
        }
    }

    InfoCard {
        width: parent.width
        title: "Connection"
        rows: {
            const n = v.net
            const r = [
                ["Interface", n.id],
                ["Connection type", n.name],
                ["Status", n.up ? "Connected" : "Disconnected"]
            ]
            if (v.wifi) {
                r.push(["Network (SSID)", n.ssid])
                r.push(["Signal strength", Fmt.isNum(n.signal_percent) ? n.signal_percent + "%" : ""])
                const f = n.frequency_mhz
                r.push(["Frequency", Fmt.isNum(f) ? Fmt.num(f / 1000, 2) + " GHz (" + (f >= 5925 ? "6" : f >= 5000 ? "5" : "2.4") + " GHz band)" : ""])
                r.push(["Max bitrate", Fmt.isNum(n.bitrate_mbps) ? n.bitrate_mbps + " Mbps" : ""])
            } else {
                r.push(["Link speed", Fmt.isNum(n.link_speed_mbps) ? n.link_speed_mbps + " Mbps" : ""])
            }
            r.push(["Hardware address", n.mac])
            r.push(["IPv4 address", (n.ipv4 || []).join(", ")])
            r.push(["IPv6 address", (n.ipv6 || [])[0] || ""])
            r.push(["Driver", n.driver])
            r.push(["Adapter", n.device_name])
            return r
        }
    }
}
