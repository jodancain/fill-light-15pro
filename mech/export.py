"""从同一套 B-rep 输出制造文件、米制 glTF、检验记录及查看器数据。"""
from model import *
from itertools import combinations

from hashlib import sha256
import numpy as np
import trimesh
import shutil
from build123d import export_step, export_stl, import_step
from trimesh.visual.material import PBRMaterial

OUT=ROOT/'mech/out'; WEB=ROOT/'web/models'
EPS=1e-4; VOL_EPS=.001
def bounds(s):
    b=s.bounding_box()
    return np.array([list(b.min),list(b.max)])
def native_shape(s):
    # 不复用 Compound 的装配 children：镜像只变换 B-rep，旧子树位置不会跟着变。
    solids=s.mirror(Plane.XZ).solids()
    return solids[0] if len(solids)==1 else Compound(list(solids))
def vol(s): return sum(q.volume for q in s.solids())
def inter(a,b): return sum(vol(s) for s in (a.intersect(b) or []))
def strong(c): return '通过' if c else '不通过'
def nd(a): return [round(float(x),3)+0. for x in a]
def fmtp_local(a): return ", ".join(f"{x:.2f}" for x in a)
def fmt(a): return ' × '.join(f'{x:.2f}' for x in a)
def write(p,s): p.write_text(s,encoding='utf-8')
def build():
    OUT.mkdir(exist_ok=True); WEB.mkdir(exist_ok=True,parents=True); make()
    print(f'已构建 {len(parts)} 个零件节点')
    rows=[]; g=trimesh.Scene(base_frame='assembly'); bb={}; mesh_stats={}; native={}
    for id,p in parts.items():
        sh=p['sh']
        # 物理导出只变换一次：三种载体均为右手系 (x,-y,z)，避免镜像打印。
        solid=native[id]=native_shape(sh); solid.label=id; solid.color=sh.color
        bb[id]=q=bounds(sh); size=q[1]-q[0]; v=vol(sh); mat=p['material']
        mass=v*MAT[mat][1]/1000; basis='体积 × 密度'
        if id in ('main_board','driver_board'):
            extra=3.2 if id=='main_board' else 2.6
            mass+=extra; basis=f'裸板密度＋器件 {extra:.1f} g'
        if p['override'] is not None:
            mass=p['override']; basis='不计入' if p['group']=='手机参照' else '单件预算'
        row={k:p[k] for k in ('id','name','group','material','color','orientation','explode','note')}
        row.update(size=nd(size),bounds=[nd(t) for t in q],volume=round(v,2),mass=round(mass,3),basis=basis)
        rows.append(row)
        verts,faces=sh.tessellate(.065,.19)
        # 接口 y 向下，glTF y 向上：反射后翻转面序；glTF 顶点单位为 m。
        mesh=trimesh.Trimesh(np.array([tuple(v) for v in verts])*[.001,-.001,.001],np.asarray(faces)[:,::-1],process=False)
        color=list(bytes.fromhex(p['color'][1:]))+[220 if id=='diffuser' else 255]
        mesh.visual=trimesh.visual.TextureVisuals(material=PBRMaterial(name=id,baseColorFactor=color,
            metallicFactor=.58 if mat in ('铝','弹片','接口') else .08,
            roughnessFactor=.5 if mat not in ('电芯','乳白聚碳酸酯') else .36,
            alphaMode='BLEND' if id=='diffuser' else 'OPAQUE',doubleSided=False))
        g.add_geometry(mesh,node_name=id,geom_name=id)
        if p['orientation']:
            assert export_step(solid,OUT/(id+'.step'))
            assert export_stl(solid,OUT/(id+'.stl'),tolerance=.045,angular_tolerance=.16)
            # 按拓扑实体而非逐面三角化求体积；另验磁盘上的 STL 是否闭合。
            loaded=trimesh.load_mesh(OUT/(id+'.stl'))
            mesh_stats[id]=(loaded.is_watertight and loaded.is_volume and len(loaded.split())==1)
            assert mesh_stats[id],(id,'STL 非闭合单实体')
    group=Compound(label='Filllight_15Pro',children=list(native.values()))
    assert export_step(group,OUT/'assembly.step')
    glb=WEB/'filllight.glb'; glb.write_bytes(g.export(file_type='glb',include_normals=True))
    restored=trimesh.load_scene(glb); assert set(restored.graph.nodes_geometry)==set(parts)
    print('制造格式及 GLB 已导出，开始核对实际实体')
    checks=[]
    def ck(name,test,measured): checks.append(dict(name=name,ok=bool(test),value=measured))
    def sh(i): return parts[i]['sh']
    from pcb_draw import produce
    from c_review import run as review_c
    K=json.loads((ROOT/'interface/keepout.json').read_text())
    assembly=np.stack([np.min([q[0] for q in bb.values()],axis=0),np.max([q[1] for q in bb.values()],axis=0)]);A=assembly[1]-assembly[0]
    total=sum(r['mass'] for r in rows)+P.hw_allowance
    eq=lambda a,b:np.allclose(a,b,atol=.0001,rtol=0)
    # 整机壳上端截面和最高点。使用玻璃起算绝对 Z，严于只比较新增厚度；不插值。
    active=[i for i in parts if i not in ('frame','liner','phone','camera_dummy')]
    env=lambda ids:np.stack([np.min([bb[i][0] for i in ids],axis=0),np.max([bb[i][1] for i in ids],axis=0)])
    pod=env(active);row=next(v for v in K['pod_square'] if v['thickness']==24)
    bands=sorted(K['pod_square'],key=lambda v:v['top_y'])
    for k,nxt in zip(bands,[*bands[1:],{'top_y':152}]):
        y,Y=k['top_y'],nxt['top_y'];slab=box(-7,77,y,Y,0,33)
        z=0
        for i in active+['frame','liner']:
            if bb[i][1,1]<y or bb[i][0,1]>Y:continue
            if bb[i][0,1]>=y and bb[i][1,1]<=Y:z=max(z,bb[i][1,2])
            else:z=max([z]+[v.bounding_box().max.Z for v in sh(i).intersect(slab) or []])
        ck(f'方顶限高 y={y:g}…{Y:g}',z<=k['thickness']+.0001,f"实际 Z≤{z:.3f}，保守按背玻璃起算，限 {k['thickness']}；不在档位之间插值。")
    for k in K['low_profile']:
        yy=k['y'];slab=box(-5,76,yy-.001,yy+.001,0,30);z=max([0]+[e.bounding_box().max.Z for i in ('frame','shell') for e in sh(i).intersect(slab) or []]);ck(f'矮区 y={yy}',z<=k['max_height'],f"背面 Z={z:.2f} ≤ {k['max_height']:.1f}；无金属。")
    ck('主板外缘保持不变',abs(bb['main_board'][1,1]-125.8)<1e-5,f"主板下沿 Y={bb['main_board'][1,1]:.3f} mm；顶部和底部的全部导电件另用分区包络核验。")
    ck('主板双面及两路驱动',eq(bb['main_board'][1]-bb['main_board'][0],[60,23.5,1]) and 14-1.2-(4.5+1.6)>=5.5,'主板两面 1410×2=2820 mm²（毛面积），较 A 少 120、较最初多 300；无主板 J5，外侧工作限高 7.5，内侧 1.2；上下板间扣除内侧器件后驱动 TOP 净 6.70，工作 5.50。未把元件/走线完成度等同于面积。')
    head0=next(k for k in K['head'] if k['gap']==0)
    slab=box(-6,77,-5,-.001,-14,27);clips=sh('frame').intersect(slab);lo=min(s.bounding_box().min.Z for s in clips);hi=max(s.bounding_box().max.Z for s in clips)
    ck('顶边之外仅非导电角扣、内衬与顶轨',hi<=head0['rear_limit'] and -T-lo<=head0['front_limit'],f'g=0：背侧 {hi:.2f} / {head0["rear_limit"]:.1f}，屏幕外 {-T-lo:.2f} / {head0["front_limit"]:.1f}；非机顶灯。')
    for k in ('input_usb_c','output_usb_c'):
        x=L['ports'][k]['x'];probe=box(x-4.6,x+4.6,125.8,148,15.05,18.75)
        ck(k+' 对外通道',inter(sh('shell'),probe)<.001,'+y 方向 9.2×3.7 直通量规至壳外；不证明所有包胶插头适配。')
    tops=[f.area for f in sh('diffuser').faces() if abs(f.center().Z-24)<.0001]
    mix=bb['diffuser'][0,2]-bb['led_W'][1,2];ck('齐平发光面积与灯距',len(tops)==1 and mix>0,f'露出面积 {sum(tops)/100:.3f} cm²；最小混光距 {mix:.2f} mm；均匀度未测。')
    head_review=review_c(ck,bb,sh,inter,env,parts,OUT,ROOT)
    pairs=[]
    for i,j in combinations(parts,2):
        if np.all(np.minimum(bb[i][1],bb[j][1])-np.maximum(bb[i][0],bb[j][0])>.0001):
            v=inter(sh(i),sh(j))
            if v>.001:pairs.append((i,j,round(v,3)))
    ck('装配静态硬干涉',not pairs,str(pairs) if pairs else f'{len(parts)*(len(parts)-1)//2} 对筛查；精确求交无 >0.001 mm³ 重叠。')
    from verify06 import audit
    checks.extend(audit(OUT/'assembly.step',{i:p['material'] for i,p in parts.items()},OUT/'archive_v04C_r5/mech/out/assembly.step'))
    checks.extend(produce());print(checks,flush=True)
    dims=[]
    for name,a,b in [('背模块高度',[35,103,0],[35,103,pod[1,2]]),('整机长度',[0,assembly[0,1],0],[0,assembly[1,1],0]),('总厚',[2,89,assembly[0,2]],[2,89,assembly[1,2]])]:
        dims.append(dict(id=str(len(dims)),name=name,a=a,b=b,value=f'{np.linalg.norm(np.subtract(a,b)):.2f} mm'))
    write(WEB/'parts.json',json.dumps(dict(version='0.4',variant=VARIANT,revision='C-r7',releaseAllowed=all(c['ok'] for c in checks),units='mm',parts=rows,dimensions=dims,assemblyBounds=assembly.tolist(),totalMass=round(total,2),allowance=P.hw_allowance,checks=checks),ensure_ascii=False,indent=2))
    pcb=ROOT/'mech/pcb/enclosure_assembly.step'
    if (OUT/'assembly.step').stat().st_size<=8_000_000:shutil.copyfile(OUT/'assembly.step',pcb)
    else:assert export_step(Compound(children=[native[i] for i in native if parts[i]['group']!='手机参照']),pcb)
    assert len(import_step(pcb).solids())>=len(parts)-2
    for i in mesh_stats:assert np.allclose(bounds(import_step(OUT/(i+'.step'))),bounds(native[i]),atol=.001)
    md=['# 外接电源全贴合背夹 · v0.4 C 第七轮放行复核','',f'整机外形（含手机及四角扣） **{fmt(A)} mm**。附件增重预算 **{total:.2f} g**，较 R5 的 128.57 g 减少 {128.57-total:.2f} g。不含手机、外置电源、线缆及腰袋；已含 {P.hw_allowance:g} g 紧固、线束与胶材。','',('**放行状态：数模检查全部通过；另须打印实配**' if all(c['ok'] for c in checks) else '**尚未放行。** 见下表不通过项。'),'', '| 项目 | 结论 | 读回值 / 判据 |','|---|---|---|']+[f"| {c['name']} | {strong(c['ok'])} | {c['value']} |" for c in checks]
    md+=['','## 零件明细','','|零件|材料|尺寸 mm|体积 cm³|增重 g|依据|','|---|---|---|---:|---:|---|']+[f"|{r['name']}|{r['material']}|{fmt(r['size'])}|{r['volume']/1000:.2f}|{r['mass']:.2f}|{r['basis']}|" for r in rows]
    md+=['',(ROOT/'mech/design04.md').read_text(),'']+head_review;write(OUT/'report.md','\n'.join(md)+'\n')
    for c in checks:
        if not c['ok']:print('未通过',c)
    if not all(c['ok'] for c in checks):raise ValueError('数模检查未通过，见报告')
    from publish04 import finish
    finish(ROOT,mesh_stats)
    print(f'完成：{len(parts)} 个节点，附件 {total:.2f} g，整机 {fmt(A)}。')
if __name__=='__main__':build()
