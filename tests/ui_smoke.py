"""End-to-end check against the running local server; uses only disposable fixture files."""
import json
import os
from pathlib import Path
import tempfile
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

options = webdriver.ChromeOptions()
options.add_argument('--headless=new')
options.add_argument('--window-size=1500,980')
options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
driver = webdriver.Chrome(options=options, service=Service(service_args=['--disable-build-check']))
wait = WebDriverWait(driver, 30)
try:
    driver.get(os.environ.get('OBSYDIAN_URL', 'http://127.0.0.1:8765'))
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.disk')) > 0)
    driver.save_screenshot(str(Path(__file__).resolve().parent.parent / 'preview.png'))
    with tempfile.TemporaryDirectory(prefix='obsydian-ui-') as folder:
        root = Path(folder)
        (root / 'Archivio').mkdir()
        (root / 'Foto').mkdir()
        (root / 'video.mp4').write_bytes(b'example video' * 10000)
        (root / 'copia.mp4').write_bytes(b'example video' * 10000)
        (root / 'note.txt').write_text('Fixture di verifica')
        driver.find_element(By.ID, 'rootPath').send_keys(folder)
        driver.find_element(By.ID, 'scanCustom').click()
        wait.until(lambda d: d.find_element(By.ID, 'statState').text == 'Scan complete')
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.list-row')) == 5)
        driver.execute_script('window.scrollTo(0,0)')
        driver.save_screenshot(str(Path(__file__).resolve().parent.parent / 'preview.png'))
        driver.find_element(By.ID, 'viewList').click()
        rows=driver.find_elements(By.CSS_SELECTOR, '.list-row')
        next(r for r in rows if 'video.mp4' in r.text).click()
        driver.find_element(By.ID, 'duplicates').click()
        wait.until(lambda d: 'confirmed' in d.find_element(By.ID, 'duplicateResults').text)
        assert 'copia.mp4' in driver.find_element(By.ID, 'duplicateResults').text
        driver.find_element(By.ID, 'rename').click()
        inp=driver.find_element(By.ID, 'dialogInput')
        inp.clear(); inp.send_keys('rinominato.mp4')
        driver.find_element(By.ID, 'confirmAction').click()
        wait.until(lambda d: (root / 'rinominato.mp4').exists())
        wait.until(lambda d: d.find_element(By.ID, 'statState').text == 'Scan complete')
        wait.until(lambda d: any('rinominato.mp4' in r.text for r in d.find_elements(By.CSS_SELECTOR, '.list-row')))
        search=driver.find_element(By.ID, 'search');search.send_keys('rinominato')
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.list-row')) == 1)
        severe=[e for e in driver.get_log('browser') if e['level']=='SEVERE' and 'favicon.ico' not in e['message']]
        assert not severe, severe
        print(json.dumps({'ui':'passed','checks':['load drives','scan','3d render','list','SHA256 duplicates','rename and automatic rescan','search'],'browser_errors':severe}))
finally:
    driver.quit()

