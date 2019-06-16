import vmdutil
from vmdutil import vmdmotion

vmd = vmdutil.Vmdio()
vmd.load('sozai\\口パク.vmd')

morphs = vmd.get_frames('morphs')
info = vmdmotion.VmdMotion(morphs)
nd = vmdutil.make_name_dict(vmdutil.frames_to_dict(morphs), True)

o_frames = list()
for frame in nd['お']:
    u = info.get_vmd_transform(frame.frame, 'う')
    o = frame.weight
    t = o + u
    if t > 1.0:
        o = 1.0 - u
        o_frames.append(frame._replace(weight=o))
    else:
        o_frames.append(frame)

vmdout = vmdutil.Vmdio()
vmdout.set_frames('morphs', o_frames)
vmdout.store('口パク_お変更.vmd')

    
