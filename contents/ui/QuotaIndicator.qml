pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls as QQC2

Item {
    id: root
    property PixelTheme theme: PixelTheme {}
    property string quotaState: "hidden"
    property string description: ""
    property bool inTitleBar: false
    objectName: "quotaIndicator"
    readonly property bool warning: ["low", "critical", "exhausted"].indexOf(quotaState) !== -1
    readonly property color warningColor: quotaState === "critical" || quotaState === "exhausted" ?
        theme.getStatusColor("ошибка") : (inTitleBar ? theme.textTitle : theme.textPrimary)
    implicitWidth: quotaState === "full" ? 6 : 10
    implicitHeight: quotaState === "full" ? 6 : 12
    width: implicitWidth
    height: implicitHeight
    visible: quotaState === "full" || warning
    Rectangle {
        anchors.centerIn: parent
        width: 6; height: 6
        radius: root.theme.isRounded ? 3 : 0
        visible: root.quotaState === "full"
        color: root.theme.activeColor
    }
    Item {
        anchors.centerIn: parent
        width: 3
        height: 11
        visible: root.warning
        Rectangle {
            width: 3; height: 6
            radius: root.theme.isRounded ? 1.5 : 0
            color: root.warningColor
        }
        Rectangle {
            anchors.bottom: parent.bottom
            width: 3; height: 3
            radius: root.theme.isRounded ? 1.5 : 0
            color: root.warningColor
        }
    }
    QQC2.ToolTip.visible: hover.containsMouse && description.length > 0
    QQC2.ToolTip.text: description
    QQC2.ToolTip.delay: 300
    MouseArea {
        id: hover
        anchors.fill: parent
        anchors.margins: -3
        acceptedButtons: Qt.NoButton
        hoverEnabled: true
    }
}
