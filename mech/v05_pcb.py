from v05_layout import *
from v05_route import path
import pcb_draw as d
import ezdxf
def render(doc,p):
    from ezdxf.addons.drawing import Frontend,RenderContext
    from ezdxf.addons.drawing.config import Configuration,ColorPolicy,BackgroundPolicy
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(15,10));ax.set_axis_off()
    Frontend(RenderContext(doc),MatplotlibBackend(ax),config=Configuration(background_policy=BackgroundPolicy.WHITE,color_policy=ColorPolicy.COLOR)).draw_layout(doc.modelspace(),finalize=True)
    ax.set_aspect('equal');fig.savefig(p,dpi=165,bbox_inches='tight',pad_inches=.22);plt.close(fig)
def pcb(j,dest):
    dest.mkdir(exist_ok=True,parents=True);d.DIR=dest;a=j['variant']=='A';suf='_battery' if a else '';checks=[]
    for k,b in j['boards'].items():
        d.board_dxf(b);f=dest/(k+'.dxf');doc=ezdxf.readfile(f);m=doc.modelspace()
        for e in m.query('TEXT'):
            if 'v0.4-C' in e.dxf.text:e.dxf.text='v0.5 / '+('灯头共用' if k!='main' else j['variant']+' 背夹主板')
        if k=='main':d.text(m,'NOTES',(0,-12),'Q_TIM：11×3.2；封装顶面 +2.2，压合垫 0.6 mm；板面朝 +Z。',.8)
        if k=='main' and a:
            for it in b['panel_flex']:d.cross(m,'NOTES',it['center'],.35)
        if k=='main' and a:d.text(m,'NOTES',(0,-14),'J5 含锁扣插合总高 14.5；J6 九线接盖面三键五灯。',.8)
        for name,(color,_) in d.LAY.items():doc.layers.get(name).rgb=tuple(bytes.fromhex(color[1:]))
        file=dest/(k+(suf if k=='main' else '')+'.dxf');doc.saveas(file);rd=ezdxf.readfile(file);checks+=d.audit(b,rd);render(rd,file.with_suffix('.png'))
        if a and k=='main' and f!=file:f.unlink()
    doc,m=d.setup();d.rounded(m,'PHONE_REF',70.6,146.6,9,'phone','public',0,-146.6)
    def rect(layer,x,X,y,Y,role,name):
        d.rect(m,layer,[x,-Y,X,-y],role,name);d.text(m,'NOTES',(x+.6,-y-1.8),name,1)
    for k,b in j['boards'].items():
        x,y,z=b['origin'];w,h=b['size'];d.rounded(m,'BOARD_OUTLINE',w,h,b['corner_radius'],'board',k,x,-y);d.text(m,'NOTES',(x+2,-y+1),k,1)
    rect('ENCLOSURE',0,70.6,-57,-13,'head','共用灯头');rect('ENCLOSURE',.2,70.4,62.8,129.4,'back','背夹')
    if a:rect('ENCLOSURE',5.3,65.3,64.8,98.8,'pack','2S 配组软包')
    rect('ENCLOSURE',3.3,38.3,-54.1,-19.1,'fan','35 mm 离心风机')
    rect('ENCLOSURE',-39,0,-54,-18,'passive','被动散热铝翼（非握持面）')
    rect('ENCLOSURE',0,46,0,47.5,'camera','镜头开窗包络')
    pts=path()
    for aa,bb in zip(pts,pts[1:]):d.ln(m,'HARNESS',(aa[0],-aa[1]),(bb[0],-bb[1]),'route','12')
    d.text(m,'NOTES',(0,61),'v0.5 '+j['variant']+' / 背面视图，单位 mm。外侧为 12 芯线束；投影重合不等于干涉。',1.25)
    file=dest/('assembly_layout'+suf+'.dxf');doc.saveas(file);rd=ezdxf.readfile(file);render(rd,file.with_suffix('.png'))
    outlines=rd.modelspace().query('LWPOLYLINE[layer=="BOARD_OUTLINE"]')
    checks.append(dict(name='整机布置 DXF 回读',ok=rd.units==4 and len(outlines)==3 and all(x.closed for x in outlines),value='三条闭合板框，R2010 / mm'))
    return checks
