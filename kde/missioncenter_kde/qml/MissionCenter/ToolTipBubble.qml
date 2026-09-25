import QtQuick
import QtQuick.Controls.Basic

// Small capsule tooltip shown below its parent after a short delay.
ToolTip {
    id: tip
    property bool shown: false
    visible: shown && text !== ""
    delay: 550
    y: parent ? parent.height + 8 : 0
    x: parent ? (parent.width - implicitWidth) / 2 : 0
    padding: 0
    topPadding: 6; bottomPadding: 6; leftPadding: 11; rightPadding: 11
    contentItem: Text {
        text: tip.text
        font.pixelSize: 12
        font.weight: Font.Medium
        color: Theme.label
    }
    background: Rectangle {
        radius: height / 2
        color: Theme.dark ? Qt.rgba(0.16, 0.16, 0.18, 0.96) : Qt.rgba(1, 1, 1, 0.97)
        border.width: 1
        border.color: Theme.separator
    }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 120 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 90 } }
}
