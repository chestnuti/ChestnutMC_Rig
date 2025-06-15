import bpy
import os
from ..config import __addon_name__

from .ImageManager import *


# 皮肤列表绘制
class CMC_UL_Skin_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # 获取当前的皮肤列表
        skin_collection = getattr(data, "cmc_skin_list", [])

        if index >= len(skin_collection):
            return

        skin = skin_collection[index]

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            # 验证skin是否有预览图
            if skin.name in skin_previews:
                row.prop(skin, "name", text="", emboss=False, icon_value=skin_previews[skin_collection[index].name].icon_id)  # 加载名称和图标
            else:
                Load_skin_previews()
            if skin.have_preset:
                row.label(icon='CHECKMARK')

        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=skin.preview)