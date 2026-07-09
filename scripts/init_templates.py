import pymysql
import json

conn = pymysql.connect(
    host='localhost',
    user='root',
    password='Admin@123',
    database='comm_platform',
    charset='utf8mb4'
)

cursor = conn.cursor()

templates = [
    {
        'name': '标准宏基站(三扇区)',
        'category': 'macro',
        'description': '适用于室外广域覆盖的宏蜂窝基站，标准三扇区配置',
        'devices_json': json.dumps({
            'devices': [
                {'type': 'tower', 'name': '通信铁塔', 'model': 'TOWER-35M', 'quantity': 1, 'position_rule': 'center', 'height': 35, 'parent': None},
                {'type': 'antenna', 'name': '扇区天线', 'model': 'ANT-1710-2170-65-18i', 'quantity': 3, 'position_rule': 'sector_top', 'offset_radius': 1.5, 'height': 30, 'downtilt': 6, 'beamwidth_h': 65, 'beamwidth_v': 7, 'gain': 18, 'parent': 'tower'},
                {'type': 'rru', 'name': '射频拉远单元', 'model': 'RRU-3942', 'quantity': 3, 'position_rule': 'below_antenna', 'offset_z': -2, 'parent': 'antenna'},
                {'type': 'bbu', 'name': '基带处理单元', 'model': 'BBU-5900', 'quantity': 1, 'position_rule': 'cabinet_center', 'parent': None},
                {'type': 'power', 'name': '电源柜', 'model': 'PWR-48V-200A', 'quantity': 1, 'position_rule': 'cabinet_west', 'offset_x': -3, 'parent': None},
                {'type': 'transmission', 'name': '传输柜', 'model': 'TRANS-ODF-48', 'quantity': 1, 'position_rule': 'cabinet_east', 'offset_x': 5, 'parent': None}
            ]
        }),
        'topology_rule': 'sector_120',
        'coverage_type': 'outdoor',
        'default_params': json.dumps({'antenna_height': 30, 'coverage_radius': 500, 'frequency': 2100, 'sector_count': 3})
    },
    {
        'name': '微基站(单扇区)',
        'category': 'micro',
        'description': '适用于城区热点补盲或街道覆盖',
        'devices_json': json.dumps({
            'devices': [
                {'type': 'antenna', 'name': '一体化天线', 'model': 'ANT-3300-3800-65-15i', 'quantity': 1, 'position_rule': 'center', 'height': 6, 'downtilt': 4, 'beamwidth_h': 65, 'gain': 15},
                {'type': 'rru', 'name': 'RRU', 'model': 'RRU-MICRO-5G', 'quantity': 1, 'position_rule': 'below_antenna', 'offset_z': -1, 'parent': 'antenna'},
                {'type': 'bbu', 'name': 'BBU', 'model': 'BBU-MICRO', 'quantity': 1, 'position_rule': 'cabinet_center', 'parent': None}
            ]
        }),
        'topology_rule': 'single_point',
        'coverage_type': 'outdoor',
        'default_params': json.dumps({'antenna_height': 6, 'coverage_radius': 200, 'frequency': 3500, 'sector_count': 1})
    },
    {
        'name': '室内分布系统(单层)',
        'category': 'indoor',
        'description': '适用于楼宇室内覆盖，单楼层',
        'devices_json': json.dumps({
            'devices': [
                {'type': 'rru', 'name': '信源RRU', 'model': 'RRU-INDOOR', 'quantity': 1, 'position_rule': 'equipment_room', 'parent': None},
                {'type': 'splitter', 'name': '功分器', 'model': 'SPL-2WAY', 'quantity': 2, 'position_rule': 'distributed_calc', 'calc_basis': 'floor_area', 'parent': 'rru'},
                {'type': 'antenna', 'name': '室分天线', 'model': 'ANT-CEILING-OMNI', 'quantity': 8, 'position_rule': 'grid', 'spacing': 15, 'height': 3.0, 'gain': 3, 'parent': 'splitter'}
            ]
        }),
        'topology_rule': 'grid',
        'coverage_type': 'indoor',
        'default_params': json.dumps({'floor_area': 1000, 'ceiling_height': 3.5, 'antenna_spacing': 15, 'frequency': 2100})
    }
]

cursor.execute("DELETE FROM m03_parametric_template")

for t in templates:
    sql = """INSERT INTO m03_parametric_template (name, category, description, devices_json, topology_rule, coverage_type, default_params) 
             VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    cursor.execute(sql, (t['name'], t['category'], t['description'], t['devices_json'], t['topology_rule'], t['coverage_type'], t['default_params']))

conn.commit()
cursor.execute("SELECT id, name, category FROM m03_parametric_template")
print("Inserted templates:")
for row in cursor.fetchall():
    print(f"  ID: {row[0]}, Name: {row[1]}, Category: {row[2]}")

conn.close()