'''Change forward steps to back steps.

'''
import sys
import math
import argparse

import vmdutil


def _make_argumentparser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'infile', nargs='?', type=argparse.FileType('rb'),
        default=sys.stdin.buffer,
        help='vmd file to change steps. default=stdin')
    parser.add_argument(
        'outfile', nargs='?', type=argparse.FileType('wb'),
        default=sys.stdout.buffer,
        help='output vmd file. default=stdout')
    return parser

_parser = _make_argumentparser()
__doc__ += _parser.format_help()

MOVE_BONES = ['センター', '右足ＩＫ', '左足ＩＫ']


def replace_position(frames, diff):
    new_frames = []
    p = (0, 0, 0)
    for i, frame in enumerate(frames):
        p = vmdutil.add_v(p, (diff[i][0], diff[i][1], -diff[i][2]))
        new_frames.append(frame._replace(position=tuple(p)))
    return new_frames


def step_back(vmdin, kind='bones'):
    frames = vmdin.get_frames(kind)
    if kind == 'bones':
        frame_dict = vmdutil.frames_to_dict(frames)
        name_dict = vmdutil.make_name_dict(frame_dict, True)
        for name in MOVE_BONES:
            bone_frames = name_dict[name]
            init_frame = bone_frames[0]._replace(position=(0, 0, 0))
            diff = vmdutil.adjacent_difference(
                [init_frame] + bone_frames,
                lambda x1, x2: vmdutil.sub_v(x1.position, x2.position))
            new_frames = replace_position(bone_frames, diff)
            name_dict[name] = new_frames
        all_frames = list()
        for name in name_dict.keys():
            all_frames.extend(name_dict[name])
        vmdout = vmdin.copy()
        vmdout.set_frames('bones', all_frames)
        return vmdout
    else:
        return None


def step_back_fd(infile, outfile, kind='bones'):
    vmdin = vmdutil.Vmdio()
    vmdin.load_fd(infile)
    vmdout = step_back(vmdin, kind)
    vmdout.store_fd(outfile)


def step_back_fname(infile, outfile, kind='bones'):
    vmdin = vmdutil.Vmdio()
    vmdin.load(infile)
    vmdout = step_back(vmdin, kind)
    vmdout.store(outfile)


if __name__ == '__main__':
    args = _parser.parse_args()
    step_back_fd(**vars(args))
