import QtQuick
import QtQuick.Effects

// "About Mission Center Glass": the brand, the version, and the credits.
Sheet {
    id: sheet

    preferredWidth: 460

    footer: [
        PillButton {
            text: "GitHub"
            tint: Theme.graphite
            onClicked: Monitor.launch("xdg-open", ["https://github.com/RobbyBobby77/mission-center-glass"])
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

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 10
            Text {
                text: "Mission Center"
                font.family: Theme.displayFamily
                font.pixelSize: 26
                font.weight: Font.Bold
                color: Theme.label
            }
            Text {
                id: glassWord
                text: "Glass"
                font.family: Theme.displayFamily
                font.pixelSize: 26
                font.weight: Font.Bold
                color: Theme.label
                visible: false
            }
            // the brand gradient (blue -> violet -> pink) through the word "Glass"
            Item {
                width: glassWord.implicitWidth
                height: glassWord.implicitHeight
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
                MultiEffect {
                    anchors.fill: parent
                    source: brandGradient
                    maskEnabled: true
                    maskSource: glassMask
                }
                ShaderEffectSource {
                    id: glassMask
                    sourceItem: glassWord
                    hideSource: true
                    visible: false
                }
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Version " + AppVersion + " · Liquid Glass edition"
            font.pixelSize: 13
            font.weight: Font.Medium
            color: Theme.secondaryLabel
        }

        Item { width: 1; height: 10 }

        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            text: "Your system at a glance — in Liquid Glass, for KDE Plasma."
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
                  + "\nBuilt on Mission Center by the Mission Center developers. "
                  + "Inter typeface by the Inter Project Authors (SIL OFL). "
                  + "Licensed under the GPL-3.0-or-later."
            font.pixelSize: 11
            color: Theme.tertiaryLabel
        }
    }
}
