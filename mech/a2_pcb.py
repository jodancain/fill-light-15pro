"""从 A2 合同生成图档；不调用写 C 路径的整套出图入口。"""
from pathlib import Path
from a2_layout import *
import pcb_draw as d
import ezdxf,shutil
def draw(j,out):
    work=out/'dxf';work.mkdir(exist_ok=True); d.DIR=work
    b=j['boards']['main'];d.board_dxf(b);doc=ezdxf.readfile(work/'main.dxf');m=doc.modelspace()
    for e in m.query('TEXT'):
        if 'v0.4-C' in e.dxf.text:e.dxf.text='A2-r1：2S 可换电池；J5 为六位板装防呆插头的插合包络，保护在主板。'
    for f in b['panel_flex']:d.cross(m,'NOTES',f['center'],.35)
    d.text(m,'NOTES',(0,-12),'面盖键灯中心投影仅作装配参考，不在主板贴装。J5-P 插合总高 ≤14.5 mm。',.78)
    for name,(color,_) in d.LAY.items():doc.layers.get(name).rgb=tuple(bytes.fromhex(color[1:]))
    doc.saveas(PCB/'main_battery.dxf')
    lay,m=d.setup();d.rounded(m,'PHONE_REF',70.6,146.6,9,'phone','public',0,-146.6)
    for k,board in j['boards'].items():
        x,y,z=board['origin'];w,h=board['size'];d.rounded(m,'BOARD_OUTLINE',w,h,board['corner_radius'],'board',k,x,-y)
        d.text(m,'NOTES',(x+1,-y+.8),board['name'],1)
    def project(v):x,X,y,Y,z,Z=v;return [x,-Y,X,-y]
    for label,v in [('电芯 1/2 叠放',CELL),('J5-P 六位防呆',PLUG),('盖仓', [5.15,65.45,100.05,130,22.65,31.95]),('风机',j['fan_bbox'])]:
        d.rect(m,'ENCLOSURE',project(v),'envelope',label);a=project(v);d.text(m,'NOTES',(a[0]+.2,a[3]-.8),label,.9)
    for name,ps in j['routes']:
        for a,b1 in zip(ps,ps[1:]):d.ln(m,'HARNESS',(a[0],-a[1]),(b1[0],-b1[1]),'route',name)
    d.text(m,'NOTES',(0,4),'A2-r1 背视 / 电芯在主板外侧，两层共投影，深度另见 STEP',1.4)
    for name,(color,_) in d.LAY.items():lay.layers.get(name).rgb=tuple(bytes.fromhex(color[1:]))
    lay.saveas(PCB/'assembly_layout_battery.dxf'); dd=ezdxf.readfile(PCB/'assembly_layout_battery.dxf')
    c=d.audit(b,ezdxf.readfile(PCB/'main_battery.dxf'))
    for k in ('driver','led'):c+=d.audit(j['boards'][k],ezdxf.readfile(PCB/(k+'.dxf')))
    shapes=dd.modelspace().query('LWPOLYLINE[layer=="BOARD_OUTLINE"]')
    c.append(dict(name='A2 整机布置 DXF 回读',ok=dd.dxfversion=='AC1024' and dd.units==4 and len(shapes)==3 and all(e.closed for e in shapes),value='三板、风机、双层包、插头和板间走线，mm。'))
    # PNG 直接用已保存 DXF，自动取全图范围，文字与线层同源。
    from ezdxf.addons.drawing import Frontend,RenderContext
    from ezdxf.addons.drawing.config import ColorPolicy,BackgroundPolicy,Configuration
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from matplotlib import pyplot as plt
    for n in ('main_battery','assembly_layout_battery'):
        doc=ezdxf.readfile(PCB/(n+'.dxf'));fig,ax=plt.subplots(figsize=(15,9));ax.set_axis_off()
        cfg=Configuration(background_policy=BackgroundPolicy.WHITE,color_policy=ColorPolicy.COLOR)
        Frontend(RenderContext(doc),MatplotlibBackend(ax),config=cfg).draw_layout(doc.modelspace(),finalize=True)
        ax.set_aspect('equal');fig.savefig(PCB/(n+'.png'),dpi=210,facecolor='white',bbox_inches='tight',pad_inches=.18);plt.close(fig)
    (PCB/'pcb_interface_battery.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
    return c
