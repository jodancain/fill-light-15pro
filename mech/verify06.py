"""直接回读交付 STEP；用背面坐标的实心量规，不构造任何取景锥。可从仓库外运行。"""
from pathlib import Path
import json,sys
from build123d import Solid,Plane,import_step
ROOT=Path(__file__).resolve().parents[1]
TOL_MM=1e-6  # 核心几何公差，仅用于边界比较
def gauge(x,X,y,Y,z,Z):
    return Solid.make_box(X-x,Y-y,Z-z,Plane(origin=(x,-Y,z)))
def volume(s):
    return sum(v.volume for v in s.solids())
def overlap(s,g):
    return sum(volume(k) for k in (s.intersect(g) or []))
def bb(s):
    b=s.bounding_box()
    return (b.min.X,b.max.X,-b.max.Y,-b.min.Y,b.min.Z,b.max.Z)
def conductor_limits(conductors):
    """上带只查 Y；下带只量 Y>113 的实形切片。不用整个节点的 X 外框替代切片。"""
    spans=[(name,k,bb(k)) for name,s in conductors.items() for k in s.solids()]
    if not spans:raise ValueError('无导电件可复核')
    top=min(b[2] for _,_,b in spans);top_bad={n for n,_,b in spans if b[2]<46-TOL_MM}
    tail=[]
    for name,s,b in spans:
        x,X,y,Y,z,Z=b
        if Y<=113+TOL_MM:continue
        if y>=113:tail.append((name,b));continue
        slab=gauge(x-1,X+1,113,Y+1,z-1,Z+1)
        for cut in s.intersect(slab) or []:
            tail.extend((name,bb(k)) for k in cut.solids())
    bad={n for n,b in tail if b[0]<5-TOL_MM or b[1]>65.4+TOL_MM or b[3]>126+TOL_MM}
    extent=(min(b[0] for _,b in tail),max(b[1] for _,b in tail),max(b[3] for _,b in tail)) if tail else None
    return top,sorted(top_bad),extent,sorted(bad)

def audit(path,materials,prior=None):
    obj={s.label:s for s in import_step(path).children}; out=[]
    def ck(name,ok,value):out.append(dict(name=name,ok=bool(ok),value=value))
    def summ(ids,g):return sum(overlap(obj[i],g) for i in ids)
    accessory=set(obj)-{'camera_dummy','phone'}
    win=gauge(0,46,0,47.5,0,max(bb(obj[i])[5] for i in accessory)+1)
    v=summ(accessory,win);ck('开窗包络 x ≤ 46.0、y ≤ 47.5 内 z > 0 无材料',abs(v)<1e-8,f'整机 STEP；{len(accessory)} 个背夹节点的实心交集之和 {v:.9f} mm³。仅排除手机和被避让的示意平台。右下 R0，左、上开至机缘。')
    cam=bb(obj['camera_dummy']);actual=(2.5,44.5,2.5,46.,0.,4.)
    ck('示意平台占位（不作定位基准）',max(abs(a-b) for a,b in zip(cam,actual))<1e-5,f'X {cam[0]:.2f}…{cam[1]:.2f}，Y {cam[2]:.2f}…{cam[3]:.2f}，最高 Z {cam[5]:.2f}。不以岛形状代替窗口检查。')
    heads=sorted([bb(k) for k in obj['screws'].solids() if bb(k)[4]>22.9],key=lambda b:b[3])
    lower=heads[-2:]; centers=sorted((b[0]+b[1])/2 for b in lower);y=max(b[3] for b in lower)
    ck('下部螺钉头外缘 y ≤ 111，或已改非金属',len(heads)==4 and abs(centers[0]-2.8)<1e-6 and abs(centers[1]-67.8)<1e-6 and (y<=111+1e-6 or materials['screws'] in ('PEEK','尼龙')),f'按四个头部实体的最远 Y 排序，取下部两颗。中心 X={centers[0]:.2f}/{centers[1]:.2f}；中心 Y={(lower[0][2]+lower[0][3])/2:.2f}；头外缘 {y:.2f} mm。材料：{materials["screws"]}。')
    # 固定的禁入区包络：强制开窗内允许为空，窗外只允许两层满厚的平板。
    upper=gauge(40,68,4,41,0,34);err=0
    for i,z,Z in [('liner',0,1.2),('frame',1.2,3)]:
        ideal=gauge(46,68,4,41,z,Z)
        err+=abs(overlap(obj[i],upper)+volume(ideal)-2*overlap(obj[i],ideal))
    err+=summ(accessory-{'frame','liner'},upper)
    ck('禁入区 1–3 上背叠层',err<1e-5 and materials['liner']=='TPU' and materials['frame']=='PC-FR',f'在 X40…68/Y4…41 内，强制开窗以外仅 1.2 TPU＋1.8 非导电 PC-FR；与无筋、无槽理想叠层的差异 {err:.8f} mm³。禁用导电填料/涂层。')
    zhigh=summ(accessory,gauge(-3.1,73.7,-3.1,47.5,3,35))
    key=summ(accessory,gauge(-4,.1,46,66,-8.25,0))
    ck('上背/外轨限高与左侧电源键',zhigh<1e-7 and key<1e-7,f'上背区 Z>3 体积 {zhigh:.8f}；左侧键段 X−4…0.1/Y46…66/Z−8.25…0 的背夹材料 {key:.8f} mm³。')
    f=obj['frame'];core=gauge(10,60,-2.9,-.1,1.21,2.99);coreloss=volume(core)-overlap(f,core)
    area=overlap(f,gauge(30,31,-3.05,0,0,3));nc=[len(obj[i].solids()) for i in ('frame','liner')]
    ck('顶轨连续截面与承力连接',max(nc)==1 and abs(coreloss)<1e-6 and area>6.,f'底壳/内衬各 {nc[0]}/{nc[1]} 个连通实形；负 Y 顶轨中段净截面 {area:.2f} mm²，50 mm 连续芯材缺失 {coreloss:.7f} mm³。夹持力、层间疲劳须实配。')
    sd=gauge(-5,76,-5,152,-11,0)
    if prior and prior.is_file():
        old={s.label:s for s in import_step(prior).children}
        delta=0.
        for i in ('frame','liner'):
            for a in (old[i].intersect(sd) or []):
                delta+=abs(volume(a)-overlap(obj[i],a))
            for a in (obj[i].intersect(sd) or []):
                delta+=abs(volume(a)-overlap(old[i],a))
        ck('四角扣侧壁和正面唇边未延长',delta<1e-5,f'Z<0 底壳＋内衬相对 R5 实体双向体积差 {delta:.8f} mm³。四角夹持仍须打样。')
    led=bb(obj['led_board']);main=bb(obj['main_board']);drive=bb(obj['driver_board']);d=bb(obj['diffuser'])
    ck('灯板上沿、窗口及主驱板冻结边界',max(abs(a-b) for a,b in zip((led[2],led[4],led[5],main[0],main[1],main[3],drive[0],drive[1],d[5]),(66,19.4,21,5.3,65.3,125.8,5.3,65.3,24)))<1e-5,
        f'灯板上沿 Y {led[2]:.2f} / Z {led[4]:.2f}…{led[5]:.2f}；齐平窗 Z {d[5]:.2f}。两电源/驱动板 X 5.30…65.30，主板下沿 Y {main[3]:.2f}。头方本地复核：灯板距禁入区 3 约 0.7 mm；灯窗前沿最紧处（激光雷达）约 1.9 mm 竖向余量，至超广角约 3.2 mm。')
    nonmetal={'TPU','PC-FR','隔热片','绝缘导热垫','乳白聚碳酸酯','PEEK','尼龙'}
    ids={i:obj[i] for i in accessory if materials[i] not in nonmetal}
    top,top_bad,tail,bottom_bad=conductor_limits(ids)
    ck('顶部包络：Y<46 无导电件',not top_bad,f'逐实体回读，{len(ids)} 个导电节点，最靠顶 Y={top:.3f} mm。违规：{top_bad or "无"}。')
    m=('无导电实体进入该区' if tail is None else '下段实形 X=%.3f…%.3f，最远 Y=%.3f mm'%tail)
    ck('底部包络：Y>113 的导电件仅在 X5.0…65.4、Y≤126.0',not bottom_bad,m+f'。违规：{bottom_bad or "无"}。外接两插头量规单列；无线充电线圈占用为已接受偏差，不作否决。')
    return out
if __name__=='__main__':
    out=ROOT/'mech/out';p=json.loads((ROOT/'web/models/parts.json').read_text())
    r=audit(out/'assembly.step',{x['id']:x['material'] for x in p['parts']},out/'archive_v04C_r5/mech/out/assembly.step')
    for a in r:print(('通过' if a['ok'] else '不通过'),a['name'],a['value'])
    sys.exit(0 if all(x['ok'] for x in r) else 3)
