"""第十一轮分区；公共板只标芯号，实际网络由变体装配表绑定。"""
from math import dist
from v05_route import path

def apply(j,pos):
    a=j['variant']=='A'; boards=j['boards'];main=boards['main'];drv=boards['driver'];h=j['harness']
    pn=['BAT+','BAT+','GND','GND','VBUS','VPHONE'] if a else ['VIN','VIN','GND','GND','VPHONE','VPHONE'];sn=['SCL','SDA','INT_N','FAULT_N' if a else 'PD_OK','CC1','CC2']
    for name,refs,nets in [('power',('J3','J1'),pn),('signal',('J4','J2'),sn)]:
        bundle=h[name];bundle.update(count=6,nets=nets);bundle.pop('twist',None)
        for board,ref,ep in zip((main,drv),refs,bundle['endpoints']):
            t=next(x for x in board['connectors'] if x['ref']==ref);u,v=t['center'];power=name=='power';pitch=2 if power else 1.25
            pins=([[u+dx,v+dy] for dy in (1,-1) for dx in (-2,0,2)] if power else [[u+(i-2.5)*pitch,v] for i in range(6)])
            t.update(type='6P 功率焊线区' if power else '6P 信号卧座',pattern='2x3' if power else 'row',pitch=pitch,pins=pins,pin1=pins[0],pin_count=6,nets=nets if board is main else ['芯'+str(i) for i in (range(1,7) if power else range(7,13))]);ep.update(type=t['type'],nets=nets,xyz=pos(board,t['center']))
        j['connection_endpoints_xyz']['功率' if name=='power' else '慢速信号']=[e['xyz'] for e in bundle['endpoints']]
    run=path();length=sum(dist(p[:3],q[:3]) for p,q in zip(run,run[1:]));h['trunk_length_mm']=round(length,2);h['pinout']=pn+sn
    h['cut_note']='245 mm 含两端短引线及服务余长；主干中心线 %.2f mm。'%length
    r=h['copper_loop_mohm_at60'];h['contact_pair_budget_mohm']=10;h['rail_loop_mohm']={n:round((r+10)*(1.5 if a and n in ('VBUS','VPHONE') else 1),2) for n in (('BAT+','VBUS','VPHONE') if a else ('VIN','VPHONE'))};h['power']['inline_pairs']=[[1,3],[2,4],[5,6]];h['connector_candidate']='功率服务接口改三组独立两路 Micro-Fit 3.0：43025-0200 ×3 配 43020-0200 ×3；43030-0007 / 43031-0001 压接 AWG24。P1=(1,3)，P2=(2,4)，P3=(5,6)；P3 必须采用机械防错分隔，不得仅靠颜色。PS-43045 §4.3 两路线对线、全载参考 5 A/针、温升 ≤30 K；镀锡端子 105°C 含自热，设计局部环境上限 75°C。三组应分开而非捆扎，实际壳温及压接温升须验证；头壳屏侧一体三槽，三个量规各 11×25×10.9 mm，槽间中心距 16 mm，整组装线防交叉；名义插长 24.77 mm。量规不是厂商精确 STEP，压线、实际固定、防误插和退插行程须实配。';h['single_open']='BAT+/GND 并联失一针时余针 4.4–4.8 A，小于独立双路的 5 A 参考值（最小余量 0.2 A）；C 余针 3 A。单根 VBUS/VPHONE 断开为断路，并非冗余。环境高于 75°C 或并排升温不得按此参考放行。';h['internal_only']=['灯板五线','风扇调速和测速','升压开关节点','85 °C 温控'];j['fan_bbox']=[3.3,38.3,-54.1,-19.1,-4.9,5.1]
    l=next(x for x in main['fixed'] if x['ref']=='L_IN');main['fixed'].remove(l);l.update(center=[31.5,27],rect=[28,23.5,35,30.5]);drv['fixed'].append(l);main['height_zones']=[x for x in main['height_zones'] if x['id'] not in ('INPUT_L','PD_POWER')];q=next(x for x in main['fixed'] if x['ref']=='Q_TIM');q['name']='保护通路导热接点' if a else '输入开关导热接点';j['thermal_contact']['usage']=q['name'];j['partition']=dict(head=['BQ25798' if a else 'LM5176','TPS25830A','MCU','TPS92692-Q1 ×2','风扇驱动','85 °C 温控'],back=['STUSB4500','USB-C ×2','口保护','I²C 三键五灯']+(['J5','两级保护、反接、采样、硬限、过温、ADC'] if a else ['输入开关']),back_loss_W=.44 if a else .25);j['thermal_budget']=dict(ambient_C=35,back_loss_W=.44 if a else .25,head_design_load_W=[3.8,7.7,17.8 if a else 17.0]+([18.6] if a else []),max_R_hotspot_ambient_K_W=[round(47/w,3) for w in ([3.8,7.7,17.8,18.6] if a else [3.8,7.7,17])],qualification='负荷及允许热阻不是工作点。装机风量、握持和塑壳温度未验证。')
    drv['fixed'].append(dict(ref='Q_HEAD',name='共用冷板功率封装包络',node='head_power_device',shape='box',side='TOP',center=[43.5,27],rect=[36,22,51,32],height=5.5))
    j['head_power_contact']=dict(side='TOP',rect_uv_mm=[36,22,51,32],size_mm=[15,10],device_top_z=-7.4,metal_z=-6.8,compressed_pad_mm=.6,path='器件顶→绝缘垫→铝鳍底梁→主鳍片；不向手机散热')
    j['enclosure']['head_bbox']=[-39,73.45,-57,-13,-29.55,11.6]
    from v11_air import budget
    j['thermal_budget'].update(fan='Delta BFB03505HHA-A，两线可调电源 4.0–5.5 V；低速点为转速比假设，调压后必须测转速。',source='Delta BFB03505HHA-A Rev01 §9',rows=budget(),method='26 片 0.4 mm 铲齿：25 条 0.8×11 mm 平行道，24 mm 长，进排各 6 个 3.3×14 mm 口，局部损失系数合计按脚本，忽略漏风。Nu=5，含局部让位、鳍效的有效面积系数 0.75，扩散与导热垫合计 0.45 K/W；停转增设左侧九片外露铝翼，每片宽 36、高 24、厚 0.9 mm，主段节距 5，端部补齿，铝翼根部六个通孔分别对准壳体进风口；环境换热系数假设 5 W/m²K，按直鳍效率及铝桥导热和内鳍并联，不能用手遮挡；内密齿自然对流 h=6，仅计 30% 齿面积，未计壳体附加散热。不是实测；噪声按转速比五次方估算。')
    # 平齐外铝面（扣面板窗口与四角）；仅模型，不把手机作为散热器。
    area=(59.05*60.15-54.85*6.75-(4-3.14159)*1.4**2)*1e-6
    loss=j['partition']['back_loss_W'];j['thermal_budget']['grip_estimate']=dict(area_m2=area,loss_W=loss,h_required_W_m2K=round(loss/(area*13),2),uncovered_surface_C_at_h8=round(35+loss/(8*area),1),uncovered_surface_C_at_h12=round(35+loss/(12*area),1),method='稳态等温盖、只算一面、忽略侧壁；h 含自然对流及辐射。握持遮挡改变边界，不能据此判定通过。')
    h['power']['inline_head']=dict(series='Micro-Fit 3.0 双路线对线 ×3',plug='43020-0200',receptacle='43025-0200',terminals=['43030-0007','43031-0001'],contacts_per_body=2,mated_length_nominal_mm=24.77,envelope_per_pair_xyz_mm=[11,25,10.9],centers_xyz=[[x,-42.5,-22.5] for x in (32.5,48.5,64.5)],extraction_xyz=[0,-1,0],pins_by_pair=h['power']['inline_pairs'],reference_A_per_pin=5,ambient_design_ceiling_C=75,qualification='AWG24，30 K 温升参考值；最终线束和最高局部环境需整机验证。')
    h['locking']='三组独立 2P 功率锁扣置于头壳屏侧线槽；信号用带锁 6P 卧座。'
    h['rloop_mohm_max']={'BAT+':40,'VBUS':60,'VPHONE':60} if a else {'VIN':60,'VPHONE':60}
