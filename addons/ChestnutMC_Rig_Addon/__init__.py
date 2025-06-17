import bpy

from .config import __addon_name__
from .i18n.dictionary import dictionary
from ...common.class_loader import auto_load
from ...common.class_loader.auto_load import add_properties, remove_properties
from ...common.i18n.dictionary import common_dictionary
from ...common.i18n.i18n import load_dictionary

from .properties import *
from .panels.ImageManager import *


# Add-on info
bl_info = {
    "name": "ChestnutMC Rig Addon",
    "author": "Chestnut_i",
    "blender": (4, 2, 0),
    "version": (0, 0, 1),
    "description": "This is a MC rig addon for Blender. Aims to provide a useful rig and user-friendly interface of rigging.",
    "warning": "This is a test version. Do not use it in current production!",
    "doc_url": "[documentation url]",
    "tracker_url": "[contact email]",
    "support": "COMMUNITY",
    "category": "3D View"
}

_addon_properties = {
    # 人模导入属性
    bpy.types.Scene: {
        "cmc_skin_list": bpy.props.CollectionProperty(type=CMC_SkinListItem),
        "cmc_skin_list_index": bpy.props.IntProperty(name="MC Skin", default=0),
        "cmc_rig_list": bpy.props.CollectionProperty(type=CMC_RigListItem),
        "cmc_rig_list_index": bpy.props.IntProperty(name="MC Rig", default=0),
        "cmc_rig_previews": bpy.props.EnumProperty(
            name="Rig Previews",
            items=enum_previews_from_rig_previews,
        ),
    },

    # 预设属性
    bpy.types.Armature: {
        "cmc_rig_preset": bpy.props.CollectionProperty(type=CMC_RigPresetItem),
    },

    # 物体属性
    bpy.types.Object: {
        "cmc_rig_preset": bpy.props.StringProperty(name="Rig Preset", default=""),
    },

    #面板属性
    bpy.types.Node:{
        "cmc_node_expand": bpy.props.BoolProperty(name="node Expand", default=False),
    },
    bpy.types.PoseBone:{
        "cmc_bone_expand": bpy.props.BoolProperty(name="bone Expand", default=True),
    }
}


# You may declare properties like following, framework will automatically add and remove them.
# Do not define your own property group class in the __init__.py file. Define it in a separate file and import it here.
# 注意不要在__init__.py文件中自定义PropertyGroup类。请在单独的文件中定义它们并在此处导入。
# _addon_properties = {
#     bpy.types.Scene: {
#         "property_name": bpy.props.StringProperty(name="property_name"),
#     },
# }

def register():
    # Register classes
    auto_load.init()
    auto_load.register()
    add_properties(_addon_properties)

    # Internationalization
    load_dictionary(dictionary)
    bpy.app.translations.register(__addon_name__, common_dictionary)

    print("{} addon is installed.".format(__addon_name__))


def unregister():
    clear_all_previews()
    # Internationalization
    bpy.app.translations.unregister(__addon_name__)

    # unRegister classes
    auto_load.unregister()
    remove_properties(_addon_properties)
    print("{} addon is uninstalled.".format(__addon_name__))
