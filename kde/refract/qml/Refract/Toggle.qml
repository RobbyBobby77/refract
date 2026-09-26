import QtQuick

// iOS/macOS style switch with a springy knob.
Rectangle {
    id: toggle

    property bool checked: false
    signal toggled(bool checked)

    implicitWidth: 44
    implicitHeight: 26
    radius: height / 2
    color: checked ? Theme.green : Theme.fill
    Behavior on color { ColorAnimation { duration: 180 } }

    Rectangle {
        id: knob
        width: toggle.height - 4 + (tap.pressed ? 5 : 0)
        height: toggle.height - 4
        radius: height / 2
        y: 2
        x: toggle.checked ? toggle.width - width - 2 : 2
        color: "white"
        border.width: 0.5
        border.color: Qt.rgba(0, 0, 0, 0.06)
        Behavior on x { SpringAnimation { spring: 5; damping: 0.38; epsilon: 0.2 } }
        Behavior on width { NumberAnimation { duration: 120 } }
    }

    TapHandler {
        id: tap
        onTapped: toggle.toggled(!toggle.checked)
    }
    HoverHandler { cursorShape: Qt.PointingHandCursor }
}
