"""依据导出的装配 STEP 重读；不以布尔成功或两个内存对象共指作为交付证据。"""
from pathlib import Path
import hashlib,json,math,shutil
from itertools import combinations
from build123d import import_step,export_step
from export import bounds,vol,inter,np
from v05_layout import R

def dump(f,j):f.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def audit_step(children,work):
    names=sorted(set(children)-{'phone','camera_dummy'});B={n:bounds(children[n]) for n in names}
    ledger=[];mx=0;bad=[]
    for a,b in combinations(names,2):
        overlap=np.maximum(0,np.minimum(B[a][1],B[b][1])-np.maximum(B[a][0],B[b][0]))
        ways='AABB 分离';volume=0.
        if all(overlap>1e-9):
            ways='实体求交';volume=inter(children[a],children[b])
        mx=max(mx,volume);ledger.append([a,b,ways,volume])
        if volume>.001:bad.append([a,b,volume])
    dst=work/'intersection_step.json';dump(dst,dict(excluded=['phone','camera_dummy'],threshold_mm3=.001,maximum_mm3=mx,fail=bad,pairs=ledger))
    j=json.loads(dst.read_text());return dict(name='装配 STEP 逐对求交回读',ok=not j['fail'] and len(j['pairs'])==math.comb(len(names),2),value=f"{len(j['pairs'])} 对，最大 {mx:.8f} mm³，越限 {bad}")
def profile(p,work):
    # 机顶外轮廓按三角面边与平面的交点求极值，含端面。硬边界另以 B-rep 全区间实体验证。
    edges=[];back_edges=[]
    for n,data in p.items():
        sh=data['sh'];b=bounds(sh)
        if n in ('phone','camera_dummy'):continue
        v,f=sh.tessellate(.025,.12);tri=np.array([tuple(x) for x in v])[np.asarray(f)]
        ee=[(tri[:,i],tri[:,(i+1)%3]) for i in range(3)]
        if b[0,1]<0:edges.extend(ee)
        if b[1,1]>=0 and n not in ('side_rail','trunk'):back_edges.extend(ee)
    a=np.concatenate([t for t,w in back_edges]);b=np.concatenate([w for t,w in back_edges]);dy=b[:,1]-a[:,1];back=[]
    for y in sorted(set(range(150))|{62.799,62.8,129.4,129.401,149.65}):
        h=((a[:,1]-y)*(b[:,1]-y)<=1e-9)&(np.abs(dy)>1e-9)
        vv=np.r_[a[h]+(b[h]-a[h])*((y-a[h,1])/dy[h])[:,None],a[np.abs(a[:,1]-y)<1e-7]]
        if len(vv):back.append([y,round(float(vv[:,2].max()),4)])
    dump(work/'back_profile_1mm.json',back)
    u=np.concatenate([a for a,b in edges]);v=np.concatenate([b for a,b in edges]);dy=v[:,1]-u[:,1]
    result=[]
    for g in range(58):
        y=-g;hit=((u[:,1]-y)*(v[:,1]-y)<=1e-9)&(np.abs(dy)>1e-9);t=(y-u[hit,1])/dy[hit]
        zz=np.r_[u[hit,2]+t*(v[hit,2]-u[hit,2]),u[np.abs(u[:,1]-y)<1e-7,2]]
        if len(zz):result.append([g,round(max(0,float(max(zz))),4),round(max(0,-8.25-float(min(zz))),4)])
    assert len(result)==58
    dump(work/'profile_1mm.json',result);return result
def common(items):
    states=[];hs=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    for work,m,j in items:
        orig=import_step(work/'assembly.step');children={x.label:x for x in orig.children}
        keys=sorted(r['id'] for r in m['parts'] if r['group']=='灯头');dest=work/'head_step';dest.mkdir(exist_ok=True)
        states.append((keys,children,dest))
    (keys,c,left),(ks,a,right)=states;assert keys==ks
    proof={}
    for k in keys:
        # 同一标准件只发一份母文件；对两个独立装配取出的实体与母件求差，再比较两份实际交付字节。
        f=left/(k+'.step');g=right/f.name
        own_c=left.parent/f.name;own_a=right.parent/f.name
        if own_c.exists():
            assert own_a.is_file()
            shutil.copy2(own_c,f)
        else:
            # 装配子节点有 XCAF 父引用，不能直接作为独立 XCAF 文档的自由主件。
            # 交付部件只取该节点的已定位 B-rep，不带父节点树；装配 STEP 仍保留名称/材料。
            from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
            from OCP.IFSelect import IFSelect_RetDone
            writer=STEPControl_Writer()
            assert writer.Transfer(c[k].wrapped,STEPControl_AsIs)==IFSelect_RetDone,k
            assert writer.Write(str(f))==IFSelect_RetDone,(k,f)

        shutil.copy2(f,g);q=import_step(g)
        bs=[bounds(s) for s in (c[k],a[k],q)];vs=[vol(s) for s in (c[k],a[k],q)]
        assert np.allclose(bs,bs[0],rtol=0,atol=2e-6) and max(vs)-min(vs)<1e-5,(k,bs,vs)
        mismatch=abs(vs[0]+vs[1]-2*inter(c[k],a[k]))
        assert mismatch<.0001 and hs(f)==hs(g),(k,mismatch)
        if own_c.exists():
            # 也统一实际打印件目录，避免 STEP HEADER 的两个生成时间导致文件 SHA 不同。
            shutil.copy2(g,own_a);assert hs(own_c)==hs(own_a)==hs(f)
        proof[k]=dict(C_volume=vs[0],A_volume=vs[1],C_bbox=bs[0].tolist(),A_bbox=bs[1].tolist(),C_sha256=hs(f),A_sha256=hs(g),boolean_difference_mm3=mismatch)
    contracts=[]
    for work,m,j in items:
        jf=next((work/'pcb').glob('pcb_interface*.json'));d=json.loads(jf.read_text())
        text=jf.read_text();dig={}
        for k in ('driver','led'):
            start=text.index('{',text.index('"'+k+'": {',text.index('"boards": {')))
            decoded,n=json.JSONDecoder().raw_decode(text[start:]);assert decoded==d['boards'][k]
            dig[k]=hashlib.sha256(text[start:start+n].encode()).hexdigest()
        contracts.append(dig)
    assert contracts[0]==contracts[1]
    dump(items[0][0].parent/'common_head.json',dict(parts=proof,interfaces=contracts))
    for work,m,j in items:
        f=work/'report.md';body=f.read_text().split('\n## 共用灯头逐件证据')[0]
        note=['','## 共用灯头逐件证据','以两个独立装配 STEP 的同名节点对比体积、包围盒，并以布尔对称差核对同形。相同标准件只发一个 STEP 母文件，两套零件包分别复制，再核二者完整文件 SHA-256；不是声称两次 STEP 导出时间戳一致。','|件名|C/A 体积 mm³|布尔差 mm³|双份交付文件 SHA-256|','|---|---:|---:|---|']
        for k,d in proof.items():note.append(f"|{k}|{d['C_volume']:.5f} / {d['A_volume']:.5f}|{d['boolean_difference_mm3']:.8f}|{d['C_sha256']}|")
        note.extend(['','灯板和驱动板子对象按交付 JSON 的原文字节比对，SHA-256 分别为 '+contracts[0]['led']+'、'+contracts[0]['driver']+'。','每对实际包围盒及原始零件 SHA 见 round11/final/common_head.json；各版逐对相交记录在该变体的 intersection_step.json。'])
        f.write_text(body+'\n'.join(note)+'\n')

    from v05_report import website
    import subprocess,os
    test=items[0][0].parent/'site-preflight';(test/'models').mkdir(parents=True,exist_ok=True)
    shutil.copytree(R/'web/vendor',test/'vendor',dirs_exist_ok=True)
    shutil.copy2(R/'web/style.css',test/'style.css');shutil.copy2(R/'web/models/comparison05.svg',test/'models/comparison05.svg')
    for work,m,j in items:
        suf='_battery' if j['variant']=='A' else ''
        for name in ['parts'+suf+'.json','filllight'+suf+'.glb']:shutil.copy2(work/name,test/'models'/name)
        website(m,j,test)
        subprocess.run(['node','--input-type=module','--check'],input=(test/('app'+suf+'.js')).read_bytes(),check=True)
        subprocess.run(['node','--disable-warning=MODULE_TYPELESS_PACKAGE_JSON',str(R/'mech/check_glb.mjs')]+(['--battery'] if suf else []),env={**os.environ,'FILL_WEB_ROOT':str(test)},check=True)
