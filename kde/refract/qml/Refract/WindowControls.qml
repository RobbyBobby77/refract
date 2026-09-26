import QtQuick
import QtQuick.Window

// macOS-style "traffic light" window controls.
Row {
    id: controls

    required property Window window
    // On the right, use KDE's order so close sits in the corner.
    property bool mirrored: false
    spacing: 9

    readonly property bool active: window.active
    HoverHandler { id: groupHover }

    Repeater {
        model: {
            const lights = [
                { kind: "close", color: "#FF5F57", ring: "#E0443E", glyph: "close" },
                { kind: "minimize", color: "#FEBC2E", ring: "#DEA123", glyph: "minimize" },
                { kind: "zoom", color: "#28C840", ring: "#1AAB29", glyph: "zoom" }
            ]
            return controls.mirrored ? [lights[1], lights[2], lights[0]] : lights
        }
        delegate: Rectangle {
            id: light
            required property var modelData
            width: 13; height: 13; radius: 6.5
            color: controls.active || groupHover.hovered ? modelData.color
                 : (Theme.dark ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(0, 0, 0, 0.13))
            border.width: 0.5
            border.color: controls.active || groupHover.hovered ? modelData.ring : "transparent"
            scale: tap.pressed ? 0.88 : 1
            Behavior on scale { NumberAnimation { duration: 90 } }

            // glyphs, drawn with rectangles so they stay crisp at any scale
            Item {
                anchors.centerIn: parent
                width: 7; height: 7
                visible: groupHover.hovered
                opacity: 0.62
                Rectangle { // close: ×
                    visible: light.modelData.glyph === "close"
                    anchors.centerIn: parent; width: 8; height: 1.4; radius: 0.7
                    rotation: 45; color: "#4d0000"
                }
                Rectangle {
                    visible: light.modelData.glyph === "close"
                    anchors.centerIn: parent; width: 8; height: 1.4; radius: 0.7
                    rotation: -45; color: "#4d0000"
                }
                Rectangle { // minimize: −
                    visible: light.modelData.glyph === "minimize"
                    anchors.centerIn: parent; width: 8; height: 1.5; radius: 0.75
                    color: "#5a3a00"
                }
                Canvas { // zoom: two triangles
                    visible: light.modelData.glyph === "zoom"
                    anchors.centerIn: parent
                    width: 8; height: 8
                    onPaint: {
                        const ctx = getContext("2d")
                        ctx.reset()
                        ctx.fillStyle = "#0a4a00"
                        ctx.beginPath(); ctx.moveTo(1, 1); ctx.lineTo(5.6, 1); ctx.lineTo(1, 5.6); ctx.closePath(); ctx.fill()
                        ctx.beginPath(); ctx.moveTo(7, 7); ctx.lineTo(2.4, 7); ctx.lineTo(7, 2.4); ctx.closePath(); ctx.fill()
                    }
                }
            }

            TapHandler {
                id: tap
                onTapped: {
                    const w = controls.window
                    if (light.modelData.kind === "close") w.close()
                    else if (light.modelData.kind === "minimize") w.showMinimized()
                    else if (w.visibility === Window.Maximized) w.showNormal()
                    else w.showMaximized()
                }
            }
        }
    }
}
