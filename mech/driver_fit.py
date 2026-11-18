"""离散器件外形试排；不是 land pattern、走线或热设计。坐标为板局部 mm。"""
import math,random

def trial(d):
    # 0.5 mm 格，矩形向外取整，试排件四周再各加 0.25 mm。
    fixed=d['connectors']+d['fixed']+[v for v in d['keepouts'] if v['side']=='TOP']+[v for v in d['height_zones'] if v['id'] in ('FAN_BUCK','J1_BAY')]; grid=[0]*44
    def mark(g,l,b,r,t):
        x=max(0,math.floor(l*2));X=min(120,math.ceil(r*2));mask=((1<<(X-x))-1)<<x
        for y in range(max(0,math.floor(b*2)),min(44,math.ceil(t*2))):g[y]|=mask
    for v in fixed:mark(grid,*v['rect'])
    for h in d['holes']:
        x,y=h['center'];r=h['keep_d']/2;mark(grid,x-r,y-r,x+r,y+r)
    todo=[(v['type'],v['w'],v['h'],c,i) for v in d['budget'] if v['type']!='电感' for c in ('W','C') for i in range(v['count'])];rng=random.Random(92692)
    longest=[]
    for attempt in range(65):
        g=grid[:];out=[]
        for name,w,h,ch,i in sorted(todo,key=lambda v:-v[1]*v[2]*(1+rng.random()*.5)):
            best=None
            for a,b in [(w,h),(h,w)]:
                W=math.ceil(2*(a+.5));H=math.ceil(2*(b+.5)); mask=(1<<W)-1
                for y in range(0,45-H):
                    used=0
                    for row in g[y:y+H]:used|=row
                    run=(~used)&((1<<120)-1)
                    for _ in range(W-1):run&=run>>1
                    while run:
                        bit=run & -run; x=bit.bit_length()-1;run^=bit
                        cost=abs((x+W/2)/2-(12 if ch=='W' else 31))+.3*y
                        if best is None or cost<best[0]:best=(cost,x,y,a,b,W,H)
            if best is None:continue
            _,x,y,a,b,W,H=best;cx=(x+W/2)/2;cy=(y+H/2)/2;mark(g,x/2,y/2,(x+W)/2,(y+H)/2);out.append(dict(type=name,ch=ch,index=i+1,rect=[cx-a/2,cy-b/2,cx+a/2,cy+b/2]))
        if len(out)==len(todo):return out
        if len(out)>len(longest):longest=out
    return longest

def compact(d):
    from copy import deepcopy
    a=deepcopy(d)
    for f in a['fixed']:
        if f['ref'] in ('L_W','L_C'):
            x,y=f['center'];f['rect']=[x-3.5,y-3.5,x+3.5,y+3.5]
    for v in a['budget']:
        if v['type']=='调光 PMOS':v.update(w=3,h=2.5)
    return {'inductor_wh':[7,7],'dimming_pmos_wh':[3,2.5],'fixed_inductors':[f['rect'] for f in a['fixed'] if f['ref'] in ('L_W','L_C')],'other_parts':trial(a)}
