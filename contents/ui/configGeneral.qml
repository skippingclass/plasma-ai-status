pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts

import org.kde.kcmutils as KCM
import org.kde.kirigami as Kirigami

KCM.SimpleKCM {
    id: root

    property string cfg_provider: "antigravity"
    property alias cfg_enableCliMonitoring: enableCliCheckBox.checked
    property alias cfg_pollInterval: pollIntervalSpin.value
    property alias cfg_customScriptPath: customScriptField.text

    Kirigami.FormLayout {
        QQC2.ComboBox {
            id: providerCombo
            Kirigami.FormData.label: i18n("Service:")
            textRole: "text"
            valueRole: "value"
            model: [
                { text: "Antigravity (GUI + CLI)", value: "antigravity" },
                { text: "OpenAI Codex", value: "codex" }
            ]
            currentIndex: root.cfg_provider === "codex" ? 1 : 0
            onActivated: root.cfg_provider = currentValue
        }
        QQC2.Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: i18n("Each widget has its own service. Add two widgets to monitor Antigravity and Codex together.")
        }


        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: i18n("Activity Monitoring")
        }

        QQC2.CheckBox {
            id: enableCliCheckBox
            Kirigami.FormData.label: i18n("Auto Monitor:")
            text: i18n("Automatically track activity and quotas for the selected service")
        }

        QQC2.SpinBox {
            id: pollIntervalSpin
            Kirigami.FormData.label: i18n("Poll Interval:")
            from: 1
            to: 60
            stepSize: 1
            enabled: enableCliCheckBox.checked
            textFromValue: value => value + " " + i18n("sec")
            valueFromText: text => parseInt(text) || 1
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: i18n("Custom Data Hook (Optional)")
        }

        QQC2.TextField {
            id: customScriptField
            Kirigami.FormData.label: i18n("Script Path:")
            placeholderText: i18n("/path/to/custom_script.py (outputs JSON)")
            Layout.fillWidth: true
        }
    }
}
