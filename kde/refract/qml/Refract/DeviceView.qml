import QtQuick
import QtQuick.Controls.Basic

// Scaffold for a device page: a large title with the device model, optional
// header accessories, and a scrolling column of cards that slides under the
// floating toolbar.
Flickable {
    id: view

    property string title: ""
    property string subtitle: ""
    property real headerSpace: 64
    default property alias body: bodyColumn.data
    property alias accessories: accessoryRow.data
    readonly property real graphHeight: Math.max(230, Math.min(440, (height - headerSpace) * 0.42))

    contentWidth: width
    contentHeight: column.implicitHeight + headerSpace + 24
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: GlassScrollBar {}

    Column {
        id: column
        y: view.headerSpace
        width: view.width
        spacing: 16

        Item {
            width: parent.width
            height: 46
            Row {
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 4
                spacing: 14
                Text {
                    id: titleText
                    text: view.title
                    font.family: Theme.displayFamily
                    font.pixelSize: 30
                    font.weight: Font.Bold
                    color: Theme.label
                }
                Text {
                    anchors.baseline: titleText.baseline
                    width: Math.min(implicitWidth, view.width - titleText.width - accessoryRow.width - 40)
                    text: view.subtitle
                    font.pixelSize: 14
                    font.weight: Font.Medium
                    color: Theme.secondaryLabel
                    elide: Text.ElideRight
                }
            }
            Row {
                id: accessoryRow
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: 2
                spacing: 10
            }
        }

        Column {
            id: bodyColumn
            width: parent.width
            spacing: 14
        }
    }
}
