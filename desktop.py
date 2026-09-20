"""Native desktop window and tray; local application state lives in the user profile."""
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import time
import urllib.request

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QIcon, QDesktopServices
from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QMessageBox, QSystemTrayIcon
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView

from launch import BASE, DATA_DIR, SESSION, current, instance_lock, save_session, version
from server import Handler, Store, ThreadingHTTPServer


class Commands(QObject):
    action = Signal(str)


class LocalPage(QWebEnginePage):
    def __init__(self, profile, origin, parent):
        super().__init__(profile, parent)
        self.origin = origin

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        if url.toString().startswith(self.origin + '/') or url.toString() == self.origin:
            return True
        if navigation_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked and url.scheme() in ('https', 'http'):
            QDesktopServices.openUrl(url)
        return False


class Window(QMainWindow):
    def __init__(self, url, app):
        super().__init__()
        self.app, self.quitting = app, False
        self.setWindowTitle('Obsydian Finder')
        self.resize(1440, 960)
        icon = QIcon(str(BASE / 'assets' / 'obsydian.png'))
        self.setWindowIcon(icon)
        app.setWindowIcon(icon)
        help_menu = self.menuBar().addMenu('Help')
        notices = QAction('Component licenses and notices', self)
        notices.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(BASE / 'THIRD_PARTY_NOTICES.md'))))
        credits = QAction('Chromium component credits', self)
        credits.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(BASE / 'licenses' / 'Chromium-CREDITS.html'))))
        help_menu.addAction(notices)
        help_menu.addAction(credits)
        self.profile = QWebEngineProfile('ObsydianFinder', self)
        self.profile.setPersistentStoragePath(str(DATA_DIR / 'web'))
        self.profile.setCachePath(str(DATA_DIR / 'cache'))
        self.web = QWebEngineView(self)
        self.web.setPage(LocalPage(self.profile, url, self.web))
        self.setCentralWidget(self.web)
        self.web.load(QUrl(url))
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip('Obsydian Finder')
        menu = QMenu(self)
        show = QAction('Show Obsydian Finder', menu)
        show.triggered.connect(self.show_window)
        quit_action = QAction('Quit Obsydian Finder', menu)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(show)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.show_window() if reason in (
            QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick) else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        self.commands = Commands(self)
        self.commands.action.connect(self.command)

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def command(self, action):
        if action == 'show':
            self.show_window()
        elif action == 'tray':
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.tray.show()
                self.hide()
            else:
                self.showMinimized()
        elif action == 'quit':
            self.quit_app()

    def quit_app(self):
        self.quitting = True
        self.tray.hide()
        self.app.quit()

    def closeEvent(self, event):
        if not self.quitting and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            self.tray.showMessage('Obsydian Finder', 'Still running in the tray. Use Quit to close the application.',
                                  QSystemTrayIcon.MessageIcon.Information, 2500)
        else:
            self.quit_app()
            event.accept()


def request(existing, endpoint, body):
    req = urllib.request.Request(existing['url'] + endpoint, data=json.dumps(body).encode(),
                                 headers={'X-Obsydian-Token': existing['token'], 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=3) as response:
        return json.load(response)


def main():
    if os.name == 'nt':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ObsydianFinder.Desktop')
    app = QApplication(sys.argv)
    app.setApplicationName('Obsydian Finder')
    app.setOrganizationName('ObsydianFinder')
    app.setQuitOnLastWindowClosed(False)
    existing = current()
    if existing and existing.get('desktop') and existing.get('version') == version():
        request(existing, '/api/desktop', {'action': 'show'})
        return
    if existing:
        request(existing, '/api/shutdown', {})
        for _ in range(50):
            if not current():
                break
            time.sleep(.1)
    lock = instance_lock()
    if lock is None:
        for _ in range(60):
            existing = current()
            if existing and existing.get('desktop'):
                request(existing, '/api/desktop', {'action': 'show'})
                return
            time.sleep(.1)
        QMessageBox.warning(None, 'Obsydian Finder', 'Another instance is still starting. Please try again shortly.')
        return
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.token = secrets.token_urlsafe(32)
    server.store = Store()
    url = f'http://127.0.0.1:{server.server_port}'
    window = Window(url, app)
    server.desktop_callback = window.commands.action.emit
    server.tray_available = QSystemTrayIcon.isSystemTrayAvailable()
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    save_session(server.server_port, server.token)
    window.show()
    # A process-level smoke test loads the real native WebEngine, captures it and exits.
    smoke = os.environ.get('OBSYDIAN_SMOKE_SCREENSHOT')
    if smoke:
        def capture():
            window.grab().save(smoke)
            tray = QSystemTrayIcon.isSystemTrayAvailable()
            if tray:
                window.close()
                hidden = not window.isVisible()
                window.command('show')
                restored = window.isVisible()
            else:
                hidden, restored = None, True
            def report(result):
                result = result if isinstance(result, dict) else {}
                Path(smoke).with_suffix('.json').write_text(json.dumps(dict(
                    webgl=bool(result.get('webgl')), ready=bool(result.get('ready')),
                    trayAvailable=tray, closeHides=hidden, restoreShows=restored)), encoding='utf-8')
                window.quit_app()
            window.web.page().runJavaScript("({webgl:typeof renderer !== 'undefined' && !!renderer.isWebGLRenderer,ready:typeof state !== 'undefined' && typeof scan === 'function' && typeof view === 'function' && !!document.getElementById('scanCustom')})", report)
        window.web.loadFinished.connect(lambda ok: QTimer.singleShot(2000, capture))
        QTimer.singleShot(20000, window.quit_app)
    try:
        app.exec()
    finally:
        server.store.cancel()
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
        try:
            if json.loads(SESSION.read_text(encoding='utf-8')).get('pid') == os.getpid():
                SESSION.unlink()
        except (OSError, ValueError):
            pass
        lock.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        import traceback
        (DATA_DIR / 'desktop-errors.log').write_text(traceback.format_exc(), encoding='utf-8')
        if os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, str(exc), 'Obsydian Finder', 0x10)
        raise
