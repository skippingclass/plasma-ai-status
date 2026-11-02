pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root

    property PixelTheme theme: PixelTheme {}

    property string label: "5 часов"
    property int percent: 99
    property real exactPercent: 99.0
    property string resetTime: ""
    property bool showExact: false
    property bool showReset: false
    property string barStyle: "auto"
    property bool isSecondBar: false
    property int totalSegments: 22
    property string colorScheme: "green"
    property int fontSize: 11
    property int barHeight: 12
    property bool dimmed: false
    property string quotaState: "hidden"
    property string quotaDescription: ""

    spacing: Math.max(2, Math.round(root.fontSize * 0.25))

    readonly property color activeColor: root.percent < 0 ? root.theme.textMuted : root.theme.getBarColor(root.isSecondBar, root.percent, root.colorScheme)
    readonly property color dimColor: root.percent < 0 ? root.theme.slotBg : root.theme.getBarDimColor(root.isSecondBar, root.percent, root.colorScheme)

    // Number of active filled blocks
    readonly property int activeCount: Math.max(0, Math.min(root.totalSegments, Math.round((root.percent / 100.0) * root.totalSegments)))

    // Label Row: "5 часов" on left, "осталось XX%" on right
    Item {
        Layout.fillWidth: true
        implicitHeight: Math.max(labelText.implicitHeight, valueText.implicitHeight)

        Text {
            id: labelText
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(implicitWidth, parent.width * 0.38)
            text: root.label
            elide: Text.ElideRight
            font.family: root.theme.pixelFontFamily
            font.pixelSize: root.fontSize
            font.weight: root.theme.isRounded ? Font.Medium : Font.Normal
            font.letterSpacing: root.theme.isRounded ? 0.1 : 0
            color: root.theme.textLabel
            renderType: root.theme.isPixelFont ? Text.NativeRendering : Text.QtRendering
            antialiasing: !root.theme.isPixelFont
        }

        Text {
            id: valueText
            anchors.left: labelText.right
            anchors.leftMargin: indicator.visible ? 18 : 8
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideRight
            text: {
                if (root.percent < 0) return "нет данных";
                const val = (root.showExact ? root.exactPercent.toFixed(1) : root.percent) + "%";
                if (root.showReset && root.resetTime) {
                    return val + " (" + root.resetTime + ")";
                }
                return "осталось " + val;
            }
            font.family: root.theme.pixelFontFamily
            font.pixelSize: root.fontSize
            font.weight: root.theme.isRounded ? Font.DemiBold : Font.Normal
            font.letterSpacing: root.theme.isRounded ? 0.2 : 0
            color: root.dimmed ? root.theme.textMuted : root.activeColor
            renderType: root.theme.isPixelFont ? Text.NativeRendering : Text.QtRendering
            antialiasing: !root.theme.isPixelFont
        }

        QuotaIndicator {
            id: indicator
            anchors.left: labelText.right
            anchors.leftMargin: 6
            anchors.verticalCenter: parent.verticalCenter
            theme: root.theme
            quotaState: root.quotaState
            description: root.quotaDescription
        }
    }

    // Bar Container
    Rectangle {
        objectName: "quotaFill"
        opacity: root.dimmed ? 0.45 : 1
        Layout.fillWidth: true
        implicitHeight: root.barHeight
        color: root.theme.slotBg
        border.color: root.theme.slotBorder
        border.width: (root.theme.slotBorder !== "transparent" && root.theme.slotBorder !== "") ? 1 : 0
        radius: root.theme.isRounded && !root.theme.isPixelFont ? height / 2 : root.theme.slotRadius

        // Material 3 Continuous Pill Mode vs Retro Segmented Mode
        Loader {
            anchors.fill: parent
            anchors.margins: root.theme.isRounded && !root.theme.isPixelFont ? 2 : 1
            sourceComponent: {
                if (root.barStyle === "continuous") return continuousBarComp;
                if (root.barStyle === "segmented") return segmentedBarComp;
                return (root.theme.isRounded && !root.theme.isPixelFont) ? continuousBarComp : segmentedBarComp;
            }
        }

        // 1. Continuous Pill Progress Bar (Material 3 Expressive, Catppuccin, Tokyo Night)
        Component {
            id: continuousBarComp

            Item {
                anchors.fill: parent

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: Math.max(0, Math.min(parent.width, (root.percent / 100.0) * parent.width))
                    color: root.activeColor
                    radius: height / 2

                    Behavior on width {
                        NumberAnimation { duration: 250; easing.type: Easing.OutCubic }
                    }
                }
            }
        }

        // 2. Retro Pixel Segmented Bar (Retro Pixel, Windows 95, Cyberpunk, Gruvbox)
        Component {
            id: segmentedBarComp

            RowLayout {
                anchors.fill: parent
                spacing: 1

                Repeater {
                    model: root.totalSegments

                    Rectangle {
                        required property int index
                        readonly property bool isActive: index < root.activeCount

                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: isActive ? root.activeColor : root.dimColor
                        radius: root.theme.slotRadius > 0 ? 1 : 0

                        // Pixel 3D top shine
                        Rectangle {
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            height: Math.max(1, Math.round(root.barHeight * 0.15))
                            color: parent.isActive ? Qt.rgba(1, 1, 1, 0.4) : "transparent"
                        }
                    }
                }
            }
        }
    }
}
