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
        'cam_vmd',
        help='vmd filename of camera')
    parser.add_argument(
        'outfile',
        help='vmd filename to output')
    parser.add_argument(
        '--omega',
        help='''limit of angular velocity after camera's cut.
        Setting to 0 makes no limit. Default = 4.5 degrees/frame.''')
    parser.add_argument(
        '--ignore',
        help='''model ignores camera when relative angle is over this.
        If 0 model always tries to look camera. Default = 140 degrees.''')
    parser.add_argument(
        '--constraint', nargs=7, action='append',
        metavar=('bone_name', 'x', 'y', 'z', 'scale_x', 'sacle_y', 'scale_z'),
        help='''make constraint to bone rotation. xyz=degrees''')
    parser.add_argument(
        '--add_frames', nargs='*',
        metavar='frame_no',
        help='''Add frames to sync camera.''')
    parser.add_argument(
        '--frame_range', nargs=2, action='append',
        metavar=('from', 'to'),
        help='''set frame range to track, other frames use vmd motion.''')
    parser.add_argument(
        '--vmd_blend', nargs=2, action='append',
        metavar=('bone_name', 'blend_ratio'),
        help='''blend vmd motion to tracking motion.''')
    return parser


def trace_camera(args):
    l = lookat.LookAt(args.from_pmx, args.from_vmd)
    l.set_target_vmd(args.cam_vmd)
    if args.omega:
        omega = math.radians(float(args.omega))
        l.set_omega_limit(omega)
    if args.ignore:
        ignore = math.radians(float(args.ignore))
        l.set_ignore_zone(ignore)
    if args.constraint:
        for con in args.constraint:
            name = con[0]
            rot = tuple([float(x) for x in con[1:4]])
            scale = tuple([float(x) for x in con[4:7]])
            l.set_constraint(name, [rot, scale])
    if args.add_frames:
        frame_nos = [int(frame_no) for frame_no in args.add_frames]
        l.set_additional_frames(frame_nos)
    if args.frame_range:
        frame_ranges = []
        for frange in args.frame_range:
            frame_ranges.append((int(frange[0]), int(frange[1])))
        l.set_frame_ranges(frame_ranges)
    if args.vmd_blend:
        for blend in args.vmd_blend:
            l.set_vmd_blend_ratio(blend[0], float(blend[1]))
    heading_frames = l.look_at()
    vmdout = vmdutil.Vmdio()
    vmdout.set_frames('bones', heading_frames)
    vmdout.store(args.outfile)
    return


_parser = _make_argumentparser()
if __name__ == '__main__':
    args = _parser.parse_args()
    trace_camera(args)
