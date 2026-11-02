"""Optional UI smoke test: python3 -m unittest discover -s tests -v."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import unittest

try:
    from PySide6.QtCore import QUrl, QObject, QRectF, QMetaObject
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
    from PySide6.QtQuick import QQuickWindow, QQuickItem
    from PySide6.QtTest import QTest
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'PySide6 is required for the optional QML smoke test')
class WidgetTests(unittest.TestCase):
    def test_appearance_settings_show_auto_preview_and_literal_custom_field(self):
        app = QGuiApplication.instance() or QGuiApplication([])
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty('i18n', engine.evaluate(
            '(function(s,a){return s.replace("%1",a === undefined ? "" : a);})'))
        path = Path(__file__).resolve().parents[1] / 'contents/ui/configAppearance.qml'
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
        self.assertFalse(component.isError(), [e.toString() for e in component.errors()])
        form = component.createWithInitialProperties(dict(
            cfg_provider='codex', cfg_theme='material3', cfg_titleMode='auto', cfg_titleText='codex.sh',
            cfg_lowQuotaThreshold=20, cfg_criticalQuotaThreshold=10, cfg_lowQuotaWarning=True, cfg_fullQuotaIndicator=True,
            cfg_dimStaleQuotas=True, cfg_showTitleBar=True))
        self.assertIsNotNone(form, [e.toString() for e in component.errors()])
        preview = form.findChild(QObject, 'titlePreview')
        field = form.findChild(QQuickItem, 'customTitleField')
        self.assertEqual(preview.property('text'), 'Codex')
        self.assertFalse(field.isVisible())
        form.setProperty('cfg_titleMode', 'custom')
        self.assertTrue(field.isVisible())
        self.assertEqual(field.property('text'), 'codex.sh')
        self.assertEqual(preview.property('text'), 'codex.sh')
        form.setProperty('cfg_theme', 'retro_pixel')
        self.assertEqual(preview.property('text'), 'codex.sh')
        form.setProperty('cfg_lowQuotaThreshold', 10)
        self.assertEqual(form.property('cfg_lowQuotaThreshold'), 10)
        form.setProperty('cfg_criticalQuotaThreshold', 5)
        self.assertEqual(form.property('cfg_criticalQuotaThreshold'), 5)
        form.deleteLater()
        engine.deleteLater()
        app.processEvents()

    def test_title_modes_preserve_literal_custom_titles_across_themes(self):
        app = QGuiApplication.instance() or QGuiApplication([])
        engine = QQmlApplicationEngine()
        ui = (Path(__file__).resolve().parents[1] / 'contents/ui').as_uri()
        engine.loadData(('''import QtQuick
import "UI_PATH"
Item {
    ProviderTitle { id: title; objectName: "title"; rounded: true; customText: "antigravity.sh" }
    PixelWindow { objectName: "card"; width: 256; height: 288; titleText: title.text }
}'''.replace('UI_PATH', ui)).encode(), QUrl('file:///tmp/widget-title-smoke.qml'))
        self.assertTrue(engine.rootObjects())
        root = engine.rootObjects()[0]
        title = root.findChild(QObject, 'title')
        label = root.findChild(QObject, 'windowTitle')
        self.assertEqual(label.property('text'), 'Antigravity')
        title.setProperty('provider', 'codex')
        self.assertEqual(label.property('text'), 'Codex')
        title.setProperty('rounded', False)
        self.assertEqual(label.property('text'), 'codex.sh')
        title.setProperty('rounded', True)
        title.setProperty('mode', 'custom')
        for literal in ('codex.sh', 'antigravity.sh', 'antigravity.exe', 'мой агент', ''):
            title.setProperty('customText', literal)
            self.assertEqual(label.property('text'), literal)
            title.setProperty('rounded', False)
            self.assertEqual(label.property('text'), literal)
            title.setProperty('rounded', True)
        title.setProperty('mode', 'legacy')
        title.setProperty('customText', 'Старый пользовательский заголовок')
        self.assertFalse(title.property('automatic'))
        self.assertEqual(label.property('text'), 'Старый пользовательский заголовок')
        title.setProperty('mode', 'auto')
        self.assertEqual(label.property('text'), 'Codex')
        engine.deleteLater()
        app.processEvents()

    def test_quota_badges_are_configurable_and_do_not_occupy_quota_labels(self):
        app = QGuiApplication.instance() or QGuiApplication([])
        engine = QQmlApplicationEngine()
        ui = (Path(__file__).resolve().parents[1] / 'contents/ui').as_uri()
        engine.loadData(('''import QtQuick
import QtQuick.Window
import "UI_PATH"
Window {
    visible: true; width: 300; height: 320
    PixelTheme { id: badgeTheme; objectName: "badgeTheme" }
    QuotaFreshness { id: freshness; objectName: "freshness"; now: 1000;
        bar1Updated: 950; bar2Updated: 950; bar1Percent: 40; bar2Percent: 60 }
    PixelWindow { objectName: "card"; width: 256; height: 288;
        theme: badgeTheme;
        titleText: "Очень длинный пользовательский заголовок.sh";
        quotaState: freshness.indicatorState }
}'''.replace('UI_PATH', ui)).encode(), QUrl('file:///tmp/widget-badges-smoke.qml'))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        state = window.findChild(QObject, 'freshness')
        card = window.findChild(QQuickItem, 'card')
        self.assertEqual(state.property('indicatorState'), 'hidden')
        state.setProperty('bar1Percent', 20)
        self.assertEqual(state.property('indicatorState'), 'low')
        state.setProperty('bar1Exact', 20.1)
        self.assertEqual(state.property('indicatorState'), 'hidden')
        state.setProperty('lowThreshold', 25)
        self.assertEqual(state.property('indicatorState'), 'low')
        state.setProperty('lowWarning', False)
        self.assertEqual(state.property('indicatorState'), 'hidden')
        state.setProperty('lowWarning', True)
        state.setProperty('bar1Exact', 14)
        self.assertEqual(state.property('indicatorState'), 'low')
        state.setProperty('bar1Exact', 10)
        self.assertEqual(state.property('indicatorState'), 'low')
        state.setProperty('bar1Exact', 9.9)
        self.assertEqual(state.property('indicatorState'), 'critical')
        state.setProperty('criticalThreshold', 5)
        self.assertEqual(state.property('indicatorState'), 'low')
        state.setProperty('bar1Exact', 0)
        self.assertEqual(state.property('indicatorState'), 'exhausted')
        theme = window.findChild(QObject, 'badgeTheme')
        header = card.findChild(QQuickItem, 'headerQuotaIndicator')
        state.setProperty('criticalThreshold', 10)
        for theme_id in ('retro_pixel', 'material3', 'win95', 'cyberpunk', 'gruvbox', 'catppuccin', 'tokyo_night'):
            theme.setProperty('activeThemeId', theme_id)
            state.setProperty('bar1Exact', 14)
            self.assertEqual(header.property('warningColor'), theme.property('textTitle'))
            state.setProperty('bar1Exact', 9.9)
            self.assertEqual(header.property('warningColor').name(), '#f0504c')
        state.setProperty('bar1Exact', 0)
        for position, name in (('header', 'headerQuotaIndicator'), ('status', 'statusQuotaIndicator')):
            card.setProperty('quotaIndicatorPosition', position)
            for width, height in ((256, 288), (160, 160)):
                card.setWidth(width)
                card.setHeight(height)
                QTest.qWait(20)
                item = card.findChild(QQuickItem, name)
                self.assertTrue(item.isVisible())
                rect = item.mapRectToItem(card, QRectF(0, 0, item.width(), item.height()))
                self.assertGreaterEqual(rect.left(), 0)
                self.assertLessEqual(rect.right(), width)
                self.assertLessEqual(rect.bottom(), height)
        card.setProperty('quotaIndicatorPosition', 'header')
        card.setProperty('showTitleBar', False)
        QTest.qWait(20)
        self.assertTrue(card.findChild(QQuickItem, 'statusQuotaIndicator').isVisible())
        card.setProperty('quotaIndicatorPosition', 'hidden')
        self.assertFalse(card.findChild(QQuickItem, 'statusQuotaIndicator').isVisible())
        state.setProperty('bar1Exact', 100)
        state.setProperty('bar1Percent', 100)
        state.setProperty('bar2Percent', 100)
        self.assertEqual(state.property('indicatorState'), 'full')
        state.setProperty('showFull', False)
        self.assertEqual(state.property('indicatorState'), 'hidden')
        state.setProperty('showFull', True)
        state.setProperty('bar1Exact', 99.6)
        self.assertEqual(state.property('indicatorState'), 'hidden')
        state.setProperty('bar1Exact', 100)
        state.setProperty('bar2Percent', -1)
        self.assertEqual(state.property('indicatorState'), 'hidden')
        state.setProperty('bar2Percent', 100)
        state.setProperty('bar1Updated', 100)
        self.assertEqual(state.property('indicatorState'), 'hidden')
        self.assertTrue(state.property('bar1Dim'))
        state.setProperty('dimStale', False)
        self.assertFalse(state.property('bar1Dim'))
        state.setProperty('bar1Updated', 950)
        state.setProperty('error', 'offline')
        self.assertEqual(state.property('indicatorState'), 'hidden')
        window.close()
        engine.deleteLater()
        app.processEvents()

    def test_manual_refresh_coalesces_and_ignores_results_after_provider_switch(self):
        import json
        app = QGuiApplication.instance() or QGuiApplication([])
        engine = QQmlApplicationEngine()
        ui = (Path(__file__).resolve().parents[1] / 'contents/ui').as_uri()
        engine.loadData(('''import QtQuick
import "UI_PATH"
Item {
    property string result: ""
    property var commands: []
    QtObject {
        id: config
        property bool enableCliMonitoring: false
        property int pollInterval: 60
        property string customScriptPath: ""
        property string provider: "antigravity"
        property string statusText: "отдыхает"
        property int bar1Percent: -1
        property int bar2Percent: -1
        property string bar1Label: "5 часов"
        property string bar2Label: "неделя"
        property string lastKnownQuotas: JSON.stringify({codex: {bar1_percent: 22, timestamp: 900}})
    }
    AntigravityMonitor {
        id: monitor
        configuration: config
        executeCommand: (source, command) => commands.push(command)
    }
    function runScenario() {
        const disabled = !monitor.canRefresh;
        config.enableCliMonitoring = true;
        const oldPoll = monitor.activeCommand;
        monitor.refreshQuotas();
        const oldRefresh = monitor.refreshCommand;
        const count = commands.length;
        monitor.refreshQuotas();
        const coalesced = commands.length === count && oldRefresh.indexOf("--force-refresh") >= 0;
        config.provider = "codex";
        monitor.handleRefreshData(oldRefresh, {"exit code": 1});
        const ignoredRefresh = monitor.bar1Val === 22 && monitor.quotaError === "";
        monitor.handlePollData(oldPoll, {"exit code": 0, stdout: JSON.stringify({bar1_percent: 99})});
        const ignoredPoll = monitor.bar1Val === 22 && monitor.activeProvider === "codex";
        monitor.refreshQuotas();
        const currentRefresh = monitor.refreshCommand;
        const pendingPoll = monitor.activeCommand;
        monitor.handleRefreshData(currentRefresh, {"exit code": 0});
        monitor.handlePollData(pendingPoll, {"exit code": 0, stdout: JSON.stringify({bar1_percent: 88})});
        monitor.handlePollData(monitor.activeCommand, {"exit code": 0, stdout: JSON.stringify({
            bar1_percent: 33, bar2_percent: 44, timestamp: Date.now()/1000})});
        const updated = monitor.bar1Val === 33 && monitor.freshness.state === "fresh";
        const cooldown = !monitor.canRefresh;
        monitor.lastManualAt = 0;
        config.customScriptPath = "/custom/script";
        const customDisabled = !monitor.canRefresh;
        result = JSON.stringify({disabled, coalesced, ignoredRefresh, ignoredPoll, updated, cooldown, customDisabled});
    }
}'''.replace('UI_PATH', ui)).encode(), QUrl('file:///tmp/widget-refresh-smoke.qml'))
        self.assertTrue(engine.rootObjects())
        root = engine.rootObjects()[0]
        self.assertTrue(QMetaObject.invokeMethod(root, 'runScenario'))
        result = json.loads(root.property('result'))
        self.assertTrue(all(result.values()), result)
        engine.deleteLater()
        app.processEvents()

    def test_freshness_ages_independently_and_dims_saved_quotas(self):
        app = QGuiApplication.instance() or QGuiApplication([])
        engine = QQmlApplicationEngine()
        ui = (Path(__file__).resolve().parents[1] / 'contents/ui').as_uri()
        engine.loadData(('''import QtQuick
import QtQuick.Window
import "UI_PATH"
Window {
    visible: true; width: 300; height: 320
    PixelTheme { id: testTheme; objectName: "testTheme" }
    QuotaFreshness { id: freshness; objectName: "freshness";
        now: 1000; bar1Updated: 950; bar2Updated: 950; bar1Percent: 40; bar2Percent: 20 }
    PixelWindow { objectName: "card"; width: 256; height: 288;
        theme: testTheme; quotaState: freshness.indicatorState; quotaDescription: freshness.description;
        bar1Percent: 40; bar2Percent: 20;
        bar1Dim: freshness.bar1Dim; bar2Dim: freshness.bar2Dim }
}'''.replace('UI_PATH', ui)).encode(), QUrl('file:///tmp/widget-freshness-smoke.qml'))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        freshness = window.findChild(QObject, 'freshness')
        card = window.findChild(QQuickItem, 'card')
        self.assertEqual(freshness.property('state'), 'fresh')
        freshness.setProperty('bar2Updated', 700)
        self.assertEqual(freshness.property('state'), 'stale')
        self.assertFalse(freshness.property('bar1Dim'))
        self.assertTrue(freshness.property('bar2Dim'))
        self.assertIn('5 мин назад', freshness.property('description'))
        freshness.setProperty('now', 1200)
        self.assertTrue(freshness.property('bar1Dim'))
        freshness.setProperty('error', 'offline')
        self.assertEqual(freshness.property('state'), 'error')
        freshness.setProperty('refreshing', True)
        self.assertEqual(freshness.property('state'), 'refreshing')
        for theme in ('retro_pixel', 'material3', 'win95', 'cyberpunk', 'gruvbox', 'catppuccin', 'tokyo_night'):
            window.findChild(QObject, 'testTheme').setProperty('activeThemeId', theme)
            for width, height in ((256, 288), (160, 160)):
                card.setWidth(width)
                card.setHeight(height)
                QTest.qWait(10)
                indicator = card.findChild(QQuickItem, 'headerQuotaIndicator')
                if indicator.isVisible():
                    rect = indicator.mapRectToItem(card, QRectF(0, 0, indicator.width(), indicator.height()))
                    self.assertGreaterEqual(rect.left(), 0)
                    self.assertLessEqual(rect.right(), width)
                    self.assertLessEqual(rect.bottom(), height)
                bar = card.findChild(QQuickItem, 'quotaBar2')
                self.assertAlmostEqual(bar.findChild(QQuickItem, 'quotaFill').opacity(), .45)
        self.assertEqual(card.property('bar1Percent'), 40)
        freshness.setProperty('custom', True)
        freshness.setProperty('bar1Updated', 0)
        freshness.setProperty('bar2Updated', 0)
        self.assertEqual(freshness.property('state'), 'hidden')
        self.assertFalse(freshness.property('bar1Dim'))
        window.close()
        engine.deleteLater()
        app.processEvents()

    def test_two_providers_render_and_themes_are_independent(self):
        app = QGuiApplication.instance() or QGuiApplication([])
        engine = QQmlApplicationEngine()
        ui = (Path(__file__).resolve().parents[1] / 'contents/ui').as_uri()
        engine.loadData(('''import QtQuick
import QtQuick.Window
import "UI_PATH"
Window {
    visible: true; width: 510; height: 300
    PixelTheme { id: retro; objectName: "retroTheme"; activeThemeId: "retro_pixel" }
    PixelTheme { id: rounded; objectName: "roundedTheme"; activeThemeId: "material3" }
    PixelWindow { objectName: "agy"; x: 12; y: 12; width: 237; height: 276;
        theme: retro; provider: "antigravity"; titleText: "antigravity.sh";
        statusText: "спит"; enableAnimation: false }
    PixelWindow { objectName: "codex"; x: 261; y: 12; width: 237; height: 276;
        theme: rounded; provider: "codex"; titleText: "codex.sh";
        statusText: "работает"; enableAnimation: false }
}'''.replace('UI_PATH', ui)).encode(), QUrl('file:///tmp/widget-smoke.qml'))
        self.assertTrue(engine.rootObjects(), 'QML components must load')
        window = engine.rootObjects()[0]
        QTest.qWait(100)
        self.assertFalse(window.grabWindow().isNull())
        self.assertEqual(window.findChild(QObject, 'agy').property('provider'), 'antigravity')
        codex = window.findChild(QObject, 'codex')
        self.assertEqual(codex.property('provider'), 'codex')
        rounded = window.findChild(QObject, 'roundedTheme')
        rounded.setProperty('activeThemeId', 'cyberpunk')
        self.assertEqual(window.findChild(QObject, 'retroTheme').property('activeThemeId'), 'retro_pixel')
        self.assertEqual(rounded.property('activeThemeId'), 'cyberpunk')
        # Switching an existing instance must replace its logo without affecting its neighbour.
        before = window.grabWindow().copy(280, 50, 200, 100)
        codex.setProperty('provider', 'antigravity')
        QTest.qWait(100)
        after = window.grabWindow().copy(280, 50, 200, 100)
        self.assertNotEqual(before, after)
        window.close()
        engine.deleteLater()
        app.processEvents()

    def test_layout_fits_default_and_small_sizes_for_both_logos(self):
        app = QGuiApplication.instance() or QGuiApplication([])
        engine = QQmlApplicationEngine()
        ui = (Path(__file__).resolve().parents[1] / 'contents/ui').as_uri()
        engine.loadData(('''import QtQuick
import QtQuick.Window
import "UI_PATH"
Window {
    visible: true; width: 300; height: 320
    PixelWindow { objectName: "card"; width: 256; height: 288;
        showExactPercent: true; showResetTimes: true;
        bar1Percent: 99; bar1Exact: 99.4; bar1Reset: "4ч 45м";
        bar2Percent: 56; bar2Exact: 55.9; bar2Reset: "1д 15ч" }
}'''.replace('UI_PATH', ui)).encode(), QUrl('file:///tmp/widget-layout-smoke.qml'))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        card = window.findChild(QQuickItem, 'card')
        for selected in ('antigravity', 'codex'):
            card.setProperty('provider', selected)
            for width, height in ((256, 288), (250, 280), (220, 215), (160, 160)):
                card.setWidth(width)
                card.setHeight(height)
                for mascot in ('auto', 'large'):
                    card.setProperty('mascotSize', mascot)
                    QTest.qWait(30)
                    for name in ('quotaBar1', 'quotaBar2', 'mascotSlot'):
                        item = card.findChild(QQuickItem, name)
                        self.assertIsNotNone(item)
                        rect = item.mapRectToItem(card, QRectF(0, 0, item.width(), item.height()))
                        self.assertGreaterEqual(rect.left(), 0, (selected, width, height, name))
                        self.assertLessEqual(rect.right(), width, (selected, width, height, name))
                        self.assertLessEqual(rect.bottom(), height-4, (selected, width, height, name))
        window.close()
        engine.deleteLater()
        app.processEvents()


if __name__ == '__main__':
    unittest.main()
