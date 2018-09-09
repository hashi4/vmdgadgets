import sys
sys.path.append('../../../vmdgadgets')
import vmdutil

OFFSET = 5
#RANGE = [(1, 3127), (3467, 6978)]
RANGE = [(1, 3100), (3467, 6978)]
def in_range(frame, offset=0):
    for r in RANGE:
        if r[0] <= frame <= (r[1] + offset):
            return True
    else:
        return False


if '__main__' == __name__ :
    vmdin = vmdutil.Vmdio()
    vmdin.load(sys.argv[1])
    bones = vmdin.get_frames('bones')
    for i in range(3):
        offset = (i + 1) * OFFSET
        output = list()
        for bone_frame in bones:
            if in_range(bone_frame.frame, offset):
                output.append(bone_frame._replace(frame=bone_frame.frame + offset))
            else:
                output.append(bone_frame)
        vmdin.set_frames('bones', output)
        vmdin.store('plus_{}.vmd'.format(offset))
