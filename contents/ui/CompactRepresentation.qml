pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    id: root

    property string provider: "antigravity"
    property PixelTheme theme: PixelTheme {}

    signal toggleRequested()

    property string statusText: "отдыхает"
    property int bar1Val: 99
    property string colorScheme: "green"
    property string quotaState: "hidden"
    property string quotaDescription: ""

    implicitWidth: Kirigami.Units.iconSizes.medium
    implicitHeight: Kirigami.Units.iconSizes.medium

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggleRequested()
    }

    Item {
        anchors.centerIn: parent
        width: 24
        height: 20

        PixelProviderLogo {
                            provider: root.provider
            anchors.centerIn: parent
            status: root.statusText
            pixelScale: 2
        }

        // Mini status dot in the bottom right corner
        QuotaIndicator {
            anchors.top: parent.top
            anchors.right: parent.right
            theme: root.theme
            quotaState: root.quotaState
            description: root.quotaDescription
        }
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            width: 5
            height: 5
            radius: root.theme.isRounded ? 2.5 : 0
            color: root.theme.getStatusColor(root.statusText)
            border.color: "#111116"
            border.width: 1
        }
    }
}
