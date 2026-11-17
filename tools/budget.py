#!/usr/bin/env python3
# 功率、续航、充电、发热和重量的粗算。所有假设写在最上面，改假设就能重算。
# 标了“估”的是估计值，要由 G2 的实验和 G8 的实测替换。
# 用法：python3 budget.py
import math

# ---------- 假设 ----------
CELLS = 2                      # 串联节数
CELL_MAH = 5000                # 单节容量（高能量型 21700 的常见规格）
CELL_V_NOM = 3.6
CELL_R = 0.022                 # 单节内阻，估
USABLE = 0.90                  # 放到截止前能用掉的比例，估

LED_W_MAX = 20.0               # 灯珠总电功率上限
LED_W_QUIET = 10.0             # 静音档
DRIVER_EFF = 0.88              # 升压恒流效率，估（TPS61500 低输入电压时；与 hw_calc.py 和 HW-DRV-08 一致）
FAN_W = 0.6                    # 40 mm 风扇，估
MCU_W = 0.1
LED_RADIANT = 0.33             # 电功率里变成光的比例，估（高显色灯珠降额使用）

PHONE_V, PHONE_A = 5.0, 3.0    # 手机输出口
BUCK_EFF = 0.92                # 5 V 降压效率，估

BATFET_A_CONT = 6.0            # BQ25798 规格书：电池持续放电电流上限（RMS）
ICHG_A = 2.5                   # 充电电流（0.5C）
CHG_EFF = 0.90                 # 充电变换效率，估

# 电池仓里串在电流通路上的电阻，估
R_SERIES = dict(电芯=CELLS * CELL_R, 弹片触点=4 * 0.010, 防反接管=2 * 0.006, 保护管=2 * 0.010,
                运输模式开关管=0.003, 充电芯片内的电池开关=0.011, 保险丝=0.005)
# 电池开关 11 mΩ 来自 BQ25798 规格书典型值；运输模式开关管是外置的 N 沟道管（规格书第 49–50 页），按 3 mΩ 估

# 散热，估
RTH_HEAD_PASSIVE = 5.5         # 灯头散热片自然对流热阻，K/W
RTH_HEAD_FAN = 2.0             # 开风扇
POD_AREA_M2 = 0.012            # 电池仓能散热的外表面
H_NAT = 8.0                    # 自然对流加辐射的换热系数，W/(m2·K)
T_AMB = 25.0


def pack_v(per_cell):
    return CELLS * per_cell


def lamp_in_w(led_w):
    return led_w / DRIVER_EFF + (FAN_W if led_w > LED_W_QUIET else 0.0) + MCU_W


def main():
    wh = CELLS * CELL_MAH / 1000.0 * CELL_V_NOM
    print(f'一、电量：{CELLS} 节 × {CELL_MAH} mAh × {CELL_V_NOM} V = {wh:.1f} Wh')

    print('二、续航（估）：')
    for w in (LED_W_MAX, 15.0, LED_W_QUIET, 5.0):
        p = lamp_in_w(w)
        print(f'  灯 {w:>4.0f} W → 电池端 {p:>4.1f} W → {wh * USABLE / p:>4.1f} 小时')

    print(f'三、电池电流（BQ25798 持续放电上限 {BATFET_A_CONT} A）：')
    phone_w = PHONE_V * PHONE_A / BUCK_EFF
    for vc in (4.1, 3.6, 3.3, 3.2, 3.0):
        v = pack_v(vc)
        a_lamp = lamp_in_w(LED_W_MAX) / v
        a_both = (lamp_in_w(LED_W_MAX) + phone_w) / v
        flag = '超限' if a_both > BATFET_A_CONT else '可以'
        # 手机满载时，灯最多还能开多大
        room_w = BATFET_A_CONT * v - phone_w - MCU_W - FAN_W
        led_ok = max(0.0, min(LED_W_MAX, room_w * DRIVER_EFF))
        print(f'  单节 {vc} V（电池 {v:.1f} V）：只开灯 {a_lamp:.1f} A；灯加手机 3 A {a_both:.1f} A（{flag}）；'
              f'手机满载时灯最多 {led_ok:.0f} W')

    print('四、充电时间（估）：')
    for name, in_w in (('普通 5 V / 3 A', 15.0), ('快充 12 V，约 30 W', 30.0)):
        chg_w = min(in_w * CHG_EFF, ICHG_A * pack_v(3.8))
        hours = wh / chg_w + 0.5      # 加半小时恒压收尾
        print(f'  {name}：进电池约 {chg_w:.0f} W → 约 {hours:.1f} 小时')

    print('五、灯头发热（估，等实验 1 的实测替换）：')
    for led_w, rth, mode in ((LED_W_QUIET, RTH_HEAD_PASSIVE, '不开风扇'), (LED_W_MAX, RTH_HEAD_FAN, '开风扇'),
                             (LED_W_MAX, RTH_HEAD_PASSIVE, '风扇坏了')):
        heat = led_w * (1 - LED_RADIANT) + led_w / DRIVER_EFF - led_w
        print(f'  灯 {led_w:.0f} W {mode}：发热 {heat:.1f} W → 散热片约 {T_AMB + heat * rth:.0f} °C（环境 {T_AMB:.0f} °C）')

    print('六、电池仓发热（估）：')
    r_total = sum(R_SERIES.values())
    print(f'  通路电阻合计 {r_total * 1000:.0f} mΩ：' + '、'.join(f'{k} {v * 1000:.0f}' for k, v in R_SERIES.items()))
    v = pack_v(3.6)
    for name, w_lamp, a_phone in (('只开灯 20 W', lamp_in_w(LED_W_MAX), 0.0), ('灯 10 W 加手机 3 A', lamp_in_w(LED_W_QUIET), PHONE_A),
                                  ('灯 20 W 加手机 3 A', lamp_in_w(LED_W_MAX), PHONE_A), ('灯 20 W 加手机 1 A', lamp_in_w(LED_W_MAX), 1.0)):
        p_phone = PHONE_V * a_phone / BUCK_EFF
        a = (w_lamp + p_phone) / v
        loss = a * a * r_total + (p_phone - PHONE_V * a_phone)
        dt = loss / (POD_AREA_M2 * H_NAT)
        print(f'  {name}：{a:.1f} A，仓内发热 {loss:.1f} W → 封闭仓温升约 {dt:.0f} K')

    print('七、重量（估）：')
    parts = dict(电芯两节=140, 打印件=90, 散热片=55, 风扇=8, 灯板=12, 驱动板=6, 主板=12, 线束螺丝弹片=15, 柔光板=5)
    print('  ' + '、'.join(f'{k} {v}' for k, v in parts.items()) + f'；合计约 {sum(parts.values())} 克')

    print('八、照度（估）：')
    for led_w in (LED_W_MAX, LED_W_QUIET):
        lm_per_w, diffuser, hot = 120.0, 0.85, 0.92
        lm = led_w * lm_per_w * diffuser * hot
        lux = lm / math.pi / 0.25           # 朗伯面光源，0.5 米处中心照度
        print(f'  灯 {led_w:.0f} W：出光约 {lm:.0f} 流明 → 0.5 米中心约 {lux:.0f} 勒克斯（按 {lm_per_w:.0f} 流明/瓦、柔光板透过 {diffuser}）')


if __name__ == '__main__':
    main()
