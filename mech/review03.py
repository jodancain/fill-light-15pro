"""按公开接口与本轮分带值验算。仓背基准使用旧滑盖实面与露出电芯的圆弧，不用包围盒顶替。"""
import math,numpy as np
from ridge import *
def review(ck,L,P,f,bb,B,sh,inter):
    q=ridge_path(L,P);edge=np.array([(y-CAP_OUT*sin(t),z+CAP_OUT*cos(t)) for y,z,t in q]);a,b=L['pod']['cell_axis_y']; y,Y=L['pod']['y'];cz=f['zc'];r=P.cell_d/2
    # 开窗内的基准是电芯圆弧，窗外采用滑盖顶；取弧与线段差值的端点和全部驻点。
    maxd=0.;worst=0.; lid=f['lid_lo']+P.lid_t
    for (u,h),(v,k) in zip(edge,edge[1:]):
        if v<=y or u>=Y or v<=u:continue
        lo=max(u,y);hi=min(v,Y);s=(k-h)/(v-u); cuts=sorted(set([lo,hi]+[w for c in (a,b) for w in (c-P.cell_slot/2,c+P.cell_slot/2) if lo<w<hi]));
        for l,m in zip(cuts,cuts[1:]):
            c=min((a,b),key=lambda c:abs((l+m)/2-c));arc=abs((l+m)/2-c)<P.cell_slot/2
            for t in [l,m]:
                ref=cz+sqrt(r*r-(t-c)**2) if arc else lid
                delta=h+(t-u)*s-ref
                if delta>maxd:maxd,worst=delta,t
    for lo,hi,allowed in BANDS:
        rise=maxd if hi>bb['ridge_cover'][0,0] and lo<58.0 else 0
        ck(f'电池仓与线束脊的取景约束 x {lo}–{hi}',rise<=min(allowed,7),f'实际最大 +{rise:.3f} / 允许 +{allowed:.1f} mm；'+(f'最差 y={worst:.3f}；所有交叠分带同时执行' if rise else '本带未增高'))
    for pos,cap in [(50,9.3),(56,16.4)]:
        from model import box
        vals=[9.]; slab=box(45,70,pos-.0005,pos+.0005,3,38)
        for node in ['ridge_cover','harness_bundle']:
            for hit in sh(node).intersect(slab) or []:vals.append(hit.bounding_box().max.Z)
        z=max(vals);ck(f'颈末过渡 y={pos}',z<=cap,f'脊盖轮廓 Z={z:.3f}，接口文档矮区 {cap:.1f} mm；未将仓体分带外推到颈部。')
    ck('线束内弯半径',min(5-HALF,5.3-HALF,23**2/(6*(X-50.8))-WIDTH/2)>=3.8,f'灯头 R3.80、脊盖过渡 R4.10、平面偏移保守下界 R{23**2/(6*(X-50.8))-WIDTH/2:.2f} mm；按连续设计线，不按离散网格棱角')
    from model import box as slab,cyl
    d=B['driver']; w,h=d['size'];work=slab(0,w,0,h,0,1)
    for it in d['connectors']+d['keepouts']+[v for v in d['height_zones'] if v['id'] in ('FAN_BUCK','J1_BAY')]:
        if it.get('side','TOP')=='TOP':
            a,c,b,e=it['rect'];work=work.cut(slab(a,b,c,e,-1,2))
    for h in d['holes']:work=work.cut(cyl(*h['center'],-1,h['keep_d'],3))
    area=sum(s.volume for s in work.solids())
    n=sum(v['w']*v['h']*v['count'] for v in d['budget']); zone=(22.4-6.6)*16
    ck('双路器件面积（不是布通验收）',2*n<=area,f'每路最大裸体投影 {n:.2f} mm²；旧区 201.50，新区 {zone:.2f}，每路至少 {max(0,n-zone):.2f} mm² 低件需区外。全板扣紧固、接口/插合和风扇降压预留后 {area:.2f} mm²；两路裸体后剩 {area-2*n:.2f} mm²，不含焊盘、走线、散热铜与间距。')
    placed=len(d.get('rough_placement',[]))+2; count=2*sum(v['count'] for v in d['budget']);ck('双路最大器件实体试排',placed==count,f'含两颗固定电感，0.5 mm 格点、多次旋转试排：{placed}/{count} 件。使用最大包络，每个待摆器件各边加 0.25 mm；未排全不等于数学无解。电气侧须以正式封装复排，再决定小封装或扩板。')
    small=len(d['compact_candidate']['other_parts'])+2;ck('双路紧凑候选器件试排',small==count,f'采用两只 7×7 电感、两只 3×2.5 调光 PMOS：{small}/{count} 件，坐标见接口 JSON compact_candidate；仅外形试排，不改变 10×10 最大限高量规，不证明电流、散热、引脚或地回流可用。')
