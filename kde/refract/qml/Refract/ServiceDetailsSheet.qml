import QtQuick
import QtQuick.Controls.Basic

// Service status and its journal.
Sheet {
    id: sheet

    property var row: ({})
    property string logs: ""
    property bool loadingLogs: false
    signal actionRequested(string action)

    readonly property var live: {
        Monitor.services.stats   // re-evaluate on refresh
        const r = Monitor.services.rowOf(row.key || "")
        return r >= 0 ? Monitor.services.get(r) : row
    }
    readonly property bool running: live.activeState === "active" || live.activeState === "activating"
    readonly property bool enabledUnit: live.enabledState === "enabled"

    function reloadLogs() {
        if (!row.name) return
        loadingLogs = true
        Monitor.requestLogs(row.name, !!row.user)
    }

    title: (row.name || "").replace(/\.service$/, "").replace(/\\x2d/g, "-")
    subtitle: row.description || ""
    preferredWidth: 760
    preferredHeight: 680
    onOpened: { logs = ""; reloadLogs() }

    Connections {
        target: Monitor
        function onLogsReady(unit, text) {
            if (unit === sheet.row.name) {
                sheet.logs = text
                sheet.loadingLogs = false
            }
        }
    }

    footer: [
        PillButton {
            text: sheet.enabledUnit ? "Disable" : "Enable"
            tint: Theme.graphite
            enabledState: sheet.live.enabledState === "enabled" || sheet.live.enabledState === "disabled" || (IsWindows && sheet.live.enabledState === "manual")
            onClicked: sheet.actionRequested(sheet.enabledUnit ? "disable" : "enable")
        },
        PillButton { text: "Restart"; tint: Theme.orange; onClicked: sheet.actionRequested("restart") },
        PillButton {
            text: sheet.running ? "Stop" : "Start"
            tint: sheet.running ? Theme.red : Theme.green
            onClicked: sheet.actionRequested(sheet.running ? "stop" : "start")
        },
        PillButton { text: "Done"; prominent: true; onClicked: sheet.close() }
    ]

    Column {
        anchors.fill: parent
        spacing: 14

        Row {
            id: facts
            width: parent.width
            spacing: 10
            Repeater {
                model: [
                    { caption: "Status", text: sheet.live.activeState + " (" + sheet.live.subState + ")" },
                    { caption: "Startup", text: IsWindows ? (sheet.enabledUnit ? "Automatic" : sheet.live.enabledState === "manual" ? "Manual" : "Disabled") : sheet.live.enabledState || Fmt.dash },
                    { caption: "Main PID", text: Fmt.isNum(sheet.live.pid) && sheet.live.pid > 0 ? String(sheet.live.pid) : Fmt.dash },
                    { caption: "Memory", text: Fmt.isNum(sheet.live.memory) ? Fmt.bytes(sheet.live.memory, 1) : Fmt.dash }
                ]
                Rectangle {
                    required property var modelData
                    width: (facts.width - 30) / 4
                    height: 62
                    radius: 14
                    color: Theme.dark ? Qt.rgba(1, 1, 1, 0.07) : Qt.rgba(1, 1, 1, 0.7)
                    border.width: 1
                    border.color: Theme.separator
                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3
                        Text { text: modelData.caption; font.pixelSize: 12; font.weight: Font.DemiBold; color: Theme.secondaryLabel }
                        Text {
                            width: parent.width
                            text: modelData.text
                            font.pixelSize: 15
                            font.weight: Font.DemiBold
                            font.features: Theme.tabular
                            color: Theme.label
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        Item {
            width: parent.width
            height: 22
            Text { text: "Journal"; font.pixelSize: 12; font.weight: Font.Bold; color: Theme.secondaryLabel; anchors.bottom: parent.bottom }
            PillButton {
                anchors.right: parent.right
                height: 24
                text: sheet.loadingLogs ? "Loading…" : "Refresh"
                tint: Theme.accent
                onClicked: sheet.reloadLogs()
            }
        }

        Rectangle {
            width: parent.width
            height: parent.height - facts.height - 22 - 2 * parent.spacing
            radius: 14
            color: Theme.dark ? Qt.rgba(0, 0, 0, 0.30) : Qt.rgba(0, 0, 0, 0.05)
            clip: true
            Flickable {
                id: logFlick
                anchors.fill: parent
                anchors.margins: 12
                contentHeight: logText.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: GlassScrollBar {}
                onContentHeightChanged: contentY = Math.max(0, contentHeight - height)
                TextEdit {
                    id: logText
                    width: logFlick.width
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.WrapAnywhere
                    text: sheet.logs !== "" ? sheet.logs : (sheet.loadingLogs ? "" : IsWindows ? "No recent Service Control Manager events for this service." : "No journal entries (you may need to be in the systemd-journal group).")
                    font.family: "monospace"
                    font.pixelSize: 11
                    color: Theme.label
                    selectionColor: Theme.alpha(Theme.accent, 0.5)
                }
            }
        }
    }
}
