"""R6/R7 交付几何的独立回读。比较同格式的体积、包围盒和完整数据，不拿元数据自证。"""
from pathlib import Path
import hashlib,json,re,sys
import numpy as np,trimesh
from build123d import import_step
ROOT=Path(__file__).resolve().parents[1]
R6=ROOT/'mech/out/archive_v04C_r6'
def digest(b):return hashlib.sha256(b).hexdigest()
# OCCT 的着色/线型条目枚举顺序不稳定。仅剔除具名的显示样式类型；
# 所有几何、拓扑、单位、上下文、装配关系、位置变换和未知实体均原样参与摘要。
STYLE=set(b"COLOUR_RGB CURVE_STYLE DRAUGHTING_PRE_DEFINED_CURVE_FONT FILL_AREA_STYLE FILL_AREA_STYLE_COLOUR MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION OVER_RIDING_STYLED_ITEM PRESENTATION_STYLE_ASSIGNMENT PRESENTATION_STYLE_BY_CONTEXT STYLED_ITEM SURFACE_SIDE_STYLE SURFACE_STYLE_FILL_AREA SURFACE_STYLE_USAGE".split())
def shape_data(data):
    pattern=rb"^(#[0-9]+\s*=\s*)([A-Z0-9_]*)(.*?);[ \t]*$"
    count=0;h=hashlib.sha256()
    for record in re.finditer(pattern,data,re.M|re.S):
        count+=1
        if record[2] not in STYLE:h.update(record[0]+b"\n")
    assert count and count==len(re.findall(rb"^#[0-9]+\s*=",data,re.M))
    return h.hexdigest()
def metrics(v,lo,hi):return dict(volume_mm3=float(v),bbox_mm=np.asarray([lo,hi],float).tolist())
def read(path):
    raw=path.read_bytes()
    if path.suffix=='.step':
        # 忽略 HEADER 的导出时刻；DATA 段包含所有 B-rep 与装配变换。
        data=raw.split(b'\nDATA;\n',1)[1]
        root=import_step(path);children=list(root.children) if root.children else [root]
        rows={}
        for c in children:
            key=c.label or path.stem;assert key not in rows
            solids=list(c.solids());q=c.bounding_box()
            rows[key]=metrics(sum(s.volume for s in solids),list(q.min),list(q.max))
            rows[key]['solids']=len(solids)
    elif path.suffix=='.stl':
        data=raw;m=trimesh.load_mesh(path);assert m.is_volume
        rows={path.stem:metrics(m.volume,*m.bounds)}
    else:
        data=raw;sc=trimesh.load_scene(path);rows={}
        for name in sc.graph.nodes_geometry:
            tr,g=sc.graph[name];m=sc.geometry[g].copy()
            m.apply_transform(tr);m.apply_scale(1000.)
            rows[name]=metrics(m.volume,*m.bounds)
    return dict(geometry_sha256=(shape_data(data) if path.suffix=='.step' else digest(data)),full_data_sha256=digest(data),nodes=rows)
def inventory(root):
    return sorted(str(f.relative_to(root)) for directory in ('mech/out','mech/pcb','web/models') for f in (root/directory).iterdir() if f.is_file() and f.suffix in ('.stl','.step','.glb'))
def snapshot(root):return {n:read(root/n) for n in inventory(root)}
def run():
    out=ROOT/'mech/out/round07';out.mkdir(exist_ok=True)
    ledger=out/'r6-geometry.json'
    if sys.argv[1:]==['--baseline']:
        ledger.write_text(json.dumps(snapshot(R6),ensure_ascii=False,indent=2)+'\n');return
    old=json.loads(ledger.read_text()) if ledger.exists() else snapshot(R6);new=snapshot(ROOT)
    assert sorted(old)==inventory(R6)==sorted(new)
    report={};maxvol=maxbox=0
    for n,left in old.items():
        assert (R6/n).is_file()
        a=left['nodes'];b=new[n]['nodes'];assert a.keys()==b.keys(),n
        v=max(abs(m['volume_mm3']-b[k]['volume_mm3']) for k,m in a.items())
        d=max(float(np.abs(np.array(m['bbox_mm'])-b[k]['bbox_mm']).max()) for k,m in a.items())
        same=left['geometry_sha256']==new[n]['geometry_sha256']
        assert same and d<1e-8 and v<1e-7,(n,same,v,d)
        report[n]=dict(full_data_identical=left['full_data_sha256']==new[n]['full_data_sha256'],nodes=len(a),max_abs_delta_volume_mm3=v,max_abs_delta_bbox_mm=d,identical_geometry_data=same,
            R6_sha256=left['geometry_sha256'],R7_sha256=new[n]['geometry_sha256'],R7_measurements=b)
        maxvol=max(v,maxvol);maxbox=max(d,maxbox)
    counts={ext:sum(n.endswith(ext) for n in new) for ext in ('.step','.stl','.glb')}
    header=dict(reference='archive_v04C_r6',units='mm；体积 mm³',step_hash_scope='STEP 保留所有非显示样式实体（含拓扑、单位、装配和位置）；另比对完整 DATA；STL/GLB 为整文件',
        file_counts=counts,assembly_nodes=len(new['mech/out/assembly.step']['nodes']),max_volume_difference_mm3=maxvol,max_bbox_difference_mm=maxbox)
    (out/'geometry.json').write_text(json.dumps(dict(**header,files=report),ensure_ascii=False,indent=2)+'\n');print(header)
if __name__=='__main__':run()
