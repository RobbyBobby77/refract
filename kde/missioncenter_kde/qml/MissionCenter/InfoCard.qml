import QtQuick
import QtQuick.Layouts

// Key/value details laid out in one or two columns, like "About This Mac".
Card {
    id: info

    property string title: ""
    property var rows: []                  // [[key, value], ...]
    readonly property int columns: width > 640 ? 2 : 1

    padding: 18
    implicitHeight: col.implicitHeight + 2 * padding

    Column {
        id: col
        width: parent.width
        spacing: 12

        Text {
            visible: info.title !== ""
            text: info.title
            font.pixelSize: 13
            font.weight: Font.DemiBold
            color: Theme.label
        }

        GridLayout {
            width: parent.width
            columns: info.columns * 2
            columnSpacing: 14
            rowSpacing: 9
            Repeater {
                model: info.rows.length * 2
                delegate: Text {
                    required property int index
                    readonly property var row: info.rows[Math.floor(index / 2)] || ["", ""]
                    readonly property bool isKey: index % 2 === 0
                    Layout.fillWidth: !isKey
                    Layout.preferredWidth: isKey ? 150 : -1
                    Layout.maximumWidth: isKey ? 170 : 100000
                    text: isKey ? row[0] : (row[1] === undefined || row[1] === null || row[1] === "" ? Fmt.dash : String(row[1]))
                    font.pixelSize: 13
                    font.weight: isKey ? Font.Medium : Font.DemiBold
                    font.features: Theme.tabular
                    color: isKey ? Theme.secondaryLabel : Theme.label
                    elide: Text.ElideRight
                    horizontalAlignment: isKey ? Text.AlignRight : Text.AlignLeft
                }
            }
        }
    }

}
