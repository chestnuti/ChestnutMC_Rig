import bpy
import os
import bpy.utils.previews

from ..config import __addon_name__
from ..preference.AddonPreferences import *


skin_previews = bpy.utils.previews.new()
rig_previews = bpy.utils.previews.new()

# 加载皮肤预览
def Load_skin_previews():
    """Load the skin preview"""
    scene = bpy.context.scene

    # 清除旧的预览图
    skin_previews.clear()

    # 创建皮肤的预览图
    for skin in scene.cmc_skin_list:
        # 只加载预览图
        skin_previews.load(skin.name, skin.path, 'IMAGE')

# 加载Rig预览图
def Load_rig_previews():
    """Load the rig preview"""
    addon_prefs = bpy.context.preferences.addons[__addon_name__].preferences
    scene = bpy.context.scene

    # 清除旧的预览图
    rig_previews.clear()

    # 创建Rig的预览图
    for rig in scene.cmc_rig_list:
        # 加载预览图
        rig_previews.load(rig.name, rig.preview, 'IMAGE')

# rig预览图的EnumProperty回调函数
def enum_previews_from_rig_previews(self, context):
    """EnumProperty callback"""
    scene = bpy.context.scene
    enum_items = []

    if context is None:
        return enum_items

    # 获取预览集合（在init中定义）
    if len(rig_previews) == 0:
        Load_rig_previews()
    pcoll = rig_previews

    files_path = []
    names = []
    for item in scene.cmc_rig_list:
        if item.path:
            files_path.append(item.path)
            names.append(item.name)

    for i, filepath in enumerate(files_path):
        # generates a thumbnail preview for a file.
        name = names[i]
        icon = pcoll.get(name)
        if not icon:
            thumb = pcoll.load(name, filepath, 'IMAGE')
        else:
            thumb = pcoll[name]
        enum_items.append((name, name, "", thumb.icon_id, i))

    return enum_items

# 清除所有预览
def clear_all_previews():
    """Clear all previews"""
    skin_previews.clear()
    rig_previews.clear()
    print("All previews cleared.")