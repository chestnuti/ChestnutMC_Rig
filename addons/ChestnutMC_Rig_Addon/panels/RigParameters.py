import bpy
from ..operators import AddonOperators

Rig_Parameters_bones = {
    "meum.body.setting": "General Setting",
    "meum.face.mouth.setting": "Face Setting",
    "meum.arm.setting.R": "Right Arm Setting",
    "meum.arm.setting.L": "Left Arm Setting",
    "meum.leg.setting.R": "Right Leg Setting",
    "meum.leg.setting.L": "Left Leg Setting"
}

Face_Parameters_nodes = {
    "Skin": ["Adjuster", "Face Texture", "FaceImageMix"],
    "Face": ["ChestnutMC_EyeShader", "SkinSorter"],
    "Mouth": ["ChestnutMC_Mouth"],
    "EdgeLight": ["ChestnutMC_EdgeLight"]
}



# 骨骼参数绘制方法
def get_rig_parameters(box, context: bpy.types.Context, bone_name: str):
    # 获取cmcrig
    armature = AddonOperators.get_cmc_rig(context.active_object)

    # 验证骨骼是否存在
    try:
        bone = armature.pose.bones[bone_name]
    except:
        return None

    # 面板展开与收起
    row = box.row()
    row.prop(bone, "cmc_bone_expand",
                icon="TRIA_DOWN" if bone.cmc_bone_expand else "TRIA_RIGHT",
                text="",
                emboss=True)
    row.label(text=Rig_Parameters_bones[bone_name], icon="POSE_HLT")
    # 面板展开与收起
    if bone.cmc_bone_expand is False:
        return None

    # 获取自定义属性
    custom_props = bone.keys()
    # 绘制参数
    for prop_name in custom_props:
        # 验证属性值是否为数字
        if type(bone[prop_name]) not in [int, float]:
            continue
        if prop_name == "cmc_bone_expand":
            continue
        row = box.row()
        row.prop(bone, '["%s"]' % prop_name, text=prop_name)

    if bone.name == "meum.arm.setting.L":
        row = box.row()
        if bone["FK/IK"] == 0:
            row.operator("cmc.switch_l_arm_fkik", text="Seamless FK->IK", icon="MODIFIER")
        else:
            row.operator("cmc.switch_l_arm_fkik", text="Seamless IK->FK", icon="MODIFIER")
    elif bone.name == "meum.arm.setting.R":
        row = box.row()
        if bone["FK/IK"] == 0:
            row.operator("cmc.switch_r_arm_fkik", text="Seamless FK->IK", icon="MODIFIER")
        else:
            row.operator("cmc.switch_r_arm_fkik", text="Seamless IK->FK", icon="MODIFIER")
    elif bone.name == "meum.leg.setting.L":
        row = box.row()
        if bone["FK/IK"] == 0:
            row.operator("cmc.switch_l_leg_fkik", text="Seamless FK->IK", icon="MODIFIER")
        else:
            row.operator("cmc.switch_l_leg_fkik", text="Seamless IK->FK", icon="MODIFIER")
    elif bone.name == "meum.leg.setting.R":
        row = box.row()
        if bone["FK/IK"] == 0:
            row.operator("cmc.switch_r_leg_fkik", text="Seamless FK->IK", icon="MODIFIER")
        else:
            row.operator("cmc.switch_r_leg_fkik", text="Seamless IK->FK", icon="MODIFIER")


# 面部参数绘制方法
def get_face_parameters(box, context: bpy.types.Context, material_name: str):
    material = None

    armature = AddonOperators.get_cmc_rig(context.active_object)
    for child in armature.children:
        if child.type == 'MESH' and child.name.startswith("preview"):
            for material in child.material_slots:
                if material.material.name.startswith(material_name):
                    material = material.material
                    break

    if material is None:
        return None

    # 在材质节点树中找到对应节点
    for node in material.node_tree.nodes:
        if node.name in Face_Parameters_nodes[material_name]:
            row = box.row()
            # 面板展开与收起
            row.prop(node, "cmc_node_expand",
                icon="TRIA_DOWN" if node.cmc_node_expand else "TRIA_RIGHT",
                text="",
                emboss=True)
            row.label(text=node.name)
            if node.cmc_node_expand is False:
                continue

            newbox = box.box()
            # 如果节点有输入(非图像节点)，则展示未连接节点
            if len(node.inputs) > 1:
                for inp in node.inputs:
                    # 如果节点被连接
                    if inp.is_linked:
                        continue
                    else:
                        newbox.template_node_view(material.node_tree, node, inp)
            # 若为图像节点，则展示节点
            elif node.type == 'TEX_IMAGE':
                newbox.template_image(node, "image", node.image_user)
            # 如果节点无输入则进入节点组(Adjuster)
            else:
                node_tree = bpy.data.node_groups.get(node.node_tree.name)
                for out in node_tree.nodes['组输出'].inputs:
                    # 如果节点有输入
                    if out.is_linked:
                        row = newbox.row()
                        row.alignment = 'RIGHT'
                        row.label(text=out.name)
                        row.label(text="Custom Used", icon= "SETTINGS")
                    else:
                        newbox.template_node_view(node_tree, node, out)