"""同尺度投影真实发布网格，按三角面深度绘制；绝不使用手机图纸。"""
from pathlib import Path
import json
import numpy as np,trimesh,matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
from matplotlib.collections import PolyCollection
ROOT=Path(__file__).resolve().parents[1]
def comparison():
    old=ROOT/'mech/out/archive_v04C_r5/web/models';now=ROOT/'web/models'; versions=[(old,'C R5 · 返工前'),(now,'C R6 · 窗口返工后')] if old.exists() else [(now,'C R6 · 窗口返工后')]
    f=Path('/System/Library/Fonts/STHeiti Medium.ttc')
    if f.exists():font_manager.fontManager.addfont(str(f));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(f)).get_name()
    fig,axes=plt.subplots(1,2*len(versions),figsize=(8.8,5.2),facecolor='#f5f5ed')
    for n,(path,title) in enumerate(versions):
        sc=trimesh.load_scene(path/'filllight.glb');data=json.loads((path/'parts.json').read_text());tri=[];cols=[]
        for p in data['parts']:
            t,g=sc.graph[p['id']];m=sc.geometry[g];v=trimesh.transform_points(m.vertices,t)*1000;tri.extend(v[m.faces]);rgb=bytes.fromhex(p['color'].lstrip('#'));cols.extend([list(rgb)]*len(m.faces))
        tri=np.array(tri);colors=np.asarray(cols)/255
        for i,(a,bb,d) in enumerate(((0,1,2),(2,1,0))):
            ax=axes[n*2+i];order=np.argsort(tri[:,:,d].mean(axis=1));q=tri[order];normal=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-9)
            lit=.68+.32*np.abs(normal@np.array([.42,.36,.83]));shade=np.clip(colors[order]*lit[:,None],0,1)
            ax.add_collection(PolyCollection(q[:,:,[a,bb]],facecolors=shade,edgecolors='face',linewidths=.19));ax.set_aspect('equal');ax.set_ylim(-154,69);ax.set_xlim((-7,79) if i==0 else (-28,53));ax.axis('off')
            ax.set_title(title if i==0 else '侧面 / 同尺度',fontsize=10,color='#36574c')
    fig.subplots_adjust(.015,.075,.985,.88,wspace=.01);fig.text(.03,.04,'同一比例 · 手机底边对齐 · 由装配网格投影，不是实物照片',fontsize=9,color='#36574c');fig.savefig(now/'comparison.png',dpi=145,facecolor=fig.get_facecolor());plt.close(fig)
