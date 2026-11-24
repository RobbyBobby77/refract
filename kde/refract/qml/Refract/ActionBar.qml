import QtQuick

// Floating glass capsule of actions for the current selection. It rises into
// view when something is selected, like a toolbar in iOS 26.
GlassSurface {
    id: bar

    property string title: ""
    property string iconSource: ""
    property var actions: []               // [{ text, icon, destructive?, prominent?, enabled?, action }]
    property bool shown: false

    height: 52
    width: content.implicitWidth + 16
    radius: height / 2
    frost: 12
    refraction: 18
    opacity: shown ? 1 : 0
    visible: opacity > 0
    scale: shown ? 1 : 0.9
    Behavior on opacity { NumberAnimation { duration: 180 } }
    Behavior on scale { SpringAnimation { spring: 3.5; damping: 0.32; epsilon: 0.002 } }

    Row {
        id: content
        anchors.verticalCenter: parent.verticalCenter
        x: 8
        spacing: 4

        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 9
            leftPadding: 10
            rightPadding: 10
            Icon {
                anchors.verticalCenter: parent.verticalCenter
                width: 22; height: 22
                visible: bar.iconSource !== ""
                source: bar.iconSource
                fallback: Theme.executableIcon
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                width: Math.min(implicitWidth, 220)
                text: bar.title
                font.pixelSize: 14
                font.weight: Font.DemiBold
                color: Theme.label
                elide: Text.ElideRight
            }
        }

        Rectangle { width: 1; height: 26; color: Theme.separator; anchors.verticalCenter: parent.verticalCenter }

        Repeater {
            model: bar.actions
            Rectangle {
                id: action
                required property var modelData
                readonly property bool enabledAction: modelData.enabled === undefined || modelData.enabled
                anchors.verticalCenter: parent.verticalCenter
                height: 38
                width: actionRow.implicitWidth + 26
                radius: height / 2
                opacity: enabledAction ? 1 : 0.4
                color: modelData.prominent ? (tap.pressed ? Qt.darker(Theme.red, 1.15) : Theme.red)
                     : tap.pressed ? Theme.fill : hover.hovered ? Theme.hoverFill : "transparent"
                Behavior on color { ColorAnimation { duration: 100 } }
                Row {
                    id: actionRow
                    anchors.centerIn: parent
                    spacing: 7
                    Icon {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 16; height: 16
                        visible: !!action.modelData.icon
                        source: action.modelData.icon || ""
                        isMask: true
                        color: action.modelData.prominent ? "white" : action.modelData.destructive ? Theme.red : Theme.label
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: action.modelData.text
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        color: action.modelData.prominent ? "white" : action.modelData.destructive ? Theme.red : Theme.label
                    }
                }
                HoverHandler { id: hover; enabled: action.enabledAction; cursorShape: Qt.PointingHandCursor }
                TapHandler { id: tap; enabled: action.enabledAction; onTapped: action.modelData.action() }
            }
        }
    }
}
