import bpy
import os
import struct
import math
import mathutils

from bpy_extras.io_utils import ImportHelper

class Reader:
    def __init__(self, filePath):
        self.filePath = filePath
        self.file = open(filePath, "rb")
    
    def seek(self, offset):
        self.file.seek(offset)

    def readString(self):
        str = ""
        bFinished = False
        while not bFinished:
            c = self.readShort()
            if c == 0:
                bFinished = True
            # 转换成char
            str += chr(c)
            # if c != 32: ?
        return str

    def readBytes(self, count):
        return self.file.read(count)
    
    def readByte(self):
        return struct.unpack("<B", self.file.read(1))[0]
    
    def readUInt(self):
        return struct.unpack("<I", self.readBytes(4))[0]
    
    def readUInt64(self):
        return struct.unpack("<Q", self.readBytes(8))[0]
    
    def readUShort(self):
        return struct.unpack("<H", self.readBytes(2))[0]
    
    def readFloat(self):
        return struct.unpack("<f", self.readBytes(4))[0]

    def readNormalizedByte(self):
        return self.readByte() / 255.0

    def readShort(self):
        return struct.unpack("<h", self.file.read(2))[0]
             
    def readNormalizedShort(self):
        return self.readShort() / 65535.0
    
class ImportFbxskel(bpy.types.Operator, ImportHelper):
    bl_idname = "import.fbxskel"
    bl_label = "Import fbxskel"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".fbxskel"
    filter_glob: bpy.props.StringProperty(
        default="*.fbxskel.*;*.skeleton.*", 
        options={'HIDDEN'}
        )
    
    files: bpy.props.CollectionProperty(
            name="File Path",
            type=bpy.types.OperatorFileListElement,
            )
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):

        dirPath = os.path.dirname(self.filepath)

        for file in self.files:
            FBXSkelFile(os.path.join(dirPath, file.name))
        if len(self.files)  == 0:
            FBXSkelFile(self.filepath)
        return {'FINISHED'}
    
# class DialogOperator(bpy.types.Operator):
#     bl_idname = "object.dialog_operator"
#     bl_label = "A problem occurred."
#     def execute(self, context):
#         self.report({'ERROR'}, error_message)
#         return {'FINISHED'}
#     def invoke(self, context, event):
#         wm = context.window_manager
#         return wm.invoke_props_dialog(self)
    
# boneslist_file = []
# boneslist_maps = []

class FBXSkelFile():
    def R(self):
        return self.reader

    def __init__(self, filePath):
        
        boneInfos = []
        # 检查当前是不是物体模式
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        # 新建armature
        bpy.ops.object.armature_add()
        bpy.ops.object.mode_set(mode='OBJECT')
        amt = bpy.context.object

        bpy.ops.object.select_all(action='DESELECT')
        amt.select_set(True)
        bpy.context.view_layer.objects.active = amt

        # 切换编辑模式
        bpy.ops.object.mode_set(mode='EDIT')
        # 删除mat所有骨骼
        for bone in amt.data.edit_bones:
            print(bone.matrix)
            amt.data.edit_bones.remove(bone)

        
        self.reader = Reader(filePath)
        self.version = self.reader.readUInt()
        
        self.signature = self.reader.readUInt64()
        if(self.signature != 1852599155):
            print("Select a fbxskel file",self.signature)
            return
        self.reader.seek(0x10)
        self.bonesStartOffs = self.reader.readUInt64()
        
        self.reader.readBytes(8)

        self.boneCount = self.reader.readUInt64()

        print("version:", self.version)
        print("boneCount:", self.boneCount)

        self.namesOffs = []
        self.hierarchy = []
        self.indices = []
        self.bonesList = []

        self.reader.seek(self.bonesStartOffs)
        for i in range(self.boneCount):
            boneInfo = {}
            self.namesOffs.append(self.reader.readUInt64())
            hash = self.reader.readBytes(4)
            boneInfo["hash"] = hash
            hir = self.reader.readShort()
            boneInfo["parent"] = hir
            self.hierarchy.append(hir)
            self.indices.append(self.reader.readShort())

            mat = mathutils.Matrix()
            if self.version == 5:
                rotation = [self.reader.readFloat(), self.reader.readFloat(), self.reader.readFloat(), self.reader.readFloat()]
                translation = [self.reader.readFloat(), self.reader.readFloat(), self.reader.readFloat()]
                self.reader.readBytes(4)
                scale = [self.reader.readFloat(), self.reader.readFloat(), 1.0]
                self.reader.readBytes(8)
            else:
                translation = [self.reader.readFloat(), self.reader.readFloat(), self.reader.readFloat()]
                self.reader.readBytes(4)
                rotation = [self.reader.readFloat(), self.reader.readFloat(), self.reader.readFloat(), self.reader.readFloat()]
                scale = [self.reader.readFloat(), self.reader.readFloat(), self.reader.readFloat()]
                self.reader.readBytes(4)
            boneInfo["translation"] = translation
            boneInfo["rotation"] = rotation
            boneInfo["scale"] = scale
            # boneslist_file.append([judgeZeroArr(translation), judgeZeroArr(rotation), judgeZeroArr(scale), hir])
            
            rot = [rotation[3], rotation[0], rotation[1], rotation[2]]
            pos = [translation[0] , translation[1] , translation[2] ]
            
            # amt新建骨骼
            bone = amt.data.edit_bones.new("b")
            bone.length = 0.1
            # 给bone的matrix赋值
            bone.matrix =  mathutils.Matrix.Translation(pos) @ mathutils.Quaternion(rot).to_matrix().to_4x4()
            # print("mat",bone.matrix)

            self.bonesList.append(bone)
            boneInfos.append(boneInfo)
        # for bone in self.bonesList:
        #     print(bone.matrix)
        #     pass
        ##############
        for i in range(self.boneCount):
            self.reader.seek(self.namesOffs[i])
            self.bonesList[i].name = self.reader.readString()
            boneInfos[i]["name"] = self.bonesList[i].name
        #     bMap = {}
        #     bMap["name"] = self.bonesList[i].name
        #     bMap["trans"] = boneslist_file[i][0]
        #     bMap["rot"] = boneslist_file[i][1]
        #     bMap["scale"] = boneslist_file[i][2]
        #     bMap["parent"] = boneslist_file[i][3]
        #     boneslist_maps.append(bMap)
        ##############

        # printList = ["Hip", "Spine_0", "Spine_1"]
        # for i in range(self.boneCount):
        #     # if boneslist_maps[i]["name"] in printList:
        #     print(boneslist_maps[i]["name"])
        #     # print("\t",boneslist_maps[i]["trans"])
        #     # print("\t",boneslist_maps[i]["rot"])
        #     print("\t",boneslist_maps[i]["scale"])
            # print(self.bonesList[i].matrix)

        for i in range(self.boneCount):
            if self.hierarchy[i] != -1:
                # boneslist_maps[i]["parentName"] = boneslist_maps[boneslist_maps[i]["parent"]]["name"]
#                if i == 1:
#                    print(self.bonesList[i].parent.matrix)
#                    print(self.bonesList[i].matrix)
                self.bonesList[i].parent = self.bonesList[self.hierarchy[i]]
                newTransform = self.bonesList[i].parent.matrix @ self.bonesList[i].matrix
                self.bonesList[i].matrix = newTransform
            else:
                # boneslist_maps[i]["parentName"] = None
                pass

        # 打印boneslist_maps
        for i in range(self.boneCount):
#            print(boneslist_maps[i]["name"], boneslist_maps[i]["rot"], boneslist_maps[i]["trans"], boneslist_maps[i]["parentName"])
            pass
        # 切换到姿态模式
        bpy.ops.object.mode_set(mode='POSE')
        amt.pose.bones[0].scale = (100, 100, 100)
        bpy.ops.pose.armature_apply()
        # 切换到编辑模式
        bpy.ops.object.mode_set(mode='EDIT')
        amt.data.edit_bones.remove(amt.data.edit_bones[0])
        # 切换物体模式
        bpy.ops.object.mode_set(mode='OBJECT')
        amt.rotation_euler = (math.radians(90), 0, 0)
        amt.name = "root"
        amt.data.name = "root"
        # amt的scale改为0.01
        amt.scale = (0.01, 0.01, 0.01)

        # 打印boneInfos
        # 写入excel
        with open("D:\\blendert\\boneInfos.txt", "w") as f:
            for i in range(self.boneCount):
                # print(boneInfos[i]["name"])
                # 写入文件

                # print(boneInfos[i]["name"],
                #     "\t",boneInfos[i]["hash"].hex(),
                #     "\t",self.indices[i],
                #     "\t",boneInfos[i]["parent"],
                #     #   "\t",boneInfos[i]["translation"],
                #     #   "\t",boneInfos[i]["rotation"],
                #     #   "\t",boneInfos[i]["scale"]
                #     )
                
                row = boneInfos[i]["name"] + "\t" + boneInfos[i]["hash"].hex() + "\t" + str(self.indices[i]) + "\t" + str(boneInfos[i]["parent"]) + "\n"
                f.write(row)
            




classes = [
    ImportFbxskel,
    # DialogOperator
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)