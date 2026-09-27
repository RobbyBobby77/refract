import QtQuick
import QtQuick.Effects

// "About Refract": the brand, the version, and the credits.
Sheet {
    id: sheet

    preferredWidth: 460

    footer: [
        PillButton {
            text: "GitHub"
            tint: Theme.graphite
            onClicked: Monitor.launch("xdg-open", ["https://github.com/RobbyBobby77/refract"])
        },
        PillButton {
            text: "Mission Center"
            tint: Theme.graphite
            onClicked: Monitor.launch("xdg-open", ["https://missioncenter.io"])
        },
        PillButton { text: "Done"; prominent: true; onClicked: sheet.close() }
    ]

    Column {
        width: parent.width
        spacing: 6

        Item {
            width: parent.width
            height: 150
            RectangularShadow {
                anchors.centerIn: icon
                width: icon.width * 0.84
                height: icon.height * 0.84
                radius: width * 0.24
                blur: 34
                offset.y: 14
                color: Qt.rgba(0, 0, 0, Theme.dark ? 0.55 : 0.28)
            }
            Image {
                id: icon
                anchors.horizontalCenter: parent.horizontalCenter
                width: 140
                height: 140
                source: AppIcon
                sourceSize: Qt.size(280, 280)
                smooth: true
            }
        }

        // the wordmark: "Refract" filled with the brand gradient (blue -> violet -> pink)
        Item {
            anchors.horizontalCenter: parent.horizontalCenter
            width: wordmark.implicitWidth
            height: wordmark.implicitHeight
            Text {
                id: wordmark
                text: "Refract"
                font.family: Theme.displayFamily
                font.pixelSize: 34
                font.weight: Font.Bold
                visible: false
            }
            Rectangle {
                id: brandGradient
                anchors.fill: parent
                visible: false
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: "#46A3FF" }
                    GradientStop { position: 0.5; color: "#A37BFF" }
                    GradientStop { position: 1; color: "#FF5A82" }
                }
            }
            ShaderEffectSource {
                id: wordmarkMask
                sourceItem: wordmark
                hideSource: true
                visible: false
            }
            MultiEffect {
                anchors.fill: parent
                source: brandGradient
                maskEnabled: true
                maskSource: wordmarkMask
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Version " + AppVersion + " · based on " + BasedOn
            font.pixelSize: 13
            font.weight: Font.Medium
            color: Theme.secondaryLabel
        }

        Item { width: 1; height: 10 }

        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            text: "Your system at a glance — through glass, for KDE Plasma."
            font.pixelSize: 14
            color: Theme.label
        }

        Item { width: 1; height: 8 }

        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            lineHeight: 1.25
            text: "Data engine: " + (Monitor.staticInfo.engine === "magpie" ? "magpie" : "built-in")
                  + (Monitor.staticInfo.desktop ? " · " + Monitor.staticInfo.desktop : "")
                  + "\nRefract is a modified version of Mission Center by the Mission Center developers, "
                  + "and is not affiliated with or endorsed by that project. "
                  + "Inter typeface by the Inter Project Authors (SIL OFL). "
                  + "Licensed under the GPL-3.0-or-later."
            font.pixelSize: 11
            color: Theme.tertiaryLabel
        }
    }
}
