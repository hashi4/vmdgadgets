import sys
sys.path.append('../../../vmdgadgets')
import vmdutil
from vmdutil import vmddef

def avoid_collision1(vmd):
    center = vmdutil.str_to_b('センター')
    right_arm = vmdutil.str_to_b('右腕')
    right_elb = vmdutil.str_to_b('右ひじ')
    #1032 追加
    c_1032 = vmddef.BONE_SAMPLE._replace(
        frame=1032, name=center,
        position=(2.141899824142456, -0.4837593138217926, 3.3104584217071533))
    ra_1032 = vmddef.BONE_SAMPLE._replace(
        frame=1032, name=right_arm,
        rotation=(0.17264382541179657, 0.13622286915779114, 0.361983984708786, 0.905872106552124))
    re_1032 = vmddef.BONE_SAMPLE._replace(
        frame=1032, name=right_elb,
        rotation=(0.635169506072998, -0.47617700695991516, -0.3107016980648041, 0.5227601528167725))
    # 1036 センター削除
    # 1036 入れ替え
    ra_1036_rot = (0.17034076154232025, 0.14684468507766724, 0.3597466051578522, 0.905540406703949)
    re_1036_rot = (0.6970929503440857, -0.4250965118408203, -0.27151989936828613, 0.5095357894897461)

    bone_frames = vmd.get_frames('bones')
    new_frames = []
    for frame in bone_frames:
        if frame.frame != 1036:
            new_frames.append(frame)
        else:
            bone_name = vmdutil.b_to_str(frame.name)
            if bone_name == 'センター':
                continue
            elif bone_name == '右腕':
                new_frames.append(frame._replace(
                    rotation=ra_1036_rot))
            elif bone_name == '右ひじ':
                new_frames.append(frame._replace(
                    rotation=re_1036_rot))
            else:
                new_frames.append(frame)
    new_frames.append(c_1032)
    new_frames.append(ra_1032)
    new_frames.append(re_1032)
    vmd.set_frames('bones', new_frames)
    return

def avoid_collision2(vmd):
    modify = {
    1317: {
        '右ひじ':((0.0, 0.0, 0.0), (0.5303139090538025, -0.5535628199577332, 0.12653225660324097, 0.6295421719551086))},
    1322: {
        '右腕': ((0.0, 0.0, 0.0), (0.25283217430114746, 0.24778856337070465, -0.011708247475326061, 0.9351678490638733)),
        '右ひじ': ((0.0, 0.0, 0.0), (0.5284314155578613, -0.5674738883972168, 0.11908495426177979, 0.6201204061508179))},
    1330: {
        'センター': ((1.5169070959091187, -0.11587631702423096, 3.358367443084717), (0.0, -0.0, -0.0, 1.0)),
        '右腕': ((0.0, 0.0, 0.0), (0.20906804502010345, 0.13286317884922028, 0.27482205629348755, 0.9290382266044617)),
        '右ひじ': ((0.0, 0.0, 0.0), (0.6034250259399414, -0.5745618939399719, -0.04226955026388168, 0.5513404607772827))},
    1333: {
        '右ひじ': ((0.0, 0.0, 0.0), (0.6193941831588745, -0.5532808899879456, -0.14503660798072815, 0.5377723574638367))},
    1339: {
        'センター': ((2.3029496669769287, 0.0, 1.9691747426986694), (0.0, -0.0, -0.0, 1.0)),
        '右腕': ((0.0, 0.0, 0.0), (0.18227244913578033, 0.19123366475105286, 0.2656165361404419, 0.9271727800369263)),
        '右ひじ': ((0.0, 0.0, 0.0), (0.574394702911377, -0.5680624842643738, -0.36492064595222473, 0.4628258943557739))},
    1342: {
        '右ひじ': ((0.0, 0.0, 0.0), (0.574394702911377, -0.5680624842643738, -0.36492064595222473, 0.4628258943557739))},
    1346: {
        'センター': ((3.0592546463012695, 0.0, 0.2976529598236084), (0.0, -0.0, -0.0, 1.0)),
        '右腕': ((0.0, 0.0, 0.0), (0.1709841787815094, 0.2831650674343109, 0.12234087288379669, 0.9357418417930603)),
        '右ひじ': ((0.0, 0.0, 0.0), (0.6452091336250305, -0.5575323700904846, -0.011836055666208267, 0.5222232341766357))}
    }
    bone_frames = vmd.get_frames('bones')
    for i, frame in enumerate(bone_frames):
        bone_name = vmdutil.b_to_str(frame.name)
        if frame.frame in modify:
            if bone_name in modify[frame.frame]:
                pos, rot = modify[frame.frame][bone_name]
                bone_frames[i] = frame._replace(
                    position=pos, rotation=rot)
    return


if __name__ == '__main__':
    vmd_name = sys.argv[1]
    vmd = vmdutil.Vmdio()
    vmd.load(vmd_name)
    avoid_collision1(vmd)
    avoid_collision2(vmd)
    vmd.store(vmd_name)
