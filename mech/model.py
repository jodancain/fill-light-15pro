"""装配坐标为接口中的毫米；形体先按功能分开，再交给同一份导出清单。"""
from pathlib import Path
import json, re, math
from board_layout import contract,xy,absrect
from v04_config import *
from c04 import *
from build123d import loft
from dataclasses import dataclass
from build123d import Solid, Plane, Pos, Compound, RectangleRounded, extrude, Color, Axis, Face, Wire

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT/'interface/mech_elec.json').read_text())
L, D = SPEC['layout'], SPEC['derived_constraints']
# 仅从公开外形说明取宽、长、厚；不查图纸或其他接口。
W,H,T = map(float,re.search(r'手机外形\s*([\d.]+)\s*×\s*([\d.]+)\s*×\s*([\d.]+)',SPEC['coordinate_system']).groups())

@dataclass(frozen=True)
class Structure:
    # 设计人员自定的尺寸或零件占位；不是手机测绘值。单位 mm。
    corner_r: float=9           # 手机圆角仅作示意
    clip_span: float=12
    liner: float=1.2
    fit: float=.25
    jaw: float=1.6
    lip: float=.85              # PETG 角唇内伸；与屏幕面保持轴向间隙
    glass_gap: float=.45
    frame: float=1.8
    wall: float=1.2             # 打印件最小设计壁厚
    head_wall: float=1.6
    housing_r: float=2.8
    slot_w: float=7.2           # 左侧扁线束通道
    insert_d: float=3.2         # M2 短铜母占位；采购后按厂商尺寸打试片
    insert_l: float=3.0
    head_d: float=4.4          # M2 90° 沉头孔大端，装妥不突破包络
    bolt_d: float=2.3
    boss_d: float=6
    neck_pitch: float=6.1
    service: float=6.0         # 颈顶开窗，供短螺钉从 +y 侧装入
    lens_t: float=2
    lens_flange: float=1.0
    mix: float=8               # 从灯珠顶面计的混光深度
    led_xyz: tuple=(3.,3.,1.0)  # 3030；高度为待核的结构预算，不是料规
    led_shift: float=1.1        # 灯板向 -y 平移，留出下缘线井
    fan_recess: float=2.2       # 散热器局部避让风扇，外侧鳍片保持
    underpass: float=0.0       # 禁止整体垫高
    sink_h: float=6.2           # 薄鳍片给驱动器件留出空间；热功率须另测
    fin_base: float=1.6
    fin_t: float=1.2
    fin_count: int=9
    fan_h: float=7
    fan_frame: float=2
    fan_pitch: float=32
    fan_gap: float=.2
    deck_adhesive: float=1.20    # 驱动板背面绝缘胶垫预算
    service_boss_h: float=5
    vent_step: float=5
    vent_w: float=3
    cell_d: float=21.2
    cell_l: float=70
    cell_gap: float=.1
    lid_t: float=1.4
    slide_gap: float=.22
    slide_lip: float=2
    keeper: float=6.5          # 滑盖中指末端弹扣的伸出长度
    cell_slot: float=14         # 开放式滑盖的电芯冠部避让窗
    cheek_vent_h: float=6       # 电芯赤道侧通风，兼容大直径
    spring_r: float=3
    board_seat: float=1.6
    board_wall: float=1.8
    usb: tuple=(9.4,3.8,6.5)   # 母座外包络宽、高、进深；非连接器工程图
    button_r: float=2.15
    light_r: float=1.02
    # 局部特征参数。计算中的微量越界只为布尔通切，不是实物尺寸；explode 为演示位移。
    cam_r: float=5               # 示意平台圆角
    neck_edge: float=1           # 端部铜母座至侧边余量
    anchor_offsets: tuple=(4,14) # 两只背板定位柱到颈下端
    foot: tuple=(3,2)            # 主板支脚方边、距板端
    shelf: tuple=(.8,.5)       # 灯板止挡搭边、止挡端部缩进
    exhaust: tuple=(8,19,.4)     # 侧出风槽数、首槽距灯头中心、上下收边
    intake: tuple=(6,13)         # 侧进风槽数、首槽距风扇中心
    grille: tuple=(9,.7,4.4,2.7,2,1) # 后盖槽数、起点偏移、节距、宽度、两端留边
    boss_merge: float=.5         # 铜母座与壁连接余量
    sink_margin: tuple=(3,2)     # 散热器相对铝基板每侧缩进
    tap_m2: float=1.6            # 铝件 M2 底孔
    fan_r: float=2               # 风扇外框圆角
    rotor: tuple=(7,.33,.5,4,2.6,.3,3.2,2,4) # 叶片数、轮毂比、端隙、叶根/叶尖与弦高占位
    driver_end_gap: float=7      # 驱动板与壳内顶边
    keeper_half: float=4         # 滑扣端檐半宽
    latch_hole: tuple=(4.6,1.6,2) # 锁孔距止端近远界及半宽
    latch_tooth: tuple=(4.3,1.9,1.65) # 弹齿距止端近远界及半宽
    ribs: tuple=(2,8,3,2.8)      # 拨筋数、起点、间距、半宽
    contact_t: float=.22         # 示意弹片板厚
    contact_ratio: float=.6      # 折片相对端面宽度
    board_pod_gap: float=.2      # 仓与主板罩外壁间距
    hood_r: float=2              # 主板罩外圆角
    socket_skin: tuple=(.55,.7)  # USB 壳壁与后壁占位，仅作示意
    button_proud: float=.55      # 按键外露高度
    guide_inset: float=2         # 导光柱进入罩内的深度
    hw_allowance: float=4.0     # 铜母、螺钉、线束、胶带的整机重量预算（g）

P=Structure()
B=contract(SPEC,P,T)
# 料色、体积密度（g/cm³）。非均质部件在 add 处按单件预算替换。
MAT={'PETG':('#43545d',1.27),'ASA':('#dc794e',1.07),'TPU':('#80aaa3',1.21),
     '乳白聚碳酸酯':('#fff1cb',1.20),'铝':('#acbec5',2.70),'铝基板':('#dadfda',2.70),
     'FR-4':('#267a6a',1.85),'封装':('#ffcd71',2.2),'风扇总成':('#394756',1.15),
     '暖白封装':('#ffc570',2.2),'冷白封装':('#e4f2ff',2.2),'线束包络':('#739495',0),
     '电芯':('#5092aa',0),'非磁316不锈钢':('#b7c2ba',8.0),'弹片':('#cca15e',8.6),'接口':('#a4adb4',0),
     '手机参照':('#aab8bc',0),'镜头平台示意':('#344d55',0)}
parts={}; features={}
def box(x,X,y,Y,z,Z):
    assert X>x and Y>y and Z>z,(x,X,y,Y,z,Z)
    return Solid.make_box(X-x,Y-y,Z-z,Plane(origin=(x,y,z)))
def rr(x,X,y,Y,z,Z,r):
    return Pos((x+X)/2,(y+Y)/2,z)*extrude(RectangleRounded(X-x,Y-y,r),amount=Z-z)
def cyl(x,y,z,d,h,axis=(0,0,1)):
    return Solid.make_cylinder(d/2,h,Plane(origin=(x,y,z),z_dir=axis))
def countersink(x,y,z,direction):
    return Solid.make_cone(P.head_d/2,P.bolt_d/2,(P.head_d-P.bolt_d)/2,
                           Plane(origin=(x,y,z),z_dir=(0,0,direction)))
def pack(*sh): return Compound(children=list(sh))
def common(a,b):
    return pack(*(a.intersect(b) or []))
def add(id,name,grp,mat,sh,move,orient=None,mass=None,note=''):
    if orient:
        assert len(sh.solids())==1 and sh.is_valid, (id,'打印件必须是单个有效实体',len(sh.solids()))
    sh.label=id; sh.color=Color(MAT[mat][0])
    parts[id]=dict(sh=sh,id=id,name=name,group=grp,material=mat,color=MAT[mat][0],
                   explode=move,orientation=orient,override=mass,note=note)
def midpoint(r): return sum(r)/2

def board_shape(b):
    w,h=b['size']; x,y,z=b['origin'];t=b['thickness']
    s=rr(x,x+w,y-h,y,z,z+t,b['corner_radius']) if b['corner_radius'] else box(x,x+w,y-h,y,z,z+t)
    for hole in b['holes']:
        xx,yy=xy(b,hole['center']);s=s.cut(cyl(xx,yy,z-.1,hole['drill'],t+.2))
    return s

def chassis():
    g='手机参照'; r=P.corner_r; s=P.clip_span; z=P.liner; top=z+P.frame
    def outline(d,lo,hi): return rr(-d,W+d,-d,H+d,lo,hi,r+d)
    def clips(a):
        return [common(a,box(x,X,y,Y,-T-5,top+1)) for x,X in ((-6,s),(W-s,W+6))
                for y,Y in ((-6,s),(H-s,H+6))]
    def clear(a):
        # 只扣 z>=0 的附件材料；圆角、四角扣及TPU须先并成整体再扣。
        return a.cut(box(0,WINDOW_XY[0],0,WINDOW_XY[1],0,top+1))
    add('phone','手机 · 公开简化外形',g,'手机参照',outline(0,-T,0),(0,0,-20),mass=0,note='仅作参照，不计增重。')
    add('camera_dummy','镜头平台 · 示意（按开窗包络内缩）',g,'镜头平台示意',rr(*CAMERA_PROXY,P.cam_r),
        (0,0,-20),mass=0,note='示意，不作定位基准。属于被避让的手机参照，不是背夹材料。')
    inner=P.fit+z; outer=inner+P.jaw; lipz=-T-P.glass_gap
    lining=outline(inner,lipz,z).cut(outline(P.fit,lipz-1,z+.1))
    liner=clear(outline(inner,0,z).fuse(*clips(lining)))
    # 侧壁只在角上连接软衬，四边中段不包覆侧面。
    plate=outline(0,z,top)
    ring=outline(outer,lipz,top).cut(outline(inner,lipz-1,z))
    lip=outline(outer,lipz-P.jaw,lipz).cut(outline(-P.lip,lipz-P.jaw-1,lipz+1))
    rail=box(*RAIL_X,*RAIL_Y,z,top).fuse(box(*RAIL_X,*RAIL_WEB_Y,0,z))
    frame=clear(plate.fuse(*clips(ring),*clips(lip),rail))
    # 背板承担力，不再设承颈或外露长线束。低平台到高背盖的过渡均用非金属。
    for x,y in MOUNTS:
        frame=frame.fuse(cyl(x,y,top,4.8,22.6-top)).cut(cyl(x,y,18.9,2.95,4.1))
    for h in B['driver']['holes']:
        x,y=xy(B['driver'],h['center']);frame=frame.fuse(cyl(x,y,top,4.5,DRIVER_O[2]-top)).cut(cyl(x,y,1.6,1.65,3.2))
    add('frame','四角半包承力底壳','壳架','PC-FR',frame,(0,0,-8),'贴背面朝平台；角唇局部支撑。')
    add('liner','软质整片内衬','壳架','TPU',liner,(0,0,-14),'平面朝平台。')
MAT.update({'绝缘导热垫':('#aea79e',2.5),'PC-FR':('#455854',1.28),'隔热片':('#d2d4be',.22),'锂聚合物包':('#abb2b4',0)})
def profile(x,X,y,Y,z,r):
    return Pos((x+X)/2,(y+Y)/2,z)*RectangleRounded(X-x,Y-y,r)
def make_hood():
    # 三个水平圆角截面放样：下摆顺手机底端收薄，上表面与灯窗齐平。
    outer=loft([profile(-.5,71.1,55.1,143,3,10),profile(-.35,70.95,62.05,137.3,11.9,8),profile(-.1,70.7,64.05,132.4,20.6,6),profile(0,70.6,64.1,130.4,24,5)],ruled=True)
    inner=loft([profile(1,69.6,65.7,141.4,2.9,6.5),profile(1.2,69.4,65.9,134.4,14,5.5),profile(1.5,69.1,65.4,129.6,22.6,3.65)],ruled=True)
    hood=outer.cut(inner)
    # 实体电路舱和灯板的四周间隙，不切穿面皮
    win=rr(5.3,65.3,67,99,22.5,24.5,4)
    hood=hood.cut(win,rr(4.9,65.7,66.6,99.4,22.5,23.45,4.4))
    diffuser=rr(5.45,65.15,67.15,98.85,23.4,24,3.85).fuse(rr(5.02,65.58,66.72,99.28,22.65,23.40,4.28))
    for x,y in MOUNTS:hood=hood.cut(cyl(x,y,3,2.3,22),cyl(x,y,22.95,4.1,2),cyl(x,y,2.99,5.02,19.61))
    # 两侧沿手机中段换气；避开靠手机侧，不以背玻璃当风道壁。
    for yy in PORT_Y:
        hood=hood.cut(box(-2,3,yy,yy+PORT_RUN,*AIR_IN),box(67.3,73,yy,yy+PORT_RUN,*AIR_OUT))
    # 下层驱动的损耗不在灯板上；侧开对流槽，不把其散热量当风机串联流量。
    for yy in AUX_Y:hood=hood.cut(box(-2,3,yy,yy+AUX_DY,*AUX_Z),box(67.3,73,yy,yy+AUX_DY,*AUX_Z))
    # 两个穿带孔仅在背盖斜尾，不在手机底边。6 mm 软带给输入线卸力。
    for xx in (8.1,12.8):hood=hood.cut(box(xx,xx+1.8,134.2,141.,2.9,24.1))
    for port in L['ports'].values():
        x=port['x'];hood=hood.cut(rr(x-6.3,x+6.3,125.5,151,14.3,20.3,1.4))
    for i,item in enumerate(o for o in B['main']['fixed'] if o['node'].startswith(('key_','light_'))):
        x,y=xy(B['main'],item['center']);r=2.1 if i<3 else .85
        hood=hood.cut(cyl(x,y,22.4,2*r+.4,2))
        add('cap_'+item['ref'],item['name'].replace('同轴中心','')+' · 透出件','壳架','TPU' if i<3 else '乳白聚碳酸酯',cyl(x,y,15+item['height'],2*r,24-(15+item['height'])),(0,0,25),note='弹性帽/导光杆打样占位，胶接限位。')
    add('shell','斜收尾一体背盖','壳架','PC-FR',hood,(0,0,32),'发光面朝平台；内桥局部可拆支撑。')
    add('diffuser','嵌入式乳白发光窗','灯头','乳白聚碳酸酯',diffuser,(0,0,39),note='从内侧装入；台阶遮光，周缘点胶。')
def make():
    chassis(); make_hood()
    # 撤去软包；热侧用可拆导风盘。冷风区盘底开窗，手机侧绝缘毡不承载风机。
    deck=rr(3,67.6,66.95,102.2,4.1,5.45,3.3).cut(rr(6,41,68.4,99.4,4,5.6,2))
    for xx in (3.,66.):deck=deck.fuse(box(xx,xx+1.5,70,100,3,4.5))
    # 降低进风窗左缘：不让整道盘沿堵住风机负压侧，保留前后两条横梁。
    deck=deck.cut(box(2.8,9.8,72.8,94.22,2.99,5.46))
    # 在前后缘拦回流：出风段由风机口、散热片基座、侧堤和盘底围成。
    for yy in (66.85,99.1):deck=deck.fuse(box(44.4,65.2,yy,yy+1.2,5.4,18.2))
    for xx,yy in [(9.8,69.2),(41,98.1),(41,69.2),(9.8,98.1)]:
        deck=deck.fuse(box(xx,xx+1.5,yy,yy+1.7,3.9,7.5))
    # 超出中央冷风窗的独立柱用细脚连接到盘边，不堵进风面。
    for yy in (69.2,98.1):deck=deck.fuse(box(4.9,43,yy,yy+1.7,4.1,5.45))
    add('shield','冷侧隔热导风盘','风道','PC-FR',deck,(0,-8,18),'盘底朝平台；肩面限位、脚榫定位，不接触手机金属。')
    add('barrier','贴机侧封面绝缘隔热毡','风道','隔热片',rr(6.8,64.2,67.5,100.3,3,3.8,2),(0,-15,8),note='含保护面膜预算；不作为风机固定面。')
    blower=rr(*FAN,2).cut(cyl(26.8,84.4,7.4,25,10.2),box(29,45,80.2,96.8,8.2,16.8))
    # 蜗壳上盖封住 +Z，只有底吸面与 +X 出口连通；不是用自由风量代替风道验收。
    blower=blower.fuse(rr(9.3,44.3,66.9,101.9,17.06,17.5,2))
    rotor=cyl(26.8,84.4,9.2,10,7.8)
    from build123d import Rot
    for i in range(11):rotor=rotor.fuse(Pos(26.8,84.4,0)*Rot(0,0,i*360/11)*box(4.8,11.9,-.45,.45,9.8,16.4))
    add('blower','35 × 35 × 10 离心风机','风道','风扇总成',pack(blower,rotor),(-18,0,16),mass=11,note='按 Delta BFB03505HHA-A 尺寸级和重量预算；测速版本与装机 P–Q 待选样。')
    sink=rr(4.3,66.3,66,100,19.4,20.6,2)
    for j in range(12):sink=sink.fuse(box(*FIN[:2],68.1+2.65*j,68.9+2.65*j,FIN[2]+1.2,19.45))
    # 四个攻丝处局部加厚避开蜗壳；采用短螺钉，端部不得侵入风机。
    for hole in B['led']['holes']:
        x,y=xy(B['led'],hole['center']);sink=sink.fuse(cyl(x,y,17,4.4,2.5)).cut(cyl(x,y,16.9,2.05,4))
    sink=Pos(0,0,-1.2)*sink
    # 原电池端口空间用于电源热接触：舌片与基座连成一体，不向背玻璃散热。
    sink=sink.fuse(box(9.3,24.3,98.7,106.6,18.2,19.4))
    add('power_tim','主板功率区绝缘导热垫','风道','绝缘导热垫',box(10.3,23.3,102.9,106.2,17.2,18.2),(6,0,15),note='下面为电源封装接触面预算 Z=17.2；实际压缩、导热和电气间距待选型。')
    add('sink','带主板导热舌的横向铝鳍','灯头','铝',sink,(17,0,19))
    for b in B.values():
        x,y,z=b['origin'];z+=b['thickness'];mv=(0,0,{'led':28,'driver':8,'main':18}[b['id']])
        add(b['id']+'_board',b['name'],'电路板','铝基板' if b['id']=='led' else 'FR-4',board_shape(b),mv)
        for it in b['connectors']+b['fixed']:
            xx,XX,yy,YY=absrect(b,it['rect']);s=box(xx,XX,yy,YY,z,z+it['height'])
            if it.get('pattern')=='usb':s=s.cut(box(xx+.6,XX-.6,yy+.6,YY+.1,z+.55,z+it['height']-.55))
            if it.get('shape')=='circle':s=cyl(*xy(b,it['center']),z,XX-xx,it['height'])
            add(it['node'],it.get('type') or it['name'],'电路板','接口',s,mv,mass=1.6 if it['ref']=='L_IN' else 1.5 if it['ref'] in ('L_W','L_C') else 1.1 if it.get('pattern')=='usb' else 0,
                note=('针 1–4：'+' / '.join(it['nets'])+'。'+it['note']) if it.get('note') and 'nets' in it else '')
        for col,mat in [('W','暖白封装'),('C','冷白封装')]:
            chips=[box(*absrect(b,e['rect']),z,z+e['height']) for e in b['leds'] if e['color']==col]
            if chips:add('led_'+col,mat+' × 36','灯头',mat,pack(*chips),mv)
    # 分舱托架：两侧立墙承担光机与主板重量，中央留冷风吸口和侧排通道。
    deck=parts['shield']['sh']
    # 灯板左侧留两柱支承，与风机外壳保持间隙；右侧边堤承托散热基座。
    for yy in (68,97.4):deck=deck.fuse(box(4.1,5.75,yy,yy+1.4,5.4,18.2))
    for xx,yy in MOUNTS:deck=deck.cut(cyl(xx,yy,2.9,5.1,20))
    parts['shield']['sh']=deck;deck.color=Color(MAT['PC-FR'][0])
    base=parts['frame']['sh']
    for xx in [3.7,65.5]:
        for yy in [107.1,122.0]:
            base=base.fuse(box(xx,xx+1.4,yy,yy+1.45,3,14),box(4.9 if xx<5 else 63.95,6.65 if xx<5 else 65.7,yy,yy+1.45,13.1,14))
    parts['frame']['sh']=base;base.color=Color(MAT['PC-FR'][0])
    screws=[]
    for x,y in MOUNTS:
        screws.extend([cyl(x,y,19.35,2.,3.6),cyl(x,y,22.95,3.8,1.0)])
    add('screws','四颗背盖沉台螺钉','壳架','非磁316不锈钢',pack(*screws),(0,0,38),mass=.8,note='成品螺钉相对磁导率 ≤1.05，热熔螺母使用同限值的铜材。')
    fast=[]
    for h in B['led']['holes']:
        x,y=xy(B['led'],h['center']);fast.extend([cyl(x,y,16.9,1.98,4.1),cyl(x,y,21,4,1.25)])
    add('led_fasteners','四只小头 M2.5 · 名义包络','灯头','非磁316不锈钢',pack(*fast),(0,0,31),mass=1,note='非磁成品，μr≤1.05。')
    # 肩面夹住隔舱两侧，脚榫落入背板浅槽；拆面盖可提起隔舱，不用撬胶或压电芯。
    hood=parts['shell']['sh'];base=parts['frame']['sh'];deck=parts['shield']['sh']
    for x,start,end in [(3.,70.6,72.5),(3.,96.7,99.4),(66.,74,94)]:
        slot=box(x-.15,x+1.65,start-.15,end+.15,2.42,3.01)
        base=base.cut(slot);deck=deck.fuse(box(x,x+1.5,start,end,2.48,3.05))
    for xx,XX,yy in [(.9,3.94,67.48),(.9,3.94,94.27),(66.68,69.7,78.22)]:
        hood=hood.fuse(box(xx,XX,yy,yy+1.2,5.45,22.68))
    for i,s in [('frame',base),('shield',deck),('shell',hood)]:
        assert s.is_valid and len(s.solids())==1,i
        parts[i]['sh']=s;s.color=Color(MAT['PC-FR'][0])
    # 85°C 开关贴基座，在散热片局部铣出凹位，保留导热接触面。
    sink=parts['sink']['sh'].cut(box(51.8,61.2,90.8,96.2,14.8,18.2))
    parts['sink']['sh']=sink;sink.color=Color(MAT['铝'][0])
    add('thermal_trip','85°C 常闭温控开关 · 候选包络','灯头','接口',rr(52,61,91,96,15.3,18.2,1),(12,0,16),mass=1.2)
    # 键帽防脱法兰贴顶壁内侧；导光件也按实形导出，透光性另打样。
    for it in (o for o in B['main']['fixed'] if o['node'].startswith(('key_','light_'))):
        i='cap_'+it['ref'];v=parts[i];x,y=xy(B['main'],it['center'])
        if it['ref'].startswith('SW'):
            v['sh']=v['sh'].fuse(cyl(x,y,21.1,5.8,1.45))
        v['sh'].color=Color(v['color']);v['orientation']='外端朝上、内端着床，法兰局部支撑；尺寸与光效先做试片。'
    parts['diffuser']['orientation']='透明或乳白 PC 打样，齐平面朝平台；亦可改用机加工乳白片，不作承力件。'
