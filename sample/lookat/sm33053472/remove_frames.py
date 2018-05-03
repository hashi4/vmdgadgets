import sys
sys.path.append('../../../vmdgadgets')
import vmdutil

CAMERA_IN = sys.argv[1]
CAMERA_OUT = sys.argv[2]
REMOVE_FRAMES = [2029,2030,2044,2045, 2091,2092,2108,2109, 2222,2223,2235,2236,2252,2253]

vmd = vmdutil.Vmdio()
vmd.load(CAMERA_IN)
c_frames = vmd.get_frames('cameras')
new_frames = list()
for frame in c_frames:
    if frame.frame not in REMOVE_FRAMES:
        new_frames.append(frame)
vmd.set_frames('cameras', new_frames)
vmd.store(CAMERA_OUT)
