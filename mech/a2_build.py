"""A2 单独输出；对实际制造文件、接口与成对实体重新验收。"""
from itertools import combinations
from pathlib import Path
import json,shutil
import numpy as np, trimesh
from build123d import Compound,export_step,export_stl,import_step
from trimesh.visual.material import PBRMaterial
from a2_layout import ROOT,PCB,CELL,UP,PLUG,SWELL,contract,power,runtimes
from export import bounds,native_shape,vol,inter,nd,box,MAT,P
import a2_model
from frozen08 import check as frozen
OUT=ROOT/'mech/out/battery'; WEB=ROOT/'web/models'
def dump(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def build():
    frozen();OUT.mkdir(exist_ok=True,parents=True);j=contract();parts=a2_model.make(j);print('A2 实体完成',len(parts),flush=True)
    rows=[];bb={};native={};scene=trimesh.Scene(base_frame='assembly');checks=[]
    def ck(name,test,value):checks.append(dict(name=name,ok=bool(test),value=str(value)))
    def sh(i):return parts[i]['sh']
    def env(ids):
        vals=[bb[i] for i in ids];return np.array([np.min([a[0] for a in vals],0),np.max([a[1] for a in vals],0)])
    for i,p in parts.items():
        s=p['sh'];a=bb[i]=bounds(s);v=vol(s);r={k:p[k] for k in ('id','name','group','material','color','orientation','explode','note')}
        mass=p['override'];tx='单件预算' if mass is not None else '实体体积 × 密度'
        if mass is None:mass=v*MAT[p['material']][1]/1000+(4.1 if i=='main_board' else 2.6 if i=='driver_board' else 0)
        if i in ('main_board','driver_board'):tx='裸板加未单列的器件预算'
        r.update(volume=round(v,3),size=nd(a[1]-a[0]),bounds=[nd(t) for t in a],mass=round(mass,3),basis=tx);rows.append(r)
        t=native[i]=native_shape(s);t.label=i;t.color=s.color
        vs,fs=s.tessellate(.065,.19)
        mesh=trimesh.Trimesh(np.array([tuple(vv) for vv in vs])*[.001,-.001,.001],np.asarray(fs)[:,::-1],process=False)
        mesh.visual=trimesh.visual.TextureVisuals(material=PBRMaterial(name=i,baseColorFactor=list(bytes.fromhex(p['color'][1:]))+[220 if i=='diffuser' else 255],metallicFactor=.13,roughnessFactor=.53,alphaMode='BLEND' if i=='diffuser' else 'OPAQUE'))
        scene.add_geometry(mesh,node_name=i,geom_name=i)
        if p['orientation']:
            assert export_step(t,OUT/(i+'.step')) and export_stl(t,OUT/(i+'.stl'),tolerance=.045,angular_tolerance=.16)
            step=import_step(OUT/(i+'.step'));smesh=trimesh.load_mesh(OUT/(i+'.stl'))
            ck('制造回读 '+i,len(step.solids())==1 and step.is_valid and np.allclose(bounds(step),bounds(t),atol=.0001) and abs(vol(step)-vol(t))<.01 and smesh.is_volume and len(smesh.split())==1,'STEP 有效单体；STL 单闭壳；体积 %.2f mm³'%v)
    assert export_step(Compound(label='Filllight_A2',children=list(native.values())),OUT/'assembly.step')
    shutil.copyfile(OUT/'assembly.step',PCB/'enclosure_assembly_battery.step')
    glb=WEB/'filllight_battery.glb';glb.write_bytes(scene.export(file_type='glb',include_normals=True))
    ck('GLB 回读',set(trimesh.load_scene(glb).graph.nodes_geometry)==set(parts) and glb.stat().st_size<=8000000,f'{len(rows)} 个同名节点；{glb.stat().st_size} B')
    ad=env(parts);common=json.loads((WEB/'parts.json').read_text())
    from verify06 import audit
    checks+=audit(PCB/'enclosure_assembly_battery.step',{i:p['material'] for i,p in parts.items()},ROOT/'mech/out/assembly.step')
    for c in checks:
        if c['name'].startswith('四角扣侧壁'):c['value']=c['value'].replace('相对 R5','相对 C-r7')
    print('装配已回读，核对干涉与高程',flush=True)
    pairs=[]
    for a,b in combinations(parts,2):
        if np.min(np.minimum(bb[a][1],bb[b][1])-np.maximum(bb[a][0],bb[b][0]))>.0001:
            v=inter(sh(a),sh(b))
            if v>.001:pairs.append((a,b,round(v,5)))
    ck('全部节点静态干涉',not pairs,str(pairs) if pairs else f'{len(rows)*(len(rows)-1)//2} 对，实心重叠不超过 0.001 mm³')
    cparts={s.label:s for s in import_step(ROOT/'mech/out/assembly.step').children}
    frozenids=[i for i in parts if i.startswith(('driver_','led_')) or i in ('frame','liner','blower','sink','shield','diffuser')]
    error=[]
    for i in frozenids:
        a=native[i];b=cparts[i]
        if not np.allclose(bounds(a),bounds(b),rtol=0,atol=1e-5) or abs(vol(a)-vol(b))>.0001:error.append(i)
    old=json.loads((PCB/'pcb_interface.json').read_text());ck('共用板、夹持和光机',not error and all(j['boards'][k]==old['boards'][k] for k in ('led','driver')),f'{len(frozenids)} 节点共用 C 生成器；装配体积/位置包络核对；两个板合同深度相等。差异 {error}')
    from c_review import run
    def inherit(name,test,value):
        if name=='C 无电池与风机量规':
            ck('A2 两芯且保留风机',all(i in parts for i in ['cell_1','cell_2','main_j5']) and np.allclose(bb['blower'][1]-bb['blower'][0],[35,35,10]),'2S1P；35×35×10 风机');return
        if name=='去电芯后的热通道':name='保留 C 进风净高与十二鳍';value='风机与机背隔热毡间净高 3.70 mm；风道内不装电芯。'
        ck(name,test,value)
    run(inherit,bb,sh,inter,env,parts,OUT,ROOT)
    for i in ('input_usb_c','output_usb_c'):
        x=float(bb[i][:,0].mean());ck(i+' 插接通道',inter(sh('shell'),box(x-4.6,x+4.6,125.8,148,15.05,18.75))<.001,'9.2×3.7 mm 口规')
    ck('共用齐平发光窗和混光间距',abs(bb['diffuser'][1,2]-24)<1e-6 and bb['diffuser'][0,2]>bb['led_W'][1,2],f"混光 {bb['diffuser'][0,2]-bb['led_W'][1,2]:.2f} mm")
    ck('主板双面及驱动器件空间',np.allclose(bb['main_board'][1]-bb['main_board'][0],[60,23.5,1]) and bb['main_board'][0,2]-1.2-bb['driver_board'][1,2]>=5.5,'1410 mm²/面；驱动顶部工作 5.5 mm；电气布线和热不在此项内。')
    ck('极耳、线端插头与六针定义',j['battery']['connector']['nets']==['BAT+','BAT+','MID','NTC','BAT−','BAT−'] and abs(bb['battery_plug'][1,2]-bb['main_j5'][0,2]-14.5)<1e-5,'总高 14.50，额定 ≥5 A/针；热敏另一端 BAT−，中点只检测。')
    def others(g,ids):return sum(inter(sh(i),g) for i in ids)
    no_cells=set(parts)-{'cell_1','cell_2','cell_separator','cell_ntc'}
    sw=others(box(*SWELL),no_cells)
    ck('双芯厚向各 10% 膨胀、无螺钉/筋压迫',sw<.001,f'量规 {SWELL}；干涉 {sw:.7f} mm³；电芯与保护电路不共包。')
    lift=box(*PLUG[:4],22.0,48)
    vv=others(lift,set(parts)-{'main_j5','battery_plug','battery_lid','panel_flex','panel_tail','overlay','lid_fasteners',*[x for x in parts if x.startswith(('key_','light_'))]})
    ck('开盖后插合件提离扫掠',vv<.001,f'板座不动，线端解锁后沿 +Z 拔出；硬件重叠 {vv:.6f} mm³，软线与手感待样件。')
    finger=others(box(49,69,100,120,32,47),set(parts)-{'battery_lid','overlay','panel_flex','panel_tail','lid_fasteners'});ck('开盖后的指腹操作空间',finger<.001,f'20×20×15 mm，Z32…47，量规交叠 {finger:.6f} mm³。')
    ck('电芯上提更换',others(box(*SWELL[:4],SWELL[4],46),no_cells-{'battery_lid','panel_flex','panel_tail','overlay','lid_fasteners',*[x for x in parts if x.startswith(('key_','light_'))]})<.001,'去盖、提线端并解锁后提取配组软包。')
    ids=set(parts)-{'phone','camera_dummy'}
    def high(y,Y):
        slab=box(-8,79,y,Y,-.01,35);z=0
        for i in ids:
            a=bb[i]
            if a[1,1]<y or a[0,1]>Y or a[1,2]<=z+1e-6:continue
            if a[0,1]>=y and a[1,1]<=Y:z=max(z,a[1,2]);continue
            for t in sh(i).intersect(slab) or []:
                if t.solids():z=max(z,t.bounding_box().max.Z)
        return float(z)
    ks=[(48,7),(50,9.3),(52,11.7),(54,14),(56,16.4),(58,18.7),(60,21.1),(62,23.4),(64,25.8),(66,28.2),(68,29.3),(70,30.4),(72,31.4),(74,32.5),(76,33.6)]
    for n,(y,h) in enumerate(ks):
        Y=ks[n+1][0] if n<len(ks)-1 else 150;z=high(y,Y)
        ck(f'连续区间 Y{y}…{Y}',z<=h-1.5+.0001,f'整段实体最大 Z={z:.3f}；采用左端保守阶梯上限 {h-1.5:.2f}，不靠插值。')
    curve={str(y):round(high(y-.0001,y+.0001),3) for y in [48,52,55.1,56,58,60,62,64,64.1,66,68,70,72,74,76,90,99.5,100.05,101,103,110,125,129.9,130.1,132.4,137.3,142.9,146]}
    for t,y in [(24,64),(25,64.8),(26,65.7),(27,66.5),(28,67.4),(29,69),(30,70.8),(32,74.5)]:
        # 仅校核新增高舱；24 mm 冻结肩部另按全宽区间和实体截面核验
        vv=others(box(-5,77,48,y-.0001,t-.00001,34),['shell','battery_lid','panel_flex','overlay'])
        ck(f'直角顶 {t} mm / Y≥{y}',vv<.001,f'阈值前方相交 {vv:.7f} mm³')
    for vm,v,w,expected in [(3.,6.,20,0),(3.39,6.79,20,0),(3.4,6.8,20,1.5),(3.7,7.4,10,3),(3.7,7.4,10.01,1.5)]:
        lamp,phone=power(vm,v,w,3);load=(lamp/.88+phone*5/.9+2)/v if lamp else 0
        ck(f'电池限流 {vm:g} V / 灯 {w:g}',load<=4.8+1e-8 and phone<=expected+1e-8 and (vm>3 or lamp==0),f'灯 {lamp:.2f} W，手机 {phone:.3f} A，包电流 {load:.3f} A')
    sweep=0;max_i=0
    for vmin in np.arange(3.0,4.201,.05):
        for vpack in [2*vmin,vmin+4.2]:
            for w in [0,3,9.9,10,10.1,15,20]:
                for ask in [0,1.5,3]:
                    lamp,phone=power(vmin,vpack,w,ask);max_i=max(max_i,(lamp/.88+5*phone/.9+2)/vpack)
                    assert lamp<=w+1e-8 and phone<=ask+1e-8
                    if vmin<3.4:assert phone==0
                    if vmin<=3:assert lamp==0
                    if w>10:assert phone<=1.5
                    sweep+=1
    ex=power(3.4,6.8,20,3);nom=power(3.7,7.4,10,3)
    ck('电池分档边界与满输出',max_i<=4.8+1e-8 and 1.42<ex[1]<1.43 and nom==(10,3) and power(3.8,7.6,20,3,False)==(0.,0.),f'{sweep} 档；最大 {max_i:.3f} A；均衡 6.8V/20W 手机 {ex[1]:.3f} A；7.4V/10W 手机 {nom[1]:.1f} A。')
    p5=bb['main_j5'];pw=bb['battery_plug']
    ck('板端、线端与 J5 装配合同',np.allclose(p5[0],[PLUG[0],PLUG[2],PLUG[4]]) and np.allclose(pw[1],[PLUG[1],PLUG[3],PLUG[5]]) and abs(p5[1,2]-pw[0,2])<1e-6,'板端 Z15…22；插合后合并包络自板面起 14.50 mm。')
    ck('风道、电芯、主热舌隔离',bb['cell_1'][0,2]-bb['sink'][1,2]>=1.49 and bb['cell_1'][0,1]>bb['blower'][1,1] and j['battery']['ntc']['charge_max_C']==45 and j['battery']['ntc']['discharge_max_C']==60,'热舌至芯 1.50 mm，含 0.30 隔热层＋1.20 托盘；芯不在风机投影内。温限是验收要求，不是实测通过。')
    from a2_pcb import draw
    checks+=draw(j,OUT)
    total=round(sum(r['mass'] for r in rows)+P.hw_allowance+1.1,2)
    dims=[dict(id=str(n),name=name,a=a,b=b,value=f'{np.linalg.norm(np.array(a)-b):.2f} mm') for n,(name,a,b) in enumerate([('背模块最高点',[35,114,0],[35,114,31.95]),('整机长度',[0,ad[0,1],0],[0,ad[1,1],0]),('含扣总厚',[2,112,ad[0,2]],[2,112,ad[1,2]])])]
    meta=dict(version='0.4',variant='A2',revision='A2-r1',units='mm',releaseAllowed=all(c['ok'] for c in checks),parts=rows,dimensions=dims,assemblyBounds=ad.tolist(),totalMass=total,allowance=P.hw_allowance+1.1,checks=checks,runtime_min=runtimes(.30),profile_y_z=curve)
    dump(WEB/'parts_battery.json',meta)
    from a2_report import report
    report(meta,j)
    bad=[c for c in checks if not c['ok']];print(f'{len(checks)-len(bad)}/{len(checks)}；{total} g；',bad,flush=True)
    if bad:raise SystemExit(3)
    frozen()
if __name__=='__main__':build()
