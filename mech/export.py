"""从同一套 B-rep 输出制造文件、米制 glTF、检验记录及查看器数据。"""
from model import *
from itertools import combinations
from coupons import samples
from hashlib import sha256
import numpy as np
import trimesh
import shutil
from build123d import export_step, export_stl, import_step
from trimesh.visual.material import PBRMaterial

OUT=ROOT/'mech/out'; WEB=ROOT/'web/models'
EPS=1e-4; VOL_EPS=.001
def bounds(s):
    b=s.bounding_box()
    return np.array([list(b.min),list(b.max)])
def native_shape(s):
    # 不复用 Compound 的装配 children：镜像只变换 B-rep，旧子树位置不会跟着变。
    solids=s.mirror(Plane.XZ).solids()
    return solids[0] if len(solids)==1 else Compound(list(solids))
def vol(s): return sum(q.volume for q in s.solids())
def inter(a,b): return sum(vol(s) for s in (a.intersect(b) or []))
def strong(c): return '通过' if c else '不通过'
def nd(a): return [round(float(x),3)+0. for x in a]
def fmtp_local(a): return ", ".join(f"{x:.2f}" for x in a)
def fmt(a): return ' × '.join(f'{x:.2f}' for x in a)
def write(p,s): p.write_text(s,encoding='utf-8')
def build():
    OUT.mkdir(exist_ok=True); WEB.mkdir(exist_ok=True,parents=True); make()
    print(f'已构建 {len(parts)} 个零件节点')
    rows=[]; g=trimesh.Scene(base_frame='assembly'); bb={}; mesh_stats={}; native={}
    for id,p in parts.items():
        sh=p['sh']
        # 物理导出只变换一次：三种载体均为右手系 (x,-y,z)，避免镜像打印。
        solid=native[id]=native_shape(sh); solid.label=id; solid.color=sh.color
        bb[id]=q=bounds(sh); size=q[1]-q[0]; v=vol(sh); mat=p['material']
        mass=v*MAT[mat][1]/1000; basis='体积 × 密度'
        if id in ('main_board','driver_board'):
            extra=3.2 if id=='main_board' else 2.6
            mass+=extra; basis=f'裸板密度＋器件 {extra:.1f} g'
        if p['override'] is not None:
            mass=p['override']; basis='不计入' if p['group']=='手机参照' else '单件预算'
        row={k:p[k] for k in ('id','name','group','material','color','orientation','explode','note')}
        row.update(size=nd(size),bounds=[nd(t) for t in q],volume=round(v,2),mass=round(mass,3),basis=basis)
        rows.append(row)
        verts,faces=sh.tessellate(.065,.19)
        # 接口 y 向下，glTF y 向上：反射后翻转面序；glTF 顶点单位为 m。
        mesh=trimesh.Trimesh(np.array([tuple(v) for v in verts])*[.001,-.001,.001],np.asarray(faces)[:,::-1],process=False)
        color=list(bytes.fromhex(p['color'][1:]))+[220 if id=='diffuser' else 255]
        mesh.visual=trimesh.visual.TextureVisuals(material=PBRMaterial(name=id,baseColorFactor=color,
            metallicFactor=.58 if mat in ('铝','弹片','接口') else .08,
            roughnessFactor=.5 if mat not in ('电芯','乳白聚碳酸酯') else .36,
            alphaMode='BLEND' if id=='diffuser' else 'OPAQUE',doubleSided=False))
        g.add_geometry(mesh,node_name=id,geom_name=id)
        if p['orientation']:
            assert export_step(solid,OUT/(id+'.step'))
            assert export_stl(solid,OUT/(id+'.stl'),tolerance=.045,angular_tolerance=.16)
            # 按拓扑实体而非逐面三角化求体积；另验磁盘上的 STL 是否闭合。
            loaded=trimesh.load_mesh(OUT/(id+'.stl'))
            mesh_stats[id]=(loaded.is_watertight and loaded.is_volume and len(loaded.split())==1)
            assert mesh_stats[id],(id,'STL 非闭合单实体')
    group=Compound(label='Filllight_15Pro',children=list(native.values()))
    assert export_step(group,OUT/'assembly.step')
    glb=WEB/'filllight.glb'; glb.write_bytes(g.export(file_type='glb',include_normals=True))
    restored=trimesh.load_scene(glb); assert set(restored.graph.nodes_geometry)==set(parts)
    print('制造格式及 GLB 已导出，开始核对实际实体')
    checks=[]
    def ck(name,test,measured): checks.append(dict(name=name,ok=bool(test),value=measured))
    def sh(i): return parts[i]['sh']
    k=L['head']; pod=L['pod']; n=L['neck']; f=features
    headids=[i for i,p in parts.items() if p['group']=='灯头' or i in ('driver_board','led_board','led_warm','led_cool') or i.startswith(('driver_','led_'))]
    def envelope(ids):
        return np.stack((np.min([bb[i][0] for i in ids],axis=0),np.max([bb[i][1] for i in ids],axis=0)))
    head=envelope(headids); podbox=envelope(['battery_tray','battery_lid','cell_1','cell_2'])
    assembly=envelope(parts); A=assembly[1]-assembly[0]
    gap=-head[1,1]; depth=head[1,2]-head[0,2]; rear=head[1,2]; front=-T-head[0,2]
    eq=lambda a,b: np.allclose(a,b,rtol=0,atol=EPS)
    ck('灯头平面与顶边距离',eq(head[:,0],k['x']) and eq(head[:,1],k['y']) and eq(gap,k['gap_above_top_edge']) and gap+EPS>=D['head_gap_above_top_edge_min'],
       f'x {head[0,0]:.1f}…{head[1,0]:.1f}；y {head[0,1]:.1f}…{head[1,1]:.1f}；间距 {gap:.2f} mm')
    ck('灯头前后突出量',rear<=min(k['z_rear_max'],D['head_z_rear_max_at_gap_12'])+EPS and front<=min(k['z_front_max_above_screen'],D['head_z_front_max_above_screen_at_gap_12'])+EPS,
       f'背玻璃以上 {rear:.2f} / 屏幕以外 {front:.2f} mm')
    ck('灯头总深',depth<=min(k['depth_max'],D['head_depth_max_at_gap_12'])+EPS,
       f'{depth:.2f} mm；布局上限 {k["depth_max"]:.1f}，现间距推导上限 {D["head_depth_max_at_gap_12"]:.1f}；未使用 15 mm 间距的 {D["head_depth_max_at_gap_15"]:.1f} mm 放宽值')
    q=bb['neck']; thick=q[1,2]-q[0,2]
    ck('颈部范围与厚度',eq(q[:,0],n['x']) and eq(q[:,1],n['y']) and eq(thick,n['thickness']),
       f'x {q[0,0]:.1f}…{q[1,0]:.1f}，y {q[0,1]:.1f}…{q[1,1]:.1f}，厚 {thick:.2f} mm')
    sx,SX,sz,SZ=(f[q] for q in ('sx','SX','sz','SZ'))
    cable=sh('harness_bundle');cb=inter(cable,sh('neck'))
    ck('扁线通道与两端开口',SX-sx<=n['harness_width_max'] and cb<VOL_EPS,f'左侧 x {sx:.2f}…{SX:.2f}；孔宽 {SX-sx:.2f} mm；改走外脊，线束与颈重叠 {cb:.3f} mm³')
    q=podbox
    ck('电池仓外包络',eq(q[:,0],pod['x']) and eq(q[:,1],pod['y']) and eq(q[1,2]-q[0,2],pod['thickness']) and q[0,1]+EPS>=D['pod_top_y_min'],
       f'x {q[0,0]:.1f}…{q[1,0]:.1f}；y {q[0,1]:.1f}…{q[1,1]:.1f}；厚 {q[1,2]-q[0,2]:.2f} mm（相对背玻璃最高 {q[1,2]:.2f} mm）')
    axes=[midpoint(bb[i][:,1]) for i in ('cell_1','cell_2')]
    ck('两节电芯轴线',eq(axes,pod['cell_axis_y']) and min(axes)+EPS>=D['pod_cell_axis_y_min'],f'y {axes[0]:.2f} / {axes[1]:.2f} mm；轴向 x，标称 Ø{P.cell_d} × {P.cell_l}')
    ck('仓底与接口基线',eq(f['base'],pod['base']),f'实壁 {f["base"]:.2f} mm，接口 {pod["base"]:.2f} mm；按本轮恢复 1.0 mm，为通用 1.2 mm 打印壁厚的明确例外')
    maxl=pod['cell_length_range'][1]; xd=midpoint(pod['x']); maxd=pod['cell_d_max']
    excess=0
    for yy in axes:
        gauge=cyl(xd-maxl/2,yy,f['zc'],maxd,maxl,(1,0,0))
        excess+=sum(inter(gauge,sh(i)) for i in ('battery_tray','battery_lid'))
    slack=[(pod['x'][1]-pod['x'][0]-2*pod['wall']-v)/2 for v in pod['cell_length_range']]
    ck('最大电芯硬壳净空',excess<VOL_EPS,f'Ø{maxd} × {maxl} 量规与仓/盖重叠 {excess:.3f} mm³；最短至最长芯每端留 {slack[0]:.2f}…{slack[1]:.2f} mm 给弹片（行程和压力未实测）')
    wx,wy=k['window']['size']; cx,cy=k['window']['center']
    # 压圈平面处量窗：通规可通过，宽、高各增大 0.2 的止规均触碰。
    def window_test(a,b):
        return inter(box(cx-a/2,cx+a/2,cy-b/2,cy+b/2,f['lens_base']-P.wall+.1,f['lens_base']-.1),sh('head_bezel'))
    mix=bb['diffuser'][0,2]-bb['led_warm'][1,2]
    ck('发光窗口与混光层',window_test(wx-.02,wy-.02)<VOL_EPS and min(window_test(wx+.2,wy),window_test(wx,wy+.2))>VOL_EPS and eq(mix,P.mix),
       f'窗 {wx:g} × {wy:g}，柔光片厚 {bb["diffuser"][1,2]-bb["diffuser"][0,2]:.2f}，灯珠至片 {mix:.2f} mm')
    ls=L['led_board']; ledsize=bb['led_board'][1]-bb['led_board'][0]
    leds=np.array([bounds(s).mean(axis=0) for node in ('led_warm','led_cool') for s in sh(node).solids()])
    xx,yy=[np.unique(leds[:,i].round(4)) for i in (0,1)]
    ck('灯板与阵列',eq(ledsize,[*ls['size'],ls['pcb_thickness']]) and eq([len(xx),len(yy)],ls['grid']) and eq(np.diff(xx),ls['pitch'][0]) and eq(np.diff(yy),ls['pitch'][1]),
       f'{fmt(ledsize)} mm，{len(xx)} × {len(yy)} = {len(leds)} 颗；节距 {fmt(ls["pitch"])} mm')
    ds=bb['driver_board'][1]-bb['driver_board'][0]; fanxy=bb['fan'].mean(axis=0)[:2]; fs=bb['fan'][1]-bb['fan'][0]
    ck('驱动板与散热叠层',eq(ds,[*L['driver_board']['size'],L['driver_board']['pcb_thickness']]) and eq(fs[:2],k['fan']['size']) and eq(fanxy,k['fan']['center']) and f['fb']>f['drive_top'] and f['drive_lo']>f['cap'],
       f'驱动板 {fmt(ds)} mm；风扇 {fmt(fs)} mm，中心 ({fanxy[0]:.1f}, {fanxy[1]:.1f})；鳍片＋风扇 {P.sink_h+fs[2]:.2f} mm；驱动裸板至风扇/盖 {f["fb"]-f["drive_top"]:.2f}/{f["drive_lo"]-f["cap"]:.2f} mm')
    mb=L['main_board']; q=bb['main_board']; headroom=f['board_ce']-q[1,2]
    ck('主板放置及器件空间',eq(q[:,0],mb['x']) and eq(q[:,1],mb['y']) and eq(q[1]-q[0],[mb['x'][1]-mb['x'][0],mb['y'][1]-mb['y'][0],mb['pcb_thickness']]) and eq(headroom,mb['height_out_max']),
       f'x {q[0,0]:.1f}…{q[1,0]:.1f}，y {q[0,1]:.1f}…{q[1,1]:.1f}，厚 {q[1,2]-q[0,2]:.2f}；罩内朝外净高 {headroom:.2f} mm')
    port_ok=True; pos=[]
    for id,pt in L['ports'].items():
        q=bb[id]; xx=q.mean(axis=0)[0]; yy=q[1,1]; pos.append(f'({xx:g}, {yy:g})')
        probe=box(q[0,0],q[1,0],yy,bb['board_hood'][1,1]+1,q[0,2],q[1,2])
        port_ok &= eq([xx,yy],[pt['x'],pt['y']]) and pt['facing']=='+y' and inter(probe,sh('board_hood'))<VOL_EPS
    ck('双 USB-C 插拔口',port_ok,' / '.join(pos)+' mm，沿 +y 直通，未计插头胶壳')
    keys=[bb[i].mean(axis=0)[:2] for i in parts if i.startswith('key_')]
    lights=[bb[i].mean(axis=0)[:2] for i in parts if i.startswith('light_')]
    kx=L['indicators']; ins=[('key_'+str(i+1)) for i in range(len(keys))]+['light_'+str(i+1) for i in range(len(lights))]
    ck('按键与电量灯',eq(keys,[[p['x'],p['y']] for p in L['buttons']]) and eq([a[0] for a in lights],np.linspace(*kx['x'],kx['count'])) and eq([a[1] for a in lights],kx['y']) and all(inter(sh('board_hood'),sh(i))<VOL_EPS for i in ins),
       f'键 x {", ".join(f"{a[0]:g}" for a in keys)}；灯 x {", ".join(f"{a[0]:g}" for a in lights)}，共线 y {keys[0][1]:g} mm')
    ck('开放四角及打印壁',P.clip_span<=12 and min(P.wall,P.liner,pod['wall'],f['base'],P.jaw,P.head_wall)>=1.2 and all(mesh_stats.values()),
       f'角夹沿边 {P.clip_span:g} mm；侧/底边中段分别敞开 {H-2*P.clip_span:.1f}/{W-2*P.clip_span:.1f} mm；仓底实壁 {f["base"]:.1f}（指定例外），其余设计壁 {P.wall:.1f} mm，{len(mesh_stats)} 个打印网格闭合（非逐点测厚）')
    # 功率高度分别以整区 3D 量规检查；装配高度以板铜面为起点，不能只用 PCB 外框做推断。
    driver=B['driver']; plane=bb['driver_board'][1,2]; obstacles=['fan','head_shell','head_grille','heatsink','ts85']
    for zone in driver['height_zones'][1:]:
        reg=absrect(driver,zone['rect']);top=zone['top']
        gauge=box(*reg,plane,plane+top)
        overlap=sum(inter(gauge,sh(obj)) for obj in obstacles)
        # 从同一块区域的板面向 +Z 探测首次碰到真实障碍的高度，二分到 0.01。
        lo,hi=0.,22.
        for _ in range(12):
            mm=(lo+hi)/2; probe=box(*reg,plane,plane+mm)
            hit=any(inter(probe,sh(obj))>VOL_EPS for obj in obstacles if bb[obj][1,2]>plane and bb[obj][0,2]<plane+mm)
            if hit:hi=mm
            else:lo=mm
        zone['static_contact_top']=round((lo+hi)/2,2)
        overlaps_fan=(reg[0]<bb['fan'][1,0] and reg[1]>bb['fan'][0,0] and reg[2]<bb['fan'][1,1] and reg[3]>bb['fan'][0,1])
        safe=min((lo+hi)/2,bb['fan'][0,2]-plane) if overlaps_fan else (lo+hi)/2
        zone['clearance_top']=round(safe,2)
        ck(zone['id']+' 工作高度',overlap<VOL_EPS and safe+.01>=top,f'全区 {reg[1]-reg[0]:.1f} × {reg[3]-reg[2]:.1f} mm；刚体首触 {round((lo+hi)/2,2):.2f}，不借用叶轮空间的实用净空 {safe:.2f} mm；工作限高 {top:.2f} mm，重叠 {overlap:.3f} mm³')
    ax0,ax1,bz0,bz1=f['battery_exit']; mb=L['main_board']
    bt=box(ax0+.02,ax1-.02,pod['y'][1]-pod['wall']-.1,mb['y'][0],bz0+.02,bz1-.02)
    bv=inter(bt,sh('board_hood'))+inter(bt,sh('battery_tray'))
    ck('电池七线出仓窗口',bv<VOL_EPS,f'独立开口 x {ax0:.2f}…{ax1:.2f} / z {bz0:.2f}…{bz1:.2f} mm，仓体至主板罩量规重叠 {bv:.3f} mm³')
    wiring=sh('harness_bundle')
    clashes=sum(inter(wiring,sh(i)) for i in ('frame','neck','head_shell','led_board','driver_board','fan','heatsink','battery_tray','board_hood','battery_lid','ridge_cover','cell_1','cell_2'))
    ck('双绞线束与两个弯段',clashes<VOL_EPS and 6.85<=P.slot_w<=n['harness_width_max'] and 2.4<=SZ-sz,
       f'量规 6.85 × 2.40，孔 {P.slot_w:.2f} × {SZ-sz:.2f} mm，宽/高总余量 {P.slot_w-6.85:.2f}/{SZ-sz-2.4:.2f} mm；头端两次 90°，中心 R5.00、内侧 R3.80；全路径重叠 {clashes:.3f} mm³。限定外径，厂商弯折数据待确认')
    for key,b in B.items():
        s=sh({'main':'main_board','led':'led_board','driver':'driver_board'}[key]);origin=b['origin']
        holes_ok=True
        for it in b['holes']:
            hx,hy=xy(b,it['center']);test=cyl(hx,hy,origin[2]-.01,it['drill']-.02,b['thickness']+.02)
            holes_ok &= inter(test,s)<VOL_EPS and inter(cyl(hx,hy,origin[2],it['drill']+.06,b['thickness']),s)>VOL_EPS
        ck(key+' 板位与实孔',eq(bounds(s)[0],[origin[0],origin[1]-b['size'][1],origin[2]]) and holes_ok,
           f"BOT 原点 ({fmtp_local(origin)})；{len(b['holes'])} 个实际通孔；厚 {b['thickness']:g} mm")
    for key,b in B.items():
        ok=True;nchecked=0
        for item in b['connectors']+b['fixed']:
            q=bb[item['node']];r=absrect(b,item['rect'])
            ok &= eq([q[0,0],q[1,0],q[0,1],q[1,1]],r);nchecked+=1
        ck(key+' 定位器件三维投影',ok,f'{nchecked} 个接口/固定件：实际 B-rep 的 XY 外包络逐个与 DXF 母数据相符；允许误差 {EPS:g} mm')
    for key,nodes in [('driver',[('head_shell',bb['driver_board'][1,2]+.1,P.insert_d),('head_grille',f['cap']+.1,P.bolt_d)]),
                      ('led',[('heatsink',bb['led_board'][0,2]-.8,2.05)])]:
        ok=True
        for hole in B[key]['holes']:
            xx,yy=xy(B[key],hole['center'])
            for node,zcheck,dia in nodes:
                ok &= inter(cyl(xx,yy,zcheck,dia-.02,.5),sh(node))<VOL_EPS and inter(cyl(xx,yy,zcheck,dia+.06,.5),sh(node))>VOL_EPS
        ck(key+' 孔柱同轴',ok,'四孔逐一通止规检查：'+('后盖通孔、壳内 M2 铜母肩均同轴' if key=='driver' else '铝散热器四只 M2.5 攻丝底孔均同轴'))
    from review03 import review
    from driver_fit import trial,compact
    B['driver']['rough_placement']=trial(B['driver'])
    B['driver']['compact_candidate']=compact(B['driver'])
    review(ck,L,P,f,bb,B,sh,inter)
    pairs=[]; tested=0
    for a,b in combinations(parts,2):
        if np.any(np.minimum(bb[a][1],bb[b][1])-np.maximum(bb[a][0],bb[b][0])<=EPS): continue
        tested+=1; overlap=inter(sh(a),sh(b))
        if overlap>VOL_EPS: pairs.append((a,b,overlap))
    ck('静态硬干涉',not pairs,f'{len(parts)*(len(parts)-1)//2} 对中 {tested} 对包围盒相交，精确布尔后 '+('; '.join(f'{a}/{b}: {v:.3f} mm³' for a,b,v in pairs) if pairs else '0 对实体重叠 > 0.001 mm³；贴合面不计'))
    ck('手机闪光灯共用',False,'现布局不让开手机闪光灯外侧照明范围；用本灯时关闭手机闪光灯。不发布、不模拟视场数据。')
    from pcb_draw import produce,DIR
    cad_checks=produce()
    checks+=cad_checks
    print('\n'.join(f'{strong(c["ok"])} | {c["name"]} | {c["value"]}' for c in checks))
    total=sum(r['mass'] for r in rows)+P.hw_allowance
    dims=[dict(id='gap',name='顶边间距',value=f'{gap:.1f} mm',a=[x,0,0],b=[x,-gap,0]) for x in [head[1,0]+2]]
    dims.extend([dict(id='depth',name='灯头深',value=f'{depth:.2f} mm',a=[head[0,0],k['y'][0],head[0,2]],b=[head[0,0],k['y'][0],head[1,2]]),
                 dict(id='pod',name='仓厚',value=f'{podbox[1,2]-podbox[0,2]:.1f} mm',a=podbox[1].tolist(),b=[podbox[1,0],podbox[1,1],podbox[0,2]]),
                 dict(id='overall',name='整机外形',value=fmt(A)+' mm',a=assembly[0].tolist(),b=[assembly[0,0],assembly[1,1],assembly[0,2]])])
    data=dict(version='0.3',units='mm',parts=rows,dimensions=dims,assemblyBounds=assembly.round(4).tolist(),
              totalMass=round(total,2),allowance=P.hw_allowance,checks=checks)
    write(WEB/'parts.json',json.dumps(data,ensure_ascii=False,indent=2,default=float)+'\n')
    md=['# 整机结构核算 · v0.3','',f'**附件增重：{total:.1f} g**（不计手机；含两节电芯 140 g 和未建模线束、铜母、螺钉、胶材 {P.hw_allowance:.1f} g）。含手机的整机外形：**{fmt(A)} mm**（x × y × z）。',
        '','本表是几何实测和质量预算，不是称重、热试验或 G5 实物验收。打印件按实体体积上界，不按切片填充率折减。PETG / ASA / TPU 密度为 1.27 / 1.07 / 1.21 g/cm³；铝 2.70、FR-4 1.85、乳白片 1.20、弹片 8.60。表中尺寸单位 mm，体积 cm³，质量 g。','',
        '| 零件（节点） | 材料 | 外形 x × y × z | 体积 | 增重 | 质量依据 |','|---|---|---:|---:|---:|---|']
    for r in rows:
        md.append(f'| {r["name"]}（{r["id"]}） | {r["material"]} | {fmt(r["size"])} | {r["volume"]/1000:.3f} | {r["mass"]:.2f} | {r["basis"]} |')
    md+=['','## 接口逐项复核','','| 项目 | 结论 | 实测 / 判据 |','|---|---|---|']+[f'| {c["name"]} | {strong(c["ok"])} | {c["value"]} |' for c in checks if c not in cad_checks]
    md+=['','## DXF 文件实体读回 · ezdxf','','| 项目 | 结论 | 实测 |','|---|---|---|']+[f'| {c["name"]} | {strong(c["ok"])} | {c["value"]} |' for c in cad_checks]
    md+=['','## 结构和质量代价','',
         f'- 灯头仍为 72 × 52 × {depth:.2f} mm，顶边间距 {gap:.2f} mm；三个外形方向增量均为 0，不动用 15 mm / 39 mm 备选。2 mm 柔光片改为外面齐平的台阶座，仍留 8 mm 混光间距。3030 高按 1.0 mm 包络而非实测。灯板及原有 12 × 6 网格整体向 −Y 调 1.10 mm，局部坐标和节距不变；为底边绕线井让位。',
         f'- 驱动板 TOP 朝风扇，BOT 距格栅 {f["drive_lo"]-f["cap"]:.2f} mm；后盖支台与壳框带铜母肩锁四孔。风扇向铝片嵌入 {P.fan_recess:.1f} mm，全高散热片 {P.sink_h:.1f} mm；风扇范围内鳍高由 {P.sink_h-P.fin_base:.1f} 降为 {P.sink_h-P.fin_base-P.fan_recess:.1f} mm。两路各预留 10 × 10 × 5.5 mm 电感和 5.5 mm 工作层，面积/铜损/风阻尚未验证。降温能力可能下降，不能据此放行 20 W。',
         f'- v0.2 为 306.09 g，本版 {total:.2f} g，变化 {total-306.09:+.2f} g。删除 5.5 mm 抬座；恢复 1.0 mm 底壁。脊盖和仓体最高点分开统计。',
         '- 主驱功率采用两对 VSYS/GND 双绞（1↔3、2↔4）；假定绝缘外径 ≤1.10 mm，八根信号 ≤0.65 mm 作三列叠放。带包覆量规 6.85 × 2.4，仓上沿局部去外包带并用侧梳限位，截面 6.85 × 2.20；不得再叠绝缘带。路线到分线区止。线规、载流、压接后拉力、最小允许弯半径和分支装配均需线厂打样；不许以截面通过代替电气签核。',
         '- 灯板：Ø5 圈留在板内时，最近 3030 的横纵净距至多分别为 1.25 和 2.30；斜距上界 2.618，仅移孔不可能得到 3.0 mm。保留对称孔和散热器攻丝，提案 Ø4.0 小头禁圈，名义间隙 0.618 mm；Ø2.8 通孔每侧承压宽仅 0.60 mm。需确认公差、采购、锁付扭矩与铝基板承压；未签核不能用普通螺钉替代。',
         '- 3.7 A 若须满足断一针后仍 ≤70% 额定，仅按 5 A 下限会到 74%；忽略其余负载也至少需 3.7/0.7≈5.29 A。电气侧应核实总电流、配对端子和降额，或提出故障关断，不改 2×2 线序。',
         '- 主板 10 mm 竖装座比硬上限多 2 mm；预留低矮卧座及水平插拔区，含插合体目标 7.5 mm。驱动板功率座位于风扇外侧高区，8.0 mm 占位，工作限高见分区。风扇 5 V 在驱动板本地产生。PCB 结构表、网名和备注见 ../pcb/README.md。']
    md+=['','## 边界与下一步','','- 只核现版简化实体。上部驱动板朝风扇一侧预留器件层，背侧仅留薄绝缘胶；不能据裸板无交叠判为可装；拿到厂商 STEP 后复核真实元件、插头和线尾再定版。不要直接加深现灯头。',
         '- 线束跨顶部并经过指南针附近，钢壳电芯与电感有磁干扰风险；电池仓遮蔽背部线圈，背面明显加厚。不支持无线充电与 MagSafe；实测防抖、指南针、无线与 0.5× / 1× / 3× 取景。',
         '- 模型没有精确传感器位置，不能证明风扇到镜头／指南针的 45 mm 指标。风量、器件温度、1 kg 侧向载荷、端口胶头、紧固件突出和滑盖寿命待实测。具体装配与试片见 ../README.md。','']
    write(OUT/'report.md','\n'.join(md))
    # 重开关键输出，拒绝缺件、错名或截断；报告保留偏离，不把偏离当布尔错误。
    reread=import_step(OUT/'assembly.step')
    def physical(q):
        return [[q[0,0],-q[1,1],q[0,2]],[q[1,0],-q[0,1],q[1,2]]]
    assert eq(bounds(reread),physical(assembly))
    step_nodes={child.label:child for child in reread.children}
    assert set(step_nodes)==set(parts),set(parts)^set(step_nodes)
    for i,shape in step_nodes.items():
        assert eq(bounds(shape),physical(bb[i])) and eq(vol(shape),vol(parts[i]['sh'])),i
    copy=DIR/'enclosure_assembly.step'
    if (OUT/'assembly.step').stat().st_size<=8_000_000:
        shutil.copyfile(OUT/'assembly.step',copy);assert sha256(copy.read_bytes()).digest()==sha256((OUT/'assembly.step').read_bytes()).digest()
    else:
        small=Compound(label='ECAD_Envelope',children=[native[i] for i in native if parts[i]['orientation'] or i in ('driver_board','main_board','led_board','fan','heatsink','cell_1','cell_2')])
        assert export_step(small,copy) and copy.stat().st_size<=8_000_000
    ecad_nodes={child.label:child for child in import_step(copy).children}
    for k,i in [('main','main_board'),('driver','driver_board'),('led','led_board')]:
        assert eq(bounds(ecad_nodes[i]),physical(bb[i])) and eq(vol(ecad_nodes[i]),vol(sh(i)))
    for i in mesh_stats: assert eq(bounds(import_step(OUT/(i+'.step'))),physical(bb[i]))
    assert len(json.loads((WEB/'parts.json').read_bytes())['parts'])==len(parts)
    assert all(c['name'] in (OUT/'report.md').read_text() for c in checks)
    print(f'{len(mesh_stats)} 套 STEP/STL；总增重 {total:.1f} g；GLB {glb.stat().st_size:,} B')
    failed=[c['name'] for c in checks if not c['ok'] and c['name'] not in ('开放四角及打印壁','手机闪光灯共用','双路最大器件实体试排')]
    if failed: raise RuntimeError('装配检查未通过：'+'、'.join(failed))
    trials=OUT/'coupons';trials.mkdir(exist_ok=True)
    for i,shape in samples().items():
        solid=native_shape(shape);solid.label=i
        assert solid.is_valid and len(solid.solids())==1,i
        assert export_step(solid,trials/(i+'.step'))
        assert export_stl(solid,trials/(i+'.stl'),tolerance=.045,angular_tolerance=.16)
        mesh=trimesh.load_mesh(trials/(i+'.stl'))
        assert mesh.is_volume and mesh.is_watertight and len(mesh.split())==1,i
        assert eq(bounds(import_step(trials/(i+'.step'))),bounds(solid)),i
    print('三组试片、六个实体已导出并回读。')
    index=OUT/'files.md'
    files=sorted(f for directory in (ROOT/'mech',ROOT/'web') for f in directory.rglob('*')
                 if f.is_file() and f!=index and not any(n.startswith('.') or n=='__pycache__' for n in f.relative_to(ROOT).parts))
    table=['# 交付清单','', '相对仓库根目录；文件大小为实际字节数。清单自身不参与哈希。','',
           '| 路径 | 字节 | SHA-256 |','|---|---:|---|']
    for path in files:
        body=path.read_bytes()
        table.append(f'| `{path.relative_to(ROOT)}` | {len(body)} | `{sha256(body).hexdigest()}` |')
    write(index,'\n'.join(table)+'\n')
    assert index.read_text().count(' | `')==len(files)
if __name__=='__main__': build()
