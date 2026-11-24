// 与网页使用同一份 three 和 GLTFLoader；映射裸模块名，不依赖 npm 或网络。
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {registerHooks} from 'node:module';
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const assetRoot=process.env.FILL_WEB_ROOT?pathToFileURL(resolve(process.env.FILL_WEB_ROOT)+'/'):new URL('../web/',import.meta.url);
const url=p=>new URL(p,assetRoot);
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

const variant=suffix?'A':'C',rev=variant+'5-r2';assert.equal(meta.revision,rev);assert.equal(meta.variant,variant);if(!process.argv.includes('--draft'))assert(meta.releaseAllowed&&meta.checks.every(c=>c.ok));else console.log('候审渲染检查；未测试且不更改 releaseAllowed。');
const html=await readFile(url(suffix?'battery.html':'index.html'),'utf8'),app=await readFile(url(suffix?'app_battery.js':'app.js'),'utf8');
assert(html.includes('机顶补光灯')&&html.includes('comparison05.svg?v='+rev)&&html.includes('./index.html?v=C5-r2')&&html.includes('./battery.html?v=A5-r2'));
assert(app.includes('parts'+suffix+'.json?v='+rev)&&app.includes('filllight'+suffix+'.glb?v='+rev));
const ids=new Set(meta.parts.map(p=>p.id));for(const k of ['head_shell','head_bezel','driver_board','blower','led_board','side_rail','trunk','power_tim','spreader'])assert(ids.has(k));assert.equal(ids.has('cell_1'),!!suffix);
const groups=app.match(/const groups = \[(.*?)\];/)[1].split(',').map(s=>s.trim().slice(1,-1));assert.deepEqual(new Set(groups),new Set(meta.parts.map(p=>p.group)));
