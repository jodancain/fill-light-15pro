"""灯板 TOP 接触面，单位 mm；矩形只占直边，避开 R2 圆角。"""
EDGES = {'left':[0,2,.8,32], 'right':[61.2,2,62,32],
         'bottom':[2,0,60,.8], 'top':[2,33.2,60,34]}
RULE='绝缘 ASA 平压条（与灯头壳同料），平面均压于阻焊；允许阻焊完整覆盖的铜线，禁止露铜、焊盘、过孔。'
PRELOAD='背面绝缘导热垫 0.50→0.40 mm（20%）；以超软垫在此压缩率的目标应力 10 kPa、约 2100 mm² 估算总力 21 N，四边按长度分配。须按采购垫压缩曲线、压敏纸及热循环后板翘复核，不是已测夹力。'
def apply(b):
    b['holes']=[]; b['clamp']=dict(side='TOP',material='ASA',face='flat',width_mm=.8,rect_uv_mm=EDGES,rule=RULE,preload=PRELOAD,masked_copper=True,exposed_copper=False,pads=False,vias=False)
    b['keepouts'] += [dict(id='CLAMP_'+k,side='TOP',rect=r,why=RULE,mode='no_parts') for k,r in EDGES.items()]
    for led in b['leds']:led['assignment_status']='串号、串内顺序及极性朝向为参考，电气侧可调'
    pins=[[60,round(28-i*2.54,2)] for i in range(5)]; c=b['connectors'][0];c.update(center=[60,22.92],rect=[59.3,17.22,60.7,28.62],pins=pins,pin1=pins[0],pin_count=5,type='5 焊盘向右侧出线',direction=[1,0,0],nets=['LEDC_P','LEDW_P','LED_N','NTC_RTN','NTC_LED'],pad_size_uv_mm=[1.4,1.24],alternative='若用六线，两相邻 LED_N 焊盘需电气重新定版')
    b['fixed'][0].update(center=[59.4,15.2],rect=[58.4,14.575,60.4,15.825])
def note():
    return '\n'.join(['## 无孔灯板：压框与布线','四边各压 0.8 mm，四角让空；上下支撑防止薄板中跨翘起，侧边母线不必因压框改道。','|边|u (mm)|v (mm)|','|---|---|---|']+[f'|{k}|{x:g}–{X:g}|{y:g}–{Y:g}|' for k,(x,y,X,Y) in EDGES.items()]+[RULE,'W_P 可经过 u=0.3–0.8 的重叠区；该区不得开阻焊窗。',PRELOAD])
