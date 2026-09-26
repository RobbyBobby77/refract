import QtQuick

// A responsive row/grid of StatTiles. `tiles` is re-evaluated every sample;
// the Repeater is driven by the count so delegates are reused, not rebuilt.
Grid {
    id: grid

    property var tiles: []                 // [{ caption, text | value+unit, footnote?, accent? }]
    property real minTile: 132

    readonly property int count: tiles.length
    readonly property bool anyFootnote: tiles.some(t => !!t.footnote)
    readonly property real cell: (width - (columns - 1) * spacing) / Math.max(columns, 1)

    width: parent ? parent.width : 0
    spacing: 12
    // as many per row as fit, then balanced so the last row isn't a lone orphan
    readonly property int maxColumns: Math.max(1, Math.min(count, Math.floor((width + spacing) / (minTile + spacing))))
    columns: Math.ceil(count / Math.ceil(count / maxColumns))

    function split(t) {
        if (t.text === undefined) return [t.value, t.unit || ""]
        const s = String(t.text)
        const i = s.lastIndexOf(" ")
        if (i <= 0 || /^\d/.test(s.slice(i + 1))) return [s, ""]
        return [s.slice(0, i), s.slice(i + 1)]
    }

    Repeater {
        model: grid.count
        StatTile {
            required property int index
            readonly property var d: grid.tiles[index] || ({})
            readonly property var parts: grid.split(d)
            width: grid.cell
            height: grid.anyFootnote ? 98 : 84
            caption: d.caption || ""
            value: parts[0] === undefined ? Fmt.dash : parts[0]
            unit: parts[1]
            footnote: d.footnote || ""
            accent: d.accent || Theme.label
        }
    }
}
