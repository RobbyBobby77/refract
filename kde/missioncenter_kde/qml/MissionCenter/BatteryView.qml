import QtQuick

DeviceView {
    id: v

    required property string devId
    readonly property var batteries: Monitor.batteries
    readonly property var bat: batteries.find(b => b.id === devId) || ({})
    readonly property color tint: (bat.percent || 0) <= 20 && bat.state === "Discharging" ? Theme.red : Theme.deviceColor("mint")

    title: "Battery"
    subtitle: [bat.manufacturer, bat.model].filter(x => !!x).join(" ")

    accessories: [
        PillButton {
            text: "Power Settings…"
            iconName: "configure"
            onClicked: Monitor.launch("systemsettings", ["kcm_powerdevilprofilesconfig"])
        }
    ]

    Row {
        width: parent.width
        spacing: 14
        GraphCard {
            width: (parent.width - parent.spacing) * 0.6
            height: v.graphHeight
            title: "Charge"
            trailing: "100%"
            series: Monitor.series("bat." + v.devId + ".percent")
            color: v.tint
        }
        GraphCard {
            width: (parent.width - parent.spacing) * 0.4
            height: v.graphHeight
            title: v.bat.state === "Charging" ? "Charge Rate" : "Power Draw"
            series: Monitor.series("bat." + v.devId + ".power")
            color: Theme.deviceColor("yellow")
            maxValue: 0
            minScale: 10
            format: function (w) { return Fmt.watts(w) }
        }
    }

    TileGrid {
        tiles: [
            { caption: "Charge", value: Fmt.num(v.bat.percent), unit: "%", accent: v.tint },
            { caption: "State", text: v.bat.state || Fmt.dash, footnote: v.bat.ac_online ? "Power adapter connected" : "On battery" },
            { caption: v.bat.state === "Charging" ? "Charge Rate" : "Power Draw", text: Fmt.watts(v.bat.power_w) },
            { caption: v.bat.state === "Charging" ? "Until Full" : "Remaining", text: Fmt.shortDuration(v.bat.time_remaining_s) },
            { caption: "Health", value: Fmt.num(v.bat.health_percent), unit: Fmt.isNum(v.bat.health_percent) ? "%" : "" },
            { caption: "Cycle Count", text: Fmt.num(v.bat.cycles) }
        ]
    }

    InfoCard {
        width: parent.width
        title: "Battery Information"
        rows: [
            ["Manufacturer", v.bat.manufacturer],
            ["Model", v.bat.model],
            ["Technology", v.bat.technology],
            ["Energy", Fmt.isNum(v.bat.energy_now_wh) ? Fmt.num(v.bat.energy_now_wh, 1) + " Wh" : ""],
            ["Full charge capacity", Fmt.isNum(v.bat.energy_full_wh) ? Fmt.num(v.bat.energy_full_wh, 1) + " Wh" : ""],
            ["Design capacity", Fmt.isNum(v.bat.energy_design_wh) ? Fmt.num(v.bat.energy_design_wh, 1) + " Wh" : ""],
            ["Voltage", Fmt.isNum(v.bat.voltage_v) ? Fmt.num(v.bat.voltage_v, 2) + " V" : ""]
        ]
    }
}
