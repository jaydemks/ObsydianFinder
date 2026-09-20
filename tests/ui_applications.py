"""Application UI and confirmation flow. The native launch function is mocked."""
import json
import secrets
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

with tempfile.TemporaryDirectory(prefix='obsydian-app-ui-') as directory:
    service = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
    service.token = secrets.token_urlsafe(32)
    service.store = server.Store()
    catalog = service.store.applications
    catalog.add('fixture', 'Fixture Application', directory, version='1.2', publisher='Test Publisher',
                size=1024*1024, method='Official uninstaller', argv=[r'C:\Fixture\uninstall.exe', '--interactive'])
    catalog.loaded = True
    threading.Thread(target=service.serve_forever, daemon=True).start()
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1680,1100')
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    driver = webdriver.Chrome(options=options, service=Service(service_args=['--disable-build-check']))
    wait = WebDriverWait(driver, 20)
    try:
        driver.get(f'http://127.0.0.1:{service.server_port}')
        wait.until(lambda d: d.find_element(By.ID, 'viewApplications').is_displayed())
        driver.find_element(By.ID, 'viewApplications').click()
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.list-row')) == 1)
        driver.find_element(By.ID, 'viewList').click()
        driver.find_element(By.CSS_SELECTOR, '.list-row').click()
        wait.until(lambda d: d.find_element(By.ID, 'uninstallApplication').is_displayed())
        assert driver.find_element(By.ID, 'rename').get_attribute('disabled')
        assert directory in driver.find_element(By.ID, 'connections').text
        assert driver.execute_script('return referenceEdges.length===1 && referenceEdges[0].kind==="installation"')
        with patch('apps.shell_execute') as launch, patch('apps.subprocess.Popen') as other:
            driver.find_element(By.ID, 'uninstallApplication').click()
            wait.until(lambda d: d.find_element(By.ID, 'uninstallDialog').is_displayed())
            assert 'C:\\Fixture\\uninstall.exe'.replace('\\\\', '\\') in driver.find_element(By.ID, 'uninstallCommand').text
            driver.find_element(By.CSS_SELECTOR, '#uninstallDialog button[value=cancel]').click()
            launch.assert_not_called(); other.assert_not_called()
            driver.find_element(By.ID, 'uninstallApplication').click()
            driver.find_element(By.ID, 'confirmUninstall').click()
            wait.until(lambda d: not d.find_element(By.ID, 'uninstallDialog').is_displayed())
            assert launch.call_count + other.call_count == 1
        driver.find_element(By.ID, 'view3d').click()
        wait.until(lambda d: '1 / 1' in d.find_element(By.ID, 'linkCount').text)
        driver.save_screenshot(str(Path(__file__).resolve().parent.parent / 'preview-applications.png'))
        driver.find_element(By.ID, 'applicationLocation').click()
        wait.until(lambda d: d.find_element(By.ID, 'statState').get_attribute('textContent') == 'Scan complete')
        assert not driver.execute_script('return !!state.applicationsView')
        assert service.store.state['root'] == directory
        assert not driver.find_element(By.ID, 'uninstallApplication').is_displayed()
        errors = [entry for entry in driver.get_log('browser') if entry['level'] == 'SEVERE' and 'favicon.ico' not in entry['message']]
        assert not errors, errors
        print(json.dumps({'applications_ui':'passed','native_launches':'mocked only','browser_errors':errors}))
    except Exception:
        print(json.dumps(driver.execute_script('return {path:state.path,running:state.running,applications:state.applicationsView,toast:document.getElementById("toast").textContent,status:document.getElementById("statState").textContent}')), flush=True)
        print(json.dumps(driver.get_log('browser')), flush=True)
        raise
    finally:
        driver.quit()
        service.store.cancel()
        service.shutdown()
        service.server_close()
