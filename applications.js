'use strict';
let installedApplications=[],applicationsTimer=null,applicationsPrevious=null;
Object.assign(dictionary,{
  'Applications':'Applicazioni','Back to files':'Torna ai file','Installed applications':'Applicazioni installate',
  'Discovering installed applications…':'Ricerca delle applicazioni installate…',
  'Official uninstall…':'Disinstallazione ufficiale…','Open removal interface':'Apri procedura di rimozione',
  'Explore installation folder':'Esplora cartella di installazione','Review application removal':'Conferma apertura della rimozione',
  'The official system tool opens next. Follow its prompts. Removal of every component or user file is not guaranteed.':'Si aprirà lo strumento ufficiale del sistema. Segui le sue istruzioni. La rimozione di tutti i componenti e dati utente non è garantita.',
  'Installation location':'Percorso di installazione','Size reported by installer':'Dimensione dichiarata dall’installer',
  'Size not reported':'Dimensione non dichiarata','No installation location was declared.':'Nessun percorso di installazione dichiarato.',
  'Open the application removal interface to continue.':'Apri la procedura di rimozione per continuare.',
  'The official removal interface is open. Complete the operation there.':'La procedura ufficiale è aperta. Completa l’operazione nella sua finestra.',
  'Application metadata does not prove ownership of every file in this folder.':'I metadati dell’applicazione non provano la proprietà di ogni file della cartella.',
  'Official uninstaller':'Disinstallatore ufficiale','Windows Installed Apps':'App installate di Windows',
  'Review application in Finder':'Esamina applicazione nel Finder','Interactive system package manager':'Gestore pacchetti interattivo del sistema',
  'Use the system package manager to remove this application.':'Usa il gestore pacchetti del sistema per rimuovere questa applicazione.'
  ,'No applications were found.':'Nessuna applicazione trovata.'
  ,'Stop the current scan before exploring an application location.':'Interrompi la scansione corrente prima di esplorare il percorso dell’applicazione.'
});
const applicationsToggle=document.createElement('button');applicationsToggle.id='viewApplications';applicationsToggle.textContent=t('Applications');
document.querySelector('.view-switch').after(applicationsToggle);
const uninstallApplication=document.createElement('button');uninstallApplication.id='uninstallApplication';uninstallApplication.className='danger';uninstallApplication.hidden=true;
const applicationLocation=document.createElement('button');applicationLocation.id='applicationLocation';applicationLocation.hidden=true;
$('enter').after(applicationLocation,uninstallApplication);
const uninstallDialog=document.createElement('dialog');uninstallDialog.id='uninstallDialog';
uninstallDialog.innerHTML='<form method="dialog"><h2 data-i18n="Review application removal">Review application removal</h2><h3 id="uninstallName"></h3><p id="uninstallMethod"></p><pre id="uninstallCommand" style="white-space:pre-wrap;overflow-wrap:anywhere;max-width:650px"></pre><p data-i18n="The official system tool opens next. Follow its prompts. Removal of every component or user file is not guaranteed."></p><p id="uninstallError" role="alert"></p><div class="dialog-buttons"><button value="cancel" data-i18n="Cancel">Cancel</button><button id="confirmUninstall" type="button" class="danger" data-i18n="Open removal interface">Open removal interface</button></div></form>';
document.body.append(uninstallDialog);applyTranslations();
function updateApplicationControls(){
  const item=state.selected?.application?state.selected:null;
  uninstallApplication.hidden=!item;applicationLocation.hidden=!item?.installPath;
  uninstallApplication.disabled=!item?.app?.uninstallAvailable;
  uninstallApplication.textContent=t('Official uninstall…');applicationLocation.textContent=t('Explore installation folder');
  applicationsToggle.textContent=t(state.applicationsView?'Back to files':'Applications');
}
function applicationNodes(){return installedApplications.map(app=>({id:app.id,name:app.name,path:'@app:'+app.id,application:true,
  isDir:false,ext:'application',size:app.size||0,installPath:app.installPath,app,readOnly:true})).sort((a,b)=>b.size-a.size||a.name.localeCompare(b.name))}
async function showApplications(){
  ++navigationGeneration;++searchGeneration;clearTimeout(searchTimer);
  if(state.applicationsView){
    state.applicationsView=false;clearTimeout(applicationsTimer);state.selected=null;state.selection.clear();updateApplicationControls();
    $('selection').hidden=true;$('selectionEmpty').hidden=false;
    if(applicationsPrevious?.path){state.path=applicationsPrevious.path;await children(state.path)}
    else{state.path='';state.items=[];nodes=[];layout();renderList();$('empty').hidden=false;$('empty').querySelector('h2').textContent=t('A universe to explore.');}
    return;
  }
  applicationsPrevious={path:state.path};state.applicationsView=true;referenceEdges=[];edgeSignature='';state.path='@applications';state.selected=null;state.selection.clear();nodes=[];
  $('selection').hidden=true;$('selectionEmpty').hidden=false;$('search').value='';state.search=false;
  updateApplicationControls();await refreshApplications();
}
async function refreshApplications(){
  clearTimeout(applicationsTimer);if(!state.applicationsView||state.closed)return;
  try{const result=await api('applications');if(!state.applicationsView)return;installedApplications=result.items;
    applyItems(applicationNodes(),installedApplications.length,t('Installed applications'));
    $('up').disabled=true;$('sceneLabel').textContent=installedApplications.length+' '+t('Installed applications')+' · '+t('Size reported by installer');
    if(!installedApplications.length){$('empty').querySelector('h2').textContent=t(result.running?'Discovering installed applications…':'No applications were found.');$('empty').querySelector('p').textContent=t('Application metadata does not prove ownership of every file in this folder.')}
    if(state.selected?.application)showApplicationDetails(state.selected);
    if(result.running)applicationsTimer=setTimeout(refreshApplications,500);
  }catch(error){toast(error.message)}
}
function showApplicationDetails(item){
  if(!item?.application)return;const app=item.app;
  $('selection').hidden=false;$('selectionEmpty').hidden=true;$('fileName').textContent=app.name;
  $('filePath').textContent=[app.publisher,app.version,app.installPath].filter(Boolean).join(' · ');
  $('fileSize').textContent=app.size?fmt(app.size):t('Size not reported');$('fileIcon').textContent='⬡';
  $('enter').hidden=true;
  $('fileShare').textContent=t('Size reported by installer');$('fileMeter').style.width='0%';
  const box=$('connections');box.replaceChildren();
  for(const component of app.components){const title=document.createElement('strong');title.textContent=t('Installation location');const path=document.createElement('p');path.textContent=component.path;const evidence=document.createElement('small');evidence.textContent=component.evidence;box.append(title,path,evidence)}
  const note=document.createElement('p');note.textContent=t(app.components.length?'Application metadata does not prove ownership of every file in this folder.':'No installation location was declared.');box.append(note);
  referenceEdges=app.components.map(component=>({source:item.path,target:component.path,kind:'installation',confidence:'declared',evidence:component.evidence}));edgeSignature='';
  $('duplicateResults').replaceChildren();$('enter').hidden=true;for(const id of ['open','duplicates','rename','move','trash'])$(id).disabled=true;updateApplicationControls();
}
async function enterApplication(item){
  if(!item?.installPath)return toast(t('No installation location was declared.'));
  if(state.running)return toast(t('Stop the current scan before exploring an application location.'));
  $('includeSystem').checked=true;
  state.applicationsView=false;clearTimeout(applicationsTimer);updateApplicationControls();await scan(item.installPath);
}
applicationsToggle.onclick=showApplications;applicationLocation.onclick=()=>enterApplication(state.selected);
uninstallApplication.onclick=()=>{
  const app=state.selected?.app;if(!app?.uninstallAvailable)return;
  uninstallDialog.dataset.applicationId=app.id;$('uninstallName').textContent=app.name;$('uninstallMethod').textContent=t(app.method);
  $('uninstallCommand').textContent=app.officialCommand;$('uninstallError').textContent='';uninstallDialog.showModal();
};
$('confirmUninstall').onclick=async()=>{
  const button=$('confirmUninstall');button.disabled=true;
  try{await api('applications/uninstall',{id:uninstallDialog.dataset.applicationId,confirm:true});uninstallDialog.close();toast(t('The official removal interface is open. Complete the operation there.'))}
  catch(error){$('uninstallError').textContent=error.message}finally{button.disabled=false}
};
window.addEventListener('languagechange',()=>{updateApplicationControls();if(state.selected?.application)showApplicationDetails(state.selected);if(state.applicationsView)refreshApplications()});
