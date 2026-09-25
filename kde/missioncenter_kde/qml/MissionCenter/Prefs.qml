pragma Singleton
import QtQuick
import QtCore

// Persistent preferences (~/.config/MissionCenter/MissionCenterGlass.conf).
Settings {
    category: "Preferences"

    property int themeMode: 0            // 0 system, 1 light, 2 dark
    property string accent: "multicolor"
    property int glassStyle: 0           // 0 clear, 1 tinted
    property bool reduceTransparency: false
    property int backdropMode: 0         // 0 glass (blur-behind), 1 wallpaper, 2 solid
    property bool nativeDecorations: false
    property bool windowButtonsRight: true

    property int updateInterval: 1000
    property int processInterval: 2000   // 0 = every update
    property int graphPoints: 60
    property bool smoothGraphs: true
    property bool cpuPerCore: false
    property bool showKernelTime: true

    property bool decimalUnits: true     // GB vs GiB
    property bool networkBits: false     // Mbps vs MB/s
    property bool fahrenheit: false

    property bool processTree: false
    property bool showUserServices: false

    property int windowWidth: 1320
    property int windowHeight: 860
    property bool windowMaximized: false
    property string lastDevice: "cpu"
    property string lastPage: "performance"
}
