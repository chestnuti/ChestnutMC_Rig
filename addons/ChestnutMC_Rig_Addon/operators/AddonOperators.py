import bpy
import os.path
import glob
import json
import struct
import shutil
import datetime

from ..config import __addon_name__
from ..panels.ImageManager import *


#*****************************************************
#********************* 读取方法 ***********************
#*****************************************************

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

def search_skin_preset(json, skin_name):
    '''搜索皮肤预设，并返回皮肤预设字典'''
    if json is None:
        return None
    for list, skin_preset in json.items():
        if skin_preset['skin_name'] == skin_name:
            return skin_preset
    return None

def check_cmc_rig(selected_object: bpy.types.Object):
    # 如果当前活动物体是Mesh
    if selected_object.type == 'MESH':
        # 验证名称前缀是否为"preview"
        if selected_object.name.startswith("preview"):
            return True
        else:
            # 获取父级骨骼
            parent_armature = None
            if selected_object.parent is not None:
                parent_armature = selected_object.parent
                if parent_armature and parent_armature.type == 'ARMATURE':
                    # 获取父级骨骼中名为"preview"的子物体
                    for child in parent_armature.children:
                        if child.type == 'MESH' and child.name.startswith("preview"):
                            return True
            else:
                return False
    # 如果当前活动物体是Armature
    elif selected_object.type == 'ARMATURE':
        # 选择子集中前缀为preview的mesh
        for child in selected_object.children:
            if child.type == 'MESH' and child.name.startswith("preview"):
                return True

    return False

def get_cmc_rig(selected_object: bpy.types.Object):
    if check_cmc_rig(selected_object):
        if selected_object.type == 'ARMATURE':
            for child in selected_object.children:
                if child.type == 'MESH' and child.name.startswith("preview"):
                    return selected_object
        elif selected_object.type == 'MESH':
            if selected_object.parent.type == 'ARMATURE':
                for chile in selected_object.parent.children:
                    if chile.type == 'MESH' and chile.name.startswith("preview"):
                        return selected_object.parent
    return None



#*****************************************************
#******************* 资产库操作 ***********************
#*****************************************************
# 加载资产库
class CHESTNUTMC_OT_LoadLibraryOperator(bpy.types.Operator):
    '''Load Library Assets'''
    bl_idname = "cmc.load_library"
    bl_label = "Load Library"

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
        rig_library = read_rig_json(self)
        # 遍历所有Blend文件
        for rig_file in glob.glob(os.path.join(addon_prefs.rig_path, "*.blend")):
            # 获取文件名
            file_name = os.path.basename(rig_file)
            if file_name in rig_library:
                # 写入列表
                item = scene.cmc_rig_list.add()
                item.name = rig_library[file_name]["name"]
                item.path = rig_file
                # 载入预览图路径和预设集合名称
                preview_path = os.path.join(addon_prefs.rig_preview_path, os.path.splitext(file_name)[0] + ".png")
                item.preview = preview_path if os.path.exists(preview_path) else os.path.join(addon_prefs.rig_preview_path, "NO_PREVIEW.png")
                item.collection = rig_library[file_name]["collection"]
            else:
                self.report({'WARNING'}, "Invalid rig library: {}".format(file_name))
            #print(item.preview)

        #加载rig预览
        Load_rig_previews()
        #print(scene.cmc_rig_previews)


        # 读取皮肤资产库JSON文件
        skin_library = read_skin_json(self)
        # 遍历所有Skin文件
        skin_list = []
        for skin_file in glob.glob(os.path.join(addon_prefs.skin_path, "*.png")):
            skin_list.append(skin_file)
        for skin_file in glob.glob(os.path.join(addon_prefs.skin_path, "*.jpg")):
            skin_list.append(skin_file)
        for skin_file in glob.glob(os.path.join(addon_prefs.skin_path, "*.jpeg")):
            skin_list.append(skin_file)

        for skin_file in skin_list:
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



# 导出资产库
class CHESTNUTMC_OT_Export_Asset_Library(bpy.types.Operator):
    bl_idname = "cmc.export_asset_library"
    bl_label = "Export Asset Library"
    bl_description = "Export Asset Library"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="DIR_PATH") # type: ignore

    def invoke(self, context, event):
        # 选择路径
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):

        ex_path = os.path.join(self.filepath, "ChestnutMC_AssetLibrary")
        assets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../assets"))
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../config"))

        # 复制文件到目标目录
        try:
            os.makedirs(ex_path, exist_ok=True)
            shutil.copytree(assets_path, os.path.join(ex_path, "assets"), dirs_exist_ok=True)
            shutil.copytree(config_path, os.path.join(ex_path, "config"), dirs_exist_ok=True)
        except Exception as e:
            self.report({"ERROR"}, f"Export Failed: {e}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Export Success to {ex_path}")
        return {"FINISHED"}


# 合并资产库
class CHESTNUTMC_OT_Merge_Assets(bpy.types.Operator):
    """Merge Assets Library"""
    bl_idname = "cmc.merge_assets"
    bl_label = "Merge Assets Library"
    bl_options = {"REGISTER", "UNDO"}

    # 模式
    mode: bpy.props.EnumProperty(
        items=[
            ("OVERWRITE", "Overwrite Existing items", "Overwrite existing items"),
            ("SKIP", "Skip Existing items", "Skip existing items"),
            ("RENAME", "Rename Existing items", "Rename existing items")
        ],
        default="RENAME"
    ) # type: ignore

    filepath: bpy.props.StringProperty(subtype="DIR_PATH") # type: ignore

    def copy_tree_with_existing(self, src, dst):
        """复制目录树，跳过或重命名已存在的文件"""
        for root, dirs, files in os.walk(src):
            # 创建对应目录结构
            rel_path = os.path.relpath(root, src)
            dest_dir = os.path.join(dst, rel_path)
            os.makedirs(dest_dir, exist_ok=True)

            # 复制文件
            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(dest_dir, file)

                # 仅当目标文件不存在时才复制
                if not os.path.exists(dst_file):
                    shutil.copy2(src_file, dst_file)
                    print(f"copied: {src_file} -> {dst_file}")
                else:
                    # 跳过已存在的
                    if self.mode == "SKIP":
                        print(f"skiped: {dst_file}")
                    # 重命名已存在的
                    elif self.mode == "RENAME":
                        suffix = 1
                        # 重命名源文件
                        while True:
                            # 生成新文件名
                            src_new_name = os.path.splitext(src_file)[0] + "_" + str(suffix) + os.path.splitext(src_file)[1]
                            src_original_name = src_file
                            dest_new_name = os.path.splitext(dst_file)[0] + "_" + str(suffix) + os.path.splitext(dst_file)[1]
                            os.rename(src_file, src_new_name)
                            if not os.path.exists(dest_new_name):
                                shutil.copy2(src_new_name, dest_new_name)
                                print(f"copied: {src_file} -> {dst_file}")
                                # 还原名字
                                os.rename(src_new_name, src_original_name)
                                break
                            suffix += 1

    def merge_rig_json(self, src_json_path, dest_json_path):
        try:
            with open(src_json_path, "r", encoding="utf-8") as src_file:
                src_json = json.load(src_file)

            with open(dest_json_path, "r", encoding="utf-8") as dest_file:
                dest_json = json.load(dest_file)
        except Exception as e:
            self.report({"ERROR"}, f"JSON Open Failed: {e}")
            return {"CANCELLED"}

        for src_name, src_value in src_json.items():
            new_name = src_name
            suffix = 1
            if src_name in dest_json:
                if self.mode == "OVERWRITE":
                    dest_json[src_name] = src_value
                elif self.mode == "SKIP":
                    continue
                elif self.mode == "RENAME":
                    while True:
                        # 新文件名
                        new_name = os.path.splitext(src_name)[0] + "_" + str(suffix) + os.path.splitext(src_name)[1]
                        suffix += 1
                        if new_name not in dest_json:
                            break
                    dest_json[new_name] = src_value
                    dest_json[new_name]["path"] = new_name
                    dest_json[new_name]["preview"] = os.path.splitext(new_name)[0] + ".png"
            else:
                dest_json[new_name] = src_value
            # 查找name重名项
            suffix = 1
            for dest_name, dest_value in dest_json.items():
                if src_value["name"] == dest_value["name"]:
                    if dest_name != new_name:
                        # 获取当前系统时间
                        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                        # 重命名
                        dest_json[new_name]["name"] = dest_json[new_name]["name"] + f"_{suffix}_{timestamp}"
                        suffix += 1

        # 保存
        with open(dest_json_path, "w", encoding="utf-8") as dest_file:
            json.dump(dest_json, dest_file, ensure_ascii=False, indent=4)


    def merge_skin_json(self, src_json_path, dest_json_path):
        try:
            with open(src_json_path, "r", encoding="utf-8") as src_file:
                src_json = json.load(src_file)

            with open(dest_json_path, "r", encoding="utf-8") as dest_file:
                dest_json = json.load(dest_file)
        except Exception as e:
            self.report({"ERROR"}, f"JSON Open Failed: {e}")

        # 检查重名皮肤预设，并返回序号
        def check_skin_name(skin_name):
            for dest_i, dest_value in dest_json.items():
                if skin_name == dest_value["skin_name"]:
                    return dest_i
            return -1

        for src_i, src_value in src_json.items():
            suffix = 1
            i = check_skin_name(src_value["skin_name"])
            if i != -1:
                if self.mode == "OVERWRITE":
                    dest_json[i] = src_value
                elif self.mode == "SKIP":
                    continue
                elif self.mode == "RENAME":
                    while True:
                        # 新名字
                        new_name = os.path.splitext(src_value["skin_name"])[0] + f"_{suffix}" + os.path.splitext(src_value["skin_name"])[1]
                        suffix += 1
                        if check_skin_name(new_name) == -1:
                            i = int(list(dest_json.keys())[-1]) + 1
                            src_value["skin_name"] = new_name
                            dest_json[i] = src_value
                            break
            else:
                i = int(list(dest_json.keys())[-1]) + 1
                dest_json[i] = src_value

        # 保存
        with open(dest_json_path, "w", encoding="utf-8") as dest_file:
            json.dump(dest_json, dest_file, ensure_ascii=False, indent=4)


    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: bpy.types.Context):
        addon_perefers = context.preferences.addons[__addon_name__].preferences

        selected_assets_path = os.path.abspath(os.path.join(self.filepath, "assets"))
        selected_config_path = os.path.abspath(os.path.join(self.filepath, "config"))

        dest_assets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../assets"))
        dest_config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../config"))

        # 检查路径是否存在
        if not os.path.exists(selected_assets_path):
            self.report({'ERROR'}, "Assets path not found: " + selected_assets_path)
            return {'CANCELLED'}
        if not os.path.exists(selected_config_path):
            self.report({'ERROR'}, "Config path not found: " + selected_config_path)
            return {'CANCELLED'}

        # 覆盖重名项复制
        if self.mode == "OVERWRITE":
            try:
                shutil.copytree(selected_assets_path, dest_assets_path, dirs_exist_ok=True)
            except Exception as e:
                self.report({"ERROR"}, f"Assets Merge Failed: {e}")
                return {"CANCELLED"}
        # 跳过或重命名重名项复制
        elif self.mode == "SKIP" or self.mode == "RENAME":
            try:
                self.copy_tree_with_existing(selected_assets_path, dest_assets_path)
            except Exception as e:
                self.report({"ERROR"}, f"Assets Merge Failed: {e}")
                return {"CANCELLED"}
        else:
            self.report({"ERROR"}, "Invalid mode")
            return {"CANCELLED"}

        self.merge_rig_json(os.path.join(selected_config_path, "RigPresets.json"), addon_perefers.rig_preset_json)
        self.merge_skin_json(os.path.join(selected_config_path, "SkinPresets.json"), addon_perefers.skin_preset_json)

        # 重新加载资产库
        bpy.ops.cmc.load_library()

        return {"FINISHED"}



#*****************************************************
#******************** 人模相关操作 ********************
#*****************************************************
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
        selected_rig_path = context.scene.cmc_rig_list[selected_rig].path

        # 验证选中项路径是否存在
        if not os.path.exists(selected_rig_path):
            self.report({'ERROR'}, "Selected rig path does not exist: {}".format(selected_rig_path))
            return {'CANCELLED'}

        # 选择骨骼名字前缀
        selected_rig_name = os.path.splitext(context.scene.cmc_rig_list[selected_rig].collection)[0]

        # 追加模式：完整复制资源到当前文件
        if addon_prefs.using_mode == 'APPEND':
            # 载入集合
            with bpy.data.libraries.load(selected_rig_path, link=False) as (data_from, data_to):
                data_to.collections = data_from.collections
            for coll in data_to.collections:
                # 验证集合名称
                if coll.name.startswith(selected_rig_name):
                    context.scene.collection.children.link(coll)
                    break
        # 关联模式：创建外部文件链接
        elif addon_prefs.using_mode == 'LINK':
            # 载入集合
            with bpy.data.libraries.load(selected_rig_path, link=True) as (data_from, data_to):
                data_to.collections = data_from.collections
            for coll in data_to.collections:
                # 验证集合名称
                if coll.name.startswith(selected_rig_name):
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
    '''Update Rig Preview'''
    bl_idname = "cmc.update_rig_preview"
    bl_label = "Update Preview"
    bl_description = "Update the rig preview image"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.cmc_rig_previews

    def execute(self, context: bpy.types.Context):
        addon_prefs = context.preferences.addons[__addon_name__].preferences

        # 获取选中人模
        selected_rig = context.scene.cmc_rig_previews
        rig_json = read_rig_json(self)
        for item, value in rig_json.items():
            if value['name'] == selected_rig:
                selected_rig = item
                break
        preview_name = os.path.splitext(item)[0] + '.png'

        output_path = os.path.join(addon_prefs.rig_preview_path, preview_name)

        # 保存原渲染路径和格式
        original_render_path = context.scene.render.filepath
        original_render_file_format = context.scene.render.image_settings.file_format
        original_render_resolution_x = context.scene.render.resolution_x
        original_render_resolution_y = context.scene.render.resolution_y
        original_show_overlays = context.space_data.overlay.show_overlays
        original_lens = context.space_data.lens
        # 设置渲染路径和格式
        context.scene.render.image_settings.file_format = 'PNG'
        context.scene.render.filepath = output_path
        context.scene.render.resolution_x = 1080
        context.scene.render.resolution_y = 1080
        context.space_data.overlay.show_overlays = False
        bpy.ops.view3d.view_selected()
        context.space_data.lens = 100

        # 视图渲染
        bpy.ops.render.opengl(write_still=True)

        # 路径还原和格式
        context.scene.render.filepath = original_render_path
        context.scene.render.image_settings.file_format = original_render_file_format
        context.scene.render.resolution_x = original_render_resolution_x
        context.scene.render.resolution_y = original_render_resolution_y
        context.space_data.overlay.show_overlays = original_show_overlays
        context.space_data.lens = original_lens

        # 重新加载资产库
        bpy.ops.cmc.load_library()

        self.report({'INFO'}, "Rig Preview updated.")

        return {'FINISHED'}


# 保存人模
class CHESTNUTMC_OT_RigSave(bpy.types.Operator):
    '''Save Rig'''
    bl_idname = "cmc.rig_save"
    bl_label = "Save Rig"
    bl_description = "Save the rig to the selected path"
    bl_options = {'REGISTER', 'UNDO'}

    rigname: bpy.props.StringProperty(name="Rig name") # type: ignore

    def save_to_blend(self, context: bpy.types.Context, select_collection: str, filename: str):
        addon_prefs = context.preferences.addons[__addon_name__].preferences

        # 设置导出路径
        export_path = os.path.join(addon_prefs.rig_path, filename)
        os.makedirs(os.path.dirname(export_path), exist_ok=True)

        # 检查重名项
        if os.path.exists(export_path):
            return False

        # 要导出的集合名称
        source_coll = bpy.data.collections.get(select_collection)
        if not source_coll:
            print(f"Connot find collection: {select_collection}")
            raise SystemExit

        # 创建导出用场景
        original_scene = bpy.context.scene
        export_scene = bpy.data.scenes.new("CMC_ExportScene")
        bpy.context.window.scene = export_scene

        # 复制源集合到导出场景
        new_coll = source_coll.copy()
        new_coll.name = self.rigname + "_Rig"
        new_coll.name = new_coll.name.replace(".", "_")
        export_scene.collection.children.link(new_coll)

        # 准备写入的数据
        data_blocks = {export_scene}

        # 写入 .blend 文件
        bpy.data.libraries.write(export_path, data_blocks)
        print(f"Collection '{source_coll.name}' have already exported to: {export_path}")

        # 清理
        bpy.context.window.scene = original_scene
        bpy.data.scenes.remove(export_scene)

        return new_coll.name

    # 保存预设到json文件
    def save_rig_json(self, context: bpy.types.Context, new_coll_name: str, filename: str):
        addon_prefs = context.preferences.addons[__addon_name__].preferences

        new_preset = {
            "name": self.rigname,
            "collection": new_coll_name,
        }

        # 打开人模json文件
        rig_json = read_rig_json(self)
        rig_json[filename] = new_preset
        # 保存
        with open(addon_prefs.rig_preset_json, 'w', encoding='utf-8') as f:
            json.dump(rig_json, f, indent=4, ensure_ascii=False)


    def invoke(self, context, event):
        return bpy.context.window_manager.invoke_props_dialog(self)

    @classmethod
    def poll(cls, context: bpy.types.Context):
        if context.active_object is not None:
            return check_cmc_rig(context.active_object)
        return False

    def execute(self, context):
        selected_obj = context.active_object

        if check_cmc_rig(selected_obj):
            # 获取骨骼
            selected_rig = get_cmc_rig(selected_obj)
            if selected_rig is None:
                self.report({"ERROR"}, "Connot find ChestnutMC rig!")
                return {"CANCELLED"}

            if self.rigname == "":
                self.rigname = selected_rig.name
            # 规范命名
            self.rigname = self.rigname.replace(".", "_")
            filename = self.rigname.replace(" ", "_")
            filename = filename + ".blend"

            # 检查json中重名项
            rig_json = read_rig_json(self)
            for key, value in rig_json.items():
                if value['name'] == self.rigname:
                    self.report({'ERROR'}, "Rig name have already exists. Please choose another name.")
                    return {'CANCELLED'}

            # 获取选中物体所属集合
            select_collection = selected_rig.users_collection[0].name
            # 保存到新blend文件并获取集合名字
            new_coll_name = self.save_to_blend(context, select_collection, filename)
            if new_coll_name:
                # 写入json文件
                self.save_rig_json(context, new_coll_name, filename)
            else:
                self.report({'ERROR'}, "Rig name have already exists. Please choose another name.")
                return {'CANCELLED'}

            # 重载资产库
            bpy.ops.cmc.load_library()

            # 选中新增人模
            context.scene.cmc_rig_previews = '%s' % self.rigname
            # 更新预览图
            bpy.ops.cmc.update_rig_preview()

            self.report({'INFO'}, f"Rig {self.rigname} saved successfully")
            return {'FINISHED'}

        self.report({'ERROR'}, "Invalid rig selected")
        return {'CANCELLED'}


# 删除人模
class CHESTNUTMC_OT_RigDelete(bpy.types.Operator):
    '''Delete Rig'''
    bl_idname = "cmc.rig_delete"
    bl_label = "Delete Rig"
    bl_description = "Delete the selected rig"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.cmc_rig_previews

    def invoke(self, context, event):
        scene = context.scene

        return context.window_manager.invoke_props_dialog(self, title="Are you sure you want to delete rig: {}?".format(scene.cmc_rig_previews))

    def execute(self, context):
        addon_prefers = bpy.context.preferences.addons[__addon_name__].preferences

        selected_rig_name = context.scene.cmc_rig_previews
        try:
            selected_rig = context.scene.cmc_rig_list[selected_rig_name]
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        # 删除选中人模.blend文件
        if os.path.exists(selected_rig.path):
            os.remove(selected_rig.path)

        # 删除预览图
        if os.path.exists(selected_rig.preview):
            os.remove(selected_rig.preview)

        # 删除json配置
        rig_json = read_rig_json(self)
        for key, value in rig_json.items():
            if value['name'] == selected_rig.name:
                del rig_json[key]
                break

        # 保存
        with open(addon_prefers.rig_preset_json, 'w', encoding='utf-8') as f:
            json.dump(rig_json, f, indent=4, ensure_ascii=False)

        # 重新加载资产库
        bpy.ops.cmc.load_library()

        return {'FINISHED'}


# 重命名人模
class CMC_OT_RigRename(bpy.types.Operator):
    '''Rename the rig'''
    bl_idname = "cmc.rig_rename"
    bl_label = "Rename Rig"
    bl_description = "Rename the rig"
    bl_options = {'REGISTER', 'UNDO'}

    new_name: StringProperty(name="New Name") # type: ignore

    @classmethod
    def poll(cls, context):
        return context.scene.cmc_rig_previews

    def invoke(self, context, event):
        return bpy.context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        addon_prefers = bpy.context.preferences.addons[__addon_name__].preferences

        selected_rig_name = context.scene.cmc_rig_previews
        try:
            selected_rig = context.scene.cmc_rig_list[selected_rig_name]
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        rig_json = read_rig_json(self)

        # 检查重名项
        for key, value in rig_json.items():
            if value['name'] == self.new_name:
                self.report({'ERROR'}, "Rig name already exists!")
                return {'CANCELLED'}

        # 重命名json配置
        for key, value in rig_json.items():
            if value['name'] == selected_rig.name:
                rig_json[key]['name'] = self.new_name
                break
        # 保存
        with open(addon_prefers.rig_preset_json, 'w', encoding='utf-8') as f:
            json.dump(rig_json, f, indent=4, ensure_ascii=False)

        # 重新加载资产库
        bpy.ops.cmc.load_library()

        return {'FINISHED'}





#*****************************************************
#******************** 皮肤相关操作 ********************
#*****************************************************
# 添加皮肤
class CHESTNUTMC_OT_SkinAdd(bpy.types.Operator):
    '''Add Skin'''
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
    '''Delete skin'''
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
    '''Rename skin'''
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
        # 验证重名项
        if os.path.exists(new_path):
            self.report({'ERROR'}, "Skin already exists: {}".format(self.new_name))
            return {'CANCELLED'}

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
    '''Apply skin to the rig'''
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
    '''Save the face preset to skin'''
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
            return check_cmc_rig(context.active_object)
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



#*****************************************************
#******************** 骨骼相关操作 ********************
#*****************************************************

# 复制骨骼变换
def copy_transform(self, context: bpy.types.Context, bone_name: str, aim_bone_name: str):
    armature = context.active_object
    # 复制变换
    bone = context.active_object.pose.bones[bone_name]
    aim_bone = context.active_object.pose.bones[aim_bone_name]
    # 为骨骼添加复制变换约束
    constraint = bone.constraints.new("COPY_TRANSFORMS")
    constraint.target = context.active_object
    constraint.subtarget = aim_bone_name
    # 应用约束
    armature.data.bones.active = bone.bone
    bpy.ops.constraint.apply(constraint=constraint.name, owner='BONE')


# ik/fk无缝切换
class CMC_OT_Switch_IK_FK(bpy.types.Operator):
    """Switch IK/FK"""
    bl_idname = "cmc.switch_ik_fk"
    bl_label = "Switch IK/FK"
    bl_description = "Switch IK/FK"
    bl_options = {'REGISTER', 'UNDO'}


    # 手臂FK转IK
    def arm_fk2ik(self, context: bpy.types.Context, side: str):
        if side != "L" and side != "R":
            return False
        ik_bone_name = "IK.arm." + side
        aim_bone_name = "FK2IK.arm." + side
        meum_bone_name = "meum.arm.setting." + side
        pole_bone_name = "IK_Pole.arm." + side

        copy_transform(self, context, ik_bone_name, aim_bone_name)

        # 切换ikfk参数
        for bone in context.active_object.pose.bones:
            if bone.name == meum_bone_name:
                bone["FK/IK"] = 1
                bone["IK极向独立控制"] = 0
            if bone.name == pole_bone_name:
                # 极向变换归零
                bone.rotation_quaternion = (1, 0, 0, 0)
                bone.rotation_euler = (0, 0, 0)
                bone.location = (0, 0, 0)
                bone.scale = (1, 1, 1)
        return True

    # 手臂IK转FK
    def arm_ik2fk(self, context: bpy.types.Context, side: str):
        if side != "L" and side != "R":
            return False
        bones_name = ["control.upper_arm." + side, "control.lower_arm." + side]
        aim_bones_name = ["IK2FK.upper_arm." + side, "IK2FK.lower_arm." + side]
        meum_bone_name = "meum.arm.setting." + side

        for i, bone_name in enumerate(bones_name):
            copy_transform(self, context, bone_name, aim_bones_name[i])

        # 切换ikfk参数
        for bone in context.active_object.pose.bones:
            if bone.name == meum_bone_name:
                bone["FK/IK"] = 0
                context.active_bone.hide = False
        return True

    # 腿FK转IK
    def leg_fk2ik(self, context: bpy.types.Context, side: str):
        if side != "L" and side != "R":
            return False
        ik_bone_name = "IK.leg." + side
        aim_bone_name = "FK2IK.leg." + side
        meum_bone_name = "meum.leg.setting." + side
        pole_bone_name = "IK_Pole.leg." + side
        aim_pole_bone_name = "FK2IK_Pole.leg." + side
        control_ankle_name = "control.ankle." + side

        copy_transform(self, context, ik_bone_name, aim_bone_name)
        copy_transform(self, context, pole_bone_name, aim_pole_bone_name)

        # 切换ikfk参数
        for bone in context.active_object.pose.bones:
            if bone.name == meum_bone_name:
                bone["FK/IK"] = 1
                #bone["IK极向独立控制"] = 0
            # control.ankle旋转归零
            if bone.name == control_ankle_name:
                bone.rotation_euler = (0, 0, 0)
        return True

    # 腿IK转FK
    def leg_ik2fk(self, context: bpy.types.Context, side: str):
        if side != "L" and side != "R":
            return False
        bones_name = ["control.upper_leg." + side, "control.lower_leg." + side]
        aim_bones_name = ["IK2FK.upper_leg." + side, "IK2FK.lower_leg." + side]
        meum_bone_name = "meum.leg.setting." + side
        feet_bone_name = "control.feet." + side
        ik_bone_name = "IK.leg." + side

        for i, bone_name in enumerate(bones_name):
            copy_transform(self, context, bone_name, aim_bones_name[i])

        # 复制ik控制骨变换至脚踝
        copy_transform(self, context, feet_bone_name, ik_bone_name)

        # 切换ikfk参数
        for bone in context.active_object.pose.bones:
            if bone.name == meum_bone_name:
                bone["FK/IK"] = 0
                context.active_bone.hide = False
            # ik控制骨复位
            if bone.name == ik_bone_name:
                bone.rotation_quaternion = (1, 0, 0, 0)
                bone.rotation_euler = (0, 0, 0)
                bone.location = (0, 0, 0)
                bone.scale = (1, 1, 1)
        return True


    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True

    def execute(self, context: bpy.types.Context):
        return {'FINISHED'}


# 右手手臂fkik调用方法
class CMC_OT_Switch_R_ARM_FKIK(bpy.types.Operator):
    bl_idname = "cmc.switch_r_arm_fkik"
    bl_label = "Seamless switch FK/IK"
    bl_description = "Seamless switch right arm FK/IK"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        if context.mode != "POSE":
            return False
        return True

    def execute(self, context: bpy.types.Context):
        meum_bone = context.object.pose.bones["meum.arm.setting.R"]
        # fk2ik
        if meum_bone["FK/IK"] == 0:
            if CMC_OT_Switch_IK_FK.arm_fk2ik(self, context, "R"):
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Fail to switch arm FK to IK")
                return {'CANCELLED'}
        # ik2fk
        elif meum_bone["FK/IK"] == 1:
            if CMC_OT_Switch_IK_FK.arm_ik2fk(self, context, "R"):
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Fail to switch arm IK to FK")
                return {'CANCELLED'}

# 左手手臂fkik调用方法
class CMC_OT_Switch_L_ARM_FKIK(bpy.types.Operator):
    bl_idname = "cmc.switch_l_arm_fkik"
    bl_label = "Seamless switch FK/IK"
    bl_description = "Seamless switch left arm FK/IK"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        if context.mode != "POSE":
            return False
        return True

    def execute(self, context: bpy.types.Context):
        meum_bone = context.object.pose.bones["meum.arm.setting.L"]
        # fk2ik
        if meum_bone["FK/IK"] == 0:
            if CMC_OT_Switch_IK_FK.arm_fk2ik(self, context, "L"):
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Fail to switch arm FK to IK")
                return {'CANCELLED'}
        # ik2fk
        elif meum_bone["FK/IK"] == 1:
            if CMC_OT_Switch_IK_FK.arm_ik2fk(self, context, "L"):
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Fail to switch arm IK to FK")
                return {'CANCELLED'}

# 右腿腿部fkik调用方法
class CMC_OT_Switch_R_LEG_FKIK(bpy.types.Operator):
    bl_idname = "cmc.switch_r_leg_fkik"
    bl_label = "Switch Right Leg FK/IK"
    bl_description = "Switch Right Leg FK/IK"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        if context.mode != "POSE":
            return False
        return True

    def execute(self, context):
        meum_bone = context.object.pose.bones["meum.leg.setting.R"]
        # fk2ik
        if meum_bone["FK/IK"] == 0:
            if CMC_OT_Switch_IK_FK.leg_fk2ik(self, context, "R"):
                return {"FINISHED"}
            else:
                self.report({"ERROR"}, "Fail to switch leg FK to IK")
                return {"CANCELLED"}
        # ik2fk
        if meum_bone["FK/IK"] == 1:
            if CMC_OT_Switch_IK_FK.leg_ik2fk(self, context, "R"):
                return {"FINISHED"}
            else:
                self.report({"ERROR"}, "Fail to switch leg IK to FK")
                return {"CANCELLED"}

# 左腿腿部fkik调用方法
class CMC_OT_Switch_L_LEG_FKIK(bpy.types.Operator):
    bl_idname = "cmc.switch_l_leg_fkik"
    bl_label = "Switch left Leg FK/IK"
    bl_description = "Switch left Leg FK/IK"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        if context.mode != "POSE":
            return False
        return True

    def execute(self, context):
        meum_bone = context.object.pose.bones["meum.leg.setting.L"]
        # fk2ik
        if meum_bone["FK/IK"] == 0:
            if CMC_OT_Switch_IK_FK.leg_fk2ik(self, context, "L"):
                return {"FINISHED"}
            else:
                self.report({"ERROR"}, "Fail to switch leg FK to IK")
                return {"CANCELLED"}
        # ik2fk
        if meum_bone["FK/IK"] == 1:
            if CMC_OT_Switch_IK_FK.leg_ik2fk(self, context, "L"):
                return {"FINISHED"}
            else:
                self.report({"ERROR"}, "Fail to switch leg IK to FK")
                return {"CANCELLED"}