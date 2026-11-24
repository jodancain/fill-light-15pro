"""v0.5 毫米合同。板坐标 (u,v)→(Ox+u,Oy-v)，三板 TOP 朝 +Z。"""
from pathlib import Path
import json,math
from a2_layout import power,runtimes
R=Path(__file__).resolve().parents[1]; PCB=R/'mech/pcb'
G=[0,5,8,10,12,15,20,25,30,35,40,50,60]
REAR=[7,10.4,12.1,13.2,14.2,15.9,18.6,21.3,24,26.7,29.5,34.9,40.3]
FRONT=[4.6,9.1,10.8,12,13.1,14.9,17.7,20.6,23.5,26.4,29.3,35.1,40.8]
SOFT=[5,6,6.6,7,7.4,8,9,10.1,11.1,12.1,13.1,15.2,17.2]
Y=[48,50,52,54,56,58,60,62,64,66,68,70]; Z=[7,9.3,11.7,14,16.4,18.7,21.1,23.4,25.8,28.2,29.3,30.4]
BAT=[5.3,65.3,64.8,98.8,4.2,11.2]; UPPER=BAT[:4]+[11.4,18.4]
CAND=[('PD402247H20',4,22,47,.30,20,7),('PD703460H15',7,34,60,1.40,15,31),('PD803460H20',8,34,60,1.50,20,35)]
def pos(b,uv,z=0):return [round(b['origin'][0]+uv[0],3),round(b['origin'][1]-uv[1],3),round(b['origin'][2]+b['thickness']+z,3)]
def contract(v):
    a=v=='A';j=json.loads((R/f'mech/baselines/v04{v.lower()}_contract.json').read_text());b=j['boards'];c=json.loads((R/'mech/baselines/v04c_contract.json').read_text())['boards']['main']
    j.update(version='0.5',variant=v,revision=v+'5-r2');b['main']['origin']=[5.3,125.8,4.7];b['led']['origin']=[4.3,-19,7.0];b['driver']['origin']=[5.3,-25,-14.5]
    if a:
        for u in b['main']['panel_flex']:u.update(side='盖面 FPC',z_base_mm=21.22,height=.28)
        # J6 在主板上。A 的线端和板端保持脚序与插拔方向。
        b['main']['height_zones']=[z for z in b['main']['height_zones'] if z['id'] not in ('TRAY','TAIL_FPC')]
        p=j['power'];p.pop('rail_v',None);p.pop('rail_a_min',None)
        p.update(vsys='BQ25798 系统电压，2S 约 6.0–8.6 V',vsys_range_V=[6.,8.6],internal_wh=10.36,contract_status='A 版待电气侧给出；暂列 C 合约，禁止据此开放充电',battery_limit_A=4.8,runtime_min=runtimes(1.4))
        j['battery']=dict(internal=True,series='2S1P',model='PD703460H15',single_cell_TWL_mm=[7,34,60],capacity_Ah=1.4,energy_Wh=10.36,continuous_cell_A=21, continuous_cell_C=15,manufacturer_peak_A=None,peak_design_A=4.8,charge_recommended_max_A=.7,charge_condition='0.5C 工程上限；未获包厂批准和温控验证前禁止充电。未公布脉冲时长，不能凭 21 A 推算保险丝或峰值。',cell1=BAT,cell2=UPPER,swollen_bbox=BAT[:4]+[4.2,19.8],ntc=dict(node='cell_ntc',nets=['NTC','BAT−'],charge_max_C=45,discharge_max_C=60),connector=dict(ref='J5',nets=['BAT+','BAT+','MID','NTC','BAT−','BAT−'],pin_rating_A_min=5,board_top_z=5.7,mated_height_max_mm=14.5,direction_xyz=[0,0,1],release='开盖后留 15 mm 上拔行程及 20×20×15 mm 指腹空间'))
    else:j['battery']=dict(internal=False,wireless_minutes=0,source='外接 USB-C PD')
    ui=b['main']['panel_flex'] if a else [s for s in b['main']['fixed'] if s['ref'].startswith(('SW','D'))]
    j['user_interface']=dict(location='可拆盖 FPC，经 J6 九线回主板' if a else '主板 TOP，经独立按帽和导光柱透盖',pins=9 if a else 0,items=[dict(ref=s['ref'],uv=s['center'],xyz=pos(b['main'],s['center'])[:2]+[21.22 if a else 5.7]) for s in ui])
    q=next(t for t in b['main']['fixed'] if t['ref']=='Q_TIM')
    j['thermal_contact']=dict(ref='Q_TIM',usage='BQ25798 充电功率区' if a else '8 V / ≥6 A 升降压前端',center_uv=q['center'],center_xyz=pos(b['main'],q['center'],2.2),size_mm=[11,3.2],package_above_top_mm=2.2,pad_compressed_mm=.6,metal_contact_z=8.5,path='绝缘导热垫 → 一体铝柱 → 盖外铝片；不向手机玻璃导热')
    def end(board,ref,h):
        b1=b[board];t=next(i for i in b1['connectors'] if i['ref']==ref);dx,dy,dz=t['direction']
        return dict(ref=board+'/'+ref,type=t['type'],uv=t['center'],xyz=pos(b1,t['center']),datum='板 TOP 中心',direction_board=t['direction'],direction_xyz=[dx,-dy,dz],mated_height_budget_mm=h,nets=t['nets'])
    j['harness']=dict(count=12,power=dict(count=4,gauge='AWG24 软铜，薄壁绝缘外径 ≤0.95 mm',section_mm2=.205,twist='两对分别 VSYS+GND；两根 VSYS 并联、两根 GND 并联',cut_length_mm=245,endpoints=[end('main','J3',2.2 if a else 7.5),end('driver','J1',2.5)],inline_head=dict(center_xyz=[54,-51.5,-11],mated_xyz_mm=[12,6,6],extraction_xyz=[-1,0,0],note='驱动 J1 是焊线端，带锁线对线接头在板外；A 主板 J3 也是焊线端')),signal=dict(count=8,gauge='AWG30，绝缘外径 ≤0.72 mm',cut_length_mm=245,endpoints=[end('main','J4',4.5),end('driver','J2',4.5)]),min_inside_bend_mm=5.,rloop_mohm_max=50,contact_pair_budget_mohm=18,copper_loop_mohm_at60=round(.0175*.245/.205*(1+.00393*40)*1000,2),locking='信号双端带锁，功率灯头内带锁；仅直流母线和慢速信号跨板。', internal_only=['灯串四线','NTC_LED / NTC_RTN 灯板两线','风扇三线及预留针','升压开关节点','85 °C 常闭开关'])
    j['routes']=[];j['connection_endpoints_xyz']={};j['routes_note']='harness 是板间合同；板坐标为原点在左下的毫米。短引线、端子压接长度由最终线厂图确认。'
    for k,board,ref,sink,r2 in [('灯板六线','driver','J3','led','J1'),('功率','main','J3','driver','J1'),('慢速信号','main','J4','driver','J2')]:
        ep=[end(board,ref,0)['xyz'],end(sink,r2,0)['xyz']];j['connection_endpoints_xyz'][k]=ep
    j['fan_bbox']=[9.3,44.3,-52.1,-17.1,-4.9,5.1];j['enclosure']={'camera_clear_xy':[0,0,46,47.5],'rail_max_z':3,'head_bbox':[0,70.6,-57,-13,-16.8,11.6],'back_height':21.7 if a else 15.0}
    from v10_limits import candidates,therm
    j["thermal_budget"]=therm(a)
    if a:j["battery"]["candidates"]=candidates()
    from v11_contact import apply
    apply(b['led'])
    out=next(x for x in b['driver']['connectors'] if x['ref']=='J3'); pads=[[56.8,round(34-i*2.54,2)] for i in range(5)]
    out.update(center=[56.8,28.92],rect=[56.1,23.22,57.5,34.62],pins=pads,pin1=pads[0],pin_count=5,nets=b['led']['connectors'][0]['nets'],type='灯板五线侧出',direction=[1,0,0])
    d=b['driver'];d['size']=[60,40];d['origin']=[5.3,-15,-14.5]; d['height_zones'][0]['rect']=[0,0,60,40];d['height_zones'].append(dict(id='HEAD_PWR',rect=[0,22,60,40],top=5.5,bot=1.5,why='前端、手机降压及主控；两面隔离'))
    j['connection_endpoints_xyz'].pop('灯板六线');j['connection_endpoints_xyz']['灯板五线']=[pos(d,out['center']),pos(b['led'],b['led']['connectors'][0]['center'])]
    if a:
        j['battery'].update(delivery='两节串联裸芯，不带保护板；BAT+ / MID / BAT− / NTC，保护全在接口板；若包厂坚持带板需提供过流点。',supplier_questionnaire={k:None for k in ['NTC_R25_ohm','NTC_B_K','DCIR_25C_mohm','charge_temperature_range_C','discharge_temperature_range_C']},runtime_basis='20 W 2.2 min/Wh，10 W 4.3 min/Wh；20 W ≥1.3 h 需 36–39 Wh。')
        for cell in j['battery']['candidates']:cell.update(runtime_20W_min=round(cell['Wh']*2.2,1),runtime_10W_min=round(cell['Wh']*4.3,1))
    from v11_electric import apply as electric
    electric(j,pos)
    return j
