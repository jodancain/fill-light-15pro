"""ECAD 交换：写真实 R2010 实体，按实体读回后渲染和核验。禁止读取任何硬件或手机图纸。"""
from pathlib import Path
import os,json,math,shutil
from collections import Counter
from hashlib import sha256
from model import ROOT,L,D,P,B,W,H,SPEC,parts,features,xy,absrect,bundle_path,remote_devices
CACHE=ROOT/'mech/out/.cache'
os.environ.setdefault('MPLCONFIGDIR',str(CACHE/'mpl'))
os.environ.setdefault('XDG_CACHE_HOME',str(CACHE))
import ezdxf
from ezdxf import units
from ezdxf.path import make_path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle
import numpy as np
DIR=ROOT/'mech/pcb'
LAY={'BOARD_OUTLINE':('#233729','成品板边'),'HOLES':('#965119','钻孔 / 紧固禁区'),'CONNECTORS':('#105794','接口 / 针一'),
     'FIXED_PARTS':('#67388e','固定器件中心'),'LED_ARRAY':('#a55811','3030 阵列'),'KEEPOUT_TOP':('#bf3342','正面禁布'),
     'KEEPOUT_BOTTOM':('#85643d','背面禁布'),'HEIGHT_LIMIT':('#168072','分区限高'),'DIMENSIONS':('#46677c','尺寸'),
     'NOTES':('#3c4942','说明'),'PHONE_REF':('#86938b','公开手机外形'),'ENCLOSURE':('#64877a','壳体 / 电芯'),
     'HARNESS':('#b54732','线束走向')}
APP='FILL_LIGHT'; SZ=75
def setup():
    d=ezdxf.new('R2010');d.units=units.MM;d.header['$MEASUREMENT']=1;d.appids.new(APP)
    st=d.styles.new('CN',dxfattribs={'font':'STHeiti Medium.ttc'});st.set_extended_font_data('Heiti SC')
    aci=dict(zip(LAY,[3,30,5,200,40,1,32,4,150,7,8,92,12]))
    for layer,(color,_) in LAY.items():
        item=d.layers.new(layer,dxfattribs={'color':aci[layer]});item.rgb=tuple(bytes.fromhex(color[1:]))
    return d,d.modelspace()
def tag(e,role,ref=''):
    e.set_xdata(APP,[(1000,role),(1000,ref)]);return e
def info(e):
    if e.has_xdata(APP):
        a=e.get_xdata(APP);return a[0].value,a[1].value
    return '',''
def att(layer):return {'layer':layer}
def ln(m,l,a,b,role='line',ref=''):return tag(m.add_line(a,b,dxfattribs=att(l)),role,ref)
def text(m,l,pos,s,h=.9,ref=''):
    return tag(m.add_text(str(s),dxfattribs={**att(l),'style':'CN','height':h,'insert':pos}),'text',ref)
def circle(m,l,c,r,role,ref):return tag(m.add_circle(c,r,dxfattribs=att(l)),role,ref)
def rect(m,l,r,role,ref):
    x,y,X,Y=r;return tag(m.add_lwpolyline([(x,y),(X,y),(X,Y),(x,Y)],close=True,dxfattribs=att(l)),role,ref)
def rounded(m,l,w,h,r,role,ref,x=0,y=0):
    if not r:return rect(m,l,[x,y,x+w,y+h],role,ref)
    t=math.tan(math.pi/8)
    pts=[(r,0,0),(w-r,0,t),(w,r,0),(w,h-r,t),(w-r,h,0),(r,h,t),(0,h-r,0),(0,r,t)]
    return tag(m.add_lwpolyline([(a+x,b+y,c) for a,b,c in pts],format='xyb',close=True,dxfattribs=att(l)),role,ref)
def cross(m,l,c,s=.55):
    x,y=c;ln(m,l,(x-s,y),(x+s,y));ln(m,l,(x,y-s),(x,y+s))
def arrow(m,l,c,v):
    x,y=c;a,b,_=v
    if not(a or b):
        circle(m,l,(x,y),.43,'top','');circle(m,l,(x,y),.10,'top','');return
    X=x+1.6*a;Y=y+1.6*b
    ln(m,l,c,(X,Y))
    for sg in [-1,1]:ln(m,l,(X,Y),(X-.65*a+sg*.32*b,Y-.65*b-sg*.32*a))
def dim(m,p1,p2,base,angle):
    a=m.add_linear_dim(base=base,p1=p1,p2=p2,angle=angle,dxfattribs=att('DIMENSIONS'),
        override={'dimtxt':1.05,'dimasz':.72,'dimgap':.25,'dimexe':.6,'dimexo':.25,'dimdec':2,'dimtad':1});a.render()
def fmtp(c):return ', '.join(f'{x:g}' for x in c)
def nets(it):return ' / '.join(n if n is not None else '待定' for n in it['nets'])
def direction(v):return {(0,0,1):'+Z',(0,1,0):'+v',(0,-1,0):'−v',(-1,0,0):'−u'}[tuple(v)]
def save(d,path):
    d.set_modelspace_vport(height=98,center=(60,21));d.saveas(path)
def board_dxf(b):
    d,m=setup();w,h=b['size'];name=b['id'];rounded(m,'BOARD_OUTLINE',w,h,b['corner_radius'],'outline',name)
    for hole in b['holes']:
        for role,k in [('drill','drill'),('hardware','keep_d')]:
            circle(m,'HOLES',hole['center'],hole[k]/2,role,hole['ref'])
        for l in ['KEEPOUT_TOP','KEEPOUT_BOTTOM']:circle(m,l,hole['center'],hole['keep_d']/2,'no_copper_parts',hole['ref'])
        cross(m,'HOLES',hole['center'],.42)
    for keep in b['keepouts']:
        rect(m,'KEEPOUT_'+keep['side'],keep['rect'],keep['mode'],keep['id'])
    for i,z in enumerate(b['height_zones']):
        r=z['rect'];rect(m,'HEIGHT_LIMIT',r,'height',z['id'])
        # 总区标签采用引线以免遮挡焊盘；局部文字均在本分区内。
        a=(r[0]+.4,r[1]+.30) if i else (.4,.25)
        text(m,'HEIGHT_LIMIT',a,f"{z['id']}  TOP ≤ {z['top']:g} mm / BOT ≤ {z['bot']:g} mm",.40 if name=='driver' and i else .57,z['id'])
    for it in b['connectors']:
        r=it['rect'];ref=it['ref'];x,y=it['center']
        rect(m,'CONNECTORS',r,'part',ref)
        if it['pattern']=='usb':rect(m,'FIXED_PARTS',r,'usb',ref);cross(m,'FIXED_PARTS',it['center'])
        circle(m,'CONNECTORS',it['pin1'],.29,'pin1',ref)
        for i,pt in enumerate(it['pins']):
            if pt is not None:cross(m,'CONNECTORS',pt,.18)
        text(m,'CONNECTORS',(it['pin1'][0]+.3,it['pin1'][1]+.2),'1',.55)
        text(m,'CONNECTORS',(r[0]+.28,r[1]+.24),ref,.68)
        arrow(m,'CONNECTORS',(x+.25,y+.28),it['direction'])
    for it in b['fixed']:
        rect(m,'FIXED_PARTS',it['rect'],'part',it['ref']);cross(m,'FIXED_PARTS',it['center'])
        x,y=it['center'];text(m,'FIXED_PARTS',(it['rect'][0]+.13,y+.3),it['ref'],.55)
    for e in b['leds']:
        rect(m,'LED_ARRAY',e['rect'],'led',e['ref']);cx,cy=e['center']
        text(m,'LED_ARRAY',(cx-.87,cy+.18),e['string']+'.'+str(e['order']),.55,e['ref'])
        for sym,k in [('+','anode'),('−','cathode')]:
            xx,yy=e[k];text(m,'LED_ARRAY',(xx-.20,yy-.61),sym,.53,e['ref'])
    dim(m,(0,0),(w,0),(0,-5),0);dim(m,(0,0),(0,h),(-5,0),90)
    if b['holes']:
        x,y=b['holes'][0]['center'];X,Y=b['holes'][-1]['center']
        dim(m,(x,Y),(X,Y),(x,h+3.8),0);dim(m,(x,y),(x,Y),(-9,y),90)
        dim(m,(0,0),(x,y),(0,-8.3),0);dim(m,(w,0),(X,y),(w+4,0),90)
    sx=w+9;sy=h+8
    text(m,'NOTES',(0,h+9),b['name']+'  /  '+name.upper(),2.2)
    text(m,'NOTES',(sx,sy),'接口索引  /  尺寸单位 mm',1.45)
    for it in b['connectors']:
        sy-=3.5;text(m,'CONNECTORS',(sx,sy),f"{it['ref']}   {it['type']}   ({fmtp(it['center'])})   {direction(it['direction'])}",.97)
        sy-=1.7;text(m,'CONNECTORS',(sx,sy),nets(it),.68,it['ref']+'_nets')
    if name=='driver':
        for line in [b['stack_note'],'每路最大裸体面积 298.66 mm²；高区 252.8 mm²，低件需外排。',f"双路试排 最大包络 {2+len(b['rough_placement'])}/26；7×7 电感、小 PMOS {2+len(b['compact_candidate']['other_parts'])}/26，详见 JSON。"]:
            sy-=2.1;text(m,'NOTES',(sx,sy),line,.82)
    for s in [f"{b['layers']} 层 / {b['material']} / 厚 {b['thickness']:g} / R{b['corner_radius']:g}",
              f"整机坐标：X={b['origin'][0]:g}+u；Y={b['origin'][1]:g}−v；BOT Z={b['origin'][2]:g}；TOP 朝 +Z",
              '圆形标记为 1 脚；箭头为插拔 / 出线；圆点套圈为朝 +Z。','钻孔与禁铜圈分开；请只将 BOARD_OUTLINE 导入板边。',
              '型号、落脚图与配对插头由电气确认；不可按占位轮廓制焊盘。']:
        sy-=2.35;text(m,'NOTES',(sx,sy),s,.82)
    for z in b['height_zones']:
        if 'clearance_top' in z:
            sy-=2.05;text(m,'HEIGHT_LIMIT',(sx,sy),f"{z['id']}  全区净空 {z['clearance_top']:.2f} mm；发板工作限高 {z['top']:.2f} mm",.78)
    save(d,DIR/(name+'.dxf'))
def assembly_dxf():
    d,m=setup();rounded(m,'PHONE_REF',W,H,P.corner_r,'phone','public',0,-H)
    for id,k in [('neck',L['neck']),('pod',L['pod']),('head',L['head'])]:
        x,X=k['x'];y,Y=k['y'];rect(m,'ENCLOSURE',[x,-Y,X,-y],'body',id)
    for i,y in enumerate(L['pod']['cell_axis_y'],1):
        cx=sum(L['pod']['x'])/2;rect(m,'ENCLOSURE',[cx-P.cell_l/2,-y-P.cell_d/2,cx+P.cell_l/2,-y+P.cell_d/2],'cell',str(i))
    for b in B.values():
        x,y,z=b['origin'];w,h=b['size'];rounded(m,'BOARD_OUTLINE',w,h,b['corner_radius'],'board',b['id'],x,-y)
        for it in b['holes']:
            xx,yy=xy(b,it['center']);circle(m,'HOLES',[xx,-yy],it['drill']/2,'drill',it['ref'])
    for r in remote_devices(B,features,P,L):
        x,y,_=r['xyz'];cw,ch,_=r['size']
        rect(m,'FIXED_PARTS',[x-cw/2,-y-ch/2,x+cw/2,-y+ch/2],'remote',r['ref'])
        text(m,'FIXED_PARTS',(x+cw/2+.5,-y),r['ref'],1.1)
    from model import ridge_path,neck_x,RX
    wp=bundle_path();cx=L['neck']['x'][0]+P.wall+P.slot_w/2
    ys=sorted(set([y for y,z in wp]+[15+i*23/32 for i in range(33)]+[y for y,z,t in ridge_path(L,P)]));cs=[(neck_x(y),-y) for y in ys];m.add_lwpolyline(cs,dxfattribs=att('HARNESS'))
    for shift in [-3.425,3.425]:m.add_lwpolyline([(x+shift,y) for x,y in cs],dxfattribs=att('HARNESS'))
    def leader(yy,label,x0,dy=0):
        ln(m,'NOTES',(x0,yy),(79,yy+dy));text(m,'NOTES',(81,yy+dy-.6),label,1.65)
    for yy,label,x0,dy in [(52,'单层铝基灯板 · 72 × 3030',66,5),(42,'四层恒流驱动板 · 风扇后方',63,0),
              (7,'可拆颈部 / 双绞功率线与信号束',61,0),(-68.9,'21700 · 电芯 1',70,0),(-91.3,'21700 · 电芯 2',70,0),
              (-113,'四层主板 / 双 USB-C 朝手机底端',64,0),(-144,'手机公开外形参照',65,0)]:
        leader(yy,label,x0,dy)
    text(m,'NOTES',(0,75),'整机背视 / 三板定位',3.2)
    text(m,'NOTES',(0,-154),'投影 (X, −Y)，单位 mm。示意，非苹果图纸数据。深度与分线点见三维文件。',1.25)
    d.set_modelspace_vport(height=260,center=(60,-40));d.saveas(DIR/'assembly_layout.dxf')
def geom(e):
    pts=np.array(list(e.get_points('xy')));return np.r_[pts.min(0),pts.max(0)]
def sdf(pt,w,h,r):
    # 到圆角矩形成品边界的有符号距离，内部为负值。
    q=np.abs(np.array(pt)-[w/2,h/2])-[w/2-r,h/2-r]
    return np.linalg.norm(np.maximum(q,0))+min(max(q),0)-r
def rect_dist(r,c):return math.hypot(max(r[0]-c[0],0,c[0]-r[2]),max(r[1]-c[1],0,c[1]-r[3]))
def overlaps(a,b):return min(a[2],b[2])-max(a[0],b[0])>1e-5 and min(a[3],b[3])-max(a[1],b[1])>1e-5
def audit(b,d):
    m=d.modelspace();gid=b['id'];w,h=b['size'];rad=b['corner_radius'];ck=[]
    def record(title,ok,detail):
        ck.append(dict(name=gid+' / '+title,ok=bool(ok),value=detail))
    outline=list(m.query('LWPOLYLINE[layer=="BOARD_OUTLINE"]'));o=outline[0]
    pts=geom(o);bulges=[p[-1] for p in o.get_points('xyb') if abs(p[-1])>1e-8]
    record('板框与单位',len(outline)==1 and o.closed and d.dxfversion=='AC1024' and d.units==4 and np.allclose(pts,[0,0,w,h]) and len(bulges)==(4 if rad else 0) and all(abs(t-math.tan(math.pi/8))<1e-7 for t in bulges) and (not rad or abs(o.get_points('xy')[0][0]-rad)<1e-6),f'R2010 / mm；{w:g} × {h:g}；R{rad:g}；{len(bulges)} 段圆弧')
    ee={(info(e)[0],info(e)[1]):e for e in m}
    holes=[];checks=[]
    for it in b['holes']:
        a=ee['drill',it['ref']];c=np.asarray(a.dxf.center)[:2];r=a.dxf.radius;k=ee['hardware',it['ref']].dxf.radius
        checks.append(np.allclose(c,it['center']) and abs(r*2-it['drill'])<1e-6 and abs(k*2-it['keep_d'])<1e-6 and sdf(c,w,h,rad)+r<=0)
        holes.append((c,k))
    record('安装孔',all(checks) and len(m.query('CIRCLE[layer=="HOLES"]'))==2*len(holes),f'{len(holes)} 孔；'+('支脚承托，无钻孔' if not holes else '孔径、孔心、禁圈和板边通过实体读回比对'))
    readings=[];all_r={};edges=[];clr=[]
    for it in b['connectors']+b['fixed']+b['leds']:
        role='led' if 'anode' in it else 'part';e=ee[role,it['ref']];r=geom(e);all_r[(role,it['ref'])]=r
        readings.append(np.allclose(r,it['rect']) and e.closed)
        for c in [(x,y) for x in (r[0],r[2]) for y in (r[1],r[3])]:
            val=-sdf(c,w,h,rad);readings.append(val>=-1e-6)
            if role=='led':edges.append(val)
        for c,k in holes:clr.append(rect_dist(r,c)-k)
    collisions=[(a,b) for i,(a,r) in enumerate(all_r.items()) for b,s in list(all_r.items())[i+1:] if overlaps(r,s)]
    mate=[(it['ref'],ko['id']) for it in b['connectors']+b['fixed']+b['leds'] for ko in b['keepouts'] if ko['side']=='TOP' and overlaps(it['rect'],ko['rect'])]
    record('器件、孔圈与禁布',all(readings) and min(clr,default=0)>=-1e-6 and not collisions and not mate,
           f'{len(b["connectors"])} 接口、{len(b["fixed"])} 定位件；器件冲突 {len(collisions)}，越禁区 {len(mate)}；'+(f'距紧固圈最近 {min(clr):.3f} mm' if clr else '无孔圈')+(str(collisions+mate) if collisions or mate else ''))
    for it in b['connectors']:
        note=ee['text',it['ref']+'_nets']
        assert note.dxf.text==nets(it) and note.dxf.layer=='CONNECTORS'
    for it in b['connectors']:assert np.allclose(np.asarray(ee['pin1',it['ref']].dxf.center)[:2],it['pin1'])
    if b['leds']:
        ls=[(k[1],r) for k,r in all_r.items() if k[0]=='led']
        centers=[((r[0]+r[2])/2,(r[1]+r[3])/2) for _,r in ls];actual={k:0 for k in ['W','C']};strings=Counter()
        for it in b['leds']:
            e=ee['led',it['ref']];xx,yy=geom(e)[:2]+1.5
            i=round((xx-min(q[0] for q in centers))/L['led_board']['pitch'][0]);j=round((yy-min(q[1] for q in centers))/L['led_board']['pitch'][1])
            col='W' if (i+j)%2==0 else 'C';assert it['color']==col
            lab={a.dxf.text:a for a in m.query('TEXT[layer=="LED_ARRAY"]') if info(a)[1]==it['ref']}
            serial=f"{col}{j+1}.{i//2+1 if j%2==0 else 6-i//2}"
            assert set(lab)=={serial,'+','−'} and np.allclose([lab['+'].dxf.insert.x+.20,lab['+'].dxf.insert.y+.61],it['anode']) and np.allclose([lab['−'].dxf.insert.x+.20,lab['−'].dxf.insert.y+.61],it['cathode'])
            actual[col]+=1;strings[serial.split('.')[0]]+=1
        gap=min(rect_dist(r,c)-k for _,r in ls for c,k in holes);record('紧固圈至灯珠',gap>=.5,f'最近 {gap:.3f} mm，四孔 Ø4.0 小头禁圈待选型')
        record('双色阵列',len(ls)==72 and min(edges)>=1 and not collisions and actual=={'W':36,'C':36} and len(strings)==12 and set(strings.values())=={6},f'72 颗；W/C 各 36，每色 6 串号 × 每串 6 颗；最小边距 {min(edges):.2f} mm，阵列未移点')
    return ck
def preview(d,b=None):
    from matplotlib.patches import Polygon
    font=next((Path(p) for p in ['/System/Library/Fonts/STHeiti Medium.ttc','/System/Library/Fonts/Hiragino Sans GB.ttc','/System/Library/Fonts/Supplemental/Arial Unicode.ttf'] if Path(p).exists()),None)
    if font:font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams['axes.unicode_minus']=False
    fig=plt.figure(figsize=(14.4,8.5),facecolor='white');label=b['name'] if b else '三板整机布局'
    fig.text(.045,.935,'结构输入图册  /  '+label,color='#203e39',fontsize=24,weight='normal')
    fig.text(.046,.891,'PCB 机械接口    /    V0.3    /    毫米 · 不按屏幕比例量取尺寸',fontsize=11,color='#557368')
    ax=fig.add_axes([.045,.19,.59,.61] if b else [.045,.16,.69,.66]);ax.set_aspect('equal');ax.set_axis_off()
    w,h=b['size'] if b else (0,0)
    ax.set_xlim((-11,w+7) if b else (-8,135));ax.set_ylim((-11,h+7) if b else (-155,69))
    fig.canvas.draw(); scale=ax.transData.transform((0,1))[1]-ax.transData.transform((0,0))[1];fs=scale*72/fig.dpi
    def render(e):
        typ=e.dxftype();l=e.dxf.layer;c=LAY.get(l,('#45655a',''))[0];role,ref=info(e)
        if typ=='DIMENSION':
            # DIMENSION 的匿名块里含 MTEXT、箭头块等，保留在原 DXF；预览单画清晰尺寸线。
            return
        if typ=='TEXT':
            x,y=e.dxf.insert.x,e.dxf.insert.y;t=e.dxf.text
            if b and not(0<=x<=w and 0<=y<=h):return
            if b and l=='HEIGHT_LIMIT':return # 右侧信息栏独立列限高，避免文字压线。
            ax.text(x,y,t,fontsize=max(4.2,e.dxf.height*fs*1.18),ha='left',va='bottom',color=c,clip_on=True);return
        if typ=='LINE':
            a=e.dxf.start;b1=e.dxf.end;ax.plot([a.x,b1.x],[a.y,b1.y],color=c,lw=.6);return
        if typ=='CIRCLE':
            xy2=(e.dxf.center.x,e.dxf.center.y);ax.add_patch(Circle(xy2,e.dxf.radius,edgecolor=c,facecolor='white' if role=='drill' else 'none',lw=.85,linestyle=':' if 'no_copper' in role else '-'));return
        if typ!='LWPOLYLINE':return
        pts=np.asarray([(v.x,v.y) for v in make_path(e).flattening(.025)])
        fill=None;ls='-';lw=1.1
        if role=='led':fill='#fbe2a0' if next(a['color'] for a in b['leds'] if a['ref']==ref)=='W' else '#d9eaf4'
        if role=='part':fill='#e3eff4' if l=='CONNECTORS' else '#ede6f4'
        if role=='height':ls='--';lw=.65
        if l.startswith('KEEPOUT'):ls=':';lw=1
        if role=='trunk':fill='#f4d3c7'
        if fill:ax.add_patch(Polygon(pts,facecolor=fill,edgecolor='none',alpha=.82))
        ax.plot(pts[:,0],pts[:,1],lw=1.7 if role in ('outline','board') else lw,ls=ls,color=c)
    for e in d.modelspace():render(e)
    if b:
        for p1,p2,st,pt in [((0,-4),(w,-4),f'{w:g} mm',(w/2,-6.4)),((-5,0),(-5,h),f'{h:g} mm',(-8,h/2))]:
            ax.annotate('',xy=p1,xytext=p2,arrowprops={'arrowstyle':'<->','color':'#405f54','lw':1})
            ax.text(*pt,st,ha='center',va='center',color='#405f54',fontsize=10,rotation=90 if p1[0]==p2[0] else 0)
        fig.text(.65,.816,'接口定位  /  器件面',fontsize=14,color='#243f38',weight='normal')
        y=.772
        for it in b['connectors']:
            fig.text(.65,y,it['ref']+'   '+it['type'],fontsize=11.3,color='#174f73')
            fig.text(.65,y-.026,f"({fmtp(it['center'])})   /   {direction(it['direction'])}   /   {it['pin_count']} 位",fontsize=9.5,color='#50665e')
            short=('VBUS / GND / CC1 / CC2 · 其余待定' if it['pattern']=='usb' else '针序待电气确认' if not any(it['nets']) else ' · '.join(it['nets']))
            fig.text(.65,y-.046,short,fontsize=7.7,color='#3e6465');y-=.082
        fig.text(.65,y-.005,'高度与紧固  /  mm',fontsize=14,color='#243f38',weight='normal');y-=.04
        for z in b['height_zones']:
            fig.text(.65,y,f"{z['id']}    TOP ≤ {z['top']:g}     BOT ≤ {z['bot']:g}",fontsize=10.2,color='#236c59');y-=.026
        fig.text(.65,y-.011,f"{b['layers']} 层   /   {b['thickness']:g} 厚   /   R{b['corner_radius']:g}   /   {len(b['holes'])} 安装孔",fontsize=9.6)
        if b['holes']:
            ho=b['holes'][0];fig.text(.65,y-.043,f"{ho['kind']}   钻 Ø{ho['drill']:g}   紧固禁圈 Ø{ho['keep_d']:g}",fontsize=9.6)
            fig.text(.65,y-.069,'孔心 u: '+fmtp([b['holes'][0]['center'][0],b['holes'][-1]['center'][0]])+'   v: '+fmtp([b['holes'][0]['center'][1],b['holes'][-1]['center'][1]]),fontsize=9)
        if b['id']=='led':fig.text(.65,y-.145,'暖黄：2700 K    淡蓝：6500 K\n框内为串号与串内序号；+ 为阳极。',fontsize=10)
        fig.text(.05,.16,'坐标原点在板框左下角；u 向右，v 向上，TOP 朝被摄物。',fontsize=10,color='#495e58')
    else:
        fig.text(.72,.75,'背视投影',fontsize=16,color='#203e39')
        fig.text(.72,.59,'绿线   板框与承载结构\n红带   主板至驱动板线束\n棕圈   安装孔',fontsize=12,linespacing=1.8)
        fig.text(.72,.36,'三板深度不同。\n投影重叠不代表实体干涉。\n请搭配装配 STEP 检查。',fontsize=11,linespacing=1.8)
    for j,k in enumerate(['BOARD_OUTLINE','HOLES','CONNECTORS','FIXED_PARTS','KEEPOUT_TOP','HEIGHT_LIMIT']):
        fig.text(.05+j*.15,.078,'━  '+LAY[k][1],fontsize=10,color=LAY[k][0])
    fig.savefig(DIR/((b['id'] if b else 'assembly_layout')+'.png'),dpi=180,facecolor='white');plt.close(fig)
def guide(payload,summary):
    md=['# PCB 结构交接 · v0.3','','**用途：导入板边、对齐、预布局及查干涉；不是厂家封装库或下单文件。** 先读本页，再开对应 PNG，最后导入 DXF。三维以同目录 STEP 为准。','',
        '## 坐标与交换','',
        '- 三板 **从 TOP 往下看**；局部原点是外接矩形左下角（圆角切去该点时仍用虚拟交点）。u 向右、v 向上；DXF 是 R2010，1:1、mm。坐标均为标称值，不含加工公差。',
        '- 各板给出 BOT 原点 O；整机逻辑坐标为 (Ox+u, Oy−v, Oz+t)，其中 t 从板底向 TOP。STEP 是右手坐标 (X,−Y,Z)；与 DXF 对齐只平移，不再镜像。整体 DXF 是背视投影，无保密镜头/传感器数据。',
        '- 导入板边只选 BOARD_OUTLINE；只将 HOLES 的**小圆**建为 NPTH，外同心圆为禁铜兼禁件，不钻第二次。实线框是器件投影/插合体预算，不是焊盘。无型号时，1 脚小圆是交接方向基准，不可据此定铜皮。','',
        '| 图层 | 含义 |','|---|---|']+[f'| {k} | {v[1]} |' for k,v in LAY.items()]
    for b in B.values():
        md+=['','## '+b['name']+'（'+b['id']+'）','','| 项目 | 结构输入；位置单位 mm |','|---|---|',
             f"| 板框与层叠 | {fmtp(b['size'])}；R{b['corner_radius']:g}；{b['layers']} 层 {b['material']}，厚 {b['thickness']:g} |",
             f"| 原点 / 面向 | BOT O=({fmtp(b['origin'])})；TOP 朝 +Z |"]
        md+=['| 安装 | '+('；'.join(f"{t['ref']} ({fmtp(t['center'])})" for t in b['holes'])+f"；{b['holes'][0]['kind']}，Ø{b['holes'][0]['drill']} 钻，Ø{b['holes'][0]['keep_d']} 双面不放件/不露铜、不走铜" if b['holes'] else '不钻孔；四角绝缘支脚承托，壳罩侧壁定位。')+' |']
        for it in b['connectors']:
            pitch='厂家混合节距待定' if it['pitch'] is None else f"{it['pitch']:g} mm"
            md.append(f"| {it['ref']} {it['type']} | 中心 ({fmtp(it['center'])})，1 脚基准 ({fmtp(it['pin1'])})，{direction(it['direction'])}，{it['pin_count']} 位，{pitch}；{nets(it)} |")
        for it in b['fixed']:md.append(f"| {it['ref']} {it['name']} | ({fmtp(it['center'])})，TOP；外形区 [{fmtp(it['rect'])}] |")
        for z in b['height_zones']:md.append(f"| {z['id']} 限高 | [{fmtp(z['rect'])}]，TOP ≤ {z['top']:g} / BOT ≤ {z['bot']:g}；{z['why']} |")
        for k in b['keepouts']:md.append(f"| {k['id']} 禁布 | {k['side']} [{fmtp(k['rect'])}]：{k['why']} |")
        if b['id']=='led':md+=['| 阵列 | 72 × YJ-BC-3030-G04；封装 3 × 3，结构高度预算 1.0。12 列 × 6 行，节距 5.5 × 7.6；暖/冷棋盘交错。每行每色 6 颗串联，六行并联。W1…W6、C1…C6，行间交替换向。焊盘极性须用原厂封装核对。 |']
    md+=['','### 板外定位（整机 X, Y, Z）','','| 器件 | 接触面中心 / 由接触面伸出方向 | 线束目的地 |','|---|---|---|']
    for it in payload['remote_parts']:
        md.append(f'| {it["ref"]} {it["name"]} | ({fmtp(it["xyz"])}) / ({fmtp(it["normal"])}) | {it["board"]} {it["port"]}：'+', '.join(it['nets'])+' |')
    md+=['','### 驱动板分区实测','','| 分区 | 刚体首触 | 不借用叶轮空间的净空 | 允许器件与装配高度 |','|---|---:|---:|---:|']
    for k in B['driver']['height_zones'][1:]:
        md.append(f"| {k['id']} | {k['static_contact_top']:.2f} | {k['clearance_top']:.2f} | {k['top']:.2f} |")
    md+=['','## 锁定、可动与签核','','- **锁定（挪动量 0 mm）**：三板外形与孔、USB 口面/朝向、三键五灯、主板支脚、72 颗发光中心、板边压筋与回转井。未协商不能移动。外形公差、板厂铣边与成品孔公差另定。',
         '- 其余连接器中心先按图冻结试排；如需移位，主/驱信号及灯板焊线端可提案沿 u ±0.3 mm，不可改变 v、朝向、禁圈、插合区或网络次序，须结构复核后生效。其余固定项 0 mm。功率电感的 10 × 10 包络可在本路 15.8 × 16 分区内平移，整包络留在区内，不得侵入孔圈；不必照画示意电感封装。',
         f"- 仅做器件外形试排：最大器件 {2+len(B['driver']['rough_placement'])}/26；两颗 7×7 电感与两颗 3×2.5 调光 PMOS 可排 {2+len(B['driver']['compact_candidate']['other_parts'])}/26。坐标见接口 JSON，不是焊盘或推荐开关回路。",
         '- 电感两区的首触与工作值见上表。靠孔的 LED 到 候选 Ø4.0 小头紧固禁圈 0.618 mm；需要螺钉头公差、孔偏心、贴装公差闭环，不能加大垫圈。线束在 LED 下缘过井，电池七线另走朝主板的仓壁窗口，不穿过电芯。',
         '- 接口基线要求断一针后仍不超过额定 70%。3.7 A 已是 5 A 的 74%；按这一个负载反推至少 5.29 A/针，尚未计风扇等支路。需电气校核整套导线与接触件的降额或故障关断。',
         '- DXF 使用 Unicode CN 文字样式。如 CAD 缺少黑体，映射 CN 为本机思源黑体或系统中文黑体，不要炸开板边；PNG 是无字体依赖的对照图。',
         '- 主板 8 mm 为从板面起算的硬上限（包括插合后的插头、卡锁、线弯）；约 10 mm 竖座至少超 2 mm。基线选卧式 2×2，含插头目标 ≤7.5 mm。若无合格料，可提案 2×2 焊线阵列＋压线夹＋线端额定配对；线端停放区未冻结，不能当作已验收或擅自取消 2×2 接口。两端每针 ≥5 A；满载/单针异常与导线温升由电气复核。',
         '- 驱动板为四层（L2 完整地平面），双 TPS92692-Q1、TOP 单面贴；不以背面 1.20 mm 物理缝隙排器件。两路各按 20 W、单路输入约 3.7 A 预留；正常总功率由固件封顶 20 W。两路同开故障依赖散热片上 85°C 常闭开关硬切使能，不表示可持续 40 W。',
         '- 温控开关装在散热片，不在驱动板上感温。J5 两线是其使能回路，不是灯板 NTC。电芯上两枚探头接主板 J5；灯板 RT1 就近贴铝基板，走独立回线。跨板信号没有 5 V；风扇由驱动板本地降压。',
         '- USB 功能网名为接口别名，A1 方向和 16 接点是预选方案，D±、SBU、屏蔽及具体引脚由电气侧核定；接口图未作厂家 land pattern。调试区按 6 个 1.27 mm 触点保留，拆罩探测。硬件需求列出 3V3、GND、SWDIO、SWCLK、NRST 和 UART；UART 是否还需 RX/TX 两脚（可能共需 7 个）及针序须由电气确认，不把未定针脚写成 NC。铝基板六个表贴焊线盘不得用贯穿焊脚，回流后核 1 mm 焊点高度及绝缘。均流电阻与二极管/电容最终落点由电气排布。',
         '- 驱动电感数量和两区空高已建模；磁饱和、铜面积、温升、卡锁/线皮与真实插拔行程、触点电流、85°C 开关外形及固定夹仍需实物验证。驱动板两只候选 10 mm 电感可放入，不等于整板布通或满足热性能。',
         '- 截面/弯折量规从主板入口沿仓背脊盖、颈部、灯板下缘至驱动分线区。散线分支及线端不以量规代替。用实选线的外径、最小弯曲半径、扭距重跑；先穿线再压壳，带插壳不能从颈槽穿过。','',
         '## 本版实际复核','']+['- '+c['name']+'：'+('通过' if c['ok'] else '不通过')+'。'+c['value'] for c in summary]
    (DIR/'README.md').write_text('\n'.join(md)+'\n')
def produce():
    DIR.mkdir(exist_ok=True);checks=[];remote=remote_devices(B,features,P,L)
    payload=dict(source='interface/mech_elec.json',source_sha256=sha256((ROOT/'interface/mech_elec.json').read_bytes()).hexdigest(),direction_convention='PCB 局部坐标：箭头指向插头所在侧/拔出或引线方向；插入相反。',version='0.3',units='mm',layers={k:v[1] for k,v in LAY.items()},boards=B,remote_parts=remote,
           project_axes='从背面看 X右、Y下、Z朝被摄物；原点左上背玻璃',step_axes='(X,-Y,Z) mm',
           rect_format='[umin,vmin,umax,vmax]，高度从各自板面起；分区覆盖 BASE，禁布优先',
           routes={'trunk_x':L['neck']['x'][0]+P.wall+P.slot_w/2,'centerline_yz':bundle_path(),'gauge_wh':[6.85,2.4],'entry_gauge_wh':[6.85,2.2],'entry_centerline_y':[50,65],'pod_trunk_x':54.55,'pod_cover_x':[50.1,58.0],'bend_center_radius':5,'power':SPEC['harness']['power'],'twists':[[1,3],[2,4]],'signal':SPEC['harness']['signal']},
           tiers={'locked':'板边、紧固孔、光学与外部人机接口：0 mm','connector_proposal':'J4 主/ J2 驱信号、灯板焊盘只可提案 u±0.3 mm，复核后生效','power':'最大包络限定在各自分区，TOP≤5.5 mm'})
    from model import ridge_path,neck_x
    xyz=[[neck_x(y),y,z] for y,z in reversed(bundle_path())]+[[neck_x(15+i*23/32),15+i*23/32,6.4] for i in range(1,33)]+[[neck_x(y),y,z] for y,z,t in ridge_path(L,P)[1:]]
    payload['routes'].pop('centerline_yz');payload['routes']['centerline_xyz']=xyz
    (DIR/'pcb_interface.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    persisted=json.loads((DIR/'pcb_interface.json').read_text())
    for b in B.values():board_dxf(b)
    assembly_dxf()
    for gid in [*B,'assembly_layout']:
        d=ezdxf.readfile(DIR/(gid+'.dxf'))
        outcome=d.audit();assert not outcome.has_errors and not outcome.fixes,(gid,outcome.errors,outcome.fixes)
        if gid in B:checks+=audit(persisted['boards'][gid],d)
        else:
            o=[e for e in d.modelspace() if info(e)[0]=='board'];ck=len(o)==3 and all(e.closed for e in o) and d.units==4 and d.dxfversion=='AC1024'
            for e in o:
                b=B[info(e)[1]];x,y,_=b['origin'];w,h=b['size'];ck &= np.allclose(geom(e),[x,-y,x+w,-y+h])
            checks.append(dict(name='整机背投影与三板原点',ok=bool(ck),value='3 条闭合板框，与装配平移量逐一核对；R2010 / mm'))
        preview(d,B.get(gid))
    guide(payload,checks)
    return checks
