"""缓存只用于重建同一版工程图，源参数/绘图器/任何字节变化均重新生成。"""
from pathlib import Path
import json,hashlib
from v05_route import path
def digest(data):return hashlib.sha256(data).hexdigest()
def record(d,j):
    source=Path(__file__).parent
    return dict(boards=digest(json.dumps(j['boards'],ensure_ascii=False).encode()),path=path(),
                source={n:digest((source/n).read_bytes()) for n in ('pcb_draw.py','v05_pcb.py','v05_route.py')},
                files={f.name:digest(f.read_bytes()) for f in sorted((d/'pcb').glob('*')) if f.suffix in ('.dxf','.png')})
def valid(d,j):
    f=d/'ecad-cache.json'
    return f.is_file() and json.dumps(json.loads(f.read_text()),sort_keys=True)==json.dumps(record(d,j),sort_keys=True)
