"""v0.4-C 的结构/系统分配；未有物料图的尺寸是选型包络，非供应商精确几何。"""
VARIANT='C'
FAN=(9.3,44.3,66.9,101.9,7.5,17.5)  # 35×35×10，向 +x 侧排、从 −z 进气
FIN=(44.85,65.8,6.15,18.2)       # 起止 x / 底顶 z；铝基座另厚 1.2
PORT_Y=(68.8,74.15,79.5,84.85,90.2,95.55); PORT_RUN=4.0
AIR_IN=(5.05,16.85); AIR_OUT=(6.15,18.2)
AUX_Y=(108.,113.2,119.9); AUX_DY=3.; AUX_Z=(7.3,11.8) # 下层驱动舱两侧独立对流，不叠加到主动风量
# 充电宝电池端与背夹 J1 口面分开预算；合同的 10% 留给压降、限流误差和瞬态。
POWER=dict(input_eff=.92,led_eff=.88,phone_eff=.90,aux_w=2.,contract_use=.90,
           led_w=20.,phone_v=5.,phone_a=3.,internal_wh=0.,rail_v=8.,rail_a_min=6.)
def load(led,phone):
    return (led/POWER['led_eff']+phone*POWER['phone_v']/POWER['phone_eff']+POWER['aux_w'])/POWER['input_eff']
def policy(v,a):
    rail=v*a*POWER['contract_use']*POWER['input_eff']-POWER['aux_w']
    for phone in (3.,1.5,0.):
        if rail>=20/POWER['led_eff']+phone*5/POWER['phone_eff']:return 20.,phone
    return max(0,int(rail*POWER['led_eff'])),0.
