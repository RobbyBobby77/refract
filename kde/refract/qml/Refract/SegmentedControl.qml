import QtQuick
import org.kde.kirigami as Kirigami

// Glass segmented control. The selection is a clear glass lens that
// springs between segments and swells while it moves, like the tab bars in
// iOS/macOS 26.
GlassSurface {
    id: seg

    property var model: []                 // [{ key, title, icon?, iconSource? }]
    property string current: ""
    property bool compact: false
    signal activated(string key)

    readonly property int currentIndex: {
        for (let i = 0; i < model.length; ++i)
            if (model[i].key === current) return i
        return 0
    }
    readonly property Item currentItem: segRepeater.count > currentIndex ? segRepeater.itemAt(currentIndex) : null

    implicitHeight: compact ? 32 : Theme.controlHeight + 2
    implicitWidth: segRow.implicitWidth + 8
    width: implicitWidth
    height: implicitHeight
    radius: height / 2
    frost: 10

    GlassSurface {
        id: lens
        y: 4
        height: seg.height - 8
        x: seg.currentItem ? seg.currentItem.x + 4 : 4
        width: seg.currentItem ? seg.currentItem.width : 0
        radius: height / 2
        refraction: 12
        bevel: height / 2
        frost: 2.5
        blurBias: 0.6
        dispersion: 1.2
        saturation: 1.0
        shadow: false
        tint: Theme.dark ? Qt.rgba(0.55, 0.55, 0.6, 0.30) : Qt.rgba(1, 1, 1, 0.78)
        specular: 1.1

        property bool moving: xAnim.running
        transform: Scale {
            origin.x: lens.width / 2
            origin.y: lens.height / 2
            xScale: lens.moving ? 1.10 : 1
            yScale: lens.moving ? 1.22 : 1
            Behavior on xScale { SpringAnimation { spring: 4; damping: 0.3; epsilon: 0.002 } }
            Behavior on yScale { SpringAnimation { spring: 4; damping: 0.3; epsilon: 0.002 } }
        }
        Behavior on x { SpringAnimation { id: xAnim; spring: 3.2; damping: 0.3; epsilon: 0.25 } }
        Behavior on width { SpringAnimation { spring: 2.4; damping: 0.32; epsilon: 0.25 } }
    }

    Row {
        id: segRow
        x: 4
        anchors.verticalCenter: parent.verticalCenter
        Repeater {
            id: segRepeater
            model: seg.model
            delegate: Item {
                id: segItem
                required property var modelData
                required property int index
                readonly property bool selected: index === seg.currentIndex
                width: segContent.implicitWidth + (seg.compact ? 26 : 34)
                height: seg.height - 8

                Row {
                    id: segContent
                    anchors.centerIn: parent
                    spacing: 7
                    Kirigami.Icon {
                        visible: !!(segItem.modelData.icon || segItem.modelData.iconSource)
                        anchors.verticalCenter: parent.verticalCenter
                        width: 16; height: 16
                        source: segItem.modelData.iconSource || segItem.modelData.icon || ""
                        isMask: true
                        color: segItem.selected ? Theme.accent : Theme.label
                        Behavior on color { ColorAnimation { duration: Theme.quick } }
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: segItem.modelData.title
                        font.pixelSize: seg.compact ? 13 : 14
                        font.weight: segItem.selected ? Font.DemiBold : Font.Medium
                        color: Theme.label
                        Behavior on color { ColorAnimation { duration: Theme.quick } }
                    }
                }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: seg.activated(segItem.modelData.key) }
            }
        }
    }
}
