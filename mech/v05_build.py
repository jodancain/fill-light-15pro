"""先写隔离构建目录，验收成功才替换该变体发布件；C/A 共用灯头由同一构造器生成。"""
import sys,shutil,hashlib,os
from itertools import combinations
from v05_layout import *
from v05_model import make,path
from v05_check import checks
from export import native_shape,vol,bounds,nd,fmt,box,np
from model import MAT
from build123d import Compound,export_step,export_stl,import_step
from trimesh.visual.material import PBRMaterial
import trimesh
OUT=R/'mech/out';WEB=R/'web/models'
STAGE=OUT/'round11'/os.environ.get('FILL_STAGE_NAME','final');assert STAGE.parent==OUT/'round11'
def dump(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def build(v):
    j=contract(v);a=v=='A';s='_battery' if a else '';work=STAGE/v;work.mkdir(parents=True,exist_ok=True);pd=work/'pcb'
    p=make(v,j);bb={i:bounds(r['sh']) for i,r in p.items()};print('实体就绪',v,len(p),flush=True)
    ck,curve,hc,metal=checks(j,p,bb);print('装配检查：',[c for c in ck if not c['ok']],flush=True)
    scene=trimesh.Scene(base_frame='assembly');ns=[];rows=[]
    for i,k in p.items():
        h=k['sh'];n=native_shape(h);n.label=i;n.color=h.color;ns.append(n);q=bb[i];vv=vol(h)
        mass=k['override'] if k['override'] is not None else vv*MAT[k['material']][1]/1000+({'main_board':4.1,'driver_board':2.6}.get(i,0))
        row={f:k[f] for f in ('id','name','group','material','orientation','explode','color','note')}
        row.update(bounds=[nd(u) for u in q],size=nd(q[1]-q[0]),volume=round(vv,4),mass=round(mass,3),basis='组件预算' if k['override'] is not None else '体积密度；主/驱板另计贴装件');rows.append(row)
        vs,fs=h.tessellate(.065,.19);mesh=trimesh.Trimesh(np.array([tuple(xx) for xx in vs])*[.001,-.001,.001],np.asarray(fs)[:,::-1],process=False)
        mesh.visual=trimesh.visual.TextureVisuals(material=PBRMaterial(name=i,baseColorFactor=list(bytes.fromhex(k['color'][1:]))+[220 if i=='diffuser' else 255],metallicFactor=.12,roughnessFactor=.53,alphaMode='BLEND' if i=='diffuser' else 'OPAQUE'));scene.add_geometry(mesh,node_name=i,geom_name=i)
        if k['orientation']:
            assert export_step(n,work/(i+'.step')) and export_stl(n,work/(i+'.stl'),tolerance=.045,angular_tolerance=.16)
            obj=import_step(work/(i+'.step'));mesh=trimesh.load_mesh(work/(i+'.stl'))
            ck.append(dict(name=i+' 制造回读',ok=bool(obj.is_valid and len(obj.solids())==1 and mesh.is_volume and len(mesh.split())==1 and abs(vol(obj)-vv)<.01 and np.allclose(bounds(obj),bounds(n),atol=.0001)),value=f'STEP 有效={obj.is_valid}，实体 {len(obj.solids())}，体积 {vol(obj):.4f}/{vv:.4f} mm³；STL 有向闭合={mesh.is_volume}，连通壳 {len(mesh.split())}'))
    group=Compound(label='Filllight_'+v+'5',children=ns);assert export_step(group,work/'assembly.step')
    back={x.label:x for x in import_step(work/'assembly.step').children};ck.append(dict(name='整机 STEP 回读',ok=back.keys()==p.keys() and all(abs(vol(back[k])-vol(p[k]['sh']))<.01 for k in p),value=f'{len(back)} 个命名节点'))
    from v10_proof import audit_step,profile
    ck.append(audit_step(back,work));j['head_profile_1mm']=profile(p,work)
    glb=work/('filllight'+s+'.glb');glb.write_bytes(scene.export(file_type='glb',include_normals=True));ck.append(dict(name='GLB 回读',ok=set(trimesh.load_scene(glb).graph.nodes_geometry)==set(p) and glb.stat().st_size<8000000,value=f'{glb.stat().st_size} B'))
    from v05_pcb import pcb
    cache=OUT/'round11'/v;dcheck=cache/'dxf-check.json'
    from v10_ecad_cache import valid as cache_valid
    if cache_valid(cache,j) and dcheck.is_file() and (cache/'pcb'/('assembly_layout'+s+'.png')).is_file():
        # DXF 由同轮独立任务生成；再次核对板框、位号、接口与实际走线。
        import ezdxf,pcb_draw as draw
        pd.mkdir(exist_ok=True);names=[k+(s if k=='main' else '') for k in j['boards']]+['assembly_layout'+s]
        for name in names:
            for ext in ('.dxf','.png'):
                src=cache/'pcb'/(name+ext);shutil.copy2(src,pd/src.name)
        for k,b in j['boards'].items():
            doc=ezdxf.readfile(pd/(k+(s if k=='main' else '')+'.dxf'));ck+=draw.audit(b,doc)
            notes=[e.dxf.text for e in doc.modelspace().query('TEXT')]
            assert any(f"BOT Z={b['origin'][2]:g}" in t for t in notes)
        rd=ezdxf.readfile(pd/('assembly_layout'+s+'.dxf'));route=list(rd.modelspace().query('LINE[layer=="HARNESS"]'));pts=path()
        assert len(route)==len(pts)-1 and all(np.allclose([e.dxf.start.x,-e.dxf.start.y,e.dxf.end.x,-e.dxf.end.y],[*aa[:2],*bb[:2]]) for e,aa,bb in zip(route,pts,pts[1:]))
        outlines=list(rd.modelspace().query('LWPOLYLINE[layer=="BOARD_OUTLINE"]'))
        ck.append(dict(name='装配布置 DXF 与线轨',ok=rd.units==4 and len(outlines)==3 and all(e.closed for e in outlines),value='闭合三板，路径逐线段回读'))
    else:ck+=pcb(j,pd)
    ex=np.array([np.min([q[0] for q in bb.values()],0),np.max([q[1] for q in bb.values()],0)])
    j['harness'].update(centerline_xyz=[list(q[:3]) for q in path()],external_rail_bbox=bb['side_rail'].round(3).tolist(),trunk_bbox=bb['trunk'].round(3).tolist(),trunk_length_mm=round(sum(math.dist(q[:3],t[:3]) for q,t in zip(path(),path()[1:])),2))
    j['conductive_bounds_xyz']={i:bb[i].round(3).tolist() for i in metal};j['head_profile']=hc;j['back_profile']=curve
    if a:j['battery']['ntc']['bbox']=bb['cell_ntc'].round(3).tolist()
    dump(pd/('pcb_interface'+s+'.json'),j)
    dims=[dict(id=str(n),name=key,a=aa,b=tt,value=f'{math.dist(aa,tt):.2f} mm') for n,(key,aa,tt) in enumerate([('灯头间距',[35,-13,0],[35,0,0]),('灯头最大深度',[35,-35,-29.55],[35,-35,11.6]),('背夹厚度（玻璃以上）',[35,110,0],[35,110,j['enclosure']['back_height']]),('整机长度',[0,ex[0,1],0],[0,ex[1,1],0])])]
    m=dict(version='0.5',variant=v,revision=v+'5-r2',releaseAllowed=all(c['ok'] for c in ck),units='mm',dimensions=dims,assemblyBounds=ex.tolist(),allowance=3.,parts=rows,checks=ck,totalMass=round(sum(r['mass'] for r in rows)+3,2))
    dump(work/('parts'+s+'.json'),m)
    from v05_report import report
    report(work/'report.md',m,j);print(v,len(ck),'检查，失败：',[c for c in ck if not c['ok']],flush=True)
    if not m['releaseAllowed']:raise ValueError('未发布，见 '+str(work/'report.md'))
    return work,m,j
def publish(items):
    from v05_report import website,readme
    for work,m,j in items:
        v=j['variant'];a=v=='A';s='_battery' if a else '';dest=OUT/'battery' if a else OUT;dest.mkdir(exist_ok=True)
        # 只清理旧版本清单中已归档、属本变体的制造文件。
        for f in dest.iterdir():
            if f.is_file() and f.suffix in ('.step','.stl') and not(work/f.name).exists():
                archive=OUT/'archive_v04_final'/f.relative_to(R)
                if archive.is_file():f.unlink()
        for f in work.iterdir():
            if f.suffix in ('.step','.stl'):shutil.copy2(f,dest/f.name)
        for f in (work/'pcb').iterdir():
            if a and f.stem in ('driver','led') and (PCB/f.name).exists():continue
            shutil.copy2(f,PCB/f.name)
        shutil.copy2(work/'assembly.step',PCB/('enclosure_assembly'+s+'.step'))
        for n in ('parts'+s+'.json','filllight'+s+'.glb'):shutil.copy2(work/n,WEB/n)
        shutil.copy2(work/'report.md',OUT/('report'+s+'.md'));website(m,j)
    readme()
def readstage(v):
    s='_battery' if v=='A' else '';w=STAGE/v
    m=json.loads((w/('parts'+s+'.json')).read_text());j=json.loads((w/'pcb'/('pcb_interface'+s+'.json')).read_text())
    assert m['revision']==j['revision']==v+'5-r2' and m['releaseAllowed'] and all(x['ok'] for x in m['checks'])
    h=json.loads((w/'stage-sha.json').read_text())
    for name,expected in h.items():assert hashlib.sha256((w/name).read_bytes()).hexdigest()==expected,name
    return w,m,j
def seal(item):
    w,_,_=item;dump(w/'stage-sha.json',{str(f.relative_to(w)):hashlib.sha256(f.read_bytes()).hexdigest() for f in w.rglob('*') if f.is_file() and 'head_step' not in f.parts and f.name!='stage-sha.json'})
    return item
if __name__=='__main__':
    arg=(sys.argv[1:] or ['all'])[0].upper();assert arg in ('C','A','ALL','RELEASE')
    if arg=='RELEASE':
        import os,time
        if os.environ.get('FILL_JOIN')=='1':
            files=[OUT/'round11'/(v+'-build.exit') for v in 'CA']
            while not all(f.is_file() and f.stat().st_size for f in files):
                if any(f.is_file() and f.read_text().strip() not in ('','0') for f in files):raise RuntimeError('单版构建未通过')
                time.sleep(4)
            assert all(f.read_text().strip()=='0' for f in files)
        items=[readstage(v) for v in 'CA']
        for w,m,j in items:
            # Validate live connector blocks against the actual staged STEP node envelopes.
            fresh=contract(j['variant'])['harness']; conn=fresh['power']['inline_head']; nodes={x.label:x for x in import_step(w/'assembly.step').children}
            for n,center in enumerate(conn['centers_xyz'],1):
                bb=bounds(nodes['head_power_lock'+str(n)]);assert np.allclose(bb.mean(axis=0),np.asarray(center)*[1,-1,1]) and np.allclose(bb[1]-bb[0],conn['envelope_per_pair_xyz_mm'])
            j['harness']['power']['inline_head']=conn;j['harness']['locking']=fresh['locking'];j['harness']['rloop_mohm_max']=fresh['rloop_mohm_max']
            dump(next((w/'pcb').glob('pcb_interface*.json')),j)
    else:
        vs='AC' if arg=='ALL' else arg;items=[seal(build(v)) for v in vs]
        if arg=='ALL':items.reverse()
    if arg in ('ALL','RELEASE'):
        from v10_proof import common
        common(items);publish(items)
        for item in items:seal(item)
    else:print('阶段验收通过；双版共用件比对后才发布。')
