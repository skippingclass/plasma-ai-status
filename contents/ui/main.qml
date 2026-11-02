/*
 * SPDX-FileCopyrightText: 2026 pirkov
 * SPDX-License-Identifier: MIT
 */
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore

PlasmoidItem {
    id: root

    readonly property bool isPlanar: Plasmoid.formFactor === PlasmaCore.Types.Planar
    
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    readonly property string provider: Plasmoid.configuration.provider === "codex" ? "codex" : "antigravity"
    readonly property string providerName: provider === "codex" ? "Codex" : "Antigravity"

    PixelTheme {
        id: visualTheme
        activeThemeId: root.currentTheme
    }

    // Per-instance provider monitor
    AntigravityMonitor {
        id: monitor
    }

    ProviderTitle {
        id: resolvedTitle
        provider: root.provider
        rounded: visualTheme.isRounded
        mode: Plasmoid.configuration.titleMode || "legacy"
        customText: Plasmoid.configuration.titleText
    }
    readonly property string currentTitle: resolvedTitle.text
    readonly property string currentStatus: monitor.currentStatus
    readonly property string currentBar1Label: monitor.bar1Label
    readonly property int currentBar1Val: monitor.bar1Val
    readonly property real currentBar1Exact: monitor.bar1Exact
    readonly property string currentBar1Reset: monitor.bar1Reset
    readonly property string currentBar2Label: monitor.bar2Label
    readonly property int currentBar2Val: monitor.bar2Val
    readonly property real currentBar2Exact: monitor.bar2Exact
    readonly property string currentBar2Reset: monitor.bar2Reset
    readonly property string currentColorScheme: Plasmoid.configuration.colorScheme
    readonly property string currentTheme: Plasmoid.configuration.theme ? Plasmoid.configuration.theme : "retro_pixel"
    toolTipMainText: root.providerName + ": " + root.currentStatus
    toolTipSubText: {
        const describe = (label, value, reset) => label + ": " + (value < 0 ? "нет данных" : value.toFixed(1) + "% осталось") + (reset ? " (сброс: " + reset + ")" : "");
        const lines = [describe(root.currentBar1Label, root.currentBar1Exact, root.currentBar1Reset),
                       describe(root.currentBar2Label, root.currentBar2Exact, root.currentBar2Reset)];
        if (monitor.freshness.description) lines.push(monitor.freshness.description);
        else if (monitor.quotaError) lines.push(monitor.quotaError);
        return lines.join("\n");
    }

    preferredRepresentation: isPlanar ? fullRepresentation : compactRepresentation

    Plasmoid.contextualActions: [
        PlasmaCore.Action {
            text: i18n("Обновить лимиты")
            icon.name: "view-refresh"
            enabled: monitor.canRefresh
            onTriggered: monitor.refreshQuotas()
        }
    ]

    compactRepresentation: CompactRepresentation {
        onToggleRequested: root.expanded = !root.expanded
        provider: root.provider
        theme: visualTheme
        statusText: root.currentStatus
        bar1Val: root.currentBar1Val
        colorScheme: root.currentColorScheme
        quotaState: Plasmoid.configuration.quotaIndicatorPosition === "hidden" ? "hidden" : monitor.freshness.indicatorState
        quotaDescription: monitor.freshness.description
    }

    fullRepresentation: FullRepresentation {
        provider: root.provider
        theme: visualTheme
        titleText: root.currentTitle
        statusText: root.currentStatus
        bar1Label: root.currentBar1Label
        bar1Percent: root.currentBar1Val
        bar1Exact: root.currentBar1Exact
        bar1Reset: root.currentBar1Reset
        bar2Label: root.currentBar2Label
        bar2Percent: root.currentBar2Val
        bar2Exact: root.currentBar2Exact
        bar2Reset: root.currentBar2Reset
        colorScheme: root.currentColorScheme
        themeName: root.currentTheme
        showTitleBar: Plasmoid.configuration.showTitleBar !== undefined ? Plasmoid.configuration.showTitleBar : true
        enableAnimation: Plasmoid.configuration.enableAnimation !== undefined ? Plasmoid.configuration.enableAnimation : true
        showExactPercent: Plasmoid.configuration.showExactPercent !== undefined ? Plasmoid.configuration.showExactPercent : false
        showResetTimes: Plasmoid.configuration.showResetTimes !== undefined ? Plasmoid.configuration.showResetTimes : false
        barStyle: Plasmoid.configuration.barStyle ? Plasmoid.configuration.barStyle : "auto"
        mascotSize: Plasmoid.configuration.mascotSize ? Plasmoid.configuration.mascotSize : "auto"
        quotaState: monitor.freshness.indicatorState
        quotaDescription: monitor.freshness.description
        quotaIndicatorPosition: Plasmoid.configuration.quotaIndicatorPosition || "header"
        bar1Dim: monitor.freshness.bar1Dim
        bar2Dim: monitor.freshness.bar2Dim
    }
}
