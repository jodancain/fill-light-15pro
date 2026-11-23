"""v0.4 板级母数据：所有平面坐标均为器件面左下角的 (u,v)，单位 mm。"""
import math
from v04_config import *
def contract(spec,p,T):
    L=spec['layout']; H=spec['harness']
    def board(id,name,size,r,th,layers,mat,origin,top,bot):
        return dict(id=id,name=name,size=list(size),corner_radius=r,thickness=th,layers=layers,material=mat,
          origin=origin,axes={'u':[1,0,0],'v':[0,-1,0],'top':[0,0,1]},origin_surface='BOT',
          holes=[],connectors=[],fixed=[],leds=[],keepouts=[],height_zones=[dict(id='BASE',rect=[0,0,*size],top=top,bot=bot,why='通用工作限高；局部覆盖区优先，禁布区始终优先')])
    mb=L['main_board']; fx=mb['x'][0]; fy=mb['y'][1]
    M=board('main','电源与控制主板',[mb['x'][1]-fx,fy-mb['y'][0]+MAIN_EXTRA],1.5,mb['pcb_thickness'],4,'FR-4',[fx,fy,MAIN_Z],min(7.5,mb['height_out_max']),1.2)
    dw,dh=L['driver_board']['size']; D=board('driver','双路恒流驱动板',[dw,dh],0,L['driver_board']['pcb_thickness'],4,'FR-4',list(DRIVER_O),5.5,0)
    D['stack_note']='TPS92692-Q1 双路；L2 完整地平面，BOT 不贴件'
    D['budget']=[dict(type=n,w=w,h=h,count=c) for n,w,h,c in [('TPS92692-Q1',6.5,6.4,1),('开关 NMOS',5,6,1),('SMB 包络',5.5,3.8,1),('电感',10,10,1),('输出 1210',3.2,2.5,4),('输入 1210',3.2,2.5,3),('2512 采样',6.3,3.2,1),('调光 PMOS',5,6,1)]]
    lw,lh=LED_WH; E=board('led','双色铝基灯板',[lw,lh],2,L['led_board']['pcb_thickness'],1,'铝基覆铜板',list(LED_O),1.0,0)
    def rect(c,s):return [round(c[0]-s[0]/2,4),round(c[1]-s[1]/2,4),round(c[0]+s[0]/2,4),round(c[1]+s[1]/2,4)]
    def conn(b,ref,name,c,size,h,nets,pitch,vec,pattern='row',status='坐标锁定；封装/焊盘待 ECAD 按最终型号核对',node=None):
        n=len(nets)
        if pattern=='2x2':
            pins=[[c[0]+(j%2-.5)*pitch,c[1]+(.5-j//2)*pitch] for j in range(n)]
        elif pattern=='usb':
            # 外形/口向锁定，不把假定焊脚当作厂家 land pattern。
            pins=[None]*n
        else:pins=[[c[0]+(j-(n-1)/2)*pitch,c[1]] for j in range(n)]
        pin1=pins[0] or [c[0]-size[0]/2+.65,c[1]+size[1]/2-.6]
        d=dict(ref=ref,type=name,center=list(c),rect=rect(c,size),height=h,pin_count=n,pitch=pitch,
          pin1=pin1,pins=pins,direction=vec,pattern=pattern,nets=nets,status=status,node=node or b['id']+'_'+ref.lower())
        b['connectors'].append(d);return d
    def fixed(b,ref,name,c,size,h,kind='box',node=None):
        b['fixed'].append(dict(ref=ref,name=name,center=list(c),rect=rect(c,size),height=h,shape=kind,side='TOP',
                               node=node or b['id']+'_'+ref.lower()))
    def ko(b,id,side,r,why,mode='no_parts'):
        b['keepouts'].append(dict(id=id,side=side,rect=list(r),why=why,mode=mode))
    def zone(b,id,r,t,bh,why):
        b['height_zones'].append(dict(id=id,rect=list(r),top=t,bot=bh,why=why))
    # USB 网络名只是功能；未知引脚保留空值，不替电气侧定料。
    for j,(node,port) in enumerate(L['ports'].items(),1):
        name='输入' if j==1 else '输出'; vb='VBUS_IN' if j==1 else 'VBUS_OUT'
        nets=['GND',vb,'CC1',None,None,None,vb,'GND','GND',vb,'CC2',None,None,None,vb,'GND']
        u=port['x']-fx; v=fy-port['y']+p.usb[2]/2
        item=conn(M,'J'+str(j),name+' USB-C 口',(u,v),(p.usb[0],p.usb[2]),p.usb[1],nets,None,[0,-1,0],'usb',
                  '拟按 16 接点 USB2 型机械占位；A1 标记为方向基准，不是厂家焊脚坐标。以实选封装为准',node)
        item['contacts']=['A1','A4','A5','A6','A7','A8','A9','A12','B1','B4','B5','B6','B7','B8','B9','B12']
        item['port_mouth']=[u,0]
    pw=list(H['power']); sig=list(H['signal']); out=list(H['led_board'])
    conn(M,'J3','2×2 功率卧座候选',(51.7,10.2),(9,7),7.5,pw,3,[-1,0,0],'2x2')
    conn(M,'J4','8P 带锁卧座',(29.4,9.6),(11.8,4.4),4.5,sig,1.25,[0,-1,0])
    conn(M,'TP1','调试触点',(5.9,4.6),(8.3,1.7),.1,[None]*6,1.27,[0,0,1],status='6 个触点预留，针序待确认；拆罩探测，装好后由罩盖住')
    M['connectors'][-1]['functional_requirements']=['3V3','GND','SWDIO','SWCLK','NRST','UART（单线/双线待确认）']
    zone(M,'PD_POWER',[3.5,18.5,19.5,23.5],2.2,1.2,'原电池座区域让给 PD 输入稳压与测温，不作完整电源级的面积承诺')
    fixed(M,'L_IN','输入级屏蔽电感占位',(15.75,10.55),(7,7),5.5,'box','input_choke')
    fixed(M,'Q_TIM','功率封装接触面占位',(11.5,21.25),(11,3.2),2.2,'box','power_contact')
    zone(M,'INPUT_L',[12.15,6.95,19.35,14.15],5.5,1.2,'输入级磁件开发包络；须核峰值饱和与发热')
    ko(M,'MATE3','TOP',[36,6.7,47.2,13.7],'J3 插合与拔出空间；须在合罩前操作')
    ko(M,'MATE4','TOP',[23.5,.4,35.3,7.4],'J4 插合空间')
    for i,(u,v) in enumerate([(u,v) for u in (0,60-p.foot[0]) for v in (p.foot[1],21-sum(p.foot))]):
        ko(M,'FOOT'+str(i+1),'BOTTOM',[u,v,u+p.foot[0],v+p.foot[0]],'绝缘支脚接触面：不放器件/露铜')
    for i,(u,v) in enumerate([(u,v) for u in (0,58.5) for v in (2.2,16)]):
        ko(M,'CLIP'+str(i+1),'TOP',[u,v,u+1.5,v+1.8],'罩内压脚压板边，不放元件或露铜')
    for i,s in enumerate(L['buttons'],1):
        fixed(M,'SW'+str(i),s['name']+'开关同轴中心',(s['x']-fx,fy-s['y']),(2*p.button_r,)*2,3,'circle','key_'+str(i))
    ki=L['indicators']
    for i in range(ki['count']):
        u=ki['x'][0]+i*(ki['x'][1]-ki['x'][0])/(ki['count']-1)-fx
        fixed(M,'D'+str(i+1),'电源状态灯／导光柱中心',(u,fy-ki['y']),(2*p.light_r,)*2,.8,'circle','light_'+str(i+1))
    for b,holes,dia,keep,kind in [(D,[(u,v) for v in (2.5,dh-2.5) for u in (2.5,dw-2.5)],2.3,6,'M2'),
                   (E,[(u,v) for v in (6.6,lh-6.6) for u in (2.4,lw-2.4)],2.8,4,'M2.5')]:
        for j,c in enumerate(holes,1):b['holes'].append(dict(ref='H'+str(j),center=list(c),drill=dia,keep_d=keep,kind=kind,plated=False,keepout_sides=['TOP','BOTTOM'],forbid=['copper','components']))
    conn(D,'J1','2×2 线阵，侧引出至带锁线对线接头',(55.0,10.7),(8.4,8.2),2.5,pw,3,[-1,0,0],'2x2')
    conn(D,'J2','8P 带锁卧座',(44.5,18.5),(11.8,4.6),4.5,sig,1.25,[0,-1,0])
    conn(D,'J3','灯板出线焊盘',(18.5,18.6),(14.6,2),1.2,out,2.54,[0,1,0])
    conn(D,'J4','风扇 4P 座',(31.5,18.4),(6.5,3.8),4.5,['5V','FAN_GND_SW','FAN_TACH','NC_PWM'],1.25,[0,0,1])['note']='针序以电气原理图为准；第 4 针预留 PWM'
    conn(D,'J5','85°C 常闭开关引线焊盘',(4.2,11.5),(4.4,2.0),1.2,['DRV_EN_IN','DRV_EN_SAFE'],2.54,[-1,0,0],status='网名为过温串联两端的功能别名，电气侧定最终名')
    ko(D,'MATE2','TOP',[38.6,9,50.4,16.2],'信号插头水平插合占位')
    ko(D,'BACK','BOTTOM',[0,0,dw,dh],'底面不贴器件；并非全板禁铜')
    for j,hole in enumerate(D['holes'],1):
        u,v=hole['center'];a,bx=(0,u) if u<dw/2 else (u,dw)
        ko(D,'SHOULDER'+str(j),'TOP',[a,v-2.2,bx,v+2.2],'M2 铜母肩延伸至侧壁')
    for i,(a,bx) in enumerate([(6.6,22.4),(22.7,38.5)]):
        zone(D,['PWR_W','PWR_C'][i],[a,.4,bx,16.4],5.5,0,'单路 20 W；电感、续流管、电容')
        fixed(D,['L_W','L_C'][i],'屏蔽功率电感最大占位',(a+5.5,7.5),(10,10),5.5)
    zone(D,'FAN_BUCK',[39.5,1,50,8],5.5,0,'风扇 5 V 降压与去耦')
    zone(D,'J1_BAY',[50.3,6.2,59.7,15.1],5.5,0,'功率焊线侧出，不装竖直座')
    for u in (0,lw-p.shelf[0]):ko(E,'LIP'+str(int(u)),'TOP',[u,.5,u+p.shelf[0],lh-.5],'侧压边筋，不布器件')
    ko(E,'THERMAL','BOTTOM',[0,0,lw,lh],'整个铝背贴合散热器：不放器件、端子或焊脚')
    conn(E,'J1','六根线侧出表贴焊盘',(43,1.25),(14.5,1.5),1.0,out,2.54,[0,-1,0])
    fixed(E,'RT1','灯板测温 NTC',(31,17),(2,1.25),.9)
    nx,ny=L['led_board']['grid'];dx,dy=PITCH
    for j in range(ny):
        for i in range(nx):
            c=[round(lw/2+(i-(nx-1)/2)*dx,3),round(lh/2+(j-(ny-1)/2)*dy,3)]
            col='W' if (i+j)%2==0 else 'C';sg=1 if j%2==0 else -1
            E['leds'].append(dict(ref=f'D{j*nx+i+1:02}',center=c,rect=rect(c,(3,3)),color=col,
              kelvin=2700 if col=='W' else 6500,string=f'{col}{j+1}',order=(i//2+1 if sg==1 else 6-i//2),
              anode=[c[0]-sg*1.15,c[1]],cathode=[c[0]+sg*1.15,c[1]],height=p.led_xyz[2],mpn='YJ-BC-3030-G04'))
    return {b['id']:b for b in (M,D,E)}
def xy(b,uv):return (b['origin'][0]+uv[0],b['origin'][1]-uv[1])
def absrect(b,r):return (b['origin'][0]+r[0],b['origin'][0]+r[2],b['origin'][1]-r[3],b['origin'][1]-r[1])

