import QtQuick
import QtQuick.Controls.Basic

// The floating glass sidebar listing monitored devices.
GlassSurface {
    id: sidebar

    property string current: "cpu"
    signal activated(string key)

    radius: Theme.sidebarRadius
    refraction: 20
    bevel: 18
    frost: 12
    blurBias: 2.6

    Text {
        id: heading
        x: 22
        y: Prefs.windowButtonsRight || Prefs.nativeDecorations ? 22 : 50
        text: "Performance"
        font.pixelSize: 12
        font.weight: Font.Bold
        color: Theme.tertiaryLabel
    }

    ListView {
        id: list
        anchors.top: heading.bottom
        anchors.topMargin: 8
        anchors.bottom: footer.top
        anchors.bottomMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        clip: true
        spacing: 2
        boundsBehavior: Flickable.StopAtBounds
        model: Monitor.devices
        delegate: SidebarItem {
            width: list.width
            selected: key === sidebar.current
            onActivated: sidebar.activated(key)
        }
        ScrollBar.vertical: GlassScrollBar {}
    }

    Column {
        id: footer
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 18
        spacing: 3
        Rectangle { width: parent.width; height: 1; color: Theme.separator }
        Item { width: 1; height: 8 }
        Text {
            width: parent.width
            text: Monitor.staticInfo.hostname || ""
            font.pixelSize: 13
            font.weight: Font.DemiBold
            color: Theme.label
            elide: Text.ElideRight
        }
        Text {
            width: parent.width
            text: (Monitor.staticInfo.os_name || "")
            font.pixelSize: 11
            color: Theme.secondaryLabel
            elide: Text.ElideRight
        }
        Text {
            width: parent.width
            text: "Up " + Fmt.duration(Monitor.cpu.uptime_s)
            font.pixelSize: 11
            font.features: Theme.tabular
            color: Theme.secondaryLabel
        }
    }
}
