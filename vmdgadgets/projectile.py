import math
import numpy as np
import os

import vmdutil
from vmdutil import vmddef
from lookat import LookAt, MotionFrame

FPS = 30
MIXEL = 0.08
G = -9.8 / MIXEL / FPS / FPS
GV = (0, G, 0)  # fixed
HALFG = G / 2


def project_asap(pos_target, v_target, v_bullet):
    # ||pos + v_t * t - 1/2gt**2|| = v_b * t
    g = vmdutil.scale_v(GV, -1)
    a = vmdutil.dot_v(g, g) * 0.25  # TODO constant
    b = vmdutil.dot_v(v_target, g)
    c = (vmdutil.dot_v(pos_target, g) + vmdutil.dot_v(v_target, v_target) -
         v_bullet ** 2)
    d = vmdutil.dot_v(pos_target, v_target) * 2
    e = vmdutil.dot_v(pos_target, pos_target)
    coeff = [a, b, c, d, e]
    roots = np.roots(coeff)
    roots = sorted([i for i in roots if np.isreal(i) and i > 0])  # TODO + 0j
    if len(roots) == 0:  # TODO (differential() == 0) & ((-) -> (+))
        print('no positive real root')  # TODO
        return None
    t = roots[0]
    collision_pos = vmdutil.add_v(pos_target, [t * i for i in v_target])
    vx = collision_pos[0] / t
    vz = collision_pos[2] / t
    vy = math.sqrt(v_bullet * v_bullet - vx * vx - vz * vz)
    return (vx, vy, vz), t, collision_pos


def project_ontime(pos_target, v_target, t):
    vx, vy, vz = v_target
    px, py, pz = pos_target
    # vy*t + 1/2*g*t*t = py
    vy = py / t - HALFG * t
    vx = px / t
    vz = pz / t
    collision_pos = vmdutil.add_v(pos_target, [t * i for i in v_target])
    return (vx, vy, vz), t, collision_pos


def replace_controlpoints(cp_all, cp, index):
    for i in range(4):
        cp_all[i][index] = cp[i]
    return cp_all


cp_all = vmddef.BONE_LERP_CONTROLPOINTS
replace_controlpoints(cp_all, vmdutil.PARABOLA2_CONTROLPOINTS, 1)
PARABOLA2 = vmddef.bone_controlpoints_to_vmdformat(cp_all)
replace_controlpoints(cp_all, vmdutil.PARABOLA1_CONTROLPOINTS, 1)
PARABOLA1 = vmddef.bone_controlpoints_to_vmdformat(cp_all)


def extreme_value(pos, v):  # 2nd order
    # vy + gt = 0
    t = -v[1] / G
    posx = pos[0] + t * v[0]
    posz = pos[2] + t * v[2]
    posy = pos[1] + t * v[1] + HALFG * t * t
    return t, (posx, posy, posz)


class Projectile(LookAt):
    def __init__(self, watcher_pmx_name, watcher_vmd_name):
        LookAt.__init__(self, watcher_pmx_name, watcher_vmd_name)
        self.initial_velocity = 8
        self.collision_time = 60  # frames
        self.fire_frames = list()
        self.export_showik = False
        self.bullets_dir = '.'
        self.tracking_mode = 'L'  # 'P', 'F'  TODO
        self.projection_mode = 'A'  # 'T' TODO

    def set_tracking_mode(self, tracking_mode):
        self.tracking_mode = tracking_mode

    def set_projection_mode(self, projection_mode):
        self.projection_mode = projection_mode

    def set_fire_frames(self, frame_nos):
        self.fire_frames = frame_nos

    def add_frames(self, queue):
        LookAt.add_frames(self, queue)
        for frame in self.fire_frames:
            # TODO specify bone
            queue.push(MotionFrame(frame, 'f', -1, 'A'))

    def get_arm_rotation(
            self, frame_type, frame_no, bone_index, parent_index,
            watcher_v, watcher_dir, watcher_pos, axis, up,
            target_v, target_pos):
        # TODO
        if 'f' in frame_type:
            return self.get_projectile_arm_rotation(
                frame_type, frame_no, bone_index, parent_index,
                watcher_v, watcher_dir, watcher_pos, axis, up,
                target_v, target_pos)
        else:
            if self.tracking_mode == 'L':
                return LookAt.get_arm_rotation(
                    self, frame_type, frame_no, bone_index, parent_index,
                    watcher_v, watcher_dir, watcher_pos, axis, up,
                    target_v, target_pos)
            elif self.tracking_mode == 'P':
                return self.get_projectile_arm_rotation(
                    frame_type, frame_no, bone_index, parent_index,
                    watcher_v, watcher_dir, watcher_pos, axis, up,
                    target_v, target_pos)

    def get_projectile_arm_rotation(
            self, frame_type, frame_no, bone_index, parent_index,
            watcher_v, watcher_dir, watcher_pos, axis, up,
            target_v, target_pos):
        look_dir = vmdutil.sub_v(target_pos, watcher_pos)
        relative_v = vmdutil.sub_v(target_v, watcher_v)
        if self.projection_mode == 'A':
            p = project_asap(look_dir, relative_v, self.initial_velocity)
        else:
            p = project_ontime(look_dir, relative_v, self.collision_time)
        if p is None:
            return vmdutil.QUATERNION_IDENTITY
        else:
            v, t, c_pos = p
        angle = vmdutil.look_at_fixed_axis(
            watcher_dir, up, vmdutil.normalize_v(v))
        hrot = tuple(vmdutil.quaternion(axis, angle))
        if (bone_index in self.watcher_transform.leaf_indexes and
           'f' in frame_type):
            self.export_bullet_motion(
                frame_no, bone_index, watcher_pos, v, t, c_pos)
        return hrot

    def export_bullet_motion(
            self, frame_no, bone_index,
            from_pos, bullet_v, collision_time, collision_pos):
        vx, vy, vz = bullet_v
        bone_defs = self.watcher_transform.bone_defs
        bone_def = bone_defs[bone_index]
        bone_name = bone_def.name_jp
        extreme_time, extreme_pos = extreme_value(from_pos, bullet_v)
        if extreme_time > 0:  # vy > 0
            b_bone = 'センター'.encode(vmddef.ENCODING)
            frame0 = vmddef.BONE_SAMPLE._replace(
                name=b_bone, frame=frame_no,
                position=tuple(from_pos))
            end_frame = math.ceil(frame_no + extreme_time)
            frame1 = frame0._replace(
                frame=end_frame,
                position=tuple(extreme_pos), interpolation=PARABOLA2)
            bullet_frames = [frame0, frame1]
            if collision_time > extreme_time:
                collision_pos = tuple(vmdutil.add_v(
                    from_pos, collision_pos))
                end_frame = math.ceil(frame_no + collision_time)
                frame2 = frame0._replace(
                    frame=end_frame,
                    position=tuple(collision_pos),
                    interpolation=PARABOLA1)
                bullet_frames.append(frame2)
            vmd_name = '{0}_{1}_{2}.vmd'.format(
                bone_name, frame_no, math.ceil(frame_no + collision_time))
            vmdo = vmdutil.Vmdio()
            vmdo.set_frames('bones', bullet_frames)
            if self.export_showik is True:
                ik_frame0 = vmddef.showik(
                    frame_no, 1, 0, ())
                ik_frame1 = ik_frame0._replace(
                    frame=end_frame + 1, show=0)
                vmdo.set_frames('showiks', [ik_frame0, ik_frame1])
            vmdo.store(os.path.join(self.bullets_dir, vmd_name))
            del vmdo
        else:
            pass  # TODO angles of depression
        return
