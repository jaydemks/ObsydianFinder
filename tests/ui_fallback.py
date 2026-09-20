"""Force WebGL creation failure and verify that file operations remain usable in List."""
import json
from pathlib import Path
import secrets
import sys
import tempfile
import threading
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server import Store, Handler, ThreadingHTTPServer
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary).resolve()
    (root / 'visible.txt').write_text('fixture')
    service = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    service.token = secrets.token_urlsafe(32)
    service.store = Store()
    threading.Thread(target=service.serve_forever, daemon=True).start()
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1600,1000')
    driver = webdriver.Chrome(options=options, service=Service(service_args=['--disable-build-check']))
    wait = WebDriverWait(driver, 20)
    try:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': "const originalContext=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){if(type.includes('webgl'))return null;return originalContext.call(this,type,...args)};"})
        driver.get(f'http://127.0.0.1:{service.server_port}')
        wait.until(lambda d: d.execute_script('return !!window.webglUnavailable'))
        assert driver.find_element(By.ID, 'view3d').get_attribute('disabled')
        assert driver.find_element(By.ID, 'list').is_displayed()
        driver.find_element(By.ID, 'rootPath').send_keys(str(root))
        driver.find_element(By.ID, 'scanCustom').click()
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.list-row')) == 1)
        driver.find_element(By.CSS_SELECTOR, '.list-row').click()
        driver.find_element(By.ID, 'rename').click()
        field = driver.find_element(By.ID, 'dialogInput')
        field.clear();field.send_keys('renamed.txt')
        driver.find_element(By.ID, 'confirmAction').click()
        wait.until(lambda d: (root / 'renamed.txt').exists())
        wait.until(lambda d: d.execute_script('return [...document.querySelectorAll(".list-row")].some(row=>row.textContent.includes("renamed.txt"))'))
        print(json.dumps({'webgl_failure_fallback':'passed','checks':['automatic List fallback','scan','select','rename']}))
    finally:
        driver.quit()
        service.store.cancel()
        service.shutdown()
        service.server_close()
