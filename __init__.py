
bl_info = {
    "name": "Fbxskel",
    "author": "Vaniland",
    "blender": (4, 2, 0),
    "version": (0, 1, 1),
    "location": "File > Import-Export",
    "description": "RE4R fbxskel importer and exporter plugin.",
    "tracker_url": "bilibili Vanilandededed",
    "warning": "",
    "category": "Import-Export",
}

if "bpy" in locals():
    import importlib
    if "importFbxskel" in locals():
        importlib.reload(importFbxskel)
    if "exportFbxskel" in locals():
        importlib.reload(exportFbxskel)
else:
    from . import importFbxskel
    from . import exportFbxskel

import bpy

def menu_func_import(self, context):
    self.layout.operator(importFbxskel.ImportFbxskel.bl_idname, text="Fbxskel (.fbxskel)", icon='PLUGIN')

def menu_func_export(self, context):
    self.layout.operator(exportFbxskel.ExportFbxskel.bl_idname, text="Fbxskel (.fbxskel)", icon='PLUGIN')


def register():
    print("Fbxskel register")
    importFbxskel.register()
    exportFbxskel.register()

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister(): 
    print("Fbxskel unregister")
    importFbxskel.unregister()
    exportFbxskel.unregister()

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()

