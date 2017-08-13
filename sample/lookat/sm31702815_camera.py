import sys
import math
sys.path.append('../../vmdgadgets')
import vmdutil
from vmdutil import vmddef

vmd = vmdutil.Vmdio()
vmd.header = vmddef.header(vmddef.HEADER1, vmddef.HEADER2_CAMERA)
cam_frame = vmddef.CAMERA_SAMPLE._replace(
    distance=0, position=(0, 10.5, -16), rotation=(math.radians(15.5), 0, 0),
    angle_of_view=30)
vmd.set_frames('cameras', [cam_frame])
vmd.store('suki_yuki_maji_magic_cam.vmd')
    
