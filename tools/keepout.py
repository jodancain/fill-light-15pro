#!/usr/bin/env python3
# 取景与传感器禁入区核算：灯头、电池仓能放在哪。
#
# 手机尺寸读自苹果《iPhone 15 Pro Dimensional Drawings》。图纸带保密声明，原始尺寸不进仓库：
# 先从 https://developer.apple.com/accessories/dimensional-drawings/ 下载图纸，
# 按 interface/phone_template.json 的格式填写，存为 refs/iphone15pro.json（refs/ 已被忽略）。
#
# 坐标系（全项目统一）：从手机背面看，原点在左上角；
#   x 向右，y 向下（即离顶边的距离），z 为高出背面玻璃的高度（朝被摄物方向为正）。
# 用法：python3 keepout.py [--phone 手机数据文件] [--json 输出文件]
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PHONE = os.path.join(HERE, '..', 'refs', 'iphone15pro.json')


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def load_phone(path):
    if not os.path.exists(path):
        sys.stderr.write(
            f'缺少手机尺寸数据：{os.path.normpath(path)}\n'
            '请从 https://developer.apple.com/accessories/dimensional-drawings/ 下载 iPhone 15 Pro 尺寸图，\n'
            '按 interface/phone_template.json 的格式填写后存到上面的路径（refs/ 不进仓库）。\n')
        sys.exit(2)
    with open(path, encoding='utf8') as f:
        return json.load(f)


P = load_phone(arg('--phone', DEFAULT_PHONE))
T_PHONE = P['body']['thickness']
PLATEAU_Z = P['plateau']['height']


def z_from_front(v):
    """图纸里“到前盖玻璃”的距离，换成高出背面玻璃的高度。"""
    return v - T_PHONE


def k_of(full_deg):
    """锥面在剖面里的斜率：每远离轴线 1 mm，允许高度增加多少 mm。"""
    return 1.0 / math.tan(math.radians(full_deg / 2.0))


# 后置镜头禁入锥：名称 → (x, y, 全锥角, 锥顶高度 z)
REAR_CAMS = {n: (c['x'], c['y'], c['cone_deg'], z_from_front(c['apex_from_front_glass']))
             for n, c in P['rear_cameras'].items()}
# 激光雷达：保守做法，按“从平台面上那个禁入圆起算的圆台”处理（比按锥顶算更严）
_L = P['lidar']
LIDAR = dict(x=_L['x'], y=_L['y'], full=_L['cone_deg'], base_r=_L['base_d_on_plateau'] / 2.0, base_z=PLATEAU_Z)
# 闪光灯：内锥到过渡高度，再往外是外锥
_F = P['flash']
FLASH = dict(x=_F['x'], y=_F['y'], inner=_F['inner_cone_deg'], outer=_F['outer_cone_deg'],
             z0=z_from_front(_F['origin_from_front_glass']), z_tr=z_from_front(_F['transition_from_front_glass']))
# 正面：前置镜头与传感器区、环境光传感器。高度指“高出屏幕玻璃”。
_S, _A = P['front']['camera_and_sensors'], P['front']['ambient_light_sensor']
FRONT = dict(sensor_top_y=_S['center_y'] - _S['size'][1] / 2.0, sensor_full=_S['cone_deg'],
             als_top_y=_A['center_y'] - _A['d'] / 2.0, als_full=_A['cone_deg'])


def cone_limit(d, full, z_apex):
    """离轴线 d 处，允许的最大高度。"""
    return z_apex + d * k_of(full)


def lidar_limit(d):
    if d <= LIDAR['base_r']:
        return LIDAR['base_z']
    return LIDAR['base_z'] + (d - LIDAR['base_r']) * k_of(LIDAR['full'])


def flash_limit(d, outer=True):
    r_tr = (FLASH['z_tr'] - FLASH['z0']) / k_of(FLASH['inner'])
    if d <= r_tr or not outer:
        return FLASH['z0'] + d * k_of(FLASH['inner'])
    return FLASH['z_tr'] + (d - r_tr) * k_of(FLASH['outer'])


def head_table(gaps=(0, 5, 8, 10, 12, 15, 20)):
    """灯头在顶边上方、底边离顶边 g 毫米时：背面和正面各能伸出多少。"""
    rows = []
    for g in gaps:
        rear = {n: cone_limit(c[1] + g, c[2], c[3]) for n, c in REAR_CAMS.items()}
        rear['激光雷达'] = lidar_limit(LIDAR['y'] + g)
        rear['闪光灯内锥'] = flash_limit(FLASH['y'] + g, outer=False)
        rear_min = min(rear.values())
        flash_outer = flash_limit(FLASH['y'] + g, outer=True)
        f_sensor = (FRONT['sensor_top_y'] + g) * k_of(FRONT['sensor_full'])
        f_als = (FRONT['als_top_y'] + g) * k_of(FRONT['als_full'])
        front_min = min(f_sensor, f_als)
        rows.append(dict(gap=g, rear_limit=round(rear_min, 1),
                         rear_by=min(rear, key=rear.get),
                         rear_if_flash_outer=round(min(rear_min, flash_outer), 1),
                         front_limit=round(front_min, 1),
                         front_by='环境光传感器' if f_als < f_sensor else '前置镜头区',
                         depth_budget=round(rear_min + T_PHONE + front_min, 1)))
    return rows


def pod_round_top(cell_d=21.2, wall=1.2, base=1.0, margin=1.5):
    """电池横放、仓顶跟着电芯圆弧走：最上面那节电芯的轴线最少离顶边多远。"""
    r_out = cell_d / 2.0 + wall
    zc = base + cell_d / 2.0
    lines = {n: (c[1], c[3], k_of(c[2])) for n, c in REAR_CAMS.items()}
    lines['激光雷达'] = (LIDAR['y'] + LIDAR['base_r'], LIDAR['base_z'], k_of(LIDAR['full']))
    need = {}
    for n, (ya, za, k) in lines.items():
        need[n] = ya + (r_out * math.sqrt(k * k + 1.0) + zc - za) / k
    yc = max(need.values()) + margin
    return dict(cell_axis_y=round(yc, 1), limited_by=max(need, key=need.get),
                pod_top_y=round(yc - r_out, 1), pod_thickness=round(base + cell_d + wall, 1),
                detail={n: round(v, 1) for n, v in need.items()})


def pod_square_top(thickness, margin=1.5):
    """仓顶做成直角时：仓顶边最少离顶边多远。"""
    need = {n: c[1] + (thickness - c[3]) / k_of(c[2]) for n, c in REAR_CAMS.items()}
    need['激光雷达'] = LIDAR['y'] + LIDAR['base_r'] + (thickness - LIDAR['base_z']) / k_of(LIDAR['full'])
    return dict(thickness=thickness, top_y=round(max(need.values()) + margin, 1),
                limited_by=max(need, key=need.get))


def low_profile(ys=(48, 50, 52, 54, 56, 58, 60, 62)):
    """镜头平台下方的矮区：离顶边 y 处最多能做多高。"""
    rows = []
    for y in ys:
        lim = {n: cone_limit(y - c[1], c[2], c[3]) for n, c in REAR_CAMS.items()}
        lim['激光雷达'] = lidar_limit(y - LIDAR['y'])
        rows.append(dict(y=y, max_height=round(min(lim.values()), 1), limited_by=min(lim, key=lim.get)))
    return rows


def main():
    out = dict(note='由 tools/keepout.py 按本地手机尺寸数据算出的禁入区结果；只含推导结果，不含图纸原始尺寸。',
               head=head_table(), pod_round=pod_round_top(),
               pod_round_18650=pod_round_top(cell_d=18.6),
               pod_square=[pod_square_top(t) for t in (10, 12, 21.5, 24)],
               low_profile=low_profile())
    print('一、灯头：底边离手机顶边 g 时，背面/正面允许伸出量（mm）')
    print('  g   背面上限(受限于)            若还要让开闪光灯外锥  正面上限(受限于)      允许总厚度')
    for r in out['head']:
        print(f"  {r['gap']:>2}  {r['rear_limit']:>5} ({r['rear_by']})  {r['rear_if_flash_outer']:>6}"
              f"            {r['front_limit']:>5} ({r['front_by']})  {r['depth_budget']:>6}")
    for key, name in (('pod_round', '21700'), ('pod_round_18650', '18650')):
        p = out[key]
        print(f"二、电池仓（{name} 横放，仓顶跟着电芯圆弧）：最上面电芯轴线离顶边 ≥ {p['cell_axis_y']} mm，"
              f"仓顶 ≥ {p['pod_top_y']} mm，仓厚 {p['pod_thickness']} mm；受限于{p['limited_by']}；各项要求 {p['detail']}")
    print('三、电池仓若做直角顶：')
    for p in out['pod_square']:
        print(f"  厚 {p['thickness']} mm → 仓顶离顶边 ≥ {p['top_y']} mm（受限于{p['limited_by']}）")
    print('四、镜头平台下方矮区的限高：')
    for r in out['low_profile']:
        print(f"  离顶边 {r['y']} mm → 最高 {r['max_height']} mm（受限于{r['limited_by']}）")
    path = arg('--json')
    if path:
        with open(path, 'w', encoding='utf8') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print('已写入', path)


if __name__ == '__main__':
    main()
