"""三个实配实验；试片不装入正式装配、质量清单或网页。"""
from model import P,L,T,W,H,parts,features,box,rr,cyl,common,midpoint
def samples():
    f=features
    # 角扣全尺寸，去掉背板中部和非夹持凸柱；保留四角间真实跨度。
    lo=-T-P.jaw-P.glass_gap; top=f['plate_top']; s=P.clip_span
    cut=box(s,W-s,s,H-s,lo-1,top+1)
    full=box(-s,W+s,-s,H+s,lo-1,top)
    corner=common(parts['frame']['sh'],full).cut(cut)
    liner=parts['liner']['sh'].cut(cut)
    # 截取第一槽，留足中指弹齿与止端扣。在取掉第二槽的边上测量触点。
    k=L['pod']; x,X=k['x']; y,Y=k['y']; z=f['tray_z']; Z=z+k['thickness']
    half=box(x-1,X+1,y-1,midpoint(k['cell_axis_y'])+P.keeper_half,z-1,Z+1)
    cell=common(parts['battery_tray']['sh'],half); lid=common(parts['battery_lid']['sh'],half)
    # 不透光外廓而不是视场数据。单面开背节材，原颈部 M2 端孔保留。
    pod=box(x,X,y,Y,z,Z).cut(box(x+k['wall'],X-k['wall'],y+k['wall'],Y-k['wall'],z-1,Z-P.wall))
    h=L['head']; x,X=h['x']; y,Y=h['y']; z=f['head_z']; Z=f['head_Z']; w=P.head_wall
    head=rr(x,X,y,Y,z,Z,P.housing_r).cut(rr(x+w,X-w,y+w,Y-w,z-1,Z-P.wall,P.housing_r-w))
    for xx in f['xs']:
        jz=(f['nz']+f['NZ'])/2
        head=head.fuse(cyl(xx,Y,jz,P.boss_d,w+P.insert_l,(0,-1,0))).cut(cyl(xx,Y+.1,jz,P.insert_d,P.insert_l+.2,(0,-1,0)))
    return dict(corner_frame=corner,corner_liner=liner,one_cell_tray=cell,one_cell_lid=lid,
                view_head=head,view_pod=pod)
