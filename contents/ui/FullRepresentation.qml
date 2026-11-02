pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid

Item {
    id: root

    property string provider: "antigravity"
    property PixelTheme theme: PixelTheme {}

    required property string titleText
    required property string statusText
    required property string bar1Label
    required property int bar1Percent
    required property string bar2Label
    required property int bar2Percent
    required property string colorScheme

    property string themeName: "retro_pixel"
    property bool showTitleBar: true
    property bool enableAnimation: true
    property bool showExactPercent: false
    property bool showResetTimes: false
    property string barStyle: "auto"
    property string mascotSize: "auto"
    property real bar1Exact: 0.0
    property real bar2Exact: 0.0
    property string bar1Reset: ""
    property string bar2Reset: ""
    property string quotaIndicatorPosition: "header"
    property string quotaState: "hidden"
    property string quotaDescription: ""
    property bool bar1Dim: false
    property bool bar2Dim: false

    implicitWidth: 256
    implicitHeight: 288
    Layout.preferredWidth: 256
    Layout.preferredHeight: 288
    Layout.minimumWidth: 160
    Layout.minimumHeight: 160

    PixelWindow {
        id: windowFrame
        provider: root.provider
        theme: root.theme
        anchors.fill: parent
        anchors.margins: 1
        titleText: root.titleText
        statusText: root.statusText
        bar1Label: root.bar1Label
        bar1Percent: root.bar1Percent
        bar1Exact: root.bar1Exact
        bar1Reset: root.bar1Reset
        bar2Label: root.bar2Label
        bar2Percent: root.bar2Percent
        bar2Exact: root.bar2Exact
        bar2Reset: root.bar2Reset
        colorScheme: root.colorScheme
        themeName: root.themeName
        showTitleBar: root.showTitleBar
        enableAnimation: root.enableAnimation
        showExactPercent: root.showExactPercent
        showResetTimes: root.showResetTimes
        barStyle: root.barStyle
        mascotSize: root.mascotSize
        quotaIndicatorPosition: root.quotaIndicatorPosition
        quotaState: root.quotaState
        quotaDescription: root.quotaDescription
        bar1Dim: root.bar1Dim
        bar2Dim: root.bar2Dim
    }
}
