"""A2-r1 结构电气合同；共板直接读取已发布的 C-r7，不另定义一套尺寸。"""
from pathlib import Path
import json,copy
ROOT=Path(__file__).resolve().parents[1]; PCB=ROOT/'mech/pcb'
PINS=['BAT+','BAT+','MID','NTC','BAT−','BAT−']
CELL=[6.9,53.9,103.0,125.0,20.9,24.9]
UP=CELL[:4]+[25.05,29.05]
SWELL=CELL[:4]+[20.9,29.85]
PLUG=[54.25,63.55,103.4,116.9,15.0,29.5]
SCREWS=[(8.1,127.8),(62.6,127.5),(62.6,101.65)]
# 两只电芯的铝塑膜端封在标称外形内；引线和检测电阻另计。
OPT=[{'model':'PD402247H20','mm':[4,22,47],'ah':.30,'C':20,'mass_each_g':7.0,'basis':'电芯质量预算，尺寸及倍率为厂家目录值'},
     {'model':'PD702025H30','mm':[7,20,25],'ah':.26,'C':30,'mass_each_g':6.5,'basis':'可选并排；需另版托盘，质量预算'},
     {'model':'THOR-105555','mm':[10,55,55],'ah':5.,'C':1,'mass_each_g':64,'basis':'裸芯定制，要求供应商书面确认 5 A 持续；非本背夹适配件'}]
def power(vmin,vpack,w,phone,ntc_ok=True):
    """4.8 A 是硬上限；先扣辅助功耗，再给灯、最后给手机。"""
    if vmin<=3 or not ntc_ok:return 0.,0.
    budget=max(0,vpack*4.8-2)
    lamp=min(w,20,budget*.88)
    a=min(phone,1.5 if w>10 else 3,max(0,(budget-lamp/.88)*.9/5)) if vmin>=3.4 else 0
    return lamp,a
def runtimes(ah):
    # 非实测。可用能量统一按标称 90%，不重复扣 DC/DC 效率。
    return [60*7.4*ah*.90/(w/.88+5*i/.9+2) for w,i in [(20,0),(10,0),(20,1.5)]]
def contract():
    j=json.loads((PCB/'pcb_interface.json').read_text());j.update(variant='A2',revision='A2-r1');b=j['boards']['main']
    b['name']='电池版充电、保护与控制主板'; ui=[i for i in b['fixed'] if i['node'].startswith(('key_','light_'))]
    b['fixed']=[i for i in b['fixed'] if i not in ui];b['panel_flex']=ui
    b['panel_flex_note']='rect/center 为板坐标下的盖面投影，非主板器件；Z=31.4 是贴装面。'
    for f in ui:f.update(side='盖面 FPC',z_base_mm=31.40,height=.36 if f['node'].startswith('key_') else .35)
    def move(i,dx,dy):
        for k in ('center','pin1'):
            if k in i:i[k]=[round(i[k][0]+dx,4),round(i[k][1]+dy,4)]
        i['rect']=[round(x+[dx,dy][n%2],4) for n,x in enumerate(i['rect'])]
        if 'pins' in i:i['pins']=[None if p is None else [p[0]+dx,p[1]+dy] for p in i['pins']]
    j3=next(i for i in b['connectors'] if i['ref']=='J3');move(j3,-9,0);j3.update(type='驱动功率短线卧式焊接区',height=2.2,direction=[0,0,1],status='板端短线；配对驱动端维持原连接，不在托盘下插拔。')
    l=next(i for i in b['fixed'] if i['ref']=='L_IN');move(l,38.55,-7.0)
    b['keepouts']=[k for k in b['keepouts'] if k['id']!='MATE3']
    b['height_zones']=[z for z in b['height_zones'] if z['id']!='INPUT_L'];b['height_zones'] += [
      dict(id='TRAY',rect=[.8,0,49,23.5],top=4.8,bot=1.2,why='托盘下限高；PD_POWER 更严，热舌单独接触'),
      dict(id='INPUT_L',rect=l['rect'],top=5.5,bot=1.2,why='服务槽下方高件，不正对电芯')]
    def pad(ref,node,kind,cx,cy,w,h,nets,pitch):
        r=[cx-w/2,cy-h/2,cx+w/2,cy+h/2];pins=[[cx+(i-(len(nets)-1)/2)*pitch,cy] for i in range(len(nets))]
        return dict(ref=ref,node=node,type=kind,center=[cx,cy],rect=r,height=.20,pin_count=len(nets),pitch=pitch,pin1=pins[0],pins=pins,direction=[0,0,1],pattern='row',nets=nets,status='板端焊线；编号对应线端正视图，非量产封装')
    # 触点位置只表示编号方向，最终焊盘、节距和锁扣由电气侧选型。
    body=[round(PLUG[0]-5.3,3),round(125.8-PLUG[3],3),round(PLUG[1]-5.3,3),round(125.8-PLUG[2],3)]
    cx,cy=(body[0]+body[2])/2,(body[1]+body[3])/2
    j5=pad('J5','main_j5','电池六针防呆板座（插合包络）',cx,cy,9.3,13.5,PINS,1)
    j5.update(rect=body,pattern='keyed_2x3',pitch=None,pin1=[cx-1.5,cy+3],pins=[None]*6,height=7.0,
              mated_height=14.5,current_per_contact_A_min=5,pinout_status='定稿',disconnect_axis=[0,0,1],status='TOP 正视；1 脚标记在近 −u/+v 角；图形是结构外形而非端子焊盘。每针 ≥5 A。')
    b['connectors'] += [j5,pad('J6','main_j6','面盖九线软排焊接区',24.1,21.2,8,1.6,['K1','K2','K3','LED1','LED2','LED3','LED4','LED5','COM'],.8)]
    b['height_zones'].append(dict(id='TAIL_FPC',rect=[23.4,21.0,48.0,23.5],top=1.6,bot=1.2,why='折返软排下方；J6 为焊接触点，器件不得顶软排。'))
    b['height_zones'].append(dict(id='BAT_MATED',rect=body,top=14.5,bot=1.2,why='J5 专用，包含板座、插头、锁扣及折线出口；不得借用邻区。'))
    b['circuits']=['BQ25798','HY2120','独立二级过压','保险丝','PD 受电','5V 手机输出','中点检测','电芯 NTC']
    j['routes'][0][1][0][0]-=9;j['connection_endpoints_xyz']['主驱功率'][0][0]-=9
    jp={'ref':'J5-P','board':'main/J5','type':'双排六位非对称防呆，带锁扣；绝缘凹端装在电池侧','pin_count':6,'nets':PINS,'pinout_status':'定稿','pitch_mm':None,'current_per_contact_A_min':5,'bbox_xyz':PLUG,'mated_height_max_mm':14.5,
        'disconnect_axis':[0,0,1],'pin1':'TOP 板面正视，1 脚标在 −u/+v 角；插头对插面须按厂家编号镜像校对','service':'拔 PD、关灯、卸三只尼龙螺钉，掀盖并托住带软排的面盖（不拉扯排线）；翻起拉耳，按住朝 +Y 的锁扣，沿 +Z 拔出至少 15 mm；不得拉线。开盖后 Z32…47 留 20×20×15 mm 指腹空间，触点内藏。','note':'1/2 BAT+；3 MID 仅检测；4 NTC，热敏另一端接 BAT−；5/6 BAT−。型号未定，普通竖装 Micro-Fit 不视为符合。'}
    j['battery']=dict(internal=True,series='2S1P',options=OPT,recommended=OPT[0]['model'],bbox_order=['xmin','xmax','ymin','ymax','zmin','zmax'],cell1=CELL,cell2=UP,swollen_bbox=SWELL,swelling_z_fraction=.10,connector=jp,
        protection='电路只在主板；包由供应商配组、绝缘、封装。非用户散芯串接。',ntc=dict(ref='RT_BAT',bbox_xyz=[31,34,102.45,103,26.3,27.4],nets=['NTC','BAT−'],charge_max_C=45,discharge_max_C=60))
    j['power'].update(internal_wh=2.22,battery_limit_A=4.8,battery_modes=[{'lamp_w':'>10','phone_A_max':1.5},{'lamp_w':'≤10','phone_A_max':3}],phone_off_cell_below_V=3.4,lamp_off_cell_at_V=3.0,
                      precedence='单节阈值与温度 > 包电流硬限 > 灯 > 手机；手机电流是上限，不是保证。待需求方确认。PD 沿用 C 合约，无剩余输入预算时暂停充电。',runtime_min=runtimes(.30))
    for key,points in {'配组包六线至主板 J5':[[53.9,117.9,25.5],[55.8,118.2,26.5],[59.7,117.7,27.4],[59.7,116.9,27.4]],'面盖软排线':[[57.7,109,31.32],[57.7,102.3,31.32],[57.7,102.3,19.2],[39.5,102,19.2],[39.5,102,18.1],[51,102,18.1],[51,102.9,17],[29.4,103.25,17],[29.4,104.6,15.2]]}.items():
        j['connection_endpoints_xyz'][key]=points;j['routes'].append([key,[p[:2] for p in points]])
    j['enclosure']['pack_lid_max_z']=31.95;return j
