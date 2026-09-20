"""Generate the project's original geometric icon in scalable and desktop formats."""
from pathlib import Path
from PIL import Image, ImageDraw
root=Path(__file__).resolve().parents[1]/'assets'
root.mkdir(exist_ok=True)
svg='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#a995ff"/><stop offset="1" stop-color="#58dfcf"/></linearGradient></defs><rect width="512" height="512" rx="112" fill="#111526"/><path d="M256 57 424 233 337 429H167L88 233Z" fill="url(#g)"/><path d="M256 98 370 234 313 383H197L141 234Z" fill="#20213c"/><path d="M256 98 256 313 141 234Z" fill="#625290"/><path d="M256 98 370 234 256 313Z" fill="#99a9d8"/><path d="M197 383 256 313 313 383Z" fill="#58cbbd"/><circle cx="418" cy="94" r="26" fill="#58dfcf"/></svg>'''
(root/'obsydian.svg').write_text(svg)
im=Image.new('RGBA',(1024,1024));d=ImageDraw.Draw(im)
d.rounded_rectangle((0,0,1023,1023),radius=224,fill='#111526')
def polygon(points,fill):d.polygon([(x*2,y*2) for x,y in points],fill=fill)
polygon([(256,57),(424,233),(337,429),(167,429),(88,233)],'#9d9dea')
polygon([(256,98),(370,234),(313,383),(197,383),(141,234)],'#20213c')
polygon([(256,98),(256,313),(141,234)],'#625290')
polygon([(256,98),(370,234),(256,313)],'#99a9d8')
polygon([(197,383),(256,313),(313,383)],'#58cbbd')
d.ellipse((784,136,888,240),fill='#58dfcf')
im.save(root/'obsydian.png');im.save(root/'obsydian.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
im.save(root/'obsydian.icns')
