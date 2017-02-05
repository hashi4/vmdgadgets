import sys
import argparse
import math
import vmdutil
import lookat


def _make_argumentparser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'from_pmx',
        help='pmx filename of model')
    parser.add_argument(
        'from_vmd',
        help='vmd filename of model'),
    parser.add_argument(
        'to_pmx',
        help='pmx filename of target')
    parser.add_argument(
        'to_vmd',
        help='vmd filename of target')
    parser.add_argument(
        'outfile',
        help='vmd filename to output')
    parser.add_argument(
        '--target_bone',
        help='''bone_name to look at.
        Default=両目(it changes y, z position of 両目to 右目's value)''')
    parser.add_argument(
        '--ignore',
        help='''model ignores target when relative angle is over this.
        If 0 model always tries to look camera. Default = 140 degrees.''')
    parser.add_argument(
        '--constraint', nargs=7, action='append',
        metavar=('bone_name', 'x', 'y', 'z', 'scale_x', 'sacle_y', 'scale_z'),
        help='''make constraint to bone rotation xyz=degrees''')
    parser.add_argument(
        '--add_frames', nargs='*',
        metavar='frame_no',
        help='''Add frames to sync target.''')
    return parser


def trace_camera(args):
    l = lookat.LookAt(args.from_pmx, args.from_vmd)
    l.set_target_pmx(args.to_pmx)
    l.set_target_vmd(args.to_vmd)
    if args.ignore:
        ignore = math.radians(float(args.ignore))
        l.set_ignore_zone(ignore)
    if args.target_bone:
        target_bone = args.target_bone
        l.set_target_bone(target_bone)
    if args.constraint:
        for con in args.constraint:
            name = con[0]
            rot = tuple([float(x) for x in con[1:4]])
            scale = tuple([float(x) for x in con[4:7]])
            l.set_constraint(name, [rot, scale])
    if args.add_frames:
        frame_nos = [int(frame_no) for frame_no in args.add_frames]
        l.set_additional_frames(frame_nos)
    heading_frames = l.look_at()
    vmdout = vmdutil.Vmdio()
    vmdout.set_frames('bones', heading_frames)
    vmdout.store(args.outfile)
    return


_parser = _make_argumentparser()
if __name__ == '__main__':
    args = _parser.parse_args()
    trace_camera(args)
