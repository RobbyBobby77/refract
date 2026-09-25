import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic

ApplicationWindow {
    id: win

    readonly property bool frameless: !Prefs.nativeDecorations
    readonly property bool maximized: visibility === Window.Maximized || visibility === Window.FullScreen
    readonly property real cornerRadius: frameless && !maximized ? Theme.windowRadius : 0
    readonly property bool showSidebar: page === "performance"
    readonly property real sidebarRight: showSidebar ? Theme.inset + Theme.sidebarWidth : 0
    property string page: StartupOptions.page || Prefs.lastPage || "performance"
    property string device: StartupOptions.device || Prefs.lastDevice || "cpu"

    width: StartupOptions.size ? parseInt(StartupOptions.size.split("x")[0]) : Prefs.windowWidth
    height: StartupOptions.size ? parseInt(StartupOptions.size.split("x")[1]) : Prefs.windowHeight
    minimumWidth: 940
    minimumHeight: 620
    visible: true
    title: "Mission Center"
    color: "transparent"
    background: null
    flags: frameless ? (Qt.Window | Qt.FramelessWindowHint) : Qt.Window
    font.family: Theme.fontFamily

    Binding { target: Theme; property: "glassSource"; value: scene }
    Binding { target: Monitor; property: "interval"; value: Prefs.updateInterval }
    Binding { target: Monitor; property: "activePage"; value: win.page }
    Binding { target: Monitor; property: "servicesUser"; value: Prefs.showUserServices }

    onPageChanged: if (!StartupOptions.screenshot) Prefs.lastPage = page
    onDeviceChanged: if (!StartupOptions.screenshot) Prefs.lastDevice = device
    onClosing: {
        if (!maximized && !StartupOptions.screenshot) {
            Prefs.windowWidth = width
            Prefs.windowHeight = height
        }
    }

    // Ask KWin to blur the desktop behind the see-through window, following
    // its rounded outline. Re-applied whenever that shape changes; the first
    // time once a frame is on screen, so the Wayland surface exists.
    function applyWindowEffects() {
        WindowEffects.apply(win, Theme.seeThrough, cornerRadius)
    }
    property bool effectsApplied: false
    onFrameSwapped: if (!effectsApplied) { effectsApplied = true; applyWindowEffects() }
    onWidthChanged: if (effectsApplied) Qt.callLater(applyWindowEffects)
    onHeightChanged: if (effectsApplied) Qt.callLater(applyWindowEffects)
    onCornerRadiusChanged: if (effectsApplied) Qt.callLater(applyWindowEffects)
    Connections {
        target: Theme
        function onSeeThroughChanged() { Qt.callLater(win.applyWindowEffects) }
    }

    // Keep the selected device valid when hardware comes and goes.
    Connections {
        target: Monitor.devices
        function onCountChanged() {
            if (Monitor.devices.rowOf(win.device) < 0 && Monitor.devices.count > 0)
                win.device = "cpu"
        }
    }

    Connections {
        target: Monitor
        function onActionFinished(what, ok, message) {
            toast.show(ok ? what : what + " failed" + (message ? ": " + message : ""), !ok)
        }
    }

    // =====================================================================
    // Actions shared by tables, menus, action bars and sheets
    // =====================================================================
    QtObject {
        id: actions

        function pidsOf(r) { return r.pids && r.pids.length ? r.pids : (r.pid ? [r.pid] : []) }
        function startsOf(r) { return r.starts || [] }
        function send(r, sig, what) { Monitor.signalProcesses(pidsOf(r), startsOf(r), sig, what + " “" + r.name + "”") }
        function quit(r) { send(r, "TERM", "Quit") }
        function forceQuit(r) {
            const n = pidsOf(r).length
            confirm.ask("Force quit “" + r.name + "”?",
                        "Any unsaved changes will be lost. "
                        + (n > 1 ? "All " + n + " processes will be terminated immediately." : "The process will be terminated immediately."),
                        "Force Quit",
                        () => send(r, "KILL", "Force quit"))
        }
        function pause(r) { send(r, "STOP", "Stopped") }
        function resume(r) { send(r, "CONT", "Resumed") }
        function processDetails(r) { procSheet.row = r; procSheet.open() }
        function processMenu(r, x, y) {
            const stopped = r.state === "Stopped"
            menu.items = [
                { text: "Details", icon: "help-about", action: () => processDetails(r) },
                { text: "Copy Name", icon: "edit-copy", action: () => Monitor.copy(r.name) },
                { text: "Copy PID", icon: "edit-copy", action: () => Monitor.copy(String(r.pid)) },
                { separator: true },
                stopped ? { text: "Continue", icon: "media-playback-start", action: () => resume(r) }
                        : { text: "Stop", icon: "media-playback-pause", action: () => pause(r) },
                { text: "Quit", icon: "application-exit", action: () => quit(r) },
                { text: "Force Quit", icon: "process-stop", destructive: true, action: () => forceQuit(r) }
            ]
            menu.popupAt(x, y)
        }

        function serviceDetails(r) { svcSheet.row = r; svcSheet.open() }
        function serviceAction(r, action) { Monitor.serviceAction(r.name, action, !!r.user) }
        function serviceMenu(r, x, y) {
            const running = r.activeState === "active" || r.activeState === "activating"
            menu.items = [
                { text: "Details & Logs", icon: "help-about", action: () => serviceDetails(r) },
                { text: "Copy Name", icon: "edit-copy", action: () => Monitor.copy(r.name) },
                { separator: true },
                running ? { text: "Stop", icon: "media-playback-stop", action: () => serviceAction(r, "stop") }
                        : { text: "Start", icon: "media-playback-start", action: () => serviceAction(r, "start") },
                { text: "Restart", icon: "view-refresh", action: () => serviceAction(r, "restart") },
                { separator: true },
                { text: "Enable", icon: "list-add", enabled: r.enabledState === "disabled", action: () => serviceAction(r, "enable") },
                { text: "Disable", icon: "list-remove", enabled: r.enabledState === "enabled", destructive: true, action: () => serviceAction(r, "disable") }
            ]
            menu.popupAt(x, y)
        }
    }

    // =====================================================================
    // Scene: everything the glass refracts. Rendered into a layer so the
    // navigation chrome above can sample it.
    // =====================================================================
    Item {
        id: scene
        anchors.fill: parent
        layer.enabled: true
        layer.mipmap: true
        layer.smooth: true

        Backdrop {
            anchors.fill: parent
            radius: win.cornerRadius
        }

        PerformancePage {
            id: perfPage
            anchors.fill: parent
            device: win.device
            leftInset: win.sidebarRight + 24
            opacity: win.page === "performance" ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: Theme.smooth; easing.type: Easing.OutCubic } }
        }

        Loader {
            id: appsPage
            anchors.fill: parent
            active: win.page === "apps" || opacity > 0
            source: "AppsPage.qml"
            opacity: win.page === "apps" ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: Theme.smooth; easing.type: Easing.OutCubic } }
        }
        Binding { target: appsPage.item; property: "actions"; value: actions; when: appsPage.item !== null }

        Loader {
            id: servicesPage
            anchors.fill: parent
            active: win.page === "services" || opacity > 0
            source: "ServicesPage.qml"
            opacity: win.page === "services" ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: Theme.smooth; easing.type: Easing.OutCubic } }
        }
        Binding { target: servicesPage.item; property: "actions"; value: actions; when: servicesPage.item !== null }
    }

    // =====================================================================
    // Navigation layer (Liquid Glass)
    // =====================================================================

    // Title-bar band: drag to move, double-click to zoom.
    Item {
        id: dragBand
        anchors.left: parent.left
        anchors.right: parent.right
        height: 62
        DragHandler {
            target: null
            enabled: win.frameless
            onActiveChanged: if (active) win.startSystemMove()
        }
        TapHandler {
            enabled: win.frameless
            onDoubleTapped: win.maximized ? win.showNormal() : win.showMaximized()
        }
    }

    Sidebar {
        id: sidebar
        x: win.showSidebar ? Theme.inset : -width - 30
        y: Theme.inset
        width: Theme.sidebarWidth
        height: win.height - 2 * Theme.inset
        current: win.device
        opacity: win.showSidebar ? 1 : 0
        visible: opacity > 0
        onActivated: key => win.device = key
        Behavior on x { SpringAnimation { spring: 2.6; damping: 0.34; epsilon: 0.3 } }
        Behavior on opacity { NumberAnimation { duration: Theme.smooth } }
    }

    WindowControls {
        visible: win.frameless
        window: win
        x: Theme.inset + 17
        y: Theme.inset + 17
    }

    SegmentedControl {
        id: pageSwitcher
        readonly property real zoneLeft: win.showSidebar ? win.sidebarRight : 110
        readonly property real zoneRight: win.width - trailingTools.width - Theme.inset - 16
        x: Math.round(Math.max(zoneLeft + 12, Math.min(zoneLeft + (win.width - zoneLeft - width) / 2, zoneRight - width)))
        y: Theme.inset + 2
        model: [
            { key: "performance", title: "Performance", iconSource: Qt.resolvedUrl("../../icons/speedometer-symbolic.svg") },
            { key: "apps", title: "Apps", iconSource: Qt.resolvedUrl("../../icons/overlapping-windows-symbolic.svg") },
            { key: "services", title: "Services", icon: "system-run-symbolic" }
        ]
        current: win.page
        onActivated: key => win.page = key
        Behavior on x { SpringAnimation { spring: 2.6; damping: 0.34; epsilon: 0.3 } }
    }

    Row {
        id: trailingTools
        anchors.right: parent.right
        anchors.rightMargin: Theme.inset + 8
        y: Theme.inset + 3
        spacing: 10

        GlassSearchField {
            id: appSearch
            visible: win.page === "apps"
            placeholder: "Search"
            onTextChanged: Monitor.processes.filterText = text
        }
        GlassSearchField {
            id: serviceSearch
            visible: win.page === "services"
            placeholder: "Search"
            onTextChanged: Monitor.services.filterText = text
        }
        GlassButton {
            iconName: "configure"
            tooltip: "Settings (Ctrl+,)"
            onClicked: settingsSheet.open()
        }
    }

    // Floating selection actions -------------------------------------------
    ActionBar {
        id: processBar
        readonly property var info: Monitor.processes.selectedInfo
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 30
        shown: win.page === "apps" && !!info.key && info.kind !== "section"
        title: info.name || ""
        iconSource: info.icon || Theme.executableIcon
        actions: [
            { text: "Details", icon: "help-about", action: () => actions.processDetails(processBar.info) },
            processBar.info.state === "Stopped"
                ? { text: "Continue", icon: "media-playback-start", action: () => actions.resume(processBar.info) }
                : { text: "Stop", icon: "media-playback-pause", action: () => actions.pause(processBar.info) },
            { text: "Quit", icon: "application-exit", action: () => actions.quit(processBar.info) },
            { text: "Force Quit", icon: "process-stop", prominent: true, action: () => actions.forceQuit(processBar.info) }
        ]
    }

    ActionBar {
        id: serviceBar
        readonly property var info: Monitor.services.selectedInfo
        readonly property bool running: info.activeState === "active" || info.activeState === "activating"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 30
        shown: win.page === "services" && !!info.key
        title: (info.name || "").replace(/\.service$/, "").replace(/\\x2d/g, "-")
        iconSource: "system-run"
        actions: [
            { text: "Details & Logs", icon: "help-about", action: () => actions.serviceDetails(serviceBar.info) },
            { text: "Restart", icon: "view-refresh", action: () => actions.serviceAction(serviceBar.info, "restart") },
            serviceBar.info.enabledState === "enabled"
                ? { text: "Disable", icon: "list-remove", action: () => actions.serviceAction(serviceBar.info, "disable") }
                : { text: "Enable", icon: "list-add", enabled: serviceBar.info.enabledState === "disabled",
                    action: () => actions.serviceAction(serviceBar.info, "enable") },
            serviceBar.running
                ? { text: "Stop", icon: "media-playback-stop", prominent: true, action: () => actions.serviceAction(serviceBar.info, "stop") }
                : { text: "Start", icon: "media-playback-start", action: () => actions.serviceAction(serviceBar.info, "start") }
        ]
    }

    Toast {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: (processBar.shown || serviceBar.shown ? 96 : 30) + (shown ? 0 : -16)
        Behavior on anchors.bottomMargin { SpringAnimation { spring: 3; damping: 0.35; epsilon: 0.3 } }
    }

    // =====================================================================
    // Window edges (frameless only)
    // =====================================================================
    ResizeFrame {
        anchors.fill: parent
        window: win
        enabled: win.frameless && !win.maximized
    }

    // Popups ----------------------------------------------------------------
    GlassMenu { id: menu }
    SettingsSheet { id: settingsSheet }
    ProcessDetailsSheet { id: procSheet; onQuitRequested: r => actions.quit(r) }
    ServiceDetailsSheet { id: svcSheet; onActionRequested: a => actions.serviceAction(svcSheet.row, a) }
    ConfirmSheet { id: confirm }

    // Keyboard ---------------------------------------------------------------
    Shortcut { sequence: "Ctrl+1"; onActivated: win.page = "performance" }
    Shortcut { sequence: "Ctrl+2"; onActivated: win.page = "apps" }
    Shortcut { sequence: "Ctrl+3"; onActivated: win.page = "services" }
    Shortcut { sequence: "Ctrl+,"; onActivated: settingsSheet.open() }
    Shortcut {
        sequence: StandardKey.Find
        onActivated: {
            if (win.page === "performance") win.page = "apps"
            Qt.callLater(() => (win.page === "services" ? serviceSearch : appSearch).focusField())
        }
    }
    Shortcut {
        sequence: "Delete"
        enabled: win.page === "apps" && processBar.shown
        onActivated: actions.quit(processBar.info)
    }
    Shortcut {
        sequence: "Escape"
        enabled: !appSearch.editing && !serviceSearch.editing   // Esc in a field clears it instead
        onActivated: {
            Monitor.processes.select("")
            Monitor.services.select("")
        }
    }
    Shortcut { sequences: [StandardKey.Quit, "Ctrl+W"]; onActivated: win.close() }
}
