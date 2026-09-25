import QtQuick
import QtQuick.Controls.Basic

// A modal Liquid Glass sheet that springs in from slightly below.
Popup {
    id: sheet

    property string title: ""
    property string subtitle: ""
    default property alias body: bodyItem.data
    property alias footer: footerRow.data
    property real preferredWidth: 560
    property real preferredHeight: -1

    parent: Overlay.overlay
    modal: true
    dim: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    width: Math.min(preferredWidth, parent ? parent.width - 80 : preferredWidth)
    height: preferredHeight > 0 ? Math.min(preferredHeight, parent ? parent.height - 80 : preferredHeight)
                                : Math.min(implicitHeight, parent ? parent.height - 80 : implicitHeight)
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? Math.round((parent.height - height) / 2) : 0
    padding: 24
    topPadding: 22

    Overlay.modal: Rectangle {
        color: Theme.dark ? Qt.rgba(0, 0, 0, 0.32) : Qt.rgba(0, 0, 0, 0.14)
    }

    background: GlassSurface {
        radius: 28
        tint: Theme.dark ? Qt.rgba(0.11, 0.11, 0.13, Theme.reduceTransparency ? 0.98 : 0.72)
                         : Qt.rgba(0.98, 0.98, 0.99, Theme.reduceTransparency ? 0.98 : 0.80)
        frost: 16
        blurBias: 3
        refraction: 22
        bevel: 26
        shadowBlur: 60
        shadowOffset: 18
        shadowColor: Theme.dark ? Qt.rgba(0, 0, 0, 0.55) : Qt.rgba(0, 0, 0, 0.25)
    }

    contentItem: Item {
        implicitHeight: header.implicitHeight + bodyItem.childrenRect.height + footerRow.implicitHeight + 40
        Column {
            id: header
            width: parent.width
            spacing: 4
            Text {
                width: parent.width
                text: sheet.title
                font.family: Theme.displayFamily
                font.pixelSize: 21
                font.weight: Font.Bold
                color: Theme.label
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                visible: sheet.subtitle !== ""
                text: sheet.subtitle
                font.pixelSize: 13
                color: Theme.secondaryLabel
                elide: Text.ElideMiddle
            }
        }
        Item {
            id: bodyItem
            anchors.top: header.bottom
            anchors.topMargin: 18
            anchors.bottom: footerRow.top
            anchors.bottomMargin: 18
            width: parent.width
        }
        Row {
            id: footerRow
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            spacing: 10
        }
    }

    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 180; easing.type: Easing.OutCubic }
            NumberAnimation { property: "scale"; from: 0.94; to: 1; duration: 420; easing.type: Easing.OutBack; easing.overshoot: 1.2 }
        }
    }
    exit: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 140 }
            NumberAnimation { property: "scale"; from: 1; to: 0.97; duration: 140 }
        }
    }
}
