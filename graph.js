'use strict';
let graphState={running:false,complete:false,edges:0},referenceEdges=[],connectionRequest=0,graphTimer=null,graphBusy=false,graphPolling=false,graphRequested=false;
const graphPanel=document.createElement('section');graphPanel.className='graph-panel';
graphPanel.innerHTML='<div class="section-label" data-i18n="Automatic connections">Automatic connections</div><p id="graphStatus"></p>';
document.querySelector('.sidebar-bottom').before(graphPanel);
if(window.applyTranslations)window.applyTranslations();
const inspectButton=document.createElement('button');inspectButton.id='inspectReferences';inspectButton.textContent=t('Show connections');$('enter').after(inspectButton);
function updateGraphControls(){inspectButton.disabled=!state.selected;if(typeof updateActivity==='function')updateActivity()}
function graphDescription(){
  if(graphState.running)return t('Reading supported files…')+' '+Number(graphState.files||0).toLocaleString(locale)+' · '+Number(graphState.edges||0).toLocaleString(locale)+' '+t('references');
  if(graphState.stale)return t('Connections appear as supported files are scanned.');
  if(graphState.complete||graphState.cancelled)return Number(graphState.edges||0).toLocaleString(locale)+' '+t('resolved references')+' · '+(graphState.cancelled?t('partial index'):t('index complete'))+' · '+Number(graphState.skipped||0)+' '+t('skipped')+(graphState.limited?' · '+t('index limit reached'):'');
  return t('Connections appear as supported files are scanned.');
}
async function pollGraph(){
  if(state.closed)return;if(graphPolling){graphRequested=true;return}clearTimeout(graphTimer);graphPolling=true;graphRequested=false;
  try{graphState=await api('references/status');$('graphStatus').textContent=graphDescription();updateGraphControls();const path=state.selected?.path||state.path;if(path&&!state.applicationsView)await loadConnections(path)}catch(e){$('graphStatus').textContent=t('Connections appear as supported files are scanned.')}finally{graphPolling=false;if(!state.closed)graphTimer=setTimeout(pollGraph,graphRequested?100:1000)}
}
inspectButton.onclick=()=>{if(state.selected){loadConnections(state.selected.path);$('connections').scrollIntoView({block:'nearest',behavior:'smooth'})}};
async function loadConnections(path){
  const request=++connectionRequest;
  try{const r=await api('references?path='+encodeURIComponent(path));if(request!==connectionRequest||(state.selected?.path||state.path)!==path)return;
    referenceEdges=r.edges||[];const box=$('connections');box.replaceChildren();
    const summary=document.createElement('p');summary.textContent=referenceEdges.length?`${r.count??referenceEdges.length} `+t('resolved references')+(r.limited?' · '+t('showing a limited selection'):''):t('No resolved references in the current index.');box.append(summary);
    if(!graphState.complete){const note=document.createElement('p');note.textContent=graphState.running?t('Indexing in progress. Results are partial.'):t('Connections appear as supported files are scanned.');box.append(note)}
    for(const edge of referenceEdges.slice(0,40)){
      const b=document.createElement('button');b.className='reference-card';const source=edge.source,target=edge.target;
      const title=document.createElement('strong');title.textContent=baseName(source)+' → '+baseName(target);
      const detail=document.createElement('small');detail.textContent=edge.evidence;const paths=document.createElement('small');paths.textContent=source+' → '+target;
      b.append(title,detail,paths);b.title=t('Open referenced location');b.onclick=()=>revealReference(target);box.append(b);
    }
    draw();
  }catch(e){if(request===connectionRequest){referenceEdges=[];$('connections').textContent=e.message;draw()}}
}
function baseName(path){return path.replace(/[\\/]+$/,'').split(/[\\/]/).pop()||path}
async function revealReference(path){
  const parent=path.replace(/[\\/][^\\/]+$/,'');await children(parent);const n=state.items.find(n=>n.path===path);if(n)select(n);else toast(t('Location opened. Use search if the file is outside the visible selection.'));
}
function drawReferenceEdges(ctx,points){
  if(!referenceEdges.length)return;
  const normalized=p=>p.replaceAll('\\','/').toLowerCase();
  const find=path=>points.find(p=>normalized(p.n.item.path)===normalized(path))||points.find(p=>p.n.item.isDir&&normalized(path).startsWith(normalized(p.n.item.path)+'/'));
  const selected=points.find(p=>p.n.item.path===state.selected?.path)||{x:w/2,y:h/2,r:30};
  const ghosts=new Map();let index=0;
  function endpoint(path){const existing=find(path);if(existing)return existing;if(ghosts.has(path))return ghosts.get(path);const angle=-Math.PI/2+index*.67,rad=160+Math.floor(index/8)*40;index++;const g={x:Math.max(70,Math.min(w-80,selected.x+Math.cos(angle)*rad)),y:Math.max(95,Math.min(h-95,selected.y+Math.sin(angle)*rad)),r:6,path};ghosts.set(path,g);return g}
  ctx.save();for(const edge of referenceEdges.slice(0,16)){
    const a=endpoint(edge.source),b=endpoint(edge.target);if(a===b)continue;
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.quadraticCurveTo((a.x+b.x)/2,(a.y+b.y)/2-30,b.x,b.y);ctx.strokeStyle='#63e3dbbd';ctx.lineWidth=1.5;ctx.setLineDash([]);ctx.shadowColor='#67e7da';ctx.shadowBlur=7;ctx.stroke();ctx.shadowBlur=0;
    const angle=Math.atan2(b.y-a.y,b.x-a.x),tx=b.x-Math.cos(angle)*(b.r+5),ty=b.y-Math.sin(angle)*(b.r+5);ctx.beginPath();ctx.moveTo(tx,ty);ctx.lineTo(tx-Math.cos(angle-.45)*8,ty-Math.sin(angle-.45)*8);ctx.lineTo(tx-Math.cos(angle+.45)*8,ty-Math.sin(angle+.45)*8);ctx.closePath();ctx.fillStyle='#8af5e7';ctx.fill();
  }
  for(const p of ghosts.values()){ctx.beginPath();ctx.arc(p.x,p.y,6,0,7);ctx.fillStyle='#122c32';ctx.fill();ctx.strokeStyle='#77e9d9';ctx.stroke();ctx.textAlign='center';ctx.fillStyle='#a8e8e0';ctx.font='12px Segoe UI, sans-serif';const name=baseName(p.path);ctx.fillText(name.length>24?name.slice(0,22)+'…':name,p.x,p.y+19);ctx.fillStyle='#688d9a';ctx.font='10px Segoe UI, sans-serif';ctx.fillText(t('OTHER LOCATION'),p.x,p.y+31)}ctx.restore();
}
window.addEventListener('scanchange',()=>{clearTimeout(graphTimer);++connectionRequest;referenceEdges=[];graphState={running:false,complete:false,stale:true,edges:0};$('graphStatus').textContent=graphDescription();$('connections').replaceChildren();sceneMemory.clear();scenePreviews={};previewTime=0;transition=null;updateGraphControls();draw();pollGraph()});
window.addEventListener('languagechange',()=>{$('graphStatus').textContent=graphDescription();inspectButton.textContent=t('Show connections');if(state.selected)loadConnections(state.selected.path);draw()});
pollGraph();
