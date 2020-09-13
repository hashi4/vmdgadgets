import argparse
import vmdutil
from vmdutil import pmxutil


def make_argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('vmd', help='vmd filename')
    parser.add_argument('pmx', nargs='?', help='pmx filename')
    return parser


if '__main__' == __name__:
    parser = make_argument_parser()
    args = parser.parse_args()

    if args.pmx is not None:
        pmx = pmxutil.Pmxio()
        pmx.load(args.pmx)
    vmd = vmdutil.Vmdio()
    vmd.load(args.vmd)
    bone_motions = vmd.get_frames('bones')
    morph_motions = vmd.get_frames('morphs')

    print('========')
    print(vmdutil.b_to_str(vmd.header.model_name))
    print('========')
    for motion_type in ['bones', 'morphs']:
        if args.pmx is not None:
            pmx_dict = pmxutil.make_index_dict(pmx.get_elements(motion_type))
        else:
            pmx_dict = None
        vmd_dict = vmdutil.make_name_dict(
            vmdutil.frames_to_dict(vmd.get_frames(motion_type)), True)

        not_used_keys = set(
            vmdutil.enum_unnecessary_keys(vmd_dict, motion_type, "greedy"))
        all_keys = set(vmd_dict.keys())

        for key in sorted(all_keys - not_used_keys):
            if pmx_dict is None:
                s = ''
            else:
                s = ' 〇' if key in pmx_dict else ' ×'
            print('{}: {}{}'.format(key, len(vmd_dict[key]), s))
        print('========')
