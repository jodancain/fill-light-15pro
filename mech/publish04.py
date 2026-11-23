"""成功构建后只撤下已归档且字节相同的旧输出，生成当前制造清单。"""
from pathlib import Path
from hashlib import sha256
from silhouette import comparison
def finish(root,prints):
    out=root/'mech/out';archive=out/'archive_v03/mech/out';current={i+e for i in prints for e in ('.step','.stl')}|{'assembly.step','cable_gauges.step'}
    if archive.exists():
        for path in [*out.glob('*.step'),*out.glob('*.stl')]:
            if path.name not in current and (archive/path.name).is_file() and path.read_bytes()==(archive/path.name).read_bytes():path.unlink()
        for path in (out/'coupons').glob('*'):
            if path.is_file() and (archive/'coupons'/path.name).is_file() and path.read_bytes()==(archive/'coupons'/path.name).read_bytes():path.unlink()
        if (out/'coupons').is_dir() and not list((out/'coupons').iterdir()):(out/'coupons').rmdir()
    if archive.exists() or not (root/'web/models/comparison.png').is_file():comparison()
    files=sorted([out/'report.md',*(out/s for s in current),*(root/'mech/pcb').glob('*'),*(root/'web/models').glob('*')])
    (out/'files.md').write_text('# v0.4 交接清单\n\n| 文件 | 字节 | SHA-256 |\n|---|---:|---|\n'+'\n'.join(f'| `{p.relative_to(root)}` | {p.stat().st_size} | {sha256(p.read_bytes()).hexdigest()} |' for p in files if p.is_file())+'\n')
