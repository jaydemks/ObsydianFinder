'use strict';
const $=id=>document.getElementById(id), state={root:'',path:'',parent:null,items:[],selected:null,running:false,drives:[],list:false,search:false,selection:new Map(),closed:false};
const fmt=n=>{if(!n)return '0 B';const k=Math.min(4,Math.floor(Math.log(n)/Math.log(1024)));return `${(n/1024**k).toLocaleString(locale,{maximumFractionDigits:k?1:0})} ${['B','KB','MB','GB','TB'][k]}`};
async function api(path,data){const r=await fetch('/api/'+path,{method:data?'POST':'GET',headers:{'X-Obsydian-Token':window.OBSYDIAN_TOKEN,...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined});const v=await r.json();if(!r.ok)throw Error(t(v.error)||t("Operation failed"));if(data&&(path==='scan'||path==='action'&&v.rescanning))window.dispatchEvent(new Event('scanchange'));return v}
let toastTimer;function toast(s){s=t(s);$('toast').textContent=s;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,6000)}
function color(n){return n.isDir?'#9c87ff':/\.(png|jpg|jpeg|webp|gif|mp4|mov|mp3|wav|mkv|flac)$/i.test(n.name)?'#60d4d0':/\.(pdf|docx?|txt|md|xlsx?|csv|odt)$/i.test(n.name)?'#ffc888':'#8394bb'}
async function loadDrives(){const {drives}=await api('drives');state.drives=drives;$('diskCount').textContent=drives.length;$('drives').replaceChildren();for(const d of drives){const b=document.createElement('button');b.className='disk';const name=document.createElement('strong');name.textContent='▱  '+t(d.label);const m=document.createElement('div');m.className='meter';const i=document.createElement('i');i.style.width=(100*(d.total-d.free)/d.total)+'%';m.append(i);const small=document.createElement('small');small.textContent=t('{free} free of {total}',{free:fmt(d.free),total:fmt(d.total)});b.append(name,m,small);b.onclick=()=>scan(d.path);$('drives').append(b)}}
let polling=false,pollTimer=null,pollRequested=false,scanEpoch=0,starting=false,navigationGeneration=0,operationBusy=false;
function busy(title){operationBusy=!!title;$('operationOverlay').hidden=!title;if(title)$('operationTitle').textContent=title;updateActionAvailability()}
function updateActionAvailability(){
  if(typeof updateApplicationControls==='function')updateApplicationControls();
  const locked=state.running||operationBusy||starting;
  for(const id of ['rename','move','trash','duplicates','open']){$(id).disabled=locked||!state.selected||!!state.selected?.readOnly||!!state.selected?.application;$(id).title=locked?t("Wait for a complete scan before managing files."):state.selected?.readOnly?t("System item: read only."):''}
  $('duplicates').disabled=$('duplicates').disabled||state.cancelled;$('actionLock').hidden=!locked&&!state.selected?.readOnly;
  $('actionLock').textContent=state.selected?.readOnly?t("🔒 System item: read only."):state.cancelled?t("🔒 Scan stopped: complete a new scan to manage files."):t("🔒 File actions are paused during scanning. You can explore and search.");
  for(const id of ['scanAll','scanCustom','refresh','includeSystem'])$(id).disabled=state.running||starting||operationBusy;
  document.querySelectorAll('.disk').forEach(b=>b.disabled=state.running||starting||operationBusy);if(typeof updateGraphControls==='function')updateGraphControls();if(typeof updateSelectionBar==='function')updateSelectionBar();
}
async function scan(path){
  if(starting||state.running||operationBusy)return;
  if(!path)return toast(t("Enter the full path to a folder."));
  starting=true;++scanEpoch;updateActionAvailability();++searchGeneration;++navigationGeneration;clearTimeout(searchTimer);
  try{
    const result=await api('scan',{path,all:path==='@computer',includeSystem:$('includeSystem').checked});
    state.applicationsView=false;state.root=result.root||path;state.path=state.root;state.search=false;state.cancelled=false;state.running=true;
    $('search').value='';state.selected=null;$('selection').hidden=true;$('selectionEmpty').hidden=false;state.items=[];state.selection.clear();nodes=[];layout();renderList();
    $('empty').hidden=false;$('empty').querySelector('h2').textContent=t("Your space is taking shape.");$('empty').querySelector('p').textContent=t("The first bubbles appear as files and folders are discovered.");
    $('scanNotice').hidden=false;$('scanNotice').classList.remove('stopped');$('cancelScan').disabled=false;
    const ds=path==='@computer'?state.drives.filter(d=>d.isDisk):state.drives.filter(d=>path.toLowerCase().startsWith(d.path.toLowerCase())).sort((a,b)=>b.path.length-a.path.length).slice(0,1);
    $('statFree').textContent=ds.length?fmt(ds.reduce((sum,d)=>sum+d.free,0)):'—';$('diskLabel').textContent=path==='@computer'?t("All connected drives"):(ds[0]?.label?t(ds[0].label):'')||t("On the selected drive");
    ensurePolling();
  }catch(e){toast(e.message)}finally{starting=false;updateActionAvailability()}
}
function ensurePolling(){clearTimeout(pollTimer);if(polling){pollRequested=true;return}poll()}
async function poll(){
  if(state.closed||polling)return;polling=true;pollRequested=false;const epoch=scanEpoch;let retry=false;
  try{
    const s=await api('status');if(epoch!==scanEpoch)return;state.running=s.running;state.cancelled=!!s.cancelled;state.root=s.root||state.root;
    if(!state.path&&s.root)state.path=s.root;
    $('statSize').textContent=fmt(s.bytes);$('statFiles').textContent=Number(s.files).toLocaleString(locale);
    $('statState').textContent=s.running?t("Scanning · partial results"):s.cancelled?t("Stopped · partial results"):s.complete?t("Scan complete"):t("Choose a drive to begin");
    $('scanNotice').hidden=!s.running&&!s.cancelled;
    $('scanNotice').classList.toggle('stopped',!!s.cancelled&&!s.running);
    $('scanTitle').textContent=s.running?t("The map grows in real time"):t("Scan stopped · results preserved");
    $('scanDetail').textContent=s.running?t('{files} files · {bytes} discovered · sizes are still partial',{files:Number(s.files).toLocaleString(locale),bytes:fmt(s.bytes)}):t("Explore the partial results or start a new scan.");
    $('cancelScan').hidden=!s.running;
    $('progress').textContent=t('{status} · {excluded} excluded · {errors} inaccessible{current}',{status:s.running?t('Scanning'):s.cancelled?t('Stopped'):t('Scan finished'),excluded:s.excluded||0,errors:s.errors||0,current:s.current?' · '+s.current:''});
    if(typeof updateActivity==='function')updateActivity();if(s.root&&!state.applicationsView){if(state.search)await refreshSearch();else await children(state.path||s.root,false)}
    updateActionAvailability();retry=s.running;
  }catch(e){toast(t("Update temporarily unavailable: ")+e.message);retry=state.running}
  finally{polling=false;if(pollRequested||epoch!==scanEpoch)pollTimer=setTimeout(poll,0);else if(retry)pollTimer=setTimeout(poll,500)}
}
function applyItems(items,count,label){for(const [path] of state.selection){const item=items.find(n=>n.path===path);if(item)state.selection.set(path,item);else if(!state.running)state.selection.delete(path)}
  state.items=items;$('breadcrumb').textContent=label;$('breadcrumb').title=label;$('empty').hidden=items.length>0;
  if(!items.length){$('empty').querySelector('h2').textContent=state.running?t("Waiting for more results…"):t("No visible items.");$('empty').querySelector('p').textContent=state.running?t("Scanning continues. You can explore other folders."):t("This folder is empty, inaccessible, or has no matching results.")}
  layout();renderList();if(typeof updateSelectionBar==='function')updateSelectionBar();
  $('sceneLabel').textContent=t('{partial}{bubbles} BUBBLES · {listed} IN LIST · {count} ITEMS',{partial:state.running||state.cancelled?t('PARTIAL · '):'',bubbles:Math.min(180,items.length),listed:items.length,count:count.toLocaleString(locale)});
  if(state.selected){const fresh=items.find(n=>n.path===state.selected.path);if(fresh){state.selected=fresh;updateSelection()}else if(!state.running){state.selected=null;$('selection').hidden=true;$('selectionEmpty').hidden=false}}
}
async function children(path,reset=true){
  if(!path)return;
  const sceneSnapshot=reset?captureScene(path):null;if(reset){++searchGeneration;clearTimeout(searchTimer);$('search').value='';state.search=false;state.path=path}
  const generation=++navigationGeneration;
  try{const v=await api('children?path='+encodeURIComponent(path));if(generation!==navigationGeneration||state.search)return;
    state.applicationsView=false;state.path=v.path;state.viewTotal=v.total;state.parent=v.parent;$('up').disabled=!v.parent;
    if(reset){state.selection.clear();yaw=0;pitch=.2;zoom=1;panX=panY=0;nodes=[];state.selected=null;$('selection').hidden=true;$('selectionEmpty').hidden=false}
    applyItems(v.items,v.count,v.path==='@computer'?t("Entire computer"):v.path);if(reset){transitionTo(sceneSnapshot);previewTime=0;refreshPreviews()}
  }catch(e){if(generation===navigationGeneration)toast(e.message)}
}
async function refreshSearch(){
  const q=$('search').value.trim(),generation=searchGeneration;if(!q)return;
  try{const r=await api('search?q='+encodeURIComponent(q));if(generation!==searchGeneration||!state.search)return;applyItems(r.items,r.count,t('Search: {query} · {count} results',{query:q,count:r.count}))}catch(e){toast(e.message)}
}
function select(n,additive=false){if(!additive)state.selection.clear();if(additive&&state.selection.has(n.path))state.selection.delete(n.path);else state.selection.set(n.path,n);state.selected=state.selection.get(n.path)||[...state.selection.values()].at(-1)||null;$('selection').hidden=!state.selected;$('selectionEmpty').hidden=!!state.selected;$('duplicateResults').replaceChildren();updateSelection();if(typeof updateSelectionBar==='function')updateSelectionBar();if(!n.application&&typeof loadConnections==='function')loadConnections(state.selected?.path||state.path);draw()}
function updateSelection(){
  const n=state.selected;if(!n)return;if(n.application){showApplicationDetails(n);return;}
  $('fileName').textContent=n.name;$('filePath').textContent=n.path;$('fileSize').textContent=fmt(n.size)+(n.partial?' +':'');$('fileIcon').textContent=n.isDir?'◈':'◇';$('fileIcon').style.color=color(n);
  const total=state.items.reduce((s,x)=>s+x.size,0),pct=total?n.size/total*100:0;$('fileMeter').style.width=Math.min(100,pct)+'%';$('fileShare').textContent=pct.toLocaleString(locale,{maximumFractionDigits:1})+t("% of displayed items")+(n.partial?t(" · still calculating"):'');
  $('enter').hidden=!n.isDir;$('duplicates').hidden=n.isDir;updateActionAvailability();
}

function renderList(){const list=$('list'),existing=new Map([...list.children].map(row=>[row.dataset.path,row]));for(const [index,n] of state.items.entries()){let row=existing.get(n.path);if(row){existing.delete(n.path);row.children[2].textContent=n.isDir?t('Folder'):n.ext||'File';row.children[1].textContent=fmt(n.size)+(n.partial?' +':'');row.onclick=e=>select(n,e.ctrlKey||e.metaKey||e.shiftKey);row.ondblclick=()=>n.application?enterApplication(n):n.isDir?children(n.path):select(n);if(list.children[index]!==row)list.insertBefore(row,list.children[index]||null);continue}row=document.createElement('button');row.dataset.path=n.path;row.className='list-row';const a=document.createElement('span');a.textContent=(n.isDir?'◈  ':'◇  ')+n.name;a.style.color=color(n);const b=document.createElement('span');b.textContent=fmt(n.size)+(n.partial?' +':'');const c=document.createElement('small');c.textContent=n.isDir?t("Folder"):n.ext||'File';row.append(a,b,c);row.onclick=e=>select(n,e.ctrlKey||e.metaKey||e.shiftKey);row.ondblclick=()=>n.isDir?children(n.path):select(n);list.insertBefore(row,list.children[index]||null)}for(const row of existing.values())row.remove()}
function view(list){state.list=list;labels.hidden=list;$('list').hidden=!list;canvas.hidden=list;$('viewList').classList.toggle('active',list);$('view3d').classList.toggle('active',!list);draw()}$('viewList').onclick=()=>view(true);$('view3d').onclick=()=>view(false);$('resetView').onclick=()=>{yaw=0;pitch=.2;zoom=1;nodes=[];layout()};$('up').onclick=()=>children(state.parent);$('enter').onclick=()=>children(state.selected.path);$('overview').onclick=()=>children(state.root);$('scanCustom').onclick=()=>scan($('rootPath').value.trim());$('rootPath').onkeydown=e=>{if(e.key==='Enter')$('scanCustom').click()};$('refresh').onclick=()=>scan(state.root||$('rootPath').value.trim());
let searchTimer,searchGeneration=0;
$('search').oninput=()=>{clearTimeout(searchTimer);++searchGeneration;++navigationGeneration;searchTimer=setTimeout(()=>{if(!state.root)return;state.search=!!$('search').value.trim();if(state.search)refreshSearch();else children(state.path)},250)};
document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();$('search').focus()}});
let pending=null;function actionDialog(action){if(!state.selected||state.running||operationBusy)return;pending={action,path:state.selected.path};const titles={rename:t("Rename item"),move:t("Move item"),trash:t("Move to trash")};$('dialogTitle').textContent=titles[action];$('dialogDescription').textContent=state.selected.path+(action==='move'?t(" — This changes the actual file location on disk."):'');$('dialogLabel').textContent=action==='rename'?t("New name"):action==='move'?t("Full path to the destination folder"):t("The file will be moved from this folder to the system trash.");$('dialogInput').hidden=action==='trash';$('dialogInput').value=action==='rename'?state.selected.name:'';$('dialogError').textContent='';$('actionDialog').showModal();if(action!=='trash')$('dialogInput').focus()}
for(const action of ['rename','move','trash'])$(action).onclick=()=>actionDialog(action);
$('confirmAction').onclick=async()=>{if(!pending||state.running)return;const b=$('confirmAction');b.disabled=true;$('actionDialog').close();busy(t("Updating the file…"));try{const data={...pending};if(data.action==='rename')data.name=$('dialogInput').value.trim();if(data.action==='move')data.destination=$('dialogInput').value.trim();const result=await api('action',data);$('actionDialog').close();toast(t("Done. Refreshing the map."));state.selected=null;state.selection.clear();$('selection').hidden=true;$('selectionEmpty').hidden=false;scenePreviews={};previewTime=0;if(state.search)await refreshSearch();else await children(state.path,false);ensurePolling();if(typeof pollGraph==='function')pollGraph()}catch(e){$('dialogError').textContent=e.message;$('actionDialog').showModal()}finally{b.disabled=false;busy(null)}};
$('open').onclick=async()=>{if(!state.selected)return;try{await api('action',{action:'open',path:state.selected.path});toast(t("Item revealed in your file manager."))}catch(e){toast(e.message)}};
$('duplicates').onclick=async()=>{const n=state.selected;if(!n)return;busy(t("Checking for duplicates…"));$('duplicates').disabled=true;$('duplicateResults').textContent=t("Comparing file contents…");try{const r=await api('duplicates',{path:n.path});if(state.selected?.path!==n.path)return;const box=$('duplicateResults');box.textContent=r.items.length?t('{count} identical copies confirmed (SHA-256).',{count:r.items.length}):t("No identical copies in the scanned files.");for(const item of r.items){const b=document.createElement('button');b.textContent=item.path;b.onclick=()=>select(item);box.append(b)}if(r.errors){const p=document.createElement('p');p.textContent=t('{count} files could not be checked.',{count:r.errors});box.append(p)}}catch(e){$('duplicateResults').textContent=e.message}finally{busy(null);updateActionAvailability()}};
document.addEventListener('DOMContentLoaded',()=>loadDrives().then(()=>ensurePolling()).catch(e=>toast(t("Could not connect to the local service: ")+e.message)));


$('trash').textContent=t("Manage trash in file manager ↗");$('trash').onclick=()=>{toast(t("Use your system trash from the file manager window."));$('open').click()};

$('scanAll').onclick=()=>scan('@computer');
$('cancelScan').onclick=async()=>{try{$('cancelScan').disabled=true;await api('cancel',{});$('scanDetail').textContent=t("Stopping. Preserving the results collected so far…");ensurePolling()}catch(e){toast(e.message);$('cancelScan').disabled=false}};

window.addEventListener('languagechange',()=>{renderList();if(state.selected)updateSelection();ensurePolling();});

