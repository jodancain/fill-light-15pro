"""C 是不可变发布包；未缺失的文件始终只读，不以再导出的时间戳替换。"""
from pathlib import Path
import hashlib,json,sys,shutil
R=Path(__file__).resolve().parents[1]; O=R/'mech/out'; A=O/'archive_v04C_r7'
def check(deep=False):
    man=json.loads((R/'mech/c_r7_frozen.json').read_text()); h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for n,v in man.items():
        p=R/n
        if not p.exists() and (A/n).exists() and h(A/n)==v:p.parent.mkdir(exist_ok=True,parents=True);shutil.copyfile(A/n,p)
        if not p.exists() and n.startswith('mech/out/'):
            from zipfile import ZipFile
            if n=='mech/out/assembly.step':raw=(R/'mech/pcb/enclosure_assembly.step').read_bytes()
            else:
                with ZipFile(R/'mech/baselines/c_r7_print_release.zip') as z:raw=z.read(n)
            if hashlib.sha256(raw).hexdigest()!=v:raise RuntimeError('发布归档不符：'+n)
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        if not p.exists() or h(p)!=v:raise RuntimeError('C-r7 发布件缺失或摘要不符，不覆盖：'+n)
    print(f'C-r7：{len(man)} 项逐文件 SHA-256 相等。',flush=True)
    import re
    index=(R/'web/index.html').read_bytes()
    base=re.sub(rb'  <!-- '+ '变体导航'.encode()+rb' -->[^\n]*?<!-- /'+ '变体导航'.encode()+rb' -->\n',b'',index)
    if hashlib.sha256(base).hexdigest()!='f28e1c9d825add1b8b14770ee2a367af48ffa223cd44a33c58b04ff529a651e7':raise RuntimeError('C 页面除导航之外有变化')
    if deep:
        from geometry07 import read
        import numpy as np
        data=json.loads((R/'mech/baselines/c_r7_geometry.json').read_text()); rows={}
        for n,v in data.items():
            m=read(R/n);q=m['nodes'];b=v['nodes'];assert q.keys()==b.keys()
            dv=max(abs(s['volume_mm3']-b[k]['volume_mm3']) for k,s in q.items())
            db=max(float(np.max(np.abs(np.asarray(s['bbox_mm'])-b[k]['bbox_mm']))) for k,s in q.items())
            assert dv<1e-7 and db<1e-8 and m['geometry_sha256']==v['geometry_sha256'],n
            rows[n]=dict(sha256=man[n],nodes=len(q),delta_mm3=dv,delta_mm=db)
        dest=O/'round08';dest.mkdir(exist_ok=True);(dest/'c_readback.json').write_text(json.dumps(rows,indent=2)+'\n')
        print('C 逐节点体积与包围盒回读：',len(rows),'文件，最大差',max(x['delta_mm3'] for x in rows.values()),max(x['delta_mm'] for x in rows.values()))
if __name__=='__main__':check('--deep' in sys.argv)
