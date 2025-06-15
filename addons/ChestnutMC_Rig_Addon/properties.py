import os

import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty, PointerProperty, CollectionProperty
from bpy.types import AddonPreferences
from .panels.UI import *


#******************** 人模导入属性 ********************
class CMC_RigListItem(bpy.types.PropertyGroup):
    name: StringProperty(name="Name") # type: ignore
    path: StringProperty(name="Rig Asset", subtype="FILE_PATH") # type: ignore
    preview: StringProperty(name="Preview", subtype="FILE_PATH") # type: ignore
    collection: StringProperty(name="Collection", default="") # type: ignore

class CMC_RigPresetItem(bpy.types.PropertyGroup):
    name: StringProperty(name="Name") # type: ignore
    enabled: BoolProperty(name="Enabled", default=False) # type: ignore


#******************** 预设属性 ********************
class CMC_SkinListItem(bpy.types.PropertyGroup):
    name: StringProperty(name="Name") # type: ignore
    path: StringProperty(name="Path") # type: ignore
    have_preset: BoolProperty(name="Have Preset", default=False) # type: ignore



