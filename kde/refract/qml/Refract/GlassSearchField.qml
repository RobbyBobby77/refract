import QtQuick
import org.kde.kirigami as Kirigami

// Capsule search field in glass; widens while focused.
GlassSurface {
    id: field

    property alias text: input.text
    property string placeholder: "Search"
    readonly property bool editing: input.activeFocus
    readonly property bool active: editing || input.text !== ""

    function focusField() { input.forceActiveFocus(); input.selectAll() }

    height: Theme.controlHeight
    width: active ? 280 : 200
    radius: height / 2
    Behavior on width { SpringAnimation { spring: 3; damping: 0.36; epsilon: 0.3 } }

    Kirigami.Icon {
        id: glass
        x: 13
        anchors.verticalCenter: parent.verticalCenter
        width: 16; height: 16
        source: "edit-find"
        isMask: true
        color: Theme.secondaryLabel
    }

    TextInput {
        id: input
        anchors.left: glass.right
        anchors.leftMargin: 8
        anchors.right: clear.left
        anchors.rightMargin: 6
        anchors.verticalCenter: parent.verticalCenter
        font.pixelSize: 14
        color: Theme.label
        selectionColor: Theme.alpha(Theme.accent, 0.5)
        selectedTextColor: Theme.label
        clip: true
        Keys.onEscapePressed: { text = ""; focus = false }

        Text {
            visible: input.text === ""
            anchors.verticalCenter: parent.verticalCenter
            text: field.placeholder
            font: input.font
            color: Theme.tertiaryLabel
        }
    }

    Rectangle {
        id: clear
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        width: 18; height: 18; radius: 9
        visible: input.text !== ""
        color: Theme.tertiaryLabel
        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -1
            text: "×"
            font.pixelSize: 14
            font.weight: Font.Bold
            color: Theme.dark ? "#1c1c1e" : "white"
        }
        TapHandler { onTapped: input.text = "" }
    }

    TapHandler { onTapped: input.forceActiveFocus() }
}
