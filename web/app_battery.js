import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';

const $ = id => document.getElementById(id);
const groups = ['手机参照','壳架','灯头','风道','电路板','电池仓'];
const views = {iso:[[.70,.32,1.16],[0,1,0]], back:[[0,0,1],[0,1,0]],
  front:[[0,0,-1],[0,1,0]], side:[[1,0,0],[0,1,0]], top:[[0,1,0],[0,0,-1]]};
const mobile = matchMedia('(max-width: 760px)');
function fold(open) {
  $('panel-body').hidden=!open; $('panel-toggle').setAttribute('aria-expanded',String(open));
  $('panel-toggle').querySelector('.fold').textContent=open?'收起 −':'展开 +';
}
$('panel-toggle').onclick=()=>fold($('panel-body').hidden);
fold(!mobile.matches);
const v3 = a => new THREE.Vector3(...a);
const scenePoint = ([x,y,z]) => v3([x,-y,z]).multiplyScalar(.001);
const el = (tag,text,cls) => { const n=document.createElement(tag); n.textContent=text;if(cls)n.className=cls;return n; };
const sv = (tag,attrs) => { const n=document.createElementNS('http://www.w3.org/2000/svg',tag);
  for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);return n; };

async function start(){
  const canvas=$('canvas'), stage=$('stage');
  const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,2)); renderer.setClearColor(0,0);
  renderer.outputColorSpace=THREE.SRGBColorSpace; renderer.toneMapping=THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure=1.15;
  const scene=new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xfffcf1,0xb0bfbb,1.9));
  for(const [pos,intensity,tint] of [[[2,3,4],2.8,0xfff4db],[[-3,1,-2],2,0xe7f1ff],[[1,-2,1],.7,0xffffff]]){
    const l=new THREE.DirectionalLight(tint,intensity);l.position.set(...pos);scene.add(l);
  }
  const cam=new THREE.OrthographicCamera(-.15,.15,.15,-.15,.0005,5);
  const ctrl=new OrbitControls(cam,canvas);
  ctrl.enableDamping=false; ctrl.minZoom=.26;ctrl.maxZoom=14;ctrl.zoomToCursor=true;
  const [d,gltf]=await Promise.all([fetch('./models/parts_battery.json?v=A2-r1').then(r=>{
    if(!r.ok)throw new Error('无法读取零件索引');return r.json();}),new GLTFLoader().loadAsync('./models/filllight_battery.glb?v=A2-r1')]);
  scene.add(gltf.scene);$('weight').textContent='附件估重 '+d.totalMass.toFixed(1)+' g';
  const records=new Map(), ray=new THREE.Raycaster(), plane=new THREE.Plane();
  let selected=null, preset='iso', w=0,h=0,span=.24,frame=0,amount=0;
  for(const meta of d.parts){
    const obj=gltf.scene.getObjectByName(meta.id);
    if(!obj)throw new Error('零件节点与索引不一致：'+meta.id);
    obj.traverse(m=>{if(!m.isMesh)return; m.userData.partId=meta.id;
      m.material=m.material.clone();m.material.side=THREE.DoubleSide;});
    records.set(meta.id,{meta,obj,home:obj.position.clone()});
  }
  function queue(){if(!frame)frame=requestAnimationFrame(()=>{frame=0;renderer.render(scene,cam);annotate();});}
  function project() {
    const ar=w/h;cam.left=-span*ar/2;cam.right=-cam.left;cam.top=span/2;cam.bottom=-cam.top;cam.updateProjectionMatrix();queue();
  }
  function extents(){
    const b=new THREE.Box3();
    for(const {meta,obj,home} of records.values()){
      if(!obj.visible)continue;
      const shift=obj.position.clone().sub(home);
      const a=scenePoint(meta.bounds[0]).add(shift),c=scenePoint(meta.bounds[1]).add(shift);
      b.expandByPoint(a);b.expandByPoint(c);
    }
    if(b.isEmpty())for(const p of d.assemblyBounds)b.expandByPoint(scenePoint(p));
    return b;
  }
  function fit(id=preset||'iso'){
    const b=extents(), center=b.getCenter(new THREE.Vector3());
    const [dir]=views[id];
    // OrbitControls 缓存相机上向量。用同一 Y 上向量工作，顶视使用极小前倾，避免极点翻转。
    cam.up.set(0,1,0);
    const axis=id==='top'?v3([0,1,0.00001]):v3(dir);
    cam.position.copy(center).add(axis.normalize().multiplyScalar(.65)); ctrl.target.copy(center);
    cam.zoom=1;cam.lookAt(center);cam.updateMatrixWorld(true);
    let mx=0,my=0;
    for(const x of [b.min.x,b.max.x])for(const y of [b.min.y,b.max.y])for(const z of [b.min.z,b.max.z]){
      const p=cam.worldToLocal(v3([x,y,z]));mx=Math.max(mx,Math.abs(p.x));my=Math.max(my,Math.abs(p.y));
    }
    span=Math.max(my,mx/(w/h))*(id==='top'?2.70:2.33);project();
    ctrl.update();preset=id;
    document.querySelectorAll('[data-view]').forEach(btn=>{
      btn.setAttribute('aria-pressed',String(btn.dataset.view===id));
      if(btn.dataset.view===id)$('view-title').textContent=btn.textContent;
    });queue();
  }
  function resize(){
    w=Math.max(1,stage.clientWidth);h=Math.max(1,stage.clientHeight);renderer.setSize(w,h,false);
    if(preset)fit(preset);else project();
  }
  function visibleCount(){
    $('vis-count').textContent=[...records.values()].filter(r=>r.obj.visible).length+' / '+records.size+' 节点';
  }
  function select(id,fromModel=false){
    if(selected){
      const prev=records.get(selected);
      prev.obj.traverse(m=>{if(m.isMesh)m.material.emissive.setHex(0);});
      prev.row.classList.remove('active');prev.btn.setAttribute('aria-pressed','false');
    }
    selected=id;$('picked').hidden=!id;
    const detail=$('detail');detail.replaceChildren(el('div','零件信息','eyebrow'));
    if(id){
      const r=records.get(id),m=r.meta;
      $('picked').textContent=m.name+' · '+m.material+' ｜ '+m.size.join(' × ')+' mm ｜ '+(m.group==='手机参照'?'不计增重':m.mass.toFixed(2)+' g');
      r.obj.traverse(o=>{if(o.isMesh){o.material.emissive.setHex(0xe77c33);o.material.emissiveIntensity=.62;}});
      r.row.classList.add('active');r.btn.setAttribute('aria-pressed','true');
      if(fromModel){r.row.closest('details').open=true;}
      detail.append(el('strong',m.name));const list=el('dl','');
      for(const [key,val] of [['材料',m.material],['尺寸',m.size.map(x=>Number(x.toFixed(2))).join(' × ')+' mm'],['增重',m.group==='手机参照'?'参照，不计入':m.mass.toFixed(2)+' g · '+m.basis]]){
        list.append(el('dt',key),el('dd',val));}
      detail.append(list);if(m.note)detail.append(el('p',m.note));
    }else{detail.append(el('strong','选择一个零件'),el('p','点选模型或目录名称查看参数；勾选框控制显隐。'));}
    queue();
  }
  function listParts(){
    $('part-count').textContent=records.size+' 件';
    for(const group of groups){
      const entries=[...records.values()].filter(r=>r.meta.group===group),section=el('details','');
      const head=el('summary',group);head.append(el('span',String(entries.length).padStart(2,'0')));section.append(head);
      if(group==='灯头')section.open=true;
      for(const r of entries){
        const m=r.meta, row=el('div','','part'),cb=el('input','','vis'),swatch=el('i','','swatch'),btn=el('button',m.name);
        cb.type='checkbox';cb.checked=true;cb.setAttribute('aria-label','显示'+m.name);
        cb.onchange=()=>{r.obj.visible=cb.checked;if(!cb.checked&&selected===m.id)select(null);visibleCount();queue();};
        swatch.style.backgroundColor=m.color;btn.setAttribute('aria-pressed','false');
        btn.onclick=()=>{if(!cb.checked){cb.checked=true;r.obj.visible=true;visibleCount();}select(selected===m.id?null:m.id);};
        row.append(cb,swatch,btn);section.append(row);Object.assign(r,{row,cb,btn});
      }
      $('groups').append(section);
    }
    visibleCount();
  }
  const dimNodes=d.dimensions.map(dim=>{
    const group=sv('g',{}),line=sv('path',{fill:'none',stroke:'#91482b','stroke-width':1.25}),
      box=sv('rect',{rx:3,fill:'#fbf9ee',stroke:'#ae795c','stroke-width':.8}),
      label=sv('text',{'text-anchor':'middle',fill:'#683822','font-size':11,'font-family':'system-ui'});
    label.textContent=dim.name+' '+dim.value;
    group.append(line,box,label);$('annotations').append(group);
    return {dim,group,line,box,label};
  });
  function annotate(){
    $('annotations').style.display=$('dims').checked?'block':'none';
    if(!$('dims').checked)return;
    const pt=a=>{const p=scenePoint(a).project(cam);return [(p.x+1)*w/2,(1-p.y)*h/2];};
    const taken=[]; // 先布放实际两端，再给重叠标签自动分行。
    for(const [i,o] of dimNodes.entries()){
      const a=pt(o.dim.a),b=pt(o.dim.b),width=Math.min(w-8,o.label.getComputedTextLength()+14);
      let x=(a[0]+b[0])/2+(i===3?-16:16),y=(a[1]+b[1])/2-12;
      x=Math.max(width/2+3,Math.min(w-width/2-3,x));y=Math.max(29,Math.min(h-15,y));
      for(let k=0;k<8&&taken.some(([px,py,pw])=>Math.abs(py-y)<19&&Math.abs(px-x)<(width+pw)/2);k++){y=y+21>h-13?y-43:y+21;}
      taken.push([x,y,width]);const [ax,ay]=a,[bx,by]=b;
      o.line.setAttribute('d',`M${ax-3},${ay-3}l6,6 M${ax},${ay}L${bx},${by}m-3,-3l6,6 M${(ax+bx)/2},${(ay+by)/2}L${x},${y}`);
      Object.entries({x:x-width/2,y:y-11,width,height:18}).forEach(([k,v])=>o.box.setAttribute(k,v));
      o.label.setAttribute('x',x);o.label.setAttribute('y',y+2);
    }
  }
  function explode(n){
    amount=Number(n)/100;
    for(const r of records.values())r.obj.position.copy(r.home).addScaledVector(scenePoint(r.meta.explode),amount);
    $('explode-val').textContent=Math.round(amount*100)+'%';
    if(amount>0)$('dims').checked=false;
    if($('clip').checked)clipRange(false);
    if(preset)fit(preset);else queue();
  }
  function applyClip(){
    const on=$('clip').checked,axis=$('axis').value,pos=Number($('cut-pos').value);
    plane.normal.set(axis==='x'?-1:0,axis==='y'?1:0,0);plane.constant=pos*.001;
    renderer.clippingPlanes=on?[plane]:[];$('cut-val').textContent=pos.toFixed(1)+' mm';queue();
  }
  function clipRange(center){
    const isX=$('axis').value==='x', b=extents(),lo=isX?b.min.x:-b.max.y,hi=isX?b.max.x:-b.min.y,slider=$('cut-pos');
    const old=Number(slider.value);slider.min=(lo*1000).toFixed(1);slider.max=(hi*1000).toFixed(1);
    slider.value=center?(lo+hi)*500:Math.max(lo*1000,Math.min(hi*1000,old));applyClip();
  }
  $('explode').oninput=e=>explode(e.target.value);
  $('dims').onchange=()=>{if($('dims').checked&&amount){$('explode').value=0;explode(0);}queue();};
  $('clip').onchange=()=>{$('axis').disabled=!$('clip').checked;$('slice').hidden=!$('clip').checked;clipRange(true);};
  $('axis').onchange=()=>clipRange(true);$('cut-pos').oninput=applyClip;
  for(const btn of document.querySelectorAll('[data-view]'))btn.onclick=()=>fit(btn.dataset.view);
  $('reset').onclick=()=>{
    for(const r of records.values()){r.obj.visible=true;r.cb.checked=true;}
    $('clip').checked=false;$('axis').value='x';$('clip').onchange();$('dims').checked=false;
    $('explode').value=0;explode(0);select(null);visibleCount();fit('iso');
  };
  ctrl.addEventListener('change',queue);
  let down=null;
  canvas.addEventListener('pointerdown',e=>{down=e.isPrimary&&e.button===0?[e.clientX,e.clientY]:null;});
  canvas.addEventListener('pointercancel',()=>{down=null;});
  canvas.addEventListener('pointermove',e=>{
    if(e.buttons&&down&&Math.hypot(e.clientX-down[0],e.clientY-down[1])>4){
      preset=null;$('view-title').textContent='自由视角';document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed','false'));
    }
  });
  canvas.addEventListener('pointerup',e=>{
    if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>4){down=null;return;}down=null;
    const b=canvas.getBoundingClientRect();
    ray.setFromCamera(new THREE.Vector2(2*(e.clientX-b.left)/b.width-1,1-2*(e.clientY-b.top)/b.height),cam);
    const objects=[...records.values()].filter(r=>r.obj.visible).map(r=>r.obj);
    const hit=ray.intersectObjects(objects,true).find(h=>!$('clip').checked||plane.distanceToPoint(h.point)>=0);
    select(hit?.object.userData.partId||null,true);
  });
  listParts();resize();new ResizeObserver(resize).observe(stage);$('status').hidden=true;
  canvas.addEventListener('webglcontextlost',()=>{$('status').textContent='图形上下文已丢失，请刷新重试。';$('status').hidden=false;});
}
start().catch(err=>{$('status').hidden=false;$('status').textContent='模型未能打开。请通过本地 HTTP 服务访问，并确认浏览器支持 WebGL 2。 '+err.message;});
