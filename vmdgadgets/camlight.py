'''
Make light frames those direction are equal to camera.

'''
import math
import sys
import argparse

from vmdutil import vmddef
import vmdutil
from vmdutil import vmdmotion

RGB = (0.602, 0.602, 0.602)


def _make_argumentparser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'infile', nargs='?', type=argparse.FileType('rb'),
        default=sys.stdin.buffer,
        help='camera motion. default=stdin')
    parser.add_argument(
        'outfile', nargs='?', type=argparse.FileType('wb'),
        default=sys.stdout.buffer,
        help='light motion. default=stdout')
    parser.add_argument(
        '--against', nargs='?', const='xy', metavar='xy',
        help='''make lights against to camera.
        by default it inverts around Y and X axis.
        you can add param \'x\' or \'y\' or \'xy\' to specify.''')
    parser.add_argument(
        '--rx', nargs='?', type=float, const=0.0, default=0.0,
        help='add bias to X axsis of camera(in degrees). default=0.0')
    parser.add_argument(
        '--ry', nargs='?', type=float, const=0.0, default=0.0,
        help='add bias to Y axsis of camera(in degrees). default=0.0')
    parser.add_argument(
        '--rgb', nargs=3, type=float, default=RGB,
        metavar=('R', 'G', 'B'), help='light color. default=0.602')
    parser.add_argument(
        '--y_only', action='store_true', default=False,
        help='Use only Y axis angle of camera direction. X axis is rx.')
    parser.add_argument(
        '--add_frames', nargs='*', default=None,
        metavar='frame_no',
        help='''Add light frames.''')
    parser.add_argument(
        '--auto_add_frames', nargs='?', type=float, const=90.0, default=None)
    return parser


_parser = _make_argumentparser()
__doc__ += _parser.format_help()


def camera_to_light(camera_frame, against=None, rx=0.0, ry=0.0,
                    rgb=RGB, y_only=False):
    rx = math.radians(rx)
    ry = math.radians(ry)
    yaw_inverse = -1.0 if against and 'y' in against else 1.0
    pitch_inverse = -1.0 if against and 'x' in against else 1.0
    rotation = list(camera_frame.rotation)
    if not y_only:
        rotation[0] += rx
    else:
        rotation[0] = rx
    rotation[1] += ry
    camera_direction = list(vmdutil.camera_direction(rotation))
    camera_direction[0] *= yaw_inverse
    camera_direction[2] *= yaw_inverse
    camera_direction[1] *= pitch_inverse
    return vmddef.light(
        camera_frame.frame, tuple(rgb), tuple(camera_direction))


def check_camera_rotation(camera_frames, threshold=math.pi * .5):
    sorted_frames = sorted(camera_frames, key=lambda f: f.frame)

    def op(x1, x2):
        return [abs(x1.rotation[i] - x2.rotation[i]) for i in range(2)]

    diffs = vmdutil.adjacent_difference(sorted_frames, op)
    diffs = [max(i[0], i[1]) for i in diffs]
    supply_frames = list()
    for index, diff in enumerate(diffs):
        if diff > threshold:
            n = int(diff * 2 // threshold)
            frame_diff = (
                sorted_frames[index + 1].frame - sorted_frames[index].frame)
            if frame_diff <= 1:
                continue
            while True:
                p = frame_diff // n
                if p > 0:
                    break
                else:
                    n -= 1
            for i in range(n - 1):
                supply_frames.append(
                    sorted_frames[index].frame + int(p) * (i + 1))
    if len(supply_frames) > 0:
        return supply_frames
    else:
        return None


def merge_list(a, b):
    if a is None or len(a) <= 0:
        return b
    if b is None or len(b) <= 0:
        return a
    return list(set(a).union(b))


def camlight(vmdin, against=None, rx=0.0, ry=0.0, rgb=RGB,
             y_only=False, add_frames=None, auto_add_frames=None):
    light_frames = []
    for camera_frame in vmdin.get_frames('cameras'):
        light_frames.append(
            camera_to_light(camera_frame, against, rx, ry, rgb, y_only))
    if auto_add_frames:
        a_frames = check_camera_rotation(
            vmdin.get_frames('cameras'), math.radians(auto_add_frames))
        add_frames = merge_list(add_frames, a_frames)
    if add_frames is not None:
        camera_frames = vmdin.get_frames('cameras')
        camera_motion = vmdmotion.VmdMotion(camera_frames)
        for frame_no in add_frames:
            frame_no = int(frame_no)
            if camera_motion.get_vmd_frame(frame_no) is None:
                rotation, position, distance, angle_of_view = (
                    camera_motion.get_vmd_transform(frame_no))
                camera_frame = vmddef.camera(
                    frame_no, distance, position, rotation, None, None, None)
                light_frames.append(
                    camera_to_light(
                        camera_frame, against, rx, ry, rgb, y_only))
    out = vmdutil.Vmdio()
    out.header = vmddef.header(
        vmddef.HEADER1, vmddef.HEADER2_CAMERA)
    out.set_frames('lights', light_frames)
    return out


def camlight_fd(infile, outfile, against=None, rx=0.0, ry=0.0,
                rgb=RGB, y_only=False, add_frames=None,
                auto_add_frames=False):
    vmdin = vmdutil.Vmdio()
    vmdin.load_fd(infile)
    vmdout = camlight(
        vmdin, against, rx, ry, rgb, y_only, add_frames, auto_add_frames)
    vmdout.store_fd(outfile)


def camlight_fname(infile, outfile, against=None, rx=0.0, ry=0.0,
                   rgb=RGB, y_only=False, add_frames=None,
                   auto_add_frames=False):
    vmdin = vmdutil.Vmdio()
    vmdin.load(infile)
    vmdout = camlight(
        vmdin, against, rx, ry, rgb, y_only, add_frames, auto_add_frames)
    vmdout.store(outfile)


if __name__ == '__main__':
    args = _parser.parse_args()
    camlight_fd(**vars(args))
