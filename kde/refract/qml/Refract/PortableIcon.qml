import QtQuick
import QtQuick.Window

Item {
    id: icon
    property var source: ""
    property color color: "white"
    property bool isMask: false
    property string fallback: "application-x-executable"
    Image {
        anchors.fill: parent
        source: {
            const name = String(icon.source || "")
            return name === "" ? "" : "image://platformicons/" + encodeURIComponent(name)
                + (icon.isMask ? "?color=" + encodeURIComponent(String(icon.color)) : "")
        }
        fillMode: Image.PreserveAspectFit
        sourceSize: Qt.size(width * Screen.devicePixelRatio, height * Screen.devicePixelRatio)
    }
}
