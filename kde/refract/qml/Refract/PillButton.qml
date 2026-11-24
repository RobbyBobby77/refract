import QtQuick

// Content-area capsule button (tinted, not glass).
Rectangle {
    id: btn

    property string text: ""
    property string iconName: ""
    property color tint: Theme.accent
    property bool prominent: false
    property bool enabledState: true
    signal clicked()

    implicitHeight: 30
    implicitWidth: row.implicitWidth + 26
    radius: height / 2
    opacity: enabledState ? 1 : 0.4
    color: prominent ? (tap.pressed ? Qt.darker(tint, 1.15) : tint)
                     : tap.pressed ? Theme.alpha(tint, 0.30) : hover.hovered ? Theme.alpha(tint, 0.22) : Theme.alpha(tint, 0.15)
    Behavior on color { ColorAnimation { duration: 100 } }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        Icon {
            visible: btn.iconName !== ""
            anchors.verticalCenter: parent.verticalCenter
            width: 15; height: 15
            source: btn.iconName
            isMask: true
            color: btn.prominent ? "white" : btn.tint
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: btn.text
            font.pixelSize: 13
            font.weight: Font.DemiBold
            color: btn.prominent ? "white" : btn.tint
        }
    }

    HoverHandler { id: hover; enabled: btn.enabledState; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: tap; enabled: btn.enabledState; onTapped: btn.clicked() }
}
