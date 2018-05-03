import sys
sys.path.append('../../../vmdgadgets')
import vmdutil

def search_cut(cframes):
    sorted_keyframes = [f.frame for f in sorted(cframes, key=lambda f: f.frame)]
    result = list()
    for index, key_frame in enumerate(sorted_keyframes[:-1]):
        if sorted_keyframes[index + 1] == key_frame + 1:
            result.append(key_frame + 1)
    return result


def cut_motion(sorted_motion, cut_frames, cut_len):
    cut_set = set()
    for c_frame in cut_frames:
        for i in range(cut_len):
            cut_set.add(c_frame + i)
    new_frames = list()
    for frame in sorted_motion:
        if not frame.frame in cut_set:
            new_frames.append(frame)
    return new_frames

if '__main__' == __name__:
    head_f = sys.argv[1] # neck head eyes motion
    cam_f = sys.argv[2] # camera motion
    head_out = sys.argv[3] # output
    camera = vmdutil.Vmdio()
    camera.load(cam_f)
    motion = vmdutil.Vmdio()
    motion.load(head_f)
    cut_frames = search_cut(camera.get_frames('cameras'))
    name_dict = vmdutil.make_name_dict(
        vmdutil.frames_to_dict(motion.get_frames('bones')), True)
    head_motion = name_dict['頭']
    head_motion = cut_motion(head_motion, cut_frames, 3)
    head_motion.extend(name_dict['両目'])
    head_motion.extend(name_dict['首'])
    vmdout = vmdutil.Vmdio()
    vmdout.set_frames('bones', head_motion)
    vmdout.store(head_out)
