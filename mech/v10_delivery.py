"""公开目录终验（不改制造件）：核实发布件、逐对台账、板图与灯头指纹均与候验版相同。"""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent;out=root/'out';state=out/'round10';pkg=state/'final'
def read(f):return json.loads(f.read_bytes())
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
result={}
for v in 'CA':
    a=v=='A';s='_battery' if a else '';w=pkg/v;dest=out/'battery' if a else out;web=root.parent/'web'
    meta=read(web/'models'/('parts'+s+'.json'));j=read(root/'pcb'/('pcb_interface'+s+'.json'))
    assert meta['revision']==v+'5-r1' and meta['releaseAllowed'] and all(c['ok'] for c in meta['checks'])
    assert j['variant']==v and j['version']=='0.5' and meta['revision'] in (web/('battery.html' if a else 'index.html')).read_text()
    files={}
    def same(src,dst):
        assert src.is_file() and dst.is_file() and sha(src)==sha(dst),(src,dst)
        files[str(dst.relative_to(root.parent))]=sha(dst)
    for f in w.iterdir():
        if f.suffix in ('.step','.stl'):same(f,dest/f.name)
    for n in ['filllight'+s+'.glb','parts'+s+'.json']:same(w/n,web/'models'/n)
    for n in ('main'+s,'assembly_layout'+s,*(() if a else ('driver','led'))):
        for ext in ('.dxf','.png'):same(w/'pcb'/(n+ext),root/'pcb'/(n+ext))
    same(w/'assembly.step',root/'pcb'/('enclosure_assembly'+s+'.step'))
    same(w/'pcb'/('pcb_interface'+s+'.json'),root/'pcb'/('pcb_interface'+s+'.json'))
    x=read(w/'intersection_step.json');count=len(meta['parts'])-2;assert not x['fail'] and len(x['pairs'])==count*(count-1)//2
    result[v]={'pairs':len(x['pairs']),'max_overlap':x['maximum_mm3'],'checks':len(meta['checks']),'mass':meta['totalMass'],'size':[round(b-a,3) for a,b in zip(*meta['assemblyBounds'])],'files':files}
common=read(pkg/'common_head.json')
assert common['interfaces'][0]==common['interfaces'][1]
for k,r in common['parts'].items():
    n=k+'.step'
    assert r['C_sha256']==r['A_sha256']==sha(pkg/'A/head_step'/n)==sha(pkg/'C/head_step'/n)
    if (out/n).exists():assert sha(out/n)==sha(out/'battery'/n)==r['C_sha256']
    assert abs(r['C_volume']-r['A_volume'])<1e-5
webcheck=read(state/'web-check.json');assert webcheck['code']==0
result.update(head_parts=len(common['parts']),web=webcheck['transport'])
(state/'delivery.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print({v:{k:t for k,t in result[v].items() if k!='files'} for v in 'CA'},result['head_parts'],result['web'])
