from common.i18n.dictionary import preprocess_dictionary

dictionary = {
    "zh_CN": {
        ("*", "ChestnutMC Import panel"): "栗籽人模导入面板",
        ("*", "ChestnutMC Skin Swapper"): "栗籽人模皮肤替换器",
        ("*", "ChestnutMC Rig Properties Panel"): "栗籽人模参数面板",
        ("*", "ChestnutMC Addon Manager Panel"): "栗籽人模组件管理面板",
        ("*", "ChestnutMC Action Manager Panel"): "栗籽人模动作管理器",
        ("*", "Libraries loaded"): "资产库已加载",
        ("*", "Please load libraries first"): "请先加载资产库",
        ("*", "ChestnutC"): "栗籽MC",
        ("*", "Resource Folder"): "资源文件夹",
        ("*", "Append"): "追加",
        ("*", "Link(Override)"): "关联（库重写）",
        ("*", "Select Skin"): "选择皮肤",
        # This is not a standard way to define a translation, but it is still supported with preprocess_dictionary.
        "Boolean Config": "布尔参数",
        "Second Panel": "第二面板",
        "Mode": "模式",
        ("*", "Add-on Preferences View"): "插件设置面板",
        ("Operator", "Import ChestnutMC Rig"): "导入栗籽人模",
        ("Operator", "Load Libraries"): "加载资产库",
        ("Operator", "Reload Libraries"): "重新加载资产库",
    }
}

dictionary = preprocess_dictionary(dictionary)

dictionary["zh_HANS"] = dictionary["zh_CN"]
