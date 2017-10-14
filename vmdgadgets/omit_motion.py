'''Remove key frames of specified bone or morph'''

import sys
import argparse
import vmdutil
from vmdutil import vmddef

def _make_argumentparser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'infile', nargs='?', type=argparse.FileType('rb'),
        default=sys.stdin.buffer,
        help='input')
    parser.add_argument(
        'outfile', nargs='?', type=argparse.FileType('wb'),
        default=sys.stdout.buffer,
        help='output')
    parser.add_argument(
        '-b', '--bone', action='append',
        metavar=('bone_name'), help='''bone name to be removed''')
    parser.add_argument(
        '-m', '--morph', action='append',
        metavar=('morph_name'), help='''morph name to be removed''')
    parser.add_argument(
        '-i', '--inverse', action='store_true',
        help=('dispose all motion except for specified'))
    return parser

def remove_frames_by_name(frames, names, inverse=False):
    if names is None or len(names) == 0:
        if inverse:
            return []
        else:
            return frames
    new_frames = list()
    names = set([vmdutil.str_to_b(name) for name in names])
    for frame in frames:
        if not inverse and frame.name not in names:
            new_frames.append(frame)
        elif inverse and frame.name in names:
            new_frames.append(frame)
    return new_frames


def remove_motion(args):
    vmd = vmdutil.Vmdio()
    vmd.load_fd(args.infile)
    args.infile.close()
    t = [args.bone, args.morph, [], [], [], []]
    for i, n in enumerate(t):
        e = vmddef.VMD_ELEMENTS[i]
        vmd.set_frames(
            e, remove_frames_by_name(vmd.get_frames(e), n, args.inverse))
    vmd.store_fd(args.outfile)
    return

_parser = _make_argumentparser()
if __name__ == '__main__':
    args = _parser.parse_args()
    remove_motion(args)
