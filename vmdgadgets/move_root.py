import sys
import math
import argparse

import vmdutil
from vmdutil import vmddef


def make_argumentparser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'infile', nargs='?',
        type=argparse.FileType('rb'),
        default=sys.stdin.buffer,
        help='original motion')
    parser.add_argument(
        'outfile', nargs='?',
        type=argparse.FileType('wb'),
        default=sys.stdout.buffer,
        help='output')
    parser.add_argument(
        '--pos', nargs=3, type=float,
        help='position of 全ての親')
    parser.add_argument(
        '--angles', nargs=3, type=float,
        help='rotation of 全ての親 in euler angles')
    return parser

def move_root(args):
    if args.pos:
        position = tuple(args.pos)
    else:
        position = (0, 0, 0)
    if args.angles:
        angles = tuple(args.angles)
    else:
        angles = (0, 0, 0)
    if angles == (0, 0, 0) and position == (0, 0, 0):
        sys.stderr.write('do nothing.')
        return
    vmdin = vmdutil.Vmdio()
    vmdin.load_fd(args.infile)
    bones = vmdin.get_frames('bones')
    frame_dict = vmdutil.frames_to_dict(bones)
    name_dict = vmdutil.make_name_dict(frame_dict, True)
    parent_frames = name_dict.get('全ての親')
    new_frames = []
    if parent_frames:
        for frame in parent_frames:
            rotation = vmdutil.euler_to_quaternion(
                tuple([math.radians(r) for r in angles]))
            rotation = vmdutil.multiply_quaternion(frame.rotation, rotation)
            frame = frame._replace(
                position=tuple(vmdutil.add_v(frame.position, position)),
                rotation=tuple(rotation))
            new_frames.append(frame)
    else:
        rotation = vmdutil.euler_to_quaternion(
            tuple([math.radians(r) for r in angles]))
        new_frames.append(vmddef.BONE_SAMPLE._replace(
            position=position, rotation=rotation))
    for key in name_dict:
        if key != '全ての親':
            new_frames.extend(name_dict[key])
    vmdin.set_frames('bones', new_frames)
    vmdin.store_fd(args.outfile)

if __name__ == '__main__':
    parser = make_argumentparser()
    args = parser.parse_args()
    move_root(args)
