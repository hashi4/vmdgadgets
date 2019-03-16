'''
Make motions of spectrum meter
'''

import sys
import wave
import struct
import math
import numpy as np
import bisect
import os
import argparse
from collections import namedtuple
import json
import vmdutil
from vmdutil import vmddef

# 2 to the power of 16
# -32,768, +32,767
WAVE_MAX_VALUE = {1: 255, 2: 32768}
MMD_FRAME_PER_SEC = 30
DEFAULT_VMD_MAX_FRAME = 20000
RESOLUTION = 1000


def _make_argumentparser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'infile', help='wavefile name.')
    parser.add_argument(
        '--config', nargs='?', default='config.json', const='config.json',
        metavar='config filename', help='configuration filename')
    return parser


_parser = _make_argumentparser()
__doc__ += _parser.format_help()


def mag2db(y):
    return math.log(y, 10) * 20


def check_waveformat(f):
    width = f.getsampwidth()
    if width != 1 and width != 2:
        return False
    channels = f.getnchannels()
    if channels != 1 and channels != 2:
        return False
    return True


def struct_format(width, samples):
    if width == 1:
        return '{0}B'.format(samples)
    else:
        return '{0}h'.format(samples)


def read_wave(f):
    if not check_waveformat(f):
        raise Exception('only supports 8 and 16bit format')
    rate = f.getframerate()
    frames = f.getnframes()
    channels = f.getnchannels()
    width = f.getsampwidth()
    strformat = struct_format(f.getsampwidth(), frames * channels)
    unpacked_datas = struct.unpack(strformat, f.readframes(frames))
    Wavedata = namedtuple(
        'Wavedata', [
            'rate', 'n_channels', 'n_frames', 'sampwidth', 'frames'])
    return Wavedata(rate, channels, frames, width, unpacked_datas)


def get_subframes(frame, n_sample, wave_data):
    start_frame = int(frame - n_sample / 2)
    if start_frame < 0:
        return None
    if (start_frame + n_sample) > wave_data.n_frames:
        return None
    result = [[] for i in range(wave_data.n_channels)]
    for i in range(n_sample):
        for j in range(wave_data.n_channels):
            result[j].append(
                wave_data.frames[(start_frame + i) * wave_data.n_channels + j])
    return result


def get_spectrum(frameno, n_sample, wave_data):
    samples = get_subframes(frameno, n_sample, wave_data)
    if samples is None:
        return None
    if wave_data.n_channels > 1:
        L = np.array(samples[0])
        R = np.array(samples[1])
        sample = (L + R) / 2
    else:
        sample = np.array(samples[0])
    sample /= WAVE_MAX_VALUE[wave_data.sampwidth]
    window = np.blackman(n_sample)
    sample *= window
    spectrum = np.fft.fft(sample)
    return np.abs(spectrum) * 2 / n_sample


def freq_ranges(nsample, rate, band_def):
    freqs = np.fft.fftfreq(nsample, 1 / rate)
    r = [i for i in freqs[1:] if i > 0]

    def c(v):
        return vmdutil.clamp(v, 0, len(r))

    ranges = list()
    for band in band_def[0]:
        high = band * band_def[1]
        low = band / band_def[1]
        ranges.append(
            (c(bisect.bisect(r, low)),
             c(bisect.bisect(r, band)),
             c(bisect.bisect(r, high))))
    r.insert(0, freqs[0])
    return r, ranges


def get_magnitudes(frame_no, n_sample, wave_data, band_def, ranges):
    spectrum = get_spectrum(frame_no, n_sample, wave_data)
    if spectrum is None:
        return None
    result = list()
    for i in range(len(band_def[0])):
        low = ranges[i][0]
        high = ranges[i][2]
        mag_max = max([spectrum[i] for i in range(low, high + 1)])
        result.append(mag_max)
#        result.append(spectrum[ranges[i][1]])
    return result

#
# mmd
#


def mmd2wave_frame(mmd_frame, rate):
    return int(mmd_frame * rate / MMD_FRAME_PER_SEC)


def mag2scale(mag, mindb):
    if mag > 0:
        db = vmdutil.clamp(mag2db(mag), mindb, 0)
    else:
        db = mindb
    return 1 - db / mindb


def zero_bones(frame_no, n_bands, config):
    bone_frames = list()
    bone_motion = vmddef.BONE_SAMPLE
    for band in range(n_bands):
        bone_name = config['METER_BONE_NAME'].format(band).encode(
            vmddef.ENCODING)
        bone_frames.append(
            bone_motion._replace(
                frame=frame_no, name=bone_name))
    return bone_frames


def zero_viewmorphs(frame_no, n_bands, config):
    morph_frames = list()
    for band in range(n_bands):
        morph_name = config['VIEW_MORPH_NAME'].format(band).encode(
            vmddef.ENCODING)
        morph = vmddef.morph(morph_name, frame_no, 0)
        morph_frames.append(morph)
    return morph_frames


def zero_metermorphs(frame_no, n_bands, config):
    morph_frames = list()
    for band in range(n_bands):
        morph_name = config['METER_MORPH_NAME'].format(band).encode(
            vmddef.ENCODING)
        morph = vmddef.morph(morph_name, frame_no, 0)
        morph_frames.append(morph)
    return morph_frames


def read_config(filename):
    try:
        fp = open(filename, 'r', encoding='utf-8')
        config = json.load(fp)
        fp.close()
        return config
    except:
        return None


def meter_interpolation():
    interpolation = vmddef.BONE_LERP_CONTROLPOINTS
    interpolation[0][1] = 100
    interpolation[1][1] = 0
    interpolation[2][1] = 127
    interpolation[3][1] = 27
    return vmddef.bone_controlpoints_to_vmdformat(interpolation)


def store_vmd(filename, bones, morphs, config):
    vmdo = vmdutil.Vmdio()
    vmdo.header = vmdo.header._replace(
        model_name=config['METER_MODEL_NAME'].encode(vmddef.ENCODING))
    vmdo.set_frames('bones', bones)
    vmdo.set_frames('morphs', morphs)
    vmdo.store(filename)


def mk_bone_motion(info, config):
    frame_no, band_no, mag = info
    bone_name = config['METER_BONE_NAME'].format(band_no).encode(
        vmddef.ENCODING)
    b_scale = mag * config['BAR_HEIGHT']
    pos = (0, b_scale, 0)
    bone = vmddef.BONE_SAMPLE._replace(
        frame=frame_no,
        name=bone_name, position=pos, interpolation=config['INTERPOLATION'])
    return bone


def mk_view_morph(info, config):
    frame_no, band_no, mag = info
    morph_name = config['VIEW_MORPH_NAME'].format(band_no).encode(
        vmddef.ENCODING)
    morph = vmddef.morph(
        morph_name, frame_no, mag * config['VIEW_MORPH_SCALE'])
    return morph


def mk_meter_morph(info, config):
    frame_no, band_no, mag = info
    morph_name = config['METER_MORPH_NAME'].format(band_no).encode(
        vmddef.ENCODING)
    morph = vmddef.morph(morph_name, frame_no, mag)
    return morph


def fft_wave(infile, config):
    # main
    f = wave.open(infile, 'r')
    wave_data = read_wave(f)
    f.close()

    filename, ext = os.path.splitext(os.path.basename(infile))
    band_def = config['BAND_DEFS'][config['BANDS']]
    n_bands = len(band_def[0])

    freqs, ranges = freq_ranges(
        config['FFT_SAMPLE'], wave_data.rate, band_def)
    mmd_frame_max = int(
        wave_data.n_frames / wave_data.rate * MMD_FRAME_PER_SEC)

    interpolation = meter_interpolation()
    config['INTERPOLATION'] = interpolation

    vmorph = 'USE_VIEW_MORPH' in config and config['USE_VIEW_MORPH'] is True
    mmorph = 'USE_METER_MORPH' in config and config['USE_METER_MORPH'] is True

    mmd_frame_no = 0
    maxf = config['VMD_MAX_FRAME'] if \
        'VMD_MAX_FRAME' in config else DEFAULT_VMD_MAX_FRAME
    vmd_per_frame = 2 * n_bands if vmorph else n_bands
    zero_paddings = vmd_per_frame * 2
    spare = vmd_per_frame * 1  # omajinai

    def overflow(vmd_recorded):
        return vmd_recorded >= maxf - zero_paddings - spare

    def vmd_name(kind, no):
        return '{0}_{1}_{2}{3:02d}.vmd'.format(
            config['METER_MODEL_NAME'], filename, kind, no)

    def vmd_name_all(kind):
        return '{0}_{1}_{2}.vmd'.format(
            config['METER_MODEL_NAME'], filename, kind)

    def insert_zero_frames(mmd_frame_no, bones, morphs):
        if mmorph:
            morphs += zero_metermorphs(
                mmd_frame_no, n_bands, config)
        else:
            bones += zero_bones(
                mmd_frame_no, n_bands, config)
        if vmorph:
            morphs += zero_viewmorphs(
                mmd_frame_no, n_bands, config)
        return

    ###
    bone_list = [list() for i in range(n_bands)]
    mmorph_list = [list() for i in range(n_bands)]
    vmorph_list = [list() for i in range(n_bands)]
    while mmd_frame_no <= mmd_frame_max:
        wave_frame = mmd2wave_frame(mmd_frame_no, wave_data.rate)
        mags = get_magnitudes(
            wave_frame, config['FFT_SAMPLE'], wave_data, band_def, ranges)
        if mags:
            for band_no in range(n_bands):
                scale = mag2scale(mags[band_no], config['MIN_DB'])
                scale = int(scale * RESOLUTION)
                scale /= RESOLUTION
                info = (mmd_frame_no, band_no, scale)
                if not mmorph:
                    bone_list[band_no].append(mk_bone_motion(info, config))
                else:
                    mmorph_list[band_no].append(mk_meter_morph(info, config))
                if vmorph:
                    vmorph_list[band_no].append(mk_view_morph(info, config))
        mmd_frame_no += config['FRAME_INCR']

    # normalize
    for band_no in range(n_bands):
        bone_list[band_no] = vmdutil.remove_redundant_frames(
            bone_list[band_no])
        mmorph_list[band_no] = vmdutil.remove_redundant_frames(
            mmorph_list[band_no])
        vmorph_list[band_no] = vmdutil.remove_redundant_frames(
            vmorph_list[band_no])


    # vmd out
    vmdout = vmdutil.Vmdio()
    store_vmd(
        vmd_name_all('b'),
        [f for sublist in bone_list for f in sublist], [], config)
    if mmorph:
        for band_no in range(n_bands):
            store_vmd(vmd_name('mm', band_no), [], mmorph_list[band_no], config)
    if vmorph:
        for band_no in range(n_bands):
            store_vmd(vmd_name('vm', band_no), [], vmorph_list[band_no], config)


def fft_wave_fname(infile, config):
    conf = read_config(config)
    if not conf:
        sys.stderr.write('cannot open {0}'.format(config))
        return
    else:
        fft_wave(infile, conf)


if __name__ == '__main__':
    args = _parser.parse_args()
    fft_wave_fname(**vars(args))
