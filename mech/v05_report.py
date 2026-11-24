"""由同一接口与回读记录生成交付说明、双页、图版。"""
from v05_layout import *
import html,re
from v10_limits import thermal_text,candidates
SINGLE='https://www.pdbattery.com/high-rate-rc-lipo-battery-cell-list.html'
def battery_lines():
    lines=["|背高 mm|两节串联型号|Wh|20 W / 10 W 分钟|","|---|---|---|---|"]
    for b in contract("A")["battery"]["candidates"]:
        lines.append(f"|{b['back_z']}|{b['model']}|{b['Wh']}|{b['runtime_20W_min']} / {b['runtime_10W_min']}|")
    lines.append("两节裸芯不带板，BAT+ / MID / BAT− / NTC。中档限 4.8 A、默认充电 0.7 A；20 W × 1.3 h 需 36–39 Wh。NTC R25/B、25°C DCIR、充放温度及带板替代品过流点待包厂回复。")
    return lines
def report(f,m,j):
    a=j['variant']=='A';v=j['variant'];lo,hi=m['assemblyBounds'];sz=[y-x for x,y in zip(lo,hi)];ck=m['checks'];h=j['harness']
    lines=[f'# v0.5 {v}｜机顶补光灯＋全贴合背夹','',f'整机含角扣外形 **'+' × '.join(f'{k:.2f}' for k in sz)+f' mm**，附件增重 **{m["totalMass"]:.2f} g**（含 3 g 线胶余量，不含手机、外接电源）。灯头主体 **70.6×44.0×28.4 mm**；含左侧被动铝翼及右耳全宽 **112.45 mm**，屏侧功率插头三槽使局部总深达 **41.15 mm**；最近边 Y−13，即 G=13；中心 Y−35，光轴 +Z。背夹从背玻璃算最高 **{j["enclosure"]["back_height"]:.1f} mm**（不含灯头）；手机外形为简化参照。','',
    '## 热预算：目标而非实测','|头部负荷 W|允许热点到环境热阻 K/W（35→82°C）|','|---|---|']+[f'|{w}|{r}|' for w,r in zip(j['thermal_budget']['head_design_load_W'],j['thermal_budget']['max_R_hotspot_ambient_K_W'])]+['≤5 W 停转，5–10 W 低速，其上正常转。下表为估算，尚无装机实测工作点或各档温度，不作为连续额定；握持≤48°C、塑壳≤55°C 待验。','背夹预计耗散 '+str(j['partition']['back_loss_W'])+' W；外露铝盖。']
    t=j['thermal_budget'];lines+=[t['fan'],t['source'],t['method'],'|负荷 W|rpm|CFM / Pa|热点估算 °C|风机估算 dBA|','|---|---|---|---|---|']+[f"|{r['load_W']}|{r['estimated_rpm']}|{r['estimated_CFM']} / {r['pressure_Pa']}|{r['estimated_hotspot_C']}|{r['fan_noise_est_dBA']}|" for r in t['rows']]+['左翼外露，不能作为握持面，需验裸露金属触温。各档是热点模型，不是焊点和 NTC 分别实测值；不能把暂停充电或降额当满足必达指标。以手机右上角 (70.6,0) 作代理，转子中心 (20.8,−36.6) 平距 61.8 mm，磁传感器精确位置未知；指南针实测为放行条件。',str(j['head_power_contact'])]
    gr=t['grip_estimate'];lines.append(f"背盖暴露面积 {gr['area_m2']*1e4:.1f} cm²；35°C 环境、综合换热系数 8 / 12 W/(m²·K) 时，估算盖温 {gr['uncovered_surface_C_at_h8']} / {gr['uncovered_surface_C_at_h12']}°C；压到 48°C 需要 ≥{gr['h_required_W_m2K']} W/(m²·K)。手遮挡及塑壳热桥另测，A 在弱换热条件不满足。")
    if a:lines+=['## 电池候选（按电池舱高度）','']+battery_lines()
    else:lines+=['C 无内置电池：外部单口 20 V/3 A PD 满配，8 V 前端 ≥6 A；表内其余档位先限手机。拔线即灭。']
    lines+=['','## 自检','',f'数模检查 **{sum(c["ok"] for c in ck)}/{len(ck)}**，不等于抗跌、射频、温升或实物验收。','','|项目|结论|读回或判据|','|---|---|---|']+[f'|{c["name"]}|'+('通过' if c['ok'] else '**不通过**')+'|'+c['value']+'|' for c in ck]
    lines+=['','## 清单一｜给电气侧','三板 TOP 全部朝 +Z，以板框左下 BOT 为原点，整机 X=Ox+u，Y=Oy−v。两版驱动与灯板板框、孔、局部坐标、局部限高和针序共用。主板 60×23.5、USB-C 边不改；仅整体 Z 改变。','|板|左下 BOT 整机坐标|','|---|---|']+[f'|{k}|{b["origin"]}|' for k,b in j['boards'].items()]
    lines+=['','|板端／接口|板面 u,v|整机 TOP x,y,z|插拔/引出方向 XYZ|插合高预算|','|---|---|---|---|---:|']+[f'|{e["ref"]} {e["type"]}|{e["uv"]}|{e["xyz"]}|{e["direction_xyz"]}|{e["mated_height_budget_mm"]}|' for k in ('power','signal') for e in h[k]['endpoints']]
    from v11_contact import note
    lines+=['',note(),'',str(j['partition']), '芯号 1–12：'+' / '.join(h['pinout']),h['cut_note'], '60°C 回路估算 mΩ：'+str(h['rail_loop_mohm']),h['connector_candidate'],h['single_open']]
    lines+=['','## 清单二｜头方本地复核','下表取区间内全部实体的最坏值，以该区左端上限作保守判定。背面仅在手机背面投影内；G 表含颈肩和外侧过渡。超过外闪软线不作为硬判失败。','','|Y 区间|背模块最高 Z|扣 1.5 后限值|','|---|---:|---:|']+[f'|{x}…{X}|{z}|{lim:.2f}|' for x,X,z,lim in j['back_profile']]
    lines+=['','|G 区间|实际向背 / 屏侧|扣 1 后硬限 背 / 屏|外闪软限|','|---|---:|---:|---:|']+[f'|{g}…{G}|{z} / {s}|{l:.2f} / {L:.2f}|{soft}|' for g,G,z,s,l,L,soft in j['head_profile']]
    lines+=['','右轨包络 '+str(h['external_rail_bbox'])+'；整条主干 '+str(h['trunk_bbox'])+f'；中心线 {h["trunk_length_mm"]:.1f} mm，弯头内侧设计 ≥5 mm。Y≥46 处出背夹，沿右外轮廓跨天线区，不把全线包围盒误当实际铜体。复核跨顶短段、右上指南针、侧键、头内金属、盖顶与顶轨；检查超广角、雷达、原闪光灯、RF、Wi-Fi、底麦、OIS 和对焦。佩戴不支持 MagSafe/Qi，拍摄请关闭自带闪光灯。','所有导电节点包络（含导线包络和电池铝塑膜，单位 mm）：','','|节点|最小 XYZ|最大 XYZ|','|---|---|---|']+[f'|{k}|{u}|{w}|' for k,(u,w) in j['conductive_bounds_xyz'].items()]
    lines+=['','机顶每 1 mm 剖面（按实体弦差 0.025 mm 的网格插切；硬边界见上方实体分区）。','|G|向背 mm|超出屏幕面 mm|','|---:|---:|---:|']+[f'|{g}|{r}|{f}|' for g,r,f in j['head_profile_1mm']]
    back=json.loads((f.parent/'back_profile_1mm.json').read_text())
    lines+=['','背夹逐毫米剖面（角扣计入，外侧线轨与线束另列；重复高度合并展示）。','|Y 起…止|最高 Z mm|','|---|---:|']
    from itertools import groupby
    for z,group in groupby(back,key=lambda r:r[1]):
        rows=list(group);lines.append(f'|{rows[0][0]}…{rows[-1][0]}|{z}|')
    lines+=['','跨顶段每一折点（中心 XYZ）；截面额外偏置：直轨相对中心 X=−3.8…+3，Z=±1.8；线束 X=±2.8，Z=±0.95。','|X|Y|Z|','|---:|---:|---:|']+[f'|{x:.3f}|{y:.3f}|{z:.3f}|' for x,y,z in h['centerline_xyz'] if -38<=y<=46]
    f.write_text('\n'.join(lines)+'\n')
def website(m,j,web_root=None):
    v=j['variant'];a=v=='A';s='_battery' if a else '';page='battery.html' if a else 'index.html';web=web_root or R/'web'
    template=(R/'mech/baselines/view05.template').read_text()
    template=template.replace('连续 20 W 为设计目标，不是实测额定。','35°C 连续满配是设计目标，风机装机工作点与温度尚未验收。左侧疏齿铝翼是停扇散热面；勿遮挡、勿握持。')
    template=template.replace('REVISION',v+'5-r2').replace('SCRIPT','app'+s+'.js').replace('VARLABEL',v+' · '+('内置换电' if a else '外接 PD')).replace('MASS',f'{m["totalMass"]:.2f}').replace('HEIGHT',str(j['enclosure']['back_height'])).replace('POWERINFO',('两节 1.4 Ah 软包串联；20 W 单灯约 %.1f 分钟，10 W 约 %.1f 分钟，20 W 加手机约 %.1f 分钟。'%(j['battery']['candidates'][1]['runtime_20W_min'],j['battery']['candidates'][1]['runtime_10W_min'],runtimes(1.4)[2])) if a else '60 W 外部 PD 满配；不内置电芯，拔线即灭。')
    (web/page).write_text(template);app=(R/'mech/baselines/view05.js.template').read_text().replace('SUFFIX',s).replace('REVISION',v+'5-r2').replace('GROUPS',repr(list(dict.fromkeys(r['group'] for r in m['parts']))))
    (web/('app'+s+'.js')).write_text(app)
def readme():
    text=['# v0.5｜PCB 机械交接','', 'C（外接电源）和 A（换包）均为机顶发光，驱动板和灯板只制作一套，板坐标不因整机平移而变。DXF 为 R2010/mm，BOARD_OUTLINE 导板边，孔、固定器件、连接器、两面禁区和限高各自分层。正视 TOP：u 向右、v 向上；装配 STEP 为 (X,−Y,Z)。不能按结构框造焊盘。','', '|板|外形 / 厚|左下 BOT 整机 XYZ|TOP|','|---|---|---|---|','|C/A 主板|60×23.5 / 1|(5.3,125.8,4.7)|+Z|','|共用驱动|60×40 / 1.6|(5.3,−15,−14.5)|+Z|','|共用灯板|62×34 / 1.6|(4.3,−19,7.0)|+Z|','', '按 main / main_battery 区分主板，driver、led 图共用。assembly_layout[_battery] 和 enclosure_assembly[_battery].step 分别给 XY 与三维。两个 PCB 接口 JSON 的 harness 含 12 芯、电阻、两端板/整机坐标、插拔及高度。灯板五线、风扇和温控留在头内。','C 三键五灯在主板，A 在盖面用九线 J6。两个 USB-C 口均朝 +Y。Q_TIM 11×3.2，封装 +2.2、压垫 0.6，热量向外。A 六针 J5 每针 ≥5 A：BAT+、BAT+、MID、NTC、BAT−、BAT−，插合 ≤14.5 mm。C 为 8 V 稳压；A 为 BQ25798 系统电压，PD 表待电气侧给出。定版前请核对料号、公差、线材与接触电阻、保险和充电电流。']
    text+=['','## 定位与限高','坐标单位 mm。下表给板端 TOP 上的中心位置，不是采购件焊盘。禁止移动灯窗、LED 光心、孔、两个 USB-C、键灯和 Q_TIM 接触区；各信号座型与线径需以插合状态实配。局部限高 / 禁区、引脚一和极性以本版 DXF 与 JSON 为准。']
    for v in 'CA':
        j=contract(v);h=j['harness'];text+=['','### '+v,'|线束端|板面 u,v|整机 x,y,z|拔出方向|插合高上限 mm|','|---|---|---|---|---|']
        for k in ('power','signal'):
            for e in h[k]['endpoints']:text+=[f'|{e["ref"]}|{e["uv"]}|{e["xyz"]}|{e["direction_xyz"]}|{e["mated_height_budget_mm"]}|']
        text+=['1–12：'+' / '.join(h['pinout']),h['cut_note'],'AWG24 ×6，AWG30 ×6；60°C 回路估算 mΩ：'+str(h['rail_loop_mohm']),h['connector_candidate'],h['single_open']]
    from v11_contact import note
    text+=['',note()]
    (PCB/'README.md').write_text('\n'.join(text)+'\n')
    (R/'mech/README.md').write_text('''# 机顶补光灯与全贴合背夹 · v0.5

运行仓库内的 `mech/build.sh all` 后运行 `mech/web.sh`。前者生成两版 STEP/STL、装配、GLB、板图与接口；后者使用随仓库的 three.js 读回网页模型、检查脚本与静态资源。`mech/web.sh serve 8000` 可在本机浏览。无需下载文件。

- **C**：外接 PD，主板在背夹内；**A**：增加可更换 2S 软包及托盘。灯头位于手机顶边上方，共用相同灯板、驱动板、风机和散热鳍。
- `out/report.md`、`out/report_battery.md`：测得的装配尺寸、质量预算、导电包络、逐毫米头部剖面、温升估算和降额条件。
- `out/` 为 C 打印件，`out/battery/` 为 A 打印件；配套 STEP 与 STL 使用实际装配坐标。头盒与前圈用 ASA，内衬 TPU，底壳与盖按件级材料及朝向打印；建议先打卡角、热熔嵌件及扣口试片。
- `pcb/`：两版主板分别出图，灯板与驱动板共用；含整机 STEP、DXF、PNG、机器可读的板框/接头定义及两端线束合同。
- `out/round11/final/`：两版装配 STEP 的两两交集、分段轮廓、单件灯头 STEP 和共用件证据。`out/archive_v04_final/` 含上一版制造文件、源码、网页和校验清单；回退请从留档副本恢复，不覆盖原始档。
- 仅采用公开手机简化外形和允许的包络；装机取景、天线、声学、指南针、手温、跌落和电池保护仍需实样。几何检查不得替代热箱或手持测试。
''')
