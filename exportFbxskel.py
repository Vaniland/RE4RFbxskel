import bpy
import ctypes
import mathutils
import struct
import os
import math
from bpy_extras.io_utils import ExportHelper

class Writer:
    def __init__(self, filePath, bDebug=False):
        self.filePath = filePath
        self.file = open(filePath, "wb")
        self.debugBuffer = []
        self.bDebug = bDebug

    def seek(self, offset, whence=0):
        self.file.seek(offset,whence)

    def tell(self):
        return self.file.tell()
    
    def close(self):
        self.file.close()
    
    def debugPrint(self):
        print("DEBUGPrintP",len(self.debugBuffer))
        print("bDebug ",self.bDebug)
            # 打印16进制 16个一行 不要显示0x，每个16进制数占两位
        for i in range(len(self.debugBuffer)):
            print(f"{self.debugBuffer[i]:02X}", end=" ")
            if i % 16 == 15:
                print()
        print()

    def writeBytes(self, bytes):
        self.file.write(bytes)
        if self.bDebug:
            # 一个一个字节写入
            for i in range(len(bytes)):
                self.debugBuffer.append(bytes[i])
    
    def writeByte(self, byte):
        self.file.write(struct.pack("<B", byte))
        if self.bDebug:
            self.debugBuffer.append(struct.pack("<B", byte))

    def writeString(self, str):
        for c in str:
            self.writeShort(ord(c))
        self.writeShort(0)

    def writeUnicodeString(self, input):
        for char in input:
            # self.file.write(bytes([ord(char)]))  # Write the Unicode character as its byte representation
            # self.file.write(bytes([0]))  # Write a null byte after each character
            self.writeByte(ord(char))
            self.writeByte(0)
        # self.file.write(bytes([0, 0]))  # Write a null terminator as a short (2 bytes)
        self.writeShort(0)
        
    
    def writeInt(self, int):
        self.writeBytes(struct.pack("<i", int))

    def writeInt64(self, int64):
        self.writeBytes(struct.pack("<q", int64))

    def writeUInt(self, uint):
        self.writeBytes(struct.pack("<I", uint))
    
    def writeUInt64(self, uint64):
        self.writeBytes(struct.pack("<Q", uint64))
    
    def writeUShort(self, ushort):
        self.writeBytes(struct.pack("<H", ushort))
    
    def writeFloat(self, float):
        self.writeBytes(struct.pack("<f", float))
    
    def writeNormalizedByte(self, byte):
        self.writeByte(int(byte * 255))
    
    def writeShort(self, short):
        self.writeBytes(struct.pack("<h", short))
    
    def writeNormalizedShort(self, short):
        self.writeShort(int(short * 65535))

    def padToNextLine(self):
        # while bstream.tell() % 16 != 0:
        #    bstream.write(bytes([0]))
        while self.file.tell() % 16 != 0:
            self.writeByte(0)

def generate_hash(key, is_wstring=False, seed=0xFFFFFFFF):
    
    def fmix(h, seed=0xFFFFFFFF):
        h ^= h >> 16
        h = ctypes.c_uint32(h * 0x85ebca6b).value & ctypes.c_uint32(seed).value
        h ^= h >> 13
        h = ctypes.c_uint32(h * 0xc2b2ae35).value & ctypes.c_uint32(seed).value
        h ^= h >> 16
        return h

    new_key = []
    for char in key:
        new_key.append(ctypes.c_uint64(ord(char)))
        if is_wstring != 0:
            new_key.append(ctypes.c_uint64(0))
    
    key = new_key
    length = ctypes.c_uint64(len(key))
    n_blocks = length.value // 4
    h1 = seed
    c1 = 0xcc9e2d51
    c2 = 0x1b873593
    
    for block_start in range(0, n_blocks * 4, 4):
        k1 = ctypes.c_uint32((((key[block_start + 3]).value << 24) | 
                              ((key[block_start + 2]).value << 16) | 
                              ((key[block_start + 1]).value << 8) | 
                              (key[block_start]).value)).value
        k1 = ctypes.c_uint32((c1 * k1) & seed).value
        k1 = ctypes.c_uint32(((k1 << 15) | (k1 >> 17)) & seed).value
        k1 = ctypes.c_uint32((c2 * k1) & seed).value
        h1 ^= k1
        h1 = ctypes.c_uint32(((h1 << 13) | (h1 >> 19)) & seed).value
        h1 = ctypes.c_uint32((h1 * 5 + 0xe6546b64) & seed).value

    tail_index = n_blocks * 4
    k1 = 0
    tail_size = length.value % 4
    if tail_size >= 3:
        k1 ^= (key[tail_index + 2]).value << 16
    if tail_size >= 2:
        k1 ^= (key[tail_index + 1]).value << 8
    if tail_size >= 1:
        k1 ^= (key[tail_index]).value
    if tail_size > 0:
        k1 = ctypes.c_uint32((k1 * c1) & seed).value
        k1 = ctypes.c_uint32(((k1 << 15) | (k1 >> 17)) & seed).value
        k1 = ctypes.c_uint32((k1 * c2) & seed).value
        h1 ^= k1

    unsigned_val = fmix(h1 ^ length.value)
    
    if unsigned_val & 0x80000000 == 0:
        return unsigned_val
    else:
        return -((unsigned_val ^ seed) + 1)

class ExportFbxskel(bpy.types.Operator, ExportHelper):
    bl_idname = "export.fbxskel"
    bl_label = "Export Fbxskel"
    bl_description = "Export Fbxskel"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ""

    # 筛选出*.fbxskel.* 和 *.skeleton.*文件
    filter_glob: bpy.props.StringProperty(
        default="*.fbxskel.*;*.skeleton.*",
        options={'HIDDEN'}
        )
    
    files: bpy.props.CollectionProperty(
        name="File Path", 
        type=bpy.types.OperatorFileListElement)
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "export_fbxskel_armature")

    def execute(self, context):
        bones = []
        bCheckMeshAsSource = True
        # amt是名为Armature的物体
        amt = context.scene.export_fbxskel_armature
        if amt is None:
            # 提示消息请选择一个Armature 返回CANCELLED
            self.report({'ERROR'}, "请选择一个骨骼")
            return {'CANCELLED'}
        # 检查amt名字前四个是否是root
        if not amt.name[:4] == "root":
            self.report({'ERROR'}, "Armature名称必须以root开头")
            return {'CANCELLED'}
        
        # 保证amt的缩放为0.01,欧拉旋转x为90度，否则报错
        if not amt.scale == mathutils.Vector((0.01, 0.01, 0.01)) and not amt.rotation_euler[0] == math.pi / 2:
            self.report({'ERROR'}, "Armature缩放必须为0.01，旋转x为90度")
            return {'CANCELLED'}

        amt_copy = amt.copy()
        amt_copy.data = amt.data.copy()
        # link到scene
        bpy.context.scene.collection.objects.link(amt_copy)
        # 切换到物体模式
        bpy.ops.object.mode_set(mode='OBJECT')
        # 如果amt_copy旋转为90度,则旋转-90度
        # 用函数math.pi/2代替90度
        if amt_copy.rotation_euler[0] == math.pi / 2:
            amt_copy.rotation_euler[0] = 0

        # 切换到姿态模式，应用当前姿态
        # deselect
        bpy.ops.object.select_all(action='DESELECT')
        amt_copy.select_set(True)
        bpy.context.view_layer.objects.active = amt_copy

        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.armature_apply()

        # 切换到编辑模式
        bpy.ops.object.mode_set(mode='EDIT')

        exportPath = self.filepath
        exportName = os.path.basename(exportPath)
        exportDir = os.path.dirname(exportPath)
        # 找寻exportDir下所有名为exportName的文件
        cnt = 0
        for file in os.listdir(exportDir):
            if exportName in file:
                exportPath = os.path.join(exportDir, file)
                cnt += 1
        if cnt > 1:
            self.report({'ERROR'}, "找到多个同前缀fbxskel文件，请只保留一个")
            return {'CANCELLED'}

        print(exportPath)
        # 检查文件是否存在
        if not os.path.exists(exportPath):
            # 提示exportPath不存在
            self.report({'ERROR'}, f"文件'{exportPath}'不存在")
            return {'CANCELLED'}
        # 取文件名
        fileName = os.path.basename(exportPath)
        version = fileName.split(".")[-1]
        version = int(version)
        # 打开文件
        writer = Writer(exportPath, True)
        # Header
        writer.writeUInt(int(version))
        writer.writeUInt(1852599155)
        writer.writeUInt64(0)
        writer.writeUInt64(48)
        writer.writeUInt64(0)
        # bonecount blender里面root要注意?
        export_bone_count = len(amt_copy.data.bones) + 1
        print("export_bone_count", export_bone_count)
        writer.writeUInt64(export_bone_count)
        writer.writeUInt64(0)

        # bones
        namesArr = []
        namesArrWithBoneNumbers = []
        namesArr.append("root")
        namesArrWithBoneNumbers.append("root")
        for i in range(len(amt_copy.data.edit_bones)):
            namesArrWithBoneNumbers.append(amt_copy.data.edit_bones[i].name)

        for i in range(len(amt_copy.data.edit_bones) + 1):
            if i == 0:
                subBoneName = "root"
                subBoneID = 0
                parentBoneID = -1
                # 矩阵无变换
                boneLocalMat = mathutils.Matrix()
            else:
                subBoneID = i
                parentBoneID = -1
                subBoneName = amt_copy.data.edit_bones[i - 1].name
                
                cur_subBoneNames = subBoneName.split(":")
                if len(cur_subBoneNames) > 1:
                    subBoneName = cur_subBoneNames[1]
                
                namesArr.append(subBoneName)
                
                boneLocalMat = amt_copy.data.edit_bones[i - 1].matrix
                # 有父骨骼的
                if amt_copy.data.edit_bones[i - 1].parent is not None:
                    # parentBoneName = amt_copy.data.bones[i].parent.name
                    # ps = parentBoneName.split(":")
                    # if len(ps) > 1:
                        # parentBoneName = ps[1]
                    parentBoneID = namesArrWithBoneNumbers.index(amt_copy.data.edit_bones[i - 1].parent.name)
                    pMat = amt_copy.data.edit_bones[i - 1].parent.matrix
                    boneLocalMat = pMat.inverted() @ boneLocalMat

                # blender里面设置root
                if amt_copy.data.edit_bones[i - 1].parent is None:
                    parentBoneID = 0
                    # if bCheckMeshAsSource is True:
            if subBoneID != -1:
                # 8 + 4 + 2 + 2 = 16字节信息
                # namestr地址指针
                writer.writeInt64(0)
                # hash
                writer.writeInt(generate_hash(subBoneName, True))
                # 这里面写入8字节的父级骨骼ID
                writer.writeShort(parentBoneID)
                if i == 0:
                    # writer.debugPrint()
                    pass
                symmetryID = subBoneID
                if "eapon" in subBoneName:
                    symmetryID = -1

                # 取前两个字符判断前缀
                prefix = subBoneName[0:2]
                oppositePrefix = None

                if prefix == "R_": oppositePrefix = "L_"
                elif prefix == "r_": oppositePrefix = "l_"
                elif prefix == "L_" : oppositePrefix = "R_"
                elif prefix == "l_" : oppositePrefix = "r_"
                if oppositePrefix is not None:
                    # 替换prefix
                    oppositeBoneName  = subBoneName.replace(prefix, oppositePrefix)
                    for j in range(len(amt_copy.data.edit_bones)):
                        filteredBnNames = namesArrWithBoneNumbers[j + 1].split(":")
                        if filteredBnNames[-1] == oppositeBoneName:
                            print(f"Symmetry bone '{amt_copy.data.edit_bones[j].name}' found for bone '{oppositeBoneName}'")
                            symmetryID = j + 1
                            break
                # 对称骨骼ID
                writer.writeShort(symmetryID)

                rot_quaternion = boneLocalMat.to_quaternion()
                location = boneLocalMat.to_translation()
                scale = boneLocalMat.to_scale()
                # 12 * 4 = 48字节数据
                if version == 5:
                    writer.writeFloat(rot_quaternion.x)
                    writer.writeFloat(rot_quaternion.y)
                    writer.writeFloat(rot_quaternion.z)
                    writer.writeFloat(rot_quaternion.w)
                    writer.writeFloat(location.x / 100)
                    writer.writeFloat(location.y / 100)
                    writer.writeFloat(location.z / 100)
                    writer.writeFloat(1)
                else:
                    writer.writeFloat(location.x / 100)
                    writer.writeFloat(location.y / 100)
                    writer.writeFloat(location.z / 100)
                    writer.writeFloat(0)
                    writer.writeFloat(rot_quaternion.x)
                    writer.writeFloat(rot_quaternion.y)
                    writer.writeFloat(rot_quaternion.z)
                    writer.writeFloat(rot_quaternion.w)
                        
                # writer.writeFloat(boneLocalMat.scale.x)
                # writer.writeFloat(boneLocalMat.scale.y)
                writer.writeFloat(1)
                writer.writeFloat(1)
                if version == 5:
                    writer.writeFloat(0)
                else:
                    # writer.writeFloat(boneLocalMat.scale.z)
                    writer.writeFloat(1)
                writer.writeFloat(0)

            # end of if subBoneID != -1
        # end of for i in range(len(amt_copy.data.bones))

        writer.padToNextLine()

        hashesOffset = writer.tell()
        indexArr = [i for i in range(len(amt_copy.data.edit_bones) + 1)]
        hashArr = []

        # print(namesArr)
        for i in range(len(namesArr)):
            # as integer?
            hash = ctypes.c_int32(generate_hash(namesArr[i], True))
            hash = hash.value
            if hash < 0:
                hash = ctypes.c_uint64(1 + 0xFFFFFFFF + ctypes.c_int64(hash).value).value
            hashArr.append(ctypes.c_int64(hash).value)

        indexArr = sorted(indexArr, key=lambda x: hashArr[x])
        # print(len(namesArr))
        # print(len(hashArr))
        for i in range(len(indexArr)):
            # print(i)
            # print(hashArr[indexArr[i]])
            writer.writeInt(ctypes.c_int32(hashArr[indexArr[i]]).value)
            writer.writeInt(indexArr[i])

        writer.padToNextLine()
        
        strOffsArr = []
        for i in range(len(namesArr)):
            strOffsArr.append(writer.tell())
            writer.writeUnicodeString(namesArr[i])

        writer.seek(48)
        for i in range(len(strOffsArr)):
            writer.writeInt64(strOffsArr[i])
            writer.seek(56, 1)

        

        writer.seek(24)
        writer.writeInt64(hashesOffset)

        # 删除amt_copy
        bpy.data.objects.remove(amt_copy)
        return {'FINISHED'}

classes = [
    ExportFbxskel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # pointerproperty,armature
    bpy.types.Scene.export_fbxskel_armature = bpy.props.PointerProperty(type=bpy.types.Object, name="Armature", description="Armature to export", poll=lambda self, obj: obj.type == 'ARMATURE')


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.export_fbxskel_armature