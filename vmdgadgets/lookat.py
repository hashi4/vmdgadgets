import sys
import math
import heapq
import copy
import vmdutil
from collections import namedtuple
from vmdutil import vmddef
from vmdutil import pmxutil
from vmdutil import pmxdef


class PriorityQueue():
    def __init__(self):
        self.items = set()
        self.queue = []

    def push(self, n):
        heapq.heappush(self.queue, n)
        return

    def pop(self):
        if len(self.queue) > 0:
            r = heapq.heappop(self.queue)
            return r
        else:
            return None

    def top(self):
        return self.queue[0] if len(self.queue) > 0 else None


def get_global_transform(
        this_transform, this_bone_def,
        parent_transform, parent_bone_def, parent_global):
    bone_vector = vmdutil.sub_v(
        vmdutil.add_v(this_bone_def.position, this_transform[1]),
        parent_bone_def.position)
    this_global_pos = vmdutil.add_v(
        parent_global[1],
        vmdutil.rotate_v3q(bone_vector, parent_global[0]))
    this_global_rot = vmdutil.multiply_quaternion(
        this_transform[0], parent_global[0])
    return this_global_rot, this_global_pos


def replace_bonedef_position(bone1, bone2, axis):
    new_position = []
    for index in range(len(bone1.position)):
        if index in axis:
            new_position.append(bone2.position[index])
        else:
            new_position.append(bone1.position[index])
    new_position = tuple(new_position)
    return bone1._replace(position=new_position)


MotionFrame = namedtuple('MotionFrame', 'frame_no type model_id bone_name')


class LookAt():
    def __init__(self, watcher_pmx_name, watcher_vmd_name):
        self.watcher_pmx_name = watcher_pmx_name
        self.watcher_vmd_name = watcher_vmd_name
        self.target_pos = (0, 0, 0)
        self.target_vmd_name = None
        self.target_pmx_name = None
        self.mode = 'FIXED'
        self.overwrite_bones = ['首', '頭', '両目']
        self.target_bone = '両目'
        self.target_bone_has_motion = False
        self.DEFAULT_CONTSTRAINT = [(179.0, 179.0, 179.0), (1, 1, .5)]
        self.constraints = {
            '首': [(10, 20, 10), (1, 1, .8)],
            '頭': [(30, 40, 20), (1, 1, .8)],
            '両目': [(20, 30, 0), (1, 1, 0)],
        }
        self.ignore_zone = math.radians(140)
        self.global_up = (0, 1, 0)
        self.omega_limit = math.pi / 40
        self.additional_frame_nos = []
        self.WATCHER = 0
        self.TARGET = 1
        self.bone_defs = {}
        self.bone_dict = {}
        self.frame_dict = {self.WATCHER: {}, self.TARGET: {}}
        self.sorted_keyframes = {self.WATCHER: {}, self.TARGET: {}}

    def set_target_pos(self, pos):
        self.target_pos = pos

    def set_target_vmd(self, vmd_name):
        self.target_vmd_name = vmd_name

    def set_target_pmx(self, pmx_name):
        self.target_pmx_name = pmx_name

    def set_overwrite_bones(self, bone_names, constraints=None):
        self.overwrite_bones = bone_names
        for bone_name in bone_names:
            if constraints and bone_name in constraints:
                self.constraints[bone_name] = constraints[bone_name]
            else:
                self.constraints[bone_name] = self.DEFAULT_CONTSTRAINT

    def set_target_bone(self, bone_name):
        self.target_bone = bone_name

    def set_omega_limit(self, limit):
        self.omega_limit = limit

    def set_ignore_zone(self, zone):
        self.ignore_zone = zone

    def set_constraint(self, bone_name, constraint):
        if bone_name in self.constraints:
            self.constraints[bone_name] = constraint

    def set_additional_frames(self, frame_nos):
        self.additional_frame_nos = frame_nos

    def add_frames(self, queue):
        for frame_no in self.additional_frame_nos:
            queue.push(MotionFrame(frame_no, 'u', -1, 'A'))

    def load(self):
        self.watcher_pmx = pmxutil.Pmxio()
        self.watcher_pmx.load(self.watcher_pmx_name)
        self.watcher_vmd = vmdutil.Vmdio()
        self.watcher_vmd.load(self.watcher_vmd_name)
        self.bone_defs[self.WATCHER] = self.watcher_pmx.get_elements('bones')
        self.watcher_motions = self.watcher_vmd.get_frames('bones')

        if self.target_vmd_name:
            self.target_vmd = vmdutil.Vmdio()
            self.target_vmd.load(self.target_vmd_name)
            if vmdutil.is_camera_header(self.target_vmd.header):
                self.mode = 'CAMERA'
                self.target_motions = self.target_vmd.get_frames('cameras')
            else:
                if not self.target_pmx_name:
                    raise Exception('pmx not setted')
                else:
                    self.target_pmx = pmxutil.Pmxio()
                    self.target_pmx.load(self.target_pmx_name)
                    self.mode = 'MODEL'
                    self.target_motions = self.target_vmd.get_frames('bones')
                    self.bone_defs[self.TARGET] = self.target_pmx.get_elements(
                        'bones')

    def setup_watcher(self, queue):
        bone_defs = self.bone_defs[self.WATCHER]
        self.bone_dict[self.WATCHER] = bone_dict = pmxutil.make_name_dict(
            bone_defs)
        if '両目' in self.overwrite_bones:
            bone_defs[bone_dict['両目']] = replace_bonedef_position(
                bone_defs[bone_dict['両目']],
                bone_defs[bone_dict['右目']], [1])
        self.constraints_rad = {
            bone_name:
            [math.radians(k) for k in self.constraints[bone_name][0]]
            for bone_name in self.overwrite_bones}
        leaf_index = -1
        # find leaf bone
        for b in self.overwrite_bones:
            if b in bone_dict:
                index = bone_dict[b]
                leaf_index = index if index > leaf_index else leaf_index
        if leaf_index == -1:
            raise Exception('bones to be overwritten are not in pmx.')
        transform_bones = pmxutil.make_bone_link(
            bone_defs, leaf_index, 0,
            criteria=lambda b: b.flag & pmxdef.BONE_CAN_ROTATE ==
            pmxdef.BONE_CAN_ROTATE)

        motion_dict = vmdutil.frames_to_dict(self.watcher_motions)
        motionname_dict = vmdutil.make_name_dict(motion_dict, decode=True)

        # (leaf-to-root AND vmd) OR overwrite
        transform_bonenames = set(
            [bone_defs[i].name_jp for i in transform_bones]).intersection(
                set(motionname_dict.keys())).union(
                set(self.overwrite_bones))
        # sort by transform order
        self.watcher_transform_bone_indexes = pmxutil.get_transform_order(
            [bone_dict[name] for name in transform_bonenames], bone_defs)

        self.frame_dict[self.WATCHER] = d = {}
        self.sorted_keyframes[self.WATCHER] = f = {}
        for bone_index in self.watcher_transform_bone_indexes:
            bone_def = bone_defs[bone_index]
            bone_name = bone_def.name_jp
            if bone_name not in self.overwrite_bones:
                d[bone_name] = {}
                f[bone_name] = (
                    [motion.frame for motion in motionname_dict[bone_name]])
                for motion in motionname_dict[bone_name]:
                    queue.push(MotionFrame(
                        motion.frame, 'b', self.WATCHER, bone_name))
                    d[bone_name][motion.frame] = motion
        return

    def setup_target(self, queue):
        if 'CAMERA' == self.mode:
            sorted_motions = sorted(self.target_motions, key=lambda e: e.frame)
            self.frame_dict[self.TARGET]['CAMERA'] = d = {}
            self.sorted_keyframes[self.TARGET]['CAMERA'] = (
                 [m.frame for m in sorted_motions])
            for i, motion in enumerate(sorted_motions):
                type = 'c' if (
                    i > 0 and
                    sorted_motions[i - 1].frame == motion.frame - 1) else 'v'
                queue.push(MotionFrame(
                    motion.frame, type, self.TARGET, 'CAMERA'))
                d[motion.frame] = motion
            return
        elif 'MODEL' == self.mode:
            bone_defs = self.bone_defs[self.TARGET]
            self.bone_dict[self.TARGET] = d = pmxutil.make_name_dict(bone_defs)
            if self.target_bone not in d:
                raise Exception('target bone is not in pmx.')
            target_index = d[self.target_bone]
            if self.target_bone == '両目':
                bone_defs[d['両目']] = replace_bonedef_position(
                bone_defs[d['両目']],
                bone_defs[d['右目']], [1, 2])
            # pmx
            transform_bones = pmxutil.make_bone_link(
                bone_defs, target_index, 0,
                criteria=lambda b: b.flag & pmxdef.BONE_CAN_ROTATE ==
                pmxdef.BONE_CAN_ROTATE)
            # vmd
            motion_dict = vmdutil.frames_to_dict(self.target_motions)
            motionname_dict = vmdutil.make_name_dict(motion_dict, decode=True)
            if self.target_bone not in motionname_dict:
                motionname_dict[self.target_bone] = []
            else:
                self.target_bone_has_motion = True

            # (pmx AND vmd) OR look_target
            transform_bonenames = set(
                [bone_defs[i].name_jp
                    for i in transform_bones]).intersection(
                    set(motionname_dict.keys())).union(
                    set([self.target_bone]))

            self.target_transform_bone_indexes = pmxutil.get_transform_order(
                [d[name] for name in transform_bonenames], bone_defs)

            for bone_index in self.target_transform_bone_indexes:
                bone_def = bone_defs[bone_index]
                bone_name = bone_def.name_jp
                self.frame_dict[self.TARGET][bone_name] = d = {}
                self.sorted_keyframes[self.TARGET][bone_name] = (
                    [motion.frame for motion in motionname_dict[bone_name]])
                for motion in motionname_dict[bone_name]:
                    queue.push(
                        MotionFrame(motion.frame, 'b', self.TARGET, bone_name))
                    d[motion.frame] = motion
            return

    def get_vmd_transform(self, frame_no, bone_name, model_id, frame_pos):
        frame_dict = self.frame_dict[model_id][bone_name]
        key_frames = self.sorted_keyframes[model_id][bone_name]
        bone_def_id = self.bone_dict[model_id][bone_name]
        bone_def = self.bone_defs[model_id][bone_def_id]
        if frame_no in key_frames:
            m = frame_dict[frame_no]
            rotation = m.rotation
            position = m.position
        else:
            current = frame_pos[bone_name]
            begin = frame_dict[key_frames[current]]
            if current < len(key_frames) - 1:
                end = frame_dict[key_frames[current + 1]]
                if (bone_def.flag & pmxdef.BONE_CAN_TRANSLATE ==
                   pmxdef.BONE_CAN_TRANSLATE):
                    position = vmdutil.interpolate_position(
                        frame_no, begin, end, 'bones')
                else:
                    position = [0, 0, 0]
                if (bone_def.flag & pmxdef.BONE_CAN_ROTATE ==
                        pmxdef.BONE_CAN_ROTATE):
                    rotation = vmdutil.interpolate_rotation(
                        frame_no, begin, end, 'bones')
                else:
                    rotation = vmdutil.QUATERNION_IDENTITY
            else:
                rotation = begin.rotation
                position = begin.position
        return rotation, position

    def get_camera_pos(self, position, rotation, distance):
        direction = vmdutil.camera_direction(rotation, distance)
        return vmdutil.add_v(position, direction)

    def get_target_camera_pos(self, frame_no, frame_pos):
            frame_dict = self.frame_dict[self.TARGET]['CAMERA']
            key_frames = self.sorted_keyframes[self.TARGET]['CAMERA']
            if frame_no in key_frames:
                m = frame_dict[frame_no]
                pos = self.get_camera_pos(
                    m.position, m.rotation, m.distance)
            else:
                current = frame_pos['CAMERA']
                begin = frame_dict[key_frames[current]]
                if current < len(key_frames) - 1:
                    end = frame_dict[key_frames[current + 1]]
                    position = vmdutil.interpolate_position(
                        frame_no, begin, end, 'cameras')
                    rotation = vmdutil.interpolate_rotation(
                        frame_no, begin, end, 'cameras')
                    distance = vmdutil.interpolate_camera_distance(
                        frame_no, begin, end)
                    pos = self.get_camera_pos(position, rotation, distance)
                else:
                    pos = self.get_camera_pos(
                        begin.position, begin.rotation, begin.distance)
            return pos

    def get_target_model_pos(self, frame_no, frame_pos):
        vmd_transforms = {}
        global_transforms = {}
        bone_defs = self.bone_defs[self.TARGET]
        for loop_i, bone_index in enumerate(self.target_transform_bone_indexes):
            # vmd transform
            bone_def = bone_defs[bone_index]
            bone_name = bone_def.name_jp
            rotation, position = self.get_vmd_transform(
                frame_no, bone_name, self.TARGET, frame_pos)
            vmd_transforms[bone_name] = (rotation, position)
            # global transform
            if loop_i == 0:  # root
                global_transforms[bone_name] = (
                    vmd_transforms[bone_name][0],
                    vmdutil.add_v(bone_def.position, position))
            else:
                parent_index = self.target_transform_bone_indexes[loop_i - 1]
                parent_name = (
                    self.bone_defs[self.TARGET][parent_index].name_jp)
                parent_vmd = vmd_transforms[parent_name]
                parent_bone_def = self.bone_defs[self.TARGET][parent_index]
                global_transforms[bone_name] = get_global_transform(
                    vmd_transforms[bone_name], bone_def,
                    vmd_transforms[parent_name], parent_bone_def,
                    global_transforms[parent_name])
        return global_transforms[self.target_bone][1]  # position

    def get_target_pos(self, frame_no, frame_pos):
        if 'FIXED' == self.mode:
            return self.target_pos
        elif 'CAMERA' == self.mode:
            return self.get_target_camera_pos(frame_no, frame_pos)
        elif 'MODEL' == self.mode:
            return self.get_target_model_pos(frame_no, frame_pos)

    def arrange_first_frame(self, first_frame):
        for index in [self.WATCHER, self.TARGET]:
            for bone_name in self.frame_dict[index]:
                d = self.frame_dict[index][bone_name]
                k = self.sorted_keyframes[index][bone_name]
                if len(k) == 0:  # target_bone
                    d[first_frame] = vmddef.BONE_SAMPLE._replace(
                        name=bone_name, frame=first_frame)
                    k.append(first_frame)
                if first_frame != k[0]:
                    d[first_frame] = d[
                        self.first_frames[index][bone_name]]._replace(
                        frame=first_frame)
                    k.insert(0, first_frame)

    def check_ignore_case(self, body_dir, look_dir):
        if self.ignore_zone <= 0:
            return False
        body_dir_y = vmdutil.project_to_plane_v(
            body_dir, self.global_up)
        look_dir_y = vmdutil.project_to_plane_v(
            look_dir, self.global_up)
        angle_around_y = vmdutil.angle_v(
            body_dir_y, look_dir_y)
        return angle_around_y > self.ignore_zone

    def set_constraints(self, bone_name, turn):
        constraint = self.constraints[bone_name]
        constraint_rad = self.constraints_rad[bone_name]
        turn = [k * j for k, j in zip(turn, constraint[1])]
        turn = [vmdutil.clamp(turn[i],
                -constraint_rad[i], constraint_rad[i])
                for i in range(len(turn))]
        return turn

    def make_look_at_frames(self, frame_no, target_pos, frame_pos):
        vmd_transforms = {}
        global_transforms = {}
        overwrite_frames = list()
        bone_defs = self.bone_defs[self.WATCHER]
        for loop_i, bone_index in enumerate(
                self.watcher_transform_bone_indexes):
            bone_def = bone_defs[bone_index]
            bone_name = bone_def.name_jp
            # vmd
            if bone_name not in self.overwrite_bones:
                rotation, position = self.get_vmd_transform(
                    frame_no, bone_name, self.WATCHER, frame_pos)
                vmd_transforms[bone_name] = (rotation, position)
            else:  # overwrite
                vmd_transforms[bone_name] = (
                    vmdutil.QUATERNION_IDENTITY, [0, 0, 0])
            # global position, rotation
            if loop_i == 0:  # root
                global_transforms[bone_name] = (
                    vmd_transforms[bone_name][0],
                    vmdutil.add_v(bone_def.position, position))
            else:
                parent_index = self.watcher_transform_bone_indexes[loop_i - 1]
                parent_name = (
                    self.bone_defs[self.WATCHER][parent_index].name_jp)
                parent_vmd = vmd_transforms[parent_name]
                parent_bone_def = self.bone_defs[self.WATCHER][parent_index]
                global_transforms[bone_name] = get_global_transform(
                    vmd_transforms[bone_name], bone_def,
                    vmd_transforms[parent_name], parent_bone_def,
                    global_transforms[parent_name])
                if bone_name in self.overwrite_bones:
                    base_dir = vmdutil.rotate_v3q(
                        (0, 0, -1),
                        global_transforms[parent_name][0])
                    up = vmdutil.rotate_v3q(
                        (0, 1, 0),
                        global_transforms[parent_name][0])
                    neck_pos = global_transforms[bone_name][1]
                    look_dir = vmdutil.sub_v(target_pos, neck_pos)

                    if self.check_ignore_case(base_dir, look_dir):
                        return []

                    turn = vmdutil.look_at(
                        base_dir, up, look_dir, self.global_up)
                    turn = self.set_constraints(bone_name, turn)
                    hrot = tuple(vmdutil.euler_to_quaternion(turn))
                    vmd_transforms[bone_name] = (hrot, (0, 0, 0))
                    global_transforms[bone_name] = get_global_transform(
                        vmd_transforms[bone_name], bone_def,
                        vmd_transforms[parent_name], parent_bone_def,
                        global_transforms[parent_name])

                    overwrite_frames.append(vmddef.BONE_SAMPLE._replace(
                        frame=frame_no,
                        name=bone_name.encode(vmddef.ENCODING),
                        rotation=hrot))
        return overwrite_frames

    def camera_delay(
            self, frame_no, frame_type, overwrite_frames,
            queue, prev, frame_pos):
        if prev['frame_no'] < 0:
            return overwrite_frames

        if 'c' in frame_type:
            maxrot = max(
                [math.acos(vmdutil.clamp(vmdutil.diff_q(
                    motion.rotation, prev['frames'][motion.name].rotation)[3],
                    -1, 1))
                    for motion in overwrite_frames])

            omega = maxrot / (frame_no - prev['frame_no'])
            if omega > self.omega_limit:
                delay_to = math.ceil(maxrot / self.omega_limit) + frame_no
                while True:
                    peek = queue.top()
                    if delay_to <= peek.frame_no:
                        break
                    if False:
                        pass
#                    if 'c' in peek.type or 'v' in peek.type:
#                        t = self.omega_limit * (peek.frame_no - frame_no) / 3
#                        scaled = [
#                            frame._replace(
#                                frame = peek.frame_no - 1,
#                                rotation=tuple(vmdutil.scale_q(
#                                    frame.rotation, t)))
#                            for frame in overwrite_frames]
#                        return scaled
                    else:
                        pop = queue.pop()
                        if pop.model_id >= 0:
                            frame_pos[pop.model_id][pop.bone_name] += 1
                queue.push(MotionFrame(delay_to, 'r', -1, 'DELAY'))
                return []
            else:
                return overwrite_frames
        else:
            return overwrite_frames

    def look_at(self):
        self.load()
        queue = PriorityQueue()
        self.setup_watcher(queue)
        self.setup_target(queue)
        if len(self.additional_frame_nos):
            self.add_frames(queue)
        first_frame = queue.top().frame_no
        self.arrange_first_frame(first_frame)
        new_frames = list()
        prev_overwrites = {'frame_no': -1, 'frames': []}
        frame_pos = {self.WATCHER: {}, self.TARGET: {}}
        for index in [self.WATCHER, self.TARGET]:
            frame_pos[index] = {
                bone_name: -1 for bone_name in self.sorted_keyframes[index]}
        if not self.target_bone_has_motion:
            frame_pos[self.TARGET][self.target_bone] = 0
        while True:
            motion_frame = queue.pop()
            if motion_frame is None:
                break
            frame_no = motion_frame.frame_no
            frame_type = motion_frame.type
            if motion_frame.model_id >= 0:
                frame_pos[motion_frame.model_id][motion_frame.bone_name] += 1
            while queue.top() is not None and queue.top().frame_no == frame_no:
                dummy = queue.pop()
                frame_type += dummy.type
                if dummy.model_id >= 0:
                    frame_pos[dummy.model_id][dummy.bone_name] += 1
            target_pos = self.get_target_pos(frame_no, frame_pos[self.TARGET])
            overwrite_frames = self.make_look_at_frames(
                    frame_no, target_pos, frame_pos[self.WATCHER])
            if len(overwrite_frames) == 0:
                continue
            if 'CAMERA' == self.mode and self.omega_limit > 0:
                overwrite_frames = self.camera_delay(
                    frame_no, frame_type, overwrite_frames,
                    queue, prev_overwrites, frame_pos)
            if len(overwrite_frames) > 0:
                prev_overwrites['frame_no'] = frame_no
                prev_overwrites['frames'] = {
                    frame.name: frame for frame in overwrite_frames}
            new_frames.extend(overwrite_frames)
        return new_frames

if __name__ == '__main__':
    print('use trace_camera.py or trace_model.py.')
