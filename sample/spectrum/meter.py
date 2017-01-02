# sample of spectrum meter

import sys
import json

def quote(s):
    return '"' + s + '"'

def print_header(config):
    print('Header,2.1,0,0')
    return


def print_model_info(config):
    print('ModelInfo,"{0}","","",""'.format(
        config['METER_MODEL_NAME']))
    return

def print_vertexes(config):
    V_TEMPLATE='Vertex,0,-1,1,0,0,0,-1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,"b01",1,"",0,"",0,"",0,0,0,0,0,0,0,0,0,0'
    VT = V_TEMPLATE.split(',')
    vno = 0
    n_bands = len(config['BAND_DEFS'][config['BANDS']][0])
    for band in range(n_bands):
        for index in range(4):
            VT[1] = str(vno)
            vno += 1
            if index % 2 == 0:
                VT[2] = str(band * config['BAR_WIDTH'])
            else:
                VT[2] = str(
                    (band + 1) * config['BAR_WIDTH'] - config['BAR_SPACE'])
            if index < 2:
                VT[28] = quote(config['METER_BONE_NAME']).format(band)
                VT[3] = '0'
            else:
                VT[28] = '"b{0}0"'.format(band)
                VT[3] = '0'
            print(','.join(VT))
    return

def print_materials(config):
    M_TEMPLATE = 'Material,"平面","",1,1,1,0.8,0,0,0,100,0.3,0.3,0.3,1,0,0,0,0,0,0,1,0,0,0,1,"","",1,"",""'
    F_TEMPLATE = 'Face,"平面",0,0,1,2'

    MT = M_TEMPLATE.split(',')
    n_bands = len(config['BAND_DEFS'][config['BANDS']][0])
    for band in range(n_bands):
        MT[1] = '"band{0}"'.format(band)
        MT[3] = MT[11] = str(config['BAR_RGB'][0]) #diffuse, env
        MT[4] = MT[12] = str(config['BAR_RGB'][1])
        MT[5] = MT[13] = str(config['BAR_RGB'][2])
        MT[7] = '0' #specular
        MT[8] = '0'
        MT[9] = '0'
        MT[6] = str(config['BAR_TRANSPARENCY'])
        print(','.join(MT))
    for band in range(n_bands):
        vbase = band * 4
        for i in range(2):
            if i == 0:
                ftext = 'Face,"band{0}",{1},{2},{3},{4}'.format(
                    band, i, vbase, vbase + 1, vbase + 2, vbase + 3)
            else:
                ftext = 'Face,"band{0}",{1},{2},{3},{4}'.format(
                    band, i, vbase + 1, vbase + 3, vbase + 2)
            print(ftext)

def print_bones(config):
    B_TEMPLATE = 'Bone,"b00","",0,0,0,0,0,1,0,0,1,1,"",0,"",0,0,0,0,0,0,1,"",0,0,0,0,0,1,0,0,0,0,1,0,0,"",0,57.29578'
    BT = B_TEMPLATE.split(',')
    BT[1] = '"センター"'
    BT[9] = '1'
    print(','.join(BT))
    BT[1] = '"bands_root"'
    BT[9] = '1'
    BT[13] = '"センター"'
    print(','.join(BT))
    n_bands = len(config['BAND_DEFS'][config['BANDS']][0])
    for band in range(n_bands):
        BT[5] = str(config['BAR_WIDTH'] * band + config['BAR_WIDTH'] / 2)
        BT[1] = '"b{0}0"'.format(band)
        BT[13] = '"bands_root"'
        BT[9] = '0'
        print(','.join(BT))
        BT[13] = BT[1]
        BT[1] = quote(config['METER_BONE_NAME']).format(band)
        BT[9] = '1'
        print(','.join(BT))


def print_morph(config):
    M_TEMPLATE = 'Morph,"モーフ1","",4,2'
    MT = M_TEMPLATE.split(',')
    BM_TEMPLATE = 'BoneMorph,"モーフ1","b01",0,10,0,0,0,0'
    BMT = BM_TEMPLATE.split(',')
    n_bands = len(config['BAND_DEFS'][config['BANDS']][0])
    for band in range(n_bands):
        morph_name = quote(config['METER_MORPH_NAME']).format(band)
        MT[1] = morph_name
        print(','.join(MT))
        BMT[1] = morph_name
        BMT[2] = quote(config['METER_BONE_NAME']).format(band)
        BMT[4] = str(config['BAR_HEIGHT'])
        print(','.join(BMT))
    MM_TEMPLATE = 'MaterialMorph,"0","band0",1,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0'
    MMT = MM_TEMPLATE.split(',')
    for band in range(n_bands):
        morph_name = quote(config['VIEW_MORPH_NAME']).format(band)
        MT[1] = morph_name
        MT[4] = '8'
        print(','.join(MT))
        MMT[1] = morph_name
        MMT[2] = '"band{0}"'.format(band)
        print(','.join(MMT))


def print_nodes(config):
    print('Node,"Root","Root"')
    print('NodeItem,"Root",0,"センター"')
    print('Node,"表情","Exp"')
    n_bands = len(config['BAND_DEFS'][config['BANDS']][0])
    for band in range(n_bands):
        print(
            ('NodeItem, "表情", 1, ' + quote(config['METER_MORPH_NAME']))
            .format(band))
    for band in range(n_bands):
        print(
            ('NodeItem, "表情", 1, ' + quote(config['VIEW_MORPH_NAME']))
            .format(band))

    print('Node,"bands",""')
    print('NodeItem,"bands",0,"bands_root"')
    for band in range(n_bands):
        print(
            ('NodeItem, "bands", 0, ' + quote(config['METER_BONE_NAME']))
            .format(band))


if __name__ == '__main__':
    functions = [print_header, print_model_info, print_vertexes,
                 print_materials, print_bones, print_morph, print_nodes]
    fp = open(sys.argv[1], 'r', encoding='utf-8')
    config = json.load(fp)
    fp.close()
    for f in functions:
        f(config)
