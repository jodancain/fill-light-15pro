"""装配坐标为接口中的毫米；形体先按功能分开，再交给同一份导出清单。"""
from pathlib import Path
import json, re, math
from board_layout import contract,xy,absrect,remote_devices
from ridge import ridge_path,strip,flat_strip,half_at,neck_x,X as RX,WIDTH,HALF,CAP_IN,CAP_OUT,BANDS
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
    cam_offset: float=6         # 取整数的示意岛，方形、无光学数据
    cam_size: float=30
    cam_height: float=4
    cam_clear: float=2
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
    cam_cut_r: float=4           # 背板避让窗圆角
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
     '电芯':('#5092aa',0),'弹片':('#cca15e',8.6),'接口':('#a4adb4',0),
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

def bundle_path():
    # (项目 y,z)：主板入口→架空仓底→颈→灯板下缘→驱动板插接前分线区。
    R=5.;yv=-14.65;zc=6.4;start=yv+R;z2=-7.8
    pts=[(15.,zc)]
    pts.append((start,zc))
    for j in range(1,49):
        a=j*math.pi/96;pts.append((start-R*math.sin(a),zc-R+R*math.cos(a)))
    pts.append((yv,z2))
    for j in range(1,49):
        a=j*math.pi/96;pts.append((yv-R*(1-math.cos(a)),z2-R*math.sin(a)))
    pts.append((-32.,z2-R))
    return pts

def head_bundle(clear=0):
    path=bundle_path();cx=L['neck']['x'][0]+P.wall+P.slot_w/2
    # 功率线 OD 1.10，信号 OD 0.65；2 对并排，8 线三列三层，另留包带/间距。
    wid=6.85+2*clear;half=1.2+clear
    side=[[],[]]
    for j,(y,z) in enumerate(path):
        a=path[max(j-1,0)];b=path[min(j+1,len(path)-1)];dy=b[0]-a[0];dz=b[1]-a[1];l=math.hypot(dy,dz)
        # 直段接弧处用解析切线，避免相邻直段长度影响法向。
        if abs(y+9.65)<1e-7:dy,dz,l=-1,0,1
        if abs(y+14.65)<1e-7:dy,dz,l=0,-1,1
        for k,sign in enumerate((-1,1)):side[k].append((cx-wid/2,y-sign*half*dz/l,z+sign*half*dy/l))
    face=Face(Wire.make_polygon(side[0]+side[1][::-1],close=True))
    return Solid.extrude(face,(wid,0,0))

def bundle_solid(clear=0):
    w=WIDTH+2*clear;h=HALF+clear
    return head_bundle(clear).fuse(flat_strip(w,6.4-h,2*h),strip(ridge_path(L,P),RX-w/2,w,lambda y:-half_at(y)-clear,lambda y:half_at(y)+clear))

def chassis():
    g='手机参照'; r=P.corner_r; s=P.clip_span; z=P.liner; top=z+P.frame
    def outline(d,lo,hi): return rr(-d,W+d,-d,H+d,lo,hi,r+d)
    def clips(a):
        return [common(a,box(x,X,y,Y,-T-5,top+1)) for x,X in ((-6,s),(W-s,W+6))
                for y,Y in ((-6,s),(H-s,H+6))]
    def clear(a):
        off=P.cam_offset-P.cam_clear; span=P.cam_size+2*P.cam_clear
        return a.cut(rr(off,off+span,off,off+span,-1,top+1,P.cam_cut_r))
    add('phone','手机 · 公开简化外形',g,'手机参照',outline(0,-T,0),(0,0,-20),mass=0,note='仅作参照，不计增重。')
    o=P.cam_offset
    add('camera_dummy','镜头平台 · 示意',g,'镜头平台示意',rr(o,o+P.cam_size,o,o+P.cam_size,0,P.cam_height,P.cam_r),
        (0,0,-20),mass=0,note='示意，非苹果图纸数据。')
    inner=P.fit+z; outer=inner+P.jaw; lipz=-T-P.glass_gap
    lining=outline(inner,lipz,z).cut(outline(P.fit,lipz-1,z+.1))
    liner=clear(outline(inner,0,z)).fuse(*clips(lining))
    # 侧壁只在角上连接软衬，四边中段不包覆侧面。
    plate=clear(outline(0,z,top))
    ring=outline(outer,lipz,top).cut(outline(inner,lipz-1,z))
    lip=outline(outer,lipz-P.jaw,lipz).cut(outline(-P.lip,lipz-P.jaw-1,lipz+1))
    frame=clear(plate.fuse(*clips(ring),*clips(lip)))
    n=L['neck']; nx,NX=n['x']; ny,NY=n['y']; nz=top; NZ=nz+n['thickness']
    xs=[NX-P.boss_d/2-P.neck_edge, NX-P.boss_d/2-P.neck_edge-P.neck_pitch]
    pins=[(midpoint(xs),y) for y in (NY-d for d in P.anchor_offsets)]
    for x,y in pins:
        frame=frame.fuse(cyl(x,y,top,P.boss_d,P.insert_l))
        frame=frame.cut(cyl(x,y,top,P.insert_d,P.insert_l+1))
    # 主板四只绝缘支脚与背板一体，让 PCB 可从 +z 直接放入，无需挤过倒扣。
    mb=L['main_board']; mx,MX=mb['x']; my,MY=mb['y']
    for xx in (mx,MX-P.foot[0]):
        for yy in (my+P.foot[1],MY-sum(P.foot)):
            frame=frame.fuse(box(xx,xx+P.foot[0],yy,yy+P.foot[0],top,top+P.board_seat))
    # 仓两侧支承与中间导轨留出独立通道，不让线束穿过两节电芯。
    pod=L['pod'];sx=nx+P.wall;SX=sx+P.slot_w
    add('frame','四角开放壳架','壳架','PETG',frame,(0,0,-8),'背板贴平台；角唇与悬空耳根用局部支撑。')
    add('liner','贴机软衬','壳架','TPU',liner,(0,0,-14),'背板外侧平放，四角向上。')
    sx=nx+P.wall; SX=sx+P.slot_w; sz=nz+P.wall; SZ=NZ-P.wall
    channel=box(sx,SX,ny-5,NY+5,sz,SZ)
    channel=box(sx,SX,ny-5,15,sz,SZ).fuse(flat_strip(P.slot_w,sz,SZ-sz),box(RX-P.slot_w/2,RX+P.slot_w/2,38,NY+1,sz,SZ))
    neck=box(nx,NX,ny,NY,nz,NZ).cut(channel,strip(ridge_path(L,P),RX-3.65,7.3,-1.42,1.42))
    for x,y in pins:
        neck=neck.cut(cyl(x,y,nz-.1,P.boss_d+2*P.fit,P.insert_l+.2),
                      cyl(x,y,nz,P.bolt_d,NZ-nz+1),countersink(x,y,NZ,-1))
    # 开窗贯通 Z；可从侧上方置入螺钉，细长 L 形扳手沿颈身操作。
    joint_y=ny+P.wall*2
    for x in xs:
        neck=neck.cut(cyl(x,ny-.1,(nz+NZ)/2,P.bolt_d,joint_y-ny+.2,(0,1,0)),
                      box(x-P.head_d/2,x+P.head_d/2,joint_y,joint_y+P.service,nz-.1,NZ+.1))
    frame=parts['frame']['sh'].cut(strip(ridge_path(L,P),RX-3.65,7.3,-1.43,1.43),flat_strip(P.slot_w,4.95,2.9));parts['frame']['sh']=frame;frame.color=Color(MAT['PETG'][0])
    neck=neck.cut(strip(ridge_path(L,P),50.45,7.65,CAP_IN-.1,CAP_OUT+.1),box(56.7,64,38,41.6,6.4+CAP_IN,NZ+.1),cyl(61.6,39.8,6.4+CAP_IN-P.insert_l,P.insert_d,P.insert_l+.1))
    add('neck','双端可拆走线颈','颈部','PETG',neck,(23,0,8),'右侧长边向下，让线槽纵壁立起；端孔局部支撑。')
    features.update(sx=sx,SX=SX,sz=sz,SZ=SZ,nz=nz,NZ=NZ,xs=xs,pins=pins,channel=channel,
                    joint_y=joint_y,plate_top=top)

def lamp():
    k=L['head']; x,X=k['x']; y,Y=k['y']; cx,cy=k['window']['center']; wx,wy=k['window']['size']
    z=-T-k['z_front_max_above_screen']; Z=min(k['z_rear_max'],z+k['depth_max'])
    w=P.head_wall; cap=z+P.wall; lens_base=Z-P.lens_t; rim=lens_base-P.wall
    u,v,h=P.led_xyz; ledface=lens_base-P.mix-h; lb=L['led_board']; pcb_lo=ledface-lb['pcb_thickness']
    sink_lo=pcb_lo-P.sink_h; ftop=sink_lo+P.fan_recess-P.fan_gap; fb=ftop-P.fan_h
    fan=k['fan']; fx,fy=fan['center']; fs=fan['size']; f=fs/2
    def centered(a,b,lo,hi): return box(cx-a/2,cx+a/2,cy-b/2,cy+b/2,lo,hi)
    shell=rr(x,X,y,Y,cap,rim,P.housing_r).cut(
        rr(x+w,X-w,y+w,Y-w,cap-1,rim+1,P.housing_r-w))
    bezel=rr(x,X,y,Y,rim,Z,P.housing_r).cut(centered(wx,wy,rim-1,Z+1))
    bezel=bezel.cut(centered(wx+2*P.lens_flange+.2,wy+2*P.lens_flange+.2,lens_base,Z+.1))
    # 分体压圈：先将柔光片粘在圈背，再从发光侧整体放入；无需把片挤过灯板肩。
    a,b=lb['size']
    shelves=[box(e,E,cy-P.led_shift-b/2+P.shelf[1],cy-P.led_shift+b/2-P.shelf[1],ledface,ledface+P.wall)
             for e,E in ((x+w,cx-a/2+P.shelf[0]),(cx+a/2-P.shelf[0],X-w))]
    shell=shell.fuse(*shelves)
    jz=(features['nz']+features['NZ'])/2
    # 底边两只内置铜母座，轴向与颈内短螺钉一致。
    for xx in features['xs']:
        shell=shell.fuse(cyl(xx,Y,jz,P.boss_d,w+P.insert_l,(0,-1,0)))
        shell=shell.cut(cyl(xx,Y+.1,jz,P.insert_d,P.insert_l+.2,(0,-1,0)))
    sx,SX,sz,SZ=(features[q] for q in ('sx','SX','sz','SZ'))
    shell=shell.cut(box(sx,SX,Y-w-.1,Y+.1,sz,SZ))
    # 两侧鳍片层出风；后盖风机层进风。槽间筋 >= 2 mm。
    for side in (x-.1,X-w-.1):
        for i in range(P.exhaust[0]):
            yy=cy-P.exhaust[1]+i*P.vent_step
            shell=shell.cut(box(side,side+w+.2,yy,yy+P.vent_w,sink_lo+P.exhaust[2],pcb_lo-P.fin_base-P.exhaust[2]))
    # 驱动板挡住部分后盖格栅，在两侧低层补设进风；与上层铝鳍片排风槽分层。
    for side in (x-.1,X-w-.1):
        for i in range(P.intake[0]):
            yy=fy-P.intake[1]+i*P.vent_step
            shell=shell.cut(box(side,side+w+.2,yy,yy+P.vent_w,cap+P.deck_adhesive+L['driver_board']['pcb_thickness'],fb))
    cover=rr(x,X,y,Y,z,cap,P.housing_r)
    edge=max(P.boss_d/2,P.head_d/2+P.wall)  # 沉头口到外侧也留足 1.2 mm
    for xx in (x+edge,X-edge):
        for yy in (y+w+P.boss_d/2-P.boss_merge,Y-w-P.boss_d/2+P.boss_merge):
            shell=shell.fuse(cyl(xx,yy,cap,P.boss_d,P.service_boss_h)).cut(cyl(xx,yy,cap-.1,P.insert_d,P.insert_l+.2))
            cover=cover.cut(cyl(xx,yy,z-.1,P.bolt_d,P.wall+.2),countersink(xx,yy,z,1))
    for i in range(P.grille[0]):
        xx=fx-f+P.grille[1]+i*P.grille[2]
        cover=cover.cut(box(xx,xx+P.grille[3],fy-f+P.grille[4],fy+f-P.grille[5],z-.1,cap+.1))
    # LED 下缘的带状回转井保持外壁轮廓；检查实体而非只量颈部截面。
    shell=shell.cut(head_bundle(.13))
    # 后盖上 1.2 mm 的胶垫改为带沉孔承台；从后盖穿板，锁入壳体肩部的 M2 铜母。
    d=B['driver'];dz=d['origin'][2];dt=dz+d['thickness']
    for hole in d['holes']:
        px,py=xy(d,hole['center']);left=px<cx
        bridge_lo,bx=(x+w-.4,px) if left else (px,X-w+.4)
        boss=cyl(px,py,dt,5.6,3.8).fuse(box(bridge_lo,bx,py-2.2,py+2.2,dt,dt+3.8))
        shell=shell.fuse(boss).cut(cyl(px,py,dt-.05,P.insert_d,3.15))
        cover=cover.fuse(cyl(px,py,cap,5.6,P.deck_adhesive)).cut(cyl(px,py,z-.1,P.bolt_d,dz-z+.2),countersink(px,py,z,1))
    add('head_shell','灯头框 · 双侧排风','灯头','ASA',shell,(0,-23,0),'发光窗朝下；两侧风槽与铜母座局部支撑。')
    add('head_bezel','发光窗压圈','灯头','ASA',bezel,(0,-23,45),'外侧平面朝平台；压圈和柔光片从发光侧装入。')
    add('head_grille','进风格栅后盖','灯头','ASA',cover,(0,-23,-37),'外侧大面平放。')
    add('diffuser','乳白柔光片','灯头','乳白聚碳酸酯',centered(wx+2*P.lens_flange,wy+2*P.lens_flange,lens_base,Z),
        (0,-23,38),note='整片裁切，从背侧装入压圈，边缘固定。')
    add('led_board','铝基灯板','电路板','铝基板',board_shape(B['led']),(0,-23,17))
    gx,gy=lb['grid']; dx,dy=lb['pitch']
    beads=[]
    for col,tag,mat in [('W','warm','暖白封装'),('C','cool','冷白封装')]:
        bb=[box(*absrect(B['led'],e['rect']),ledface,ledface+h) for e in B['led']['leds'] if e['color']==col]
        beads.extend(bb); add('led_'+tag,('暖白 2700 K' if col=='W' else '冷白 6500 K')+' · 3030 × 36','电路板',mat,pack(*bb),(0,-23,23),mass=.35)
    sa=a-2*P.sink_margin[0]; sb=b-2*P.sink_margin[1]; sink=centered(sa,sb,pcb_lo-P.fin_base,pcb_lo)
    for i in range(P.fin_count):
        yy=cy-sb/2+(sb-P.fin_t)*i/(P.fin_count-1)
        sink=sink.fuse(box(cx-sa/2,cx+sa/2,yy,yy+P.fin_t,sink_lo,pcb_lo-P.fin_base))
    # 风扇外框嵌入局部避让腔。保留周边全高鳍片，不令风扇与鳍片重叠。
    sink=sink.cut(box(fx-f-.25,fx+f+.25,fy-f-.25,fy+f+.25,sink_lo-.1,sink_lo+P.fan_recess))
    for hole in B['led']['holes']:
        hx,hy=xy(B['led'],hole['center'])
        sink=sink.fuse(cyl(hx,hy,pcb_lo-3.8,4.8,3.8)).cut(cyl(hx,hy,pcb_lo-3.5,2.05,3.6))
    # 铝件四只加厚安装台与风扇四角同轴，M2 盲孔不打穿贴灯面的散热底板。
    for dx in (-1,1):
        for dy in (-1,1):
            hx=fx+dx*P.fan_pitch/2; hy=fy+dy*P.fan_pitch/2
            sink=sink.fuse(cyl(hx,hy,sink_lo+P.fan_recess,P.boss_d,P.sink_h-P.fin_base-P.fan_recess))
            sink=sink.cut(cyl(hx,hy,sink_lo+P.fan_recess-.1,P.tap_m2,P.insert_l+.1))
    # 温控开关压接实铝平面（独立于风扇），横向耳片卡簧/夹具待定型。
    sink=sink.fuse(box(7,14,-36,-28,sink_lo,pcb_lo-P.fin_base))
    add('heatsink','横向通风铝鳍片','灯头','铝',sink,(0,-23,5))
    fanbody=rr(fx-f,fx+f,fy-f,fy+f,fb,ftop,P.fan_r).cut(cyl(fx,fy,fb-.1,fs-2*P.fan_frame,P.fan_h+.2))
    for xx in (-1,1):
        for yy in (-1,1):
            fanbody=fanbody.cut(cyl(fx+xx*P.fan_pitch/2,fy+yy*P.fan_pitch/2,fb-.1,P.bolt_d,P.fan_h+.2))
    nb,ratio,clear,root,tip,neg,pos,low,high=P.rotor
    hub=cyl(fx,fy,fb+clear,fs*ratio,P.fan_h-2*clear)
    blades=[box(fx+root,fx+f-tip,fy-neg,fy+pos,fb+low,fb+high).rotate(Axis((fx,fy,0),(0,0,1)),i*360/nb) for i in range(nb)]
    add('fan','40 mm 轴流风扇','灯头','风扇总成',pack(fanbody,hub.fuse(*blades)),(0,-23,-12),mass=13,note='按 13 g 预算，非实测；叶轮与框分体。')
    db=L['driver_board']; a,b=db['size']; drive_lo=cap+P.deck_adhesive; drive_top=drive_lo+db['pcb_thickness']
    by=y+w+P.driver_end_gap
    add('driver_board','灯驱动板 · 上部层','电路板','FR-4',board_shape(B['driver']),
        (0,-23,-24),note='裸板＋器件重量预算；器件高度未定，电感与固定接口另列占位；未覆盖未定型器件。')
    features.update(head_z=z,head_Z=Z,fan_xy=(fx,fy),drive_lo=drive_lo,drive_top=drive_top,fb=fb,
                    cap=cap,pcb_lo=pcb_lo,lens_base=lens_base,led_top=ledface+h,ftop=ftop,beads=beads)

def power():
    k=L['pod']; x,X=k['x']; y,Y=k['y']; mid=(x+X)/2; w=k['wall']
    base=k['base']; z=features['plate_top']+P.underpass; Z=z+k['thickness']; ax=k['cell_axis_y']
    zc=z+base+P.cell_gap+k['cell_d_max']/2
    # 两端实壁托住弹片，上下侧壁在电芯赤道处开长窗。盖由 -x 端推入。
    tray=box(x,X,y,Y,z,Z).cut(box(x+w,X-w,y+w,Y-w,z+base,Z+.2))
    shoulder=Z-P.wall; lid_hi=shoulder-P.slide_gap; lid_lo=lid_hi-P.lid_t
    tray=tray.cut(box(x-.1,x+w+.1,y+w,Y-w,lid_lo-P.slide_gap,Z+.1))
    for e,E in ((y+w,y+w+P.slide_lip),(Y-w-P.slide_lip,Y-w)):
        tray=tray.fuse(box(x,X-w,e,E,shoulder,Z))
    # 对侧端檐压住中指，取出电芯不必拆螺钉。
    m=midpoint(ax); end=X-w
    tongue=box(end-P.keeper,end,m-P.keeper_half,m+P.keeper_half,shoulder,Z).cut(box(end-P.latch_hole[0],end-P.latch_hole[1],m-P.latch_hole[2],m+P.latch_hole[2],shoulder-.1,Z+.1))
    tray=tray.fuse(tongue)
    window_x=k['cell_length_range'][1]/2+.2
    for e,E in ((y-.1,y+w+.1),(Y-w-.1,Y+.1)):
        tray=tray.cut(box(mid-window_x,mid+window_x,e,E,zc-P.cheek_vent_h/2,zc+P.cheek_vent_h/2))
    # 电芯测温和两对独立电池线由下端壁出仓，与下方主驱线束分道。
    sx,SX,sz,SZ=(features[q] for q in ('sx','SX','sz','SZ'))
    # 不打旧仓底通孔。
    battery_end=next(j for j in B['main']['connectors'] if j['ref']=='J5')
    ax0,ax1,*_=absrect(B['main'],battery_end['rect']); bz0=z+1.4;bz1=bz0+2.7
    tray=tray.cut(box(ax0,ax1,Y-w-.1,Y+.1,bz0,bz1))
    features['battery_exit']=(ax0,ax1,bz0,bz1)
    lid=box(x,X-w-P.slide_gap,y+w+P.slide_gap,Y-w-P.slide_gap,lid_lo,lid_hi)
    for yy in ax:
        lid=lid.cut(box(x+w,X,yy-P.cell_slot/2,yy+P.cell_slot/2,lid_lo-1,lid_hi+1))
    # 指压中指使方齿下降，推到位后落入端檐孔；滑入、滑出均须按压。
    lid=lid.fuse(box(end-P.latch_tooth[0],end-P.latch_tooth[1],m-P.latch_tooth[2],m+P.latch_tooth[2],lid_hi,lid_hi+P.wall))
    grip_x=x+P.ribs[1]
    # 中指根部两道拨筋，退盖方向 -x。
    for i in range(P.ribs[0]):
        xx=grip_x+P.ribs[2]*i
        lid=lid.fuse(box(xx,xx+P.wall,midpoint(ax)-P.ribs[3],midpoint(ax)+P.ribs[3],lid_hi,Z))
    # 线束在端壁局部开鞍形口，绝不从仓底贯穿。中段保持老版滑盖和两道电芯露冠窗。
    q=ridge_path(L,P); tunnel=strip(q,RX-3.65,7.3,-1.43,1.43)
    roof=strip(q,50.1,7.9,CAP_IN,CAP_OUT)
    # 颈末不以顶盖跨矮区；侧脊沿扁束左边作低梁，越过仓顶边后再闭合压盖。
    side=box(50.1,51.3,50.6,57.85,8.82,23.0)
    roof=roof.fuse(side).cut(box(49,59,44,57.12,16.20,37))
    tray=tray.cut(tunnel,roof); lid=max(lid.cut(tunnel,roof).solids(),key=lambda s:s.volume)
    roof=roof.cut(box(50,59,108.7,115,0,35))
    # 两端横耳带 M2 通孔；中间悬桥可整个从 +Z 拿掉。耳台均在仓投影之外。
    for yy,zz in [(39.8,6.4),(105.9,9.5)]:
        tab=box(57.90,63.8,yy-1.7,yy+1.7,zz+CAP_IN,zz+CAP_OUT)
        if yy>100:tab=tab.fuse(box(57.8,59.05,yy-1.3,yy+1.3,zz+CAP_IN,17.5))
        else:tab=box(57.8,63.8,yy-1.7,yy+1.7,zz+CAP_IN,zz+CAP_OUT)
        roof=roof.fuse(tab).cut(cyl(61.6,yy,zz+CAP_IN-.1,P.bolt_d,1.5))
    roof=roof.cut(strip(q,RX-WIDTH/2-.03,WIDTH+.06,-1.23,1.23))
    parts['neck']['sh']=parts['neck']['sh'].cut(roof);parts['neck']['sh'].color=Color(MAT['PETG'][0])
    add('ridge_cover','仓背线束脊盖','电池仓','PETG',roof,(0,0,30),'侧立打印；拆两端 M2 后向外抬盖，再提线束抽电池盖。')
    add('battery_tray','双槽电池仓','电池仓','PETG',tray,(0,7,10),'仓底朝下；长通风窗采用局部支撑。')
    add('battery_lid','指拨滑盖','电池仓','PETG',lid,(-64,7,16),'盖板底面平放；三指沿 x 方向。')
    for i,yy in enumerate(ax,1):
        left=mid-P.cell_l/2; right=mid+P.cell_l/2
        add(f'cell_{i}',f'21700 电芯 {i}','电池仓','电芯',cyl(left,yy,zc,P.cell_d,P.cell_l,(1,0,0)),
            (0,7+(i-1)*6,25),mass=70,note='标称 70 × Ø21.2；每节按 70 g 计。')
        for j,(a,b) in enumerate([(x+w,left),(right,X-w)],1):
            # 触点示意：贴壁基片 + 接触面，细折片连通两面，非实物弹簧。
            t=P.contact_t; sign=1 if j==1 else -1; wall=a if j==1 else b
            tip=b if j==1 else a
            def disk(start,end): return cyl(min(start,end),yy,zc,2*P.spring_r,abs(end-start),(1,0,0))
            contact=disk(wall,wall+t*sign).fuse(disk(tip,tip-t*sign),
                        box(a,b,yy-P.spring_r*P.contact_ratio,yy+P.spring_r*P.contact_ratio,zc,zc+t))
            add(f'contact_{i}_{j}',f'电芯 {i} · {"左" if j==1 else "右"}弹片','电池仓','弹片',
                contact,(-12 if j==1 else 12,7,15),note='标称长度下压缩态占位；不代表压力或额定电流。')
    features.update(zc=zc,lid_lo=lid_lo,base=base,tray_z=z)

def controls():
    b=L['main_board']; x,X=b['x']; y,Y=b['y']; w=P.board_wall
    z=features['plate_top']; bz=z+P.board_seat; top=bz+b['pcb_thickness']; ce=top+b['height_out_max']
    g='电路板'; fit=P.fit; x0=x-fit-w; x1=X+fit+w; y0=y-fit-w; y1=Y+fit+w
    # 靠电池仓的一道壁共享装配间隙，显式裁短，不移动 PCB。
    y0=max(y0,L['pod']['y'][1]+P.board_pod_gap)
    shell=rr(x0,x1,y0,y1,z,ce+P.wall,P.hood_r).cut(
        box(x-fit,X+fit,y-fit,Y+fit,z-.1,ce))
    usbw,usbh,depth=P.usb
    for key,port in L['ports'].items():
        xx,yy=port['x'],port['y']
        opening=box(xx-usbw/2-fit,xx+usbw/2+fit,yy-.1,y1+.1,top-fit,top+usbh+fit)
        shell=shell.cut(opening)
        sock=box(xx-usbw/2,xx+usbw/2,yy-depth,yy,top,top+usbh)
        sock=sock.cut(box(xx-usbw/2+P.socket_skin[0],xx+usbw/2-P.socket_skin[0],yy-depth+P.socket_skin[1],yy+.1,top+P.socket_skin[0],top+usbh-P.socket_skin[0]))
        add(key,('输入' if 'input' in key else '输出')+' USB-C 母座',g,'接口',sock,(0,18,13),mass=1.2,note='向 +y 插拔，包络占位，未含线缆胶头。')
    for i,key in enumerate(L['buttons']):
        xx,yy=key['x'],key['y']
        shell=shell.cut(cyl(xx,yy,ce-.1,2*(P.button_r+fit),P.wall+.2))
        add(f'key_{i+1}',key['name']+'键帽／柱',g,'接口',cyl(xx,yy,top,2*P.button_r,ce+P.wall+P.button_proud-top),
            (0,13,30),mass=.35,note='含开关的柱状占位。')
    k=L['indicators']; ax=[k['x'][0]+i*(k['x'][1]-k['x'][0])/(k['count']-1) for i in range(k['count'])]
    for i,xx in enumerate(ax,1):
        yy=k['y']; shell=shell.cut(cyl(xx,yy,ce-.1,2*(P.light_r+fit),P.wall+.2))
        add(f'light_{i}',f'电量导光柱 {i}',g,'乳白聚碳酸酯',
            cyl(xx,yy,ce-P.guide_inset,2*P.light_r,P.wall+P.guide_inset),(0,13,30))
    shell=shell.cut(box(features['sx'],features['SX'],y0-.1,y-fit+.1,top-.2,top+3.2))
    ax0,ax1,bz0,bz1=features['battery_exit']
    shell=shell.cut(box(ax0,ax1,y0-.1,y-fit+.1,bz0,bz1))
    # 调试焊盘仅在拆罩后接触，不在正式壳体上留常开探针孔。
    for k in B['main']['keepouts']:
        if not k['id'].startswith('CLIP'):continue
        ax0,ax1,ay0,ay1=absrect(B['main'],k['rect'])
        if ax0<x+1:ax0=x-fit-.4
        else:ax1=X+fit+.4
        shell=shell.fuse(box(ax0,ax1,ay0,ay1,top,ce+.1))
    q=ridge_path(L,P); yy=105.9; shelf=9.5+CAP_IN
    shell=shell.fuse(box(59.4,x1,yy-1.95,yy+1.95,shelf-P.insert_l,ce+.1)).cut(cyl(61.6,yy,shelf-P.insert_l,P.insert_d,ce+2-shelf+P.insert_l),box(56.7,64,yy-1.8,yy+1.8,shelf,ce+2),strip(q,RX-3.65,7.3,-1.43,1.43),strip(q,50.45,7.65,CAP_IN-.1,CAP_OUT+.1))
    shell=shell.cut(box(57.65,59.2,yy-1.45,yy+1.45,shelf,18))
    shell=shell.cut(parts['ridge_cover']['sh'])
    for i in range(len(ax)):shell=shell.cut(cyl(ax[i],L['indicators']['y'],ce-P.guide_inset,2*(P.light_r+fit),P.guide_inset+P.wall+.2))
    add('board_hood','主板罩 · 底边双口','壳架','PETG',shell,(0,13,23),'按键面朝平台；母座两窗局部支撑。')
    add('main_board','电源与控制主板',g,'FR-4',board_shape(B['main']),(0,13,9),
        note='估重含小器件余量，不含另列的母座与按键。')
    features.update(board_ce=ce,board_z=bz)

def board_items():
    # 使 PCB 工程师可直接用 STEP 的器件最大实体做干涉检查。
    for key,b in B.items():
        plane=b['origin'][2]+b['thickness']
        for it in b['connectors']+b['fixed']:
            if it['node'] in parts:continue
            if it.get('shape')=='circle':continue
            shape=box(*absrect(b,it['rect']),plane,plane+it['height'])
            add(it['node'],it.get('type',it.get('name',''))+' · '+it['ref'],'电路板','接口',shape,
                (0,12,16) if key=='main' else (0,-23,-19 if key=='driver' else 21),
                mass=(1.8 if it['ref'] in ('L_W','L_C') else 0),note='结构占位；非供应商 STEP。连接件重量计入板级预算。')
    b=B['main'];z=b['origin'][2]+b['thickness']
    for item in b['fixed']:
        if item['node'].startswith('light_'):
            sh=box(*absrect(b,item['rect']),z,z+item['height'])
            add('smd_'+item['node'],item['ref']+' 电量贴片灯','电路板','封装',sh,(0,13,12),mass=0,note='与导光柱同轴；质量已含在主板小器件中。')
    # 螺钉头最大占位，螺纹啮合不参加硬干涉；其余金属辅料仍计在重量预算。
    b=B['led'];z=b['origin'][2]+b['thickness']
    caps=[cyl(*xy(b,h['center']),z,h['keep_d'],1.55) for h in b['holes']]
    add('led_fasteners','M2.5 紧固头上限 · 四处','灯头','接口',pack(*caps),(0,-23,20),mass=0,note='Ø4.0 小头包络（待采购），禁用大垫圈；重量已计辅料。')
    for r in remote_devices(B,features,P,L):
        x,y,z=r['xyz'];w,l,h=r['size'];nz=r['normal'][2]
        sh=box(x-w/2,x+w/2,y-l/2,y+l/2,min(z,z+nz*h),max(z,z+nz*h))
        add(r['ref'].lower(),r['name'],'电池仓' if r['board']=='main' else '灯头','接口',sh,(0,8,18) if r['board']=='main' else (0,-23,-6),mass=.15 if r['board']=='main' else 1.0,note='尺寸为采购上限，需用实际元件和绝缘固定件复核。')
    add('harness_bundle','主驱线束 · 满包络','颈部','线束包络',bundle_solid(),(15,0,5),mass=0,note='两对双绞＋八芯。显示到两端分线区；重量已计入辅料。')

def make():
    parts.clear(); features.clear()
    for fn in (chassis,lamp,power,controls,board_items):
        fn()
    return parts,features
