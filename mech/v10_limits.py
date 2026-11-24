"""热预算为设计估算（不等于单机温升合格）；尺寸 mm，额定电流 A。"""
import math
from v05_layout import CAND,runtimes
def candidates():
    out=[]
    for i,(model,t,w,l,ah,rate,g) in enumerate(CAND):
        h=[17.0,21.7,23.9][i]
        out.append(dict(model=model,cell_TWL=[t,w,l],Ah=ah,Wh=round(7.4*ah,2),pair_mass_g=2*g,runtime_min=[round(m,1) for m in runtimes(ah)],back_z=h,top_y=[62.8,62.8,64.8][i],continuous_A=round(rate*ah,2),max_design_A=4.8,proposed_charge_A=round(.5*ah,3),note=['改低型/线端 J5 与面板，非现盖减薄','推荐，当前结构','后移盖前缘、重做电池托盘'][i]))
    return out
def therm(a):
    # 外表有效面积预算；不计贴手机的面。辐射/对流需按实际涂层、方向验证。
    # C: 18 条长 31.5mm 高 6mm 的外鳍；A: 10 条长 8mm 高 2.2mm 尾鳍。
    base=.00090 if a else .00290
    faces=(2*10*8*2.2 if a else 2*18*31.5*6)*1e-6
    eff=base+.60*faces
    r=1/(9*eff)+1.5
    lim=(48-35-2)/r
    return dict(ambient_C=35,surface_limit_C=48,control_target_C=46,source='工程估算，实机热箱验证前适用保守限额',continuous_lamp_C_35C_phone_off_W=(None if a else math.floor(max(0,(lim/(1/.92-1)-2)*.88)*10)/10),base_m2=base,fin_faces_m2=faces,eff_m2=eff,R_K_W=r,loss_max_W=lim,continuous_out_W=lim/(1/.92-1),charge_current_A=math.floor(100*min(.7,lim/(8.4*(1/.90-1))))/100,T_at_2W=35+2*r,T_at_3W=35+3*r)
def thermal_text(a):
    t=therm(a)
    return ('35°C 环境，不计手机、手掌和被遮盖的一面。取黑化外露表面 h=9 W/(m²·K)，鳍间效率 0.60、扩散裕量 1.5 K/W。可用有效面积 %.0f mm²，等效热阻 %.1f K/W。以 46°C 为控制目标留 2°C 裕量，连续耗散预算 %.2f W。'%(1e6*t['eff_m2'],t['R_K_W'],t['loss_max_W']))+(
      'A：按 8.4 V、充电效率 90%%，0.7 A 充电损耗约 0.65 W；按握持约束，独立充电先限 %.2f A（未扣其他板损耗），并发负载从热预算扣除；电芯温度达到 45°C 禁充，放电上限 60°C。'%t['charge_current_A'] if a else
      'C：2 / 3 W 耗散时保守预测握持面约 %.0f / %.0f°C，不能连续满载。按 92%% 效率，转换前端连续总输出先限 %.1f W；减去风机/控制 2 W，关手机口后的连续灯功率约 %.1f W（灯驱 88%%）。'%(t['T_at_2W'],t['T_at_3W'],t['continuous_out_W'],max(0,(t['continuous_out_W']-2)*.88)))+' 高温、横握遮鳍还要动态降额，板温与握持面热电偶标定后才能开放 20 W；48°C 硬停。'
