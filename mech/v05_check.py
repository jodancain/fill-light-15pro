"""分区而非整机长方体判定；报告实测的剖面最大值和所有超限项。"""
from itertools import combinations
from export import bounds,inter,vol,box,np
from v05_layout import *
from v05_model import path
def checks(j,p,bb):
    C=[];curve=[];hc=[]
    def ck(k,ok,s):C.append({'name':k,'ok':bool(ok),'value':str(s)})
    def both(i,g):return inter(p[i]['sh'],g)
    ids=set(p)-{'phone','camera_dummy'}
    def hit(q,items):
        b=bounds(q);return sum(both(i,q) for i in items if np.all(np.minimum(bb[i][1],b[1])-np.maximum(bb[i][0],b[0])>.000001))
    vent=sum(hit(box(-40,-.01,y+.001,y+3.299,-8.999,4.999),{'sink'}) for y in (-51,-46,-41,-36,-31,-26));ck('六个进风口铝翼贯通',vent<1e-6,f'外侧进风净截面金属侵入 {vent:.8f} mm³')
    win=hit(box(0,46,0,47.5,0,35),ids);ck('开窗包络',win<1e-6,f'附件实心交集 {win:.7f} mm³')
    upper=box(40,68,4,41,0,35);u=hit(upper,ids-{'frame','liner'})
    vals=[both(k,upper) for k in ('frame','liner')]
    ck('禁入区均匀绝缘叠层',u<1e-7 and np.allclose(vals,[22*37*1.8,22*37*1.2]),f'窗外 1.8＋1.2 mm；额外材料 {u:.7f} mm³')
    rail_top=hit(box(8,62.6,-3.05,0,3,30),ids)
    ck('顶轨高度',rail_top<1e-7,f'基座 Z>3 体积 {rail_top:.8f}')
    metal={i for i in ids if p[i]['material'] not in ('PC-FR','TPU','ASA','隔热片','绝缘导热垫','乳白聚碳酸酯')}
    above=hit(box(0,70.6,0,46,-22,42),metal);below=sum(hit(g,metal) for g in (box(-8,5,113,151,-22,42),box(65.4,80,113,151,-22,42),box(-8,80,126,151,-22,42)))
    ck('背面上下导电禁带（含线束和铝塑膜）',max(above,below)<1e-6,f'上/下违规体积 {above:.6f}/{below:.6f} mm³')
    key=sum(hit(g,ids) for g in [box(70.6,80,25,66,-8.25,0),box(-6,0,46,66,-8.25,0)])
    ck('双侧按键',key<1e-6,f'侧面 Z−8.25…0 占用 {key:.6f} mm³')
    ck('侧轨主干在手机轮廓外',bb['side_rail'][0,0]>70.6 and hit(box(0,70.6,0,46,-22,35),{'trunk'})<1e-6,'右轨全长 X%.2f…%.2f；跨越 Y0…46 的导体不投影在手机上'%tuple(bb['side_rail'][:,0]))
    sample=p['trunk']['sh'].intersect(box(65,85,-2,50,-20,20)); sections=[s.bounding_box() for s in sample if s.solids()];inner=min(s.min.X for s in sections);top=max(s.max.Z for s in sections)
    ck('禁入区3及顶角铜体',inner>=73.6 and top<=3.7,f'Y −2…50 实体截片 Xmin={inner:.3f}，Zmax={top:.3f}；以 X72.5 全表最低 4.7 保守校验，余 {4.7-top:.3f} mm；离右侧外表面 {inner-70.6:.3f} mm')
    def section(y,Y,x,X,low=-25,high=36):
        g=box(x,X,y,Y,low,high);cache={}
        active=[i for i in ids if bb[i][1,1]>y and bb[i][0,1]<Y and bb[i][1,0]>x and bb[i][0,0]<X]
        def measure(i):
            if i not in cache:
                b=bb[i]
                if b[0,1]>=y and b[1,1]<=Y and b[0,0]>=x and b[1,0]<=X:cache[i]=(b[0,2],b[1,2])
                else:
                    vv=[s.bounding_box() for s in (p[i]['sh'].intersect(g) or []) if s.solids()]
                    cache[i]=(min(r.min.Z for r in vv),max(r.max.Z for r in vv)) if vv else None
            return cache[i]
        result=[]
        for k,sign in ((0,-1),(1,1)):
            best=-math.inf
            for i in sorted(active,key=lambda i:sign*bb[i][k,2],reverse=True):
                if sign*bb[i][k,2]<=best+1e-8:break
                m=measure(i)
                if m is not None:best=max(best,sign*m[k])
            result.append(best*sign if math.isfinite(best) else 0.)
        return result
    for n,y in enumerate(Y):
        end=Y[n+1] if n+1<len(Y) else 150;lo,hi=section(y,end,0,70.6);curve.append([y,end,round(hi,3),Z[n]-1.5])
    ck('背模块连续限高',all(k[2]<=k[3]+.0001 for k in curve),'各区全宽最大实形，不在表内插值；详见清单二。')
    for n,g in enumerate(G[:-1]):
        gn=G[n+1];lo,hi=section(-gn,-g,min(b[0,0] for b in bb.values())-1,max(b[1,0] for b in bb.values())+1);rear=max(0,hi);front=max(0,-8.25-lo);hc.append([g,gn,round(rear,3),round(front,3),REAR[n]-1,FRONT[n]-1,SOFT[n]])
    ck('灯头＋颈肩全宽 G 表硬边界',all(r<=rr+.0001 and f<=ff+.0001 for _,__,r,f,rr,ff,_ in hc),str([i for i in hc if i[2]>i[4]+.0001 or i[3]>i[5]+.0001])+'；见逐段表（全宽含外侧线槽）。')
    near=hit(box(-5,70.6,-8,0,-20,35),metal)
    ck('机顶导电件离顶边',near<1e-6,'头内金属不进入 G<8；仅右轨绝缘导线必须在手机轮廓外跨过顶边，天线性能留实测。')
    # 全装配逐对布尔移至整机 STEP 读回后执行（v10_proof.audit_step）。
    for i in ('input_usb_c','output_usb_c'):
        x=float(bb[i][:,0].mean());v=hit(box(x-4.5,x+4.5,125.8,151,5.85,9.35),ids);ck(i+' 开口',v<.001,f'9×3.5 直出量规：{v:.5f} mm³')
    if j['variant']=='A':
        v=hit(box(5.3,65.3,64.8,98.8,4.2,19.8),ids-{'cell_1','cell_2','separator','cell_ntc'})
        ck('2S 软包两芯各膨胀 10%',v<.001,f'刚件/螺钉侵占 {v:.6f} mm³；上方另留 NTC。')
    h=j['harness'];r=h['copper_loop_mohm_at60']+h['contact_pair_budget_mohm'];ck('12芯电阻预算',r<=50 and h['power']['count']==h['signal']['count']==6 and all(val<=(40 if net=='BAT+' else 60) for net,val in h['rail_loop_mohm'].items()),f'60 °C 热铜＋端接 {r:.2f} mΩ；实物四线测量前非实测值')
    return C,curve,hc,sorted(metal)
