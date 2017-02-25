import sys
import math
import heapq
import bisect
import vmdutil
from collections import namedtuple
from vmdutil import vmddef
from vmdutil import pmxutil
from vmdutil import pmxdef

FRAME_MIN = 0
FRAME_MAX = 4294967295  # UINT32_MAX


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


class FrameRange():
    def __init__(self, frame_ranges=None):
        self.frame_ranges = frame_ranges
        if frame_ranges is not None:
            self.min_frame = min([r[0] for r in frame_ranges])
            self.max_frame = max([r[1] for r in frame_ranges])
        else:
            self.min_frame = 0
            self.max_frame = FRAME_MAX

    def is_in_range(self, frame_no):
        if self.frame_ranges is None:
            return True
        for r in self.frame_ranges:
            if r[0] <= frame_no <= r[1]:
                return True
        return False

    def is_over_max(self, frame_no):
        if self.frame_ranges is None:
            return False
        return True if frame_no > self.max_frame else False


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
        self.frame_range = FrameRange()
        self.target_vmd_name = None
        self.target_pmx_name = None
        self.target_mode = 'FIXED'
        self.point_mode = 'FACE'
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
        self.motion_name_dict = {self.WATCHER: {}, self.TARGET: {}}

    def set_target_pos(self, pos):
        self.target_pos = pos

    def set_target_vmd(self, vmd_name):
        self.target_vmd_name = vmd_name

    def set_target_pmx(self, pmx_name):
        self.target_pmx_name = pmx_name

    def set_point_mode(self, mode='FACE'):
        self.point_mode = mode

    def set_overwrite_bones(self, bone_names, constraints=None):
        self.overwrite_bones = bone_names
        for bone_name in bone_names:
            if constraints and bone_name in constraints:
                self.constraints[bone_name] = constraints[bone_name]
            else:
                self.constraints[bone_name] = self.DEFAULT_CONTSTRAINT

    def set_target_bone(self, bone_name):
        self.target_bone = bone_name

    def set_frame_range(self, frame_ranges):
        self.frame_range = FrameRange(frame_ranges)

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
                self.target_mode = 'CAMERA'
                self.target_motions = self.target_vmd.get_frames('cameras')
            else:
                if not self.target_pmx_name:
                    raise Exception('pmx not setted')
                else:
                    self.target_pmx = pmxutil.Pmxio()
                    self.target_pmx.load(self.target_pmx_name)
                    self.target_mode = 'MODEL'
                    self.target_motions = self.target_vmd.get_frames('bones')
                    self.bone_defs[self.TARGET] = self.target_pmx.get_elements(
                        'bones')

    def check_bones(self, bone_names, bone_dict):
        for name in bone_names:
            if name not in bone_dict:
                return False
        return True

    def make_arm_dir(self):
        base_dirs = {}
        leaf_indexes = self.watcher_leaves
        overwrite_indexes = [
            self.bone_dict[self.WATCHER][name]
            for name in self.overwrite_bones]
        graph = self.watcher_bone_graph
        leaves = sorted(leaf_indexes, reverse=True)
        bone_defs = self.bone_defs[self.WATCHER]

        for leaf_index in leaf_indexes:
            base_dirs[leaf_index] = (0, 0, -1)
            degree = graph.in_degree(leaf_index)
            parent_index = next(iter(graph.preds[leaf_index]))
            base_dir = vmdutil.sub_v(
                bone_defs[leaf_index].position,
                bone_defs[parent_index].position)
            while True:
                if parent_index in overwrite_indexes:
                    base_dirs[parent_index] = base_dir
                degree = graph.in_degree(parent_index)
                if degree <= 0:
                    break
                parent_index = next(iter(graph.preds[parent_index]))
        return base_dirs

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

        if not self.check_bones(self.overwrite_bones, bone_dict):
            raise Exception('bones to be overwritten are not in pmx.')

        # bone_graph
        overwrite_indexes = [bone_dict[name] for name in self.overwrite_bones]
        self.watcher_bone_graph = pmxutil.make_bone_link_graph(
            bone_defs, 0, overwrite_indexes)
        out_degrees = self.watcher_bone_graph.out_degree()
        self.watcher_leaves = [e[0] for e in out_degrees if e[1] == 0]

        # vmd
        motion_dict = vmdutil.frames_to_dict(self.watcher_motions)
        self.motion_name_dict[self.WATCHER] = vmdutil.make_name_dict(
            motion_dict, decode=True)

        # remove motionless nodes from graph
        transform_bones = [e[0] for e in out_degrees]
        for node_index in transform_bones:
            name = bone_defs[node_index].name_jp
            if (name not in self.motion_name_dict[self.WATCHER] and
                    name not in self.overwrite_bones):
                self.watcher_bone_graph.remove_node(node_index)
        transform_bones = [node for node in self.watcher_bone_graph.edges]
        transform_bonenames = [bone_defs[i].name_jp for i in transform_bones]

        # sort by transform order
        self.watcher_transform_bone_indexes = pmxutil.get_transform_order(
            [bone_dict[name] for name in transform_bonenames], bone_defs)
        self.watcher_transform_bone_names = [
            bone_defs[bone_index].name_jp for bone_index in
            self.watcher_transform_bone_indexes]

        # make dir
        if 'ARM' == self.point_mode:
            self.base_dirs = self.make_arm_dir()
        else:
            self.base_dirs = {}
            for index in overwrite_indexes:
                self.base_dirs[index] = (0, 0, -1)

        self.frame_dict[self.WATCHER] = d = {}
        self.sorted_keyframes[self.WATCHER] = f = {}
        for bone_index in self.watcher_transform_bone_indexes:
            bone_def = bone_defs[bone_index]
            bone_name = bone_def.name_jp
            if bone_name not in self.overwrite_bones:
                d[bone_name] = {}
                f[bone_name] = (
                    [motion.frame for motion in
                     self.motion_name_dict[self.WATCHER][bone_name]])
                for motion in self.motion_name_dict[self.WATCHER][bone_name]:
                    queue.push(MotionFrame(
                        motion.frame, 'b', self.WATCHER, bone_name))
                    d[bone_name][motion.frame] = motion
        return

    def setup_target(self, queue):
        if 'CAMERA' == self.target_mode:
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
        elif 'MODEL' == self.target_mode:
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
            self.motion_name_dict[self.TARGET] = vmdutil.make_name_dict(
                motion_dict, decode=True)
            if self.target_bone not in self.motion_name_dict[self.TARGET]:
                self.motion_name_dict[self.TARGET][self.target_bone] = []
            else:
                self.target_bone_has_motion = True

            # (pmx AND vmd) OR look_target
            transform_bonenames = set(
                [bone_defs[i].name_jp
                    for i in transform_bones]).intersection(
                    set(self.motion_name_dict[self.TARGET].keys())).union(
                    set([self.target_bone]))

            self.target_transform_bone_indexes = pmxutil.get_transform_order(
                [d[name] for name in transform_bonenames], bone_defs)

            for bone_index in self.target_transform_bone_indexes:
                bone_def = bone_defs[bone_index]
                bone_name = bone_def.name_jp
                self.frame_dict[self.TARGET][bone_name] = d = {}
                self.sorted_keyframes[self.TARGET][bone_name] = (
                    [motion.frame for motion in
                     self.motion_name_dict[self.TARGET][bone_name]])
                for motion in self.motion_name_dict[self.TARGET][bone_name]:
                    queue.push(
                        MotionFrame(motion.frame, 'b', self.TARGET, bone_name))
                    d[motion.frame] = motion
            return

    def get_vmd_index(self, model_id, bone_name, frame_no):
        keys = self.sorted_keyframes[model_id][bone_name]
        index = bisect.bisect_left(keys, frame_no)
        if index <= len(keys) - 1 and keys[index] == frame_no:
            return index, True
        else:
            return index - 1, False

    def get_vmd_transform(self, frame_no, bone_name, model_id):
        frame_dict = self.frame_dict[model_id][bone_name]
        key_frames = self.sorted_keyframes[model_id][bone_name]
        bone_def_id = self.bone_dict[model_id][bone_name]
        bone_def = self.bone_defs[model_id][bone_def_id]
        vmd_index, is_key_frame = self.get_vmd_index(
            model_id, bone_name, frame_no)

        if is_key_frame:
            m = frame_dict[frame_no]
            rotation = m.rotation
            position = m.position
        else:
            begin = frame_dict[key_frames[vmd_index]]
            if vmd_index < len(key_frames) - 1:
                end = frame_dict[key_frames[vmd_index + 1]]
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

    def get_target_camera_pos(self, frame_no):
        frame_dict = self.frame_dict[self.TARGET]['CAMERA']
        key_frames = self.sorted_keyframes[self.TARGET]['CAMERA']
        vmd_index, is_key_frame = self.get_vmd_index(
            self.TARGET, 'CAMERA', frame_no)

        if is_key_frame:
            m = frame_dict[frame_no]
            pos = self.get_camera_pos(
                m.position, m.rotation, m.distance)
        else:
            begin = frame_dict[key_frames[vmd_index]]
            if vmd_index < len(key_frames) - 1:
                end = frame_dict[key_frames[vmd_index + 1]]
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

    def get_target_model_pos(self, frame_no):
        vmd_transforms = {}
        global_transforms = {}
        bone_defs = self.bone_defs[self.TARGET]
        for loop_i, bone_index in enumerate(
                self.target_transform_bone_indexes):
            # vmd transform
            bone_def = bone_defs[bone_index]
            bone_name = bone_def.name_jp
            rotation, position = self.get_vmd_transform(
                frame_no, bone_name, self.TARGET)
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

    def get_target_pos(self, frame_no):
        if 'FIXED' == self.target_mode:
            return self.target_pos
        elif 'CAMERA' == self.target_mode:
            return self.get_target_camera_pos(frame_no)
        elif 'MODEL' == self.target_mode:
            return self.get_target_model_pos(frame_no)

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

    def apply_constraints(self, bone_name, turn):
        constraint = self.constraints[bone_name]
        constraint_rad = self.constraints_rad[bone_name]
        turn = [k * j for k, j in zip(turn, constraint[1])]
        turn = [vmdutil.clamp(turn[i],
                -constraint_rad[i], constraint_rad[i])
                for i in range(len(turn))]
        return turn

    def get_watcher_center_transform(self, frame_no):
        bone_defs = self.bone_defs[self.WATCHER]
        bone_dict = self.bone_dict[self.WATCHER]
        transform_bone_names = self.watcher_transform_bone_names
        if '全ての親' in transform_bone_names:
            root_rotation, root_position = self.get_vmd_transform(
                frame_no, '全ての親', self.WATCHER)
            root_def = bone_defs[bone_dict['全ての親']]
        else:
            root_def = None
        if 'センター' in transform_bone_names:
            center_rotation, center_position = self.get_vmd_transform(
                frame_no, 'センター', self.WATCHER)
            center_def = bone_defs[bone_dict['センター']]
        else:
            center_def = None

        if root_def is not None:
            if center_def is not None:
                global_center = get_global_transform(
                    (center_rotation, center_position), center_def,
                    (root_rotation, root_position), root_def,
                    (root_rotation, root_position))
            else:
                global_center = (root_rotation, root_position)
        else:
            if center_def is not None:
                global_center = (center_rotation, center_position)
            else:
                global_center = (vmdutil.QUATERNION_IDENTITY, (0, 0, 0))
        return global_center

    def get_face_rotation(
            self, frame_type, frame_no, bone_name, parent_name,
            global_transforms, vmd_transforms,
            watcher_v, watcher_dir, watcher_pos, up,
            target_v, target_pos):

        look_dir = vmdutil.sub_v(target_pos, watcher_pos)
        if self.check_ignore_case(watcher_dir, look_dir):
            return None

        turn = vmdutil.look_at(
            watcher_dir, up, look_dir, self.global_up)
        turn = self.apply_constraints(bone_name, turn)
        hrot = tuple(vmdutil.euler_to_quaternion(turn))
        return hrot

    def get_arm_rotation(
            self, frame_type, frame_no, bone_name, parent_name,
            global_transforms, vmd_transforms,
            watcher_v, watcher_dir, watcher_pos, watcher_axis, watcher_up,
            target_v, target_pos):

        look_dir = vmdutil.sub_v(target_pos, watcher_pos)
        turn = vmdutil.look_at_fixed_axis(
            watcher_dir, watcher_up, look_dir)
        turn = self.apply_constraints(
            bone_name, [turn, 0, 0])[0]
        hrot = tuple(vmdutil.quaternion(watcher_axis, turn))
        return hrot

    def make_look_at_frames(
            self, frame_type, frame_no, target_pos,
            next_frame_no, next_center_transform, next_target_pos):
        vmd_transforms = {}
        global_transforms = {}
        overwrite_frames = list()
        bone_defs = self.bone_defs[self.WATCHER]
        cpos = (0, 0, 0)
        watcher_v = (0, 0, 0)
        if next_frame_no is not None:
            target_v = vmdutil.sub_v(next_target_pos, target_pos)
            target_v = vmdutil.scale_v(
                target_v, 1 / (next_frame_no - frame_no))
        else:
            target_v = (0, 0, 0)
        for loop_i, bone_index in enumerate(
                self.watcher_transform_bone_indexes):
            bone_def = bone_defs[bone_index]
            bone_name = bone_def.name_jp
            # vmd
            if bone_name not in self.overwrite_bones:
                rotation, position = self.get_vmd_transform(
                    frame_no, bone_name, self.WATCHER)
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
                parent_index = next(iter(
                    self.watcher_bone_graph.preds[bone_index]))
                parent_name = (
                    self.bone_defs[self.WATCHER][parent_index].name_jp)
                parent_vmd = vmd_transforms[parent_name]
                parent_bone_def = self.bone_defs[self.WATCHER][parent_index]
                global_transforms[bone_name] = get_global_transform(
                    vmd_transforms[bone_name], bone_def,
                    vmd_transforms[parent_name], parent_bone_def,
                    global_transforms[parent_name])
                if bone_name == 'センター' and next_frame_no is not None:
                    cpos = global_transforms[bone_name][1]
                    watcher_v = vmdutil.sub_v(next_center_transform[1], cpos)
                    watcher_v = vmdutil.scale_v(
                        watcher_v, 1 / (next_frame_no - frame_no))
                if bone_name in self.overwrite_bones:
                    neck_pos = global_transforms[bone_name][1]
                    look_dir = vmdutil.sub_v(target_pos, neck_pos)
                    base_dir = self.base_dirs[bone_index]
                    base_dir = vmdutil.rotate_v3q(
                        base_dir, global_transforms[parent_name][0])

                    if (
                        bone_def.flag & pmxdef.BONE_AXIS_IS_FIXED ==
                            pmxdef.BONE_AXIS_IS_FIXED):
                        axis = bone_def.fixed_axis
                        up = vmdutil.rotate_v3q(
                            axis, global_transforms[parent_name][0])
                        hrot = self.get_arm_rotation(
                            frame_type, frame_no, bone_name,
                            parent_name,
                            global_transforms, vmd_transforms,
                            watcher_v, base_dir, neck_pos, axis, up,
                            target_v, target_pos)
                        if hrot is None:
                            return []
                    else:
                        up = vmdutil.rotate_v3q(
                            (0, 1, 0),
                            global_transforms[parent_name][0])
                        hrot = self.get_face_rotation(
                            frame_type, frame_no, bone_name,
                            parent_name,
                            global_transforms, vmd_transforms,
                            watcher_v, base_dir, neck_pos, up,
                            target_v, target_pos)
                        if hrot is None:
                            return []
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
            queue, prev):
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
                    pop = queue.pop()
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
        self.add_frames(queue)
        first_frame = queue.top().frame_no
        self.arrange_first_frame(first_frame)
        new_frames = list()
        prev_overwrites = {'frame_no': -1, 'frames': []}
        while True:
            motion_frame = queue.pop()
            if motion_frame is None:
                break
            frame_no = motion_frame.frame_no
            frame_type = motion_frame.type
            while queue.top() is not None and queue.top().frame_no == frame_no:
                dummy = queue.pop()
                frame_type += dummy.type

            if self.frame_range.is_over_max(frame_no):
                break
            if not self.frame_range.is_in_range(frame_no):
                continue

            target_pos = self.get_target_pos(frame_no)
            next_frame = queue.top()
            if next_frame is not None:
                next_frame_no = next_frame.frame_no
                next_center_transform = (
                    self.get_watcher_center_transform(next_frame_no))
                # TODO reuse
                next_target_pos = self.get_target_pos(next_frame_no)
            else:
                next_frame_no = None
                next_center_transform = None
                next_target_pos = None
            overwrite_frames = self.make_look_at_frames(
                    frame_type, frame_no, target_pos,
                    next_frame_no, next_center_transform, next_target_pos)
            if len(overwrite_frames) == 0:
                continue
            if 'CAMERA' == self.target_mode and self.omega_limit > 0:
                overwrite_frames = self.camera_delay(
                    frame_no, frame_type, overwrite_frames,
                    queue, prev_overwrites)
            if len(overwrite_frames) > 0:
                prev_overwrites['frame_no'] = frame_no
                prev_overwrites['frames'] = {
                    frame.name: frame for frame in overwrite_frames}
            new_frames.extend(overwrite_frames)
        return new_frames

if __name__ == '__main__':
    print('use trace_camera.py or trace_model.py.')
