'''
Compare vmd files

'''
import enum
import argparse
import vmdutil
from vmdutil import vmddef


SEPARATOR = '@@ {} @@'
HEADER = {
    'bones': SEPARATOR.format('ボーン'),
    'morphs': SEPARATOR.format('モーフ'),
    'cameras': SEPARATOR.format('カメラ'),
    'lights': SEPARATOR.format('照明')
}

DiffResult = enum.Enum(
    'DiffResult',
    'EQUAL NOT_EQUAL A_ONLY B_ONLY')


def make_argumentparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('vmd_a', help='vmd A')
    parser.add_argument('vmd_b', help='vmd B')
    parser.add_argument('--names', nargs='*',
        help='specify bone or morph names to diff')
    parser.add_argument(
        '-o', metavar='filename', type=argparse.FileType('wb'),
        help='write diff frames(unsigned and \'+\' signed) to vmd file')
    parser.add_argument(
        '--short', action='store_true',
        help='omit unnecessary keys')
    return parser


def reformat_camera_interpolation(interpolation):
    c = vmddef.camera_vmdformat_to_controlpoints(interpolation)
    return vmddef.camera_controlpoints_to_vmdformat(c)


def reformat_bone_interpolation(interpolation):
    c = vmddef.bone_vmdformat_to_controlpoints(interpolation)
    return vmddef.bone_controlpoints_to_vmdformat(c)


# not care about floating point rounding
def compare_vmd_frame(frame_a, frame_b):
    def compare_camera(frame_a, frame_b):
        # distance, position, rotation, angle_of_view, perspective,
        # interpolation
        frame_a = frame_a._replace(
            interpolation=reformat_camera_interpolation(frame_a.interpolation))
        frame_b = frame_b._replace(
            interpolation=reformat_camera_interpolation(frame_b.interpolation))
        return frame_a == frame_b

    def compare_light(frame_a, frame_b):
        # rgb, direction
        return frame_a == frame_b

    def compare_screw_bone(frame_a, frame_b):
        # rotaion[3], interpolation
        angle_a = frame_a.rotation[3]
        angle_b = frame_b.rotation[3]
        interpolation_a = reformat_bone_interpolation(frame_a.interpolation)
        interpolation_b = reformat_bone_interpolation(frame_b.interpolation)
        return (
            frame_a.position == frame_b.position and
            interpolation_a == interpolation_b and
            abs(angle_a - angle_b) < vmdutil.NEJIRI_THRESHOLD)

    def compare_bone(frame_a, frame_b):
        name = vmdutil.b_to_str(frame_a.name)
        if '捩' not in name:
            # position, rotation, interpolation
            # do b_to_str() if compare name
            interpolation_a = reformat_bone_interpolation(
                frame_a.interpolation)
            interpolation_b = reformat_bone_interpolation(
                frame_b.interpolation)
            return (
                frame_a.position == frame_b.position and
                frame_a.rotation == frame_b.rotation and
                interpolation_a == interpolation_b)
        else:
            return compare_screw_bone(frame_a, frame_b)

    def compare_morph(frame_a, frame_b):
        return frame_a.weight == frame_b.weight

    switch_case = {
        vmddef.bone: compare_bone,
        vmddef.morph: compare_morph,
        vmddef.camera: compare_camera,
        vmddef.light: compare_light
    }

    return switch_case[type(frame_a)](frame_a, frame_b)


def diff_noname_frames(frame_dict_a, frame_dict_b, buf=None):
    # frame_dict: {frame: [frame]}
    def insert_result(f, v, d):
        r = d.setdefault('', dict())  # no name
        r[frame] = v

    if buf is None:
        buf = dict()

    union_frames = set(frame_dict_a).union(frame_dict_b)
    for frame in union_frames:
        len_a = len(frame_dict_a[frame])
        len_b = len(frame_dict_b[frame])
        if len_a == 0 and len_b == 0:
            continue
        elif len_a > 0 and len_b == 0:
            insert_result(frame, DiffResult.A_ONLY, buf)
        elif len_a == 0 and len_b > 0:
            insert_result(frame, DiffResult.B_ONLY, buf)
        elif compare_vmd_frame(frame_dict_a[frame][0], frame_dict_b[frame][0]):
            insert_result(frame, DiffResult.EQUAL, buf)
        else:
            insert_result(frame, DiffResult.NOT_EQUAL, buf)
    return buf


def diff_named_frames(
        names,
        frames_a, index_dict_a, frames_b, index_dict_b, buf=None):
    # index_dict: {name : {frame: index}}
    def insert_result(f, v, d):
        r = d.setdefault(name, dict())
        r[frame] = v

    if buf is None:
        buf = dict()

    for name in names:
        fa = index_dict_a.get(name, dict())
        fb = index_dict_b.get(name, dict())
        union_frames = set(fa).union(fb)

        for frame in union_frames:
            a = fa.get(frame, None)
            b = fb.get(frame, None)
            if a is None and b is None:
                continue
            elif a is not None and b is None:
                insert_result(frame, DiffResult.A_ONLY, buf)
            elif a is None and b is not None:
                insert_result(frame, DiffResult.B_ONLY, buf)
            elif compare_vmd_frame(frames_a[a], frames_b[b]):
                insert_result(frame, DiffResult.EQUAL, buf)
            else:
                insert_result(frame, DiffResult.NOT_EQUAL, buf)
    return buf


def print_file_info(args, vmd_a, vmd_b):
    print('--- {}: {}'.format(
        args.vmd_a, vmdutil.b_to_str(vmd_a.header.model_name)))
    print('+++ {}: {}'.format(
        args.vmd_b, vmdutil.b_to_str(vmd_b.header.model_name)))


def print_summary(key_type, diff_info, args):
    print(HEADER[key_type])
    name_dict = dict()
    for name, frame_dict in diff_info.items():
        for frame_no in sorted(frame_dict):
            diff_data = frame_dict[frame_no]
            if diff_data != DiffResult.EQUAL:
                frame_string = str(frame_no)
                if diff_data == DiffResult.A_ONLY:
                    frame_string = '-' + frame_string
                elif diff_data == DiffResult.B_ONLY:
                    frame_string = '+' + frame_string
                l = name_dict.setdefault(name, list())
                l.append(frame_string)

    for name in sorted(name_dict):
        l = name_dict[name]
        print('{}:{}'.format(name, ','.join([i for i in l])))
    return


def write_motion_diff(vmd_b, bone_diff, morph_diff, args):
    def collect_diff_frames(key_type, motions_b, diff_info, args):
        result = list()
        index_dict_b = vmdutil.make_index_dict(motions_b, True)
        for name, frame_dict in diff_info.items():
            for frame_no, diff_data in frame_dict.items():
                if (diff_data == DiffResult.B_ONLY or
                        diff_data == DiffResult.NOT_EQUAL):
                    result.append(motions_b[index_dict_b[name][frame_no]])
        return result

    bone_motions = collect_diff_frames(
        'bones', vmd_b.get_frames('bones'), bone_diff, args)
    morph_motions = collect_diff_frames(
        'morphs', vmd_b.get_frames('morphs'), morph_diff, args)

    vmdout = vmdutil.Vmdio()
    vmdout.header = vmd_b.header
    vmdout.set_frames('bones', bone_motions)
    vmdout.set_frames('morphs', morph_motions)
    vmdout.store_fd(args.o)
    return


def write_camera_diff(vmd_b, camera_diff, light_diff, args):
    camera_motions = list()
    camera_dict = vmdutil.frames_to_dict(vmd_b.get_frames('cameras'))
    frame_dict = camera_diff.get('', None)
    if frame_dict is not None:
        for frame_no, diff_data in frame_dict.items():
            if (diff_data == DiffResult.B_ONLY or
                    diff_data == DiffResult.NOT_EQUAL):
                camera_motions.append(camera_dict[frame_no][0])

    light_motions = list()
    light_dict = vmdutil.frames_to_dict(vmd_b.get_frames('lights'))
    frame_dict = light_diff.get('', None)
    if frame_dict is not None:
        for frame_no, diff_data in frame_dict.items():
            if (diff_data == DiffResult.B_ONLY or
                    diff_data == DiffResult.NOT_EQUAL):
                light_motions.append(light_dict[frame_no][0])

    vmdout = vmdutil.Vmdio()
    vmdout.header = vmd_b.header
    vmdout.set_frames('cameras', camera_motions)
    vmdout.set_frames('lights', light_motions)
    vmdout.store_fd(args.o)
    return


def diff_noname(key_type, vmd_a, vmd_b):
    frame_dict_a = vmdutil.frames_to_dict(vmd_a.get_frames(key_type))
    frame_dict_b = vmdutil.frames_to_dict(vmd_b.get_frames(key_type))
    return diff_noname_frames(frame_dict_a, frame_dict_b)


def omit_unnecessary_frames(frames_a, frames_b, key_type):
    def keys_used(nd, key_type):
        keys_to_omit = vmdutil.enum_unnecessary_keys(nd, key_type)
        return set(nd).difference(keys_to_omit)

    def update_frames(nd, keys):
        result = list()
        for key, value in nd.items():
            if key in keys:
                result.extend(value)
        return result

    nd_a = vmdutil.make_name_dict(vmdutil.frames_to_dict(frames_a), True)
    nd_b = vmdutil.make_name_dict(vmdutil.frames_to_dict(frames_b), True)
    keys_a = keys_used(nd_a, key_type)
    keys_b = keys_used(nd_b, key_type)
    need_keys = keys_a.union(keys_b)
    result_a = update_frames(nd_a, need_keys)
    result_b = update_frames(nd_b, need_keys)
    return result_a, result_b


def diff_named(key_type, vmd_a, vmd_b, args, names=None):
    frames_a = vmd_a.get_frames(key_type)
    frames_b = vmd_b.get_frames(key_type)
    if args.short is True:
        frames_a, frames_b = (
            omit_unnecessary_frames(frames_a, frames_b, key_type))
    index_dict_a = vmdutil.make_index_dict(frames_a, True)
    index_dict_b = vmdutil.make_index_dict(frames_b, True)
    if names is None:
        names = set(index_dict_a).union(index_dict_b)
    return diff_named_frames(
        names, frames_a, index_dict_a, frames_b, index_dict_b)


# {key_type: name: {frame: result}}
if __name__ == '__main__':
    parser = make_argumentparser()
    args = parser.parse_args()
    vmd_a = vmdutil.Vmdio()
    vmd_b = vmdutil.Vmdio()
    vmd_a.load(args.vmd_a)
    vmd_b.load(args.vmd_b)
    is_camera = vmdutil.is_camera_header(vmd_b.header)
    print_file_info(args, vmd_a, vmd_b)
    if is_camera is True:
        camera_diff = diff_noname('cameras', vmd_a, vmd_b)
        light_diff = diff_noname('lights', vmd_a, vmd_b)
        print_summary('cameras', camera_diff, args)
        print_summary('lights', light_diff, args)
        if args.o is not None:
            write_camera_diff(vmd_b, camera_diff, light_diff, args)
    else:
        if args.names is not None:
            names = args.names
        else:
            names = None
        bone_diff = diff_named('bones', vmd_a, vmd_b, args, names)
        morph_diff = diff_named('morphs', vmd_a, vmd_b, args, names)
        print_summary('bones', bone_diff, args)
        print_summary('morphs', morph_diff, args)
        if args.o is not None:
            write_motion_diff(vmd_b, bone_diff, morph_diff, args)
