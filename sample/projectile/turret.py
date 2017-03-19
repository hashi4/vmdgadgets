import sys
import re
import glob
import os
from concurrent import futures
sys.path.append('../../vmdgadgets')

import vmdutil
import lookat
import bismark

PUL = 'PU主砲_砲身_L先'
PUU = 'PU主砲_砲身_U先'
SUL = 'SU主砲_砲身_L先'
SUU = 'SU主砲_砲身_U先'
PLL = 'PL主砲_砲身_L先'
PLU = 'PL主砲_砲身_U先'
SLL = 'SL主砲_砲身_L先'
SLU = 'SL主砲_砲身_U先'

# frame, target
SEQ1_RANGE = (1, 250)  # camera
SEQ2_RANGE = (400, 1250)  # drone
SEQ3_RANGE = (1351, 9999)
SEQ1_FIRE_FRAMES = {PUL: [110],
                    PUU: [110],
                    SUL: [250],
                    SUU: [250],
                    PLL: [400],
                    PLU: [400],
                    SLL: [400],
                    SLU: [400], }
RELOAD = 60  # TODO reload_time < collision_time
SEQ2_UPPER_P = [460] + [i for i in range(570, 1251, RELOAD)]
SEQ2_UPPER_S = [460] + [i for i in range(585, 1251, RELOAD)]
SEQ2_LOWER_P = [400] + [i for i in range(600, 1251, RELOAD)]
SEQ2_LOWER_S = [400] + [i for i in range(615, 1251, RELOAD)]
SEQ2_FIRE_FRAMES = {PUL: SEQ2_UPPER_P,
                    PUU: SEQ2_UPPER_P,
                    SUL: SEQ2_UPPER_S,
                    SUU: SEQ2_UPPER_S,
                    PLL: SEQ2_LOWER_P,
                    PLU: SEQ2_LOWER_P,
                    SLL: SEQ2_LOWER_S,
                    SLU: SEQ2_LOWER_S}
SEQ3_FIRE_FRAMES = {PUL: [1410],
                    PUU: [1410],
                    SUL: [1410],
                    SUU: [1410],
                    PLL: [],
                    PLU: [],
                    SLL: [],
                    SLU: []}
ALL_FIRE_FRAMES = set()
for frames in SEQ1_FIRE_FRAMES.values():
    ALL_FIRE_FRAMES = ALL_FIRE_FRAMES.union(set(frames))
for frames in SEQ2_FIRE_FRAMES.values():
    ALL_FIRE_FRAMES = ALL_FIRE_FRAMES.union(set(frames))
for frames in SEQ3_FIRE_FRAMES.values():
    ALL_FIRE_FRAMES = ALL_FIRE_FRAMES.union(set(frames))

RE = re.compile('(^.*)_([0-9]+)_.*')

BISMARK = 'model\\bismark_renamed.pmx'
GUNNER = 'motion\\gunner.vmd'
CAMERA = 'motion\\camera.vmd'
DRONE_MODEL = 'model\\drone.pmx'
DRONE_MOTION = 'motion\\drone.vmd'
BULLETS_DIR = 'motion\\bullets'


def concat_bullet_frames():
    vmds = glob.glob(r'motion\bullets\*.vmd')
    vmd_frames = {PUL: {'bones': [], 'showiks': []},
                  PUU: {'bones': [], 'showiks': []},
                  SUL: {'bones': [], 'showiks': []},
                  SUU: {'bones': [], 'showiks': []},
                  PLL: {'bones': [], 'showiks': []},
                  PLU: {'bones': [], 'showiks': []},
                  SLL: {'bones': [], 'showiks': []},
                  SLU: {'bones': [], 'showiks': []}}

    def in_fire_frames(bone_name, frame_no):
        for fire_frames in [
                SEQ1_FIRE_FRAMES, SEQ2_FIRE_FRAMES, SEQ3_FIRE_FRAMES]:
            if bone_name in fire_frames and frame_no in fire_frames[bone_name]:
                return True
        return False

    for vmd in vmds:
        o = RE.match(vmd)
        if o is not None:
            vmdfile, frame = o.groups()
            bone = os.path.basename(vmdfile)
            frame = int(frame)
            if in_fire_frames(bone, frame):
                vmdin = vmdutil.Vmdio()
                vmdin.load(vmd)
                motion_frames = vmdin.get_frames('bones')
                vmd_frames[bone]['bones'].extend(motion_frames)
                iks = vmdin.get_frames('showiks')
                vmd_frames[bone]['showiks'].extend(iks)
                del vmdin
    for bone in vmd_frames:
        if len(vmd_frames[bone]['bones']) > 0:
            vmdout = vmdutil.Vmdio()
            vmdout.set_frames('bones', vmd_frames[bone]['bones'])
            vmdout.set_frames('showiks', vmd_frames[bone]['showiks'])
            vmdout.store('motion\\' + bone + '.vmd')


def upper_to_camera_seq1():
    s1 = bismark.BismarkUpper(
        BISMARK, GUNNER)
    s1.export_showik = True
    s1.set_target_vmd(CAMERA)
    s1.set_fire_frames(ALL_FIRE_FRAMES)
    s1.set_additional_frames([120])
    s1.set_frame_range([SEQ1_RANGE])
    s1.bullets_dir = BULLETS_DIR
    frames = s1.look_at()
    return frames


def upper_to_drone_seq2():
    s1 = bismark.BismarkUpper(BISMARK, GUNNER)
    s1.export_showik = True
    s1.set_target_pmx(DRONE_MODEL)
    s1.set_target_vmd(DRONE_MOTION)
    s1.set_target_bone('センター')
    s1.initial_velocity = 10
    s1.set_fire_frames(ALL_FIRE_FRAMES)
    s1.set_tracking_mode('P')
    s1.set_additional_frames([1350])
    s1.set_frame_range([SEQ2_RANGE])
    s1.bullets_dir = BULLETS_DIR
    frames = s1.look_at()
    return frames


def lower_to_drone_seq2():
    s1 = bismark.BismarkLower(BISMARK, GUNNER)
    s1.export_showik = True
    s1.set_target_pmx(DRONE_MODEL)
    s1.set_target_vmd(DRONE_MOTION)
    s1.set_target_bone('センター')
    s1.initial_velocity = 10
    s1.set_fire_frames(ALL_FIRE_FRAMES)
    s1.set_tracking_mode('P')
    s1.set_additional_frames([1350])
    s1.set_frame_range([SEQ2_RANGE])
    s1.bullets_dir = BULLETS_DIR
    frames = s1.look_at()
    return frames


def upper_to_camera_seq3():
    s1 = bismark.BismarkUpper(BISMARK, GUNNER)
    s1.export_showik = True
    s1.set_target_vmd(CAMERA)
    s1.collision_time = 120
    s1.set_fire_frames(ALL_FIRE_FRAMES)
    s1.set_tracking_mode('P')
    s1.set_projection_mode('T')
    s1.set_frame_range([SEQ3_RANGE])
    s1.bullets_dir = BULLETS_DIR
    frames = s1.look_at()
    return frames


def turret_and_face():
    tasks = [upper_to_camera_seq1, upper_to_drone_seq2, lower_to_drone_seq2,
             upper_to_camera_seq3]
    executor = futures.ProcessPoolExecutor()
    future_list = [executor.submit(task) for task in tasks]

    face1 = executor.submit(face_camera)
    face2 = executor.submit(face_drone)

    turret_frames = []
    for future in futures.as_completed(future_list):
        turret_frames.extend(future.result())
    vmdout = vmdutil.Vmdio()
    vmdout.set_frames('bones', turret_frames)
    vmdout.store('motion\\turret.vmd')
    del vmdout

    face_frames = face1.result()
    face_frames.extend(face2.result())
    vmdout = vmdutil.Vmdio()
    vmdout.set_frames('bones', face_frames)
    vmdout.store('motion\\face.vmd')
    del vmdout


def face_camera():
    s1 = lookat.LookAt(BISMARK, GUNNER)
    s1.set_target_vmd(CAMERA)
    s1.set_constraint('両目', [(20, 30, 0), (0.1, 0.1, 0)])
    s1.set_additional_frames([120])
    s1.set_frame_range([SEQ1_RANGE, (1251, 1350)])
    frames = s1.look_at()
    return frames


def face_drone():
    s2 = lookat.LookAt(BISMARK, GUNNER)
    s2.set_target_pmx(DRONE_MODEL)
    s2.set_target_vmd(DRONE_MOTION)
    s2.set_target_bone('センター')
    s2.set_additional_frames([350, 1250])
    s2.set_frame_range([SEQ2_RANGE])
    return s2.look_at()


def clean():
    vmds = glob.glob('motion\\bullets\\*.vmd')
    for vmd in vmds:
        os.unlink(vmd)


if __name__ == '__main__':
    if not os.path.exists(BULLETS_DIR):
        os.mkdir(BULLETS_DIR)

    clean()
    turret_and_face()
    concat_bullet_frames()
