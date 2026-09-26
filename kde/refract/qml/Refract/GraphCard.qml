import QtQuick

// A card holding a history graph with Apple-style captions around it.
Card {
    id: card

    property string title: ""
    property string trailing: ""          // e.g. "100%" or the autoscale max
    property string legend1: ""
    property string legend2: ""
    property alias graph: graph
    property alias series: graph.series
    property alias series2: graph.series2
    property alias color: graph.color
    property alias color2: graph.color2
    property alias maxValue: graph.maxValue
    property alias minScale: graph.minScale
    property alias format: graph.format

    padding: 18

    Item {
        id: header
        width: parent.width
        height: 20
        Text {
            text: card.title
            font.pixelSize: 13
            font.weight: Font.DemiBold
            color: Theme.label
        }
        Row {
            anchors.right: parent.right
            spacing: 14
            Legend { visible: card.legend1 !== ""; text: card.legend1; swatch: graph.color }
            Legend { visible: card.legend2 !== ""; text: card.legend2; swatch: graph.color2; dashed: true }
            Text {
                text: card.trailing !== "" ? card.trailing : graph.format(graph.scaleMax)
                font.pixelSize: 12
                font.weight: Font.Medium
                font.features: Theme.tabular
                color: Theme.secondaryLabel
            }
        }
    }

    Graph {
        id: graph
        anchors.top: header.bottom
        anchors.topMargin: 10
        anchors.bottom: footer.top
        anchors.bottomMargin: 8
        width: parent.width
        label1: card.legend1
        label2: card.legend2
    }

    Item {
        id: footer
        anchors.bottom: parent.bottom
        width: parent.width
        height: 14
        Text {
            text: Math.round(graph.points * Monitor.interval / 1000) + " seconds"
            font.pixelSize: 11
            font.weight: Font.Medium
            color: Theme.tertiaryLabel
        }
        Text {
            anchors.right: parent.right
            text: "0"
            font.pixelSize: 11
            font.weight: Font.Medium
            color: Theme.tertiaryLabel
        }
    }

    component Legend: Row {
        property string text
        property color swatch
        property bool dashed: false
        spacing: 6
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: 14; height: 3; radius: 1.5
            color: parent.dashed ? "transparent" : parent.swatch
            Row {
                visible: parent.parent.dashed
                spacing: 2
                Repeater { model: 3; Rectangle { width: 3.3; height: 3; radius: 1.5; color: Theme.alpha(graph.color2, 1) } }
            }
        }
        Text {
            text: parent.text
            font.pixelSize: 12
            font.weight: Font.Medium
            color: Theme.secondaryLabel
        }
    }
}
