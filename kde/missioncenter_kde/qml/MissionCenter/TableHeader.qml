import QtQuick

// Sortable column header. Numeric columns can show a live total above their
// title, the way Mission Center (and Task Manager) do.
Item {
    id: header

    property var columns: []               // [{ key, title, width (0 = fill), total?, align? }]
    property string sortColumn: ""
    property bool sortAscending: true
    signal sortRequested(string key)

    readonly property real fixedWidth: columns.reduce((a, c) => a + (c.width > 0 ? c.width : 0), 0)
    readonly property int fillCount: Math.max(1, columns.filter(c => !(c.width > 0)).length)
    function widthOf(i) {
        const c = columns[i]
        if (!c) return 0
        return c.width > 0 ? c.width : Math.max(120, (width - fixedWidth) / fillCount)
    }

    height: 50

    Row {
        anchors.fill: parent
        Repeater {
            model: header.columns.length
            Item {
                id: cell
                required property int index
                readonly property var col: header.columns[index] || ({})
                readonly property bool sorted: col.key === header.sortColumn
                readonly property bool alignRight: col.align === "right" || (col.width > 0 && col.key !== "user" && col.align !== "left")
                width: header.widthOf(index)
                height: header.height

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 4
                    radius: 9
                    color: hover.hovered ? Theme.hoverFill : "transparent"
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: cell.alignRight ? undefined : parent.left
                    anchors.right: cell.alignRight ? parent.right : undefined
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 1
                    Text {
                        anchors.right: cell.alignRight ? parent.right : undefined
                        visible: cell.col.total !== undefined
                        text: cell.col.total || ""
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        font.features: Theme.tabular
                        color: cell.col.color || Theme.label
                    }
                    Row {
                        anchors.right: cell.alignRight ? parent.right : undefined
                        spacing: 4
                        Text {
                            text: cell.col.title || ""
                            font.pixelSize: 12
                            font.weight: cell.sorted ? Font.Bold : Font.DemiBold
                            color: cell.sorted ? Theme.label : Theme.secondaryLabel
                        }
                        Text {
                            visible: cell.sorted
                            text: header.sortAscending ? "▲" : "▼"
                            font.pixelSize: 8
                            anchors.verticalCenter: parent.verticalCenter
                            color: Theme.secondaryLabel
                        }
                    }
                }

                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: header.sortRequested(cell.col.key) }
            }
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Theme.separator
    }
}
