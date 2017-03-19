import sys
sys.path.append('../../vmdgadgets')
from vmdutil import vmddef
from vmdutil import pmxutil

MODEL_NAME=r'model\ゴリマ式_ビスマルクdrei v1.01.pmx'
REPLACE_FROM = '左右上下'
REPLAT_TO = 'PSUL' # port steer upper lower
VMD_NAME_LENGTH = 15
VMDOUT = r'model\bismark_renamed.pmx'

trans = str.maketrans(REPLACE_FROM, REPLAT_TO)
pmx = pmxutil.Pmxio()
pmx.load(MODEL_NAME)
bones = pmx.get_elements('bones')
new_bones = []
for bone in bones:
    b = bone.name_jp.encode(vmddef.ENCODING)
    if len(b) > VMD_NAME_LENGTH:
        new_name = bone.name_jp.translate(trans)
        assert len(new_name) <= VMD_NAME_LENGTH
        new_bone = bone._replace(name_jp=new_name)
        new_bones.append(new_bone)
    else:
        new_bones.append(bone)
pmx.set_elements('bones', new_bones)
pmx.store(VMDOUT)
