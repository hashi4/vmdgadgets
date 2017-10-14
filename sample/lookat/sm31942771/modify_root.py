import sys
import bisect
sys.path.append('../../../vmdgadgets')
import vmdutil

def get_index(frame_no, keys):
    index = bisect.bisect_left(keys, frame_no)
    if index <= len(keys) -1 and keys[index] == frame_no:
        return index, True
    else:
        return index - 1, False


def get_vmdtransformation(frame_no, key_frames, frames):
    vmd_index, b = get_index(frame_no, key_frames)
    if vmd_index < 0:
        return frames[0].rotation, frames[0].position
    else:
        begin = frames[vmd_index]
        if vmd_index < len(key_frames) - 1:
            end = frames[vmd_index + 1]
            position = vmdutil.interpolate_position(
                frame_no, begin, end, 'bones')
            rotation = vmdutil.interpolate_rotation(
                frame_no, begin, end, 'bones')
        else:
            position = begin.position
            rotation = begin.rotation
    return rotation, position


if __name__ == '__main__':
    vmd = vmdutil.Vmdio()
    if len(sys.argv) > 1:
        vmd.load(sys.argv[1])
    else:
        vmd.load_fd(sys.stdin.buffer)

    bones = vmd.get_frames('bones')
    frame_dict = vmdutil.frames_to_dict(bones)
    name_dict = vmdutil.make_name_dict(frame_dict, True)
    target_bones = {'センター', '右足ＩＫ', '左足ＩＫ'}
    root_frames = name_dict['全ての親']
    root_key_frames = [frame.frame for frame in root_frames]
    new_frames = []
    for move_bone in target_bones:
        for frame in name_dict[move_bone]:
            p_rot, p_pos = get_vmdtransformation(
                frame.frame, root_key_frames, root_frames)
            frame = frame._replace(position=tuple(vmdutil.add_v(
                frame.position, p_pos)))
            new_frames.append(frame)
    for bone_name in name_dict:
        if bone_name not in target_bones and bone_name != '全ての親':
            new_frames.extend(name_dict[bone_name])
    vmd.set_frames('bones', new_frames)
    if len(sys.argv) > 2:
        vmd.store(sys.argv[2])
    else:
        vmd.store_fd(sys.stdout.buffer)
