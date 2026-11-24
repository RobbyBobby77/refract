import QtQuick

// A round (or capsule, when it has text) glass button.
GlassSurface {
    id: btn

    property string iconName: ""
    property string iconSource: ""
    property string text: ""
    property color iconColor: Theme.label
    property bool prominent: false        // filled with the accent colour
    property bool destructive: false
    property string tooltip: ""
    signal clicked()

    implicitHeight: Theme.controlHeight
    implicitWidth: text !== "" ? row.implicitWidth + 30 : implicitHeight
    width: implicitWidth
    height: implicitHeight
    radius: height / 2
    press: tap.pressed ? 1 : (hover.hovered ? 0.35 : 0)
    tint: prominent ? Theme.alpha(destructive ? Theme.red : Theme.accent, 0.82) : Theme.glassTint
    shadowBlur: 18
    shadowOffset: 5
    scale: tap.pressed ? 0.94 : (hover.hovered ? 1.03 : 1)
    Behavior on scale { SpringAnimation { spring: 5; damping: 0.35; epsilon: 0.002 } }
    Behavior on press { NumberAnimation { duration: 120 } }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 7
        Icon {
            visible: btn.iconName !== "" || btn.iconSource !== ""
            anchors.verticalCenter: parent.verticalCenter
            width: 17; height: 17
            source: btn.iconSource !== "" ? btn.iconSource : btn.iconName
            isMask: true
            color: btn.prominent ? "white" : (btn.destructive ? Theme.red : btn.iconColor)
        }
        Text {
            visible: btn.text !== ""
            anchors.verticalCenter: parent.verticalCenter
            text: btn.text
            font.pixelSize: 14
            font.weight: Font.DemiBold
            color: btn.prominent ? "white" : (btn.destructive ? Theme.red : Theme.label)
        }
    }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: tap; onTapped: btn.clicked() }

    ToolTipBubble { text: btn.tooltip; shown: hover.hovered && btn.tooltip !== "" }
}
