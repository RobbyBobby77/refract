import QtQuick

DeviceView {
    id: v

    required property string devId
    readonly property var fans: Monitor.fans
    readonly property var fan: fans.find(f => f.id === devId) || ({})
    readonly property color tint: Theme.deviceColor("cyan")

    title: (Monitor.devices.get(Monitor.devices.rowOf("fan:" + devId)).title) || "Fan"
    subtitle: fan.name || ""

    GraphCard {
        width: parent.width
        height: v.graphHeight
        title: "Fan Speed"
        series: Monitor.series("fan." + v.devId + ".rpm")
        color: v.tint
        maxValue: 0
        minScale: 1000
        format: function (r) { return Fmt.rpm(r) }
    }

    TileGrid {
        tiles: [
            { caption: "Speed", value: Fmt.num(v.fan.rpm), unit: "RPM", accent: v.tint },
            { caption: "Duty Cycle", value: Fmt.num(v.fan.pwm_percent), unit: Fmt.isNum(v.fan.pwm_percent) ? "%" : "" },
            { caption: "Temperature", text: Fmt.temp(v.fan.temperature_c) },
            { caption: "Status", text: (v.fan.rpm || 0) > 0 ? "Spinning" : "Idle" }
        ]
    }

    InfoCard {
        width: parent.width
        title: "Sensor"
        rows: [
            ["Sensor chip", v.fan.name],
            ["Label", v.fan.label],
            ["Identifier", v.fan.id]
        ]
    }
}
