'use strict';
let trashPending=[],stopPending=false;
Object.assign(dictionary,{
  'Ready':'Pronto','No selection':'Nessuna selezione','Quit Obsydian':'Chiudi Obsydian','Quit Obsydian?':'Chiudere Obsydian?',
  'This stops scanning, background analysis and the local service.':'Interrompe scansione, analisi in background e servizio locale.',
  'Obsydian is closed':'Obsydian è chiuso','You can close this tab. Use Start Obsydian.cmd to open the app again.':'Puoi chiudere questa scheda. Usa Start Obsydian.cmd per riaprire l’app.',
  'Clear selection':'Deseleziona','Move selected to Recycle Bin':'Sposta selezionati nel cestino','Move selected items to Recycle Bin?':'Spostare gli elementi selezionati nel cestino?',
  'Move to Recycle Bin':'Sposta nel cestino','items selected':'elementi selezionati','Stopping…':'Interruzione…','Discovering connections…':'Ricerca connessioni…',
  'Automatic connections':'Connessioni automatiche','Connections appear as supported files are scanned.':'Le connessioni appaiono durante la scansione dei file supportati.',
  'Scanning…':'Scansione…','Working…':'Operazione in corso…','No permanent deletion. Items that are already missing will only be removed from the map.':'Nessuna eliminazione definitiva. Gli elementi già assenti verranno rimossi solo dalla mappa.',
  'Moving items to Recycle Bin…':'Spostamento degli elementi nel cestino…','removed from the map':'rimossi dalla mappa','could not be moved':'non spostati',
  'Stop the scan before modifying files.':'Interrompi la scansione prima di modificare i file.',
  'Protected items cannot be moved to Recycle Bin.':'Gli elementi protetti non possono essere spostati nel cestino.',
  'Middle-drag to pan · Ctrl/⌘-click to select multiple · Right-click for actions':'Rotellina premuta per spostarsi · Ctrl/⌘-clic per selezione multipla · Tasto destro per azioni',
  'Show connections':'Mostra connessioni','Local service stopped.':'Servizio locale arrestato.',
  'Stopping the application…':'Chiusura dell’applicazione…','errors':'errori'
});
document.querySelector('.scene-help').dataset.i18n='Middle-drag to pan · Ctrl/⌘-click to select multiple · Right-click for actions';
window.applyTranslations();
function updateActivity(){
  const working=state.running||graphState.running||starting;
  $('stopAll').disabled=!working||stopPending||state.closed;
  $('stopAll').textContent=t(stopPending?'Stopping…':'Stop scan');
  $('activitySummary').textContent=t(state.running?'Scanning…':graphState.running?'Discovering connections…':operationBusy?'Working…':'Ready');
}
function updateSelectionBar(){
  const count=state.selection.size;$('selectionBar').hidden=false;$('selectionCount').textContent=count?count+' '+t('items selected'):t('No selection');$('clearSelection').disabled=!count;
  const protectedItem=[...state.selection.values()].some(n=>n.application||n.readOnly||n.path===state.root||state.drives.some(d=>d.isDisk&&d.path===n.path));
  const disabled=!count||state.running||operationBusy||protectedItem;
  $('trashSelection').disabled=disabled;$('trash').disabled=disabled;
  $('trashSelection').title=state.running?t('Stop the scan before modifying files.'):protectedItem?t('Protected items cannot be moved to Recycle Bin.'):'';
  for(const row of $('list').children)row.classList.toggle('selected',state.selection.has(row.dataset.path));
  updateActivity();
}
$('clearSelection').onclick=()=>{state.selection.clear();state.selected=null;$('selection').hidden=true;$('selectionEmpty').hidden=false;updateSelectionBar();draw()};
function confirmTrashSelection(){
  if($('trashSelection').disabled)return;
  trashPending=[...state.selection.keys()];$('bulkDescription').textContent=trashPending.length+' '+t('items selected')+'. '+t('No permanent deletion. Items that are already missing will only be removed from the map.');
  $('bulkPaths').replaceChildren();for(const path of trashPending){const p=document.createElement('p');p.textContent=path;$('bulkPaths').append(p)}$('bulkError').textContent='';$('bulkDialog').showModal();
}
$('trashSelection').onclick=confirmTrashSelection;$('trash').onclick=confirmTrashSelection;$('trash').textContent=t('Move to Recycle Bin');
$('confirmTrash').onclick=async()=>{
  if(!trashPending.length||state.running||operationBusy)return;
  $('bulkDialog').close();busy(t('Moving items to Recycle Bin…'));
  try{
    const response=await api('actions',{action:'trash',paths:trashPending});const removed=new Set(response.results.filter(r=>r.ok).map(r=>r.path)),errors=response.results.filter(r=>!r.ok);
    for(const path of removed)state.selection.delete(path);
    state.items=state.items.filter(n=>!removed.has(n.path));nodes=nodes.filter(n=>!removed.has(n.item.path));state.selected=[...state.selection.values()].at(-1)||null;
    $('selection').hidden=!state.selected;$('selectionEmpty').hidden=!!state.selected;scenePreviews={};previewTime=0;referenceEdges=[];layout();renderList();updateSelectionBar();
    if(state.search)await refreshSearch();else await children(state.path,false);
    ensurePolling();pollGraph();
    toast(removed.size+' '+t('removed from the map')+(errors.length?' · '+errors.length+' '+t('could not be moved'):''));
    if(errors.length){trashPending=errors.map(r=>r.path);$('bulkDescription').textContent=errors.length+' '+t('could not be moved');$('bulkPaths').replaceChildren();for(const path of trashPending){const p=document.createElement('p');p.textContent=path;$('bulkPaths').append(p)}$('bulkError').textContent=errors.map(r=>r.path+': '+t(r.error)).join('\n');$('bulkDialog').showModal()}
  }catch(e){$('bulkError').textContent=e.message;$('bulkDialog').showModal()}finally{busy(null);updateSelectionBar()}
};
async function stopEverything(){
  if(stopPending)return;stopPending=true;updateActivity();
  try{await api('cancel',{});await api('references/cancel',{});ensurePolling();pollGraph()}catch(e){toast(e.message)}finally{stopPending=false;updateActivity()}
}
$('stopAll').onclick=stopEverything;$('cancelScan').onclick=stopEverything;
$('quitApp').onclick=()=>$('quitDialog').showModal();
$('confirmQuit').onclick=async()=>{
  $('quitDialog').close();busy(t('Stopping the application…'));state.closed=true;clearTimeout(pollTimer);clearTimeout(graphTimer);cancelAnimationFrame(animationFrame);
  try{await api('shutdown',{});$('closedScreen').hidden=false;document.title='Obsydian — '+t('Local service stopped.');$('operationOverlay').hidden=true}
  catch(e){state.closed=false;busy(null);toast(e.message);ensurePolling();pollGraph()}
};
document.addEventListener('keydown',e=>{
  if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)||document.querySelector('dialog[open]'))return;
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='a'){e.preventDefault();state.selection.clear();for(const n of state.items.slice(0,state.list?200:180))state.selection.set(n.path,n);state.selected=[...state.selection.values()].at(-1)||null;if(state.selected){$('selection').hidden=false;$('selectionEmpty').hidden=true;updateSelection()}updateSelectionBar();draw()}
  if(e.key==='Delete'&&state.selection.size){e.preventDefault();confirmTrashSelection()}
});
$('resetView').onclick=()=>resetCamera();
window.addEventListener('languagechange',()=>{$('trash').textContent=t('Move to Recycle Bin');updateSelectionBar()});
updateSelectionBar();

(async()=>{try{const info=await api('info');if(info.desktop&&info.trayAvailable){const button=document.createElement('button');button.id='minimizeTray';button.textContent=t('Hide to tray');button.onclick=()=>api('desktop',{action:'tray'}).catch(e=>toast(e.message));$('quitApp').before(button)}}catch{}})();
