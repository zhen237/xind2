import bpy
import math

# ==============================================
# 通信厂区 3D 建模脚本 - 完整版
# 使用方法：在 Blender Scripting 工作区运行此脚本
# ==============================================

def clear_scene():
    """清空场景中的所有对象"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0
    print("✓ 已清空场景")

def create_material(name, color, metallic=0.0, roughness=0.5):
    """创建材质"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    
    if "Principled BSDF" in mat.node_tree.nodes:
        bsdf = mat.node_tree.nodes["Principled BSDF"]
    else:
        bsdf = mat.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
        output = mat.node_tree.nodes.get("Material Output")
        if output:
            mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    return mat

def create_ground():
    """创建地面 (200m x 200m)"""
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.scale = (100, 100, 1)
    bpy.ops.object.transform_apply(scale=True)
    
    mat = create_material("Concrete", (0.55, 0.55, 0.55, 1), 0.0, 0.8)
    ground.data.materials.append(mat)
    print("✓ 已创建地面")

def create_road():
    """创建道路网络"""
    # 主道路
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0.01))
    road = bpy.context.active_object
    road.name = "Main_Road"
    road.scale = (50, 6, 1)
    bpy.ops.object.transform_apply(scale=True)
    road.data.materials.append(create_material("Asphalt", (0.25, 0.25, 0.25, 1), 0.1, 0.7))
    
    # 横向道路
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-20, -20, 0.01))
    road2 = bpy.context.active_object
    road2.name = "Side_Road"
    road2.scale = (6, 30, 1)
    bpy.ops.object.transform_apply(scale=True)
    road2.data.materials.append(create_material("Asphalt", (0.25, 0.25, 0.25, 1), 0.1, 0.7))
    
    # 道路标线
    for i in range(-45, 46, 5):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(i, 0, 0.02))
        line = bpy.context.active_object
        line.name = f"Road_Line_{i}"
        line.scale = (2, 0.15, 0.01)
        bpy.ops.object.transform_apply(scale=True)
        line.data.materials.append(create_material("White_Line", (1.0, 1.0, 1.0, 1), 0.0, 0.9))
    
    print("✓ 已创建道路")

def create_tower():
    """创建通信铁塔 (35m高)"""
    tower_height = 35
    
    # 创建塔基
    bpy.ops.mesh.primitive_cylinder_add(radius=3, depth=1, location=(0, 0, 0.5))
    base = bpy.context.active_object
    base.name = "Tower_Base"
    base.data.materials.append(create_material("Concrete", (0.6, 0.6, 0.6, 1), 0.0, 0.8))
    
    # 创建塔架
    segment_height = 7
    num_segments = int(tower_height / segment_height)
    
    for i in range(num_segments):
        width = 5 - i * 0.5
        height = segment_height
        z_pos = i * segment_height
        
        corners = [(width/2, width/2), (-width/2, width/2), (width/2, -width/2), (-width/2, -width/2)]
        for j, (x, y) in enumerate(corners):
            # 主柱
            bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=height, location=(x, y, z_pos + height/2))
            pillar = bpy.context.active_object
            pillar.name = f"Tower_Pillar_{i}_{j}"
            pillar.data.materials.append(create_material("Steel", (0.7, 0.7, 0.7, 1), 0.8, 0.4))
            
            # 水平横梁
            if j < 3:
                x2, y2 = corners[j+1]
                length = math.sqrt((x2-x)**2 + (y2-y)**2)
                angle = math.atan2(y2 - y, x2 - x)
                bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=length, location=((x+x2)/2, (y+y2)/2, z_pos + height*0.3))
                beam = bpy.context.active_object
                beam.name = f"Tower_Beam_{i}_{j}"
                beam.rotation_euler = (0, math.pi/2, angle)
                beam.data.materials.append(create_material("Steel", (0.7, 0.7, 0.7, 1), 0.8, 0.4))
            
            # 斜撑
            if j < 2:
                x3, y3 = corners[j+2]
                length = math.sqrt((x3-x)**2 + (y3-y)**2) * 1.1
                bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=length, location=((x+x3)/2, (y+y3)/2, z_pos + height*0.6))
                brace = bpy.context.active_object
                brace.name = f"Tower_Brace_{i}_{j}"
                brace.rotation_euler = (0, math.pi/2, angle + math.pi/2)
                brace.data.materials.append(create_material("Steel", (0.7, 0.7, 0.7, 1), 0.8, 0.4))
    
    # 天线平台
    bpy.ops.mesh.primitive_cylinder_add(radius=3, depth=0.3, location=(0, 0, tower_height - 1.5))
    platform = bpy.context.active_object
    platform.name = "Antenna_Platform"
    platform.data.materials.append(create_material("Steel", (0.7, 0.7, 0.7, 1), 0.8, 0.4))
    
    # 添加天线阵列
    create_antennas(tower_height)
    
    print("✓ 已创建通信铁塔")

def create_antennas(height):
    """创建天线阵列"""
    # 板状天线
    for i in range(4):
        angle = i * (math.pi / 2)
        x = 2 * math.cos(angle)
        y = 2 * math.sin(angle)
        
        # 天线面板
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, height + 0.8))
        antenna = bpy.context.active_object
        antenna.name = f"Panel_Antenna_{i+1}"
        antenna.scale = (0.5, 0.05, 1.2)
        bpy.ops.object.transform_apply(scale=True)
        antenna.rotation_euler = (0, 0, angle)
        antenna.data.materials.append(create_material("Antenna", (0.15, 0.35, 0.65, 1), 0.0, 0.5))
    
    # 卫星天线
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.8, location=(0, 0, height + 3))
    dish = bpy.context.active_object
    dish.name = "Satellite_Dish"
    dish.scale = (1, 0.2, 1)
    bpy.ops.object.transform_apply(scale=True)
    dish.data.materials.append(create_material("Dish", (0.1, 0.1, 0.1, 1), 0.8, 0.3))
    
    # 支撑杆
    bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=1.5, location=(0, 0, height + 2.2))
    dish_pole = bpy.context.active_object
    dish_pole.name = "Dish_Pole"
    dish_pole.data.materials.append(create_material("Steel", (0.7, 0.7, 0.7, 1), 0.8, 0.4))

def create_buildings():
    """创建建筑物"""
    # 主机房 (8m x 12m x 4m)
    create_equipment_room()
    
    # 办公楼
    create_office_building()
    
    # 仓库
    create_warehouse()
    
    # 员工宿舍
    create_dormitory()
    
    print("✓ 已创建建筑物")

def create_equipment_room():
    """创建主机房"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-25, -15, 0))
    room = bpy.context.active_object
    room.name = "Main_Equipment_Room"
    room.scale = (6, 4, 2)
    bpy.ops.object.transform_apply(scale=True)
    room.data.materials.append(create_material("Wall", (0.92, 0.92, 0.92, 1), 0.0, 0.6))
    
    # 屋顶
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-25, -15, 4))
    roof = bpy.context.active_object
    roof.name = "Main_Roof"
    roof.scale = (6.2, 4.2, 0.25)
    bpy.ops.object.transform_apply(scale=True)
    roof.data.materials.append(create_material("Roof", (0.35, 0.35, 0.55, 1), 0.1, 0.7))
    
    # 门
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-25, -19.1, 1))
    door = bpy.context.active_object
    door.name = "Main_Door"
    door.scale = (0.8, 0.03, 1.8)
    bpy.ops.object.transform_apply(scale=True)
    door.data.materials.append(create_material("Door", (0.35, 0.25, 0.15, 1), 0.0, 0.7))
    
    # 窗户
    for i in range(4):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(-20 + i * 2.5, -15, 2))
        window = bpy.context.active_object
        window.name = f"Main_Window_{i+1}"
        window.scale = (0.6, 0.03, 0.8)
        bpy.ops.object.transform_apply(scale=True)
        window.data.materials.append(create_material("Window", (0.3, 0.5, 0.8, 1), 0.0, 0.3))
    
    # 空调外机
    for i in range(3):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(-18 + i * 2, -15.1, 1))
        ac = bpy.context.active_object
        ac.name = f"AC_Unit_{i+1}"
        ac.scale = (0.5, 0.3, 0.5)
        bpy.ops.object.transform_apply(scale=True)
        ac.data.materials.append(create_material("AC", (0.9, 0.9, 0.9, 1), 0.3, 0.6))

def create_office_building():
    """创建办公楼 (两层)"""
    # 一楼
    bpy.ops.mesh.primitive_cube_add(size=1, location=(20, -20, 0))
    office1 = bpy.context.active_object
    office1.name = "Office_Floor1"
    office1.scale = (8, 6, 3)
    bpy.ops.object.transform_apply(scale=True)
    office1.data.materials.append(create_material("Wall", (0.95, 0.95, 0.95, 1), 0.0, 0.6))
    
    # 二楼
    bpy.ops.mesh.primitive_cube_add(size=1, location=(20, -20, 6))
    office2 = bpy.context.active_object
    office2.name = "Office_Floor2"
    office2.scale = (8, 6, 2.8)
    bpy.ops.object.transform_apply(scale=True)
    office2.data.materials.append(create_material("Wall", (0.95, 0.95, 0.95, 1), 0.0, 0.6))
    
    # 屋顶
    bpy.ops.mesh.primitive_cube_add(size=1, location=(20, -20, 9))
    roof = bpy.context.active_object
    roof.name = "Office_Roof"
    roof.scale = (8.2, 6.2, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    roof.data.materials.append(create_material("Roof", (0.4, 0.4, 0.6, 1), 0.1, 0.7))
    
    # 窗户
    for floor in range(2):
        for col in range(4):
            for row in range(3):
                bpy.ops.mesh.primitive_cube_add(size=1, location=(15 + col * 2.5, -23 + row * 2, 1.5 + floor * 6))
                window = bpy.context.active_object
                window.name = f"Office_Window_{floor+1}_{col+1}_{row+1}"
                window.scale = (0.5, 0.03, 0.7)
                bpy.ops.object.transform_apply(scale=True)
                window.data.materials.append(create_material("Window", (0.3, 0.5, 0.8, 1), 0.0, 0.3))

def create_warehouse():
    """创建仓库"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-35, 20, 0))
    warehouse = bpy.context.active_object
    warehouse.name = "Warehouse"
    warehouse.scale = (10, 8, 3)
    bpy.ops.object.transform_apply(scale=True)
    warehouse.data.materials.append(create_material("Warehouse_Wall", (0.75, 0.7, 0.65, 1), 0.0, 0.7))
    
    # 卷帘门
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-35, 28.1, 1.5))
    door = bpy.context.active_object
    door.name = "Warehouse_Door"
    door.scale = (4, 0.05, 2.5)
    bpy.ops.object.transform_apply(scale=True)
    door.data.materials.append(create_material("Roller_Door", (0.6, 0.6, 0.6, 1), 0.5, 0.5))

def create_dormitory():
    """创建员工宿舍"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(30, 25, 0))
    dorm = bpy.context.active_object
    dorm.name = "Dormitory"
    dorm.scale = (10, 8, 3)
    bpy.ops.object.transform_apply(scale=True)
    dorm.data.materials.append(create_material("Dorm_Wall", (0.85, 0.85, 0.9, 1), 0.0, 0.6))
    
    # 屋顶
    bpy.ops.mesh.primitive_cube_add(size=1, location=(30, 25, 6))
    roof = bpy.context.active_object
    roof.name = "Dorm_Roof"
    roof.scale = (10.2, 8.2, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    roof.data.materials.append(create_material("Roof", (0.4, 0.4, 0.6, 1), 0.1, 0.7))

def create_equipment():
    """创建设备区域"""
    # 室外机柜组
    create_cabinets()
    
    # 发电机房
    create_generator_room()
    
    # 消防设施
    create_fire_fighting()
    
    print("✓ 已创建设备")

def create_cabinets():
    """创建设备机柜组"""
    for row in range(3):
        for col in range(4):
            bpy.ops.mesh.primitive_cube_add(size=1, location=(-15 + col * 2, -5 + row * 3, 0))
            cabinet = bpy.context.active_object
            cabinet.name = f"Cabinet_{row+1}_{col+1}"
            cabinet.scale = (0.5, 0.35, 1.2)
            bpy.ops.object.transform_apply(scale=True)
            cabinet.data.materials.append(create_material("Cabinet", (0.15, 0.15, 0.18, 1), 0.6, 0.4))
    
    # 机柜围栏
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-15, -6.5, 0.6))
    fence = bpy.context.active_object
    fence.name = "Cabinet_Fence"
    fence.scale = (8.5, 0.1, 1.2)
    bpy.ops.object.transform_apply(scale=True)
    fence.data.materials.append(create_material("Fence", (0.6, 0.6, 0.6, 1), 0.7, 0.5))

def create_generator_room():
    """创建发电机房"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-18, 15, 0))
    gen_room = bpy.context.active_object
    gen_room.name = "Generator_Room"
    gen_room.scale = (5, 4, 2)
    bpy.ops.object.transform_apply(scale=True)
    gen_room.data.materials.append(create_material("Generator_Wall", (0.5, 0.5, 0.5, 1), 0.2, 0.7))
    
    # 烟囱
    bpy.ops.mesh.primitive_cylinder_add(radius=0.4, depth=5, location=(-18, 15, 4.5))
    chimney = bpy.context.active_object
    chimney.name = "Chimney"
    chimney.data.materials.append(create_material("Chimney", (0.4, 0.4, 0.4, 1), 0.3, 0.6))

def create_fire_fighting():
    """创建消防设施"""
    # 消防栓
    positions = [(-20, -10), (-10, 10), (10, -15), (25, 15)]
    for i, (x, y) in enumerate(positions):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=0.8, location=(x, y, 0.4))
        hydrant = bpy.context.active_object
        hydrant.name = f"Fire_Hydrant_{i+1}"
        hydrant.data.materials.append(create_material("Fire_Hydrant", (1.0, 0.1, 0.1, 1), 0.0, 0.8))
    
    # 灭火器箱
    for i, (x, y) in enumerate([(-22, -18), (-18, -22), (18, -22), (22, -18)]):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 0.3))
        box = bpy.context.active_object
        box.name = f"Extinguisher_Box_{i+1}"
        box.scale = (0.3, 0.15, 0.5)
        bpy.ops.object.transform_apply(scale=True)
        box.data.materials.append(create_material("Extinguisher_Box", (1.0, 0.1, 0.1, 1), 0.0, 0.8))

def create_cables():
    """创建线缆和管道"""
    # 主电缆沟
    bpy.ops.mesh.primitive_cylinder_add(radius=0.35, depth=50, location=(-7, 0, -0.5))
    trench = bpy.context.active_object
    trench.name = "Main_Cable_Trench"
    trench.rotation_euler = (math.pi/2, 0, 0)
    trench.data.materials.append(create_material("Trench", (0.35, 0.35, 0.35, 1), 0.0, 0.8))
    
    # 分支电缆沟
    bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=35, location=(-25, -8, -0.4))
    trench2 = bpy.context.active_object
    trench2.name = "Branch_Trench"
    trench2.rotation_euler = (math.pi/2, 0, math.pi/2)
    trench2.data.materials.append(create_material("Trench", (0.35, 0.35, 0.35, 1), 0.0, 0.8))
    
    # 管道支架
    for i in range(10):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=2, location=(-30 + i * 3, -5, 1))
        pole = bpy.context.active_object
        pole.name = f"Cable_Pole_{i+1}"
        pole.data.materials.append(create_material("Steel", (0.7, 0.7, 0.7, 1), 0.8, 0.4))
    
    print("✓ 已创建线缆")

def create_fence():
    """创建厂区围栏"""
    fence_height = 2.5
    
    # 围栏支柱
    positions = []
    for i in range(21):
        positions.append((-50 + i * 5, 50, fence_height/2))
        positions.append((-50 + i * 5, -50, fence_height/2))
        positions.append((50, -50 + i * 5, fence_height/2))
        positions.append((-50, -50 + i * 5, fence_height/2))
    
    for i, (x, y, z) in enumerate(positions):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=fence_height, location=(x, y, z))
        post = bpy.context.active_object
        post.name = f"Fence_Post_{i+1}"
        post.data.materials.append(create_material("Steel", (0.7, 0.7, 0.7, 1), 0.7, 0.5))
    
    # 大门
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 50.1, 1.2))
    gate = bpy.context.active_object
    gate.name = "Main_Gate"
    gate.scale = (8, 0.15, 2.2)
    bpy.ops.object.transform_apply(scale=True)
    gate.data.materials.append(create_material("Steel", (0.6, 0.6, 0.6, 1), 0.7, 0.5))
    
    print("✓ 已创建围栏")

def create_landscaping():
    """创建绿化和装饰"""
    # 草地区域
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-30, 30, 0.01))
    grass = bpy.context.active_object
    grass.name = "Lawn_1"
    grass.scale = (15, 15, 1)
    bpy.ops.object.transform_apply(scale=True)
    grass.data.materials.append(create_material("Grass", (0.2, 0.6, 0.2, 1), 0.0, 0.7))
    
    # 树木
    tree_positions = [(-35, 35), (-25, 38), (-30, 32), (25, 35), (30, 30), (35, 33)]
    for i, (x, y) in enumerate(tree_positions):
        create_tree(x, y, name=f"Tree_{i+1}")
    
    # 路灯
    light_positions = [(0, 45), (0, -45), (45, 0), (-45, 0), (30, 30), (-30, -30)]
    for i, (x, y) in enumerate(light_positions):
        create_street_light(x, y, name=f"Street_Light_{i+1}")
    
    print("✓ 已创建绿化")

def create_tree(x, y, name="Tree"):
    """创建树木"""
    # 树干
    bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=2.5, location=(x, y, 1.25))
    trunk = bpy.context.active_object
    trunk.name = f"{name}_Trunk"
    trunk.data.materials.append(create_material("Trunk", (0.4, 0.3, 0.2, 1), 0.0, 0.8))
    
    # 树冠
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.5, location=(x, y, 3.5))
    crown = bpy.context.active_object
    crown.name = f"{name}_Crown"
    crown.scale = (1, 1.5, 1)
    bpy.ops.object.transform_apply(scale=True)
    crown.data.materials.append(create_material("Leaves", (0.25, 0.55, 0.25, 1), 0.0, 0.7))

def create_street_light(x, y, name="Street_Light"):
    """创建路灯"""
    # 灯杆
    bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=6, location=(x, y, 3))
    pole = bpy.context.active_object
    pole.name = f"{name}_Pole"
    pole.data.materials.append(create_material("Steel", (0.75, 0.75, 0.75, 1), 0.8, 0.4))
    
    # 灯头
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + 0.5, y, 6))
    head = bpy.context.active_object
    head.name = f"{name}_Head"
    head.scale = (0.4, 0.1, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    head.data.materials.append(create_material("Light", (0.2, 0.2, 0.2, 1), 0.8, 0.3))

def setup_lighting():
    """设置照明"""
    # 太阳光
    bpy.ops.object.light_add(type='SUN', location=(50, 50, 100))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 2.0
    sun.data.color = (1.0, 0.98, 0.95)
    
    # 环境光
    bpy.ops.object.light_add(type='AREA', location=(0, 0, 60))
    area = bpy.context.active_object
    area.name = "Ambient"
    area.data.energy = 300
    area.scale = (30, 30, 1)
    bpy.ops.object.transform_apply(scale=True)
    
    print("✓ 已设置照明")

def export_model():
    """导出为 glTF 格式"""
    bpy.ops.export_scene.gltf(
        filepath="communication_site_full.glb",
        format='GLB',
        export_selected=False,
        export_materials='EXPORT',
        export_apply=True,
        export_normals=True,
        export_uv=True,
        export_animation=False,
        export_colors=True
    )
    print("✓ 模型已导出为 communication_site_full.glb")

# ==============================================
# 主执行函数
# ==============================================
if __name__ == "__main__":
    clear_scene()
    create_ground()
    create_road()
    create_tower()
    create_buildings()
    create_equipment()
    create_cables()
    create_fence()
    create_landscaping()
    setup_lighting()
    # export_model()  # 取消注释以自动导出
    print("\n🎉 通信厂区建模完成！")
    print("包含：通信铁塔、机房、办公楼、仓库、宿舍、设备机柜、线缆、绿化等")
    print("提示：选择 File > Export > glTF 2.0 导出模型")