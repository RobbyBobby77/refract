import QtQuick
import QtQuick.Effects
import QtQuick.Layouts

// The widget itself: Refract's sidebar rows on a glass card. Plain QML (plus
// i18n from the context), so preview.py can render it outside plasmashell.
Item {
    id: card

    required property SystemStats stats
    property bool dark: true
    property bool tinted: false
    property bool glass: true               // draw the card; off over Plasma's own background
    // The desktop's wallpaper item: the card frosts the part of it behind itself.
    // Without one (panel popup, plasmawindowed) the card is a plain tint.
    property Item backdrop: null
    property bool showHeader: true
    property color labelColor: dark ? "#FFFFFF" : "#000000"
    property string fontFamily: "Inter"
    signal openRequested(string device)

    implicitWidth: 306
    implicitHeight: content.implicitHeight + 2 * content.anchors.margins

    // --- Refract's palette -------------------------------------------------------
    readonly property color secondaryLabel: dark ? Qt.rgba(235/255, 235/255, 245/255, 0.62) : Qt.rgba(60/255, 60/255, 67/255, 0.66)
    readonly property color tertiaryLabel: dark ? Qt.rgba(235/255, 235/255, 245/255, 0.34) : Qt.rgba(60/255, 60/255, 67/255, 0.36)
    readonly property color blue:   dark ? "#0A84FF" : "#007AFF"
    readonly property color purple: dark ? "#BF5AF2" : "#AF52DE"
    readonly property color green:  dark ? "#30D158" : "#34C759"
    readonly property color orange: dark ? "#FF9F0A" : "#FF9500"
    readonly property color pink:   dark ? "#FF375F" : "#FF2D55"
    readonly property bool frosted: glass && backdrop !== null
    // Frosted glass needs less tint to stay legible than glass over a sharp wallpaper.
    readonly property real tintStrength: (tinted ? 0.86 : 0.70) - (frosted ? 0.22 : 0)
    // (Light glass needs more white to read as light over a dark wallpaper.)
    readonly property color fillTop: dark ? Qt.rgba(0.12, 0.12, 0.14, tintStrength)
                                          : Qt.rgba(0.97, 0.97, 0.98, tintStrength + (frosted ? 0.16 : 0.02))
    readonly property color fillBottom: dark ? Qt.rgba(0.09, 0.09, 0.11, tintStrength + 0.08)
                                             : Qt.rgba(0.94, 0.94, 0.96, tintStrength + (frosted ? 0.22 : 0.10))
    readonly property color rim: dark ? Qt.rgba(1, 1, 1, 0.14) : Qt.rgba(1, 1, 1, 0.85)

    // --- formatting, as in Refract: decimal units, "—" when unknown ------------------
    function isNum(v) { return v !== undefined && v !== null && v !== "" && !isNaN(v) }
    function num(v, digits) { return Number(v).toLocaleString(Qt.locale(), "f", digits) }
    function scaled(v, units, digits) {
        let i = 0
        let x = Math.abs(v)
        while (x >= 1000 && i < units.length - 1) { x /= 1000; ++i }
        const d = digits !== undefined ? digits : (x < 10 ? 2 : x < 100 ? 1 : 0)
        return num(x, i === 0 ? 0 : d) + " " + units[i]
    }
    function percent(v) { return isNum(v) ? num(v, 0) + "%" : "—" }
    function bytes(v, digits) { return isNum(v) ? scaled(v, ["bytes", "KB", "MB", "GB", "TB"], digits) : "—" }
    function rate(v) { return isNum(v) ? scaled(v, ["B/s", "KB/s", "MB/s", "GB/s"], 0) : "—" }
    function freq(mhz) { return isNum(mhz) && mhz > 0 ? (mhz >= 1000 ? num(mhz / 1000, 2) + " GHz" : num(mhz, 0) + " MHz") : "—" }
    function temp(c) { return isNum(c) && c > 0 ? num(c, 0) + " °C" : "" }

    // --- frosted backdrop: the wallpaper behind the card, blurred and clipped ------
    readonly property real blurPad: 48       // extra wallpaper around the card, so edges blur evenly
    readonly property real radius: 22
    property rect behindRect: Qt.rect(0, 0, 0, 0)
    function trackBackdrop() {
        if (!frosted) return
        const p = card.mapToItem(backdrop, 0, 0)
        const r = Qt.rect(p.x - blurPad, p.y - blurPad, width + 2 * blurPad, height + 2 * blurPad)
        if (r.x !== behindRect.x || r.y !== behindRect.y || r.width !== behindRect.width || r.height !== behindRect.height)
            behindRect = r
    }
    // Widgets move without telling their children, so check the position now and then
    // (cheap: the blur is only redone when it actually changed).
    Timer {
        interval: 300
        repeat: true
        running: card.frosted && card.visible
        triggeredOnStart: true
        onTriggered: card.trackBackdrop()
    }
    onWidthChanged: trackBackdrop()
    onHeightChanged: trackBackdrop()

    // An opaque rounded shape under everything carries the shadow; the frosted
    // glass covers its inside, so only the outside shadow shows.
    Rectangle {
        anchors.fill: parent
        visible: card.frosted
        radius: card.radius
        color: "black"
        layer.enabled: visible
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(0, 0, 0, card.dark ? 0.55 : 0.25)
            shadowBlur: 0.9
            shadowVerticalOffset: 5
        }
    }
    ShaderEffectSource {
        id: behind
        visible: false
        width: card.behindRect.width        // MultiEffect sizes its passes from the source
        height: card.behindRect.height
        sourceItem: card.frosted ? card.backdrop : null
        sourceRect: card.behindRect
    }
    Item {
        id: roundMask
        visible: false
        layer.enabled: true
        width: card.width + 2 * card.blurPad
        height: card.height + 2 * card.blurPad
        Rectangle {
            x: card.blurPad; y: card.blurPad
            width: card.width; height: card.height
            radius: card.radius
        }
    }
    MultiEffect {
        visible: card.frosted
        x: -card.blurPad; y: -card.blurPad
        width: card.width + 2 * card.blurPad
        height: card.height + 2 * card.blurPad
        source: behind
        autoPaddingEnabled: false           // blurPad already brings in the wallpaper around the card
        blurEnabled: true
        blurMax: 64
        blur: 1.0
        saturation: 0.35        // a little vibrancy, like Refract's glass
        maskEnabled: true
        maskSource: roundMask
        maskThresholdMin: 0.5
        maskSpreadAtMin: 1.0
    }

    Rectangle {
        id: glassFill
        anchors.fill: parent
        visible: card.glass
        radius: card.radius
        gradient: Gradient {
            GradientStop { position: 0; color: card.fillTop }
            GradientStop { position: 1; color: card.fillBottom }
        }
        border.width: 1
        border.color: card.rim
        layer.enabled: visible && !card.frosted
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(0, 0, 0, card.dark ? 0.5 : 0.22)
            shadowBlur: 0.9
            shadowVerticalOffset: 5
        }
    }
    // light catching the top edge
    Rectangle {
        visible: card.glass
        x: glassFill.radius
        y: 1
        width: parent.width - 2 * glassFill.radius
        height: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: 0.3; color: Qt.rgba(1, 1, 1, card.dark ? 0.32 : 0.95) }
            GradientStop { position: 1; color: "transparent" }
        }
    }

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: card.glass ? 8 : 0
        spacing: 0

        RowLayout {
            visible: card.showHeader
            Layout.fillWidth: true
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            Layout.topMargin: 6
            Layout.bottomMargin: 2
            spacing: 8
            Image {
                source: Qt.resolvedUrl("../images/refract.svg")
                sourceSize: Qt.size(18, 18)
                Layout.preferredWidth: 18
                Layout.preferredHeight: 18
            }
            Text {
                text: "Refract"
                font.family: card.fontFamily
                font.pixelSize: 13
                font.weight: Font.DemiBold
                color: card.secondaryLabel
            }
            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignRight
                text: card.stats.hostName
                font.family: card.fontFamily
                font.pixelSize: 12
                font.weight: Font.Medium
                color: card.tertiaryLabel
                elide: Text.ElideRight
            }
            TapHandler { onTapped: card.openRequested("") }
        }

        DeviceRow {
            visible: card.stats.showCpu
            title: i18n("CPU")
            summary: card.percent(card.stats.cpu) + "  " + card.freq(card.stats.cpuFrequency)
            values: card.stats.cpuHistory
            tint: card.blue
            dark: card.dark; labelColor: card.labelColor; secondaryColor: card.secondaryLabel; fontFamily: card.fontFamily
            onActivated: card.openRequested("cpu")
        }
        DeviceRow {
            visible: card.stats.showMemory
            title: i18n("Memory")
            summary: card.bytes(card.stats.memoryUsed, 1) + " / " + card.bytes(card.stats.memoryTotal, 0)
                     + "  (" + card.percent(card.stats.memoryPercent) + ")"
            values: card.stats.memoryHistory
            tint: card.purple
            dark: card.dark; labelColor: card.labelColor; secondaryColor: card.secondaryLabel; fontFamily: card.fontFamily
            onActivated: card.openRequested("memory")
        }
        DeviceRow {
            visible: card.stats.showDisk
            title: i18n("Disk")
            summary: i18n("Read %1   Write %2", card.rate(card.stats.diskReadRate), card.rate(card.stats.diskWriteRate))
            values: card.stats.readHistory
            values2: card.stats.writeHistory
            maxValue: -1
            tint: card.green
            dark: card.dark; labelColor: card.labelColor; secondaryColor: card.secondaryLabel; fontFamily: card.fontFamily
            onActivated: card.openRequested("")
        }
        DeviceRow {
            visible: card.stats.showNetwork
            title: i18n("Network")
            summary: "↓ " + card.rate(card.stats.download) + "   ↑ " + card.rate(card.stats.upload)
            values: card.stats.downloadHistory
            values2: card.stats.uploadHistory
            maxValue: -1
            tint: card.orange
            dark: card.dark; labelColor: card.labelColor; secondaryColor: card.secondaryLabel; fontFamily: card.fontFamily
            onActivated: card.openRequested("")
        }
        DeviceRow {
            visible: card.stats.showGpu && card.stats.hasGpu
            title: i18n("GPU")
            summary: card.percent(card.stats.gpu) + (card.temp(card.stats.gpuTemperature) ? "  " + card.temp(card.stats.gpuTemperature) : "")
            values: card.stats.gpuHistory
            tint: card.pink
            dark: card.dark; labelColor: card.labelColor; secondaryColor: card.secondaryLabel; fontFamily: card.fontFamily
            onActivated: card.openRequested("")
        }
        // spare height stays below the rows
        Item { Layout.fillHeight: true }
    }
}
