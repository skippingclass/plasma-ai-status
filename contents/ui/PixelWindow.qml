pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid

Rectangle {
    id: root

    property string provider: "antigravity"
    property PixelTheme theme: PixelTheme {}

    property string titleText: "antigravity.sh"
    property string statusText: "отдыхает"
    property string bar1Label: "5 часов"
    property int bar1Percent: 72
    property real bar1Exact: 72.0
    property string bar1Reset: ""
    property string bar2Label: "неделя"
    property int bar2Percent: 95
    property real bar2Exact: 95.0
    property string bar2Reset: ""
    property string colorScheme: "green"
    property string themeName: "retro_pixel"
    property bool showTitleBar: true
    property bool enableAnimation: true
    property bool showExactPercent: false
    property bool showResetTimes: false
    property string barStyle: "auto"
    property string mascotSize: "auto"
    property string quotaState: "hidden"
    property string quotaDescription: ""
    property bool bar1Dim: false
    property bool bar2Dim: false

    implicitWidth: 256
    implicitHeight: 288

    // Fill parent if available
    width: parent ? parent.width : implicitWidth
    height: parent ? parent.height : implicitHeight

    color: root.theme.windowBg
    radius: root.theme.windowRadius
    clip: root.theme.windowRadius > 0

    // Retro / Expressive window frame border
    border.color: root.theme.frameBorder
    border.width: root.theme.frameBorderWidth

    // Top highlight line for 3D bevel retro effect
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: root.theme.frameHighlight
        visible: root.theme.frameHighlight !== "transparent"
        z: 2
    }

    // Proportional dimensions
    readonly property int titleBarHeight: root.showTitleBar ? Math.max(22, Math.min(38, Math.round(root.height * 0.11))) : 0
    readonly property int availableBodyHeight: Math.max(50, root.height - titleBarHeight)
    readonly property real spacingScale: Math.max(0.8, Math.min(2.5, root.height / 220.0))

    // Reserve room for status, both bars and padding before choosing a logo size.
    readonly property int dynamicMascotScale: {
        const fraction = root.mascotSize === "small" ? 0.26 : root.mascotSize === "large" ? 0.40 : 0.31;
        const requested = Math.floor(availableBodyHeight * fraction / 10);
        const heightBudget = Math.floor((availableBodyHeight - 48 * spacingScale - (enableAnimation ? 8 : 0)) / 23);
        const widthBudget = Math.floor((root.width - 2 * horizPadding) / 12);
        return Math.max(2, Math.min(13, requested, heightBudget, widthBudget));
    }

    // Dynamic font and bar sizes
    readonly property int titleFontSize: Math.max(10, Math.min(16, Math.round(Math.max(22, root.height * 0.11) * 0.50)))
    readonly property int statusFontSize: Math.max(11, Math.min(22, Math.round(dynamicMascotScale * 2.2)))
    readonly property int barFontSize: Math.max(9, Math.min(18, Math.round(dynamicMascotScale * 1.8)))
    readonly property int barHeight: Math.max(10, Math.min(24, Math.round(dynamicMascotScale * 2.0)))
    readonly property int horizPadding: Math.max(10, Math.min(32, Math.round(root.width * 0.055)))

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Title Bar
        Rectangle {
            visible: root.showTitleBar
            Layout.fillWidth: true
            implicitHeight: root.titleBarHeight
            color: root.theme.headerBg
            // Rounded top corners for Material 3 / Catppuccin
            radius: root.theme.headerRadius

            // Bottom mask for rounded header so only top corners are round
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: root.theme.headerRadius
                color: root.theme.headerBg
                visible: root.theme.headerRadius > 0
            }

            Rectangle {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: root.theme.headerBorder
                visible: root.theme.headerBorder !== "transparent"
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Math.max(8, Math.round(8 * root.spacingScale))
                anchors.rightMargin: Math.max(8, Math.round(8 * root.spacingScale))
                spacing: Math.max(6, Math.round(6 * root.spacingScale))

                // Left mini icon: always clean, crisp and static (never bounces in titlebar)
                Item {
                    readonly property int iconScale: Math.max(1, Math.round(root.titleBarHeight / 22))
                    implicitWidth: 12 * iconScale
                    implicitHeight: 10 * iconScale

                    PixelProviderLogo {
                            provider: root.provider
                        anchors.centerIn: parent
                        pixelScale: parent.iconScale
                        animated: false
                        status: "отдыхает"
                    }
                }

                Text {
                    text: root.theme.isRounded && (root.titleText === "antigravity.sh" || root.titleText === "codex.sh") ? (root.provider === "codex" ? "Codex" : "Antigravity") : root.titleText
                    font.family: root.theme.pixelFontFamily
                    font.pixelSize: root.titleFontSize
                    font.weight: root.theme.isRounded ? Font.DemiBold : Font.Normal
                    font.letterSpacing: root.theme.isRounded ? 0.2 : 0
                    color: root.theme.textTitle
                    renderType: root.theme.isPixelFont ? Text.NativeRendering : Text.QtRendering
                    antialiasing: !root.theme.isPixelFont
                }

                Item {
                    Layout.fillWidth: true
                }
            }
        }

        // 2. Main Window Body
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: root.horizPadding
                anchors.rightMargin: root.horizPadding
                spacing: 0

                // Top flexible spacer: generous minimum breathing room so mascot never touches the top
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: Math.max(8, Math.round(12 * root.spacingScale))
                    Layout.maximumHeight: Math.round(26 * root.spacingScale)
                }

                // Mascot & Status Area
                ColumnLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: Math.max(4, Math.round(6 * root.spacingScale))

                    Item {
                        Layout.alignment: Qt.AlignHCenter
                        objectName: "mascotSlot"
                        implicitWidth: mascot.implicitWidth
                        implicitHeight: mascot.implicitHeight

                        PixelProviderLogo {
                            provider: root.provider
                            id: mascot
                            anchors.centerIn: parent
                            status: root.statusText
                            pixelScale: root.dynamicMascotScale
                            animated: root.enableAnimation
                        }
                    }

                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: root.statusText
                        font.family: root.theme.pixelFontFamily
                        font.pixelSize: root.statusFontSize
                        font.weight: root.theme.isRounded ? Font.DemiBold : Font.Normal
                        font.letterSpacing: root.theme.isRounded ? 0.3 : 0
                        color: root.statusText === "спит" ? root.theme.textMuted : root.theme.getStatusColor(root.statusText)
                        renderType: root.theme.isPixelFont ? Text.NativeRendering : Text.QtRendering
                        antialiasing: !root.theme.isPixelFont
                    }
                }

                // Middle flexible spacer (between status and bars)
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 6
                    Layout.maximumHeight: Math.round(28 * root.spacingScale)
                }

                // Progress Bars Section
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Math.max(4, Math.round(6 * root.spacingScale))

                    PixelProgressBar {
                        objectName: "quotaBar1"
                        theme: root.theme
                        Layout.fillWidth: true
                        isSecondBar: false
                        label: root.bar1Label
                        percent: root.bar1Percent
                        exactPercent: root.bar1Exact
                        resetTime: root.bar1Reset
                        showExact: root.showExactPercent
                        showReset: root.showResetTimes
                        barStyle: root.barStyle
                        colorScheme: root.colorScheme
                        fontSize: root.barFontSize
                        barHeight: root.barHeight
                        dimmed: root.bar1Dim
                        quotaState: root.quotaState
                        quotaDescription: root.quotaDescription
                    }

                    PixelProgressBar {
                        objectName: "quotaBar2"
                        theme: root.theme
                        Layout.fillWidth: true
                        isSecondBar: true
                        dimmed: root.bar2Dim
                        label: root.bar2Label
                        percent: root.bar2Percent
                        exactPercent: root.bar2Exact
                        resetTime: root.bar2Reset
                        showExact: root.showExactPercent
                        showReset: root.showResetTimes
                        barStyle: root.barStyle
                        colorScheme: root.colorScheme
                        fontSize: root.barFontSize
                        barHeight: root.barHeight
                    }
                }

                // Bottom flexible spacer
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 6
                    Layout.maximumHeight: Math.round(22 * root.spacingScale)
                }
            }
        }
    }
}
