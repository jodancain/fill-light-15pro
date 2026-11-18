"""主驱线束的中性线；剖面为直线和相切圆弧。坐标单位 mm。"""
from math import sin,cos,pi,radians,sqrt,asin
from build123d import Face,Wire,Solid
X=54.55; WIDTH=6.85; HALF=1.2; CAP_IN=1.26; CAP_OUT=2.46
BANDS=[(40,44,1.8),(44,48,3.6),(46,58,4.7),(50,54,7.3),(54,58,10.2)]
def ridge_path(L,P):
    a,b=L['pod']['cell_axis_y'];pod=L['pod']; cz=P.liner+P.frame+pod['base']+P.cell_gap+pod['cell_d_max']/2
    rad=11.84; blend=5.3; flat=24.87; theta=radians(89); angle=asin(sqrt(1-((flat+blend-cz)/(rad+blend))**2)); dx=(rad+blend)*sin(angle)
    # 返回截面点 (y,z,切线角)，每弧 ≤2°。坡段同圆弧相切。
    q=[]
    def pt(y,z,t):q.append((y,z,t))
    def arc(y,z,r,t0,t1):
        n=int(abs(t1-t0)*180/pi/2)+1
        for k in range(n+1):
            t=t0+(t1-t0)*k/n;pt(y+r*sin(t),z-r*cos(t),t)
    z0=6.4;y1=a-rad*sin(theta);z1=cz+rad*cos(theta);z2=z0+blend*(1-cos(theta));y2=y1-(z1-z2)*cos(theta)/sin(theta)
    pt(38,z0,0);arc(y2-blend*sin(theta),z0+blend,blend,0,theta)
    arc(a,cz,-rad,theta,-angle);arc(a+dx,flat+blend,blend,-angle,0);arc(b-dx,flat+blend,blend,0,angle);arc(b,cz,-rad,angle,-theta)
    z0=9.5;z2=z0+blend*(1-cos(theta));y2=b+rad*sin(theta)+(cz+rad*cos(theta)-z2)*cos(theta)/sin(theta)
    arc(y2+blend*sin(theta),z0+blend,blend,-theta,0);pt(max(109.2,q[-1][0]+.1),z0,0)
    return [v for j,v in enumerate(q) if not j or abs(v[0]-q[j-1][0])>1e-7]
def half_at(y):
    # 首槽入口约束段解开外包带，用侧梳将两对双绞及信号约束在 2.20 mm 厚；线皮须实配。
    return 1.1 if 50<=y<=65 else 1.2

def strip(q,x,w,low,high):
    def edge(h):return [(x,y-(h(y) if callable(h) else h)*sin(t),z+(h(y) if callable(h) else h)*cos(t)) for y,z,t in q]
    return Solid.extrude(Face(Wire.make_polygon(edge(low)+edge(high)[::-1],close=True)),(w,0,0))
def neck_x(y):
    t=min(1,max(0,(y-15)/23)); return 50.8+(X-50.8)*(3*t*t-2*t**3)
def flat_strip(xw,z,h):
    ys=[15+i*23/32 for i in range(33)];e=lambda s:[(neck_x(y)+s*xw/2,y,z) for y in ys];return Solid.extrude(Face(Wire.make_polygon(e(-1)+e(1)[::-1],close=True)),(0,0,h))
