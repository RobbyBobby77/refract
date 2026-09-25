import QtQuick
import QtQuick.Controls.Basic
import org.kde.kirigami as Kirigami

// Apps & processes: a live, sortable tree table.
Item {
    id: page

    property var actions: null
    readonly property var model: Monitor.processes
    readonly property real memTotal: Monitor.memory.total || 1
    readonly property var disks: Monitor.disks
    readonly property var gpus: Monitor.gpus
    readonly property real diskTotal: disks.reduce((a, d) => a + (d.read_bps || 0) + (d.write_bps || 0), 0)
    readonly property real gpuTotal: gpus.reduce((a, g) => Math.max(a, g.usage || 0), 0)

    readonly property var columns: {
        const w = table.width
        const cols = [{ key: "name", title: "Name", width: 0 }]
        cols.push({ key: "pid", title: "PID", width: 78 })
        if (w > 1050) cols.push({ key: "user", title: "User", width: 118, align: "left" })
        cols.push({ key: "cpu", title: "CPU", width: 88, total: Fmt.percent(Monitor.cpu.usage), color: Theme.deviceColor("blue") })
        cols.push({ key: "memory", title: "Memory", width: 112,
                    total: Fmt.percent((Monitor.memory.used || 0) / page.memTotal * 100), color: Theme.deviceColor("purple") })
        cols.push({ key: "disk", title: "Disk", width: 108, total: Fmt.rate(page.diskTotal, 1), color: Theme.deviceColor("green") })
        if (page.gpus.length > 0)
            cols.push({ key: "gpu", title: "GPU", width: 80, total: Fmt.percent(page.gpuTotal), color: Theme.deviceColor("pink") })
        if (w > 900 && page.gpus.length > 0)
            cols.push({ key: "gpuMemory", title: "GPU Memory", width: 112 })
        return cols
    }

    Binding { target: page.model; property: "treeMode"; value: Prefs.processTree }

    // --- header ---------------------------------------------------------
    Row {
        id: titleRow
        x: 22
        y: 66
        spacing: 14
        Text {
            id: titleText
            text: "Apps"
            font.family: Theme.displayFamily
            font.pixelSize: 30
            font.weight: Font.Bold
            color: Theme.label
        }
        Text {
            anchors.baseline: titleText.baseline
            text: page.model.appCount + " apps · " + Fmt.num(page.model.processCount) + " processes · "
                  + Fmt.num(Monitor.cpu.threads) + " threads"
            font.pixelSize: 14
            font.weight: Font.Medium
            font.features: Theme.tabular
            color: Theme.secondaryLabel
        }
    }
    PillSegmented {
        anchors.right: parent.right
        anchors.rightMargin: 22
        anchors.verticalCenter: titleRow.verticalCenter
        model: [{ key: "list", title: "List" }, { key: "tree", title: "Tree" }]
        current: Prefs.processTree ? "tree" : "list"
        onActivated: key => Prefs.processTree = key === "tree"
    }

    // --- table ------------------------------------------------------------
    Card {
        id: card
        anchors.fill: parent
        anchors.topMargin: 128
        anchors.leftMargin: 18
        anchors.rightMargin: 18
        anchors.bottomMargin: 18
        padding: 8

        TableHeader {
            id: tableHeader
            width: parent.width
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
            footer: Item { height: 70 }   // room for the floating action bar

            delegate: ProcessRow {
                width: table.width
                columns: page.columns
                header: tableHeader
                memTotal: page.memTotal
                selected: key === page.model.selectedKey
                onClicked: page.model.select(key)
                onToggle: page.model.toggleExpanded(key)
                onActivated: if (page.actions) page.actions.processDetails(page.model.get(rowIndex))
                onContextMenu: (x, y) => {
                    page.model.select(key)
                    if (page.actions) page.actions.processMenu(page.model.get(rowIndex), x, y)
                }
            }
        }

        Text {
            anchors.centerIn: table
            visible: page.model.processCount === 0
            text: "Gathering processes…"
            font.pixelSize: 14
            color: Theme.secondaryLabel
        }
    }

    component ProcessRow: Item {
        id: row

        required property int index
        required property string key
        required property string kind
        required property int depth
        required property bool expandable
        required property bool expanded
        required property string name
        required property string icon
        required property var pid
        required property var cpu
        required property var memory
        required property var disk
        required property var gpu
        required property var gpuMemory
        required property string user
        required property int count

        property var columns: []
        property TableHeader header
        property real memTotal: 1
        property bool selected: false
        readonly property int rowIndex: index
        readonly property bool isSection: kind === "section"

        signal clicked()
        signal toggle()
        signal activated()
        signal contextMenu(real x, real y)

        height: isSection ? 40 : 34

        Rectangle {
            anchors.fill: parent
            anchors.leftMargin: 2
            anchors.rightMargin: 2
            radius: 9
            visible: !row.isSection
            color: row.selected ? Theme.accent
                 : rowHover.hovered ? Theme.hoverFill
                 : (row.index % 2 ? (Theme.dark ? Qt.rgba(1, 1, 1, 0.025) : Qt.rgba(0, 0, 0, 0.022)) : "transparent")
        }

        // section header ("Apps", "Processes")
        Row {
            visible: row.isSection
            anchors.verticalCenter: parent.verticalCenter
            x: 10
            spacing: 8
            Text {
                text: "›"
                font.pixelSize: 18
                font.weight: Font.DemiBold
                color: Theme.secondaryLabel
                rotation: row.expanded ? 90 : 0
                Behavior on rotation { NumberAnimation { duration: 160 } }
            }
            Text {
                text: row.name
                font.pixelSize: 14
                font.weight: Font.Bold
                color: Theme.label
            }
            Text {
                text: row.count
                font.pixelSize: 13
                font.weight: Font.Medium
                font.features: Theme.tabular
                color: Theme.tertiaryLabel
            }
        }

        Row {
            visible: !row.isSection
            anchors.fill: parent
            Repeater {
                model: row.columns.length
                Item {
                    id: cell
                    required property int index
                    readonly property var col: row.columns[index] || ({})
                    width: row.header ? row.header.widthOf(index) : 0
                    height: row.height

                    readonly property real heat: {
                        switch (col.key) {
                        case "cpu": return Math.min(1, (row.cpu || 0) / 20)
                        case "memory": return Math.min(1, (row.memory || 0) / (row.memTotal * 0.08))
                        case "disk": return Math.min(1, (row.disk || 0) / (32 * 1024 * 1024))
                        case "gpu": return Math.min(1, (row.gpu || 0) / 40)
                        }
                        return 0
                    }
                    Rectangle {
                        visible: cell.heat > 0.01 && !row.selected
                        anchors.fill: parent
                        anchors.topMargin: 3
                        anchors.bottomMargin: 3
                        anchors.leftMargin: 3
                        anchors.rightMargin: 3
                        radius: 7
                        color: Theme.alpha(cell.col.color || Theme.accent, 0.08 + cell.heat * 0.34)
                    }

                    // name column
                    Row {
                        visible: cell.col.key === "name"
                        anchors.verticalCenter: parent.verticalCenter
                        x: 10 + row.depth * 20
                        width: parent.width - x - 8
                        spacing: 7
                        Text {
                            width: 12
                            text: row.expandable ? "›" : ""
                            font.pixelSize: 16
                            font.weight: Font.DemiBold
                            color: row.selected ? "white" : Theme.secondaryLabel
                            rotation: row.expanded ? 90 : 0
                            Behavior on rotation { NumberAnimation { duration: 160 } }
                            anchors.verticalCenter: parent.verticalCenter
                            TapHandler { onTapped: row.toggle() }
                        }
                        Kirigami.Icon {
                            width: 18; height: 18
                            anchors.verticalCenter: parent.verticalCenter
                            source: row.icon !== "" ? row.icon : Theme.executableIcon
                            fallback: Theme.executableIcon
                        }
                        Text {
                            width: parent.width - 12 - 18 - 2 * parent.spacing
                            anchors.verticalCenter: parent.verticalCenter
                            text: row.name + (row.kind === "app" && row.count > 1 ? "  (" + row.count + ")" : "")
                            font.pixelSize: 13
                            font.weight: row.kind === "app" ? Font.DemiBold : Font.Normal
                            color: row.selected ? "white" : Theme.label
                            elide: Text.ElideRight
                        }
                    }

                    Text {
                        visible: cell.col.key !== "name"
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        horizontalAlignment: cell.col.align === "left" ? Text.AlignLeft : Text.AlignRight
                        elide: Text.ElideRight
                        font.pixelSize: 13
                        font.features: cell.col.key === "user" ? ({}) : Theme.tabular
                        color: row.selected ? "white" : (cell.col.key === "pid" || cell.col.key === "user" ? Theme.secondaryLabel : Theme.label)
                        text: {
                            switch (cell.col.key) {
                            case "pid": return row.pid === null || row.pid === undefined ? "" : String(row.pid)
                            case "user": return row.user
                            case "cpu": return Fmt.percent(row.cpu, 1)
                            case "memory": return Fmt.bytes(row.memory, 1)
                            case "disk": return Fmt.rate(row.disk, 1)
                            case "gpu": return Fmt.isNum(row.gpu) ? Fmt.percent(row.gpu, 1) : ""
                            case "gpuMemory": return Fmt.isNum(row.gpuMemory) && row.gpuMemory > 0 ? Fmt.bytes(row.gpuMemory, 1) : ""
                            }
                            return ""
                        }
                    }
                }
            }
        }

        HoverHandler { id: rowHover }
        TapHandler {
            acceptedButtons: Qt.LeftButton
            onTapped: row.isSection ? row.toggle() : row.clicked()
            onDoubleTapped: if (!row.isSection) row.activated()
        }
        TapHandler {
            acceptedButtons: Qt.RightButton
            enabled: !row.isSection
            onTapped: (eventPoint) => {
                const p = row.mapToItem(null, eventPoint.position.x, eventPoint.position.y)
                row.contextMenu(p.x, p.y)
            }
        }
    }
}
