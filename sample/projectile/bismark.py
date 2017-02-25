import sys
sys.path.append('../../../vmdgadgets')
import vmdutil
from projectile import Projectile
from lookat import LookAt
class BismarkUpper(Projectile):
    def __init__(self, watcher_pmx_name, watcher_vmd_name):
        Projectile.__init__(self, watcher_pmx_name, watcher_vmd_name)
        self.set_overwrite_bones(
            ['左上主砲X',
             'PU主砲_砲身_U', 'PU主砲_砲身_U先', 'PU主砲_砲身_L',
             'PU主砲_砲身_L先', '右上主砲X', 'SU主砲_砲身_U',
            'SU主砲_砲身_U先', 'SU主砲_砲身_L', 'SU主砲_砲身_L先'])
        self.set_point_mode('ARM')

class BismarkLower(Projectile):
    def __init__(self, watcher_pmx_name, watcher_vmd_name):
        Projectile.__init__(self, watcher_pmx_name, watcher_vmd_name)
        self.set_overwrite_bones(
            ['左下主砲X',
             'PL主砲_砲身_U', 'PL主砲_砲身_U先', 'PL主砲_砲身_L',
             'PL主砲_砲身_L先', '右下主砲X', 'SL主砲_砲身_U',
            'SL主砲_砲身_U先', 'SL主砲_砲身_L', 'SL主砲_砲身_L先'])
        self.set_point_mode('ARM')
