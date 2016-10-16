import sys
sys.path.append('../../vmdgadgets')
import vmdutil
from vmdutil import vmddef

CENTER='センター'.encode(vmddef.ENCODING)

def replace_controlpoints(cp_all, cp, index):
    for i in range(4):
        cp_all[i][index] =cp[i]
    return cp_all


para1 = vmdutil.PARABOLA1_CONTROLPOINTS 
para2 = vmdutil.PARABOLA2_CONTROLPOINTS

cp_all = vmddef.BONE_LERP_CONTROLPOINTS
replace_controlpoints(cp_all, para1, 1)
interpolation1 = vmddef.bone_controlpoints_to_vmdformat(cp_all)

cp_all = vmddef.BONE_LERP_CONTROLPOINTS
replace_controlpoints(cp_all, para2, 1)
interpolation2 = vmddef.bone_controlpoints_to_vmdformat(cp_all)

bone = vmddef.BONE_SAMPLE

bone_frames = []
initial_frame = bone._replace(name=CENTER)
bone_frames.append(initial_frame)

# frame 20: center: (0,-3,0)
bone_frames.append(
    bone._replace(
    name=CENTER, frame=20, position=(0, -3, 0)))
# farme 35: center: (0, 30, 0) parabola2
bone_frames.append(
    bone._replace(name=CENTER, frame=35,
    position=(0, 30, 0), interpolation=interpolation2))
# frame 50: center: (0, -3, 0), parabola1
bone_frames.append(
    bone._replace(name=CENTER, frame=50,
    position=(0, -3, 0), interpolation=interpolation1))
# fame 70: center(0, 0, 0)
bone_frames.append(
    bone._replace(name=CENTER, frame=70, position=(0, 0, 0)))



vmdout = vmdutil.Vmdio()
vmdout.header = vmdout.header._replace(
    model_name='parabola_sample'.encode(vmddef.ENCODING))
vmdout.set_frames('bones', bone_frames)
vmdout.store('parabola.vmd')
