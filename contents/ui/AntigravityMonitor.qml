pragma ComponentBehavior: Bound

import QtQuick
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.plasma.plasmoid

Item {
    id: root

    property var configuration: Plasmoid.configuration
    property var executeCommand: (source, command) => source.connectSource(command)

    property bool monitoringEnabled: root.configuration.enableCliMonitoring
    property int intervalSec: Math.max(1, root.configuration.pollInterval)
    property string customScript: root.configuration.customScriptPath

    property string currentStatus: root.configuration.statusText
    property int bar1Val: monitoringEnabled ? -1 : root.configuration.bar1Percent
    property int bar2Val: monitoringEnabled ? -1 : root.configuration.bar2Percent
    property string bar1Label: root.configuration.bar1Label
    property string bar2Label: root.configuration.bar2Label
    property real bar1Exact: bar1Val
    property real bar2Exact: bar2Val
    property string bar1Reset: ""
    property string bar2Reset: ""

    readonly property string scriptPath: Qt.resolvedUrl("../scripts/status_provider.py").toString().replace(/^file:\/\//, "")

    property bool ready: false
    property string provider: root.configuration.provider === "codex" ? "codex" : "antigravity"
    property string quotaError: ""
    readonly property bool quotaStale: freshness.stale
    property bool backgroundRefreshing: false
    property string refreshCommand: ""
    property string refreshProvider: ""
    property int refreshGeneration: -1
    property real lastManualAt: 0
    property string lastManualProvider: ""
    readonly property bool canRefresh: ready && monitoringEnabled && !customScript && !refreshCommand &&
        (lastManualProvider !== provider || freshness.now - lastManualAt >= 5)
    property QuotaFreshness freshness: QuotaFreshness {
        enabled: root.monitoringEnabled
        custom: root.customScript.length > 0
        refreshing: root.backgroundRefreshing || (root.refreshCommand.length > 0 && root.refreshProvider === root.provider)
        error: root.quotaError
        lowWarning: root.configuration.lowQuotaWarning !== false
        lowThreshold: root.configuration.lowQuotaThreshold !== undefined ? root.configuration.lowQuotaThreshold : 20
        criticalThreshold: root.configuration.criticalQuotaThreshold !== undefined ? root.configuration.criticalQuotaThreshold : 10
        showFull: root.configuration.fullQuotaIndicator !== false
        dimStale: root.configuration.dimStaleQuotas !== false
        bar1Exact: root.bar1Exact
        bar2Exact: root.bar2Exact
        bar1Percent: root.bar1Val
        bar2Percent: root.bar2Val
        bar1Label: root.bar1Label
        bar2Label: root.bar2Label
    }
    property string activeCommand: ""
    property string activeProvider: ""
    property int generation: 0
    property int activeGeneration: -1

    function shellQuote(value) {
        return "'" + value.replace(/'/g, "'\\''") + "'";
    }

    function applyQuota(parsed) {
        root.bar1Val = parsed.bar1_percent !== undefined ? Number(parsed.bar1_percent) : -1;
        root.bar2Val = parsed.bar2_percent !== undefined ? Number(parsed.bar2_percent) : -1;
        root.bar1Exact = parsed.bar1_exact !== undefined ? Number(parsed.bar1_exact) : root.bar1Val;
        root.bar2Exact = parsed.bar2_exact !== undefined ? Number(parsed.bar2_exact) : root.bar2Val;
        root.bar1Reset = parsed.bar1_reset || resetCountdown(parsed.bar1_resets_at);
        root.bar2Reset = parsed.bar2_reset || resetCountdown(parsed.bar2_resets_at);
        root.bar1Label = parsed.bar1_label || "5 часов";
        root.bar2Label = parsed.bar2_label || "неделя";
        root.freshness.bar1Updated = Number(parsed.bar1_updated_at || parsed.timestamp || 0);
        root.freshness.bar2Updated = Number(parsed.bar2_updated_at || parsed.timestamp || 0);
        root.backgroundRefreshing = parsed.quota_refreshing || false;
    }

    function resetCountdown(timestamp) {
        if (!timestamp) return "";
        const minutes = Math.floor((Number(timestamp) * 1000 - Date.now()) / 60000);
        if (minutes <= 0) return "скоро";
        if (minutes >= 1440) return Math.floor(minutes / 1440) + "д " + Math.floor(minutes % 1440 / 60) + "ч";
        if (minutes >= 60) return Math.floor(minutes / 60) + "ч " + minutes % 60 + "м";
        return minutes + "м";
    }

    function savedQuotas() {
        try {
            const saved = JSON.parse(root.configuration.lastKnownQuotas || "{}");
            return saved && typeof saved === "object" ? saved : {};
        } catch (error) {
            return {};
        }
    }

    function restoreQuota() {
        if (root.customScript) return;
        const saved = savedQuotas()[root.provider];
        if (saved) {
            applyQuota(saved);
        }
    }

    function rememberQuota(parsed) {
        if (root.customScript || (root.bar1Val < 0 && root.bar2Val < 0)) return;
        const saved = savedQuotas();
        const snapshot = saved[root.provider] || {};
        for (let index = 1; index <= 2; index++) {
            const prefix = "bar" + index + "_";
            if (parsed[prefix + "percent"] === undefined || Number(parsed[prefix + "percent"]) < 0) continue;
            for (const field of ["label", "percent", "exact", "resets_at", "updated_at"]) {
                if (parsed[prefix + field] !== undefined) snapshot[prefix + field] = parsed[prefix + field];
                else delete snapshot[prefix + field];
            }
        }
        snapshot.timestamp = parsed.timestamp || 0;
        saved[root.provider] = snapshot;
        const serialized = JSON.stringify(saved);
        if (serialized !== root.configuration.lastKnownQuotas)
            root.configuration.lastKnownQuotas = serialized;
    }

    function resetProvider() {
        generation++;
        currentStatus = "спит";
        bar1Val = -1;
        bar2Val = -1;
        bar1Exact = -1;
        bar2Exact = -1;
        bar1Label = "5 часов";
        bar2Label = "неделя";
        bar1Reset = "";
        bar2Reset = "";
        quotaError = "";
        freshness.bar1Updated = 0;
        freshness.bar2Updated = 0;
        backgroundRefreshing = false;
        restoreQuota();
        poll();
    }

    function poll() {
        if (!ready || !monitoringEnabled || activeCommand) return;
        activeProvider = provider;
        activeGeneration = generation;
        activeCommand = "python3 " + shellQuote(scriptPath) + " --provider " + shellQuote(provider) + " " + shellQuote(customScript);
        executeCommand(execSource, activeCommand);
    }

    function refreshQuotas() {
        if (!canRefresh) return;
        freshness.now = Date.now() / 1000;
        lastManualAt = freshness.now;
        lastManualProvider = provider;
        generation++;
        refreshProvider = provider;
        refreshGeneration = generation;
        refreshCommand = "python3 " + shellQuote(scriptPath) + " --provider " + shellQuote(provider) +
                         " --refresh-only --force-refresh";
        executeCommand(refreshSource, refreshCommand);
    }

    Component.onCompleted: {
        ready = true;
        if (monitoringEnabled) resetProvider();
    }

    onProviderChanged: { if (ready) resetProvider(); }
    onCustomScriptChanged: { if (ready) resetProvider(); }
    onMonitoringEnabledChanged: {
        generation++;
        if (!ready) return;
        if (monitoringEnabled) resetProvider();
        else {
            currentStatus = root.configuration.statusText;
            bar1Val = root.configuration.bar1Percent;
            bar2Val = root.configuration.bar2Percent;
            bar1Exact = bar1Val;
            bar2Exact = bar2Val;
            bar1Label = root.configuration.bar1Label;
            bar2Label = root.configuration.bar2Label;
            bar1Reset = "";
            bar2Reset = "";
            quotaError = "";
            backgroundRefreshing = false;
        }
    }

    Plasma5Support.DataSource {
        id: execSource
        engine: "executable"
        connectedSources: []

        onNewData: (sourceName, data) => root.handlePollData(sourceName, data)
    }

    function handlePollData(sourceName, data) {
        const correctProvider = root.activeProvider === root.provider && root.activeGeneration === root.generation;
        execSource.disconnectSource(sourceName);
        root.activeCommand = "";
        if (!correctProvider) {
            root.poll();
            return;
        }
        if (!root.monitoringEnabled) return;
        const stdout = data["stdout"] ? data["stdout"].trim() : "";
        try {
            if (data["exit code"] !== 0 || !stdout) throw new Error("Провайдер не вернул данные");
            const parsed = JSON.parse(stdout);
            root.currentStatus = parsed.status || "отдыхает";
            root.applyQuota(parsed);
            root.rememberQuota(parsed);
            root.quotaError = parsed.quota_error || "";
        } catch (error) {
            root.quotaError = "Ошибка чтения данных: " + error;
        }
    }

    Plasma5Support.DataSource {
        id: refreshSource
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => root.handleRefreshData(sourceName, data)
    }

    function handleRefreshData(sourceName, data) {
        const current = root.refreshProvider === root.provider && root.refreshGeneration === root.generation;
        refreshSource.disconnectSource(sourceName);
        root.refreshCommand = "";
        if (current) {
            root.generation++;
            root.backgroundRefreshing = false;
            if (data["exit code"] !== 0) root.quotaError = "Не удалось запустить обновление лимитов";
        }
        root.poll();
    }

    Timer {
        interval: 1000
        running: root.monitoringEnabled
        repeat: true
        onTriggered: root.freshness.now = Date.now() / 1000
    }

    Timer {
        interval: root.intervalSec * 1000
        running: root.monitoringEnabled
        repeat: true
        triggeredOnStart: true
        onTriggered: root.poll()
    }

    // React to configuration changes
    Connections {
        target: root.configuration

        function onStatusTextChanged() {
            if (!root.monitoringEnabled) {
                root.currentStatus = root.configuration.statusText;
            }
        }
        function onBar1PercentChanged() {
            if (!root.monitoringEnabled) root.bar1Val = root.configuration.bar1Percent;
        }
        function onBar2PercentChanged() {
            if (!root.monitoringEnabled) root.bar2Val = root.configuration.bar2Percent;
        }
        function onBar1LabelChanged() {
            if (!root.monitoringEnabled) root.bar1Label = root.configuration.bar1Label;
        }
        function onBar2LabelChanged() {
            if (!root.monitoringEnabled) root.bar2Label = root.configuration.bar2Label;
        }
    }
}
