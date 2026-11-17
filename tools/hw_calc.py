#!/usr/bin/env python3
# 硬件架构阶段的几项核算：灯驱动每路能出多大功率、电流采样电阻、过压分压、
# 充电测温分压、走线宽度、主控引脚够不够。都是初值，G3 画原理图时按规格书再核一遍。
# 用法：python3 hw_calc.py
import math

# ---------- 灯驱动（TPS61500，规格书 SLVS893F） ----------
ILIM_MIN, ILIM_TYP = 3.0, 3.8      # 开关限流，第 6 页
VREF_FB = 0.200                    # 反馈基准，第 1 页
VREF_OVP = 1.229                   # 过压脚门槛，第 6 页
FSW = 600e3                        # 取 600 kHz（第 10 页表：176 kΩ）
L_BOOST = 10e-6
EFF = 0.88                         # 估
VF_DIODE = 0.4
LED_VF, LED_SERIES = 3.05, 6       # 每颗约 3.05 V，6 颗串，估
BALLAST_V = 0.3                    # 均流电阻压降
P_CH_MAX = 20.0                    # 每路满量程功率


def led_string_v():
    return LED_VF * LED_SERIES + BALLAST_V + VREF_FB


def boost_max_power(vin, ilim):
    """规格书第 13 页的思路：电感峰值电流不能超过开关限流。"""
    vout = led_string_v()
    duty = 1.0 - vin / (vout + VF_DIODE)
    ripple = vin * duty / (L_BOOST * FSW)
    iin_avg = ilim - ripple / 2.0
    return duty, ripple, EFF * vin * iin_avg


# ---------- 充电测温分压（BQ25798，规格书 SLUSDV2C 第 13–14 页） ----------
T1_PCT, T5_PCT = 0.733, 0.342      # 冷、热两个停充门槛占基准电压的比例。规格书按推荐分压和 103AT
                                   # 标为 0 °C 和 60 °C；这里另选分压电阻，把热门槛挪到 45 °C
NTC_R25, NTC_B = 10e3, 3435.0      # 103AT 类，B 值法近似


def ntc(t_c):
    return NTC_R25 * math.exp(NTC_B * (1.0 / (t_c + 273.15) - 1.0 / 298.15))


def ts_divider(t_cold=0.0, t_hot=45.0):
    """选上拉 RT1、下拉 RT2，让 t_cold 落在冷门槛、t_hot 落在热门槛。"""
    rc, rh = ntc(t_cold), ntc(t_hot)
    a_over_rt1 = T1_PCT / (1 - T1_PCT)        # (RT2‖Rcold)/RT1
    b_over_rt1 = T5_PCT / (1 - T5_PCT)        # (RT2‖Rhot)/RT1
    ratio = a_over_rt1 / b_over_rt1
    # (RT2*rc/(RT2+rc)) / (RT2*rh/(RT2+rh)) = ratio  →  解 RT2
    rt2 = (ratio * rh * rc - rc * rh) / (rc - ratio * rh)
    rt1 = (rt2 * rc / (rt2 + rc)) / a_over_rt1
    return rc, rh, rt1, rt2


# ---------- 走线宽度（IPC-2221 外层） ----------
def trace_width_mm(amps, rise_k=20.0, oz=1.0):
    area_mil2 = (amps / (0.048 * rise_k ** 0.44)) ** (1 / 0.725)
    return area_mil2 / (1.378 * oz) * 0.0254


# ---------- 主控引脚 ----------
PINS_NEEDED = [
    ('I²C 时钟、数据', 2), ('充电芯片中断', 1), ('暖白、冷白调光', 2), ('灯驱动使能', 1), ('风扇调速', 1),
    ('灯板测温（模拟）', 1), ('电芯测温（模拟）', 1), ('电池中点电压（模拟）', 1), ('电源键（要能唤醒）', 1),
    ('加、减键', 2), ('五颗指示灯', 5), ('输出口使能与故障', 2), ('调试串口', 2),
]
PINS_AVAILABLE = 15    # ESP32-C3-MINI-1 可用引脚数（含启动配置脚，G3 按模块规格书再核）
PINS_TO_EXPANDER = ('五颗指示灯', '输出口使能与故障')   # 5 V 降压用上拉默认打开，不占引脚


def main():
    vout = led_string_v()
    print(f'一、灯驱动：灯串电压约 {vout:.1f} V（{LED_SERIES} 颗串），开关频率 {FSW / 1e3:.0f} kHz，电感 {L_BOOST * 1e6:.0f} µH')
    print('  母线电压  占空比  电感纹波  每路可出功率（限流取最小值 / 典型值）')
    for vin in (6.0, 6.4, 7.2, 8.4, 9.0, 10.8, 12.6):
        d, rip, p_min = boost_max_power(vin, ILIM_MIN)
        _, _, p_typ = boost_max_power(vin, ILIM_TYP)
        note = '（三节）' if vin > 8.4 else ''
        print(f'  {vin:>5.1f} V   {d * 100:>4.0f}%   {rip:>4.2f} A    {p_min:>4.1f} W / {p_typ:>4.1f} W {note}')
    i_fs = P_CH_MAX / (vout - VREF_FB)
    r_sense = VREF_FB / i_fs
    print(f'  满量程电流 {i_fs:.2f} A → 采样电阻约 {r_sense * 1000:.0f} mΩ，耗散 {VREF_FB * i_fs:.2f} W')
    v_ovp = 25.0
    print(f'  过压保护取 {v_ovp:.0f} V → 分压比 {v_ovp / VREF_OVP:.1f}（例如上 191 kΩ、下 10 kΩ → {VREF_OVP * (191 + 10) / 10:.1f} V）')

    rc, rh, rt1, rt2 = ts_divider()
    print(f'二、充电测温分压（0 °C 和 45 °C 停充）：测温电阻 0 °C {rc / 1e3:.1f} kΩ、45 °C {rh / 1e3:.2f} kΩ → '
          f'上拉约 {rt1 / 1e3:.2f} kΩ，下拉约 {rt2 / 1e3:.0f} kΩ')
    chk_c = (rt2 * rc / (rt2 + rc)) / (rt1 + rt2 * rc / (rt2 + rc))
    chk_h = (rt2 * rh / (rt2 + rh)) / (rt1 + rt2 * rh / (rt2 + rh))
    print(f'  验算：0 °C 时 {chk_c * 100:.1f}%（门槛 {T1_PCT * 100:.1f}%），45 °C 时 {chk_h * 100:.1f}%（门槛 {T5_PCT * 100:.1f}%）')

    print('三、走线宽度（外层，温升 20 K）：')
    for amps in (3.0, 4.0, 6.0, 10.0):
        print(f'  {amps:>4.0f} A：1 盎司铜 {trace_width_mm(amps):.1f} mm，2 盎司铜 {trace_width_mm(amps, oz=2.0):.1f} mm')

    total = sum(n for _, n in PINS_NEEDED)
    moved = sum(n for name, n in PINS_NEEDED if name in PINS_TO_EXPANDER)
    print(f'四、主控引脚：需要 {total} 个，模块可用约 {PINS_AVAILABLE} 个；'
          f'把指示灯和输出口信号（{moved} 个）挪到 I²C 扩展芯片后剩 {total - moved} 个')


if __name__ == '__main__':
    main()
