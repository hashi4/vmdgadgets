import sys
import argparse
from collections import defaultdict
from collections import Iterable
import vmdutil
from vmdutil import vmddef

def make_argumentparser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i', '--infile', nargs='+', type=argparse.FileType('rb'),
        default=sys.stdin.buffer,
        help='input')
    parser.add_argument(
        '-o', '--outfile', type=argparse.FileType('wb'),
        default=sys.stdout.buffer,
        help='output')
    return parser



def merge(args):
    all_frames = defaultdict(list)
    vmd_header = None
    def load_vmd(infile):
        nonlocal vmd_header
        vmdin = vmdutil.Vmdio()
        try:
            vmdin.load_fd(infile)
        except:
            sys.stderr.write('cannot load {0}\n'.format(infile.name))
            return
        if vmd_header is None:
            vmd_header = vmdin.header
        for element in vmddef.VMD_ELEMENTS:
            frames = all_frames[element]
            vmd_frames = vmdin.get_frames(element)
            frames.extend(vmd_frames)   

    if type(args.infile) == type([]):
        for file in args.infile:
            if file.name == '<stdin>':
                file = sys.stdin.buffer
            load_vmd(file)
    else:
        load_vmd(args.infile)

    vmdout = vmdutil.Vmdio()
    for element in vmddef.VMD_ELEMENTS:
        frames = all_frames[element]
        if len(frames) > 0:
            vmdout.set_frames(element, frames)
    if vmd_header is not None:
        vmdout.header = vmd_header
    vmdout.store_fd(args.outfile)

if __name__ == '__main__':
    parser = make_argumentparser()
    args = parser.parse_args()
    merge(args)
