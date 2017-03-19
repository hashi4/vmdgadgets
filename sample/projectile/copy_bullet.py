import sys
sys.path.append('../../vmdgadgets')
from vmdutil import pmxutil
from vmdutil import pmxdef

ORIG = r'model\bullet.pmx'
COPY_TO = r'model\bullet{0}.pmx'
EDGE_BONES = ['PU主砲_砲身_L先', 'PU主砲_砲身_U先', 'SU主砲_砲身_L先',
              'SU主砲_砲身_U先', 'PL主砲_砲身_L先', 'PL主砲_砲身_U先',
              'SL主砲_砲身_L先', 'SL主砲_砲身_U先']

def copy_bullets():
    orig = pmxutil.Pmxio()
    orig.load(ORIG)
    for i, bone_name in enumerate(EDGE_BONES):
        orig.model_info = orig.model_info._replace(name_jp=bone_name)
        orig.store(COPY_TO.format(i))

if __name__ == '__main__':
    copy_bullets()
