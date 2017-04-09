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
        '--add_frames', nargs='*', default=None,
        metavar='frame_no',
        help='''Add light frames.''')
    return parser


_parser = _make_argumentparser()
__doc__ += _parser.format_help()


def camera_to_light(camera_frame, against=None, rx=0.0, ry=0.0, rgb=RGB):
    rx = math.radians(rx)
    ry = math.radians(ry)
    yaw_inverse = -1.0 if against and 'y' in against else 1.0
    pitch_inverse = -1.0 if against and 'x' in against else 1.0
    rotation = list(camera_frame.rotation)
    rotation[0] += rx
    rotation[1] += ry
    camera_direction = list(vmdutil.camera_direction(rotation))
    camera_direction[0] *= yaw_inverse
    camera_direction[2] *= yaw_inverse
    camera_direction[1] *= pitch_inverse
    return vmddef.light(
        camera_frame.frame, tuple(rgb), tuple(camera_direction))


def camlight(vmdin, against=None, rx=0.0, ry=0.0, rgb=RGB, add_frames=None):
    light_frames = []
    for camera_frame in vmdin.get_frames('cameras'):
        light_frames.append(
            camera_to_light(camera_frame, against, rx, ry, rgb))
    if add_frames is not None:
        camera_frames = vmdin.get_frames('cameras')
        camera_motion = vmdmotion.CameraTransformation(camera_frames)
        for frame_no in add_frames:
            frame_no = int(frame_no)
            if camera_motion.get_vmd_frame(frame_no) is None:
                rotation, position, distance, angle_of_view = (
                    camera_motion.get_vmd_transform(frame_no))
                camera_frame = vmddef.camera(
                    frame_no, distance, position, rotation, None, None, None)
                light_frames.append(
                    camera_to_light(camera_frame, against, rx, ry, rgb))
    out = vmdutil.Vmdio()
    out.header = vmddef.header(
        vmddef.HEADER1, vmddef.HEADER2_CAMERA)
    out.set_frames('lights', light_frames)
    return out


def camlight_fd(infile, outfile, against=None, rx=0.0, ry=0.0,
                rgb=RGB, add_frames=None):
    vmdin = vmdutil.Vmdio()
    vmdin.load_fd(infile)
    vmdout = camlight(vmdin, against, rx, ry, rgb, add_frames)
    vmdout.store_fd(outfile)


def camlight_fname(infile, outfile, against=None, rx=0.0, ry=0.0,
                   rgb=RGB, add_frames=None):
    vmdin = vmdutil.Vmdio()
    vmdin.load(infile)
    vmdout = camlight(vmdin, against, rx, ry, rgb, add_frames)
    vmdout.store(outfile)


if __name__ == '__main__':
    args = _parser.parse_args()
    camlight_fd(**vars(args))
