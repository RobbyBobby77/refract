import QtQuick

// The window background: desktop wallpaper, heavily blurred and tinted, clipped
// to the window's rounded shape. This is what the glass refracts.
Item {
    id: root

    property real radius: Theme.windowRadius
    readonly property string imageUrl: Prefs.backdropMode === 0
        ? (Theme.dark ? Monitor.wallpaperDark : Monitor.wallpaperLight) : ""

    Image {
        id: img
        source: root.imageUrl
        sourceSize.width: 1600
        asynchronous: true
        mipmap: true
        smooth: true
        visible: false
    }

    ShaderEffect {
        anchors.fill: parent
        property var source: img
        property size itemSize: Qt.size(width, height)
        property size imageSize: Qt.size(Math.max(img.implicitWidth, 1), Math.max(img.implicitHeight, 1))
        property real radius: root.radius
        property real blurBias: 4.5
        property real useImage: img.status === Image.Ready && root.imageUrl !== "" ? 1 : 0
        property real saturation: Theme.dark ? 1.3 : 1.2
        property real grain: 0.014
        property vector4d overlay: Qt.vector4d(Theme.windowOverlay.r, Theme.windowOverlay.g, Theme.windowOverlay.b, Theme.windowOverlay.a)
        property vector4d c1: Theme.dark ? Qt.vector4d(0.30, 0.22, 0.75, 1) : Qt.vector4d(0.55, 0.60, 1.0, 1)
        property vector4d c2: Theme.dark ? Qt.vector4d(0.75, 0.20, 0.45, 1) : Qt.vector4d(1.0, 0.62, 0.78, 1)
        property vector4d c3: Theme.dark ? Qt.vector4d(0.10, 0.45, 0.55, 1) : Qt.vector4d(0.55, 0.92, 0.88, 1)
        property vector4d c4: Theme.dark ? Qt.vector4d(0.05, 0.05, 0.09, 1) : Qt.vector4d(0.80, 0.82, 0.90, 1)
        fragmentShader: ShaderDir + "backdrop.frag.qsb"
    }
}
