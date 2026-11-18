// 与网页使用同一份 three 和 GLTFLoader；映射裸模块名，不依赖 npm 或网络。
import {registerHooks} from 'node:module';
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const url=p=>new URL('../web/'+p,import.meta.url);
registerHooks({resolve(s,c,next){return s==='three'?{url:url('vendor/three.module.js').href,shortCircuit:true}:next(s,c);}});
const {GLTFLoader}=await import(url('vendor/GLTFLoader.js'));
const {Box3}=await import('three');
const [data,meta]=await Promise.all([readFile(url('models/filllight.glb')),readFile(url('models/parts.json'),'utf8').then(JSON.parse)]);
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
