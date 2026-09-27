import QtQuick
import org.kde.ksysguard.sensors as Sensors

// Plasma's system sensors (ksystemstats) and a short history of each, one
// sample a second, 40 points like Refract's sidebar. Plain QML, no Plasma
// APIs, so preview.py can run it outside plasmashell.
Item {
    id: stats
    visible: false

    property bool showCpu: true
    property bool showMemory: true
    property bool showDisk: true
    property bool showNetwork: true
    property bool showGpu: true

    readonly property var cpu: cpuUsage.value
    readonly property var cpuFrequency: cpuFreq.value
    readonly property var memoryUsed: memUsed.value
    readonly property var memoryTotal: memTotal.value
    readonly property var memoryPercent: memPercent.value
    readonly property var diskReadRate: diskRead.value
    readonly property var diskWriteRate: diskWrite.value
    readonly property var download: netDown.value
    readonly property var upload: netUp.value
    readonly property var gpu: gpuUsage.value
    readonly property var gpuTemperature: gpuTemp.value
    readonly property bool hasGpu: gpuUsage.name !== ""
    readonly property string hostName: hostname.value || ""

    readonly property int points: 40
    property var cpuHistory: blank()
    property var memoryHistory: blank()
    property var readHistory: blank()
    property var writeHistory: blank()
    property var downloadHistory: blank()
    property var uploadHistory: blank()
    property var gpuHistory: blank()

    function blank() { return new Array(points).fill(NaN) }
    function isNum(v) { return v !== undefined && v !== null && v !== "" && !isNaN(v) }
    function pushed(list, v) {
        const out = list.concat([isNum(v) ? Number(v) : NaN])
        return out.length > points ? out.slice(out.length - points) : out
    }

    Sensors.Sensor { id: cpuUsage; sensorId: "cpu/all/usage"; updateRateLimit: 1000 }
    Sensors.Sensor { id: cpuFreq; sensorId: "cpu/all/averageFrequency"; enabled: stats.showCpu; updateRateLimit: 1000 }
    Sensors.Sensor { id: memUsed; sensorId: "memory/physical/used"; enabled: stats.showMemory; updateRateLimit: 1000 }
    Sensors.Sensor { id: memTotal; sensorId: "memory/physical/total"; enabled: stats.showMemory }
    Sensors.Sensor { id: memPercent; sensorId: "memory/physical/usedPercent"; updateRateLimit: 1000 }
    Sensors.Sensor { id: diskRead; sensorId: "disk/all/read"; enabled: stats.showDisk; updateRateLimit: 1000 }
    Sensors.Sensor { id: diskWrite; sensorId: "disk/all/write"; enabled: stats.showDisk; updateRateLimit: 1000 }
    Sensors.Sensor { id: netDown; sensorId: "network/all/download"; enabled: stats.showNetwork; updateRateLimit: 1000 }
    Sensors.Sensor { id: netUp; sensorId: "network/all/upload"; enabled: stats.showNetwork; updateRateLimit: 1000 }
    Sensors.Sensor { id: gpuUsage; sensorId: "gpu/all/usage"; enabled: stats.showGpu; updateRateLimit: 1000 }
    Sensors.Sensor { id: gpuTemp; sensorId: "gpu/gpu0/temperature"; enabled: stats.showGpu; updateRateLimit: 1000 }
    Sensors.Sensor { id: hostname; sensorId: "os/system/hostname" }

    Timer {
        interval: 1000
        repeat: true
        running: true
        onTriggered: {
            // CPU and memory always: the panel icon and tooltip use them.
            stats.cpuHistory = stats.pushed(stats.cpuHistory, cpuUsage.value)
            stats.memoryHistory = stats.pushed(stats.memoryHistory, memPercent.value)
            if (stats.showDisk) {
                stats.readHistory = stats.pushed(stats.readHistory, diskRead.value)
                stats.writeHistory = stats.pushed(stats.writeHistory, diskWrite.value)
            }
            if (stats.showNetwork) {
                stats.downloadHistory = stats.pushed(stats.downloadHistory, netDown.value)
                stats.uploadHistory = stats.pushed(stats.uploadHistory, netUp.value)
            }
            if (stats.showGpu && stats.hasGpu)
                stats.gpuHistory = stats.pushed(stats.gpuHistory, gpuUsage.value)
        }
    }
}
