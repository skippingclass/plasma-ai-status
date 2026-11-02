pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts

import org.kde.kcmutils as KCM
import org.kde.kirigami as Kirigami

KCM.SimpleKCM {
    id: root

    property string cfg_titleMode: "legacy"
    property string cfg_provider: "antigravity"
    property string cfg_quotaIndicatorPosition: "header"
    property alias cfg_lowQuotaWarning: lowWarningCheck.checked
    property alias cfg_lowQuotaThreshold: lowThresholdSpin.value
    property alias cfg_criticalQuotaThreshold: criticalThresholdSpin.value
    property alias cfg_fullQuotaIndicator: fullIndicatorCheck.checked
    property alias cfg_dimStaleQuotas: dimStaleCheck.checked
    property PixelTheme previewTheme: PixelTheme { activeThemeId: root.cfg_theme }
    property ProviderTitle previewTitle: ProviderTitle {
        objectName: "titlePreview"
        provider: root.cfg_provider
        rounded: root.previewTheme.isRounded
        mode: root.cfg_titleMode
        customText: root.cfg_titleText
    }
    property alias cfg_titleText: titleField.text
    property string cfg_colorScheme: colorSchemeCombo.currentValue
    property string cfg_theme: themeCombo.currentValue
    property alias cfg_showTitleBar: showTitleBarCheck.checked
    property alias cfg_enableAnimation: enableAnimationCheck.checked
    property alias cfg_showExactPercent: showExactPercentCheck.checked
    property alias cfg_showResetTimes: showResetTimesCheck.checked
    property string cfg_barStyle: barStyleCombo.currentValue
    property string cfg_mascotSize: mascotSizeCombo.currentValue

    Kirigami.FormLayout {

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: i18n("Theme & Palette")
        }

        QQC2.ComboBox {
            id: themeCombo
            Kirigami.FormData.label: i18n("Theme:")
            textRole: "text"
            valueRole: "value"
            model: [
                { text: i18n("Retro Pixel (Classic)"), value: "retro_pixel" },
                { text: i18n("Material 3 Expressive"), value: "material3" },
                { text: i18n("Cyberpunk 2077"), value: "cyberpunk" },
                { text: i18n("Windows 95 Classic"), value: "win95" },
                { text: i18n("Gruvbox Retro"), value: "gruvbox" },
                { text: i18n("Catppuccin Mocha"), value: "catppuccin" },
                { text: i18n("Tokyo Night"), value: "tokyo_night" }
            ]
            currentIndex: {
                for (let i = 0; i < count; i++) {
                    if (model[i].value === root.cfg_theme) return i;
                }
                return 0;
            }
            onActivated: root.cfg_theme = currentValue
        }

        QQC2.ComboBox {
            id: colorSchemeCombo
            Kirigami.FormData.label: i18n("Accent Color:")
            textRole: "text"
            valueRole: "value"
            model: [
                { text: i18n("Theme Default"), value: "green" },
                { text: i18n("Neon Cyan"), value: "cyan" },
                { text: i18n("Retro Amber"), value: "amber" }
            ]
            currentIndex: {
                for (let i = 0; i < count; i++) {
                    if (model[i].value === root.cfg_colorScheme) return i;
                }
                return 0;
            }
            onActivated: root.cfg_colorScheme = currentValue
        }

        QQC2.ComboBox {
            id: barStyleCombo
            Kirigami.FormData.label: i18n("Bar Style:")
            textRole: "text"
            valueRole: "value"
            model: [
                { text: i18n("Auto (Match Theme)"), value: "auto" },
                { text: i18n("Segmented Blocks (Retro)"), value: "segmented" },
                { text: i18n("Continuous Smooth (Pill)"), value: "continuous" }
            ]
            currentIndex: {
                for (let i = 0; i < count; i++) {
                    if (model[i].value === root.cfg_barStyle) return i;
                }
                return 0;
            }
            onActivated: root.cfg_barStyle = currentValue
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: i18n("Window Frame & Title")
        }

        QQC2.CheckBox {
            id: showTitleBarCheck
            Kirigami.FormData.label: i18n("Title Bar:")
            text: i18n("Show window title bar and icon")
        }

        QQC2.CheckBox {
            objectName: "automaticTitleCheck"
            Kirigami.FormData.label: i18n("Automatic Title:")
            text: i18n("Match the service and theme")
            checked: root.previewTitle.automatic
            enabled: showTitleBarCheck.checked
            onClicked: root.cfg_titleMode = checked ? "auto" : "custom"
        }
        QQC2.Label {
            visible: root.previewTitle.automatic
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: i18n("Current title: %1", root.previewTitle.text)
        }

        QQC2.TextField {
            id: titleField
            objectName: "customTitleField"
            Kirigami.FormData.label: i18n("Window Title:")
            placeholderText: i18n("Custom title (shown exactly as entered)")
            visible: !root.previewTitle.automatic
            enabled: showTitleBarCheck.checked
            Layout.fillWidth: true
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: i18n("Quota Indicators")
        }
        QQC2.ComboBox {
            Kirigami.FormData.label: i18n("Position:")
            textRole: "text"
            valueRole: "value"
            model: [
                {text: i18n("Title bar (status when title bar is hidden)"), value: "header"},
                {text: i18n("Next to activity status"), value: "status"},
                {text: i18n("Hidden"), value: "hidden"}
            ]
            currentIndex: root.cfg_quotaIndicatorPosition === "status" ? 1 : root.cfg_quotaIndicatorPosition === "hidden" ? 2 : 0
            onActivated: root.cfg_quotaIndicatorPosition = currentValue
        }
        QQC2.CheckBox {
            id: lowWarningCheck
            Kirigami.FormData.label: i18n("Low Quota:")
            text: i18n("Show ! when either limit is low")
            enabled: root.cfg_quotaIndicatorPosition !== "hidden"
        }
        QQC2.SpinBox {
            id: lowThresholdSpin
            Kirigami.FormData.label: i18n("Warning Threshold:")
            from: 0
            to: 100
            enabled: lowWarningCheck.checked && root.cfg_quotaIndicatorPosition !== "hidden"
            textFromValue: value => value + "%"
            valueFromText: text => parseInt(text) || 0
        }
        QQC2.SpinBox {
            id: criticalThresholdSpin
            Kirigami.FormData.label: i18n("Red Below:")
            from: 0
            to: 100
            enabled: lowWarningCheck.checked && root.cfg_quotaIndicatorPosition !== "hidden"
            textFromValue: value => value + "%"
            valueFromText: text => parseInt(text) || 0
        }
        QQC2.CheckBox {
            id: fullIndicatorCheck
            Kirigami.FormData.label: i18n("Full Quota:")
            text: i18n("Show a dot only when both limits are 100%")
            enabled: root.cfg_quotaIndicatorPosition !== "hidden"
        }
        QQC2.CheckBox {
            id: dimStaleCheck
            Kirigami.FormData.label: i18n("Stale Data:")
            text: i18n("Dim saved quotas when outdated or unavailable")
        }
        QQC2.Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: i18n("Normal quotas have no indicator. Freshness and errors remain in the tooltip. Indicators use current data only; panel widgets show them beside the logo.")
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: i18n("Mascot & Details")
        }

        QQC2.ComboBox {
            id: mascotSizeCombo
            Kirigami.FormData.label: i18n("Mascot Size:")
            textRole: "text"
            valueRole: "value"
            model: [
                { text: i18n("Auto (Bold / Prominent)"), value: "auto" },
                { text: i18n("Large (Max Hero)"), value: "large" },
                { text: i18n("Medium (Balanced)"), value: "medium" },
                { text: i18n("Small (Compact)"), value: "small" }
            ]
            currentIndex: {
                for (let i = 0; i < count; i++) {
                    if (model[i].value === root.cfg_mascotSize) return i;
                }
                return 0;
            }
            onActivated: root.cfg_mascotSize = currentValue
        }

        QQC2.CheckBox {
            id: enableAnimationCheck
            Kirigami.FormData.label: i18n("Animation:")
            text: i18n("Enable floating mascot levitation and shimmer")
        }

        QQC2.CheckBox {
            id: showExactPercentCheck
            Kirigami.FormData.label: i18n("Decimals:")
            text: i18n("Display exact percentages (e.g. 51.2%)")
        }

        QQC2.CheckBox {
            id: showResetTimesCheck
            Kirigami.FormData.label: i18n("Reset Times:")
            text: i18n("Show quota reset timer next to percentages (e.g. 47.2% (11м))")
        }
    }
}
