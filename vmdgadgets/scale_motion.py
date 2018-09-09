'''scale position of bones, camera
'''

import sys
import argparse
import vmdutil

DEFAULT_TARGETS = ['センター', '右足ＩＫ', '左足ＩＫ']


def make_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        'infile', nargs='?', type=argparse.FileType('rb'),
        default=sys.stdin.buffer,
        help='bone or camera motion. default=stdin')
    parser.add_argument(
        'outfile', nargs='?', type=argparse.FileType('wb'),
        default=sys.stdout.buffer,
        help='scaled motion. default=stdout')
    parser.add_argument(
        '-s', '--scale', nargs='+', type=float,
        help='--scale p q r => x *= p, y *= q, z *= r\n' +
             '--scale t => x *= t, y *= t, z *= t')
    parser.add_argument(
        '--lr', nargs='?', const='both', default='both')
    parser.add_argument(
        '-b', '--bones', nargs='+',
        help='bone names, default=センター, 右足ＩＫ, 左足ＩＫ')
    return parser


def get_scale(args, is_camera):
    if not args.scale:
        return (1.0, 1.0, 1.0)
    n_args = len(args.scale)
    if n_args != 1 and n_args != 3:
        raise('invalid scale option')
    if 1 == n_args:
        return tuple([args.scale[0]] * 3)
    else:
        return (args.scale[0], args.scale[1], args.scale[2])


def scale_pos(frame, scale, lr='both'):
    def s():
        return tuple([i * j for i, j in zip(frame.position, scale)])

    if 'both' == lr:
        return s()
    elif 'l' == lr:
        return s() if frame.position[0] > 0 else frame.position
    elif 'r' == lr:
        return s() if frame.position[0] < 0 else frame.position
    else:
        return frame.position


def scale_bone(vmdin, args):
    scale = get_scale(args, False)
    bone_frames = vmdin.get_frames('bones')
    nd = vmdutil.make_name_dict(vmdutil.frames_to_dict(bone_frames), True)
    out_frames = list()
    if args.bones:
        targets = args.bones
    else:
        targets = DEFAULT_TARGETS

    for key in nd:
        if key in targets:
            for frame in nd[key]:
                pos = scale_pos(frame, scale, args.lr)
                out_frames.append(frame._replace(position=pos))
        else:
            out_frames.extend(nd[key])

    vmdin.set_frames('bones', out_frames)
    return vmdin


def scale_camera(vmdin, args):
    scale = get_scale(args, True)
    cam_frames = vmdin.get_frames('cameras')
    out_frames = list()

    for frame in cam_frames:
        pos = scale_pos(frame, scale, args.lr)
        out_frames.append(frame._replace(position=pos))

    vmdin.set_frames('cameras', out_frames)
    return vmdin


def scale_motion(args):
    vmdin = vmdutil.Vmdio()
    vmdin.load_fd(args.infile)
    is_camera = vmdutil.is_camera_header(vmdin.header)
    vmdo = vmdutil.Vmdio()
    if is_camera:
        vmdo = scale_camera(vmdin, args)
    else:
        vmdo = scale_bone(vmdin, args)
    vmdo.store_fd(args.outfile)


if '__main__' == __name__:
    parser = make_parser()
    args = parser.parse_args()
    scale_motion(args)
