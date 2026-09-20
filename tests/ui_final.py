"""Full UI checks on an isolated server and disposable fixtures, never user drives."""
import json
import secrets
import sys
import tempfile
import threading
import time
from urllib.parse import quote
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select


class SlowEntries:
    def __init__(self, entries):
        with entries:
            self.entries = iter(sorted(entries, key=lambda entry: entry.name))
    def __iter__(self): return self
    def __next__(self):
        item = next(self.entries)
        time.sleep(.05)
        return item
    def close(self): pass


class CountingStore(server.Store):
    def __init__(self):
        super().__init__()
        self.scan_starts = 0
    def start(self, *args, **kwargs):
        self.scan_starts += 1
        return super().start(*args, **kwargs)


with tempfile.TemporaryDirectory(prefix='obsydian-final-') as directory:
    base = Path(directory).resolve()
    roots = [base / 'Studio', base / 'Archive']
    for root in roots:
        root.mkdir()
        (root / '00-source.md').write_text('[Asset](zz-target.bin)\n', encoding='utf8')
        for index in range(60):
            (root / f'item-{index:03}.txt').write_text('fixture' * (index + 10))
        (root / 'zz-target.bin').write_bytes(b'asset fixture' * 5000)
        (root / 'Project').mkdir()
        (root / 'Project' / 'app.md').write_text('[Asset](../zz-target.bin)\n')
        (root / 'Project' / 'video.mp4').write_bytes(b'video fixture' * 150000)
    original_scandir, original_drives = server.os.scandir, server.drives
    server.os.scandir = lambda path: SlowEntries(original_scandir(path))
    server.drives = lambda: [dict(path=str(root), label=root.name, total=10000000,
                                 free=7000000, isDisk=True) for root in roots]
    service = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
    service.token = secrets.token_urlsafe(32)
    service.store = CountingStore()
    serving = threading.Thread(target=service.serve_forever, daemon=True)
    serving.start()
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1680,1100')
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    driver = webdriver.Chrome(options=options, service=Service(service_args=['--disable-build-check']))
    wait = WebDriverWait(driver, 30)
    checks = []
    try:
        driver.get(f'http://127.0.0.1:{service.server_port}')
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.disk')) == 2)
        assert not driver.find_elements(By.ID, 'indexReferences')
        assert driver.find_element(By.ID, 'stopAll').is_displayed()
        driver.find_element(By.ID, 'scanAll').click()
        wait.until(lambda d: service.store.references.status()['files'] > 0)
        assert service.store.state['running']
        assert driver.find_element(By.ID, 'stopAll').is_enabled()
        wait.until(lambda d: service.store.references.status()['edges'] > 0)
        assert service.store.state['running'], 'Connections appeared only after scan completion'
        wait.until(lambda d: d.execute_script('return referenceEdges.length > 0'))
        checks.append('automatic connections appear during file scanning')
        driver.find_element(By.ID, 'stopAll').click()
        wait.until(lambda d: not service.store.state['running'])
        wait.until(lambda d: not service.store.references.status()['running'])
        assert service.store.state['cancelled']
        assert service.store.state['bytes'] > 0
        wait.until(lambda d: 'partial' in d.find_element(By.ID, 'statState').get_attribute('textContent'))
        checks.append('visible Stop stops scan and connections, preserves results')
        field = driver.find_element(By.ID, 'rootPath')
        field.clear(); field.send_keys(str(roots[0]))
        driver.find_element(By.ID, 'scanCustom').click()
        wait.until(lambda d: service.store.state['root'] == str(roots[0]))
        wait.until(lambda d: d.find_element(By.ID, 'statState').get_attribute('textContent') == 'Scan complete')
        wait.until(lambda d: service.store.references.status()['complete'])
        wait.until(lambda d: d.execute_script('return !transition && projected.length > 2'))
        before = driver.execute_script('return {position:camera.position.toArray(),target:orbit.target.toArray(),direction:camera.position.clone().sub(orbit.target).normalize().toArray()}')
        canvas = driver.find_element(By.ID, 'universe')
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(canvas, -100, -80)
        actions.w3c_actions.pointer_action.pointer_down(button=1)
        actions.move_by_offset(55, 32)
        actions.w3c_actions.pointer_action.pointer_up(button=1)
        actions.perform()
        wait.until(lambda d: d.execute_script('return orbit.target.distanceTo(new THREE.Vector3(...arguments[0]))>1', before['target']))
        after = driver.execute_script('return {position:camera.position.toArray(),target:orbit.target.toArray(),direction:camera.position.clone().sub(orbit.target).normalize().toArray()}')
        assert sum(abs(a-b) for a,b in zip(before['position'],after['position'])) > 1, (before, after)
        assert max(abs(a-b) for a,b in zip(before['direction'],after['direction'])) < .00001, (before, after)
        checks.append('middle drag pans without rotating')
        driver.find_element(By.ID, 'viewList').click()
        def row(name):
            return next(r for r in driver.find_elements(By.CSS_SELECTOR, '.list-row') if name in r.text)
        row('item-000.txt').click()
        ActionChains(driver).key_down(Keys.CONTROL).click(row('item-001.txt')).key_up(Keys.CONTROL).perform()
        assert driver.execute_script('return state.selection.size') == 2
        assert '2' in driver.find_element(By.ID, 'selectionCount').text
        # Simulate files removed by another program; the app must prune stale nodes.
        (roots[0] / 'item-000.txt').unlink()
        (roots[0] / 'item-001.txt').unlink()
        starts = service.store.scan_starts
        driver.find_element(By.ID, 'trashSelection').click()
        wait.until(lambda d: d.find_element(By.ID, 'bulkDialog').is_displayed())
        driver.find_element(By.ID, 'confirmTrash').click()
        wait.until(lambda d: not d.find_element(By.ID, 'operationOverlay').is_displayed())
        wait.until(lambda d: not any('item-000.txt' in r.text or 'item-001.txt' in r.text for r in d.find_elements(By.CSS_SELECTOR, '.list-row')))
        assert service.store.scan_starts == starts, 'Batch action restarted file scanning'
        assert not service.store.state['running']
        checks.append('multi-select prunes missing files without restarting scan')
        ActionChains(driver).double_click(row('Project')).perform()
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.list-row')) == 2)
        row('app.md').click()
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.reference-card')) > 0)
        driver.find_element(By.ID, 'view3d').click()
        wait.until(lambda d: d.execute_script('return !transition'))
        driver.save_screenshot(str(Path(__file__).resolve().parent.parent / 'preview-final.png'))
        Select(driver.find_element(By.ID, 'languageSelect')).select_by_value('it')
        wait.until(lambda d: d.find_element(By.ID, 'quitApp').text == 'Chiudi Obsydian')
        assert 'Interrompi' in driver.find_element(By.ID, 'stopAll').text
        Select(driver.find_element(By.ID, 'languageSelect')).select_by_value('en')
        checks.append('updated controls localized in English and Italian')
        driver.find_element(By.ID, 'quitApp').click()
        wait.until(lambda d: d.find_element(By.ID, 'quitDialog').is_displayed())
        driver.find_element(By.ID, 'confirmQuit').click()
        wait.until(lambda d: d.find_element(By.ID, 'closedScreen').is_displayed())
        serving.join(5)
        assert not serving.is_alive(), 'Quit did not stop local HTTP service'
        checks.append('Quit confirmation stops the local service')
        logs = driver.get_log('browser')
        missing_reference_urls = ['/api/references?path='+quote(str(roots[0] / name), safe='')
                                  for name in ('item-000.txt', 'item-001.txt')]
        # The test deliberately removes selected files outside the app. A concurrent
        # reference poll may correctly reject those exact missing paths before pruning.
        def expected_missing_response(entry):
            return (entry.get('source') == 'network' and 'status of 400' in entry['message']
                    and any(url in entry['message'] for url in missing_reference_urls))
        errors = [e for e in logs if e['level'] == 'SEVERE' and 'favicon.ico' not in e['message']
                  and not expected_missing_response(e)]
        assert not errors, errors
        print(json.dumps({'ui_final':'passed','checks':checks,'browser_errors':errors,
                          'expected_missing_file_responses':sum(expected_missing_response(e) for e in logs)}))
    except Exception:
        driver.save_screenshot(str(Path(__file__).resolve().parent.parent / 'preview-final-error.png'))
        print(json.dumps(driver.execute_script('return {path:state.path,rows:state.items.length,selected:state.selected?.name,selection:state.selection.size,toast:document.getElementById("toast").textContent,errors:document.getElementById("bulkError").textContent}')), flush=True)
        print(json.dumps(driver.get_log('browser')), flush=True)
        raise
    finally:
        driver.quit()
        service.store.cancel()
        service.shutdown()
        service.server_close()
        server.os.scandir, server.drives = original_scandir, original_drives

