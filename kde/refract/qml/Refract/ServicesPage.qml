import QtQuick
import QtQuick.Controls.Basic

// systemd services of the system or the user session.
Item {
    id: page

    property var actions: null
    readonly property var model: Monitor.services
    readonly property var stats: model.stats

    readonly property var columns: {
        const w = table.width
        const cols = [{ key: "name", title: "Name", width: w > 1000 ? 300 : 240, align: "left" }]
        cols.push({ key: "description", title: "Description", width: 0 })
        cols.push({ key: "activeState", title: "Status", width: 118, align: "left" })
        if (w > 860) cols.push({ key: "enabledState", title: "Startup", width: 104, align: "left" })
        cols.push({ key: "pid", title: "PID", width: 78 })
        cols.push({ key: "memory", title: "Memory", width: 104 })
        return cols
    }

    // "app-geoclue\x2ddemo@autostart.service" -> "app-geoclue-demo@autostart"
    function displayName(unit) {
        return unit.replace(/\.service$/, "").replace(/\\x2d/g, "-")
    }

    function statusText(active, sub) {
        if (active === "active") return sub === "running" ? "Running" : sub === "exited" ? "Exited" : sub.charAt(0).toUpperCase() + sub.slice(1)
        if (active === "failed") return "Failed"
        if (active === "activating") return "Starting"
        if (active === "deactivating") return "Stopping"
        return "Stopped"
    }
    function statusColor(active, sub) {
        if (active === "active") return sub === "running" ? Theme.green : Theme.teal
        if (active === "failed") return Theme.red
        if (active === "activating" || active === "deactivating") return Theme.yellow
        return Theme.graphite
    }
    function startupText(s) {
        switch (s) {
        case "enabled": case "enabled-runtime": return IsWindows ? "Automatic" : "Enabled"
        case "manual": return "Manual"
        case "disabled": return "Disabled"
        case "static": return "Static"
        case "masked": case "masked-runtime": return "Masked"
        case "generated": case "transient": return "Automatic"
        case "indirect": return "Indirect"
        case "alias": return "Alias"
        }
        return s || ""
    }

    Row {
        id: titleRow
        x: 22
        y: 66
        spacing: 14
        Text {
            id: titleText
            text: "Services"
            font.family: Theme.displayFamily
            font.pixelSize: 30
            font.weight: Font.Bold
            color: Theme.label
        }
        Text {
            anchors.baseline: titleText.baseline
            text: page.model.loaded
                  ? Fmt.num(page.stats.total) + " services · " + Fmt.num(page.stats.running) + " running"
                    + (page.stats.failed > 0 ? " · " : "")
                  : "Loading…"
            font.pixelSize: 14
            font.weight: Font.Medium
            font.features: Theme.tabular
            color: Theme.secondaryLabel
        }
        Text {
            anchors.baseline: titleText.baseline
            visible: page.model.loaded && page.stats.failed > 0
            text: Fmt.num(page.stats.failed) + " failed"
            font.pixelSize: 14
            font.weight: Font.DemiBold
            color: Theme.red
        }
    }
    PillSegmented {
        visible: !IsWindows
        anchors.right: parent.right
        anchors.rightMargin: 22
        anchors.verticalCenter: titleRow.verticalCenter
        model: [{ key: "system", title: "System" }, { key: "user", title: "User" }]
        current: Prefs.showUserServices ? "user" : "system"
        onActivated: key => Prefs.showUserServices = key === "user"
    }

    Card {
        anchors.fill: parent
        anchors.topMargin: 128
        anchors.leftMargin: 18
        anchors.rightMargin: 18
        anchors.bottomMargin: 18
        padding: 8

        TableHeader {
            id: tableHeader
            width: parent.width
            height: 40
            columns: page.columns
            sortColumn: page.model.sortColumn
            sortAscending: page.model.sortAscending
            onSortRequested: key => page.model.sortBy(key)
        }

        ListView {
            id: table
            anchors.top: tableHeader.bottom
            anchors.bottom: parent.bottom
            width: parent.width
            clip: true
            model: page.model
            reuseItems: true
            cacheBuffer: 400
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: GlassScrollBar {}
            footer: Item { height: 70 }

            delegate: Item {
                id: row
                required property int index
                required property string key
                required property string name
                required property string description
                required property string activeState
                required property string subState
                required property string enabledState
                required property var pid
                required property var memory
                readonly property bool selected: key === page.model.selectedKey

                width: table.width
                height: 34

                Rectangle {
                    anchors.fill: parent
                    anchors.leftMargin: 2
                    anchors.rightMargin: 2
                    radius: 9
                    color: row.selected ? Theme.accent
                         : hover.hovered ? Theme.hoverFill
                         : (row.index % 2 ? (Theme.dark ? Qt.rgba(1, 1, 1, 0.025) : Qt.rgba(0, 0, 0, 0.022)) : "transparent")
                }

                Row {
                    anchors.fill: parent
                    Repeater {
                        model: page.columns.length
                        Item {
                            id: cell
                            required property int index
                            readonly property var col: page.columns[index] || ({})
                            width: tableHeader.widthOf(index)
                            height: row.height

                            Row {
                                visible: cell.col.key === "activeState"
                                anchors.verticalCenter: parent.verticalCenter
                                x: 12
                                spacing: 7
                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 8; height: 8; radius: 4
                                    color: page.statusColor(row.activeState, row.subState)
                                    border.width: row.selected ? 1 : 0
                                    border.color: "white"
                                }
                                Text {
                                    text: page.statusText(row.activeState, row.subState)
                                    font.pixelSize: 13
                                    color: row.selected ? "white" : Theme.label
                                }
                            }

                            Text {
                                visible: cell.col.key !== "activeState"
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                horizontalAlignment: cell.col.align === "left" || cell.col.key === "description" ? Text.AlignLeft : Text.AlignRight
                                elide: Text.ElideRight
                                font.pixelSize: 13
                                font.weight: cell.col.key === "name" ? Font.Medium : Font.Normal
                                font.features: cell.col.key === "pid" || cell.col.key === "memory" ? Theme.tabular : ({})
                                color: row.selected ? "white"
                                     : cell.col.key === "name" || cell.col.key === "memory" ? Theme.label : Theme.secondaryLabel
                                text: {
                                    switch (cell.col.key) {
                                    case "name": return page.displayName(row.name)
                                    case "description": return row.description
                                    case "enabledState": return page.startupText(row.enabledState)
                                    case "pid": return Fmt.isNum(row.pid) && row.pid > 0 ? String(row.pid) : ""
                                    case "memory": return Fmt.isNum(row.memory) ? Fmt.bytes(row.memory, 1) : ""
                                    }
                                    return ""
                                }
                            }
                        }
                    }
                }

                HoverHandler { id: hover }
                TapHandler {
                    onTapped: page.model.select(row.key)
                    onDoubleTapped: if (page.actions) page.actions.serviceDetails(page.model.get(row.index))
                }
                TapHandler {
                    acceptedButtons: Qt.RightButton
                    onTapped: (eventPoint) => {
                        page.model.select(row.key)
                        const p = row.mapToItem(null, eventPoint.position.x, eventPoint.position.y)
                        if (page.actions) page.actions.serviceMenu(page.model.get(row.index), p.x, p.y)
                    }
                }
            }
        }

        Text {
            anchors.centerIn: table
            visible: !page.model.loaded
            text: IsWindows ? "Loading Windows services…" : "Asking systemd…"
            font.pixelSize: 14
            color: Theme.secondaryLabel
        }
    }
}
