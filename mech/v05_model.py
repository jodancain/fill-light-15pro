"""共享灯头、右侧开放线槽和 C/A 背夹；坐标内部一直取背视。"""
import math,copy
from build123d import Solid,Wire,Pos,Color,Compound
import model as m
from model import box,rr,cyl,pack,add,MAT
from v05_layout import *
BASE=None
def base():
    global BASE
    if BASE is None:
        from build123d import import_step
        from export import native_shape
        arc=R/'mech/out/archive_v04_final';file=arc/'mech/out/assembly.step'
        if file.is_file():
            obj={q.label:q for q in import_step(file).children};BASE={}
            for r in json.loads((arc/'web/models/parts.json').read_text())['parts']:
                r=dict(r);r['sh']=native_shape(obj[r['id']]);r['override']=r['mass'] if r['basis'] in ('单件预算','不计入') else None;BASE[r['id']]=r
        else:m.make();BASE=dict(m.parts)
        print('共用基线就绪',flush=True)
    m.parts.clear()
def plus(s,*others):
    for o in others:s=s.fuse(o)
    return s
from v05_route import path
def strip(pts,n,N,z,Z):
    wires=[]
    for x,y,h,dx,dy in pts:
        wires.append(Wire.make_polygon([(x-dy*w,y+dx*w,h+t) for w,t in [(n,z),(N,z),(N,Z),(n,Z)]],close=True))
    return Solid.make_loft(wires,ruled=True)
def make(v,j):
    base();p=m.parts
    def reuse(i,delta=(0,0,0),group=None,shape=None):
        d=dict(BASE[i]);s=Pos(*delta)*(d['sh'] if shape is None else shape);d['sh']=s
        if group:d['group']=group
        s.color=Color(d['color']);s.label=i;p[i]=d
    def put(i,n,g,mat,s,orient=None,mass=None,note=''):
        add(i,n,g,mat,s,(0,0,20 if g!='灯头' else 30),orient,mass,note)
    def printed(i,n,g,s,mat='PC-FR'):put(i,n,g,mat,s,'平整承力面朝平台；孔与风槽局部支撑。')
    for i in ['phone','camera_dummy','liner']:reuse(i)
    chassis=BASE['frame']['sh'].cut(box(-6,78,-6,152,3,40))
    # 在 y<0 的外部顶轨上接宽肩，矩形插肩进入灯头；两只铜母不在手机上方 8 mm 带内。
    tongue=rr(10,60,-16.85,-.65,.65,2.95,1.2).cut(BASE['liner']['sh'])
    for x in (14,56):tongue=tongue.cut(cyl(x,-15.35,.5,2.4,2.7))
    chassis=chassis.fuse(tongue)
    a=v=='A';H=21.7 if a else 15.;y0=62.8
    # 直接由底壳承托主板；两侧绝缘支脚/压脚避开板内器件。
    for x in (6.4,63.9):
        for y in (106,122):chassis=chassis.fuse(box(x-.8,x+.8,y-.8,y+.8,3,4.7))
    if a:
        # 旧盖燕尾浅槽被 A 托盘封住后成为浮空内腔（1.8×2.2×0.58）。
        # 填回已废弃的槽底，合并内壳，不删 STL 内部三角面冒充过检。
        chassis=chassis.fuse(box(2.84,4.66,70.44,72.66,2.40,3.06))
        chassis=chassis.fuse(rr(3.5,67.1,63.2,100.5,3,4.2,1.2))
        for x in (3.55,65.85):chassis=chassis.fuse(box(x,x+1.2,64.6,99.4,4.15,9.2))
        for y in (63.25,99.15):chassis=chassis.fuse(box(4.7,65.9,y,y+1.2,4.15,10.4))
    hold=[(2.75,72),(67.85,72),(2.75,108.8),(67.85,108.8)]
    shell=rr(.2,70.4,y0,129.4,3,H,3.5).cut(rr(1.65,68.95,y0+1.45,128,2.95,H-1.4,2.1))
    for x,y in hold:
        chassis=chassis.fuse(cyl(x,y,3,4.8,H-4.45)).cut(cyl(x,y,H-5.9,1.75,5))
        shell=shell.cut(cyl(x,y,2.9,5.05,H-4.3),cyl(x,y,H-1.45,2.25,1.5),cyl(x,y,H-.75,3.9,1))
    put('cover_screws','四颗背夹 M2 非磁紧固件','壳架','非磁316不锈钢',pack(*[cyl(x,y,H-4.7,1.65,3.95).fuse(cyl(x,y,H-.75,3.6,.7)) for x,y in hold]),mass=.65)
    # 头部全部用同一装配构造。旧热舌从散热器末端截掉。
    dt=(0,-119,-12.4);dd=(0,-150.3,-19.)
    for i in BASE:
        if i in ('led_W','led_C','thermal_trip','diffuser'):reuse(i,dt,'灯头')
    for board in ('led','driver'):
        b=j['boards'][board];name=board+'_board';reuse(name,group='灯头',shape=m.board_shape(b))
        for it in b['connectors']+b['fixed']:
            x,X,y,Y=m.absrect(b,it['rect']);z=b['origin'][2]+b['thickness']
            shape=box(x,X,y,Y,z,z+it['height'])
            if it['node']=='head_power_device':put(it['node'],it['name'],'灯头','接口',shape)
            else:reuse(it['node'],group='灯头',shape=shape)
    reuse('blower',(-6,-121,-12.4),'灯头')
    # 一体铲齿铝：连续基板直接贴 TIM；不继承旧攻丝柱与鳍节距。
    sink=rr(4.3,66.3,-53,-19,5.8,6.6,2)
    for i in range(26):
        y=-51+1.20*i;sink=sink.fuse(box(39.5,63.5,y,y+.4,-5.2,5.85))
    sink=sink.fuse(box(41.3,56.3,-47,-37,-6.8,-5.18))
    # 实铣温控开关座及板端接头避让；开关顶面贴基板。
    sink=sink.cut(box(51.8,61.2,-28.2,-22.8,2.7,5.8),p['blower']['sh'])
    for it in j['boards']['driver']['connectors']+j['boards']['driver']['fixed']:
        sink=sink.cut(p[it['node']]['sh'])
    # 机顶左侧自然对流翼：单独直立疏齿，气流不必穿过停转蜗壳。根部以整条铝桥接灯板基板。
    sink=sink.fuse(box(-3,6,-52,-20,5.8,6.6),box(-3,-.5,-54,-18,-16,8))
    for y in (-54,-51.95,-46.95,-41.95,-36.95,-31.95,-26.95,-21.95,-19):
        sink=sink.fuse(rr(-39,-2.8,y,y+.9,-16,8,.44))
    for y in (-51,-46,-41,-36,-31,-26):sink=sink.cut(box(-40,.1,y,y+3.3,-9,5))
    reuse('sink',group='灯头',shape=sink)
    put('head_power_tim','功率封装顶面绝缘导热垫','灯头','绝缘导热垫',box(41.3,56.3,-47,-37,-7.4,-6.8))
    put('led_tim','灯板整面软垫 0.50→0.40','灯头','绝缘导热垫',rr(4.3,66.3,-53,-19,6.6,7,2))
    tub=rr(0,70.6,-57,-13,-16.8,9.9,2.6).cut(rr(1.55,69.05,-55.45,-14.55,-15.3,10,1.45))
    for h in j['boards']['driver']['holes']:
        x,y,_=pos(j['boards']['driver'],h['center']);tub=tub.fuse(cyl(x,y,-15.35,4.0,.85)).cut(cyl(x,y,-16.9,1.65,2.5))
    # 正温侧壁直接承托铝基板；在无风口的两端以托肩承托鳍片基座。
    for x in (1.3,65.4):
        for y in (-52.4,-22):tub=tub.fuse(box(x,x+3.9,y,y+1.5,5,5.8))
    # 风机的安装座绕过驱动板：左壁悬臂沿 Y 两点承重。
    for y in (-53.2,-20):tub=tub.fuse(box(1.35,12,y,y+2,-6.6,-4.9))
    # 结构凸台和紧固件只在 G>=14，中心舌肩与端面传力。
    for x in (14,56):tub=tub.fuse(box(x-3.3,x+3.3,-16.95,-14.4,-4.0,6.3))
    tub=tub.cut(box(9.75,60.25,-17.0,-12.8,.52,3.06))
    for x in (14,56):tub=tub.cut(cyl(x,-15.35,-3.5,2.35,10))
    put('head_bolts','灯头双 M2 穿肩锁紧件','灯头','非磁316不锈钢',pack(*[cyl(x,-15.35,-3.5,1.98,6.55) for x in (14,56)]),mass=.9)
    # 两侧进排；保留风机底吸平面前的连通气室。
    for y in [-51,-46,-41,-36,-31,-26]:
        tub=tub.cut(box(-.2,2,y,y+3.3,-9.0,5.0),box(68.7,71,y,y+3.3,-9.0,5))
    bezel=rr(0,70.6,-57,-13,9.9,11.6,2.6).cut(rr(5.3,65.3,-52,-20,9.8,11.8,4),rr(4.9,65.7,-52.4,-19.6,9.8,11.05,4.4))
    # 可卸前圈：四只自攻/短热熔嵌件，坐落在独立角柱，不借 PCB 承力。
    fixes=[(3,-54),(67.6,-54),(3,-16.3),(67.6,-16.3)]
    for x,y in fixes:
        tub=tub.fuse(cyl(x,y,5.0,4.8,4.9),box(.8 if x<5 else 67.5,3.2 if x<5 else 69.9,y-.7,y+.7,5,9.9)).cut(cyl(x,y,6.5,1.65,3.6))
        bezel=bezel.cut(cyl(x,y,9.89,2.2,1.8),cyl(x,y,10.9,3.6,1))
    put('bezel_screws','前圈四颗 M2','灯头','非磁316不锈钢',pack(*[cyl(x,y,6.8,1.55,4.1).fuse(cyl(x,y,10.9,3.4,.65)) for x,y in fixes]),mass=.65)
    # 前圈一体的四条平底筋；扩压脚仅止于板面，不让螺钉穿板。
    for u,vv,U,V in j['boards']['led']['clamp']['rect_uv_mm'].values():
        bezel=bezel.fuse(box(4.3+u,4.3+U,-19-V,-19-vv,8.6,10.04))
    printed('head_bezel','可卸灯头前圈','灯头',bezel,'ASA')
    # 独立双路插合量规：约 24.77 mm 插长；另留锁舌、翼与装配公差。
    # 三槽有间隔；端壳夹在同一不可翻转的带肩托架中，按顺序装线而非任意互插。
    for n,x in enumerate((27.,43.,59.)):
        put('head_power_lock'+str(n+1),'P'+str(n+1)+' 独立双路插合量规','灯头','接口',box(x,x+11,-55,-30,-27.95,-17.05),mass=1.8)
    rack=box(25.4,71.6,-55.5,-30,-29.55,-28.3)
    for x in (25.4,40.7,56.7,70.45):rack=rack.fuse(box(x,x+1.15,-55.5,-30,-28.5,-16.8))
    rack=rack.fuse(box(25.4,69,-53,-50,-17.05,-16.7),box(25.4,69,-34,-32,-17.05,-16.7))
    tub=tub.fuse(rack)

    # 三侧开口截面，绝缘线束以薄编织套约束；正面承力舌和右轨分开。
    ps=path();harness=strip(ps,-2.8,2.8,-.95,.95)
    # 独立右轨只在外轮廓以外；弯头属灯头/背夹内部走线。内背筋+上下挡边。
    ext=[q for q in ps if q[0]==76.5]
    rail=Solid.make_loft([Wire.make_polygon([(x-w,y,h+t) for w,t in [(-3,-1.8),(3.8,-1.8),(3.8,1.8),(-3,1.8),(-3,1.05),(2.9,1.05),(2.9,-1.05),(-3,-1.05)]],close=True) for x,y,h,_,__ in ext],ruled=True)
    # 右轨以外耳和灯头、背盖各连接一端；轨道与握持侧键段不交叠。
    for y,h in [(-28,-6.6),(86,7.35)]:
        anchor=box(69.7,73.45,y,y+2,h-1,h+1)
        if y<0:tub=tub.fuse(anchor)
        else:shell=shell.fuse(anchor)
        rail=rail.cut(anchor)
    rail=rail.cut(BASE['liner']['sh'],BASE['frame']['sh'])
    chassis=chassis.cut(harness)  # 顶角外侧的电缆通槽，不侵入手机投影
    printed('side_rail','右侧线槽 · 双挡边','壳架',rail)
    put('trunk','12 芯线束 · 六功率＋六信号','线束','线束包络',harness,(None),mass=4.7)
    tub=tub.cut(box(67.7,71,-48.5,-39,-12.4,-5.2),harness)
    shell=shell.cut(box(68.4,71,99.5,106.4,6.2,13.3))
    print('灯头成形',v,flush=True);tub=tub.cut(p['sink']['sh'],p['blower']['sh'])
    print('shell solids',[(round(s.volume,4),str(s.bounding_box())) for s in tub.solids()],flush=True)
    printed('head_shell','共用机顶灯头底盒','灯头',tub,'ASA')
    # 主板落在完全独立的尾仓，两个 USB 保持板边和间距。
    b=j['boards']['main'];put('main_board',b['name'],'电路板','FR-4',m.board_shape(b))
    for it in b['connectors']+b['fixed']:
        xx,XX,yy,YY=m.absrect(b,it['rect']);s=box(xx,XX,yy,YY,5.7,5.7+it['height']);i=it['node']
        if it.get('shape')=='circle':s=cyl(*pos(b,it['center'])[:2],5.7,XX-xx,it['height'])
        if it.get('pattern')=='usb':
            s=s.cut(box(xx+.6,XX-.6,yy+.6,YY+.1,6.25,5.7+it['height']-.55));shell=shell.cut(box(xx-1.1,XX+1.1,125.65,130,5.1,10.1))
        put(i,it.get('type') or it['name'],'电路板','接口',s,mass=1.4 if i in ('input_usb_c','output_usb_c','input_choke','main_j5') else .12)
    ymetal=65.2  # 两版共用平齐外露铝面；A 在电芯膨胀区以上
    def metal(z,Z,slack=0):
        return rr(5.8-slack,64.85+slack,ymetal-slack,125.35+slack,z,Z,1.4).cut(box(10+slack,66.8,106.8+slack,113.55-slack,z-.1,Z+.1))
    plate=metal(H-1.2,H).fuse(box(11.3,22.3,102.95,106.15,8.5,H-1.15))
    # 低损耗背板：整面平齐铝盖与保护开关导热柱。
    put('power_tim','主板功率区绝缘导热垫','电路板','绝缘导热垫',box(11.3,22.3,102.95,106.15,7.9,8.5))
    put('spreader','外露被动散热片与接触柱','壳架','铝',plate)
    shell=shell.cut(metal(H-1.55,H+.1,-.30),metal(H-1.25,H+.1,.12),box(11.15,22.45,102.8,106.3,8.4,H))
    if a:
        for n,e in enumerate((BAT,UPPER),1):put('cell_'+str(n),'2S 配组软包 · 电芯 '+str(n),'电池仓','锂聚合物包',rr(*e,.75),mass=31)
        put('separator','电芯间绝缘层','电池仓','隔热片',box(5.5,65.1,65,98.6,11.2,11.4))
        put('cell_ntc','电芯 NTC · 贴膜布置','电池仓','接口',box(32,35,78,81,18.4,18.65),mass=.12)
        put('battery_plug','J5 六针锁扣插合上半体','电池仓','接口',rr(54.25,63.55,103.4,116.9,12.7,20.2,.6),mass=2)
        put('thermal_break','电芯与主功率区间绝缘隔断','电池仓','隔热片',box(5.4,65.2,100.58,101.58,3,19.95))
        # 顶部电池盖带 UI；FPC 贴外侧沉槽，拆盖后可解线。
        shell=shell.cut(rr(11.4,63.8,107.05,113.25,21.07,22,1))
        put('panel_flex','九线薄膜面板','电路板','FR-4',rr(11.55,63.65,107.2,113.1,21.07,21.22,.9),mass=.65)
    for i,it in enumerate(j['user_interface']['items']):
        x,y,it_z=it['xyz'];is_key=it['ref'].startswith('SW');diam=3.9 if is_key else 1.45
        lo=(21.22 if a else 5.7+(3 if is_key else .8));hi=21.50 if a else H
        if not a:shell=shell.cut(cyl(x,y,H-1.5,diam+.25,1.7))
        put('cap_'+it['ref'],it['ref']+' · '+('按键' if is_key else '电量灯'),'电路板','TPU' if is_key else '乳白聚碳酸酯',cyl(x,y,lo,diam,hi-lo),orient=None if a else '平端朝平台。',mass=.1)
    if a:
        # 盖前缘落在底壳承托台上，压合面不穿入一体托盘及上挡边。
        shell=shell.cut(rr(3.37,67.23,63.07,100.63,2.95,4.35,1.25),box(4.55,66.05,63.1,64.6,4.1,10.55))
    shell=shell.cut(harness)  # 线束圆弯在侧壁内的实际贯通窗口
    printed('back_cover','背夹可拆盖','壳架',shell);printed('frame','四角底壳、顶轨与承力插肩','壳架',chassis)
    return dict(p)
