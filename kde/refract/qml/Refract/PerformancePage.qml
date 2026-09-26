import QtQuick

// Shows the detail view for the device selected in the sidebar.
Item {
    id: page

    property string device: "cpu"
    property real leftInset: 0

    function viewFor(key) {
        const sep = key.indexOf(":")
        const kind = sep < 0 ? key : key.slice(0, sep)
        const id = sep < 0 ? "" : key.slice(sep + 1)
        const ordinalOf = list => Math.max(0, list.findIndex(x => x.id === id))
        switch (kind) {
        case "memory": return ["MemoryView.qml", {}]
        case "disk": return ["DiskView.qml", { devId: id, ordinal: ordinalOf(Monitor.disks) }]
        case "net": return ["NetworkView.qml", { devId: id }]
        case "gpu": return ["GpuView.qml", { devId: id, ordinal: ordinalOf(Monitor.gpus) }]
        case "fan": return ["FanView.qml", { devId: id }]
        case "bat": return ["BatteryView.qml", { devId: id }]
        default: return ["CpuView.qml", {}]
        }
    }

    function reload() {
        const [file, props] = viewFor(device)
        loader.setSource(Qt.resolvedUrl(file), props)
        enter.restart()
    }

    onDeviceChanged: reload()
    Component.onCompleted: reload()

    Loader {
        id: loader
        anchors.fill: parent
        anchors.leftMargin: page.leftInset
        anchors.rightMargin: 22
        asynchronous: false
    }

    ParallelAnimation {
        id: enter
        NumberAnimation { target: loader; property: "opacity"; from: 0; to: 1; duration: 260; easing.type: Easing.OutCubic }
        NumberAnimation { target: loader; property: "anchors.topMargin"; from: 14; to: 0; duration: 380; easing.type: Easing.OutCubic }
    }
}
