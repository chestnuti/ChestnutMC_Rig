import bpy
import os.path
import glob
import json
import struct

from ..config import __addon_name__
from ..panels.ImageManager import *

#******************** 读取方法 ********************
def read_skin_json(self):
    addon_prefs = bpy.context.preferences.addons[__addon_name__].preferences

    # 验证资产库路径
    try:
        with open(addon_prefs.skin_preset_json, 'r') as f:
            library = json.load(f)
            #print(library)
            return library
    except Exception as e:
        self.report({'ERROR'}, "Fail to load skin json: {}".format(str(e)))
        return None

def search_skin_preset(json, skin_name):
    '''搜索皮肤预设，并返回皮肤预设字典'''
    if json is None:
        return None
    for list, skin_preset in json.items():
        if skin_preset['skin_name'] == skin_name:
            return skin_preset
    return None


#******************** 加载资产库操作 ********************
class CHESTNUTMC_OT_LoadLibraryOperator(bpy.types.Operator):
    '''Load Library Assets'''
    bl_idname = "cmc.load_library"
    bl_label = "Load Library"

    def read_rig_json(self):
        addon_prefs = bpy.context.preferences.addons[__addon_name__].preferences

        # 验证资产库路径
        try:
            with open(addon_prefs.rig_preset_json, 'r') as f:
                library = json.load(f)
                #print(library)
                return library
        except Exception as e:
            self.report({'ERROR'}, "Fail to load rig json: {}".format(str(e)))
            return None

    # 加载资产库
    def execute(self, context: bpy.types.Context):
        addon_prefs = context.preferences.addons[__addon_name__].preferences
        scene = context.scene

        # 验证资产库路径
        if not os.path.isdir(addon_prefs.rig_path):
            self.report({'ERROR'}, "Invalid assets path: {}".format(addon_prefs.rig_path))
            return {'CANCELLED'}
        if not os.path.isdir(addon_prefs.skin_path):
            self.report({'ERROR'}, "Invalid assets path: {}".format(addon_prefs.skin_path))
            return {'CANCELLED'}

        # 清除旧的场景列表
        scene.cmc_rig_list.clear()
        scene.cmc_skin_list.clear()

        # 读取人模资产库JSON文件
        rig_library = self.read_rig_json()
        # 遍历所有Blend文件
        for rig_file in glob.glob(os.path.join(addon_prefs.rig_path, "*.blend")):
            # 获取文件名
            file_name = os.path.basename(rig_file)
            # 写入列表
            item = scene.cmc_rig_list.add()
            item.name = file_name
            item.path = rig_file
            # 载入预览图路径
            if item.name in rig_library:
                item.preview = os.path.join(
                    addon_prefs.rig_preview_path,
                    rig_library[item.name]["preview"]
                )
            else:
                item.preview = ""
            #print(item.preview)
            # 载入预设集合名称
            item.collection = rig_library[item.name]["collection"]

        #加载rig预览
        Load_rig_previews()
        #print(scene.cmc_rig_previews)


        # 读取皮肤资产库JSON文件
        skin_library = read_skin_json(self)
        # 遍历所有Skin文件
        for skin_file in glob.glob(os.path.join(addon_prefs.skin_path, "*.png" or "*.jpg" or "*.jpeg")):
            # 获取文件名
            file_name = os.path.basename(skin_file)
            # 写入列表
            item = scene.cmc_skin_list.add()
            item.name = file_name
            item.path = skin_file
            # 验证是否有脸部预设
            if search_skin_preset(skin_library, item.name):
                item.have_preset = True
            else:
                item.have_preset = False

        # 加载皮肤预览
        Load_skin_previews()

        return {'FINISHED'}




#******************** 人模相关操作 ********************
# 导入人模
class CHESTNUTMC_OT_RigImportOperator(bpy.types.Operator):
    '''Import ChestnutMC Rig'''
    bl_idname = "cmc.rig_import"
    bl_label = "Import ChestnutMC Rig"

    # 确保在操作之前备份数据，用户撤销操作时可以恢复
    bl_options = {'REGISTER', 'UNDO'}

    # 人模库重写功能
    def rig_override(self, collection):
        # 将选中人模进行库重写
        if collection is not None:
            try:
                # 创建库重写
                new_root = collection.override_hierarchy_create(bpy.context.scene, bpy.context.view_layer, do_fully_editable=True)
                # 确保全部重写
                for obj in new_root.all_objects:
                    if obj.data and obj.data.library:  # 若 Mesh 仍为 linked
                        obj.data.override_create(remap_local_usages=True)
                # 删除原集合
                bpy.data.collections.remove(collection)

                # 找到集合中前缀为preview的mesh
                for obj in new_root.objects:
                    if obj.name.startswith("preview"):
                        # 重写材质
                        for slot in obj.material_slots:
                            mat = slot.material
                            # 将材质转为本地项
                            mat.make_local(clear_liboverride=True)
                            if mat.name.startswith("Skin"):
                                # 找到其中名为Adjuster的节点
                                for node in mat.node_tree.nodes:
                                    if node.name == "Adjuster":
                                        # 将材质转为本地项
                                        node.node_tree.make_local(clear_liboverride=True)
                        # 重写几何节点
                        for modifier in obj.modifiers:
                            # 前缀为Delete Alpha Face的几何节点修改器
                            if modifier.type == 'NODES' and modifier.name.startswith("Delete Alpha Face"):
                                # 将几何节点转换为本地项
                                modifier.node_group.make_local(clear_liboverride=True)
                return True
            except Exception as e:
                print({'ERROR'}, "Fail to override rig: {}".format(str(e)))

        return False

    @classmethod
    def poll(cls, context: bpy.types.Context):
        scene = context.scene
        # 检查资产库是否已加载
        if not scene.cmc_rig_list:
            return False
        return True

    def execute(self, context: bpy.types.Context):
        addon_prefs = context.preferences.addons[__addon_name__].preferences

        selected_rig = context.scene.cmc_rig_previews
        selected_rig_path = os.path.join(addon_prefs.rig_path, selected_rig)
        print(selected_rig_path)

        # 验证选中项路径是否存在
        if not os.path.exists(selected_rig_path):
            self.report({'ERROR'}, "Selected rig path does not exist: {}".format(selected_rig_path))
            return {'CANCELLED'}


        # 追加模式：完整复制资源到当前文件
        if addon_prefs.using_mode == 'APPEND':
            # 载入集合
            with bpy.data.libraries.load(selected_rig_path, link=False) as (data_from, data_to):
                data_to.collections = data_from.collections
            for coll in data_to.collections:
                # 验证集合名称
                if coll.name.startswith(context.scene.cmc_rig_list[selected_rig].collection):
                    context.scene.collection.children.link(coll)
                    break
        # 关联模式：创建外部文件链接
        elif addon_prefs.using_mode == 'LINK':
            # 载入集合
            with bpy.data.libraries.load(selected_rig_path, link=True) as (data_from, data_to):
                data_to.collections = data_from.collections
            for coll in data_to.collections:
                # 验证集合名称
                if coll.name.startswith(context.scene.cmc_rig_list[selected_rig].collection):
                    context.scene.collection.children.link(coll)
                    break
            # 创建库重写
            if self.rig_override(coll):
                self.report({'INFO'}, "Rig override complete.")
            else:
                self.report({'ERROR'}, "Rig override failed.")

        # 非法模式
        else:
            self.report({'ERROR'}, "Invalid mode selected")
            return {'CANCELLED'}


        return {'FINISHED'}


# 变更预览图
class CHESTNUTMC_OT_UpdateRigPreview(bpy.types.Operator):
    bl_idname = "cmc.update_rig_preview"
    bl_label = "Update Rig Preview"
    bl_description = "Update the rig preview image"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.cmc_rig_list_index >= 0

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        addon_prefs = context.preferences.addons[__addon_name__].preferences

        # 获取当前选中的人模
        selected_rig = scene.cmc_rig_list[scene.cmc_rig_list_index]



        return {'FINISHED'}


#******************** 皮肤相关操作 ********************
# 添加皮肤
class CHESTNUTMC_OT_SkinAdd(bpy.types.Operator):
    bl_idname = "cmc.skin_add"
    bl_label = "Add Skin"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH") # type: ignore

    filter_glob: bpy.props.StringProperty(
        default="*.png;*.jpg;*.jpeg",
        options={'HIDDEN'}
    ) # type: ignore

    def invoke(self, context, event):
        # 选择文件
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        addon_prefs = context.preferences.addons[__addon_name__].preferences
        scene = context.scene

        #  目标路径
        dest = addon_prefs.skin_path

        # 检查重名项
        if os.path.exists(os.path.join(dest, os.path.basename(self.filepath))):
            # 删除重名文件
            self.report({'ERROR'}, "Skin already exists: {}".format(os.path.basename(self.filepath)))
            return {'CANCELLED'}
        # 将皮肤拷贝到资产库中
        os.system(f'copy "{self.filepath}" "{dest}"')
        self.report({'INFO'}, f"Skin saved to: {dest}")

        # 添加列表
        item = scene.cmc_skin_list.add()
        item.name = os.path.basename(self.filepath)
        item.path = os.path.join(dest, item.name)
        # 验证是否有脸部预设
        if search_skin_preset(read_skin_json(self), item.name):
            item.have_preset = True
        else:
            item.have_preset = False

        # 添加预览
        skin_previews.load(item.name, item.path, 'IMAGE')
        return {'FINISHED'}


# 删除皮肤
class CHESTNUTMC_OT_SkinRemove(bpy.types.Operator):
    bl_idname = "cmc.skin_remove"
    bl_label = "Remove Skin"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        scene = context.scene

        return context.window_manager.invoke_props_dialog(self, title="Are you sure you want to remove skin: {}?".format(scene.cmc_skin_list[scene.cmc_skin_list_index].name))

    def execute(self, context):
        scene = context.scene

        index = scene.cmc_skin_list_index

        if index >= 0:
            try:
            # 删除文件夹中的文件
                skin_path = scene.cmc_skin_list[index].path
                os.remove(skin_path)
            except FileNotFoundError:
                self.report({'INFO'}, f"Skin not found: {skin_path}")
                return {'CANCELED'}

            # 删除列表
            scene.cmc_skin_list.remove(index)

            # 更新预览
            Load_skin_previews()
        else:
            self.report({'ERROR'}, "No skin selected")
            return {'CANCELLED'}


        return {'FINISHED'}

# 重命名皮肤
class CHESTNUTMC_OT_SkinRename(bpy.types.Operator):
    bl_idname = "cmc.skin_rename"
    bl_label = "Rename Skin"
    bl_description = "Rename skin"
    bl_options = {'REGISTER', 'UNDO'}

    new_name: bpy.props.StringProperty(name="New Name") # type: ignore

    def invoke(self, context, event):

        return bpy.context.window_manager.invoke_props_dialog(self)

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        addon_prefs = context.preferences.addons[__addon_name__].preferences

        index = scene.cmc_skin_list_index

        # 文件后缀
        file_name, file_extension = os.path.splitext(scene.cmc_skin_list[index].path)
        # 组装新名字
        self.new_name = self.new_name + file_extension
        # 组装新路径
        new_path = os.path.join(os.path.dirname(scene.cmc_skin_list[index].path), self.new_name)

        # 验证是否有脸部预设
        if scene.cmc_skin_list[index].have_preset:
            # 更新脸部预设名称
            try:
                skin_presets = read_skin_json(self)
                if skin_presets is None:
                    self.report({'ERROR'}, "Failed to load skin presets.")
                    return {'CANCELLED'}
                current_preset = search_skin_preset(skin_presets, scene.cmc_skin_list[index].name)
                current_preset['skin_name'] = self.new_name
                # 更新预设JSON文件
                with open(addon_prefs.skin_preset_json, 'w') as f:
                    json.dump(skin_presets, f, ensure_ascii=False, indent=4)
            except Exception as e:
                self.report({'ERROR'}, "Failed to update face preset: {}".format(str(e)))
                return {'CANCELLED'}

        # 重命名文件
        try:
            os.rename(scene.cmc_skin_list[index].path, new_path)
            self.report({'INFO'}, "Rename Success")
        except Exception as e:
            self.report({'ERROR'}, str(e))

        # 重命名列表
        scene.cmc_skin_list[index].name = self.new_name
        scene.cmc_skin_list[index].path = new_path

        # 更新预览
        Load_skin_previews()

        return {'FINISHED'}


# 应用皮肤
class CHESTNUTMC_OT_SkinApply(bpy.types.Operator):
    bl_idname = "cmc.skin_apply"
    bl_label = "Apply Skin"
    bl_description = "Apply skin"
    bl_options = {'REGISTER', 'UNDO'}


    def apply_face_preset(self, object, selected_skin):
        scene = bpy.context.scene
        addon_prefs = bpy.context.preferences.addons[__addon_name__].preferences
        # 验证当前物体是否有脸部预设
        if not scene.cmc_skin_list[selected_skin].have_preset:
            self.report({'INFO'}, "Selected skin does not have a face preset. Only the base skin will be applied.")
            return False

        # 读取skin预设JSON文件
        skin_presets = read_skin_json(self)
        # 验证预设是否存在
        if search_skin_preset(skin_presets, selected_skin) is None:
            self.report({'INFO'}, "Selected skin preset does not exist.")
            scene.cmc_skin_list[selected_skin].have_preset = False
            return False
        else:
            skin_presets = search_skin_preset(skin_presets, selected_skin)

        # 获取当前活动物体的父级骨骼
        parent_armature = None
        if object.parent is not None and object.parent.type == 'ARMATURE':
            parent_armature = object.parent
        else:
            self.report({'ERROR'}, "Active object is not a valid ChestnutMC Rig.")
            return False

        ##### 应用骨骼预设 #####
        bone_preset = skin_presets["bone"]
        # 遍历字典
        for bone_name in bone_preset:
            bone = parent_armature.pose.bones.get(bone_name)
            if not bone:
                self.report({'ERROR'}, f"Bone '{bone_name}' not found in armature.")
                continue

            # 骨骼位置
            bone.location.x = bone_preset[bone_name][0]
            bone.location.y = bone_preset[bone_name][1]
            bone.location.z = bone_preset[bone_name][2]
            # 骨骼旋转
            bone.rotation_quaternion.x = bone_preset[bone_name][3]
            bone.rotation_quaternion.y = bone_preset[bone_name][4]
            bone.rotation_quaternion.z = bone_preset[bone_name][5]
            # 骨骼缩放
            bone.scale.x = bone_preset[bone_name][6]
            bone.scale.y = bone_preset[bone_name][7]
            bone.scale.z = bone_preset[bone_name][8]

        ##### 应用属性预设 #####
        property_preset = skin_presets["porperty"]
        # 遍历字典
        for bone_name, prop_name in property_preset.items():
            for prop_name, prop_value in prop_name.items():
                # 骨骼属性赋值
                parent_armature.pose.bones[bone_name][prop_name] = prop_value

        ##### 应用Eye预设 #####
        eye_preset = skin_presets["Eye"]
        # 获取当前活动物体的Face材质
        face_material = None
        for material in object.material_slots:
            if material.name.startswith("Face"):
                face_material = material
                break
        # 找到ChestnutMC_EyeShader节点
        eye_shader = None
        if face_material:
            for node in face_material.material.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree.name.startswith("ChestnutMC_EyeShader"):
                    eye_shader = node
                    break
        # 应用预设
        for prop_name, prop_value in eye_preset.items():
            if eye_shader and prop_name in eye_shader.inputs:
                eye_shader.inputs[prop_name].default_value = prop_value
            else:
                self.report({'ERROR'}, f"Eye shader input '{prop_name}' not found.")

        ##### 应用Face预设 #####
        face_preset = skin_presets["Face"]
        # 找到SkinSorter节点
        skin_sorter = None
        if face_material:
            for node in face_material.material.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree.name.startswith("SkinSorter"):
                    skin_sorter = node
                    break
        # 应用预设
        if skin_sorter:
            for prop_name, prop_value in face_preset.items():
                if prop_name in skin_sorter.inputs:
                    skin_sorter.inputs[prop_name].default_value = prop_value
                else:
                    self.report({'ERROR'}, f"Skin sorter input '{prop_name}' not found.")
        else:
            self.report({'ERROR'}, "Skin sorter node not found in material.")

        ##### 应用Mouth预设 #####
        # 获取当前活动物体的Mouth材质
        mouth_material = None
        for material in object.data.materials:
            if material.name.startswith("Mouth"):
                mouth_material = material
                break
        # 找到ChestnutMC_Mouth节点
        mouth_shader = None
        for node in mouth_material.node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree.name.startswith("ChestnutMC_Mouth"):
                mouth_shader = node
                break
        # 应用预设
        if mouth_shader:
            for prop_name, prop_value in skin_presets["Mouth"].items():
                if prop_name in mouth_shader.inputs:
                    mouth_shader.inputs[prop_name].default_value = prop_value
                else:
                    self.report({'ERROR'}, f"Mouth shader input '{prop_name}' not found.")

        return False

    def apply_skin(self, object, texture):

        # 选中前缀为Skin和EdgeLight的材质
        for material in object.material_slots:
            if material.name.startswith("Skin"):
                self.change_material_texture(material, texture)
            elif material.name.startswith("EdgeLight"):
                self.change_material_texture(material, texture)

        # 处理几何节点修改器
        self.change_geo_texture(object, texture)

        return True

    # 变更材质贴图
    def change_material_texture(self, material, texture):
        tex_account = 0
        only_node = None

        # 找到其中名为Skin Texture的图像节点
        for node in material.material.node_tree.nodes:
            #print(node.name, node.type, node.label)
            if node.type == 'TEX_IMAGE':
                if node.label.startswith("Skin Texture"):
                    # 将选中的皮肤贴图替换掉当前材质中的贴图
                    node.image = texture
                    print("Succeed: " + texture.name)
                    return True
                else:
                    tex_account += 1
                    only_node = node

        # 如果有且仅有一个贴图节点，则替换掉该节点的贴图
        if tex_account == 1:
            only_node.image = texture
            return True

        self.report({'INFO'}, "Failed: " + texture.name)
        return False

    # 变更几何节点贴图
    def change_geo_texture(self, act_object, texture):
        context = bpy.context

        for modifier in act_object.modifiers:
            # 前缀为Delete Alpha Face的几何节点修改器
            if modifier.type == 'NODES' and modifier.name.startswith("Delete Alpha Face"):
                # 获取几何节点树
                node_tree = modifier.node_group
                if not node_tree:
                    print({'ERROR'}, "Cannot find geometry node tree.")
                    continue
                # 遍历所有图像纹理节点
                for node in node_tree.nodes:
                    if node.type == 'IMAGE' and node.image:
                        try:
                            # 加载新图像并替换
                            new_image = texture
                            node.image = new_image
                            # 标记需要更新界面
                            context.area.tag_redraw()
                        except Exception as e:
                            print({'ERROR'}, f"Cannot load texture: {str(e)}")
                            continue

    @classmethod
    def poll(cls, context: bpy.types.Context):
        if context.active_object is not None:
            return context.active_object.type == 'MESH' or context.active_object.type == 'ARMATURE'
        return False

    def execute(self, context):
        # 获取当前选中的皮肤
        selected_skin = context.scene.cmc_skin_list[context.scene.cmc_skin_list_index]

        # 验证选中项路径是否存在
        if not os.path.exists(selected_skin.path):
            self.report({'ERROR'}, f"Skin not found: {selected_skin.name}")
            return {'CANCELLED'}

        applyed = False

        # 加载皮肤图像
        if not bpy.data.images.get(selected_skin.name):
            texture = bpy.data.images.load(selected_skin.path)
        else:
            texture = bpy.data.images[selected_skin.name]

        # 如果当前活动物体是Mesh
        if context.active_object.type == 'MESH':
            # 验证名称前缀是否为"preview"
            if context.active_object.name.startswith("preview"):
                # 应用皮肤
                applyed = self.apply_skin(context.active_object, texture)
                # 如果有脸部预设，则应用脸部预设
                if selected_skin.have_preset:
                    self.apply_face_preset(context.active_object, selected_skin.name)
            else:
                # 获取父级骨骼
                parent_armature = None
                if context.active_object.parent is not None:
                    parent_armature = context.active_object.parent
                    if parent_armature and parent_armature.type == 'ARMATURE':
                        # 获取父级骨骼中名为"preview"的子物体
                        for child in parent_armature.children:
                            if child.type == 'MESH' and child.name.startswith("preview"):
                                # 应用皮肤
                                applyed = self.apply_skin(child, texture)
                                # 如果有脸部预设，则应用脸部预设
                                if selected_skin.have_preset:
                                    self.apply_face_preset(child, selected_skin.name)
                else:
                    self.report({'ERROR'}, "Invalid active object: The active object is not belong to a normative ChestnutMC Rig.")
                    return {'CANCELLED'}
        # 如果当前活动物体是Armature
        elif context.active_object.type == 'ARMATURE':
            # 选择子集中前缀为preview的mesh
            for child in context.active_object.children:
                if child.type == 'MESH' and child.name.startswith("preview"):
                    # 应用皮肤
                    applyed = self.apply_skin(child, texture)
                    # 如果有脸部预设，则应用脸部预设
                    if selected_skin.have_preset:
                        self.apply_face_preset(child, selected_skin.name)

        if applyed:
            self.report({'INFO'}, f"Applied skin: {selected_skin.name}")
            return {'FINISHED'}
        self.report({'ERROR'}, "Invalid active object: The active object is not belong to a normative ChestnutMC Rig.")
        return {'CANCELLED'}


# 储存皮肤脸部预设
class CHESTNUTMC_OT_SaveFace2Skin(bpy.types.Operator):
    bl_idname = "cmc.save_face2skin"
    bl_label = "Save Face to Skin"
    bl_description = "Save the current face to skin"
    bl_options = {'REGISTER', 'UNDO'}

    # 保存预设操作
    def save_preset_values(self, obj, new_preset):
        """保存当前脸部预设值到字典"""
        addon_prefs = bpy.context.preferences.addons[__addon_name__].preferences
        scene = bpy.context.scene

        # 获取父级骨骼
        parent_armature = None
        if obj.parent is not None and obj.parent.type == 'ARMATURE':
            parent_armature = obj.parent
        else:
            return False

        ##### 修改名字 #####
        new_preset["skin_name"] = scene.cmc_skin_list[scene.cmc_skin_list_index].name

        ##### 保存骨骼变换数据 (位置/旋转/缩放)或自定义属性 #####
        for bone in parent_armature.pose.bones:
            # 查找骨骼是否在“bone”字典中存在键值
            if bone.name in new_preset["bone"]:  # 存在则更新
                bone_data = [
                bone.location.x, bone.location.y, bone.location.z,
                bone.rotation_quaternion.x, bone.rotation_quaternion.y, bone.rotation_quaternion.z,
                bone.scale.x, bone.scale.y, bone.scale.z
                ]
                new_preset["bone"][bone.name] = bone_data
            else:
                continue

        ##### 保存骨骼属性参数 #####
        for bone_name, prop_item in new_preset["porperty"].items():
            for prop_name, prop_value in prop_item.items():
                new_preset["porperty"][bone_name][prop_name] = parent_armature.pose.bones[bone_name][prop_name]

        ##### 保存眼睛材质参数 #####
        # 获取当前活动物体的Face材质
        face_material = None
        for material in obj.material_slots:
            if material.name.startswith("Face"):
                face_material = material
                break

        eye_shader = None
        if face_material:
            # 找到ChestnutMC_EyeShader节点
            for node in face_material.material.node_tree.nodes:
                if node.type == 'GROUP' and node.node_tree.name.startswith("ChestnutMC_EyeShader"):
                    eye_shader = node
                    break
        # 保存预设
        for prop_name, prop_value in new_preset["Eye"].items():
            if eye_shader and prop_name in eye_shader.inputs:
                # 获取材质参数值
                if eye_shader.inputs[prop_name].type == 'RGBA':
                    eye_shader.inputs[prop_name].default_value.foreach_get(new_preset["Eye"][prop_name])
                else:
                    new_preset["Eye"][prop_name] = eye_shader.inputs[prop_name].default_value
            else:
                return False

        ##### 保存脸部材质参数 #####
            # 找到SkinSorter节点
            skin_sorter = None
            if face_material:
                for node in face_material.material.node_tree.nodes:
                    if node.type == 'GROUP' and node.node_tree.name.startswith("SkinSorter"):
                        skin_sorter = node
                        break
            # 保存预设
            for prop_name, prop_value in new_preset["Face"].items():
                if skin_sorter and prop_name in skin_sorter.inputs:
                    # 获取材质参数值
                    if skin_sorter.inputs[prop_name].type == 'RGBA':
                        skin_sorter.inputs[prop_name].default_value.foreach_get(new_preset["Face"][prop_name])
                    else:
                        new_preset["Face"][prop_name] = skin_sorter.inputs[prop_name].default_value
                else:
                    return False

        ##### 保存嘴巴材质参数 #####
        # 获取当前活动物体的Mouth材质
        mouth_material = None
        for material in obj.data.materials:
            if material.name.startswith("Mouth"):
                mouth_material = material
                break
        # 找到ChestnutMC_Mouth节点
        mouth_shader = None
        for node in mouth_material.node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree.name.startswith("ChestnutMC_Mouth"):
                mouth_shader = node
                break
        # 保存预设
        if mouth_shader:
            for prop_name, prop_value in new_preset["Mouth"].items():
                if prop_name in mouth_shader.inputs:
                    if mouth_shader.inputs[prop_name].type == 'RGBA':
                        mouth_shader.inputs[prop_name].default_value.foreach_get(new_preset["Mouth"][prop_name])
                    else:
                        new_preset["Mouth"][prop_name] = mouth_shader.inputs[prop_name].default_value
                else:
                    return False


        ##### 保存到json文件 #####
        # 打开json文件
        file = read_skin_json(self)
        # 查找是否有同名预设
        for seq, item in file.items():
            # 如果有同名预设
            if item["skin_name"] == new_preset["skin_name"]:
                file[seq] =  new_preset
                with open(addon_prefs.skin_preset_json, 'w', encoding='utf-8') as f:
                    json.dump(file, f, indent=4, ensure_ascii=False)
                # 更新预览
                Load_skin_previews()
                scene.cmc_skin_list[scene.cmc_skin_list_index].have_preset = True
                return True
        # 如果没有同名预设
        with open(addon_prefs.skin_preset_json, 'w', encoding='utf-8') as f:
            seq = int(list(file.keys())[-1]) + 1
            file[seq] = new_preset
            json.dump(file, f, indent=4, ensure_ascii=False)
        # 更新预览
        Load_skin_previews()
        scene.cmc_skin_list[scene.cmc_skin_list_index].have_preset = True
        return True


    @classmethod
    def poll(cls, context: bpy.types.Context):
        # 确保当前活动物体是Armature或Mesh
        if context.active_object is not None:
            return context.active_object.type == 'ARMATURE' or context.active_object.type == 'MESH'
        return False

    def invoke(self, context: bpy.types.Context, event):
        scene = context.scene

        selected_skin = scene.cmc_skin_list[scene.cmc_skin_list_index]
        # 检查是否有预设
        if selected_skin.have_preset:
            bpy.context.window_manager.invoke_props_dialog(self, title="This skin already have a face preset. Do you want to repalce it?")
            return {'RUNNING_MODAL'}
        else:
            self.execute(context)
            return {'RUNNING_MODAL'}

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        addon_prefs = context.preferences.addons[__addon_name__].preferences

        selected_skin = scene.cmc_skin_list[scene.cmc_skin_list_index]
        # 创建预设字典
        new_preset = {}
        # 打开PresetSaveItem.json文件
        try:
            with open(addon_prefs.preset_save_item_json, 'r') as f:
                new_preset = json.load(f)
                new_preset = new_preset["Face2SkinList"]
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load skin presets: {str(e)}")
            return {'CANCELLED'}

        if new_preset is None:
            self.report({'ERROR'}, "Lost preset data. Reinstall the addon to fix the issue.")
            return {'CANCELLED'}

        # 如果当前活动物体是Mesh
        if context.active_object.type == 'MESH':
            # 验证名称前缀是否为"preview"
            if context.active_object.name.startswith("preview"):
                # 保存预设
                if self.save_preset_values(context.active_object, new_preset):
                    self.report({'INFO'}, "Skin preset saved.")
                    return {'FINISHED'}
            else:
                # 获取父级骨骼
                parent_armature = None
                if context.active_object.parent is not None:
                    parent_armature = context.active_object.parent
                    if parent_armature and parent_armature.type == 'ARMATURE':
                        # 获取父级骨骼中名为"preview"的子物体
                        for child in parent_armature.children:
                            if child.type == 'MESH' and child.name.startswith("preview"):
                                # 保存预设
                                if self.save_preset_values(child, new_preset):
                                    self.report({'INFO'}, "Skin preset saved.")
                                    return {'FINISHED'}
                else:
                    self.report({'ERROR'}, "Invalid active object: The active object is not belong to a normative ChestnutMC Rig.")
                    return {'CANCELLED'}
        # 如果当前活动物体是Armature
        elif context.active_object.type == 'ARMATURE':
            # 选择子集中前缀为preview的mesh
            for child in context.active_object.children:
                if child.type == 'MESH' and child.name.startswith("preview"):
                    # 保存预设
                    if self.save_preset_values(child, new_preset):
                        self.report({'INFO'}, "Skin preset saved.")
                        return {'FINISHED'}

        self.report({'ERROR'}, "Failed to save skin preset.")
        return {'CANCELLED'}
