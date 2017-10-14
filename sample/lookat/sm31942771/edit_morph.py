# にやり2->にやり
# あ2: あ２+あ+ぺろ総和ù抑制
# あ: あ+ぺろ総和抑制

ORIGINAL = r'sozai\pdapm4ダンス.vmd'

import sys
sys.path.append('../../../vmdgadgets')
import vmdutil

def あ(morphs):
    return morphs

def にやり２(morphs):
    for i, frame in enumerate(morphs):
        if vmdutil.b_to_str(frame.name) == 'にやり２':
            morphs[i] = frame._replace(name=vmdutil.str_to_b('にやり'))
    return morphs

def get_morph_weight(frame_no, frames, keys):
    index, b = vmdutil.get_interval(frame_no, frames, keys)
    if b is True:
        weight = frames[index].weight
    else:
        begin = frames[index]
        end = frames[index + 1]
        t = (frame_no - begin.frame) / (end.frame - begin.frame)
        weight = vmdutil.lerp_v([begin.weight], [end.weight], t)[0]
    return weight

def あplusぺろっ(morphs):
    frame_dict = vmdutil.frames_to_dict(morphs)
    name_dict = vmdutil.make_name_dict(frame_dict, True)
    pelo = name_dict['ぺろっ']
    pelo_keys = [frame.frame for frame in pelo]
    for i, frame in enumerate(morphs):
        if vmdutil.b_to_str(frame.name) == 'あ':
            pelo_weight = get_morph_weight(frame.frame, pelo, pelo_keys)
            if frame.weight + pelo_weight > 0.9:
                d = 0.9 - pelo_weight
                if d < 0:
                    d = 0
                morphs[i] = frame._replace(weight=d)
    return morphs

def あplusあ２plusぺろっ(morphs):
    frame_dict = vmdutil.frames_to_dict(morphs)
    name_dict = vmdutil.make_name_dict(frame_dict, True)
    a = name_dict['あ']
    a_keys = [frame.frame for frame in a]
    pelo = name_dict['ぺろっ']
    pelo_keys = [frame.frame for frame in pelo]
    for i, frame in enumerate(morphs):
        if vmdutil.b_to_str(frame.name) == 'あ２':
            a_weight = get_morph_weight(frame.frame, a, a_keys)
            pelo_weight = get_morph_weight(frame.frame, pelo, pelo_keys)
            plus = a_weight + pelo_weight
            #if plus > 1:
            #    pass
            if frame.weight + plus > 0.8:
                d = 0.8 - plus
                if d < 0:
                    d = 0
                morphs[i] = frame._replace(weight=d)
    return morphs

if __name__ == '__main__':
    vmd = vmdutil.Vmdio()
    vmd.load(ORIGINAL)
    morphs = vmd.get_frames('morphs')
    morphs = にやり２(morphs)
    morphs = あplusあ２plusぺろっ(morphs)
    morphs = あplusぺろっ(morphs)
    vmdout = vmdutil.Vmdio()
    vmdout.set_frames('morphs', morphs)
    vmdout.store('morph_edited.vmd')


