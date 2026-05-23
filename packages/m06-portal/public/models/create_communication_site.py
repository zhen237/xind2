import bpy
import math

# ==============================================
# 通信厂区 3D 建模脚本
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
    
    # 获取或创建 Principled BSDF 节点
    if "Principled BSDF" in mat.node_tree.nodes:
        bsdf = mat.node_tree.nodes["Principled BSDF"]
    else:
        bsdf = mat.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
        # 连接到输出节点
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

def create_tower():
    """创建通信铁塔 (30m高)"""
    tower_height = 30
    segment_height = 6
    num_segments = int(tower_height / segment_height)
    
    for i in range(num_segments):
        width = 4 - i * 0.4
        height = segment_height
        z_pos = i * segment_height
        
        # 四个主柱
        corners = [(width/2, width/2), (-width/2, width/2), (width/2, -width/2), (-width/2, -width/2)]
        for j, (x, y) in enumerate(corners):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=height, location=(x, y, z_pos + height/2))
            pillar = bpy.context.active_object
            pillar.name = f"Tower_Pillar_{i}_{j}"
            mat = create_material("Steel", (0.7, 0.7, 0.7, 1), 0.8, 0.4)
            pillar.data.materials.append(mat)
            
            # 水平横梁
            if j < 3:
                x2, y2 = corners[j+1]
                length = math.sqrt((x2-x)**2 + (y2-y)**2)
                angle = math.atan2(y2 - y, x2 - x)
                bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=length, location=((x+x2)/2, (y+y2)/2, z_pos + height*0.3))
                beam = bpy.context.active_object
                beam.name = f"Tower_Beam_{i}_{j}"
                beam.rotation_euler = (0, math.pi/2, angle)
                beam.data.materials.append(mat)
    
    # 添加天线平台
    bpy.ops.mesh.primitive_cylinder_add(radius=2.5, depth=0.3, location=(0, 0, tower_height - 1))
    platform = bpy.context.active_object
    platform.name = "Antenna_Platform"
    platform.data.materials.append(create_material("Steel", (0.7, 0.7, 0.7, 1), 0.8, 0.4))
    
    # 添加3个板状天线
    for i in range(3):
        angle = i * (2 * math.pi / 3)
        x = 1.5 * math.cos(angle)
        y = 1.5 * math.sin(angle)
        
        # 天线面板
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, tower_height + 0.5))
        antenna = bpy.context.active_object
        antenna.name = f"Panel_Antenna_{i+1}"
        antenna.scale = (0.4, 0.04, 1.0)
        bpy.ops.object.transform_apply(scale=True)
        antenna.data.materials.append(create_material("Antenna", (0.15, 0.3, 0.6, 1), 0.0, 0.6))
    
    print("✓ 已创建通信铁塔")

def create_equipment_room():
    """创建机房建筑 (8m x 5m x 3m)"""
    # 主体
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-20, -10, 0))
    room = bpy.context.active_object
    room.name = "Equipment_Room"
    room.scale = (4, 2.5, 1.5)
    bpy.ops.object.transform_apply(scale=True)
    
    mat_wall = create_material("Wall", (0.95, 0.95, 0.95, 1), 0.0, 0.6)
    room.data.materials.append(mat_wall)
    
    # 屋顶
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-20, -10, 3))
    roof = bpy.context.active_object
    roof.name = "Roof"
    roof.scale = (4.2, 2.7, 0.2)
    bpy.ops.object.transform_apply(scale=True)
    roof.data.materials.append(create_material("Roof", (0.3, 0.3, 0.5, 1), 0.1, 0.7))
    
    # 门
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-20, -12.6, 0.75))
    door = bpy.context.active_object
    door.name = "Door"
    door.scale = (0.7, 0.03, 1.4)
    bpy.ops.object.transform_apply(scale=True)
    door.data.materials.append(create_material("Door", (0.3, 0.2, 0.1, 1), 0.0, 0.7))
    
    # 空调外机
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-15.5, -10, 0.8))
    ac = bpy.context.active_object
    ac.name = "AC_Unit"
    ac.scale = (0.5, 0.35, 0.5)
    bpy.ops.object.transform_apply(scale=True)
    ac.data.materials.append(create_material("AC", (0.85, 0.85, 0.85, 1), 0.3, 0.6))
    
    print("✓ 已创建机房")

def create_cabinets():
    """创建设备机柜"""
    # 机柜1
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-12, -8, 0))
    cabinet1 = bpy.context.active_object
    cabinet1.name = "Cabinet_1"
    cabinet1.scale = (0.5, 0.35, 1.1)
    bpy.ops.object.transform_apply(scale=True)
    
    # 机柜2
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-10.8, -8, 0))
    cabinet2 = bpy.context.active_object
    cabinet2.name = "Cabinet_2"
    cabinet2.scale = (0.5, 0.35, 1.1)
    bpy.ops.object.transform_apply(scale=True)
    
    mat = create_material("Cabinet", (0.15, 0.15, 0.15, 1), 0.6, 0.4)
    cabinet1.data.materials.append(mat)
    cabinet2.data.materials.append(mat)
    
    print("✓ 已创建设备机柜")

def create_cables():
    """创建线缆"""
    # 主电缆沟
    bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=40, location=(-10, 0, -0.5))
    trench = bpy.context.active_object
    trench.name = "Cable_Trench"
    trench.rotation_euler = (math.pi/2, 0, 0)
    trench.data.materials.append(create_material("Trench", (0.3, 0.3, 0.3, 1), 0.0, 0.8))
    
    # 三根电缆
    for i in range(3):
        bpy.ops.curve.primitive_bezier_curve_add(location=(0, 0, -0.3))
        cable = bpy.context.active_object
        cable.name = f"Cable_{i+1}"
        cable.data.dimensions = '3D'
        cable.data.bevel_depth = 0.04
        
        # 设置曲线点
        points = cable.data.splines[0].bezier_points
        points[0].co = (0, i * 0.2, -0.3)
        points[0].handle_right = (5, i * 0.2, -0.3)
        points[1].co = (-20, i * 0.2, -0.3)
        points[1].handle_left = (-15, i * 0.2, -0.3)
        
        cable.data.materials.append(create_material("Cable", (0.1, 0.1, 0.1, 1), 0.0, 0.8))
    
    print("✓ 已创建线缆")

def create_fence():
    """创建围栏"""
    fence_height = 2
    positions = []
    
    # 北侧围栏支柱
    for i in range(21):
        positions.append((-50 + i * 5, 50, fence_height/2))
        positions.append((-50 + i * 5, -50, fence_height/2))
        positions.append((50, -50 + i * 5, fence_height/2))
        positions.append((-50, -50 + i * 5, fence_height/2))
    
    for i, (x, y, z) in enumerate(positions):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=fence_height, location=(x, y, z))
        post = bpy.context.active_object
        post.name = f"Fence_Post_{i}"
        post.data.materials.append(create_material("Fence", (0.7, 0.7, 0.7, 1), 0.7, 0.5))
    
    print("✓ 已创建围栏")

def setup_lighting():
    """设置照明"""
    # 太阳光
    bpy.ops.object.light_add(type='SUN', location=(40, 40, 80))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 2.0
    sun.data.color = (1.0, 0.98, 0.95)
    
    # 环境光
    bpy.ops.object.light_add(type='AREA', location=(0, 0, 50))
    area = bpy.context.active_object
    area.name = "Ambient"
    area.data.energy = 200
    area.scale = (20, 20, 1)
    bpy.ops.object.transform_apply(scale=True)
    
    print("✓ 已设置照明")

def export_model():
    """导出为 glTF 格式"""
    bpy.ops.export_scene.gltf(
        filepath="communication_site.glb",
        format='GLB',
        export_selected=False,
        export_materials='EXPORT',
        export_apply=True,
        export_normals=True,
        export_uv=True,
        export_animation=False
    )
    print("✓ 模型已导出为 communication_site.glb")

# ==============================================
# 主执行函数
# ==============================================
if __name__ == "__main__":
    clear_scene()
    create_ground()
    create_tower()
    create_equipment_room()
    create_cabinets()
    create_cables()
    create_fence()
    setup_lighting()
    # export_model()  # 取消注释以自动导出
    print("\n🎉 通信厂区建模完成！")
    print("提示：选择 File > Export > glTF 2.0 导出模型")