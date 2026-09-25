import QtQuick

// A headline metric: small caption above a large tabular number.
Card {
    id: tile

    property string caption: ""
    property string value: ""
    property string unit: ""
    property string footnote: ""
    property color accent: Theme.label

    implicitWidth: 168
    implicitHeight: footnote !== "" ? 98 : 84
    padding: 14
    radius: 18

    Column {
        anchors.fill: parent
        spacing: 3
        Text {
            width: parent.width
            text: tile.caption
            font.pixelSize: 12
            font.weight: Font.DemiBold
            color: Theme.secondaryLabel
            elide: Text.ElideRight
        }
        Row {
            spacing: 4
            Text {
                id: valueText
                text: tile.value
                font.family: Theme.displayFamily
                // numbers get the big treatment; words ("Discharging") step down
                font.pixelSize: /^[-+\d.,—]/.test(tile.value) ? 26 : 20
                font.weight: Font.DemiBold
                font.features: Theme.tabular
                color: tile.accent
            }
            Text {
                anchors.baseline: valueText.baseline
                text: tile.unit
                visible: text !== ""
                font.pixelSize: 14
                font.weight: Font.DemiBold
                color: Theme.secondaryLabel
            }
        }
        Text {
            width: parent.width
            visible: tile.footnote !== ""
            text: tile.footnote
            font.pixelSize: 12
            font.weight: Font.Medium
            font.features: Theme.tabular
            color: Theme.tertiaryLabel
            elide: Text.ElideRight
        }
    }
}
