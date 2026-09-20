"""Isolated UI regression: two disposable 'disks', deliberately slow reads, no real disk scan."""
import json
import secrets
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class SlowEntries:
    def __init__(self, entries):
        self.entries = entries

    def __enter__(self):
        self.entries.__enter__()
        return self

    def __exit__(self, *args):
        return self.entries.__exit__(*args)

    def __iter__(self):
        return self

    def close(self):
        self.entries.close()

    def __next__(self):
        item = next(self.entries)
        time.sleep(.045)
        return item


class SlowOperations(server.Store):
    def duplicates(self, value):
        time.sleep(1.2)
        return super().duplicates(value)


with tempfile.TemporaryDirectory(prefix='obsydian-progressive-') as temporary:
    base = Path(temporary).resolve()
    roots = [base / 'Disco A', base / 'Disco B']
    for root in roots:
        root.mkdir()
        for index in range(60):
            (root / f'file-{index:03}.txt').write_bytes(b'duplicate fixture' * 100)
        (root / 'Windows').mkdir()
        (root / 'Windows' / 'system.txt').write_text('visible but protected')
        (root / 'Project').mkdir()
        (root / 'Project' / 'main.md').write_text('[Related file](../file-000.txt)\n')
        (root / 'Project' / 'video.mp4').write_bytes(b'video fixture' * 100000)
    original_scandir, original_drives = server.os.scandir, server.drives
    server.os.scandir = lambda path: SlowEntries(original_scandir(path))
    server.drives = lambda: [dict(path=str(root), label=root.name, total=10000000,
                                 free=9000000, isDisk=True) for root in roots]
    service = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
    service.token = secrets.token_urlsafe(32)
    service.store = SlowOperations()
    threading.Thread(target=service.serve_forever, daemon=True).start()
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1500,980')
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    driver = webdriver.Chrome(options=options, service=Service(service_args=['--disable-build-check']))
    wait = WebDriverWait(driver, 35)
    checks = []
    try:
        driver.get(f'http://127.0.0.1:{service.server_port}')
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.disk')) == 2)
        include = driver.find_element(By.ID, 'includeSystem')
        if not include.is_selected():
            include.click()
        driver.find_element(By.ID, 'scanAll').click()
        wait.until(lambda d: service.store.state['running'])
        wait.until(lambda d: d.find_element(By.ID, 'scanNotice').is_displayed())
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.list-row')) >= 1)
        assert service.store.state['running'], 'No progressive map before completion'
        assert service.store.state['root'] == '@computer'
        assert service.store.state['includeSystem'] is True
        wait.until(lambda d: service.store.state['bytes'] > 0)
        assert service.store.state['running'], 'No progressive byte count'
        driver.save_screenshot(str(Path(__file__).resolve().parent.parent / 'preview-streaming.png'))
        checks.append('all disks and partial map visible during scan')
        driver.find_element(By.ID, 'cancelScan').click()
        wait.until(lambda d: not service.store.state['running'])
        assert service.store.state['cancelled'] is True
        assert service.store.state['bytes'] > 0
        wait.until(lambda d: 'stopped' in d.find_element(By.ID, 'scanNotice').get_attribute('class'))
        assert len(driver.find_elements(By.CSS_SELECTOR, '.list-row')) >= 1
        checks.append('cancellation preserves partial map')
        path_input = driver.find_element(By.ID, 'rootPath')
        path_input.clear()
        path_input.send_keys(str(roots[0]))
        driver.find_element(By.ID, 'scanCustom').click()
        wait.until(lambda d: service.store.state['root'] == str(roots[0]))
        wait.until(lambda d: not service.store.state['running'])
        wait.until(lambda d: d.find_element(By.ID, 'statState').get_attribute('textContent') == 'Scan complete')
        driver.find_element(By.ID, 'viewList').click()
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.list-row')) == 62)
        rows = driver.find_elements(By.CSS_SELECTOR, '.list-row')
        next(row for row in rows if 'file-000.txt' in row.text).click()
        driver.find_element(By.ID, 'duplicates').click()
        wait.until(lambda d: d.find_element(By.ID, 'operationOverlay').is_displayed())
        wait.until(lambda d: not d.find_element(By.ID, 'operationOverlay').is_displayed())
        wait.until(lambda d: 'confirmed' in d.find_element(By.ID, 'duplicateResults').text)
        checks.append('blocking operation overlay appears and clears')
        assert not driver.find_elements(By.ID, 'indexReferences')
        wait.until(lambda d: 'index complete' in d.find_element(By.ID, 'graphStatus').text)
        project_row = next(row for row in driver.find_elements(By.CSS_SELECTOR, '.list-row') if 'Project' in row.text)
        ActionChains(driver).context_click(project_row).perform()
        wait.until(lambda d: d.find_element(By.ID, 'contextMenu').is_displayed())
        next(button for button in driver.find_elements(By.CSS_SELECTOR, '#contextMenu button') if button.text == 'Enter folder').click()
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.list-row')) == 2)
        next(row for row in driver.find_elements(By.CSS_SELECTOR, '.list-row') if 'main.md' in row.text).click()
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.reference-card')) > 0)
        assert 'file-000.txt' in driver.find_element(By.ID, 'connections').text
        driver.find_element(By.ID, 'view3d').click()
        time.sleep(1)
        driver.save_screenshot(str(Path(__file__).resolve().parent.parent / 'preview-graph.png'))
        ActionChains(driver).key_down(Keys.ALT).send_keys(Keys.ARROW_LEFT).key_up(Keys.ALT).perform()
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.list-row')) == 62)
        wait.until(lambda d: d.execute_script('return Object.keys(scenePreviews).length > 0'))
        checks.append('right-click navigation, cross-folder references, back navigation, nested previews')
        Select(driver.find_element(By.ID, 'languageSelect')).select_by_value('it')
        wait.until(lambda d: d.find_element(By.ID, 'statState').get_attribute('textContent') == 'Analisi completata')
        assert 'Analizza tutto' in driver.find_element(By.ID, 'scanAll').text
        assert 'Connessioni automatiche' in driver.find_element(By.CSS_SELECTOR, '.graph-panel').text
        driver.refresh()
        wait.until(lambda d: d.find_element(By.ID, 'statState').get_attribute('textContent') == 'Analisi completata')
        assert driver.find_element(By.TAG_NAME, 'html').get_attribute('lang') == 'it'
        Select(driver.find_element(By.ID, 'languageSelect')).select_by_value('en')
        wait.until(lambda d: d.find_element(By.ID, 'statState').get_attribute('textContent') == 'Scan complete')
        checks.append('English default, Italian switch and persisted language')
        errors = [entry for entry in driver.get_log('browser')
                  if entry['level'] == 'SEVERE' and 'favicon.ico' not in entry['message']]
        assert not errors, errors
        print(json.dumps({'ui_progressive': 'passed', 'checks': checks, 'browser_errors': errors}))
    finally:
        driver.quit()
        if service.store.state['running']:
            service.store.cancel()
            deadline = time.monotonic() + 10
            while service.store.state['running'] and time.monotonic() < deadline:
                time.sleep(.05)
        service.shutdown()
        service.server_close()
        server.os.scandir, server.drives = original_scandir, original_drives


