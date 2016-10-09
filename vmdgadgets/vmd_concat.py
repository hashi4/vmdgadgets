'''Copy paticuler frames in vmd file to another.

'''
import sys
import codecs
import re
import bisect
import functools
import argparse
from collections import defaultdict

import vmdutil
from vmdutil import vmddef

TRANSLATE_BONES = ['センター', '左足ＩＫ', '右足ＩＫ']

EPILOG = '''Infile is a csv formatted file.
In csv file, lines end with \'.vmd\' indicate names of vmd file to be copied.
Other lines following name line are instructions for copy.
Each line should have 4 tokens, or 6 or 7.
 0: start frame number of source file to be copied
 1: end frame number of source file to be copied(include this frame)
 2: frame number of dest file to write
 3: value to translate along x axis(optional)
 4: value to translate along y axis(optional)
 5: value to translate along z axis(optional)
 6: if length of tokens > 6, then mirror(optional)

             | mirror(*1) | translate  |
 ------------+------------+------------+
 bone        |  yes       | yes(*2)    |
 ------------+------------+------------+
 morph       |  no        | no         |
 ------------+------------+------------+
 camera      |  yes       | yes        |
 ------------+------------+------------+
 light       |  yes       | no         |
 ------------+------------+------------+
 other       |  no        | no         |
 ------------+------------+------------+
(*1) at first mirror, then translate.
(*2) [{0}] are translated.

example,
---- infile.txt ----
foo.vmd
0,100,10,1,2,3,1
bar.vmd
0,50,110
--------------------
$ python {1} infile.txt out.vmd
Copy from frame_No. 0 to frame_No. 100 of foo.vmd to frame_No. 10 of out.vmd.
Motions are mirrored and then translated to (+1, +2, +3).
Copy from frame_No. 0 to frame_No. 50 of bar.vmd to frame_no 110 of out.vmd.
No bones are mirrored nor translated.
'''.format(', '.join(TRANSLATE_BONES), sys.argv[0])


def _make_argumentparser():
    parser = argparse.ArgumentParser(
        epilog=EPILOG, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        'infile', nargs='?', type=argparse.FileType('r', encoding='shift-jis'),
        default=sys.stdin,
        help='instructions for copy. default=stdin')
    parser.add_argument(
        'outfile', nargs='?', type=argparse.FileType('wb'),
        default=sys.stdout.buffer,
        help='output vmd file. default=stdout')
    return parser

_parser = _make_argumentparser()
__doc__ += _parser.format_help()


def trim_CRLF(line):
    return line.strip('\n').strip('\r').strip()


def read_instruction(instruction):
    instructions = defaultdict(list)  # {vmd_filename: [recipe]}
    vmd_name = ''
    for line in instruction:
        # comment
        if re.match('^\s*#.*', line):
            continue
        line = trim_CRLF(line)
        inst = line.split(',')
        # filename
        if len(inst) == 1 and line[line.rindex('.'):] == '.vmd':
            vmd_name = line
            continue
        # recipe
        tmp_list = list()
        # 1) src_from,  src_to, dest_to
        # 2) dest_from, dest_to, src
        for i in range(3):
            tmp_list.append(int(inst[i]))
        for i in range(3, len(inst)):  # [translate(x,y,z), mirror]
            tmp_list.append(float(inst[i]))
        instructions[vmd_name].append(tmp_list)
    return instructions


def load_vmds(file_list):
    camera_motion = True
    first_file = True
    vmds = dict()
    for file_name in file_list:
        if file_name == '':
            sys.stderr.write('no file_name')
            continue
        vmd_in = vmdutil.Vmdio()
        vmd_in.load(file_name)
        if vmdutil.is_vmd_header(vmd_in.header):
            is_camera = vmdutil.is_camera_header(vmd_in.header)
            if first_file:
                camera_motion = is_camera
                header = vmd_in.header
                first_file = False
            elif camera_motion != is_camera:
                sys.stderr.write('skip {0}'.format(file_name))
                continue
            vmds[file_name] = vmd_in
        else:
            sys.stderr.write('skip {0}'.format(file_name))
            continue
    return header, vmds


def transform_none(motion_def, instruction):
    return motion_def


def translate_bone(motion_def, instruction):
    if len(instruction) < 4:
        return motion_def
    else:
        bone_name = vmdutil.b_to_str(motion_def.name)
        if bone_name in TRANSLATE_BONES:
            position = motion_def.position
            delta = instruction[3:6]
            r = vmdutil.add_v(position, delta)
            motion_def = motion_def._replace(position=tuple(r))
        return motion_def


def mirror_bone(motion_def, instruction):
    if len(instruction) > 6:
        return vmdutil.mirror_frame(motion_def)
    else:
        return motion_def


def translate_camera(motion_def, instruction):
    if len(instruction) < 4:
        return motion_def
    else:
        position = motion_def.position
        delta = instruction[3:6]
        r = vmdutil.add_v(position, delta)
        motion_def = motion_def._replace(position=tuple(r))
    return motion_def


def mirror_camera(motion_def, instruction):
    if len(instruction) > 6:
        return vmdutil.mirror_frame(motion_def)
    else:
        return motion_def


def mirror_light(motion_def, instruction):
    if len(instruction) > 6:
        new_direction = (
            motion_def.direction[0] * -1, motion_def.direction[1],
            motion_def.direction[2])
        motion_def = motion_def._replace(direction=new_direction)
        return motion_def
    else:
        return motion_def


class Transform:
    def __init__(self):
        e = vmddef.VMD_ELEMENTS
        self.transforms = {
            e[0]: (translate_bone, mirror_bone),
            e[1]: (transform_none, transform_none),
            e[2]: (translate_camera, mirror_camera),
            e[3]: (transform_none, mirror_light),
            e[4]: (transform_none, transform_none),
            e[5]: (transform_none, transform_none),
        }

    def __call__(self, element, motion_def, instruction):
        translate, mirror = self.transforms[element]
        motion_def = mirror(motion_def, instruction)
        motion_def = translate(motion_def, instruction)
        return motion_def


def copy_motion(instructions, frame_dict):
    trans = Transform()
    new_frames = defaultdict(list)
    for instruction in instructions:
        for element in vmddef.VMD_ELEMENTS:
            motion_dict = frame_dict[element]
            src_frames = sorted(motion_dict.keys())
            src_from_frame, src_to_frame, dest_frame, *d = instruction
            copy_length = src_to_frame - src_from_frame  # +1
            index = bisect.bisect_left(src_frames, src_from_frame)
            while index < len(src_frames):
                to_be_copied = src_frames[index]
                delta = to_be_copied - src_from_frame
                if delta > copy_length:
                    break
                for frame_info in motion_dict[to_be_copied]:
                    new_info = trans(
                        element, frame_info, instruction)
                    new_frame = new_info._replace(
                        frame=(dest_frame + delta))
                    new_frames[element].append(new_frame)
                index += 1
    return new_frames


def do_concat(inst_file):
    instructions = read_instruction(inst_file)
    header, vmd_ins = load_vmds(instructions.keys())
    # load srcs
    frame_dict = dict()
    for vmd_name in vmd_ins.keys():
        frame_dict[vmd_name] = vmdutil.make_motion_dict(vmd_ins[vmd_name])
    # copy
    new_frames = list()
    for vmd_name in vmd_ins.keys():
        new_frames.append(
            copy_motion(instructions[vmd_name], frame_dict[vmd_name]))
    # merge
    out_frames = dict()
    for element in vmddef.VMD_ELEMENTS:
        out_frames[element] = functools.reduce(
            lambda x, y: x + y, [frames[element] for frames in new_frames])
    return header, out_frames


def vmd_concatenate_fd(infile, outfile):
    header, new_frames = do_concat(infile)
    p = vmdutil.Vmdio()
    p.header = header
    for element in vmddef.VMD_ELEMENTS:
        p.set_frames(element, new_frames[element])
    p.store_fd(outfile)


def vmd_concatenate(infile, outfile):
    fin = open(infile, 'r')
    fout = open(outfile, 'wb')
    vmd_concatenate_fd(fin, fout)
    fin.close()
    fout.close()


if __name__ == '__main__':
    args = _parser.parse_args()
    vmd_concatenate_fd(**vars(args))
