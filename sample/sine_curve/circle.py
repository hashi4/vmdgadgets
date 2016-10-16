import sys
sys.path.append('../../vmdgadgets')
import vmdutil
from vmdutil import vmddef


def replace_controlpoints(cp_all, cp, index):
    for i in range(4):
        cp_all[i][index] =cp[i]
    return cp_all


sine1 = vmdutil.SINE1_CONTROLPOINTS  #  sin,  [1x, 1y, 2x, 2y]
sine2 = vmdutil.SINE2_CONTROLPOINTS  #  1 - cos
cp_all = vmddef.BONE_LERP_CONTROLPOINTS  # [1x[X,Y,Z,R], 1y[],2x[],2y[]]
replace_controlpoints(cp_all, sine1, 2)  # Z: sin
replace_controlpoints(cp_all, sine2, 0)  # X: (1 - cos)
interpolation1 = vmddef.bone_controlpoints_to_vmdformat(cp_all)
cp_all = vmddef.BONE_LERP_CONTROLPOINTS
replace_controlpoints(cp_all, sine1, 0)  # X: sin
replace_controlpoints(cp_all, sine2, 2)  # Z: (1 - cos)
interpolation2 = vmddef.bone_controlpoints_to_vmdformat(cp_all)

bone = vmddef.BONE_SAMPLE

bone_frames = []
initial_frame = bone._replace(position=(30, 0, 0))
bone_frames.append(initial_frame)

# frame 30: X:sine2, Z:sine1, (0, 0, 30)
bone_frames.append(
    bone._replace(
    frame=30, position=(0, 0, 30), interpolation=interpolation1))
# frame 60: X:sine1, Z:sine2, (-30, 0, 0)
bone_frames.append(
    bone._replace(
    frame=60, position=(-30, 0, 0), interpolation=interpolation2))
# frame 90 X:sine2, Z:sine1, (0, 0, -30)
bone_frames.append(
    bone._replace(
    frame=90, position=(0, 0, -30), interpolation=interpolation1))
# frame 120 X:sine1, Z:sine2, (30, 0, 0)
bone_frames.append(
    bone._replace(
    frame=120, position=(30, 0, 0), interpolation=interpolation2))

vmdout = vmdutil.Vmdio()
vmdout.header = vmdout.header._replace(
    model_name='circle_sample'.encode(vmddef.ENCODING))
vmdout.set_frames('bones', bone_frames)
vmdout.store('circle.vmd')
