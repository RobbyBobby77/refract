import QtQuick
import QtQuick.Controls.Basic

// Thin overlay scroller that fades in while scrolling, macOS style.
ScrollBar {
    id: bar
    policy: ScrollBar.AsNeeded
    minimumSize: 0.08
    padding: 3
    contentItem: Rectangle {
        implicitWidth: bar.hovered || bar.pressed ? 8 : 6
        implicitHeight: implicitWidth
        radius: width / 2
        color: Theme.dark ? Qt.rgba(1, 1, 1, bar.pressed ? 0.55 : 0.38) : Qt.rgba(0, 0, 0, bar.pressed ? 0.48 : 0.32)
        opacity: bar.active || bar.hovered ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 260 } }
        Behavior on implicitWidth { NumberAnimation { duration: 120 } }
    }
    background: Item {}
}
