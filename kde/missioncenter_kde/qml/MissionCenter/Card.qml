import QtQuick

// Content-layer panel: translucent fill with a lit hairline rim.
Item {
    id: card

    property real radius: Theme.cardRadius
    property real padding: 18
    property color fill: Theme.cardFill
    property color fillBottom: Theme.cardFillBottom
    property color rimColor: Theme.cardRim
    property real rimStrength: Theme.dark ? 0.55 : 0.9

    default property alias content: inner.data
    readonly property alias contentItem: inner

    ShaderEffect {
        anchors.fill: parent
        property size itemSize: Qt.size(width, height)
        property real radius: card.radius
        property real specular: card.rimStrength
        property vector4d fill: Qt.vector4d(card.fill.r, card.fill.g, card.fill.b, card.fill.a)
        property vector4d fillBottom: Qt.vector4d(card.fillBottom.r, card.fillBottom.g, card.fillBottom.b, card.fillBottom.a)
        property vector4d rimColor: Qt.vector4d(card.rimColor.r, card.rimColor.g, card.rimColor.b, card.rimColor.a)
        fragmentShader: ShaderDir + "panel.frag.qsb"
    }

    Item {
        id: inner
        anchors.fill: parent
        anchors.margins: card.padding
    }
}
