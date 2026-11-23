"""C 的台账：实形、外部插线量规和功率政策分别计算，软线未知姿态不算作通过。"""
from pathlib import Path
import numpy as np
from c04 import *
def run(ck,bb,sh,inter,env,parts,OUT,ROOT):
    from model import box,cyl,pack
    from build123d import Compound,export_step,import_step
    from export import native_shape,bounds
    n=len(PORT_Y)
    def vent(x,X,span):
        return all(inter(sh('shell'),box(x,X,y+.02,y+PORT_RUN-.02,span[0]+.02,span[1]-.02))<.001 for y in PORT_Y)
    ck('横向进排风开口',vent(-1,2,AIR_IN) and vent(68,72,AIR_OUT),f'各 {n} 孔，窄边 {PORT_RUN:g}；进/出侧开口 {n*PORT_RUN*(AIR_IN[1]-AIR_IN[0]):.1f} / {n*PORT_RUN*(AIR_OUT[1]-AIR_OUT[0]):.1f} mm²。不是风量。')
    ck('驱动舱对流侧槽',all(inter(sh('shell'),box(x,X,y+.02,y+AUX_DY-.02,AUX_Z[0]+.02,AUX_Z[1]-.02))<.001 for x,X in [(-1,2),(68,72)] for y in AUX_Y),f'两侧各 {len(AUX_Y)*AUX_DY*(AUX_Z[1]-AUX_Z[0]):.1f} mm²，仅作辅助通风。')
    throat=box(44.05,44.70,80.22,96.78,8.22,16.78)
    ck('风机至鳍口的净通道',all(inter(parts[i]['sh'],throat)<.001 for i in ['shield','blower','sink','shell']), '出口名义 16.6×8.6=142.8 mm²；最小净量规 16.56×8.56、通至鳍入口前。')
    ck('C 无电池与风机量规','pouch' not in parts and 'main_j5' not in parts and np.allclose(bb['blower'][1]-bb['blower'][0],[35,35,10]),'机内 0 Wh；替代 A 的 30×30×5 风机和电池托架。')
    ck('去电芯后的热通道',abs(bb['blower'][0,2]-bb['barrier'][1,2]-3.7)<.001 and len([1 for v in PORT_Y])==6,'冷风窗中，风机吸面至隔热毡 3.70 mm；十二鳍标称高 12.05 mm（温控口局部减短），机外未加厚。')
    pad=bb['power_tim'];fet=bb['power_contact']
    ck('主板热接触与电感包络',abs(fet[1,2]-pad[0,2])<.001 and np.all(fet[0,:2]>=pad[0,:2]) and np.all(fet[1,:2]<=pad[1,:2]) and np.allclose(bb['input_choke'][1]-bb['input_choke'][0],[7,7,5.5]),'导热接触预算 11×3.2 mm、Z=17.20；另留 7×7×5.5 mm 屏蔽电感，不以预排代替电流/热验证。')
    ck('合同负载分配',all(load(*policy(v,a))<=.90*v*a+.0001 for v,a in [(20,3),(15,3),(15,2),(5,3),(5,1.5),(5,.5)]) and policy(20,3)==(20.,3.) and policy(15,3)==(20.,1.5),'逐档按合同功率的 90% 验收；仅为预算，不代表稳压、电流或温度已测。')
    # 配件量规另存，不把腰包或两米线纳入手机尺寸和重量。
    gauges={}
    for name,x in [('input',22),('output',48)]:
        body=box(x-5.5,x+5.5,125.8,143.8,14.5,19.3)
        lead=cyl(x,143.8,16.9,3.8,18.2,(0,1,0))
        g=body.fuse(lead);gauges[name]=g
        ck(name+' 插头与直出线规',sum(inter(s['sh'],g) for s in parts.values() )<.001,'包胶宽 11、高 4.8、长 18；线 Ø3.8，直出到 y=162。检装配重叠，不据此保证天线和麦克风。')
    ck('两口同时插线',inter(*gauges.values())<.001,'两件直出量规互不重叠；实际软线弯曲和包胶公差待测。')
    solids=[]
    for k,g in gauges.items():
        v=native_shape(g);v.label='plug_gauge_'+k;solids.append(v)
    file=OUT/'cable_gauges.step';assert export_step(Compound(children=solids),file) and len(import_step(file).solids())==2
    def fmt_region(title,b,why):
        return f'| {title} | {b[0,0]:.2f}…{b[1,0]:.2f} | {b[0,1]:.2f}…{b[1,1]:.2f} | {b[1,2]:.2f} | {why} |'
    rows=['## 清单二｜头方已复核第 6 轮几何','',
          '''头方用本地数据逐点复核：平台投影内、背玻璃以上无背夹材料；窗边到各取景锥最小余量 3.4 mm，新顶轨到闪光灯内锥约 4.0 mm。灯窗前沿（Y≈64、Z=24）到激光雷达约 1.9 mm（竖向），到超广角约 3.2 mm；灯板到禁入区 3 约 0.7 mm。下部两颗背盖螺钉已离开底部左右禁金属边条；四角扣、侧键与开孔均与第 5 轮一致，通过。上述取景数值来自头方，不由简化模型计算。''','',
          '均按背玻璃为 Z=0。机身区域取当前 B-rep 的包围盒或切片；插线两行来自另存的实形量规；软线只给安装约束，不编造实测值。','',
          '| 复核对象 | X mm | Y mm | 最高 Z mm | 结论 / 实物验证 |','|---|---:|---:|---:|---|']
    def cutbox(ids,volume):
        arr=np.array([bounds(h) for i in ids for h in sh(i).intersect(volume) or []])
        return np.stack([arr[:,0].min(axis=0),arr[:,1].max(axis=0)])
    rows.append(fmt_region('上背壳架、开窗周边及顶角',cutbox(['frame','liner'],box(-4,75,-4,48,-11,25)),'平台已避让；背麦实际收音仍须装机比较；前唇另至 Z=−10.30。简化镜头岛不作定位基准。'))
    rows.append('| 镜头窗的右边／下边（方角） | 46.00／0…46.00 | 0…47.50／47.50 | 3.00 | 上及左通至机缘，实心矩形内零材料；窗边到各锥最小余量 3.4 mm（头方复核）。 |')
    rows.append(fmt_region('外侧顶轨（含两端接头）',cutbox(['frame'],box(8,62.6,-3.05,-.05,0,3)),'新顶轨到闪光灯内锥约 4.0 mm（头方复核）。不走电源键侧壁。'))
    for name,x,X,y,Y in [('左上',-4,12,-4,12),('右上',58.6,75,-4,12),('左下',-4,12,134.6,151),('右下',58.6,75,134.6,151)]:
        rows.append(fmt_region(name+'角扣（含前唇）',cutbox(['frame','liner'],box(x,X,y,Y,-11,3)),'正面唇边最低 Z=−10.30；夹持几何不延长，需实物确认屏幕圆角和脱扣力。'))
    rows.append('| 移位的下部两颗背盖钉头 | 0.90…4.70／65.90…69.70 | 106.60…110.40 | 23.95 | 螺柱、沉台及导风盘退让随动；头方已确认两钉离开底部左右禁金属边条。 |')
    for title,y,Y in [('薄肩及表点间隔',48,61.8),('坡肩过渡',61.8,64),('下背面光窗和控制面',64,130.4),('尾坡和软带孔',130.4,143)]:
        rows.append(fmt_region(title,cutbox(['frame','liner','shell','diffuser'],box(-4,75,y,Y,0,25)),'外表面冻结；头方实形复核最紧为雷达，竖向余量约 1.9 mm。' if y<130 else '核插线、绑带、底部麦克风；此行为未装带的印件。'))
    rows.append(fmt_region('背盖之后的底部两角',cutbox(['frame','liner'],box(-4,75,143,151,-11,25)),'开孔与四角已通过几何复核；收音、屏幕贴合须实测；中段无跨接横梁，前唇最低 Z=−10.30。'))
    for title,ids,why in [('风机与转子',['blower'],'核指南针、OIS 及磁干扰。'),('铝鳍与导热舌',['sink'],'铝鳍按现状接受；无线充电线圈占用为已接受偏差，不支持 Qi/MagSafe。'),('三板、接口与已建模紧固件', [i for i in parts if parts[i]['group']=='电路板' or i in ('screws','led_fasteners')],'头方已核禁金属区；主板下沿保持 125.8。')]:
        rows.append(fmt_region(title,env(ids),why))
    rows.append(fmt_region('冻结的灯板及其四只小头钉',env(['led_board','led_fasteners']),'灯板及四颗紧固件均不在禁金属区，按现状接受。'))
    rows.append(fmt_region('冻结的上部背盖两钉',cutbox(['screws'],box(-2,74,99,105,3,26)),'头方已逐点复核，上部两钉按现状接受。'))
    for k,g in gauges.items():rows.append(fmt_region(('输入' if k=='input' else '输出')+'插头＋第一段线',bounds(g),'进入底部天线带是已接受偏差，不计入背夹底部分区判据。须双线插入核 RF、收音、拉力与遮挡。'))
    rows+=['','6 mm 软带穿两孔：切口 x=8.1…9.9 / 12.8…14.6、y=134.2…141。系带到输入线后设计限界 x=8…28、y=133…148、Z≤21.5（未测）。两线在 y≥162 后才允许转向，输入向腰侧；输出短线在手机底口用 90° 弯头折向背面，避开扬声器、麦克风。弯折段与最终手机插头不在公开精确数据中，无固定最高点；头方须按实选两端、线弯和握持姿态扫掠签核。外接包固定在身上，不得摆到镜头前、不得贴在背面。']
    return rows
