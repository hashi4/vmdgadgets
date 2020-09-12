import math
import heapq
import vmdutil
import re
from collections import namedtuple
from vmdutil import vmddef
from vmdutil import pmxutil
from vmdutil import pmxdef
from vmdutil import vmdmotion

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
# flame_type:
# 'o': key frames of overwrite bones
# 'b': bones(watcher, target, ext)
# 'c': camera frames of 'cut'
# 'v': camera frames
# 'r': delay
# 'u': addtional
# 'i': ignore


class LookAt():
    def __init__(self, watcher_pmx_name, watcher_vmd_name):
        self.watcher_pmx_name = watcher_pmx_name
        self.watcher_vmd_name = watcher_vmd_name
        self.target_pos = (0, 0, 0)
        self.frame_ranges = FrameRange()
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
        self.vmd_blend_ratios = {
            '首': (0, 0, 0),
            '頭': (0, 0, 0),
            '両目': (0, 0, 0),
        }
        self.forward_dirs = {
            '首': (0, 0, -1),
            '頭': (0, 0, -1),
            '両目': (0, 0, -1),
        }
        self.up_blend_weight = {
            '首': 1.0,
            '頭': 1.0,
            '両目': 1.0,
        }
        self.watcher_extlink = None
        self.ignore_zone = math.radians(140)
        self.ignore_zone2 = None
        self.global_up = (0, 1, 0)
        self.omega_limit = math.pi / 40
        self.additional_frame_nos = []
        self.near_mode = False
        self.vmd_lerp = False
        self.use_vmd_interpolation = False
        self.WATCHER = 0
        self.TARGET = 1
        self.WATCHER_EX = 2
        self.bone_defs = {}
        self.bone_dict = {}
        self.ignore_checked = False

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
            elif bone_name not in self.constraints:
                self.constraints[bone_name] = self.DEFAULT_CONTSTRAINT
            else:
                pass

    def set_target_bone(self, bone_name):
        self.target_bone = bone_name

    def set_frame_ranges(self, frame_ranges):
        self.frame_ranges = FrameRange(frame_ranges)

    def set_omega_limit(self, limit):
        self.omega_limit = limit

    def set_ignore_zone(self, zone):
        self.ignore_zone = zone

    def set_ignore_zone2(self, zone):
        self.ignore_zone2 = zone

    def set_constraint(self, bone_name, constraint):
        if bone_name in self.constraints:
            self.constraints[bone_name] = constraint

    def set_vmd_blend_ratio(self, bone_name, ratio):
        self.vmd_blend_ratios[bone_name] = ratio

    def set_forward_dir(self, bone_name, dir):
        self.forward_dirs[bone_name] = vmdutil.normalize_v(dir)

    def set_up_blend_weight(self, bone_name, weight):
        self.up_blend_weight[bone_name] = weight

    def set_near_mode(self, b):
        self.near_mode = b

    def set_vmd_lerp(self, b):
        self.vmd_lerp = b

    def set_use_vmd_interpolation(self, b):
        self.use_vmd_interpolation = b

    def set_additional_frames(self, frame_nos):
        self.additional_frame_nos = frame_nos

    def set_watcher_external_link(self, bone_name, pmx_name, vmd_name):
        self.watcher_extlink = (bone_name, pmx_name, vmd_name)

    def add_frames(self, queue):
        for frame_no in self.additional_frame_nos:
            queue.push(MotionFrame(frame_no, 'u', -1, 'A'))

    def need_vmd_blend(self):
        if self.use_vmd_interpolation:
            return False
        for b in self.vmd_blend_ratios.values():
            for r in b:
                if r > 0:
                    return True
        return False

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

        if self.watcher_extlink is not None:
            self.watcher_extlink_pmx = pmxutil.Pmxio()
            self.watcher_extlink_pmx.load(self.watcher_extlink[1])
            self.watcher_extlink_vmd = vmdutil.Vmdio()
            self.watcher_extlink_vmd.load(self.watcher_extlink[2])
            self.bone_defs[self.WATCHER_EX] = (
                self.watcher_extlink_pmx.get_elements('bones'))

    def check_bones(self, bone_names, bone_dict):
        for name in bone_names:
            if name not in bone_dict:
                return False
        return True

    def make_arm_dir(self):
        base_dirs = {}
        leaf_indexes = self.watcher_transform.leaf_indexes
        graph = self.watcher_transform.transform_bone_graph
        bone_defs = self.watcher_transform.bone_defs
        for leaf_index in leaf_indexes:
            if leaf_index in self.overwrite_indexes:
                bone_def = bone_defs[leaf_index]
                if (bone_def.flag & pmxdef.BONE_DISP_DIR ==
                   pmxdef.BONE_DISP_DIR):
                    disp_to_bone_index = bone_def.disp_dir
                    base_dir = vmdutil.sub_v(
                        bone_defs[disp_to_bone_index].position,
                        bone_def.position)
                else:
                    base_dir = bone_def.disp_dir
                base_dirs[leaf_index] = base_dir
                degree = graph.in_degree(leaf_index)
                if degree <= 0:
                    continue
                parent_index = next(iter(graph.preds[leaf_index]))
                while True:
                    if parent_index in self.overwrite_indexes:
                        base_dirs[parent_index] = base_dir
                    degree = graph.in_degree(parent_index)
                    if degree <= 0:
                        break
                    parent_index = next(iter(graph.preds[parent_index]))
        return base_dirs

    def setup_watcher_extlink(self, queue):
        bone_defs = self.bone_defs[self.WATCHER_EX]
        ext_bone = self.watcher_extlink[0]
        self.bone_dict[self.WATCHER_EX] = bone_dict = pmxutil.make_index_dict(
            bone_defs)
        if not self.check_bones([ext_bone], bone_dict):
            raise Exception('external link bone is not in pmx')
        self.watcher_extlink_transform = extt = vmdmotion.BoneTransformation(
            bone_defs, self.watcher_extlink_vmd.get_frames('bones'),
            [ext_bone], True)
        for bone_index in extt.transform_bone_indexes:
            bone_name = bone_defs[bone_index].name_jp
            for motion in extt.motion_name_dict[bone_name]:
                queue.push(MotionFrame(
                    motion.frame, 'b', self.WATCHER_EX, bone_name))
        return self.watcher_extlink_transform

    def setup_watcher(self, queue):
        bone_defs = self.bone_defs[self.WATCHER]
        self.bone_dict[self.WATCHER] = bone_dict = pmxutil.make_index_dict(
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
        self.watcher_transform = vmdmotion.BoneTransformation(
            bone_defs, self.watcher_motions, self.overwrite_bones, True)

        self.overwrite_indexes = [
            self.watcher_transform.bone_name_to_index[bone_name]
            for bone_name in self.overwrite_bones]
        self.overwrite_indexes = pmxutil.get_transform_order(
            self.overwrite_indexes, bone_defs)
        self.overwrite_bones = [
            bone_defs[bone_index].name_jp for
            bone_index in self.overwrite_indexes]

        # make dir
        if 'ARM' == self.point_mode:
            self.base_dirs = self.make_arm_dir()
        else:
            self.base_dirs = {}
            for index in self.overwrite_indexes:
                bone_name = bone_defs[index].name_jp
                dir = self.forward_dirs.get(bone_name)
                if dir is not None:
                    self.base_dirs[index] = dir
                else:
                    self.base_dirs[index] = (0, 0, -1)

        # queue frames
        for bone_index in self.watcher_transform.transform_bone_indexes:
            bone_def = bone_defs[bone_index]
            bone_name = bone_def.name_jp
            for motion in (
                    self.watcher_transform.motion_name_dict[bone_name]):
                if bone_name not in self.overwrite_bones:
                    queue.push(MotionFrame(
                        motion.frame, 'b', self.WATCHER, bone_name))
                else:
                    queue.push(MotionFrame(
                        motion.frame, 'o', self.WATCHER, bone_name))

        if self.watcher_extlink is not None:
            transform = self.setup_watcher_extlink(queue)
            self.watcher_transform.set_external_link(
                transform, self.watcher_extlink[0])

        return

    def setup_target(self, queue):
        if 'CAMERA' == self.target_mode:
            self.target_transform = vmdmotion.VmdMotion(self.target_motions)
            sorted_motions = self.target_transform.sorted_motions
            for i, motion in enumerate(sorted_motions):
                type = 'c' if (
                    i > 0 and
                    sorted_motions[i - 1].frame == motion.frame - 1) else 'v'
                queue.push(MotionFrame(
                    motion.frame, type, self.TARGET, 'CAMERA'))
            return
        elif 'MODEL' == self.target_mode:
            bone_defs = self.bone_defs[self.TARGET]
            self.bone_dict[self.TARGET] = d = (
                pmxutil.make_index_dict(bone_defs))
            if self.target_bone not in d:
                raise Exception('target bone is not in pmx.')
            if self.target_bone == '両目':
                bone_defs[d['両目']] = replace_bonedef_position(
                    bone_defs[d['両目']],
                    bone_defs[d['右目']], [1, 2])
            # pmx
            self.target_transform = vmdmotion.BoneTransformation(
                bone_defs, self.target_motions, [self.target_bone], True)

            for bone_index in self.target_transform.transform_bone_indexes:
                bone_def = bone_defs[bone_index]
                bone_name = bone_def.name_jp
                for motion in (
                        self.target_transform.motion_name_dict[bone_name]):
                    queue.push(
                        MotionFrame(motion.frame, 'b', self.TARGET, bone_name))
            return

    def get_camera_pos(self, rotation, position, distance):
        direction = vmdutil.camera_direction(rotation, distance)
        return vmdutil.add_v(position, direction)

    def get_target_camera_pos(self, frame_no):
        rotation, position, distance, angle_of_view = (
            self.target_transform.get_vmd_transform(frame_no))
        pos = self.get_camera_pos(rotation, position, distance)
        return pos

    def get_target_model_pos(self, frame_no):
        bone_dict = self.target_transform.bone_name_to_index
        global_target, vmd_target, additional_transform = (
            self.target_transform.do_transform(
                frame_no, bone_dict[self.target_bone]))
        return global_target[1]

    def get_target_pos(self, frame_no):
        if 'FIXED' == self.target_mode:
            return self.target_pos
        elif 'CAMERA' == self.target_mode:
            return self.get_target_camera_pos(frame_no)
        elif 'MODEL' == self.target_mode:
            return self.get_target_model_pos(frame_no)

    def check_ignore_case2(self, turn):
        turn = [abs(t) for t in turn]
        return turn[0] > self.ignore_zone2[0] or turn[1] > self.ignore_zone2[1]

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

    def scale_turn(self, bone_name, turn, r=False):
        constraint = self.constraints[bone_name]
        weight = constraint[1]
        if r:
            weight = [1 - k for k in weight]
        turn = [k * j for k, j in zip(turn, weight)]
        return turn

    def apply_constraints(self, bone_name, turn):
        constraint_rad = self.constraints_rad[bone_name]
        turn = [vmdutil.clamp(turn[i],
                -constraint_rad[i], constraint_rad[i])
                for i in range(len(turn))]
        return turn

    def copy_vmd_of_overwrite_bones(
            self, frame_no, frame_type, bone_name=None):
        if 'o' not in frame_type:
            return []
        new_frames = list()
        if bone_name is not None:
            frame = self.watcher_transform.get_vmd_frame(frame_no, bone_name)
            if frame is not None:
                return [frame]
            else:
                return []
        for bone_name in self.overwrite_bones:
            frame = self.watcher_transform.get_vmd_frame(frame_no, bone_name)
            if frame is not None:
                new_frames.append(frame)
        return new_frames

    def get_watcher_center_transform(self, frame_no):
        bone_dict = self.watcher_transform.bone_name_to_index
        global_center, vmd_center, additional_center = (
            self.watcher_transform.do_transform(frame_no, bone_dict['センター']))
        if global_center is None:
            global_center = (vmdutil.QUATERNION_IDENTITY, (0, 0, 0))
        return global_center

    def apply_near_mode(self, bone_index, rotation, target_pos):
        bone_defs = self.watcher_transform.bone_defs
        leaves = self.watcher_transform.transform_bone_graph.get_leaves(
            bone_index)
        for ow_index in self.overwrite_indexes:
            if ow_index in leaves:
                delta = vmdutil.sub_v(
                    bone_defs[bone_index].position,
                    bone_defs[ow_index].position)
                delta = vmdutil.rotate_v3q(delta, rotation)
                target_pos = vmdutil.add_v(target_pos, delta)
                break  # first leaf in sorted overwrite-bones
        return target_pos

    def get_face_rotation(
            self, frame_type, frame_no, bone_index, parent_index,
            watcher_v, watcher_dir, watcher_pos, up,
            target_v, target_pos):

        bone_defs = self.watcher_transform.bone_defs
        bone_name = bone_defs[bone_index].name_jp
        look_dir = vmdutil.sub_v(target_pos, watcher_pos)

        if (self.ignore_zone2 is None and
                self.check_ignore_case(watcher_dir, look_dir)):
            return None

        turn = vmdutil.look_at(
            watcher_dir, up, look_dir, self.global_up)

        if self.ignore_checked is True:
            if 'i' in frame_type:
                return None
        elif self.ignore_zone2 is not None and self.check_ignore_case2(turn):
            return None

        if (self.vmd_lerp and
                bone_index not in self.watcher_transform.leaf_indexes):
            vmd_rot = self.watcher_transform.get_vmd_transform(
                frame_no, bone_index)[0]
            vmd_euler = vmdutil.quaternion_to_euler(vmd_rot)
            turn = [turn[0], turn[1], 0]
            turn = self.scale_turn(bone_name, turn)
            vmd_euler = self.scale_turn(bone_name, vmd_euler, True)
            turn = vmdutil.add_v(turn, vmd_euler)
        else:
            turn = self.scale_turn(bone_name, turn)
        turn = self.apply_constraints(bone_name, turn)
        hrot = tuple(vmdutil.euler_to_quaternion(turn))
        return hrot

    def get_arm_rotation(
            self, frame_type, frame_no, bone_index, parent_index,
            watcher_v, watcher_dir, watcher_pos, watcher_axis, watcher_up,
            target_v, target_pos):

        bone_defs = self.watcher_transform.bone_defs
        bone_name = bone_defs[bone_index].name_jp
        look_dir = vmdutil.sub_v(target_pos, watcher_pos)
        turn = vmdutil.look_at_fixed_axis(
            watcher_dir, watcher_up, look_dir)
        turn = self.apply_constraints(
            bone_name, [turn, 0, 0])[0]
        hrot = tuple(vmdutil.quaternion(watcher_axis, turn))
        return hrot

    def get_rotation(self, frame_no, frame_type, bone_index,
                     watcher_v, target_v, target_pos):

        bone_graph = self.watcher_transform.transform_bone_graph
        bone_defs = self.watcher_transform.bone_defs
        bone_def = bone_defs[bone_index]
        if bone_graph.in_degree(bone_index) > 0:
            parent_index = next(iter(bone_graph.preds[bone_index]))
            global_parent, vmd_parent, add_parent = (
                self.watcher_transform.do_transform(
                    frame_no, parent_index))
            add_trans = self.watcher_transform.get_additional_transform(
                frame_no, bone_index)
            neck_rotation, neck_pos = vmdmotion.get_global_transform(
                (vmdutil.QUATERNION_IDENTITY, [0, 0, 0]), bone_def,
                vmd_parent, bone_defs[parent_index],
                global_parent, add_trans)
        else:
            # neck_pos = bone_def.position
            raise Exception('overwrite bone should not be root.')
        forward_dir = self.base_dirs[bone_index]
        base_dir = vmdutil.rotate_v3q(forward_dir, global_parent[0])

        if self.near_mode:
            target_pos = self.apply_near_mode(
                bone_index, neck_rotation, target_pos)

        if (
            bone_def.flag & pmxdef.BONE_AXIS_IS_FIXED ==
                pmxdef.BONE_AXIS_IS_FIXED):
            axis = bone_def.fixed_axis
            up = vmdutil.rotate_v3q(axis, global_parent[0])
            hrot = self.get_arm_rotation(
                frame_type, frame_no, bone_index,
                parent_index,
                watcher_v, base_dir, neck_pos, axis, up,
                target_v, target_pos)
        else:
            up = (0, -forward_dir[2], forward_dir[1])
            up = vmdutil.rotate_v3q(up, global_parent[0])
            hrot = self.get_face_rotation(
                frame_type, frame_no, bone_index,
                parent_index,
                watcher_v, base_dir, neck_pos, up,
                target_v, target_pos)
        return hrot

    def make_look_at_frames(
            self, frame_type, frame_no, target_pos,
            next_frame_no, next_center_transform, next_target_pos,
            bone_index=None):

        overwrite_frames = list()
        bone_defs = self.watcher_transform.bone_defs

        if next_frame_no is not None:
            target_v = vmdutil.sub_v(next_target_pos, target_pos)
            target_v = vmdutil.scale_v(
                target_v, 1 / (next_frame_no - frame_no))

        # center velocity
            global_center, vmd_center, add_center = (
                self.watcher_transform.do_transform(
                    frame_no,
                    self.watcher_transform.bone_name_to_index['センター']))
            cpos = global_center[1]
            watcher_v = vmdutil.sub_v(next_center_transform[1], cpos)
            watcher_v = vmdutil.scale_v(
                watcher_v, 1 / (next_frame_no - frame_no))
        else:
            target_v = (0, 0, 0)
            cpos = (0, 0, 0)
            watcher_v = (0, 0, 0)

        def get_lookat_frame(b_index):
            result = list()
            bone_def = bone_defs[b_index]
            bone_name = bone_def.name_jp
            hrot = self.get_rotation(
                frame_no, frame_type, b_index,
                watcher_v, target_v, target_pos)
            if hrot is None:  # ignore_case
                if self.use_vmd_interpolation:
                    vmd_frame = self.watcher_transform.get_vmd_frame(
                        frame_no, bone_name)
                    if vmd_frame:
                        result.append(vmd_frame)
                return result
            self.watcher_transform.do_transform(
                frame_no, b_index, (hrot, (0, 0, 0)))
            if (not self.use_vmd_interpolation or
                    b_index in self.watcher_transform.leaf_indexes):
                result.append(vmddef.BONE_SAMPLE._replace(
                    frame=frame_no,
                    name=bone_name.encode(vmddef.ENCODING),
                    rotation=hrot))
            else:
                vmd_frame = self.watcher_transform.get_vmd_frame(
                    frame_no, bone_name)
                if vmd_frame:
                    result.append(vmd_frame._replace(
                        rotation=hrot))
            return result

        if bone_index is not None:
            result = get_lookat_frame(bone_index)
            if 0 == len(result):
                return []
            else:
                overwrite_frames.extend(result)
        else:
            for bone_index in self.overwrite_indexes:
                result = get_lookat_frame(bone_index)
                if 0 == len(result):
                    return []
                else:
                    overwrite_frames.extend(result)
        # vmd_blend
        if self.need_vmd_blend():
            overwrite_frames = self.blend_vmd(
                frame_no, frame_type, overwrite_frames,
                watcher_v, target_v, target_pos)
        return overwrite_frames

    def blend_vmd(self, frame_no, frame_type, overwrite_frames,
                  watcher_v, target_v, target_pos):
        def find_frame(bone_name):
            for index, frame in enumerate(overwrite_frames):
                if vmdutil.b_to_str(frame.name) == bone_name:
                    return overwrite_frames.pop(index)

        bone_defs = self.watcher_transform.bone_defs

        # remove transformation data from db
        self.watcher_transform.delete_descendants(
            frame_no, self.overwrite_indexes[0])
        # blend vmd
        for bone_index in self.overwrite_indexes:
            bone_name = bone_defs[bone_index].name_jp
            if bone_index in self.watcher_transform.leaf_indexes:  # eyes
                # lookat
                hrot = self.get_rotation(
                    frame_no, frame_type, bone_index,
                    watcher_v, target_v, target_pos)
                if hrot is not None:
                    frame = find_frame(bone_name)
                    frame = frame._replace(rotation=hrot)
                    self.watcher_transform.do_transform(
                        frame_no, bone_index, (hrot, (0, 0, 0)))
                    overwrite_frames.append(frame)
            else:
                ratio = self.vmd_blend_ratios.get(bone_name, (0, 0, 0))
                # blend
                frame = find_frame(bone_name)
                if ratio[0] > 0 or ratio[1] > 0 or ratio[2] > 0:
                    vmd_rot = self.watcher_transform.get_vmd_transform(
                        frame_no, bone_index)[0]
                    vmd_euler = vmdutil.quaternion_to_euler(vmd_rot)
                    if vmd_euler[0] > 0:  # up
                        weight = self.up_blend_weight.get(bone_name, 1.0)
                        vmd_euler = (
                            vmd_euler[0] * weight,
                            vmd_euler[1], vmd_euler[2])
                    vmd_euler = [i * j for i, j in zip(vmd_euler, ratio)]
                    look_euler = vmdutil.quaternion_to_euler(frame.rotation)
                    # blend
                    look_euler = [i + j for i, j in zip(look_euler, vmd_euler)]
                    look_euler = self.apply_constraints(bone_name, look_euler)
                    hrot = tuple(vmdutil.euler_to_quaternion(look_euler))
                    frame = frame._replace(rotation=hrot)
                    self.watcher_transform.do_transform(
                        frame_no, bone_index, (hrot, (0, 0, 0)))
                else:
                    self.watcher_transform.do_transform(
                        frame_no, bone_index, (frame.rotation, (0, 0, 0)))
                overwrite_frames.append(frame)
        return overwrite_frames

    def camera_delay(
            self, frame_no, frame_type, overwrite_frames,
            queue, prev):
        if prev['frame_no'] < 0:
            return overwrite_frames

        if 'c' in frame_type:
            maxrot = max(
                [2 * math.acos(vmdutil.clamp(vmdutil.dot_v(
                    motion.rotation,
                    prev['frames'][vmdutil.b_to_str(motion.name)].rotation),
                    -1, 1))
                    for motion in overwrite_frames if
                    prev['frames'].get(
                        vmdutil.b_to_str(motion.name)) is not None])

            omega = maxrot / (frame_no - prev['frame_no'])
            if omega > self.omega_limit:
                delay_to = math.ceil(maxrot / self.omega_limit) + frame_no
                while True:
                    peek = queue.top()
                    if (peek is None or delay_to <= peek.frame_no or
                            'o' in peek.type):
                        break
                    queue.pop()
                queue.push(MotionFrame(delay_to, 'r', -1, 'DELAY'))
                return []
            else:
                return overwrite_frames
        else:
            return overwrite_frames

    def check_ignore_frames(self, queue_base):
        tmp_queue = PriorityQueue()
        result_queue = PriorityQueue()
        result_queue.queue = queue_base.queue[:]
        if len(self.watcher_transform.leaf_indexes) > 1:
            # TODO:
            pass
        for bone_index in self.watcher_transform.leaf_indexes:
            if bone_index not in self.overwrite_indexes:
                continue
            tmp_queue.queue = result_queue.queue[:]
            while True:
                motion_frame = tmp_queue.pop()
                if motion_frame is None:
                    break
                frame_no = motion_frame.frame_no
                frame_type = motion_frame.type
                while (tmp_queue.top() is not None and
                        tmp_queue.top().frame_no == frame_no):
                    dummy = tmp_queue.pop()
                    frame_type += dummy.type
                if not self.frame_ranges.is_in_range(frame_no):
                    continue
                if 'u' in frame_type:
                    continue
                target_pos = self.get_target_pos(frame_no)
                hrot = self.get_rotation(
                    frame_no, frame_type, bone_index,
                    None, None, target_pos)
                if hrot is None and 'i' not in frame_type:
                    result_queue.push(MotionFrame(frame_no, 'i', -1, 'IGNORE'))
        self.ignore_checked = True
        self.watcher_transform.clear()
        return result_queue.queue

    def look_at_npath(self):
        self.load()
        queue = PriorityQueue()
        self.setup_watcher(queue)
        self.setup_target(queue)
        self.add_frames(queue)
        new_frames = dict()
        bone_defs = self.watcher_transform.bone_defs
        queue_backup = queue.queue

        if self.ignore_zone2 is not None:
            queue_backup = self.check_ignore_frames(queue)

        for bone_index in self.overwrite_indexes:
            bone_name = bone_defs[bone_index].name_jp
            queue.queue = queue_backup[:]
            new_frames[bone_index] = list()
            is_leaf = bone_index in self.watcher_transform.leaf_indexes
            prev_overwrites = {'frame_no': -1, 'frames': []}
            while True:
                motion_frame = queue.pop()
                if motion_frame is None:
                    break
                frame_no = motion_frame.frame_no
                frame_type = motion_frame.type
                while (queue.top() is not None and
                        queue.top().frame_no == frame_no):
                    dummy = queue.pop()
                    frame_type += dummy.type

                if not self.frame_ranges.is_in_range(frame_no):
                    new_frames[bone_index].extend(
                        self.copy_vmd_of_overwrite_bones(
                            frame_no, frame_type, bone_name))
                    continue

                if (not is_leaf and self.watcher_transform.get_vmd_frame(
                        frame_no, bone_name) is None):
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
                        next_frame_no, next_center_transform,
                        next_target_pos,
                        bone_index)
                if len(overwrite_frames) <= 0:
                    continue
                if (is_leaf and 'CAMERA' == self.target_mode and
                        self.omega_limit > 0):
                    overwrite_frames = self.camera_delay(
                        frame_no, frame_type, overwrite_frames,
                        queue, prev_overwrites)
                    if len(overwrite_frames) > 0:
                        prev_overwrites['frame_no'] = frame_no
                        prev_overwrites['frames'] = {
                            vmdutil.b_to_str(frame.name):
                            frame for frame in overwrite_frames}
                new_frames[bone_index].extend(overwrite_frames)
            self.watcher_transform.replace_vmd_frames(new_frames[bone_index])
        return [f for inner_list in new_frames.values() for f in inner_list]

    def look_at(self):
        if self.use_vmd_interpolation:
            return self.look_at_npath()
        self.load()
        queue = PriorityQueue()
        self.setup_watcher(queue)
        self.setup_target(queue)
        self.add_frames(queue)
        new_frames = list()
        prev_overwrites = {'frame_no': -1, 'frames': []}
        o_frame_pattern = re.compile('^o*$')
        vmd_blend = self.need_vmd_blend()

        while True:
            motion_frame = queue.pop()
            if motion_frame is None:
                break
            frame_no = motion_frame.frame_no
            frame_type = motion_frame.type
            while queue.top() is not None and queue.top().frame_no == frame_no:
                dummy = queue.pop()
                frame_type += dummy.type

            if not self.frame_ranges.is_in_range(frame_no):
                new_frames.extend(
                    self.copy_vmd_of_overwrite_bones(frame_no, frame_type))
                continue

            if (not vmd_blend and not self.vmd_lerp and
                    not self.use_vmd_interpolation and
                    o_frame_pattern.match(frame_type)):
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
                    vmdutil.b_to_str(frame.name):
                    frame for frame in overwrite_frames}
            new_frames.extend(overwrite_frames)
            self.watcher_transform.delete(frame_no)
            if 'MODEL' == self.target_mode:
                self.target_transform.delete(frame_no)
        return new_frames


if __name__ == '__main__':
    print('use trace_camera.py or trace_model.py.')
