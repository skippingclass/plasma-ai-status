pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls as QQC2

Rectangle {
    id: root
    property PixelTheme theme: PixelTheme {}
    property string quotaState: "hidden"
    property string description: ""
    objectName: "quotaIndicator"
    width: 6
    height: 6
    radius: theme.isRounded ? 3 : 0
    visible: quotaState !== "hidden"
    color: quotaState === "error" ? theme.getStatusColor("ошибка") :
           quotaState === "stale" ? "#e3b341" :
           quotaState === "refreshing" ? "#68b5f8" :
           quotaState === "fresh" ? theme.activeColor : theme.textMuted
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
