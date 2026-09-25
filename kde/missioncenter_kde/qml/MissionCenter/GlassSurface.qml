import QtQuick
import QtQuick.Effects

// Liquid Glass: the navigation-layer material. It refracts and frosts the
// layered scene (Theme.glassSource) that sits behind it. Put it *outside*
// that scene – glass never samples itself.
Item {
    id: root

    property real radius: height / 2
    property Item source: Theme.glassSource
    property real refraction: 16
    property real bevel: Math.min(radius, 20)
    property real dispersion: 0.9
    property real frost: 9
    property real blurBias: 2.2
    property real saturation: 1.7
    property real specular: 1.0
    property real shine: 1.0
    property real press: 0
    property color tint: Theme.glassTint
    property color rimColor: Theme.glassRim
    property bool shadow: true
    property real shadowBlur: 26
    property real shadowOffset: 8
    property color shadowColor: Theme.shadow

    default property alias content: contentLayer.data
    readonly property alias contentItem: contentLayer

    RectangularShadow {
        anchors.fill: parent
        visible: root.shadow && root.opacity > 0
        radius: Math.min(root.radius, Math.min(width, height) / 2)
        blur: root.shadowBlur
        offset.y: root.shadowOffset
        spread: -4
        color: root.shadowColor
    }

    ShaderEffect {
        anchors.fill: parent
        visible: root.source !== null && width > 0 && height > 0
        property var source: root.source
        property real flipY: 1
        property size itemSize: Qt.size(width, height)
        property size sourceSize: root.source ? Qt.size(root.source.width, root.source.height) : Qt.size(1, 1)
        property real radius: root.radius
        property real bevel: root.bevel
        property real refraction: Theme.reduceTransparency ? 0 : root.refraction
        property real dispersion: root.dispersion
        property real frost: root.frost
        property real blurBias: root.blurBias
        property real saturation: root.saturation
        property real specular: root.specular
        property real shine: root.shine
        property real press: root.press
        property vector4d tint: Qt.vector4d(root.tint.r, root.tint.g, root.tint.b, root.tint.a)
        property vector4d rimColor: Qt.vector4d(root.rimColor.r, root.rimColor.g, root.rimColor.b, root.rimColor.a)
        vertexShader: ShaderDir + "glass.vert.qsb"
        fragmentShader: ShaderDir + "glass.frag.qsb"
    }

    Item {
        id: contentLayer
        anchors.fill: parent
    }
}
