"""Exercise folder navigation with real WebGL, pointer input and delayed local HTTP."""
import json
import math
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import time
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


class DelayedHandler(server.Handler):
    """Pause one children response without blocking unrelated requests."""
    delayed_path = None
    entered = threading.Event()
    release = threading.Event()

    def do_GET(self):
        url = urlsplit(self.path)
        path = parse_qs(url.query).get('path', [None])[0]
        if url.path == '/api/children' and path == type(self).delayed_path:
            type(self).delayed_path = None
            type(self).entered.set()
            if not type(self).release.wait(10):
                return self.reply({'error': 'Test response barrier timed out'}, 500)
        return super().do_GET()


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def main():
    with tempfile.TemporaryDirectory(prefix='obsydian-navigation-') as temporary:
        root = Path(temporary).resolve()
        studio, archive = root / 'Studio', root / 'Archive'
        studio.mkdir(); archive.mkdir()
        nested = studio / 'Nested'
        nested.mkdir()
        (nested / 'inside.dat').write_bytes(bytes(48000))
        for directory in (studio, archive):
            for index, size in enumerate((32000, 18000, 9000)):
                (directory / ('asset-%s.dat' % index)).write_bytes(bytes(size))
        (root / 'readme.txt').write_text('Disposable navigation test data.')
        service = server.ThreadingHTTPServer(('127.0.0.1', 0), DelayedHandler)
        service.token = secrets.token_urlsafe(32)
        service.store = server.Store()
        service.store.start(str(root))
        threading.Thread(target=service.serve_forever, daemon=True).start()
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--window-size=1600,1050')
        options.add_argument('--enable-unsafe-swiftshader')
        options.add_argument('--use-gl=angle')
        options.add_argument('--use-angle=swiftshader')
        options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
        driver = webdriver.Chrome(options=options, service=Service(service_args=['--disable-build-check']))
        wait = WebDriverWait(driver, 25)

        def settled(path):
            wait.until(lambda d: d.execute_script(
                'return state.path===arguments[0] && !transition && nodes.length && '
                'nodes.every(n=>Math.abs(n.r-n.targetR)<.1)', str(path)))

        def double_click(x, y):
            bounds = driver.execute_script('return canvas.getBoundingClientRect().toJSON()')
            ActionChains(driver).move_to_element_with_offset(
                driver.find_element(By.ID, 'universe'),
                round(x - bounds['width'] / 2), round(y - bounds['height'] / 2)
            ).double_click().perform()

        try:
            with patch('server.drives', return_value=[dict(path=str(root), label='Navigation fixture',
                                                          total=1000000, free=500000, isDisk=True)]):
                driver.get(f'http://127.0.0.1:{service.server_port}')
                wait.until(lambda d: d.execute_script('return typeof renderer!=="undefined" && renderer.isWebGLRenderer && nodes.length===3'))
                settled(root)
                wait.until(lambda d: d.execute_script(
                    'return nodes.find(n=>n.item.path===arguments[0])?.childrenGroup.children.length>0', str(studio)))
                driver.execute_script('camera.position.set(-120,900,1200);orbit.target.set(30,90,10);orbit.update();draw()')
                driver.save_screenshot(str(Path(__file__).with_name('native-navigation.png')))
                # Observe rendered coordinates at the hand-off, not the implementation's
                # interpolation formula. A coordinate-system rebase must preserve pixels.
                driver.execute_script('''
                    window.navigationSamples=[];
                    function screenPoint(mesh){world.updateMatrixWorld(true);camera.updateMatrixWorld(true);
                        const p=mesh.getWorldPosition(new THREE.Vector3()).project(camera);
                        return [(p.x+1)*w/2,(1-p.y)*h/2]}
                    const originalTransition=transitionTo;
                    transitionTo=function(snapshot){
                        const previous=new Map((snapshot?.nodes||[]).map(n=>[n.item.path,screenPoint(n.mesh)]));
                        const previews=new Map((snapshot?.folder?.childrenGroup.children||[]).map(m=>[m.userData.path,screenPoint(m)]));
                        originalTransition(snapshot);
                        if(!transition)return;
                        const pairs=transition.isExit?transition.old.map(n=>[previous.get(n.item.path),screenPoint(n.mesh)]):
                            nodes.filter(n=>previews.has(n.item.path)).map(n=>[previews.get(n.item.path),screenPoint(n.mesh)]);
                        navigationSamples.push({phase:'start',exit:transition.isExit,pairs});
                    };
                    const originalFinish=finishTransition;
                    finishTransition=function(){
                        const active=transition;
                        if(!active)return originalFinish();
                        const ending=performance.now()-active.start>=active.duration-1;
                        draw();
                        const before=new Map(nodes.map(n=>[n.item.path,screenPoint(n.mesh)]));
                        originalFinish();
                        if(ending)navigationSamples.push({phase:'finish',exit:active.isExit,
                            pairs:nodes.map(n=>[before.get(n.item.path),screenPoint(n.mesh)])});
                    };
                ''')
                initial = driver.execute_script('return {position:camera.position.toArray(),target:orbit.target.toArray(),ids:nodes.map(n=>n.mesh.uuid)}')
                preview = driver.execute_script('''
                    const n=nodes.find(n=>n.item.path===arguments[0]);
                    world.updateMatrixWorld(true);
                    const child=n.childrenGroup.children[0];
                    const p=child.getWorldPosition(new THREE.Vector3()).project(camera);
                    return {opacity:n.mesh.material.opacity,depthWrite:n.mesh.material.depthWrite,
                        x:(p.x+1)*w/2,y:(1-p.y)*h/2,owner:hit((p.x+1)*w/2,(1-p.y)*h/2)?.n.item.path};
                ''', str(studio))
                assert 0 < preview['opacity'] < .65 and preview['depthWrite'] is False, preview
                assert preview['owner'] == str(studio), preview
                DelayedHandler.delayed_path = str(studio)
                double_click(preview['x'], preview['y'])
                assert DelayedHandler.entered.wait(5), 'Canvas double click did not request containing folder'
                retained = driver.execute_script('return {ids:nodes.map(n=>n.mesh.uuid),position:camera.position.toArray(),visible:bubbleGroup.children.length}')
                assert retained['ids'] == initial['ids'] and retained['visible'] >= 3, retained
                assert distance(initial['position'], retained['position']) < 1, retained
                DelayedHandler.release.set()
                settled(studio)
                driver.find_element(By.ID, 'up').click()
                settled(root)
                restored = driver.execute_script('return {position:camera.position.toArray(),target:orbit.target.toArray()}')
                assert distance(initial['position'], restored['position']) < .1, restored
                assert distance(initial['target'], restored['target']) < .1, restored
                samples = driver.execute_script('return navigationSamples')
                assert {(sample['phase'], sample['exit']) for sample in samples} == {
                    ('start', False), ('finish', False), ('start', True), ('finish', True)}, samples
                for sample in samples:
                    assert sample['pairs'], sample
                    assert max(distance(a, b) for a, b in sample['pairs']) < 1.5, sample

                # Enter another level and reverse direction during an active flight.
                driver.execute_script('children(arguments[0])', str(studio))
                settled(studio)
                nested_point = driver.execute_script('const n=nodes.find(n=>n.item.path===arguments[0]);const p=project(n);return {x:p.x,y:p.y}', str(nested))
                double_click(nested_point['x'], nested_point['y'])
                settled(nested)
                assert driver.execute_script('return state.items[0].name') == 'inside.dat'
                driver.find_element(By.ID, 'up').click()
                wait.until(lambda d: d.execute_script('return !!transition'))
                driver.execute_script('children(arguments[0])', str(root))
                settled(root)

                # Competing navigation responses must converge on the last request.
                driver.execute_script('children(arguments[0]);children(arguments[1]);children(arguments[2]);',
                                      str(studio), str(archive), str(root))
                settled(root)
                time.sleep(.3)
                cleanup = driver.execute_script('return {paths:nodes.map(n=>n.item.path),meshes:bubbleGroup.children.length,labels:labels.querySelectorAll(".world-label:not(.reference-ghost)").length}')
                assert cleanup['meshes'] == 3 and cleanup['labels'] == 3, cleanup
                assert set(cleanup['paths']) == {str(studio), str(archive), str(root / 'readme.txt')}, cleanup

                # List navigation uses the same data and remains available after transitions.
                driver.find_element(By.ID, 'viewList').click()
                row = next(row for row in driver.find_elements(By.CSS_SELECTOR, '.list-row')
                           if row.get_attribute('data-path') == str(studio))
                ActionChains(driver).double_click(row).perform()
                settled(studio)
                assert driver.find_element(By.ID, 'list').is_displayed()
                assert not driver.find_element(By.ID, 'universe').is_displayed()
                assert len(driver.find_elements(By.CSS_SELECTOR, '.list-row')) == 4
                driver.find_element(By.ID, 'up').click()
                settled(root)
                errors = [entry for entry in driver.get_log('browser')
                          if entry['level'] == 'SEVERE' and 'favicon' not in entry['message']]
                assert not errors, errors
                print(json.dumps({'navigation': 'passed', 'checks': [
                    'transparent folder shell', 'preview under pointer enters containing folder',
                    'pending HTTP retains scene', 'parent camera restored',
                    'preview and scene projected positions match both transition boundaries',
                    'nested folder entry and navigation interrupted during flight',
                    'rapid navigation has no orphan meshes or labels', 'List navigation'], 'errors': errors}))
        finally:
            DelayedHandler.release.set()
            driver.quit()
            service.store.cancel()
            service.shutdown()
            service.server_close()


if __name__ == '__main__':
    main()
