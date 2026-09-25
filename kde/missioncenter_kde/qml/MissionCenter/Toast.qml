import QtQuick
import org.kde.kirigami as Kirigami

// Transient glass notification ("Couldn't stop sshd.service …").
GlassSurface {
    id: toast

    property string message: ""
    property bool error: false

    function show(text, isError) {
        message = text
        error = isError
        shown = true
        hideTimer.restart()
    }

    property bool shown: false
    height: 44
    width: Math.min(row.implicitWidth + 36, parent ? parent.width - 80 : 600)
    radius: height / 2
    opacity: shown ? 1 : 0
    visible: opacity > 0
    Behavior on opacity { NumberAnimation { duration: 200 } }

    Timer { id: hideTimer; interval: toast.error ? 6000 : 3000; onTriggered: toast.shown = false }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 9
        Kirigami.Icon {
            anchors.verticalCenter: parent.verticalCenter
            width: 18; height: 18
            source: toast.error ? "dialog-warning" : "dialog-ok-apply"
            isMask: true
            color: toast.error ? Theme.orange : Theme.green
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(implicitWidth, toast.parent ? toast.parent.width - 150 : 500)
            text: toast.message
            font.pixelSize: 13
            font.weight: Font.Medium
            color: Theme.label
            elide: Text.ElideRight
            maximumLineCount: 1
        }
    }
    TapHandler { onTapped: toast.shown = false }
}
