"""Collect official Qt component license texts for the bundled Qt release."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import html
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1] / 'licenses'
BASE = 'https://doc.qt.io/qt-6/'

def fetch(name):
    with urllib.request.urlopen(BASE + name, timeout=45) as response:
        return response.read().decode('utf-8')

def main():
    index = fetch('qtwebengine-licensing.html')
    names = sorted(set(re.findall(r'href="(qtwebengine-3rdparty[^"#]+\.html)', index)))
    qt_index = fetch('licenses-used-in-qt.html')
    qt_names = set(re.findall(r'href="([^"]*attribution[^"#]*\.html)', qt_index))
    modules = ('qt-attribution-', 'qtcore-', 'qtgui-', 'qtnetwork-', 'qtqml-', 'qtquick-',
               'qtwebchannel-', 'qtpositioning-', 'qtshadertools-', 'qtimageformats-', 'qtsvg-', 'qtdbus-')
    names = sorted(set(names) | {name for name in qt_names if name.startswith(modules)})
    target = ROOT / 'QtWebEngine-components'
    target.mkdir(parents=True, exist_ok=True)
    def save(name):
        page = fetch(name)
        title = re.search(r'<h1[^>]*>(.*?)</h1>', page, re.S)
        title = re.sub('<[^>]+>', '', title.group(1)) if title else name
        # Preserve component license notices and attribution verbatim; omit site navigation.
        content = re.search(r'<div class="descr"[^>]*>(.*?)<!-- @@@', page, re.S)
        if not content:
            raise RuntimeError('License body not found: ' + name)
        body = content.group(1)
        body = re.sub(r'href="(?!https?:|#)([^"]+)"', lambda m: 'href="'+BASE+m.group(1)+'"', body)
        (target / name).write_text('<!doctype html><meta charset="utf-8"><h1>' + html.escape(title) +
                                  '</h1><p>Source: <a href="' + BASE + name + '">' + BASE + name +
                                  '</a></p>' + body, encoding='utf-8')
        return name, title
    with ThreadPoolExecutor(max_workers=8) as pool:
        items = list(pool.map(save, names))
    links = ''.join('<li><a href="QtWebEngine-components/'+name+'">'+html.escape(title)+'</a></li>' for name,title in items)
    (ROOT / 'Chromium-CREDITS.html').write_text('<!doctype html><meta charset="utf-8"><title>Qt WebEngine component licenses</title>'
       '<h1>Qt 6.11.2 and Chromium component licenses</h1><p>Official component notices from '
       '<a href="'+BASE+'qtwebengine-licensing.html">Qt WebEngine licensing</a>. These local pages are included for offline access.</p><ul>'+links+'</ul>', encoding='utf-8')
    print('Saved', len(items), 'component license pages.')

if __name__ == '__main__':
    main()
