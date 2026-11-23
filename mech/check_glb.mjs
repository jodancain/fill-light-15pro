// 与网页使用同一份 three 和 GLTFLoader；映射裸模块名，不依赖 npm 或网络。
import {registerHooks} from 'node:module';
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const url=p=>new URL('../web/'+p,import.meta.url);
registerHooks({resolve(s,c,next){return s==='three'?{url:url('vendor/three.module.js').href,shortCircuit:true}:next(s,c);}});
const {GLTFLoader}=await import(url('vendor/GLTFLoader.js'));
const {Box3}=await import('three');
const suffix=process.argv.includes('--battery')?'_battery':'';
const [data,meta]=await Promise.all([readFile(url('models/filllight'+suffix+'.glb')),readFile(url('models/parts'+suffix+'.json'),'utf8').then(JSON.parse)]);
const {scene}=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');
let triangles=0;
for(const p of meta.parts){
  const obj=scene.getObjectByName(p.id);assert.ok(obj?.isMesh,p.id);
  const box=new Box3().setFromObject(obj,true);const [lo,hi]=p.bounds;
  for(const [got,want] of [[box.min,[lo[0],-hi[1],lo[2]]],[box.max,[hi[0],-lo[1],hi[2]]]])
    assert.ok(got.toArray().every((x,i)=>Math.abs(x*1000-want[i])<.10),p.id+' 方向或单位错误');
  triangles+=obj.geometry.index.count/3;
}
console.log(`本地 GLTFLoader 回读：${meta.parts.length} 节点，${triangles} 个三角面；命名、方向与毫米包络一致。`);
if(meta.variant==='C'){
  const byId=new Map(meta.parts.map(x=>[x.id,x]));
  for(const id of ['power_contact','power_tim','input_choke','input_usb_c','output_usb_c'])assert.ok(byId.has(id),id);
  assert(!byId.has('pouch')&&!byId.has('main_j5'));assert.deepEqual(byId.get('blower').size,[35,35,10]);
  const app=await readFile(url('app.js'),'utf8'), html=await readFile(url('index.html'),'utf8');
  const gs=app.match(/const groups = \[(.*?)\];/)[1].split(',').map(s=>s.trim().slice(1,-1));
  assert.deepEqual(new Set(gs),new Set(meta.parts.map(x=>x.group)));assert(html.includes('C　外接电池 · 已选定'));
  console.log('C 版目录分组、供电与风道节点、网页方案标记一致。');
}
if(['C-r6','C-r7'].includes(meta.revision)){
  const ref=meta.parts.find(p=>p.id==='camera_dummy'), screws=meta.parts.find(p=>p.id==='screws');
  assert.deepEqual(ref.bounds,[[2.5,2.5,0],[44.5,46,4]]);assert(ref.note.includes('不作定位基准'));
  assert(screws.bounds[1][1]<=111);assert(meta.checks.some(c=>c.ok&&c.name.startsWith('开窗包络')));
  const html=await readFile(url('index.html'),'utf8');assert(html.includes('已知偏差与使用限制')&&html.includes('关闭手机闪光灯'));
  console.log('冻结模型、示意平台、下钉外缘、开窗判据和网页使用限制一致。');
}
if(meta.revision==='C-r7'){
  const j4=meta.parts.find(x=>x.id==='driver_j4');
  assert(j4.note.includes('5V / FAN_GND_SW / FAN_TACH / NC_PWM'));
  assert(j4.note.includes('针序以电气原理图为准；第 4 针预留 PWM'));
  assert(meta.releaseAllowed && meta.checks.every(c=>c.ok));
  console.log('R7 网页零件中的风扇 J4 针序、预留针注释与放行状态通过。');
}

if(suffix){
  assert.equal(meta.revision,'A2-r1');assert.equal(meta.variant,'A2');
  assert(meta.releaseAllowed && meta.checks.every(c=>c.ok));
  const A=await readFile(url('battery.html'),'utf8'),C=await readFile(url('index.html'),'utf8');
  const app=await readFile(url('app_battery.js'),'utf8');
  assert(A.includes('app_battery.js?v=A2-r1')&&C.includes('app.js?v=C-r7'));
  assert(A.includes('./index.html?v=C-r7')&&C.includes('./battery.html?v=A2-r1'));
  assert(app.includes('parts_battery.json?v=A2-r1')&&app.includes('filllight_battery.glb?v=A2-r1'));
  const groups=app.match(/const groups = \[(.*?)\];/)[1].split(',').map(s=>s.trim().slice(1,-1));
  assert.deepEqual(new Set(groups),new Set(meta.parts.map(p=>p.group)));
  const lookup=new Map(meta.parts.map(p=>[p.id,p]));
  for(const k of ['cell_1','cell_2','cell_ntc','main_j5','battery_plug','pack_leads','panel_tail','battery_lid'])assert(lookup.has(k));
  console.log('A2 标记、默认 C 导航、版本化 URL、共用板、换电节点和零件组均已读回。');
}
