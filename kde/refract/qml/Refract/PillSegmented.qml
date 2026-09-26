import QtQuick

// Content-area segmented control (the regular macOS kind): a recessed track
// with a raised thumb that springs to the selected segment.
Rectangle {
    id: seg

    property var model: []                 // [{ key, title }]
    property string current: ""
    signal activated(string key)

    readonly property int currentIndex: {
        for (let i = 0; i < model.length; ++i)
            if (model[i].key === current) return i
        return 0
    }

    implicitHeight: 30
    implicitWidth: row.implicitWidth + 6
    radius: height / 2
    color: Theme.fill

    Rectangle {
        id: thumb
        readonly property Item target: rep.count > seg.currentIndex ? rep.itemAt(seg.currentIndex) : null
        y: 3
        height: seg.height - 6
        x: target ? target.x + 3 : 3
        width: target ? target.width : 0
        radius: height / 2
        color: Theme.dark ? Qt.rgba(1, 1, 1, 0.24) : "#FFFFFF"
        border.width: Theme.dark ? 0 : 0.5
        border.color: Qt.rgba(0, 0, 0, 0.06)
        Behavior on x { SpringAnimation { spring: 3.5; damping: 0.32; epsilon: 0.25 } }
        Behavior on width { SpringAnimation { spring: 3.5; damping: 0.32; epsilon: 0.25 } }
    }

    Row {
        id: row
        x: 3
        anchors.verticalCenter: parent.verticalCenter
        Repeater {
            id: rep
            model: seg.model
            Item {
                id: cell
                required property var modelData
                required property int index
                width: label.implicitWidth + 28
                height: seg.height - 6
                Text {
                    id: label
                    anchors.centerIn: parent
                    text: cell.modelData.title
                    font.pixelSize: 13
                    font.weight: cell.index === seg.currentIndex ? Font.DemiBold : Font.Medium
                    color: Theme.label
                }
                TapHandler { onTapped: seg.activated(cell.modelData.key) }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
            }
        }
    }
}
