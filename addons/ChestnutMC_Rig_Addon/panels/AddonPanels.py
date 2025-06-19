import bpy

from ..config import __addon_name__
from ..operators.AddonOperators import *
from ....common.i18n.i18n import i18n
from ....common.types.framework import reg_order
from .UI import *
from .RigParameters import *


class BasePanel(object):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ChestnutMC"

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True


# 导入面板
@reg_order(0)
class ImportPanel(BasePanel, bpy.types.Panel):
    bl_label = "ChestnutMC Import panel"
    bl_idname = "CHESTNUTMC_PT_ImportPanel"

    def draw(self, context: bpy.types.Context):
        addon_prefs = context.preferences.addons[__addon_name__].preferences

        layout = self.layout
        scene = context.scene

        row = layout.row()
        if CHESTNUTMC_OT_RigImportOperator.poll(context):
            row.label(text="Libraries loaded")
            row.operator(CHESTNUTMC_OT_LoadLibraryOperator.bl_idname, text="Reload Libraries", icon="FILE_REFRESH")
        else:
            row.label(icon="INFO", text="Please load libraries first")
            row.operator(CHESTNUTMC_OT_LoadLibraryOperator.bl_idname, text="Load Libraries")
        layout.separator()

        layout.prop(addon_prefs, "using_mode", text="Mode")
        # layout.props_enum(addon_prefs, "rig_preset")
        # layout.template_list("UI_UL_list","",addon_prefs,"Rig_assets_List",addon_prefs,"Rig_assets_List_index",rows=1,)

        # 预览面板
        row = layout.row()
        row.template_icon_view(scene, "cmc_rig_previews")
        row = layout.row()
        row.prop(scene, "cmc_rig_previews", text='Select Rig')

        # 操作按钮行
        layout.operator(CHESTNUTMC_OT_RigImportOperator.bl_idname, icon="IMPORT")
        row = layout.row()
        colum = row.column()
        colum.operator(CHESTNUTMC_OT_RigSave.bl_idname, icon="FILE_NEW")
        colum.operator(CHESTNUTMC_OT_RigDelete.bl_idname, icon="TRASH")
        colum = row.column()
        colum.operator(CHESTNUTMC_OT_UpdateRigPreview.bl_idname, icon="FILE_REFRESH")
        colum.operator(CMC_OT_RigRename.bl_idname, icon="FILE_TICK")
        layout.separator()

    @classmethod
    def poll(cls, context: bpy.types.Context):
        if context.mode != "OBJECT":
            return False
        return True

# 皮肤面板
@reg_order(1)
class SkinSwapperPanel(BasePanel, bpy.types.Panel):
    bl_label = "ChestnutMC Skin Swapper"
    bl_idname = "CHESTNUTMC_PT_SkinSwapperPanel"

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        addon_prefs = context.preferences.addons[__addon_name__].preferences

        scene = context.scene

        # 列表模板
        layout.label(text="Select Skin")
        row = layout.row()
        row.template_list(
            "CMC_UL_Skin_List",  # 列表类型
            "cmc_skin_list",    # 唯一标识符
            scene,         # 数据源
            "cmc_skin_list",    # 集合属性
            scene,
            "cmc_skin_list_index"   # 活动项索引
        )

        column = row.column(align=True,)
        column.scale_x  = 0.7
        column.operator(CHESTNUTMC_OT_SkinAdd.bl_idname, text="Add", icon='ADD')
        column.operator(CHESTNUTMC_OT_SkinRemove.bl_idname, text="Remove", icon='REMOVE')
        column.separator()
        column.operator(CHESTNUTMC_OT_SkinRename.bl_idname, text="Rename", icon='FILE_TICK')
        if not scene.cmc_skin_list_index >= len(scene.cmc_skin_list):
            column.template_icon(icon_value=skin_previews[scene.cmc_skin_list[scene.cmc_skin_list_index].name].icon_id, scale=4.0)
        layout.operator(CHESTNUTMC_OT_SkinApply.bl_idname, text="Apply Skin", icon='CHECKMARK')
        layout.operator(CHESTNUTMC_OT_SaveFace2Skin.bl_idname, text="Save Arm and Face to Skin", icon='FILE_NEW')

    @classmethod
    def poll(cls, context: bpy.types.Context):
        if context.mode != "OBJECT" and context.mode != 'POSE':
            return False
        return True


# 参数面板
@reg_order(2)
class RigPropertiesPanel(BasePanel, bpy.types.Panel):
    bl_label = "ChestnutMC Rig Properties Panel"
    bl_idname = "CHESTNUTMC_PT_RigPropertiesPanel"

    def draw(self, context: bpy.types.Context):
        layout = self.layout

        # 骨骼参数绘制面板
        # 验证活动物体为骨骼
        armature = None
        if context.active_object and context.active_object.type != "ARMATURE":
            if context.active_object.parent is not None and context.active_object.parent.type == "ARMATURE":
                for child in context.active_object.parent.children:
                    if child.name.startswith("preview"):
                        armature = context.active_object.parent
        elif context.active_object and context.active_object.type == "ARMATURE":
            if context.active_object.children:
                for child in context.active_object.children:
                    if child.name.startswith("preview"):
                        armature = context.active_object
        if armature is not None:
            box  = layout.box()
            get_rig_parameters(box, context, "meum.body.setting")
            box  = layout.box()
            get_rig_parameters(box, context, "meum.face.mouth.setting")
            box  = layout.box()
            row = box.row()
            Lbox = row.box()
            get_rig_parameters(Lbox, context, "meum.arm.setting.R")
            Rbox  = row.box()
            get_rig_parameters(Rbox, context, "meum.arm.setting.L")
            row = box.row()
            Lbox = row.box()
            get_rig_parameters(Lbox, context, "meum.leg.setting.R")
            Rbox  = row.box()
            get_rig_parameters(Rbox, context, "meum.leg.setting.L")

            # 材质参数绘制面板
            box = layout.box()
            get_face_parameters(box, context, "Mouth")
            box = layout.box()
            get_face_parameters(box, context, "Face")
            box = layout.box()
            get_face_parameters(box, context, "Skin")
            box = layout.box()
            get_face_parameters(box, context, "EdgeLight")


        #row.prop(node, "ac_expand", icon="TRIA_DOWN" if node.ac_expand else "TRIA_RIGHT", text="", emboss=False)
    @classmethod
    def poll(cls, context: bpy.types.Context):
        if context.mode != "OBJECT" and context.mode != 'POSE':
            return False
        return True

# 组件面板
@reg_order(3)
class AddonManagerPanel(BasePanel, bpy.types.Panel):
    bl_label = "ChestnutMC Addon Manager Panel"
    bl_idname = "CHESTNUTMC_PT_AddonManagerPanel"

    def draw(self, context: bpy.types.Context):
        layout = self.layout

    @classmethod
    def poll(cls, context: bpy.types.Context):
        if context.mode != "OBJECT":
            return False
        return True


# 动作管理面板
@reg_order(4)
class ActionManagerPanel(BasePanel, bpy.types.Panel):
    bl_label = "ChestnutMC Action Manager Panel"
    bl_idname = "CHESTNUTMC_PT_ActionManagerPanel"

    def draw(self, context: bpy.types.Context):
        layout = self.layout

    @classmethod
    def poll(cls, context: bpy.types.Context):
        if context.mode != 'POSE':
            return False
        return True
