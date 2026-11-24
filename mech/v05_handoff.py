"""不依赖 CAD 内核的前置交接。结果只进候审区，不与制造发布件混放。"""
from v05_layout import *
from v05_report import battery_lines
from hashlib import sha256
import io,zipfile,difflib,subprocess,base64
def route():
    from v05_route import path
    return [list(p[:3]) for p in path()]
def run():
    folder=R/'mech/out/round09';folder.mkdir(parents=True,exist_ok=True)
    for v in 'CA':
        a=v=='A';s='_battery' if a else '';j=contract(v);h=j['harness'];pts=route()
        h.update(centerline_xyz=pts,trunk_length_mm=round(sum(math.dist(x,y) for x,y in zip(pts,pts[1:])),3))
        name='pcb_interface'+s+'.json';loc=folder/v/'pcb';loc.mkdir(parents=True,exist_ok=True)
        out=loc/name;out.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        r=json.loads(out.read_text());boards=r['boards'];check=[]
        def ck(t,x):
            if not x:raise ValueError(t)
            check.append(t)
        ck('三板板框与 TOP 原点',[(boards[k]['size'],boards[k]['origin']) for k in ('main','driver','led')]==[([60,23.5],[5.3,125.8,4.7]),([60,22],[5.3,-25,-14.5]),([62,34],[4.3,-19,7])])
        sig=['GND','DIM_W','DIM_C','DRV_EN','DRV_FLT','FAN_PWM','FAN_TACH','NTC_LED']
        ck('八芯双端针序',all(e['nets']==sig for e in h['signal']['endpoints']))
        ck('风机座 J4',next(e['nets'] for e in boards['driver']['connectors'] if e['ref']=='J4')==['5V','FAN_GND_SW','FAN_TACH','NC_PWM'])
        ck('热铜与端接总回阻估算',h['copper_loop_mohm_at60']+18<=50)
        ck('三键五灯坐标',len(j['user_interface']['items'])==8)
        ck('板端坐标正反算',all(pos(boards[e['ref'].split('/')[0]],e['uv'])==e['xyz'] for k in ('power','signal') for e in h[k]['endpoints']))
        if a:ck('J5 与电池功率轨',j['battery']['connector']['nets']==['BAT+','BAT+','MID','NTC','BAT−','BAT−'] and 'rail_v' not in j['power'])
        text=['# v0.5 '+v+'｜结构与电气预交接','', '**候审：以下为设计值和接口文件回读，不是实体或制造检查通过。勿凭此投板或打印。**','','灯头 70.6×44×28.4 mm，最近边 G=13，TOP 朝后；两版同源。背夹最高 Z='+str(j['enclosure']['back_height'])+' mm。35×35×10 风机、12 鳍，散热负荷 12+2.73 W，35°C 环境/75°C 基座要求 ≤2.72 K/W。持续 20 W 和握持面 ≤48°C 待样机。','',
        '|板端|板坐标 u,v|整机 TOP x,y,z|插拔方向 XYZ|插合限高 mm|','|---|---|---|---|---|']
        for k in ('power','signal'):
            for e in h[k]['endpoints']:text.append(f'|{e["ref"]}|{e["uv"]}|{e["xyz"]}|{e["direction_xyz"]}|{e["mated_height_budget_mm"]}|')
        text+=['','每芯裁线 245 mm。两对 VSYS/GND 分别双绞，AWG24，慢信号八线 AWG30。铜回路 20°C：2×0.0175×0.245/(2×0.205)=20.91 mΩ；60°C 取 24.20 mΩ。全链端接预算 18 mΩ，合计 42.20 mΩ，3 A 压降 0.127 V；实物四线法必须 ≤50 mΩ。弯头内侧目标 ≥5 mm；支路和插拔手势待实配。','Q_TIM 在板坐标 '+str(j['thermal_contact']['center_uv'])+'，11×3.2 mm，封装顶高 2.2 mm，压合绝缘垫 0.6 mm。铝柱接触面 Z=8.5，热量朝外散。',j['user_interface']['location']+'。逐键和逐灯的板坐标、装机坐标见同目录接口。']
        if a:text+=['']+battery_lines()
        text+=['','局部合同检查：'+'；'.join(check)+'。','仍待实体核验：两版完整干涉、XY 禁带、G 分段及背部高度曲线、右轨的键位和弯曲净空、整机质量、STEP/STL/GLB/DXF 以及离线网页。头方另核天线、指南针、实机取景、侧键和底部双线。']
        (loc.parent/'handoff.md').write_text('\n'.join(text)+'\n')
        print(v,name,out.stat().st_size,sha256(out.read_bytes()).hexdigest(),check,flush=True)
if __name__=='__main__':run()
