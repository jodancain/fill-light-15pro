"""ECAD 交换：写真实 R2010 实体，按实体读回后渲染和核验。禁止读取任何硬件或手机图纸。"""
from pathlib import Path
import os,json,math,shutil
from collections import Counter
from hashlib import sha256
ROOT=Path(__file__).resolve().parents[1]
from v04_config import PITCH
from c04 import FAN,POWER,VARIANT,policy
from v04_config import WINDOW_XY,RAIL_X,RAIL_Y,MOUNTS
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
     'NOTES':('#3c4942','说明'),'PHONE_REF':('#86938b','公开手机外形'),'ENCLOSURE':('#64877a','背壳 / 风机'),
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
def direction(v):return {(1,0,0):'+u',(0,0,1):'+Z',(0,1,0):'+v',(0,-1,0):'−v',(-1,0,0):'−u'}[tuple(v)]
def save(d,path):
    d.set_modelspace_vport(height=98,center=(60,21));d.saveas(path)
def board_dxf(b):
    d,m=setup();w,h=b['size'];name=b['id'];rounded(m,'BOARD_OUTLINE',w,h,b['corner_radius'],'outline',name)
    if 'clamp' in b:
        cl=b['clamp']; d.layers.new('CLAMP_CONTACT',dxfattribs={'color':6})
        for edge,r in cl['rect_uv_mm'].items(): rect(m,'CLAMP_CONTACT',r,'clamp',edge)
        text(m,'CLAMP_CONTACT',(0,-13),cl['rule'],.75,'clamp_rule')
        text(m,'NOTES',(0,-15),'参考串号/次序/焊盘朝向：电气侧可调。四边直段宽 0.8 mm，R2 四角不压。',.75)
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
        j4=next(c for c in b['connectors'] if c['ref']=='J4')
        sy-=2.1;text(m,'NOTES',(sx,sy),'J4：'+j4['note'],.82,'J4_note')
        for line in [b['stack_note'],'每路最大裸体面积 298.66 mm²；高区 252.8 mm²，低件需外排。',f"双路试排 最大包络 {2+len(b['rough_placement'])}/26；7×7 电感、小 PMOS {2+len(b['compact_candidate']['other_parts'])}/26，详见 JSON。"]:
            sy-=2.1;text(m,'NOTES',(sx,sy),line,.82)
    for s in [f"{b['layers']} 层 / {b['material']} / 厚 {b['thickness']:g} / R{b['corner_radius']:g}",
              f"整机坐标：X={b['origin'][0]:g}+u；Y={b['origin'][1]:g}−v；BOT Z={b['origin'][2]:g}；TOP 朝 +Z",
              '圆形标记为 1 脚；箭头为插拔 / 出线；圆点套圈为朝 +Z。','钻孔与禁铜圈分开；请只将 BOARD_OUTLINE 导入板边。',
              'v0.4-C：外接 PD，机内无电芯；两口分别为输入和 5V 输出。','型号、落脚图与配对插头由电气确认；不可按占位轮廓制焊盘。']:
        sy-=2.35;text(m,'NOTES',(sx,sy),s,.82)
    for z in b['height_zones']:
        if 'clearance_top' in z:
            sy-=2.05;text(m,'HEIGHT_LIMIT',(sx,sy),f"{z['id']}  全区净空 {z['clearance_top']:.2f} mm；发板工作限高 {z['top']:.2f} mm",.78)
    save(d,DIR/(name+'.dxf'))
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
            i=round((xx-min(q[0] for q in centers))/PITCH[0]);j=round((yy-min(q[1] for q in centers))/PITCH[1])
            col='W' if (i+j)%2==0 else 'C';assert it['color']==col
            lab={a.dxf.text:a for a in m.query('TEXT[layer=="LED_ARRAY"]') if info(a)[1]==it['ref']}
            serial=f"{col}{j+1}.{i//2+1 if j%2==0 else 6-i//2}"
            assert set(lab)=={serial,'+','−'} and np.allclose([lab['+'].dxf.insert.x+.20,lab['+'].dxf.insert.y+.61],it['anode']) and np.allclose([lab['−'].dxf.insert.x+.20,lab['−'].dxf.insert.y+.61],it['cathode'])
            actual[col]+=1;strings[serial.split('.')[0]]+=1
        if holes:
            gap=min(rect_dist(r,c)-k for _,r in ls for c,k in holes);record('紧固圈至灯珠',gap>=.5,f'最近 {gap:.3f} mm，四孔 Ø4.0 小头禁圈待选型')
        else:
            clamp=b['clamp']; polys=list(m.query('LWPOLYLINE[layer=="CLAMP_CONTACT"]'));actual_rect={info(e)[1]:geom(e) for e in polys}
            expected=clamp['rect_uv_mm'];same=set(actual_rect)==set(expected) and len(polys)==4 and all(e.closed and np.allclose(actual_rect[info(e)[1]],expected[info(e)[1]]) for e in polys)
            gap=min(math.hypot(max(t[0]-r[2],r[0]-t[2],0),max(t[1]-r[3],r[1]-t[3],0)) for _,r in ls for t in actual_rect.values());record('绝缘压框至灯珠',same and gap>=.5 and any(e.dxf.text==clamp['rule'] for e in m.query('TEXT[layer=="CLAMP_CONTACT"]')),f'四直边回读；距最近灯珠 {gap:.3f} mm')
        record('双色阵列',len(ls)==72 and min(edges)>=1 and not collisions and actual=={'W':36,'C':36} and len(strings)==12 and set(strings.values())=={6},f'72 颗；W/C 各 36，每色 6 串号 × 每串 6 颗；最小边距 {min(edges):.2f} mm，12×6，节距按贴合版')
    return ck
def preview(d,b=None):
    from matplotlib.patches import Polygon
    font=next((Path(p) for p in ['/System/Library/Fonts/STHeiti Medium.ttc','/System/Library/Fonts/Hiragino Sans GB.ttc','/System/Library/Fonts/Supplemental/Arial Unicode.ttf'] if Path(p).exists()),None)
    if font:font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams['axes.unicode_minus']=False
    fig=plt.figure(figsize=(14.4,8.5),facecolor='white');label=b['name'] if b else '三板整机布局'
    fig.text(.045,.935,'结构输入图册  /  '+label,color='#203e39',fontsize=24,weight='normal')
    fig.text(.046,.891,'PCB 机械接口    /    V0.4 · C    /    毫米 · 不按屏幕比例量取尺寸',fontsize=11,color='#557368')
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
        fig.text(.72,.59,'绿线   板框与承载结构\n红线   机内连接示意\n棕圈   安装孔',fontsize=12,linespacing=1.8)
        fig.text(.72,.36,'三板深度不同。\n投影重叠不代表实体干涉。\n请搭配装配 STEP 检查。',fontsize=11,linespacing=1.8)
    for j,k in enumerate(['BOARD_OUTLINE','HOLES','CONNECTORS','FIXED_PARTS','KEEPOUT_TOP','HEIGHT_LIMIT']):
        fig.text(.05+j*.15,.078,'━  '+LAY[k][1],fontsize=10,color=LAY[k][0])
    fig.savefig(DIR/((b['id'] if b else 'assembly_layout')+'.png'),dpi=180,facecolor='white');plt.close(fig)
def produce():
    from model import ROOT,L,D,P,B,W,H,SPEC,parts,xy,absrect
    from model import MOUNTS
    from driver_fit import trial,compact
    d=B['driver'];d['rough_placement']=trial(d);d['compact_candidate']=compact(d)
    DIR.mkdir(exist_ok=True);checks=[]
    def pinloc(board,ref):
        bd=B[board];it=next(r for r in bd['connectors'] if r['ref']==ref);return [*xy(bd,it['center']),round(bd['origin'][2]+bd['thickness'],3)]
    ends={'主驱功率':(pinloc('main','J3'),pinloc('driver','J1')), '主驱信号':(pinloc('main','J4'),pinloc('driver','J2')), '灯板六线':(pinloc('driver','J3'),pinloc('led','J1')), '风机三线（四位座，第4针空置）':(pinloc('driver','J4'),[44.3,88.5,12.5]), '温控硬切':(pinloc('driver','J5'),[56.5,93.5,16.75])}
    routes=[(name,[a[:2],b[:2]]) for name,(a,b) in ends.items()]
    payload=dict(version='0.4',variant=VARIANT,revision='C-r7',enclosure=dict(camera_clear_xy=[0,0,*WINDOW_XY],rail_x=RAIL_X,rail_y=RAIL_Y,rail_max_z=3,cover_screw_xy=MOUNTS,lower_head_max_y=111.,units='mm；整机背视坐标'),power=dict(**POWER,contract_modes=[dict(v=v,a=a,led_w=policy(v,a)[0],phone_a=policy(v,a)[1]) for v,a in [(20,3),(15,3),(15,2),(5,3),(5,1.5)]],unknown='待机，输出关闭'),units='mm',boards=B,axes='板左下 BOT：X=Ox+u，Y=Oy−v，Z=Oz；TOP 朝 +Z；STEP 为 (X,−Y,Z)。',connection_endpoints_xyz=ends,routes_note='端点以板面器件中心或板外引线区代表。背视直线仅表达电气连接，不是可制造的空间线束路径。',routes=routes,layers=LAY,battery=dict(internal=False,wireless_minutes=0,source='外置单口 USB-C PD SPR 电源',connector='main/J1'),fan_bbox=FAN)
    (DIR/'pcb_interface.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); rb=json.loads((DIR/'pcb_interface.json').read_text())
    md=['# 贴合背夹 · PCB 结构交接 v0.4 · C 第七轮（沿用第六轮几何）','','坐标与 STEP 换算：'+payload['axes'],'','板框、安装孔、USB 开口、三键五灯与发光中心固定；不能无复核移动。Q_TIM 的接触面必须落在铝舌导热垫内；L_IN 只能在 INPUT_L 内放置。其余接口现为试排位置，不是封装批准。两功率电感只可在各自分区内平移。']
    for b in B.values():
        board_dxf(b);doc=ezdxf.readfile(DIR/(b['id']+'.dxf'));assert not doc.audit().has_errors;cs=audit(rb['boards'][b['id']],doc);checks+=cs;preview(doc,b)
        md+=['','## '+b['name'],'','| 项目 | PCB 局部坐标 / 规格（mm） |','|---|---|',f"| 板体 | {fmtp(b['size'])}，R{b['corner_radius']}，{b['layers']} 层 {b['material']}，厚 {b['thickness']}；BOT 原点 {fmtp(b['origin'])} |"]
        for h in b['holes']:md.append(f"| {h['ref']} | {fmtp(h['center'])}，钻 Ø{h['drill']}，紧固禁圈 Ø{h['keep_d']} |")
        for it in b['connectors']:md.append(f"| {it['ref']} {it['type']} | {fmtp(it['center'])}；1脚 {fmtp(it['pin1'])}，方向 {direction(it['direction'])}；{nets(it)}{'；'+it['note'] if it.get('note') else ''} |")
        for it in b['fixed']:md.append(f"| {it['ref']} {it['name']} | 中心 {fmtp(it['center'])} |")
        for k in b['keepouts']:md.append(f"| {k['id']} {k['side']} | {fmtp(k['rect'])}；{k['why']} |")
        for k in b['height_zones']:md.append(f"| {k['id']} | {fmtp(k['rect'])}：TOP ≤ {k['top']}，BOT ≤ {k['bot']} |")
    md+=['','主板 60×23.5，较 A 向下收 1 mm（两面少 120 mm²）；USB 边固定，仍比最初 60×21 多 300 mm²，4 层；取消内置电池、主板 J5 及充电路径。J1 目标 20V/3A Sink，J2 仅 5V 最大 3A Source；45W 档限手机，详见报告预算。原 BQ25798 方案不可直接视为定版；需 8V/6A 无电池稳压电源与板温检测。驱动板 L2 保持完整地；J1 改短引线，候选紧凑方案只作本体排布，配对插头、走线与返回电流均须复排。','灯板 62×34；4.5×5.2 节距；每色 6 串×6 并，温控硬切、六线与板载 NTC 保留。四孔用 Ø4 小头，螺钉公差待验。','DXF：'+ '；'.join(k+'：'+v[1] for k,v in LAY.items()),'','整机 DXF 的 ENCLOSURE 层已更新镜头窗、外顶轨、背盖钉头投影，不是 PCB 钻孔。板框、孔位、接口仍为 R5 坐标。头方已接受冻结导电件；分区包络实测见 ../out/report.md。']
    (DIR/'README.md').write_text('\n'.join(md)+'\n');doc,m=setup();rounded(m,'PHONE_REF',W,H,P.corner_r,'phone','public',0,-H)
    rounded(m,'ENCLOSURE',71.6,87.9,9,'body','shell',-.5,-143);rect(m,'ENCLOSURE',[FAN[0],-FAN[3],FAN[1],-FAN[2]],'blower','35x35')
    wx,wy=WINDOW_XY
    ln(m,'ENCLOSURE',(0,-wy),(wx,-wy),'window','edge_y');ln(m,'ENCLOSURE',(wx,-wy),(wx,0),'window','edge_x')
    rect(m,'ENCLOSURE',[RAIL_X[0],-RAIL_Y[1],RAIL_X[1],-RAIL_Y[0]],'rail','top')
    for k,(x,y) in enumerate(MOUNTS):circle(m,'ENCLOSURE',(x,-y),1.9,'cover_head','S'+str(k+1))
    for b in B.values():
        x,y,z=b['origin'];rounded(m,'BOARD_OUTLINE',*b['size'],b['corner_radius'],'board',b['id'],x,-y)
        for h in b['holes']:
            xx,yy=xy(b,h['center']);circle(m,'HOLES',(xx,-yy),h['drill']/2,'drill',h['ref'])
    for title,pts in routes:m.add_lwpolyline([(x,-y) for x,y in pts],dxfattribs=att('HARNESS'))
    for y,lab in [(20,'手机公开外形'),(47.5,'镜头开窗 · 左上通边'),(108.5,'下部背盖钉 · 上移'),(68,'灯板与横向风道'),(96,'35 mm 离心风机'),(112,'底层驱动 / 上层主板'),(125.8,'USB-C ×2 朝下')]:
        ln(m,'NOTES',(61,-y),(74,-y));text(m,'NOTES',(75,-y),lab,1.8)
    save(doc,DIR/'assembly_layout.dxf');doc=ezdxf.readfile(DIR/'assembly_layout.dxf');q=[e for e in doc.modelspace() if info(e)[0]=='board'];assert not doc.audit().has_errors and len(q)==3 and all(e.closed for e in q);preview(doc)
    checks.append(dict(name='整机背视 DXF',ok=True,value='3 个闭合板框，单位毫米。'))
    return checks
