import QtQuick
import QtQuick.Controls.Basic

// Live details for a process (or the main process of an app).
Sheet {
    id: sheet

    property var row: ({})                 // a ProcessModel row
    property var details: ({})
    signal quitRequested(var row)

    // follow the live row: an app's main process can change while this is open
    readonly property int pid: live.pid || 0

    function refresh() {
        if (pid > 0) details = Monitor.processDetails(pid)
    }

    title: row.name || ""
    subtitle: row.kind === "app" ? (row.count || 0) + " processes · main PID " + pid : "PID " + pid
    preferredWidth: 640
    preferredHeight: 700

    onOpened: refresh()
    onPidChanged: if (opened) refresh()
    Timer { interval: Monitor.interval; repeat: true; running: sheet.opened; onTriggered: sheet.refresh() }

    // live values follow the table row with the same key
    readonly property var live: {
        Monitor.cpu   // re-evaluate every sample
        const r = Monitor.processes.rowOf(row.key || "")
        return r >= 0 ? Monitor.processes.get(r) : row
    }

    footer: [
        PillButton { text: "Copy Command"; tint: Theme.graphite; onClicked: Monitor.copy(sheet.details.cmdline || "") },
        PillButton { text: IsWindows ? "End Process" : "Quit"; tint: Theme.red; onClicked: { sheet.quitRequested(sheet.live); sheet.close() } },
        PillButton { text: "Done"; prominent: true; onClicked: sheet.close() }
    ]

    Flickable {
        anchors.fill: parent
        contentHeight: col.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: GlassScrollBar {}

        Column {
            id: col
            width: parent.width
            spacing: 16

            Row {
                width: parent.width
                spacing: 10
                Repeater {
                    model: [
                        { caption: "CPU", text: Fmt.percent(sheet.live.cpu, 1), color: Theme.deviceColor("blue") },
                        { caption: "Memory", text: Fmt.bytes(sheet.live.memory, 1), color: Theme.deviceColor("purple") },
                        { caption: "Disk", text: Fmt.rate(sheet.live.disk, 1), color: Theme.deviceColor("green") },
                        { caption: "GPU", text: Fmt.isNum(sheet.live.gpu) ? Fmt.percent(sheet.live.gpu, 1) : Fmt.dash, color: Theme.deviceColor("pink") }
                    ]
                    Rectangle {
                        required property var modelData
                        width: (col.width - 30) / 4
                        height: 70
                        radius: 16
                        color: Theme.alpha(modelData.color, Theme.dark ? 0.16 : 0.12)
                        Column {
                            anchors.left: parent.left
                            anchors.leftMargin: 14
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2
                            Text { text: modelData.caption; font.pixelSize: 12; font.weight: Font.DemiBold; color: Theme.secondaryLabel }
                            Text {
                                text: modelData.text
                                font.family: Theme.displayFamily
                                font.pixelSize: 21
                                font.weight: Font.DemiBold
                                font.features: Theme.tabular
                                color: Theme.label
                            }
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: grid.implicitHeight + 28
                radius: 16
                color: Theme.dark ? Qt.rgba(1, 1, 1, 0.06) : Qt.rgba(1, 1, 1, 0.7)
                border.width: 1
                border.color: Theme.separator
                Grid {
                    id: grid
                    x: 16; y: 14
                    width: parent.width - 32
                    columns: 2
                    columnSpacing: 16
                    rowSpacing: 9
                    Repeater {
                        model: {
                            const d = sheet.details
                            const rows = [
                                ["State", d.state], ["User", d.user], ["Parent PID", d.ppid],
                                ["Threads", d.threads], [IsWindows ? "Priority" : "Nice", d.nice],
                                ["Started", Fmt.dateTime(d.start_time)],
                                ["Resident memory", Fmt.bytes(d.memory_rss, 1)],
                                ["Shared memory", Fmt.bytes(d.memory_shared, 1)],
                                ["Swapped", Fmt.bytes(d.memory_swap, 1)],
                                ["Open files", d.open_files],
                                ["Executable", d.exe], ["Working directory", d.cwd],
                                ["Control group", d.cgroup]
                            ]
                            const flat = []
                            for (const r of rows) flat.push(r[0], r[1] === null || r[1] === undefined || r[1] === "" ? Fmt.dash : String(r[1]))
                            return flat
                        }
                        Text {
                            required property var modelData
                            required property int index
                            width: index % 2 === 0 ? 140 : grid.width - 156
                            text: modelData
                            horizontalAlignment: index % 2 === 0 ? Text.AlignRight : Text.AlignLeft
                            font.pixelSize: 13
                            font.weight: index % 2 === 0 ? Font.Medium : Font.DemiBold
                            font.features: Theme.tabular
                            color: index % 2 === 0 ? Theme.secondaryLabel : Theme.label
                            elide: Text.ElideMiddle
                        }
                    }
                }
            }

            Text { text: "Command line"; font.pixelSize: 12; font.weight: Font.Bold; color: Theme.secondaryLabel }
            Rectangle {
                width: parent.width
                height: cmd.implicitHeight + 24
                radius: 14
                color: Theme.dark ? Qt.rgba(0, 0, 0, 0.25) : Qt.rgba(0, 0, 0, 0.05)
                TextEdit {
                    id: cmd
                    x: 12; y: 12
                    width: parent.width - 24
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.WrapAnywhere
                    text: sheet.details.cmdline || Fmt.dash
                    font.family: "monospace"
                    font.pixelSize: 12
                    color: Theme.label
                    selectionColor: Theme.alpha(Theme.accent, 0.5)
                }
            }
        }
    }
}
