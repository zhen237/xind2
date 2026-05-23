import bpy
import math

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def create_material(name, color, roughness=0.5, metallic=0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for node in nodes:
        nodes.remove(node)
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    output = nodes.new(type='ShaderNodeOutputMaterial')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def create_floor(length, width):
    bpy.ops.mesh.primitive_plane_add(size=1)
    floor = bpy.context.active_object
    floor.name = "厂区地面"
    floor.scale = (length/2, width/2, 1)
    mat = create_material("地面材质", (0.35, 0.35, 0.35, 1), roughness=0.9)
    floor.data.materials.append(mat)
    return floor

def create_road_segment(x, y, length, rotation, width=12):
    bpy.ops.mesh.primitive_plane_add(size=1)
    road = bpy.context.active_object
    road.name = "道路"
    road.scale = (length/2, width/2, 1)
    road.location = (x, y, 0.01)
    road.rotation_euler.z = rotation
    mat = create_material("道路材质", (0.2, 0.2, 0.2, 1), roughness=0.8)
    road.data.materials.append(mat)
    return road

def create_building_simple(name, x, y, width, depth, height, color):
    bpy.ops.mesh.primitive_cube_add(size=1)
    building = bpy.context.active_object
    building.name = name
    building.location = (x, y, height/2)
    building.scale = (width/2, depth/2, height/2)
    mat = create_material(f"{name}材质", color, roughness=0.6)
    building.data.materials.append(mat)
    return building

def create_antenna_tower(x, y, height=25):
    mat_steel = create_material("钢材材质", (0.3, 0.3, 0.3, 1), roughness=0.3, metallic=0.9)
    mat_concrete = create_material("混凝土材质", (0.5, 0.5, 0.5, 1), roughness=0.8)
    
    bpy.ops.mesh.primitive_cylinder_add(radius=1.5, depth=2)
    base = bpy.context.active_object
    base.name = "天线塔基座"
    base.location = (x, y, 1)
    base.data.materials.append(mat_concrete)
    
    bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=height)
    tower = bpy.context.active_object
    tower.name = "天线塔主体"
    tower.location = (x, y, 2 + height/2)
    tower.data.materials.append(mat_steel)
    
    for i in range(3):
        arm_height = 5 + i * 8
        bpy.ops.mesh.primitive_cylinder_add(radius=3, depth=0.2)
        arm = bpy.context.active_object
        arm.name = f"天线臂_{i}"
        arm.location = (x, y, arm_height)
        arm.data.materials.append(mat_steel)
        
        for j in range(3):
            angle = j * 120
            bx = x + 2.5 * math.cos(math.radians(angle))
            by = y + 2.5 * math.sin(math.radians(angle))
            bpy.ops.mesh.primitive_cone_add(radius1=0.2, radius2=0.05, depth=1.5)
            antenna = bpy.context.active_object
            antenna.name = f"天线_{i}_{j}"
            antenna.location = (bx, by, arm_height + 0.75)
            antenna.data.materials.append(mat_steel)
    
    return tower

def create_fence_perimeter():
    mat_fence = create_material("围栏材质", (0.6, 0.6, 0.6, 1), roughness=0.5)
    positions = [(-150, 0, 300, 0), (150, 0, 300, 0), (0, -120, 240, math.radians(90)), (0, 120, 240, math.radians(90))]
    for x, y, length, rot in positions:
        bpy.ops.mesh.primitive_plane_add(size=1)
        fence = bpy.context.active_object
        fence.name = "围栏"
        fence.scale = (length/2, 1.5/2, 1)
        fence.location = (x, y, 1.5/2)
        fence.rotation_euler.z = rot
        fence.data.materials.append(mat_fence)

def create_trees():
    mat_green = create_material("树木材质", (0.15, 0.45, 0.15, 1), roughness=0.8)
    mat_trunk = create_material("树干材质", (0.35, 0.25, 0.15, 1), roughness=0.7)
    
    tree_positions = [
        (-180, 150), (-120, 160), (-60, 155), (0, 158), (60, 152), (120, 160), (180, 150),
        (-180, -150), (-120, -158), (-60, -152), (0, -156), (60, -160), (120, -155), (180, -150),
        (-200, 0), (200, 0), (-190, 80), (190, -80)
    ]
    
    for x, y in tree_positions:
        height = 6 + (hash(f"{x}{y}") % 5)
        bpy.ops.mesh.primitive_cone_add(radius1=2.5, radius2=0.5, depth=height)
        tree = bpy.context.active_object
        tree.name = "树冠"
        tree.location = (x, y, height/2 + 1)
        tree.data.materials.append(mat_green)
        
        bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=2)
        trunk = bpy.context.active_object
        trunk.name = "树干"
        trunk.location = (x, y, 1)
        trunk.data.materials.append(mat_trunk)

def create_lamp_posts():
    mat_metal = create_material("金属材质", (0.2, 0.2, 0.2, 1), roughness=0.3, metallic=0.8)
    
    positions = []
    for i in range(-5, 6):
        positions.append((i * 50, -110))
        positions.append((i * 50, 110))
    
    for x, y in positions:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=5)
        pole = bpy.context.active_object
        pole.name = "路灯杆"
        pole.location = (x, y, 2.5)
        pole.data.materials.append(mat_metal)
        
        bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=0.15)
        lamp = bpy.context.active_object
        lamp.name = "路灯"
        lamp.location = (x, y, 5)
        lamp.data.materials.append(mat_metal)

def main():
    clear_scene()
    
    create_floor(400, 300)
    
    create_road_segment(0, -110, 400, 0)
    create_road_segment(0, 110, 400, 0)
    create_road_segment(-150, 0, 220, math.radians(90))
    create_road_segment(150, 0, 220, math.radians(90))
    
    create_building_simple("主办公楼", 0, 80, 50, 30, 40, (0.15, 0.35, 0.55, 1))
    create_building_simple("生产车间A", -130, 30, 70, 50, 18, (0.6, 0.6, 0.65, 1))
    create_building_simple("生产车间B", 130, 30, 70, 50, 18, (0.6, 0.6, 0.65, 1))
    create_building_simple("数据中心", -100, -50, 40, 30, 22, (0.1, 0.2, 0.35, 1))
    create_building_simple("立体仓库", 100, -50, 60, 40, 25, (0.5, 0.5, 0.7, 1))
    create_building_simple("员工宿舍", -130, -80, 45, 35, 12, (0.75, 0.75, 0.75, 1))
    create_building_simple("食堂", 130, -80, 35, 25, 10, (0.7, 0.55, 0.4, 1))
    
    create_antenna_tower(0, -50, height=28)
    
    create_fence_perimeter()
    create_trees()
    create_lamp_posts()
    
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 64
    
    bpy.ops.object.light_add(type='SUN', location=(100, -100, 80))
    sun = bpy.context.active_object
    sun.data.energy = 2
    
    bpy.ops.object.camera_add(location=(250, -250, 150))
    camera = bpy.context.active_object
    camera.rotation_euler = (math.radians(55), 0, math.radians(45))
    bpy.context.scene.camera = camera
    
    print("通信厂区创建完成！")

if __name__ == "__main__":
    main()