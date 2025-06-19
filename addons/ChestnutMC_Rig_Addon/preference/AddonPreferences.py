import os

import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty, PointerProperty, CollectionProperty
from bpy.types import AddonPreferences

from ..config import __addon_name__
from ..properties import *


class CMC_ImportPreferences(AddonPreferences):
    # this must match the add-on name (the folder name of the unzipped file)
    bl_idname = __addon_name__

    # https://docs.blender.org/api/current/bpy.props.html
    # The name can't be dynamically translated during blender programming running as they are defined
    # when the class is registered, i.e. we need to restart blender for the property name to be correctly translated.

    #******************** 资产库属性 ********************
    rig_path: StringProperty(
        name="Rig Folder",
        default=os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "../assets/Rig"
        )),
        subtype='DIR_PATH',
    ) # type: ignore
    rig_preset_json: StringProperty(
        name="Rig Folder",
        default=os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "../config/RigPresets.json"
        )),
        subtype='FILE_PATH',
    ) # type: ignore
    rig_preview_path: StringProperty(
        name="Rig Preview Folder",
        default=os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "../assets/Rig/Previews"
        )),
        subtype='DIR_PATH',
    ) # type: ignore

    skin_path: StringProperty(
        name="Skin File",
        default=os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "../assets/Skin"
        )),
        subtype='DIR_PATH',
    ) # type: ignore
    skin_preset_json: StringProperty(
        name="Skin File",
        default=os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "../config/SkinPresets.json"
        )),
        subtype='FILE_PATH',
    ) # type: ignore
    preset_save_item_json: StringProperty(
        name="Preset Save List",
        default=os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "../config/PresetSaveItem.json"
        )),
        subtype='FILE_PATH',
    ) # type: ignore

    #******************** 设置偏好 ********************
    using_mode: EnumProperty(
        name="Mode",
        items=[
            ('APPEND', "Append", "Append the rig"),
            ('LINK', "Link(Override)", "Link the rig"),
        ],
        default='APPEND',
    ) # type: ignore

    #******************** 预设属性 ********************
    rig_presets: {} # type: ignore


    #******************** 绘制面板 ********************
    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.label(text="Add-on Preferences")
        row = layout.row()
        row.label(text="Presets Panel")
        row.operator("cmc.export_asset_library", text="Export Asset Library", icon="EXPORT")
