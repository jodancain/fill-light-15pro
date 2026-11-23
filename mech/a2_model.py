"""从共用底壳与冻结光机装配派生 A2，仅替换尾舱。"""
import model as m
from model import box,rr,cyl,add,pack,Pos,Color,MAT
from a2_layout import CELL,UP,PLUG,SCREWS
def make(j):
    m.make();parts=m.parts; b=j['boards']['main']
    def replace(i,s):
        s.label=i;s.color=Color(parts[i]['color']);parts[i]['sh']=s
    # 外部三键五灯保留相同 XY，采用固定在翻盖上的低背膜片面板。主板只留排线。
    for i in list(parts):
        if i.startswith(('cap_','key_','light_')):parts.pop(i)
    for row in b['connectors']+b['fixed']:
        i=row['node']
        if i not in ('input_choke','main_j3','main_j5','main_j6'):continue
        s=box(*m.absrect(b,row['rect']),15,15+row['height'])
        if i in parts:
            replace(i,s);parts[i]['name']=row.get('type',row.get('name',i))
        else:add(i,row['type'],'电路板','接口',s,(0,0,13),mass=1.2 if i=='main_j5' else .15,note='1/2 BAT+；3 MID；4 NTC；5/6 BAT−。每针 ≥5 A；插合总高 ≤14.5 mm。' if i=='main_j5' else '软排由检修盖引出。')
    hood=parts['shell']['sh'].cut(rr(5.7,65,100.85,128.7,19.5,34,2))
    rim=rr(5.15,65.45,100.05,130.0,22.65,30.35,2.8).cut(rr(6.4,64.2,101.32,128.7,22.5,30.5,1.5))
    # 托底同壳一体；三面护边、右侧低止挡。封边不受螺钉预紧力。
    tray=box(6.35,54.35,101.4,126.35,19.7,20.9)
    tray=tray.fuse(box(5.65,6.85,101.3,126.4,19.7,23.1),box(6.4,54.35,125.55,126.75,19.7,27.5),
                  box(6.4,54.35,101.35,102.55,19.7,26.0),box(54.1,55.3,124.05,125.6,19.7,24.0))
    for x,y in SCREWS:
        peg=cyl(x,y,22.7,5.0,7.65).intersect(box(4,67,100.05,130,22,31))[0];rim=rim.fuse(peg)
    hood=hood.fuse(rim,tray).cut(box(54.05,64.08,103.1,117.2,14.99,31))
    lid=rr(5.15,65.45,100.05,130,30.35,31.95,2.8)
    # 面膜局部凹入 0.65，凹处加厚在底面；不侵入鼓胀量规。
    recess=rr(11.6,63.7,106.45,113.55,31.26,32.05,1.1)
    lid=lid.fuse(rr(11.5,63.8,106.35,113.65,30.05,30.45,1.15)).cut(recess)
    # 软排线过盖，不需要穿软包；掀盖方向朝右。所有穿孔在电芯以外。
    lid=lid.fuse(box(55.6,59.8,101.97,107.15,30.05,30.4)).cut(box(55.8,59.6,102.1,107.15,31.26,32.1),box(55.8,59.6,102.1,102.65,29.9,32.1))
    bolts=[]
    for x,y in SCREWS:
        hood=hood.cut(cyl(x,y,25.8,1.70,5.1))
        lid=lid.cut(cyl(x,y,30.3,2.2,2.0),cyl(x,y,31.25,3.7,.8))
        bolts.extend([cyl(x,y,26,1.55,5.25),cyl(x,y,31.25,3.45,.65)])
    replace('shell',hood);parts['shell']['name']='带硬托盘的电池版尾舱';parts['shell']['orientation']='托仓开口向上；下摆定位，风口横梁与内肩局部支撑。'
    add('battery_lid','电池检修盖','电池仓','PC-FR',lid,(0,0,50),'外表面朝上，托边着床；面板另贴。')
    MAT['尼龙']=('#c8bda4',1.15)
    add('lid_fasteners','三只绝缘尼龙 M2 盖钉','电池仓','尼龙',pack(*bolts),(0,0,56),mass=.3,note='打印底孔攻丝或用非金属嵌套；试片验证拔出力。')
    add('tray_insulation','热舌上方封面隔热片','电池仓','隔热片',box(7,53.8,102.6,106.65,19.4,19.7),(0,0,18))
    for i,env in enumerate((CELL,UP),1):add('cell_'+str(i),f'配组软包电芯 {i} · 300 mAh','电池仓','锂聚合物包',rr(*env,.6),(0,0,24+6*i),mass=7,note='PD402247H20；质量为预算，封边、极耳尺寸及出货公差待样品确认。')
    add('cell_separator','电芯间绝缘纸','电池仓','隔热片',box(7,53.8,103.15,124.85,24.9,25.05),(0,0,30))
    add('cell_ntc','RT_BAT · 电芯温度','电池仓','接口',box(*j['battery']['ntc']['bbox_xyz']),(5,0,28),mass=.15)
    add('battery_plug','J5-P · 电池六位防呆线端','电池仓','接口',rr(*PLUG[:4],22.,PLUG[-1],.6),(10,0,34),mass=3,note='板面起算，插合与锁扣总高 ≤14.5 mm；端子 ≥5 A/针。解锁后沿 +Z 提离。')
    # 薄膜面板和三颗锅仔/五颗侧发光器件均使用同一面盖安装坐标。
    MAT['聚酰亚胺软板']=('#af823a',1.6)
    add('panel_flex','面盖三键五灯软排线','电路板','聚酰亚胺软板',rr(11.75,63.35,106.6,113.4,31.26,31.4,.8),(0,0,54),mass=.5,note='聚酰亚胺 FPC，按组件预算计重。')
    for f in b['panel_flex']:
        x,y=m.xy(b,f['center']);add(f['node'],f['name']+' · 盖面','电路板','接口',cyl(x,y,31.4,4.1 if f['node'].startswith('key') else 1.4,f['height']),(0,0,55),mass=.04)
    add('overlay','透明视窗与三键薄膜','电池仓','TPU',rr(11.75,63.35,106.6,113.4,31.77,31.94,.8),(0,0,58),mass=.4)
    # 两条可拆电气路径也参加干涉：浅 U 形软排储长，六芯绝缘引线从包尾出。
    # 平直段和折边是带厚度的空间量规，不是 FPC 铜箔展开图。
    mat='线束包络';f=box(56,59.4,102.22,106.6,31.26,31.39).fuse(
        box(56,59.4,102.22,102.35,19.12,31.39),box(39.4,59.4,100.77,103.17,19.12,19.25),
        box(39.4,39.53,100.77,103.17,18.02,19.25),box(39.4,51.1,100.77,103.17,18.02,18.15),
        box(50.97,51.1,100.77,103.17,16.92,18.15),box(29.0,51.1,102.05,104.45,16.92,17.05),
        box(29.0,31.7,102.05,104.7,16.92,17.05),box(29.0,31.7,104.57,104.7,15.2,17.05))
    add('panel_tail','盖面软排折返净空','电路板',mat,f,(5,0,27),mass=.25,note='收纳路径、拆盖托住；最终软排弯折寿命和实装行程待检。')
    lead=box(53.9,59.9,117.25,119.85,25.15,27.75).fuse(box(56.5,59.9,116.9,119.85,25.15,27.75))
    add('pack_leads','配组包六线出线包络','电池仓',mat,lead,(2,0,30),mass=.42,note='端封外绝缘扁线束占位；芯线、绝缘与载流另需实测。')
    return parts
