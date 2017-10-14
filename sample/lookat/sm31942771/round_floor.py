import sys
import math
sys.path.append('../../../vmdgadgets')
import vmdutil
from vmdutil import vmddef


def rotate_root(frame_no, interval, dir=True):
    bone = vmddef.BONE_SAMPLE
    bone = bone._replace(name='センター'.encode('shift-jis'))
    bone_frames = []
    d = 1 if dir else -1
    for i in range(4):
        y = i * math.pi / 2 
        e = (0, -y * d, 0)
        rotation = vmdutil.euler_to_quaternion(e)
        bone_frames.append(
            bone._replace(
                frame=frame_no, rotation=rotation))
        frame_no += interval
    return bone_frames


if __name__ == '__main__':
    # left
    #interval =113
    #interval =120 
    #interval =133
    interval = 161
    #interval =280


    # right
    #interval = 123
    #interval = 147
    #interval = 181

    #frames = 4432
    #frames = 4508 
    frames = 3864
    rounds = frames // (interval*4) + 1
    bone_frames = []
    for i in range(rounds):
        frame = i * interval * 4
        c = rotate_root(frame, interval, False)
        for f in c:
            if f.frame <= frames:
                bone_frames.append(f)
            else:
                break
    vmdout = vmdutil.Vmdio()
    vmdout.header = vmdout.header._replace(
        model_name='circle_sample'.encode(vmddef.ENCODING))
    vmdout.set_frames('bones', bone_frames)
    vmdout.store('stage.vmd')
