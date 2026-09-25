pragma Singleton
import QtQuick

// Design tokens. Colours follow Apple's system palette (dark/light variants),
// the geometry follows the Liquid Glass guidelines: concentric corner radii,
// generous insets, capsule controls.
QtObject {
    id: theme

    // --- appearance ------------------------------------------------------
    readonly property bool dark: {
        const forced = StartupOptions.theme
        if (forced === "dark") return true
        if (forced === "light") return false
        if (Prefs.themeMode === 2) return true
        if (Prefs.themeMode === 1) return false
        return Qt.styleHints.colorScheme !== Qt.ColorScheme.Light
    }
    readonly property bool reduceTransparency: Prefs.reduceTransparency
    readonly property bool tinted: Prefs.glassStyle === 1

    // Set by Main.qml: the layered scene that chrome glass refracts.
    property Item glassSource: null

    // --- Apple system colours ----------------------------------------------
    readonly property color red:    dark ? "#FF453A" : "#FF3B30"
    readonly property color orange: dark ? "#FF9F0A" : "#FF9500"
    readonly property color yellow: dark ? "#FFD60A" : "#FFCC00"
    readonly property color green:  dark ? "#30D158" : "#34C759"
    readonly property color mint:   dark ? "#63E6E2" : "#00C7BE"
    readonly property color teal:   dark ? "#40CBE0" : "#30B0C7"
    readonly property color cyan:   dark ? "#64D2FF" : "#32ADE6"
    readonly property color blue:   dark ? "#0A84FF" : "#007AFF"
    readonly property color indigo: dark ? "#5E5CE6" : "#5856D6"
    readonly property color purple: dark ? "#BF5AF2" : "#AF52DE"
    readonly property color pink:   dark ? "#FF375F" : "#FF2D55"
    readonly property color graphite: dark ? "#98989D" : "#8E8E93"

    // KDE's accent colour (System Settings → Colours), via the platform palette.
    readonly property SystemPalette systemPalette: SystemPalette { colorGroup: SystemPalette.Active }

    function named(name) {
        switch (name) {
        case "system": return systemPalette.highlight
        case "red": return red
        case "orange": return orange
        case "yellow": return yellow
        case "green": return green
        case "mint": return mint
        case "teal": return teal
        case "cyan": return cyan
        case "indigo": return indigo
        case "purple": return purple
        case "pink": return pink
        case "graphite": return graphite
        default: return blue
        }
    }

    readonly property color accent: Prefs.accent === "multicolor" ? blue : named(Prefs.accent)
    // Device colours stay distinct in multicolour mode, otherwise follow the accent.
    function deviceColor(name) {
        return Prefs.accent === "multicolor" ? named(name) : accent
    }

    // --- labels & fills ----------------------------------------------------------
    readonly property color label: dark ? "#FFFFFF" : "#000000"
    readonly property color secondaryLabel: dark ? Qt.rgba(235/255, 235/255, 245/255, 0.62) : Qt.rgba(60/255, 60/255, 67/255, 0.66)
    readonly property color tertiaryLabel: dark ? Qt.rgba(235/255, 235/255, 245/255, 0.34) : Qt.rgba(60/255, 60/255, 67/255, 0.36)
    readonly property color quaternaryLabel: dark ? Qt.rgba(235/255, 235/255, 245/255, 0.18) : Qt.rgba(60/255, 60/255, 67/255, 0.18)
    readonly property color separator: dark ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(0, 0, 0, 0.09)
    readonly property color fill: dark ? Qt.rgba(120/255, 120/255, 128/255, 0.30) : Qt.rgba(120/255, 120/255, 128/255, 0.16)
    readonly property color secondaryFill: dark ? Qt.rgba(120/255, 120/255, 128/255, 0.20) : Qt.rgba(120/255, 120/255, 128/255, 0.10)
    readonly property color hoverFill: dark ? Qt.rgba(1, 1, 1, 0.07) : Qt.rgba(0, 0, 0, 0.045)

    // --- materials ---------------------------------------------------------------
    // content-layer cards
    readonly property color cardFill: reduceTransparency ? (dark ? "#2A2A2E" : "#FFFFFF")
                                     : dark ? Qt.rgba(1, 1, 1, 0.075) : Qt.rgba(1, 1, 1, 0.58)
    readonly property color cardFillBottom: reduceTransparency ? cardFill
                                     : dark ? Qt.rgba(1, 1, 1, 0.045) : Qt.rgba(1, 1, 1, 0.46)
    readonly property color cardRim: dark ? Qt.rgba(1, 1, 1, 0.30) : Qt.rgba(1, 1, 1, 0.95)
    // navigation-layer glass
    readonly property color glassTint: reduceTransparency ? (dark ? Qt.rgba(0.14, 0.14, 0.16, 0.96) : Qt.rgba(0.97, 0.97, 0.98, 0.96))
                                     : tinted ? (dark ? Qt.rgba(0.10, 0.10, 0.12, 0.62) : Qt.rgba(1, 1, 1, 0.70))
                                     : dark ? Qt.rgba(0.22, 0.22, 0.25, 0.32) : Qt.rgba(1, 1, 1, 0.40)
    readonly property color glassRim: dark ? Qt.rgba(1, 1, 1, 0.55) : Qt.rgba(1, 1, 1, 1.0)
    // window background: 0 glass (see-through, over KWin's blur),
    // 1 wallpaper tint, 2 solid. Glass needs the compositor; otherwise solid.
    readonly property int backdrop: Prefs.backdropMode === 0 && (!WindowEffects.available || reduceTransparency) ? 2 : Prefs.backdropMode
    readonly property bool seeThrough: backdrop === 0
    readonly property color windowFillTop: seeThrough
        ? (dark ? Qt.rgba(0.12, 0.12, 0.14, tinted ? 0.86 : 0.74) : Qt.rgba(0.97, 0.97, 0.98, tinted ? 0.88 : 0.76))
        : (dark ? "#1F1F22" : "#F4F4F7")
    readonly property color windowFillBottom: seeThrough
        ? (dark ? Qt.rgba(0.09, 0.09, 0.11, tinted ? 0.90 : 0.80) : Qt.rgba(0.94, 0.94, 0.96, tinted ? 0.92 : 0.82))
        : (dark ? "#18181B" : "#EDEDF1")
    readonly property color windowRim: dark ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.9)
    // wallpaper mode: just a hint of the desktop's colour, like macOS tinting
    readonly property color windowOverlay: dark ? Qt.rgba(0.09, 0.09, 0.11, 0.78) : Qt.rgba(0.96, 0.96, 0.98, 0.74)
    readonly property color shadow: dark ? Qt.rgba(0, 0, 0, 0.45) : Qt.rgba(0, 0, 0, 0.16)

    // --- geometry ----------------------------------------------------------------
    readonly property real windowRadius: 26
    readonly property real inset: 10
    readonly property real sidebarRadius: windowRadius - inset
    readonly property real cardRadius: 22
    readonly property real controlHeight: 38
    readonly property real sidebarWidth: 264

    // --- type ----------------------------------------------------------------
    readonly property string fontFamily: "Inter"
    readonly property string displayFamily: "Inter Display"
    readonly property var tabular: ({ "tnum": 1 })
    readonly property url executableIcon: Qt.resolvedUrl("../../icons/application-x-executable.svg")

    // --- motion -------------------------------------------------------------------
    readonly property int quick: 160
    readonly property int smooth: 320

    function alpha(c, a) { return Qt.rgba(c.r, c.g, c.b, a) }
    function mix(a, b, t) { return Qt.rgba(a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t, a.b + (b.b - a.b) * t, a.a + (b.a - a.a) * t) }
}
