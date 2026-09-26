import QtQuick
import QtQuick.Controls.Basic
import org.kde.kirigami as Kirigami

// Context menu made of Liquid Glass.
Popup {
    id: menu

    property var items: []                 // [{ text, icon?, destructive?, enabled?, separator?, action }]

    function popupAt(px, py) {
        const ov = parent
        x = Math.min(px, ov.width - width - 8)
        y = Math.min(py, ov.height - height - 8)
        open()
    }

    parent: Overlay.overlay
    padding: 6
    width: 230
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: GlassSurface {
        radius: 16
        tint: Theme.dark ? Qt.rgba(0.12, 0.12, 0.14, 0.62) : Qt.rgba(1, 1, 1, 0.74)
        frost: 14
        blurBias: 2.8
        refraction: 14
        shadowBlur: 36
        shadowOffset: 12
    }

    contentItem: Column {
        Repeater {
            model: menu.items
            Item {
                id: entry
                required property var modelData
                readonly property bool isSeparator: !!modelData.separator
                readonly property bool enabledEntry: modelData.enabled === undefined || modelData.enabled
                width: menu.availableWidth
                height: isSeparator ? 11 : 32

                Rectangle {
                    visible: entry.isSeparator
                    anchors.verticalCenter: parent.verticalCenter
                    x: 10
                    width: parent.width - 20
                    height: 1
                    color: Theme.separator
                }

                Rectangle {
                    visible: !entry.isSeparator
                    anchors.fill: parent
                    radius: 9
                    color: hover.hovered && entry.enabledEntry ? (entry.modelData.destructive ? Theme.red : Theme.accent) : "transparent"
                }
                Row {
                    visible: !entry.isSeparator
                    anchors.verticalCenter: parent.verticalCenter
                    x: 10
                    spacing: 10
                    opacity: entry.enabledEntry ? 1 : 0.4
                    Kirigami.Icon {
                        width: 16; height: 16
                        anchors.verticalCenter: parent.verticalCenter
                        source: entry.modelData.icon || ""
                        visible: !!entry.modelData.icon
                        isMask: true
                        color: hover.hovered ? "white" : (entry.modelData.destructive ? Theme.red : Theme.label)
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: entry.modelData.text || ""
                        font.pixelSize: 13
                        font.weight: Font.Medium
                        color: hover.hovered && entry.enabledEntry ? "white" : (entry.modelData.destructive ? Theme.red : Theme.label)
                    }
                }
                HoverHandler { id: hover; enabled: !entry.isSeparator }
                TapHandler {
                    enabled: !entry.isSeparator && entry.enabledEntry
                    onTapped: {
                        menu.close()
                        if (entry.modelData.action) entry.modelData.action()
                    }
                }
            }
        }
    }

    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 120 }
            NumberAnimation { property: "scale"; from: 0.92; to: 1; duration: 260; easing.type: Easing.OutBack }
        }
    }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 100 } }
}
