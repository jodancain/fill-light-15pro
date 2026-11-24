"""First-order compact exchanger: all coefficients explicit; not measured ratings."""
import math
from bisect import bisect_right
def budget():
    # Manufacturer curve section 9, approximate digitization; airflow m3/min and mmH2O.
    pp=[11.2,10,8.5,6.8,4.6,2.5,0];rho=1.145;cp=1007;mu=1.9e-5
    area=25*.0008*.011;dh=2*.0008*.011/(.0008+.011);wall=26*2*.024*.011
    def point(scale):
        lo,hi=0.,.001*scale
        for _ in range(55):
            q=(lo+hi)/2;x=min(5.999999,q*6000/scale);i=int(x);pressure=(pp[i]+(x-i)*(pp[i+1]-pp[i]))*9.807*scale**2
            speed=q/area;re=rho*speed*dh/mu;drop=48*mu*.024*speed/dh**2+rho/2*(3*(q/(6*.0033*.014))**2+2*speed**2)
            if drop>pressure:hi=q
            else:lo=q
        return q,pressure
    out=[]
    for watts,s in [(3.8,0),(7.7,.8),(17,1),(17.8,1),(18.6,1)]:
        if s:
            q,p=point(s);cap=rho*cp*q;hc=5*.027/dh;ua=hc*(wall+.024*.0304)*.75;R=.45+1/(cap*(1-math.exp(-ua/cap)));noise=31+50*math.log10(s)
        else:
            q=p=noise=0
            # Nine external free-convection plates. Area counts only two broad faces.
            # Isothermal-base straight fin, adiabatic tip; 160 W/mK aluminum.
            h=5.;L=.036;t=.0009;mL=L*math.sqrt(2*h/(160*t));eta=math.tanh(mL)/mL
            # 9mm lateral spreading in 32mm x 0.8mm bridge, before the external wing.
            Rext=.009/(160*.032*.0008)+1/(h*eta*2*9*L*.024)
            Rinner=1/(6*(wall*.30+.062*.034)*.85);R=.45+1/(1/Rext+1/Rinner)
        out.append(dict(load_W=watts,estimated_rpm=round(8500*s),estimated_CFM=round(q*2118.88,2),pressure_Pa=round(p,1),R_K_W=round(R,2),estimated_hotspot_C=round(35+R*(watts+.75*s**3),1),fan_noise_est_dBA=round(noise,1) if s else None))
    return out
