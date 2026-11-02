#!/usr/bin/env python3
"""Render the actual QML components with deterministic demo quotas (requires PySide6)."""
import argparse
import os
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_SCALE_FACTOR', '1')

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest

THEMES = ('retro_pixel', 'material3', 'win95', 'cyberpunk', 'gruvbox', 'catppuccin', 'tokyo_night')


def main():
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=repository / 'assets')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    app = QGuiApplication([])
    engine = QQmlApplicationEngine()
    qml = '''import QtQuick
import QtQuick.Window
import "UI_PATH"
Window {
    id: scene
    visible: true
    width: 560
    height: 320
    color: "#111116"
    property string selectedTheme: "retro_pixel"
    PixelTheme { id: demoTheme; activeThemeId: scene.selectedTheme }
    ProviderTitle { id: agyTitle; provider: "antigravity"; rounded: demoTheme.isRounded; mode: "auto" }
    ProviderTitle { id: codexTitle; provider: "codex"; rounded: demoTheme.isRounded; mode: "auto" }
    FullRepresentation {
        x: 16; y: 16; width: 256; height: 288
        provider: "antigravity"
        theme: demoTheme
        titleText: agyTitle.text
        statusText: "думает"
        bar1Label: "5 часов"; bar1Percent: 72; bar1Exact: 72.4; bar1Reset: "2ч 18м"
        bar2Label: "неделя"; bar2Percent: 56; bar2Exact: 55.9; bar2Reset: "1д 15ч"
        colorScheme: "green"
        showExactPercent: true; showResetTimes: true; enableAnimation: false
    }
    FullRepresentation {
        x: 288; y: 16; width: 256; height: 288
        provider: "codex"
        theme: demoTheme
        titleText: codexTitle.text
        statusText: "работает"
        bar1Label: "5 часов"; bar1Percent: 84; bar1Exact: 84.0; bar1Reset: "4ч 12м"
        bar2Label: "неделя"; bar2Percent: 63; bar2Exact: 63.0; bar2Reset: "5д 20ч"
        colorScheme: "green"
        showExactPercent: true; showResetTimes: true; enableAnimation: false
    }
}'''.replace('UI_PATH', (repository / 'contents/ui').as_uri())
    engine.loadData(qml.encode(), QUrl('file:///tmp/plasma-ai-status-screenshots.qml'))
    if not engine.rootObjects():
        raise RuntimeError('Could not load widget QML')
    window = engine.rootObjects()[0]
    for theme in THEMES:
        window.setProperty('selectedTheme', theme)
        QTest.qWait(350)
        screenshot = window.grabWindow()
        if screenshot.isNull():
            raise RuntimeError(f'Empty screenshot for {theme}')
        target = args.output / f'theme_{theme}.png'
        if not screenshot.save(str(target)):
            raise RuntimeError(f'Could not save {target}')
        if theme == 'retro_pixel':
            screenshot.save(str(args.output / 'preview.png'))
        print(target)
    window.close()
    engine.deleteLater()
    app.processEvents()


if __name__ == '__main__':
    main()
