import QtQuick

// Load Kirigami only on Plasma; Windows uses Qt's bundled image support.
Item {
    id: icon
    property var source: ""
    property color color: "white"
    property bool isMask: false
    property string fallback: "application-x-executable"
    Loader {
        id: loader
        anchors.fill: parent
        source: IsWindows ? "PortableIcon.qml" : "PlasmaIcon.qml"
    }
    Binding { target: loader.item; property: "source"; value: icon.source; when: loader.status === Loader.Ready }
    Binding { target: loader.item; property: "color"; value: icon.color; when: loader.status === Loader.Ready }
    Binding { target: loader.item; property: "isMask"; value: icon.isMask; when: loader.status === Loader.Ready }
    Binding { target: loader.item; property: "fallback"; value: icon.fallback; when: loader.status === Loader.Ready }
}
