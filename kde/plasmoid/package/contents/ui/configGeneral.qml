import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kcmutils as KCM
import org.kde.kirigami as Kirigami

KCM.SimpleKCM {
    property alias cfg_showCpu: showCpu.checked
    property alias cfg_showMemory: showMemory.checked
    property alias cfg_showDisk: showDisk.checked
    property alias cfg_showNetwork: showNetwork.checked
    property alias cfg_showGpu: showGpu.checked
    property alias cfg_showHeader: showHeader.checked
    property alias cfg_appearance: appearance.currentIndex
    property alias cfg_tinted: tinted.checked
    // Plasma also hands over each setting's default.
    property bool cfg_showCpuDefault
    property bool cfg_showMemoryDefault
    property bool cfg_showDiskDefault
    property bool cfg_showNetworkDefault
    property bool cfg_showGpuDefault
    property bool cfg_showHeaderDefault
    property int cfg_appearanceDefault
    property bool cfg_tintedDefault

    Kirigami.FormLayout {
        QQC2.CheckBox { id: showCpu; Kirigami.FormData.label: i18n("Show:"); text: i18n("CPU") }
        QQC2.CheckBox { id: showMemory; text: i18n("Memory") }
        QQC2.CheckBox { id: showDisk; text: i18n("Disk") }
        QQC2.CheckBox { id: showNetwork; text: i18n("Network") }
        QQC2.CheckBox { id: showGpu; text: i18n("GPU") }
        QQC2.CheckBox { id: showHeader; text: i18n("Title and computer name") }

        Item { Kirigami.FormData.isSection: true }

        QQC2.ComboBox {
            id: appearance
            Kirigami.FormData.label: i18n("Appearance:")
            model: [i18n("Follow Plasma"), i18n("Light"), i18n("Dark")]
        }
        QQC2.CheckBox {
            id: tinted
            Kirigami.FormData.label: i18n("Glass:")
            text: i18n("Tinted (less see-through, more contrast)")
        }
    }
}
