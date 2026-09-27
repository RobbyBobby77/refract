import QtQuick
import QtQuick.Layouts

// One device, as in Refract's sidebar: a live sparkline, the name and a
// one-line summary. Clicking it opens Refract.
Item {
    id: row

    property string title
    property string summary
    property var values: []
    property var values2: []
    property real maxValue: 100
    property color tint
    property bool dark: true
    property color labelColor
    property color secondaryColor
    property string fontFamily
    signal activated()

    Layout.fillWidth: true
    implicitHeight: 62

    function alpha(c, a) { return Qt.rgba(c.r, c.g, c.b, a) }
    function mix(a, b, t) { return Qt.rgba(a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t, a.b + (b.b - a.b) * t, 1) }

    Rectangle {
        anchors.fill: parent
        radius: 13
        color: hover.hovered ? (row.dark ? Qt.rgba(1, 1, 1, 0.07) : Qt.rgba(0, 0, 0, 0.045)) : "transparent"
        Behavior on color { ColorAnimation { duration: 160 } }
    }

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12

        Rectangle {
            id: spark
            width: 54; height: 38
            radius: 9
            color: row.alpha(row.tint, row.dark ? 0.12 : 0.10)
            border.width: 1
            border.color: row.alpha(row.tint, 0.38)
            clip: true
            Sparkline {
                anchors.fill: parent
                anchors.margins: 1
                values: row.values
                values2: row.values2
                maxValue: row.maxValue
                color: row.tint
                color2: row.mix(row.tint, row.labelColor, 0.35)
            }
        }

        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - spark.width - parent.spacing
            spacing: 2
            Text {
                width: parent.width
                text: row.title
                font.family: row.fontFamily
                font.pixelSize: 14
                font.weight: Font.DemiBold
                color: row.labelColor
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                text: row.summary
                font.family: row.fontFamily
                font.pixelSize: 12
                font.weight: Font.Medium
                font.features: { "tnum": 1 }
                color: row.secondaryColor
                elide: Text.ElideRight
            }
        }
    }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: row.activated() }
}
