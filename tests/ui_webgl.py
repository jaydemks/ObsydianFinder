"""Real WebGL rendering, world-space shadows and reference arrows on disposable data."""
import json, secrets, sys, tempfile, threading, time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
root_project=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='obsydian-webgl-') as folder:
    root=Path(folder).resolve()
    entries={'Creative Studio':350000,'Media Library':780000,'Research':110000,'Projects':210000,'Documents':60000,'Archives':550000}
    for name,size in entries.items():
        directory=root/name;directory.mkdir()
        for i in range(3):(directory/f'asset-{i}.dat').write_bytes(bytes(size//3))
    (root/'Creative Studio'/'timeline.json').write_text('{"music":"../Media Library/asset-0.dat","notes":"../Research/asset-0.dat"}')
    (root/'Projects'/'project.md').write_text('[Artwork](../Creative%20Studio/asset-0.dat)\n[Source](../Research/asset-1.dat)')
    (root/'notes.md').write_text('[Project](Projects/project.md)')
    service=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);service.token=secrets.token_urlsafe(32);service.store=server.Store()
    service.store.start(str(root))
    threading.Thread(target=service.serve_forever,daemon=True).start()
    options=webdriver.ChromeOptions();options.add_argument('--headless=new');options.add_argument('--window-size=1680,1050');options.set_capability('goog:loggingPrefs',{'browser':'ALL'})
    driver=webdriver.Chrome(options=options,service=Service(service_args=['--disable-build-check']));wait=WebDriverWait(driver,30)
    try:
        with patch('server.drives',return_value=[dict(path=str(root),label='Demo workspace',total=8000000,free=5000000,isDisk=True)]):
            driver.get(f'http://127.0.0.1:{service.server_port}')
            wait.until(lambda d:d.execute_script('return typeof renderer!=="undefined" && renderer.isWebGLRenderer && nodes.length>4'))
            wait.until(lambda d:service.store.references.status()['complete'])
            wait.until(lambda d:d.execute_script('return edgeGroup.children.length>0'))
            before=driver.execute_script('return {floor:floor.position.toArray(),rotation:floor.rotation.x,shadow:sun.castShadow&&floor.receiveShadow,colors:[...new Set(nodes.map(n=>n.mesh.material.color.getHexString()))]}')
            assert before['shadow'] and len(before['colors'])>=3,before
            driver.execute_script('camera.position.set(400,550,900);orbit.update();draw()')
            after=driver.execute_script('return floor.position.toArray()');assert after==before['floor']
            driver.execute_script('camera.position.set(-70,930,1250);orbit.target.set(-140,100,30);orbit.update();draw()')
            driver.execute_script("select(state.items.find(n=>n.name==='Creative Studio'))")
            wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,'.reference-card'))>0)
            time.sleep(1)
            # Public documentation contains demonstration data, never a user's filesystem paths.
            driver.execute_script("const root=arguments[0];const walk=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);while(walk.nextNode()){if(walk.currentNode.parentElement.tagName!=='SCRIPT')walk.currentNode.textContent=walk.currentNode.textContent.replaceAll(root,'Demo workspace')}document.getElementById('breadcrumb').textContent='Demo workspace';",str(root))
            (root_project/'docs').mkdir(exist_ok=True)
            driver.save_screenshot(str(root_project/'docs'/'screenshot.png'))
            errors=[e for e in driver.get_log('browser') if e['level']=='SEVERE' and 'favicon' not in e['message']]
            assert not errors,errors
            print(json.dumps({'webgl':'passed','checks':['real renderer','fixed ground shadows','capacity colors','3D reference arrows'],'errors':errors}))
    finally:
        driver.quit();service.store.cancel();service.shutdown();service.server_close()
