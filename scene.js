'use strict';
const canvas=$('universe');
let w=1,h=1,yaw=0,pitch=.16,zoom=1,panX=0,panY=0,nodes=[],projected=[],drag=null,hover=null;
let animationFrame=0,lastAnimation=0,transition=null,scenePreviews={},previewTime=0,previewPending=false;
const sceneMemory=new Map();
const navigationFrames=new Map();
let pendingScene=null;
const world=new THREE.Scene();world.background=new THREE.Color('#0e1220');world.fog=new THREE.FogExp2('#0e1220',.00015);
const camera=new THREE.PerspectiveCamera(44,1,1,8000);camera.position.set(0,820,1100);
let renderer;
try{renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.35}
catch(error){
  window.webglUnavailable=true;
  // Keep all file controls usable when an embedded browser cannot create WebGL.
  renderer={setSize(){},render(){}};
  queueMicrotask(()=>{view(true);$('view3d').disabled=true;$('view3d').title=t('3D acceleration unavailable');toast(t('3D acceleration unavailable')+' · '+t('Use List view or update your graphics driver.'))});
}
const orbit=new OrbitControls(camera,canvas);orbit.enableDamping=true;orbit.dampingFactor=.12;orbit.minDistance=100;orbit.maxDistance=3600;orbit.maxPolarAngle=Math.PI*.47;orbit.target.set(0,100,0);orbit.mouseButtons={LEFT:THREE.MOUSE.ROTATE,MIDDLE:THREE.MOUSE.PAN,RIGHT:null};orbit.zoomToCursor=true;
world.add(new THREE.HemisphereLight('#bacfff','#292442',2));
const sun=new THREE.DirectionalLight('#d6e5ff',4);sun.position.set(-380,900,400);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-1300,right:1300,top:1300,bottom:-1300,near:10,far:2600});sun.shadow.normalBias=1.5;sun.shadow.bias=-.00015;world.add(sun);world.add(sun.target);
const rim=new THREE.PointLight('#9c7eff',180000,1800);rim.position.set(350,220,-350);world.add(rim);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(12000,12000),new THREE.MeshStandardMaterial({color:'#151b2d',roughness:.87,metalness:.22}));floor.rotation.x=-Math.PI/2;floor.position.y=-65;floor.receiveShadow=true;world.add(floor);
const grid=new THREE.GridHelper(5000,80,'#3b4261','#252c42');grid.position.y=-64.5;grid.material.transparent=true;grid.material.opacity=.35;world.add(grid);
const bubbleGroup=new THREE.Group(),edgeGroup=new THREE.Group();world.add(bubbleGroup,edgeGroup);
const geometry=new THREE.SphereGeometry(1,40,28),facetGeometry=new THREE.IcosahedronGeometry(1,1);
const raycaster=new THREE.Raycaster(),mouse=new THREE.Vector2();
const labels=document.createElement('div');labels.className='world-labels';canvas.after(labels);
let edgeSignature='',focusMesh=null,edgePickables=[];
function weightRatio(item){const drive=state.drives.find(d=>d.isDisk&&d.path.toLowerCase()===item.path.toLowerCase());if(drive?.total)return Math.max(0,Math.min(1,1-drive.free/drive.total));return Math.max(0,Math.min(1,item.size/Math.max(1,state.viewTotal||state.items.reduce((s,n)=>s+n.size,0))))}
function weightColor(item,total){if(item.application)return '#b5a4ff';const r=total===undefined?weightRatio(item):item.size/Math.max(1,total);return r<.05?'#4de3bb':r<.15?'#54bff2':r<.35?'#a68cff':r<.65?'#ffbf63':'#ff728d'}
function makeBubble(item){
  const material=new THREE.MeshPhysicalMaterial({color:weightColor(item),metalness:item.isDir?0:.24,roughness:.2,clearcoat:1,clearcoatRoughness:.14,transparent:true,opacity:item.isDir?.13:1,depthWrite:!item.isDir,side:THREE.FrontSide});
  const mesh=new THREE.Mesh(item.application?facetGeometry:geometry,material);mesh.castShadow=!item.isDir;mesh.receiveShadow=false;mesh.userData.item=item;bubbleGroup.add(mesh);
  const ring=new THREE.Mesh(new THREE.TorusGeometry(1.08,.012,8,64),new THREE.MeshBasicMaterial({color:'#f4ecff',transparent:true,opacity:0}));ring.rotation.x=Math.PI/2;mesh.add(ring);
  const label=document.createElement('div');label.className='world-label';const title=document.createElement('strong'),size=document.createElement('span');label.append(title,size);labels.append(label);
  const n={item,mesh,ring,label,x:0,y:0,z:0,r:1,targetR:30,baseOpacity:item.isDir?.13:1,childrenGroup:new THREE.Group()};mesh.userData.node=n;mesh.add(n.childrenGroup);return n;
}
function disposeNode(n){bubbleGroup.remove(n.mesh);n.mesh.material.dispose();n.ring.geometry.dispose();n.ring.material.dispose();for(const child of [...n.childrenGroup.children]){child.material.dispose()}n.label.remove()}
function layout(){
  if(window.webglUnavailable){nodes=[];return;}
  if(transition)return;
  if(pendingScene){nodes=[];}
  for(const mesh of [...bubbleGroup.children])if(!nodes.some(n=>n.mesh===mesh)&&!pendingScene?.nodes.some(n=>n.mesh===mesh))disposeNode(mesh.userData.node);
  const existing=new Map(nodes.map(n=>[n.item.path,n])),max=Math.max(1,...state.items.map(n=>n.size)),items=state.items.slice(0,180);
  const packed=packItems(items),saved=sceneMemory.get(state.path)?.layout;
  const next=items.map((item,index)=>{
    let n=existing.get(item.path);if(n)existing.delete(item.path);else n=makeBubble(item);
    n.item=item;n.mesh.userData.item=item;const p=packed.get(item.path);n.targetR=p.r;
    if(!n.positioned){const position=saved?.get(item.path)?.position||p.position;n.x=position.x;n.y=position.y;n.z=position.z;n.positioned=true;n.mesh.position.copy(position)}
    n.mesh.material.color.set(weightColor(item));n.label.children[0].textContent=item.name;n.label.children[1].textContent=(item.application?t('Application')+' · ':'')+fmt(item.size)+(item.partial?' +':'');return n;
  });
  for(const n of existing.values())disposeNode(n);nodes=next;edgeSignature='';animateGrowth();refreshPreviews();
}
function packItems(items){
  const result=new Map(),placed=[],counts=[0,0,0,0],centers=[[-175,-50],[210,-70],[-200,260],[220,270]],max=Math.max(1,...items.map(n=>n.size));
  for(const item of items){const r=14+Math.cbrt(item.size/max)*64,g=item.application?0:item.isDir?0:/\.(png|jpg|mp4|mp3|mov|wav|webp)$/i.test(item.name)?1:/\.(pdf|txt|md|docx|xlsx)$/i.test(item.name)?2:3,rank=counts[g]++,center=item.application?[0,0]:centers[g];let x=center[0],z=center[1];
    for(let k=0;k<2000;k++){const angle=k*2.399963,d=Math.sqrt(k)*23;x=center[0]+Math.cos(angle)*d;z=center[1]+Math.sin(angle)*d;if(!placed.some(p=>Math.hypot(x-p.x,z-p.z)<r+p.r+30))break}
    placed.push({x,z,r});result.set(item.path,{position:new THREE.Vector3(x*1.7,55+r+(rank%3)*18,z*1.9),r});
  }return result;
}
function resize(){const b=canvas.parentElement.getBoundingClientRect();if(!b.width||!b.height)return;w=b.width;h=b.height;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();draw()}
new ResizeObserver(resize).observe(canvas.parentElement);
function project(n){const p=n.mesh.position.clone().project(camera);const distance=camera.position.distanceTo(n.mesh.position);return {x:(p.x+1)*w/2,y:(1-p.y)*h/2,z:p.z,r:n.r*h/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov/2))*distance),n,s:1}}
function rememberScene(){sceneMemory.set(state.path,{position:camera.position.clone(),target:orbit.target.clone(),layout:new Map(nodes.map(n=>[n.item.path,{position:n.mesh.position.clone(),r:n.r}]))});if(sceneMemory.size>24)sceneMemory.delete(sceneMemory.keys().next().value)}
function captureScene(path){
  if(transition)finishTransition();rememberScene();
  return {path:state.path,target:path,nodes:[...nodes],position:camera.position.clone(),look:orbit.target.clone(),folder:nodes.find(n=>n.item.path===path)};
}
function prepareScene(snapshot){if(window.webglUnavailable||state.list||!snapshot||snapshot.path===snapshot.target)return;pendingScene=snapshot}
function frameFor(folder){const scale=Math.max(.00001,folder.r*(folder.previewScale||.00085));return {scale,origin:folder.mesh.position.clone().addScaledVector(folder.previewCenter||new THREE.Vector3(0,100,0),-scale)}}
function inFrame(vector,frame){return vector.clone().multiplyScalar(frame.scale).add(frame.origin)}
function transitionTo(snapshot){
  if(!pendingScene||!snapshot||window.webglUnavailable){pendingScene=null;return;}
  const old=pendingScene.nodes;pendingScene=null;
  const saved=sceneMemory.get(state.path),toPosition=saved?.position.clone()||new THREE.Vector3(0,820,1100),toTarget=saved?.target.clone()||new THREE.Vector3(0,100,0);
  const outward=navigationFrames.get(snapshot.path),isExit=outward?.parent===state.path,folder=isExit?nodes.find(n=>n.item.path===snapshot.path):snapshot.folder;
  if(!folder){for(const n of old)disposeNode(n);camera.position.copy(toPosition);orbit.target.copy(toTarget);return;}
  if(isExit){for(const n of nodes){n.r=n.targetR;n.mesh.scale.setScalar(n.r)}}
  if(isExit&&scenePreviews[folder.item.path])previewNodes(folder,scenePreviews[folder.item.path]);
  const frame=isExit?frameFor(folder):frameFor(snapshot.folder),matched=new Map();
  folder.mesh.updateMatrixWorld(true);
  for(const mesh of folder.childrenGroup.children){const position=new THREE.Vector3(),scale=new THREE.Vector3();mesh.getWorldPosition(position);mesh.getWorldScale(scale);matched.set(mesh.userData.path,{position,r:scale.x,mesh});mesh.visible=false;}
  const incoming=nodes.map(n=>({node:n,position:new THREE.Vector3(n.x,n.y,n.z),r:n.targetR}));
  let fromPosition=camera.position.clone(),fromTarget=orbit.target.clone(),endPosition,endTarget;
  if(isExit){
    fromPosition=inFrame(fromPosition,frame);fromTarget=inFrame(fromTarget,frame);camera.position.copy(fromPosition);orbit.target.copy(fromTarget);
    for(const n of old){const p=inFrame(n.mesh.position,frame);n.x=p.x;n.y=p.y;n.z=p.z;n.r*=frame.scale;n.mesh.position.copy(p);n.mesh.scale.setScalar(n.r)}
    endPosition=toPosition;endTarget=toTarget;
    for(const n of nodes){n.mesh.material.opacity=0;n.label.style.opacity=0;}
  }else{
    navigationFrames.set(state.path,{parent:snapshot.path});
    endPosition=inFrame(toPosition,frame);endTarget=inFrame(toTarget,frame);
    for(const record of incoming){const n=record.node,start=matched.get(n.item.path),p=start?.position||snapshot.folder.mesh.position;n.x=p.x;n.y=p.y;n.z=p.z;n.r=start?.r||.001;n.mesh.position.copy(p);n.mesh.scale.setScalar(n.r);}
  }
  transition={start:performance.now(),progress:0,duration:matchMedia('(prefers-reduced-motion: reduce)').matches?1:950,isExit,old,incoming,matched,frame,fromPosition,fromTarget,toPosition:endPosition,toTarget:endTarget,finalPosition:toPosition,finalTarget:toTarget,
    oldTransforms:old.map(n=>({node:n,position:n.mesh.position.clone(),r:n.r,ringOpacity:n.ring.material.opacity})),incomingStarts:incoming.map(({node:n})=>({position:n.mesh.position.clone(),r:n.r}))};
  transition.disabledControls=['viewApplications','resetView','search'].map(id=>$(id)).filter(Boolean).map(element=>({element,disabled:element.disabled}));
  for(const {element} of transition.disabledControls)element.disabled=true;
  edgeGroup.visible=false;for(const c of edgeGroup.children)if(c.userData.label)c.userData.label.hidden=true;
  for(const n of old){n.label.hidden=true;n.mesh.castShadow=false;for(const child of n.childrenGroup.children)child.userData.baseOpacity=child.material.opacity;}
  if(isExit)environmentFrame(frame.scale,frame.origin);
  orbit.enabled=false;camera.near=Math.max(.00001,frame.scale);camera.updateProjectionMatrix();animateGrowth();draw();
}
function finishTransition(){
  if(!transition)return;const active=transition;transition=null;
  for(const {element,disabled} of active.disabledControls)element.disabled=disabled;
  for(const n of active.old)disposeNode(n);
  for(const {node:n,position,r} of active.incoming){n.x=position.x;n.y=position.y;n.z=position.z;n.r=r;n.mesh.position.copy(position);n.mesh.scale.setScalar(r);n.mesh.material.opacity=n.baseOpacity;n.label.style.opacity=1;for(const child of n.childrenGroup.children)child.visible=true;}
  camera.position.copy(active.finalPosition);orbit.target.copy(active.finalTarget);camera.near=1;camera.updateProjectionMatrix();orbit.enabled=true;orbit.update();edgeGroup.visible=true;edgeSignature='';
  environmentFrame(1,new THREE.Vector3());
  previewTime=0;refreshPreviews();draw();window.dispatchEvent(new Event('scene-navigation-end'));
}
function environmentFrame(scale,origin){
  floor.scale.setScalar(scale);floor.position.copy(origin).addScaledVector(new THREE.Vector3(0,-65,0),scale);grid.scale.setScalar(scale);grid.position.copy(origin).addScaledVector(new THREE.Vector3(0,-64.5,0),scale);world.fog.density=.00015/scale;
  sun.position.copy(origin).addScaledVector(new THREE.Vector3(-380,900,400),scale);sun.target.position.copy(origin);
  Object.assign(sun.shadow.camera,{left:-1300*scale,right:1300*scale,top:1300*scale,bottom:-1300*scale,near:10*scale,far:2600*scale});sun.shadow.camera.updateProjectionMatrix();sun.shadow.normalBias=1.5*scale;
  rim.position.copy(origin).addScaledVector(new THREE.Vector3(350,220,-350),scale);rim.distance=1800*scale;rim.intensity=180000*scale*scale;
}
function previewNodes(n,preview){
  if(transition)return;const signature=preview.items.map(p=>p.path+':'+p.size).join('|');if(signature===n.previewSignature)return;n.previewSignature=signature;
  for(const child of [...n.childrenGroup.children]){n.childrenGroup.remove(child);child.material.dispose()}
  const packed=packItems(preview.items.slice(0,8)),bounds=new THREE.Box3();
  for(const p of packed.values()){const extent=new THREE.Vector3(p.r,p.r,p.r);bounds.expandByPoint(p.position.clone().sub(extent));bounds.expandByPoint(p.position.clone().add(extent));}
  const center=packed.size?bounds.getCenter(new THREE.Vector3()):new THREE.Vector3(),bound=Math.max(30,...[...packed.values()].map(p=>p.position.distanceTo(center)+p.r));n.previewCenter=center;n.previewScale=.82/bound;
  for(const item of preview.items.slice(0,8)){const p=packed.get(item.path),mesh=new THREE.Mesh(geometry,new THREE.MeshPhysicalMaterial({color:weightColor(item,n.item.size),roughness:.2,metalness:0,transparent:true,opacity:item.isDir?.13:1,depthWrite:!item.isDir}));mesh.userData.path=item.path;mesh.scale.setScalar(p.r*n.previewScale);mesh.position.copy(p.position).sub(center).multiplyScalar(n.previewScale);n.childrenGroup.add(mesh)}
}
async function refreshPreviews(){if(transition||pendingScene||previewPending||!state.path||state.search||state.applicationsView||Date.now()-previewTime<1000)return;previewPending=true;const path=state.path;try{const result=await api('previews?path='+encodeURIComponent(path));if(path===state.path&&!transition&&!pendingScene){scenePreviews={...scenePreviews,...result.previews};for(const n of nodes)if(result.previews[n.item.path])previewNodes(n,result.previews[n.item.path])}}catch{}finally{previewPending=false;previewTime=Date.now()}}
function clearEdges(){for(const c of [...edgeGroup.children]){edgeGroup.remove(c);c.geometry?.dispose();c.material?.dispose();c.userData.label?.remove()}edgePickables=[]}
function buildEdges(){
  const edges=typeof referenceEdges==='undefined'?[]:referenceEdges;
  const signature=(state.selected?.path||state.path)+'|'+edges.slice(0,48).map(e=>e.source+'>'+e.target).join('|')+'|'+nodes.map(n=>n.item.path).join('|');if(signature===edgeSignature)return;edgeSignature=signature;clearEdges();
  const normalize=p=>p.replaceAll('\\','/').toLowerCase();
  const find=path=>nodes.find(n=>normalize(n.item.path)===normalize(path))||nodes.find(n=>n.item.isDir&&normalize(path).startsWith(normalize(n.item.path)+'/'));
  const ghosts=new Map();const focus=nodes.find(n=>n.item.path===state.selected?.path)?.mesh.position||new THREE.Vector3(0,100,0);
  function endpoint(path){const n=find(path);if(n)return n.mesh.position.clone();if(ghosts.has(path))return ghosts.get(path).position.clone();const angle=ghosts.size*2.4,r=260+ghosts.size*8,p=new THREE.Vector3(focus.x+Math.cos(angle)*r,focus.y+140+ghosts.size%3*35,focus.z+Math.sin(angle)*r);const ghost=new THREE.Mesh(new THREE.OctahedronGeometry(9),new THREE.MeshStandardMaterial({color:'#66efea',emissive:'#228d91',emissiveIntensity:.8}));ghost.position.copy(p);ghost.userData.path=path;ghost.userData.label=document.createElement('div');ghost.userData.label.className='world-label reference-ghost';ghost.userData.label.textContent=path.split(/[\\/]/).pop();labels.append(ghost.userData.label);edgeGroup.add(ghost);edgePickables.push(ghost);ghosts.set(path,ghost);return p}
  let visible=0;for(const e of edges.slice(0,48)){const a=endpoint(e.source),b=endpoint(e.target);if(a.distanceTo(b)<1)continue;const mid=a.clone().lerp(b,.5);mid.y+=80;const curve=new THREE.QuadraticBezierCurve3(a,mid,b);const tube=new THREE.Mesh(new THREE.TubeGeometry(curve,32,2.2,8,false),new THREE.MeshBasicMaterial({color:e.kind==='installation'?'#f6c26f':'#6cece2',transparent:true,opacity:.9}));tube.userData.edge=e;edgeGroup.add(tube);edgePickables.push(tube);const at=curve.getPoint(.76),direction=curve.getTangent(.76);const arrow=new THREE.Mesh(new THREE.ConeGeometry(7,19,8),new THREE.MeshBasicMaterial({color:'#f4edba'}));arrow.position.copy(at);arrow.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),direction);edgeGroup.add(arrow);visible++}
  $('linkCount').textContent=edges.length?`${visible} / ${edges.length} `+t('links shown'):t('No links in this view');
}
function draw(){if(!renderer||state.list||document.hidden)return;if(!transition)buildEdges();projected=[];for(const n of nodes){n.mesh.position.set(n.x,n.y,n.z);n.mesh.scale.setScalar(Math.max(.000001,n.r));n.ring.material.opacity=(state.selection.has(n.item.path)?.9:n.item.isDir?.24:0)*(transition?transition.progress:1);n.mesh.material.emissive.set(state.selection.has(n.item.path)?'#403666':'#000000');const p=project(n);projected.push(p);n.label.hidden=p.z>1||p.z<-1||p.x<0||p.x>w||p.y<0||p.y>h;n.label.style.transform=`translate(${p.x}px,${p.y+p.r+9}px) translateX(-50%)`;n.label.classList.toggle('selected',state.selection.has(n.item.path));n.label.style.opacity=transition?transition.progress:Math.max(.45,1-camera.position.distanceTo(n.mesh.position)/3500)}
  if(!transition)for(const c of edgeGroup.children)if(c.userData.label){const p=c.position.clone().project(camera);c.userData.label.hidden=p.z>1;c.userData.label.style.transform=`translate(${(p.x+1)*w/2}px,${(1-p.y)*h/2-23}px) translateX(-50%)`}
  renderer.render(world,camera)
}
function animateGrowth(){if(window.webglUnavailable)return;if(!animationFrame)animationFrame=requestAnimationFrame(grow)}
function grow(now){animationFrame=0;const dt=Math.max(0,Math.min(64,now-lastAnimation));lastAnimation=now;const k=1-Math.exp(-dt/120);if(!transition)for(const n of nodes)n.r+=(n.targetR-n.r)*k;
  if(transition){const tr=transition,u=Math.min(1,(now-tr.start)/tr.duration),s=u*u*(3-2*u);tr.progress=s;camera.position.lerpVectors(tr.fromPosition,tr.toPosition,s);orbit.target.lerpVectors(tr.fromTarget,tr.toTarget,s);camera.lookAt(orbit.target);
    for(const [index,record] of tr.incoming.entries()){const n=record.node;if(!tr.isExit){const end=inFrame(record.position,tr.frame),start=tr.incomingStarts[index],p=start.position.clone().lerp(end,s);n.x=p.x;n.y=p.y;n.z=p.z;n.r=THREE.MathUtils.lerp(start.r,record.r*tr.frame.scale,s)}n.mesh.material.opacity=n.baseOpacity*(tr.isExit?s:1)}
    for(const record of tr.oldTransforms){const n=record.node;n.ring.material.opacity=record.ringOpacity*(1-s);if(tr.isExit){const target=tr.matched.get(n.item.path),p=record.position.clone().lerp(target?.position||record.position,s);n.x=p.x;n.y=p.y;n.z=p.z;n.r=THREE.MathUtils.lerp(record.r,target?.r||.00001,s);n.mesh.position.set(n.x,n.y,n.z);n.mesh.scale.setScalar(n.r);n.mesh.material.opacity=n.baseOpacity*(target?1:1-s)}else n.mesh.material.opacity=n.baseOpacity*(1-s);for(const child of n.childrenGroup.children)child.material.opacity=child.userData.baseOpacity*(1-s);}
    const blend=tr.isExit?1-s:s,scale=THREE.MathUtils.lerp(1,tr.frame.scale,blend),origin=tr.frame.origin.clone().multiplyScalar(blend);environmentFrame(scale,origin);
    if(u===1)finishTransition();
  }else orbit.update();draw();if(!state.closed)animationFrame=requestAnimationFrame(grow)
}
function hit(x,y){if(transition)return null;mouse.set(x/w*2-1,1-y/h*2);raycaster.setFromCamera(mouse,camera);const hit=raycaster.intersectObjects(nodes.map(n=>n.mesh),false)[0];if(!hit)return null;const n=nodes.find(n=>n.mesh===hit.object);return project(n)}
let down=null;
canvas.addEventListener('pointerdown',e=>{if(e.button===0){const b=canvas.getBoundingClientRect();down={x:e.clientX,y:e.clientY,node:hit(e.clientX-b.left,e.clientY-b.top),additive:e.ctrlKey||e.metaKey||e.shiftKey}}closeContextMenu()});
canvas.addEventListener('pointerup',e=>{if(down&&Math.hypot(e.clientX-down.x,e.clientY-down.y)<5&&down.node)select(down.node.n.item,down.additive);down=null});
canvas.addEventListener('pointermove',e=>{const b=canvas.getBoundingClientRect(),x=e.clientX-b.left,y=e.clientY-b.top;hover=hit(x,y);const tip=$('tooltip');tip.hidden=true;if(hover){const n=hover.n.item;tip.textContent=n.name+' · '+fmt(n.size)+' · '+(weightRatio(n)*100).toFixed(1)+'% '+t('relative weight');tip.hidden=false}else{mouse.set(x/w*2-1,1-y/h*2);raycaster.setFromCamera(mouse,camera);const edge=raycaster.intersectObjects(edgePickables,false)[0]?.object.userData;if(edge?.edge){tip.textContent=edge.edge.source+' → '+edge.edge.target+' · '+edge.edge.evidence;tip.hidden=false}else if(edge?.path){tip.textContent=edge.path;tip.hidden=false}}tip.style.left=Math.max(8,Math.min(w-310,x+12))+'px';tip.style.top=Math.max(8,Math.min(h-80,y-55))+'px'});
canvas.addEventListener('pointerleave',()=>$('tooltip').hidden=true);
canvas.addEventListener('dblclick',e=>{const b=canvas.getBoundingClientRect(),p=hit(e.clientX-b.left,e.clientY-b.top);if(p?.n.item.application)enterApplication(p.n.item);else if(p?.n.item.isDir)children(p.n.item.path);else{const edge=raycaster.intersectObjects(edgePickables,false)[0]?.object.userData;if(edge?.path){if(state.applicationsView&&state.selected?.application)enterApplication(state.selected);else revealReference(edge.path)}}});
canvas.addEventListener('contextmenu',e=>{e.preventDefault();const b=canvas.getBoundingClientRect(),p=hit(e.clientX-b.left,e.clientY-b.top);if(p){if(!state.selection.has(p.n.item.path))select(p.n.item);openContextMenu(e.clientX,e.clientY)}});
canvas.addEventListener('auxclick',e=>{if(e.button===1)e.preventDefault()});
function resetCamera(){camera.position.set(0,820,1100);orbit.target.set(0,100,0);orbit.update();draw()}
const linkCount=document.createElement('div');linkCount.id='linkCount';linkCount.className='link-count';canvas.parentElement.append(linkCount);
animateGrowth();

const contextMenu=document.createElement('div');contextMenu.id='contextMenu';contextMenu.className='context-menu';contextMenu.setAttribute('role','menu');contextMenu.hidden=true;document.body.append(contextMenu);
function closeContextMenu(){contextMenu.hidden=true}
function openContextMenu(x,y){
  contextMenu.replaceChildren();const title=document.createElement('div');title.className='context-title';title.textContent=state.selection.size>1?state.selection.size+' '+t('items selected'):state.selected.name;contextMenu.append(title);
  const options=[['enter','Enter folder'],['inspectReferences','Show connections'],['open','Show in system'],['duplicates','Verify duplicates'],['rename','Rename'],['move','Move to folder…'],['trash','Move to Recycle Bin'],['uninstallApplication','Uninstall application…']];
  for(const [id,label] of options){if(state.selection.size>1&&!['trash','inspectReferences'].includes(id))continue;const target=$(id);if(!target||target.hidden)continue;const b=document.createElement('button');b.setAttribute('role','menuitem');b.textContent=t(label);b.disabled=target.disabled;b.onclick=()=>{closeContextMenu();target.click()};contextMenu.append(b)}
  contextMenu.hidden=false;contextMenu.style.left=Math.max(8,Math.min(innerWidth-contextMenu.offsetWidth-8,x))+'px';contextMenu.style.top=Math.max(8,Math.min(innerHeight-contextMenu.offsetHeight-8,y))+'px';contextMenu.querySelector('button:not(:disabled)')?.focus();
}
document.addEventListener('pointerdown',e=>{if(!contextMenu.contains(e.target))closeContextMenu()});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape')closeContextMenu();
  if(!contextMenu.hidden&&['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();const buttons=[...contextMenu.querySelectorAll('button:not(:disabled)')],i=buttons.indexOf(document.activeElement);buttons[(i+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus()}
  if(e.altKey&&e.key==='ArrowLeft'&&state.parent){e.preventDefault();children(state.parent)}
});
document.addEventListener('contextmenu',e=>{const row=e.target.closest('.list-row');if(row){e.preventDefault();const n=state.items.find(n=>n.path===row.dataset.path);if(n){if(!state.selection.has(n.path))select(n);openContextMenu(e.clientX,e.clientY)}}});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)animateGrowth()});

canvas.addEventListener('auxclick',e=>{if(e.button===1)e.preventDefault()});

