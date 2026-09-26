import QtQuick
import QtQuick.Controls.Basic

// Preferences, grouped like System Settings on macOS.
Sheet {
    id: sheet

    title: "Settings"
    subtitle: "Refract " + AppVersion
    signal aboutRequested()
    preferredWidth: 600
    preferredHeight: 700

    footer: [
        PillButton { text: "About Refract"; tint: Theme.graphite; onClicked: sheet.aboutRequested() },
        PillButton { text: "Done"; prominent: true; onClicked: sheet.close() }
    ]

    component Group: Rectangle {
        default property alias rows: groupCol.data
        property string heading: ""
        width: parent ? parent.width : 0
        height: groupCol.implicitHeight + (heading !== "" ? 24 : 0)
        color: "transparent"
        Text {
            visible: parent.heading !== ""
            x: 4
            text: parent.heading
            font.pixelSize: 12
            font.weight: Font.Bold
            color: Theme.secondaryLabel
        }
        Rectangle {
            y: parent.heading !== "" ? 22 : 0
            width: parent.width
            height: groupCol.implicitHeight
            radius: 14
            color: Theme.dark ? Qt.rgba(1, 1, 1, 0.06) : Qt.rgba(1, 1, 1, 0.7)
            border.width: 1
            border.color: Theme.separator
            Column {
                id: groupCol
                width: parent.width
            }
        }
    }

    component SettingRow: Item {
        id: row
        property string label: ""
        property string hint: ""
        property bool last: false
        default property alias control: slot.data
        width: parent ? parent.width : 0
        height: hint !== "" ? 58 : 46
        Column {
            anchors.left: parent.left
            anchors.leftMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: slot.left
            anchors.rightMargin: 12
            spacing: 2
            Text { text: row.label; font.pixelSize: 13; font.weight: Font.Medium; color: Theme.label }
            Text { visible: row.hint !== ""; text: row.hint; font.pixelSize: 12; color: Theme.secondaryLabel; width: parent.width; elide: Text.ElideRight }
        }
        Item {
            id: slot
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: childrenRect.width
            height: childrenRect.height
        }
        Rectangle {
            visible: !row.last
            anchors.bottom: parent.bottom
            x: 14
            width: parent.width - 14
            height: 1
            color: Theme.separator
        }
    }

    Flickable {
        anchors.fill: parent
        contentHeight: settingsCol.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: GlassScrollBar {}

        Column {
            id: settingsCol
            width: parent.width
            spacing: 18

            Group {
                heading: "Appearance"
                SettingRow {
                    label: "Appearance"
                    PillSegmented {
                        model: [{ key: "0", title: "Auto" }, { key: "1", title: "Light" }, { key: "2", title: "Dark" }]
                        current: String(Prefs.themeMode)
                        onActivated: key => Prefs.themeMode = parseInt(key)
                    }
                }
                SettingRow {
                    label: "Accent colour"
                    Row {
                        spacing: 8
                        Repeater {
                            model: ["multicolor", "system", "blue", "purple", "pink", "red", "orange", "yellow", "green", "graphite"]
                            Rectangle {
                                id: swatch
                                required property string modelData
                                width: 20; height: 20; radius: 10
                                gradient: modelData === "multicolor" ? multi : null
                                color: Theme.named(modelData)
                                border.width: Prefs.accent === modelData ? 2.5 : 0
                                border.color: Theme.label
                                Gradient {
                                    id: multi
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0; color: Theme.red }
                                    GradientStop { position: 0.35; color: Theme.yellow }
                                    GradientStop { position: 0.65; color: Theme.green }
                                    GradientStop { position: 1; color: Theme.blue }
                                }
                                Text {
                                    visible: swatch.modelData === "system"
                                    anchors.centerIn: parent
                                    text: "K"
                                    font.pixelSize: 11
                                    font.weight: Font.Bold
                                    color: "white"
                                }
                                ToolTipBubble {
                                    text: swatch.modelData === "multicolor" ? "Multicolour" : swatch.modelData === "system" ? "KDE accent colour" : ""
                                    shown: swatchHover.hovered
                                }
                                TapHandler { onTapped: Prefs.accent = swatch.modelData }
                                HoverHandler { id: swatchHover }
                                HoverHandler { cursorShape: Qt.PointingHandCursor }
                            }
                        }
                    }
                }
                SettingRow {
                    label: "Liquid Glass"
                    hint: "Clear shows more of what's behind; Tinted adds contrast"
                    PillSegmented {
                        model: [{ key: "0", title: "Clear" }, { key: "1", title: "Tinted" }]
                        current: String(Prefs.glassStyle)
                        onActivated: key => Prefs.glassStyle = parseInt(key)
                    }
                }
                SettingRow {
                    label: "Window background"
                    hint: WindowEffects.available ? "Glass shows your desktop through the window" : "Glass needs KWin's blur effect"
                    PillSegmented {
                        model: [{ key: "0", title: "Glass" }, { key: "1", title: "Wallpaper" }, { key: "2", title: "Solid" }]
                        current: String(Prefs.backdropMode)
                        onActivated: key => Prefs.backdropMode = parseInt(key)
                    }
                }
                SettingRow {
                    label: "Reduce transparency"
                    Toggle { checked: Prefs.reduceTransparency; onToggled: c => Prefs.reduceTransparency = c }
                }
                SettingRow {
                    label: "Window buttons"
                    PillSegmented {
                        model: [{ key: "left", title: "Left" }, { key: "right", title: "Right" }]
                        current: Prefs.windowButtonsRight ? "right" : "left"
                        onActivated: key => Prefs.windowButtonsRight = key === "right"
                    }
                }
                SettingRow {
                    label: "Use KDE window decorations"
                    hint: "Takes effect after restarting Refract"
                    last: true
                    Toggle { checked: Prefs.nativeDecorations; onToggled: c => Prefs.nativeDecorations = c }
                }
            }

            Group {
                heading: "Performance"
                SettingRow {
                    label: "Update interval"
                    PillSegmented {
                        model: [{ key: "500", title: "0.5 s" }, { key: "1000", title: "1 s" }, { key: "2000", title: "2 s" }, { key: "4000", title: "4 s" }]
                        current: String(Prefs.updateInterval)
                        onActivated: key => Prefs.updateInterval = parseInt(key)
                    }
                }
                SettingRow {
                    label: "Process list updates"
                    hint: "How often the Apps table refreshes; slower uses less CPU"
                    PillSegmented {
                        model: [{ key: "0", title: "Live" }, { key: "2000", title: "2 s" }, { key: "5000", title: "5 s" }]
                        current: String(Prefs.processInterval)
                        onActivated: key => Prefs.processInterval = parseInt(key)
                    }
                }
                SettingRow {
                    label: "Graph history"
                    PillSegmented {
                        model: [{ key: "30", title: "30" }, { key: "60", title: "60" }, { key: "120", title: "120" }, { key: "240", title: "240" }]
                        current: String(Prefs.graphPoints)
                        onActivated: key => Prefs.graphPoints = parseInt(key)
                    }
                }
                SettingRow {
                    label: "Smooth graph lines"
                    Toggle { checked: Prefs.smoothGraphs; onToggled: c => Prefs.smoothGraphs = c }
                }
                SettingRow {
                    label: "Show kernel time in CPU graph"
                    Toggle { checked: Prefs.showKernelTime; onToggled: c => Prefs.showKernelTime = c }
                }
                SettingRow {
                    label: "Data engine"
                    hint: Monitor.staticInfo.engine === "magpie" ? "Mission Center's own collector, via its IPC bridge" : "Build the native parts (build-native.sh) to use magpie"
                    last: true
                    Text {
                        text: Monitor.staticInfo.engine === "magpie" ? "magpie" : "Built-in"
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        color: Theme.secondaryLabel
                    }
                }
            }

            Group {
                heading: "Units"
                SettingRow {
                    label: "Data sizes"
                    PillSegmented {
                        model: [{ key: "1", title: "Decimal (GB)" }, { key: "0", title: "Binary (GiB)" }]
                        current: Prefs.decimalUnits ? "1" : "0"
                        onActivated: key => Prefs.decimalUnits = key === "1"
                    }
                }
                SettingRow {
                    label: "Network speed"
                    PillSegmented {
                        model: [{ key: "0", title: "Bytes/s" }, { key: "1", title: "Bits/s" }]
                        current: Prefs.networkBits ? "1" : "0"
                        onActivated: key => Prefs.networkBits = key === "1"
                    }
                }
                SettingRow {
                    label: "Temperature"
                    last: true
                    PillSegmented {
                        model: [{ key: "0", title: "°C" }, { key: "1", title: "°F" }]
                        current: Prefs.fahrenheit ? "1" : "0"
                        onActivated: key => Prefs.fahrenheit = key === "1"
                    }
                }
            }

            Group {
                heading: "Apps & Services"
                SettingRow {
                    label: "Show processes as a tree"
                    Toggle { checked: Prefs.processTree; onToggled: c => Prefs.processTree = c }
                }
                SettingRow {
                    label: "Show user services"
                    hint: "List services of your user session instead of the system"
                    last: true
                    Toggle { checked: Prefs.showUserServices; onToggled: c => Prefs.showUserServices = c }
                }
            }

            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: "Refract is based on Mission Center by the Mission Center developers · GPL-3.0"
                font.pixelSize: 11
                color: Theme.tertiaryLabel
            }
        }
    }
}
