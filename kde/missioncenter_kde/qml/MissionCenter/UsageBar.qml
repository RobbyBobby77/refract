import QtQuick

// A capsule bar made of coloured segments, e.g. memory composition or disk use.
Item {
    id: bar

    property var segments: []              // [{ value, color, label }]
    property real total: 1
    property real barHeight: 12
    property bool showLegend: true
    property var format: function (v) { return Fmt.bytes(v, 1) }

    implicitHeight: barHeight + (showLegend ? 26 : 0)

    Rectangle {
        id: track
        width: parent.width
        height: bar.barHeight
        radius: height / 2
        color: Theme.fill
        clip: true
        Row {
            anchors.fill: parent
            Repeater {
                model: bar.segments
                Rectangle {
                    required property var modelData
                    height: track.height
                    width: bar.total > 0 ? Math.max(0, track.width * modelData.value / bar.total) : 0
                    color: modelData.color
                    Behavior on width { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
                }
            }
        }
        // soft top highlight so the bar reads as a glossy capsule
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            gradient: Gradient {
                GradientStop { position: 0; color: Qt.rgba(1, 1, 1, 0.22) }
                GradientStop { position: 0.6; color: Qt.rgba(1, 1, 1, 0) }
            }
        }
    }

    Flow {
        visible: bar.showLegend
        anchors.top: track.bottom
        anchors.topMargin: 9
        width: parent.width
        spacing: 16
        Repeater {
            model: bar.segments
            Row {
                required property var modelData
                spacing: 6
                visible: !!modelData.label
                Rectangle { width: 8; height: 8; radius: 4; color: modelData.color; anchors.verticalCenter: parent.verticalCenter }
                Text {
                    text: modelData.label + "  " + bar.format(modelData.value)
                    font.pixelSize: 12
                    font.weight: Font.Medium
                    font.features: Theme.tabular
                    color: Theme.secondaryLabel
                }
            }
        }
    }
}
