pragma ComponentBehavior: Bound
import QtQuick

QtObject {
    property bool enabled: true
    property bool custom: false
    property bool refreshing: false
    property string error: ""
    property real now: Date.now() / 1000
    property real bar1Updated: 0
    property real bar2Updated: 0
    property int bar1Percent: -1
    property int bar2Percent: -1
    property real bar1Exact: bar1Percent
    property real bar2Exact: bar2Percent
    property bool lowWarning: true
    property int lowThreshold: 20
    property int criticalThreshold: 10
    property bool showFull: true
    property bool dimStale: true
    property string bar1Label: "5 часов"
    property string bar2Label: "неделя"

    readonly property bool visible: enabled && (!custom || bar1Updated > 0 || bar2Updated > 0)
    readonly property bool bar1Stale: bar1Percent >= 0 && (bar1Updated <= 0 || now - bar1Updated > 180)
    readonly property bool bar2Stale: bar2Percent >= 0 && (bar2Updated <= 0 || now - bar2Updated > 180)
    readonly property bool stale: bar1Stale || bar2Stale
    readonly property bool bar1Dim: dimStale && visible && bar1Percent >= 0 && (bar1Stale || error.length > 0)
    readonly property bool bar2Dim: dimStale && visible && bar2Percent >= 0 && (bar2Stale || error.length > 0)
    readonly property string state: !visible ? "hidden" : refreshing ? "refreshing" : error ? "error" : stale ? "stale" :
                                    (bar1Updated > 0 || bar2Updated > 0) ? "fresh" : "unknown"
    readonly property bool bar1Current: visible && !error && bar1Percent >= 0 && !bar1Stale
    readonly property bool bar2Current: visible && !error && bar2Percent >= 0 && !bar2Stale
    readonly property real lowest: Math.min(bar1Current ? bar1Exact : Infinity, bar2Current ? bar2Exact : Infinity)
    readonly property string indicatorState: lowWarning && lowest < 100 && lowest <= Math.max(0, Math.min(100, lowThreshold)) ?
        (lowest <= 0 ? "exhausted" : lowest < Math.max(0, Math.min(100, criticalThreshold)) ? "critical" : "low") :
        showFull && bar1Current && bar2Current && bar1Exact >= 100 && bar2Exact >= 100 ? "full" : "hidden"
    readonly property string description: {
        if (!visible) return "";
        const labels = {fresh: "Лимиты актуальны", refreshing: "Обновление лимитов…",
                        error: "Не удалось обновить лимиты", stale: "Данные лимитов устарели",
                        unknown: "Лимиты ещё не получены"};
        const quotaMessage = indicatorState === "full" ? "Оба лимита полностью доступны" :
                             indicatorState === "exhausted" ? "Лимит исчерпан" :
                             indicatorState === "critical" ? "Критический остаток лимита (< " + criticalThreshold + "%)" :
                             indicatorState === "low" ? "Низкий остаток лимита (≤ " + lowThreshold + "%)" : "";
        const lines = [labels[state]];
        if (quotaMessage) lines.push(quotaMessage);
        lines.push(describe(bar1Label, bar1Percent, bar1Updated), describe(bar2Label, bar2Percent, bar2Updated));
        if (error) lines.push(error);
        return lines.join("\n");
    }

    function describe(label, percent, updated) {
        if (percent < 0) return label + ": нет данных";
        if (updated <= 0) return label + ": время обновления неизвестно";
        const seconds = Math.max(0, Math.floor(now - updated));
        const age = seconds < 60 ? "только что" : seconds < 3600 ? Math.floor(seconds / 60) + " мин назад" :
                    seconds < 86400 ? Math.floor(seconds / 3600) + " ч назад" : Math.floor(seconds / 86400) + " дн назад";
        return label + ": обновлено " + age;
    }
}
