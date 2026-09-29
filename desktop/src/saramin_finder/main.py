from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QStyle, QSystemTrayIcon

from saramin_finder.infrastructure.database import Store
from saramin_finder.ui.bridge import Bridge


class AppWindow(QWebEngineView):
    def __init__(self, store: Store):
        super().__init__()
        self.setWindowTitle("Saramin Finder · PC 공고 관리")
        self.resize(1280, 850)
        self.setMinimumSize(900, 620)
        icon = self.style().standardIcon(QStyle.SP_FileDialogDetailedView)
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        menu = QMenu()
        show_action = QAction("앱 열기", self)
        show_action.triggered.connect(self.showNormal)
        menu.addAction(show_action)
        exit_action = QAction("종료", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(exit_action)
        self.tray.setContextMenu(menu)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        self.bridge = Bridge(store, self, self.notify)
        self.channel = QWebChannel(self.page())
        self.channel.registerObject("bridge", self.bridge)
        self.page().setWebChannel(self.channel)
        self.page().navigationRequested.connect(self._navigation)
        html = Path(__file__).parent / "ui" / "index.html"
        self.load(QUrl.fromLocalFile(str(html.resolve())))

    def _navigation(self, request):
        # Local HTML is the only page allowed to access the privileged bridge.
        if request.url().isLocalFile():
            return
        if request.url().scheme() in ("https", "http"):
            QDesktopServices.openUrl(request.url())
        request.reject()

    def notify(self, summary: dict):
        if self.tray.isVisible() and QSystemTrayIcon.supportsMessages():
            self.tray.showMessage(summary["title"], summary["message"],
                                  QSystemTrayIcon.Information, 8000)


def data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return base / "SaraminAIFinder"


def main() -> int:
    root = data_dir()
    root.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=root / "desktop.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8")
    app = QApplication(sys.argv)
    try:
        store = Store(root / "jobs.sqlite3")
        window = AppWindow(store)
        window.show()
        if os.environ.get("SARFINDER_TEST_EXIT_MS"):
            QTimer.singleShot(int(os.environ["SARFINDER_TEST_EXIT_MS"]), app.quit)
        return app.exec()
    except Exception as exc:
        logging.exception("Desktop startup failed")
        QMessageBox.critical(None, "사람인 공고 관리 시작 오류", str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
