import QtQuick

// Apple-style alert: a question, an explanation, and a destructive default.
Sheet {
    id: sheet

    property string message: ""
    property string confirmText: "Continue"
    property var callback: null

    function ask(titleText, messageText, buttonText, callback) {
        title = titleText
        message = messageText
        confirmText = buttonText
        sheet.callback = callback
        open()
    }

    preferredWidth: 440

    footer: [
        PillButton { text: "Cancel"; tint: Theme.graphite; onClicked: sheet.close() },
        PillButton {
            text: sheet.confirmText
            prominent: true
            tint: Theme.red
            onClicked: {
                sheet.close()
                if (sheet.callback) sheet.callback()
            }
        }
    ]

    Text {
        width: parent.width
        text: sheet.message
        wrapMode: Text.WordWrap
        font.pixelSize: 13
        color: Theme.secondaryLabel
    }
}
