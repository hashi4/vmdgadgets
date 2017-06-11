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
        '--eyes_only', action='store_true', default=False,
        help='makes eyes motions only.')
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
        '--vmd_blend', nargs=4, action='append',
        metavar=('bone_name', 'blend_ratio_x', 'y', 'z'),
        help='''blend vmd motion to tracking motion.''')
    parser.add_argument(
        '--forward_dir', nargs=4, action='append',
        metavar=('bone_name', 'x', 'y', 'z'),
        help='''set forward direction, default=(0, 0, -1)''')
    parser.add_argument(
        '--pitch_trim', nargs=2, action='append',
        help='''set up(+)/down(-) trim angle in degrees''')
    parser.add_argument(
        '--up_blend_weight', nargs=2, action='append',
        help='''multiply this weight when x axis of vmd_blend < 0.''')
    parser.add_argument(
        '--near', action='store_true', default=False,
        help='''adjust look-at point of neck and head according to the
                 distance to the eyes''')
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
            l.set_vmd_blend_ratio(
                blend[0], (float(blend[1]), float(blend[2]), float(blend[3])))
    if args.eyes_only:
        l.set_overwrite_bones(['両目'])
    if args.forward_dir:
        for forward in args.forward_dir:
            bone_name = forward[0]
            direction = [float(n) for n in forward[1:]]
            l.set_forward_dir(bone_name, direction)
    if args.pitch_trim:
        for trim in args.pitch_trim:
            bone_name = trim[0]
            h = math.tan(math.radians(float(trim[1])))
            direction = (0, -h, -1)
            l.set_forward_dir(bone_name, direction)
    if args.up_blend_weight:
        for weight in args.up_blend_weight:
            bone_name = weight[0]
            val = float(weight[1])
            l.set_up_blend_weight(bone_name, val)
    if args.near:
        l.set_near_mode(True)
    heading_frames = l.look_at()
    vmdout = vmdutil.Vmdio()
    vmdout.set_frames('bones', heading_frames)
    vmdout.store(args.outfile)
    return


_parser = _make_argumentparser()
if __name__ == '__main__':
    args = _parser.parse_args()
    trace_camera(args)
