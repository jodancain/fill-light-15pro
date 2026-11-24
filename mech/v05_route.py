"""扁线排在侧键上方通过，过顶角时在线框外；板坐标 mm。"""
import math
def path():
    x=76.5;r=9.;cx=x-r
    pts=[(63.6,-45,-8.8,1,0)]
    for i in range(13):
        a=-math.pi/2+i*math.pi/24;pts.append((cx+r*math.cos(a),-36+r*math.sin(a),-8.8,-math.sin(a),math.cos(a)))
    for y in [-35,-32,-28,-24,-20,-16,-12,-8,-6,0,10,22,34,46,60,67,71,75,79,83,87,91,95]:
        z=-8.8+10.9*(1-math.cos(math.pi*min(1,(y+36)/30)))/2
        z+=7.65*(1-math.cos(math.pi*min(1,max(0,(y-67)/24))))/2
        pts.append((x,y,z,0,1))
    pts.append((x,95.5,9.75,0,1))
    for i in range(1,13):
        a=i*math.pi/24;pts.append((cx+r*math.cos(a),95.5+r*math.sin(a),9.75,-math.sin(a),math.cos(a)))
    pts.append((64.25,104.5,9.75,-1,0));return pts
