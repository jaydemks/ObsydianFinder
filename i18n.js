'use strict';
const dictionary={
  "Explore your space": "Esplora il tuo spazio",
  "YOUR UNIVERSE": "IL TUO UNIVERSO",
  "Explore space": "Esplora lo spazio",
  "CONNECTED DRIVES": "DISCHI CONNESSI",
  "Scan entire computer": "Analizza tutto il computer",
  "Include system folders (read only)": "Includi cartelle di sistema (sola lettura)",
  "Scan a folder": "Scansiona una cartella",
  "Scan folder ↗": "Analizza cartella ↗",
  "Local and private": "Locale e privato",
  "Your files stay on your computer.": "I tuoi file restano sul tuo computer.",
  "A NEW PERSPECTIVE ON YOUR FILES": "UNA NUOVA PROSPETTIVA SUI TUOI FILE",
  "Every byte, in its place": "Ogni byte, al suo posto",
  "Search scanned files…": "Cerca nei file analizzati…",
  "Search files": "Cerca file",
  "SCANNED SIZE": "SPAZIO ANALIZZATO",
  "Logical file size": "Dimensione logica dei file",
  "FILES DISCOVERED": "FILE ESPLORATI",
  "Choose a drive to begin": "Scegli un disco per iniziare",
  "AVAILABLE SPACE": "SPAZIO DISPONIBILE",
  "On the selected drive": "Sul disco selezionato",
  "YOUR SPACE, EXPLAINED": "IL TUO SPAZIO, IN CHIARO",
  "Discover what takes space.": "Scopri cosa pesa.",
  "Find what matters.": "Ritrova ciò che conta.",
  "3D universe": "Universo 3D",
  "List": "Elenco",
  "Parent folder": "Cartella superiore",
  "Up": "Risali",
  "Your computer": "Il tuo computer",
  "Reset bubble positions": "Ripristina posizione delle bolle",
  "Center": "Centra",
  "Scanning": "Analisi in corso",
  "The map updates as files are discovered.": "La mappa si aggiorna progressivamente.",
  "Stop scan": "Interrompi",
  "Three-dimensional folder map. A list view is also available.": "Mappa tridimensionale delle cartelle. È disponibile anche la vista Elenco.",
  "A universe to explore.": "Un universo da esplorare.",
  "Choose a drive or folder.": "Seleziona un disco o una cartella.",
  "Bubbles reveal how its space is used.": "Le bolle ne riveleranno la distribuzione dello spazio.",
  "WAITING FOR A SCAN": "IN ATTESA DI UNA SCANSIONE",
  "Folders": "Cartelle",
  "Documents": "Documenti",
  "Other files": "Altri file",
  "Drag the background to rotate · Scroll to zoom · Double-click to enter": "Trascina lo sfondo per ruotare · Rotella per zoom · Doppio clic per entrare",
  "Ready. Choose where to begin.": "Pronto. Scegli da dove iniziare.",
  "Refresh scan": "Aggiorna scansione",
  "INSPECTOR": "ISPETTORE",
  "Follow the connections.": "Segui le connessioni.",
  "Select a bubble to inspect its size, explore it, and manage files.": "Seleziona una bolla per conoscere il suo peso, esplorarla e gestire i file.",
  "LOGICAL SIZE": "DIMENSIONE LOGICA",
  "CONNECTIONS": "CONNESSIONI",
  "🔒 File actions are paused during scanning. You can explore and search.": "🔒 Operazioni sospese durante la scansione. Puoi esplorare la mappa e cercare.",
  "Explore folder ↗": "Esplora cartella ↗",
  "Show in file manager ↗": "Mostra nel sistema ↗",
  "Check duplicates": "Verifica duplicati",
  "Rename": "Rinomina",
  "Move to a folder…": "Sposta in una cartella…",
  "Move to trash": "Sposta nel cestino",
  "Sizes tell a story.": "Dimensioni che raccontano.",
  "Larger bubbles represent larger files; a minimum size keeps small files visible. Lines show the containing folder.": "Le bolle più grandi indicano file più pesanti; una dimensione minima mantiene visibili quelli piccoli. Le linee indicano la cartella che li contiene.",
  "Drag a bubble to arrange the map. Use Move to change the actual file location.": "Trascina una bolla per disporla nella mappa. Per spostare davvero un file usa «Sposta».",
  "Working…": "Operazione in corso…",
  "Please wait before starting another operation.": "Attendi il completamento prima di avviare altre operazioni.",
  "FILE ACTIONS": "GESTIONE FILE",
  "Cancel": "Annulla",
  "Confirm": "Conferma",
  "Operation failed": "Operazione non riuscita",
  "Wait for a complete scan before managing files.": "Attendi una scansione completa prima di gestire i file.",
  "System item: read only.": "Elemento di sistema: sola lettura.",
  "🔒 System item: read only.": "🔒 Elemento di sistema: sola lettura.",
  "🔒 Scan stopped: complete a new scan to manage files.": "🔒 Scansione interrotta: completa una nuova analisi per gestire i file.",
  "Enter the full path to a folder.": "Inserisci il percorso completo di una cartella.",
  "Your space is taking shape.": "Il tuo spazio prende forma.",
  "The first bubbles appear as files and folders are discovered.": "Le prime bolle appariranno appena troviamo file e cartelle.",
  "All connected drives": "Tutti i dischi collegati",
  "Scanning · partial results": "Analisi in corso · dati parziali",
  "Stopped · partial results": "Interrotta · dati parziali",
  "Scan complete": "Analisi completata",
  "The map grows in real time": "La mappa cresce in tempo reale",
  "Scan stopped · results preserved": "Scansione interrotta · risultati conservati",
  "Explore the partial results or start a new scan.": "Puoi esplorare i risultati parziali o avviare una nuova scansione.",
  "Stopped": "Interrotta",
  "Scan finished": "Analisi terminata",
  "Update temporarily unavailable: ": "Aggiornamento momentaneamente non disponibile: ",
  "Waiting for more results…": "In attesa dei prossimi risultati…",
  "No visible items.": "Nessun elemento visibile.",
  "Scanning continues. You can explore other folders.": "La scansione continua. Puoi navigare nelle altre cartelle.",
  "This folder is empty, inaccessible, or has no matching results.": "La cartella è vuota, non accessibile o non contiene risultati corrispondenti.",
  "PARTIAL · ": "PARZIALE · ",
  "Entire computer": "Tutto il computer",
  "% of displayed items": "% degli elementi visualizzati",
  " · still calculating": " · calcolo in corso",
  "Folder": "Cartella",
  "Rename item": "Rinomina elemento",
  "Move item": "Sposta elemento",
  " — This changes the actual file location on disk.": " — Lo spostamento modifica davvero il percorso sul disco.",
  "New name": "Nuovo nome",
  "Full path to the destination folder": "Percorso completo della cartella di destinazione",
  "The file will be moved from this folder to the system trash.": "Il file sarà rimosso da questa cartella e inviato al cestino del sistema.",
  "Updating the file…": "Modifica del file in corso…",
  "Done. Refreshing the map.": "Operazione completata. Aggiorno la mappa.",
  "Item revealed in your file manager.": "Elemento aperto nel sistema.",
  "Checking for duplicates…": "Verifica dei duplicati in corso…",
  "Comparing file contents…": "Confronto del contenuto in corso…",
  "No identical copies in the scanned files.": "Nessuna copia identica nei file analizzati.",
  "Could not connect to the local service: ": "Connessione al servizio locale non riuscita: ",
  "Manage trash in file manager ↗": "Gestisci cestino nel sistema ↗",
  "Use your system trash from the file manager window.": "Usa il cestino del sistema dalla finestra che si apre.",
  "Stopping. Preserving the results collected so far…": "Interruzione richiesta. Conservo i risultati raccolti…",
  "Home folder": "Cartella personale",
  "Language": "Lingua",
  "Waiting…": "In attesa…",
  "Double-click to enter": "Doppio clic per entrare",
  "Right-click for actions": "Clic destro per le azioni",
  "Folders & projects": "Cartelle e progetti",
  "Code & other files": "Codice e altri file",
  "Enter folder": "Entra nella cartella",
  "Show in system": "Mostra nel sistema",
  "Verify duplicates": "Verifica duplicati",
  "Move to folder…": "Sposta nella cartella…",
  "Manage trash in system": "Gestisci cestino nel sistema",
  "REFERENCE GRAPH": "GRAFO DEI RIFERIMENTI",
  "Index connections": "Indicizza connessioni",
  "Stop indexing": "Interrompi indicizzazione",
  "Show connections": "Mostra connessioni",
  "Reading supported files…": "Lettura dei file supportati…",
  "references": "riferimenti",
  "Scan changed. Rebuild the reference index.": "Scansione modificata. Ricostruisci l’indice dei riferimenti.",
  "resolved references": "riferimenti risolti",
  "partial index": "indice parziale",
  "index complete": "indice completo",
  "skipped": "saltati",
  "index limit reached": "limite dell’indice raggiunto",
  "Index file paths and imports after the scan. No runtime dependencies are inferred.": "Indicizza percorsi e importazioni dopo la scansione. Non vengono dedotte dipendenze di esecuzione.",
  "Reference index unavailable. Restart the updated service.": "Indice dei riferimenti non disponibile. Riavvia il servizio aggiornato.",
  "showing a limited selection": "selezione limitata",
  "No resolved references in the current index.": "Nessun riferimento risolto nell’indice corrente.",
  "Indexing in progress. Results are partial.": "Indicizzazione in corso. I risultati sono parziali.",
  "Use “Index connections” after scanning to inspect supported text files.": "Usa «Indicizza connessioni» dopo la scansione per esaminare i file di testo supportati.",
  "Open referenced location": "Apri il percorso indicato",
  "Location opened. Use search if the file is outside the visible selection.": "Percorso aperto. Usa la ricerca se il file non è nella selezione visibile.",
  "OTHER LOCATION": "ALTRO PERCORSO",
  "An absolute path is required.": "È richiesto un percorso assoluto.",
  "Symlinks and junctions are not allowed.": "Collegamenti e junction non sono consentiti.",
  "The path is outside the scanned folders.": "Il percorso è esterno alle cartelle analizzate.",
  "Protected system path: read-only access is available.": "Percorso di sistema protetto: disponibile solo in lettura.",
  "The path no longer exists. Scan again.": "Il percorso non esiste più. Ripeti la scansione.",
  "A scan is already running.": "Una scansione è già in corso.",
  "Select an accessible absolute folder path.": "Seleziona il percorso assoluto di una cartella accessibile.",
  "Symlinks and junctions cannot be scanned.": "Non è possibile analizzare collegamenti e junction.",
  "No accessible disks were found.": "Nessun disco accessibile trovato.",
  "This folder is not available. Wait for the scan or scan again.": "Cartella non disponibile. Attendi o ripeti la scansione.",
  "Complete a scan before checking duplicates.": "Completa una scansione prima di verificare i duplicati.",
  "Select a scanned file.": "Seleziona un file analizzato.",
  "The file changed during comparison. Try again.": "Il file è cambiato durante il confronto. Riprova.",
  "Complete a scan before modifying files.": "Completa una scansione prima di modificare i file.",
  "The scan root cannot be modified.": "La radice analizzata non può essere modificata.",
  "Invalid file name.": "Nome del file non valido.",
  "The destination must be a folder.": "La destinazione deve essere una cartella.",
  "An item with this name already exists.": "Esiste già un elemento con questo nome.",
  "A folder cannot be moved into itself.": "Non puoi spostare una cartella dentro se stessa.",
  "Unknown action.": "Azione sconosciuta.",
  "The Windows Recycle Bin is unavailable in this preview. Use Show in File Explorer to manage the file.": "Il Cestino Windows non è disponibile in questa anteprima. Usa Mostra in Esplora file per gestire il file.",
  "The Trash is unavailable.": "Cestino non disponibile.",
  "Desktop Trash is unavailable. Install gio to use this action.": "Cestino desktop non disponibile. Installa gio per usare questa azione.",
  "Trash is unavailable for this path.": "Cestino non disponibile per questo percorso.",
  "Host is not allowed.": "Host non consentito.",
  "Origin is not allowed.": "Origine non consentita.",
  "Unauthorized session. Reload the page.": "Sessione non autorizzata. Ricarica la pagina.",
  "The request is too large.": "Richiesta troppo grande.",
  "Invalid request.": "Richiesta non valida.",
  "Endpoint not found.": "Endpoint non trovato.",
  "Method not allowed.": "Metodo non consentito.",
  "File not found.": "File non trovato.",
  "Interface files not found.": "Interfaccia non trovata.",
  "Right-click for actions · Double-click to enter · Alt + ← to go up": "Clic destro per le azioni · Doppio clic per entrare · Alt + ← per risalire",
  "Live nested previews show the largest items inside each folder.": "Le anteprime annidate mostrano gli elementi più grandi in ogni cartella.",
  "Open folder": "Apri cartella",
  "Go up": "Risali",
  "Show in file manager": "Mostra nel sistema",
  "Move…": "Sposta…",
  "Copy path": "Copia percorso",
  "Path copied": "Percorso copiato",
  "Expand preview": "Espandi anteprima",
  "Collapse preview": "Comprimi anteprima",
  "Loading preview…": "Caricamento anteprima…",
  "Partial results": "Risultati parziali",
  "{free} free of {total}": "{free} liberi di {total}",
  "{files} files · {bytes} discovered · sizes are still partial": "{files} file · {bytes} rilevati · dimensioni ancora parziali",
  "{status} · {excluded} excluded · {errors} inaccessible{current}": "{status} · {excluded} esclusi · {errors} non accessibili{current}",
  "{partial}{bubbles} BUBBLES · {listed} IN LIST · {count} ITEMS": "{partial}{bubbles} BOLLE · {listed} IN ELENCO · {count} ELEMENTI",
  "Search: {query} · {count} results": "Ricerca: {query} · {count} risultati",
  "{count} identical copies confirmed (SHA-256).": "{count} copie identiche confermate (SHA-256).",
  "{count} files could not be checked.": "{count} file non verificabili."
};
const reverse={"Esplora il tuo spazio":"Explore your space","IL TUO UNIVERSO":"YOUR UNIVERSE","Esplora lo spazio":"Explore space","DISCHI CONNESSI":"CONNECTED DRIVES","Analizza tutto il computer":"Scan entire computer","Includi cartelle di sistema (sola lettura)":"Include system folders (read only)","Scansiona una cartella":"Scan a folder","Analizza cartella ↗":"Scan folder ↗","Locale e privato":"Local and private","I tuoi file restano sul tuo computer.":"Your files stay on your computer.","UNA NUOVA PROSPETTIVA SUI TUOI FILE":"A NEW PERSPECTIVE ON YOUR FILES","Ogni byte, al suo posto":"Every byte, in its place","Cerca nei file analizzati…":"Search scanned files…","Cerca file":"Search files","SPAZIO ANALIZZATO":"SCANNED SIZE","Dimensione logica dei file":"Logical file size","FILE ESPLORATI":"FILES DISCOVERED","Scegli un disco per iniziare":"Choose a drive to begin","SPAZIO DISPONIBILE":"AVAILABLE SPACE","Sul disco selezionato":"On the selected drive","IL TUO SPAZIO, IN CHIARO":"YOUR SPACE, EXPLAINED","Scopri cosa pesa.":"Discover what takes space.","Ritrova ciò che conta.":"Find what matters.","Universo 3D":"3D universe","Elenco":"List","Cartella superiore":"Parent folder","Risali":"Up","Il tuo computer":"Your computer","Ripristina posizione delle bolle":"Reset bubble positions","Centra":"Center","Scansione in corso":"Scanning","La mappa si aggiorna progressivamente.":"The map updates as files are discovered.","Interrompi":"Stop scan","Mappa tridimensionale delle cartelle. È disponibile anche la vista Elenco.":"Three-dimensional folder map. A list view is also available.","Un universo da esplorare.":"A universe to explore.","Seleziona un disco o una cartella.":"Choose a drive or folder.","Le bolle ne riveleranno la distribuzione dello spazio.":"Bubbles reveal how its space is used.","IN ATTESA DI UNA SCANSIONE":"WAITING FOR A SCAN","Cartelle":"Folders","Documenti":"Documents","Altri file":"Other files","Trascina lo sfondo per ruotare · Rotella per zoom · Doppio clic per entrare":"Drag the background to rotate · Scroll to zoom · Double-click to enter","Pronto. Scegli da dove iniziare.":"Ready. Choose where to begin.","Aggiorna scansione":"Refresh scan","ISPETTORE":"INSPECTOR","Segui le connessioni.":"Follow the connections.","Seleziona una bolla per conoscere il suo peso, esplorarla e gestire i file.":"Select a bubble to inspect its size, explore it, and manage files.","DIMENSIONE LOGICA":"LOGICAL SIZE","CONNESSIONI":"CONNECTIONS","🔒 Operazioni sospese durante la scansione. Puoi esplorare la mappa e cercare.":"🔒 File actions are paused during scanning. You can explore and search.","Esplora cartella ↗":"Explore folder ↗","Mostra nel sistema ↗":"Show in file manager ↗","Verifica duplicati":"Check duplicates","Rinomina":"Rename","Sposta in una cartella…":"Move to a folder…","Sposta nel cestino":"Move to trash","Dimensioni che raccontano.":"Sizes tell a story.","Le bolle più grandi indicano file più pesanti; una dimensione minima mantiene visibili quelli piccoli. Le linee indicano la cartella che li contiene.":"Larger bubbles represent larger files; a minimum size keeps small files visible. Lines show the containing folder.","Trascina una bolla per disporla nella mappa. Per spostare davvero un file usa «Sposta».":"Drag a bubble to arrange the map. Use Move to change the actual file location.","Operazione in corso…":"Working…","Attendi il completamento prima di avviare altre operazioni.":"Please wait before starting another operation.","GESTIONE FILE":"FILE ACTIONS","Annulla":"Cancel","Conferma":"Confirm","Operazione non riuscita":"Operation failed","Attendi una scansione completa prima di gestire i file.":"Wait for a complete scan before managing files.","Elemento di sistema: sola lettura.":"System item: read only.","🔒 Elemento di sistema: sola lettura.":"🔒 System item: read only.","🔒 Scansione interrotta: completa una nuova analisi per gestire i file.":"🔒 Scan stopped: complete a new scan to manage files.","Inserisci il percorso completo di una cartella.":"Enter the full path to a folder.","Il tuo spazio prende forma.":"Your space is taking shape.","Le prime bolle appariranno appena troviamo file e cartelle.":"The first bubbles appear as files and folders are discovered.","Tutti i dischi collegati":"All connected drives","Analisi in corso · dati parziali":"Scanning · partial results","Interrotta · dati parziali":"Stopped · partial results","Analisi completata":"Scan complete","La mappa cresce in tempo reale":"The map grows in real time","Scansione interrotta · risultati conservati":"Scan stopped · results preserved","Puoi esplorare i risultati parziali o avviare una nuova scansione.":"Explore the partial results or start a new scan.","Analisi in corso":"Scanning","Interrotta":"Stopped","Analisi terminata":"Scan finished","Aggiornamento momentaneamente non disponibile: ":"Update temporarily unavailable: ","In attesa dei prossimi risultati…":"Waiting for more results…","Nessun elemento visibile.":"No visible items.","La scansione continua. Puoi navigare nelle altre cartelle.":"Scanning continues. You can explore other folders.","La cartella è vuota, non accessibile o non contiene risultati corrispondenti.":"This folder is empty, inaccessible, or has no matching results.","PARZIALE · ":"PARTIAL · ","Tutto il computer":"Entire computer","% degli elementi visualizzati":"% of displayed items"," · calcolo in corso":" · still calculating","Cartella":"Folder","Rinomina elemento":"Rename item","Sposta elemento":"Move item"," — Lo spostamento modifica davvero il percorso sul disco.":" — This changes the actual file location on disk.","Nuovo nome":"New name","Percorso completo della cartella di destinazione":"Full path to the destination folder","Il file sarà rimosso da questa cartella e inviato al cestino del sistema.":"The file will be moved from this folder to the system trash.","Modifica del file in corso…":"Updating the file…","Operazione completata. Aggiorno la mappa.":"Done. Refreshing the map.","Elemento aperto nel sistema.":"Item revealed in your file manager.","Verifica dei duplicati in corso…":"Checking for duplicates…","Confronto del contenuto in corso…":"Comparing file contents…","Nessuna copia identica nei file analizzati.":"No identical copies in the scanned files.","Connessione al servizio locale non riuscita: ":"Could not connect to the local service: ","Gestisci cestino nel sistema ↗":"Manage trash in file manager ↗","Usa il cestino del sistema dalla finestra che si apre.":"Use your system trash from the file manager window.","Interruzione richiesta. Conservo i risultati raccolti…":"Stopping. Preserving the results collected so far…","Cartella personale":"Home folder"};

(() => {
  let language='en';
  try { language=localStorage.getItem('obsydian-language')==='it'?'it':'en'; } catch (_) {}
  window.language=language;
  window.locale=language==='it'?'it-IT':'en-US';
  window.t=(key,params={})=>{
    if(key==null)return '';
    const en=reverse[key]||key;
    const result=window.language==='it'?(dictionary[en]||key):en;
    return result.replace(/\{(\w+)\}/g,(match,name)=>Object.prototype.hasOwnProperty.call(params,name)?String(params[name]):match);
  };
  const texts=[],attributes=[];
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  while(walker.nextNode()){
    const node=walker.currentNode;
    if(['SCRIPT','STYLE'].includes(node.parentElement?.tagName))continue;
    const value=node.textContent,trimmed=value.trim();
    if(dictionary[trimmed])texts.push({node,key:trimmed,prefix:value.slice(0,value.indexOf(trimmed)),suffix:value.slice(value.indexOf(trimmed)+trimmed.length)});
  }
  for(const element of document.querySelectorAll('[title],[placeholder],[aria-label]')){
    for(const name of ['title','placeholder','aria-label']){
      const key=element.getAttribute(name);if(dictionary[key])attributes.push({element,name,key});
    }
  }
  function apply(){
    document.documentElement.lang=window.language;
    document.title='Obsydian · '+t('Explore your space');
    for(const item of texts)if(item.node.isConnected)item.node.textContent=item.prefix+t(item.key)+item.suffix;
    for(const item of attributes)item.element.setAttribute(item.name,t(item.key));
    for(const element of document.querySelectorAll('[data-i18n]'))element.textContent=t(element.dataset.i18n);
    document.getElementById('languageSelect').value=window.language;
  }
  window.applyTranslations=apply;
  window.setLanguage=(value)=>{
    window.language=value==='it'?'it':'en';window.locale=window.language==='it'?'it-IT':'en-US';
    try{localStorage.setItem('obsydian-language',window.language);}catch(_){}
    apply();window.dispatchEvent(new Event('languagechange'));
  };
  document.getElementById('languageSelect').addEventListener('change',event=>setLanguage(event.target.value));
  apply();
})();
