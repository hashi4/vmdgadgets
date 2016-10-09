'''Translate, scale and rotate vmd motion.

'''
import sys
import math
import functools
import argparse

import vmdutil

CENTER = 'センター'
CENTERS = [CENTER]
# CENTERS = ['上半身', '下半身']
LEFT = '左足ＩＫ'
RIGHT = '右足ＩＫ'

D = (0.875424, 0, 0)


def _make_argumentparser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'infile', nargs='?', type=argparse.FileType('rb'),
        default=sys.stdin.buffer,
        help='vmd file to transform. default=stdin')
    parser.add_argument(
        'outfile', nargs='?', type=argparse.FileType('wb'),
        default=sys.stdout.buffer,
        help='output vmd file. default=stdout')
    parser.add_argument(
        '--leftfoot', nargs=3, type=float, default=D,
        metavar=('x', 'y', 'z'),
        help='position of left foot. y is ignored. default={0}'.format(
            ', '.join([str(p) for p in D])))
    parser.add_argument(
        '--scale', nargs='?', type=float, const=1.0, default=1.0,
        help='scale steps. default=1.0')
    parser.add_argument(
        '--ry', nargs='?', type=float, const=0.0, default=0.0,
        help='degrees to turn motions around Y axis default=0.0')
    parser.add_argument(
        '--offset', nargs=3, type=float, default=(0.0, 0.0, 0.0),
        metavar=('x', 'y', 'z'), help='offset to translate, default=0,0,0')
    return parser

_parser = _make_argumentparser()
__doc__ += _parser.format_help()


def move_feetIK(target_frame, name_dict, leftfoot, isR, rad=0,
                scale=1.0, offset=(0, 0, 0)):
    b = -1.0 if isR else 1.0
    offset = (offset[0], offset[2])
    fpos = (b * leftfoot[0], leftfoot[2])
    tpos = (target_frame.position[0], target_frame.position[2])
    operations = (
        fpos,
        (vmdutil.add_v, tpos), (vmdutil.rotate_v2, rad),
        (vmdutil.scale_v, scale), (vmdutil.add_v, offset),
        (vmdutil.sub_v, fpos)
    )
    tpos = functools.reduce(lambda x, y: y[0](x, y[1]), operations)
    x, y, z = tpos[0], target_frame.position[1], tpos[1]
    org = target_frame.rotation
    # -rad: mmd's coordinate system is left handed
    new_rot = vmdutil.compose_quaternion(org, (0, 1, 0), -rad, True)
    return target_frame._replace(rotation=tuple(new_rot), position=(x, y, z))


def move_LRIKs(name_dict, leftfoot, rad=0,
               scale=1.0, offset=(0, 0, 0)):
    return (
        [move_feetIK(frame, name_dict, leftfoot, False, rad, scale, offset)
            for frame in name_dict[LEFT]],
        [move_feetIK(frame, name_dict, leftfoot, True, rad, scale, offset)
            for frame in name_dict[RIGHT]]
    )


def move_center_frames(name_dict, rad=0, scale=1.0, offset=(0, 0, 0)):
    result = {}
    offset = (offset[0], offset[2])
    for key in CENTERS:
        result[key] = list()
        for frame in name_dict[key]:
            rotation = vmdutil.compose_quaternion(
                frame.rotation, (0, 1, 0), -rad, True)
            pos_xz = vmdutil.rotate_v2(
                (frame.position[0], frame.position[2]), rad)
            pos_xz = vmdutil.scale_v(pos_xz, scale)
            pos_xz = vmdutil.add_v(pos_xz, offset)
            result[key].append(
                frame._replace(
                    rotation=tuple(rotation),
                    position=(pos_xz[0], frame.position[1], pos_xz[1])))
    return result


def transmotion(vmdin, leftfoot, ry=0, scale=1.0, offset=(0, 0, 0)):
    rad = math.radians(ry)
    bone_frames = vmdin.get_frames('bones')
    frame_dict = vmdutil.frames_to_dict(bone_frames)
    name_dict = vmdutil.make_name_dict(frame_dict, decode=True)
    center0 = name_dict[CENTER][0].position

    center_frames = move_center_frames(name_dict, rad, scale, offset)
    rik, lik = move_LRIKs(name_dict, leftfoot, rad, scale, offset)

    for name in center_frames.keys():
        name_dict[name] = center_frames[name]
    name_dict[LEFT] = lik
    name_dict[RIGHT] = rik

    new_frames = list()
    for key in name_dict.keys():
        new_frames.extend(name_dict[key])
    vmdout = vmdin.copy()
    vmdout.set_frames('bones', new_frames)
    return vmdout


def transmotion_fd(infile, outfile, leftfoot,
                   ry=0, scale=1.0, offset=(0, 0, 0)):
    vmdin = vmdutil.Vmdio()
    vmdin.load_fd(infile)
    vmdout = transmotion(vmdin, leftfoot, ry, scale, offset)
    vmdout.store_fd(outfile)


def transmotion_fname(infile, outfile, leftfoot,
                      ry=0, scale=1.0, offset=(0, 0, 0)):
    vmdin = vmdutil.Vmdio()
    vmdin.load(infile)
    vmdout = transmotion(vmdin, leftfoot, ry, scale, offset)
    vmdout.store(outfile)


if __name__ == '__main__':
    args = _parser.parse_args()
    transmotion_fd(**vars(args))
