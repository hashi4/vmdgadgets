import argparse
import vmdutil
import lookat

import trace_camera


def _make_argumentparser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'from_pmx',
        help='pmx filename of model')
    parser.add_argument(
        'from_vmd',
        help='vmd filename of model')
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
    parser = trace_camera.make_common_arguments(parser)
    return parser


def trace_model(args):
    l = lookat.LookAt(args.from_pmx, args.from_vmd)
    l.set_target_pmx(args.to_pmx)
    l.set_target_vmd(args.to_vmd)
    if args.target_bone:
        target_bone = args.target_bone
        l.set_target_bone(target_bone)
    trace_camera.set_common_options(args, l)
    heading_frames = l.look_at()
    vmdout = vmdutil.Vmdio()
    vmdout.set_frames('bones', heading_frames)
    vmdout.store(args.outfile)
    return


_parser = _make_argumentparser()
if __name__ == '__main__':
    args = _parser.parse_args()
    trace_model(args)
