import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as P5Support
import org.kde.plasma.plasmoid

// Refract's sidebar as a desktop widget: live graphs for CPU, memory, disk,
// network and GPU on a glass card (GlassCard.qml). Data comes from Plasma's
// own system sensors (SystemStats.qml), so it works without Refract running;
// clicking a row opens Refract. This file is the Plasma side: settings, the
// panel icon, and launching the app.
PlasmoidItem {
    id: root

    readonly property var cfg: Plasmoid.configuration
    // On the desktop (or in plasmawindowed) the card shows directly; in a panel,
    // a small CPU graph opens it as a popup.
    readonly property bool onDesktop: [PlasmaCore.Types.Planar, PlasmaCore.Types.MediaCenter,
                                       PlasmaCore.Types.Application].includes(Plasmoid.formFactor)
    // Our own glass, unless the user switched on Plasma's standard background
    // (or we're in a panel popup, which has its own).
    readonly property bool glass: onDesktop && !(Plasmoid.effectiveBackgroundHints & PlasmaCore.Types.StandardBackground)
    readonly property bool themeDark: Kirigami.ColorUtils.brightnessForColor(Kirigami.Theme.backgroundColor) === Kirigami.ColorUtils.Dark

    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground | PlasmaCore.Types.ConfigurableBackground
    preferredRepresentation: onDesktop ? fullRepresentation : compactRepresentation
    toolTipMainText: "Refract"
    toolTipSubText: i18n("CPU %1 · Memory %2", Math.round(sensors.cpu || 0) + "%", Math.round(sensors.memoryPercent || 0) + "%")

    // Refract's typeface, bundled with the widget (install.sh copies it in).
    FontLoader { id: interMedium; source: Qt.resolvedUrl("../fonts/Inter-Medium.ttf") }
    FontLoader { id: interSemiBold; source: Qt.resolvedUrl("../fonts/Inter-SemiBold.ttf") }
    readonly property string fontFamily: interSemiBold.status === FontLoader.Ready ? "Inter" : Kirigami.Theme.defaultFont.family

    SystemStats {
        id: sensors
        showCpu: root.cfg.showCpu
        showMemory: root.cfg.showMemory
        showDisk: root.cfg.showDisk
        showNetwork: root.cfg.showNetwork
        showGpu: root.cfg.showGpu
    }

    // --- opening Refract ------------------------------------------------------------
    // Found once: the Flatpak, a source install (`refract` on PATH), or neither.
    property string refract: ""
    readonly property string probe: "if flatpak info io.github.RobbyBobby77.Refract >/dev/null 2>&1; then echo flatpak;"
                                  + " elif command -v refract >/dev/null 2>&1; then echo native; fi"
    P5Support.DataSource {
        id: shell
        engine: "executable"
        connectedSources: []
        onNewData: (source, data) => {
            if (source === root.probe)
                root.refract = (data.stdout || "").trim()
            disconnectSource(source)
        }
    }
    Component.onCompleted: shell.connectSource(probe)

    // kstart gives Refract its own app scope, as if started from the launcher.
    function openRefract(device) {
        const args = device ? " --device " + device : ""
        if (refract === "flatpak")
            shell.connectSource("kstart --desktopfile io.github.RobbyBobby77.Refract flatpak run io.github.RobbyBobby77.Refract" + args)
        else if (refract === "native")
            shell.connectSource("kstart --desktopfile io.github.RobbyBobby77.Refract refract" + args)
        else
            Qt.openUrlExternally("https://github.com/RobbyBobby77/refract")
        root.expanded = false
    }

    compactRepresentation: MouseArea {
        id: compact
        readonly property bool vertical: Plasmoid.formFactor === PlasmaCore.Types.Vertical
        readonly property color blue: root.themeDark ? "#0A84FF" : "#007AFF"
        Layout.minimumWidth: vertical ? -1 : compactRow.implicitWidth
        Layout.minimumHeight: vertical ? width * 0.75 : -1
        hoverEnabled: true
        onClicked: root.expanded = !root.expanded

        RowLayout {
            id: compactRow
            anchors.fill: parent
            spacing: Kirigami.Units.smallSpacing
            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: height * 1.4
                Layout.margins: 2
                radius: 5
                color: Qt.rgba(compact.blue.r, compact.blue.g, compact.blue.b, 0.12)
                border.width: 1
                border.color: Qt.rgba(compact.blue.r, compact.blue.g, compact.blue.b, 0.38)
                clip: true
                Sparkline {
                    anchors.fill: parent
                    anchors.margins: 1
                    values: sensors.cpuHistory
                    color: compact.blue
                }
            }
            Text {
                visible: !compact.vertical
                text: Math.round(sensors.cpu || 0) + "%"
                color: Kirigami.Theme.textColor
                font.family: root.fontFamily
                font.weight: Font.DemiBold
                font.features: { "tnum": 1 }
                Layout.minimumWidth: metrics.width
                TextMetrics { id: metrics; text: "100%"; font.family: root.fontFamily; font.weight: Font.DemiBold }
            }
        }
    }

    fullRepresentation: GlassCard {
        stats: sensors
        glass: root.glass
        // The desktop's wallpaper, to frost behind the card.
        backdrop: root.glass && Plasmoid.containment ? Plasmoid.containment.wallpaperGraphicsObject : null
        // Forced light/dark only applies to our own glass; elsewhere follow Plasma.
        dark: !root.glass || root.cfg.appearance === 0 ? root.themeDark : root.cfg.appearance === 2
        labelColor: root.glass ? (dark ? "#FFFFFF" : "#000000") : Kirigami.Theme.textColor
        tinted: root.cfg.tinted
        showHeader: root.cfg.showHeader
        fontFamily: root.fontFamily
        Layout.minimumWidth: Kirigami.Units.gridUnit * 13
        Layout.preferredWidth: Kirigami.Units.gridUnit * 17
        Layout.minimumHeight: implicitHeight
        Layout.preferredHeight: implicitHeight
        onOpenRequested: device => root.openRefract(device)
    }
}
