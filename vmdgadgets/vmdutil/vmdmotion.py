import bisect

from . import vmdutil
from . import pmxutil
from . import pmxdef


def get_global_transform(this_transform, this_bone_def,
                         parent_transform, parent_bone_def, parent_global):
    """ Compute the global rotation and position.

    Args:
        this_transform: (rotation, position) of this bone
        this_bone_def: pmxdef.bone of this bone
        parent_bone_def: (rotation, positoin) of parent bone
        parent_bone_def: pmxdef.bone of parent
        parent_global: global (rotation, position) of parent bone
    Returns:
        (rotation, position)
    """
    bone_vector = vmdutil.sub_v(
        vmdutil.add_v(this_bone_def.position, this_transform[1]),
        parent_bone_def.position)
    this_global_pos = vmdutil.add_v(
        parent_global[1],
        vmdutil.rotate_v3q(bone_vector, parent_global[0]))
    this_global_rot = vmdutil.multiply_quaternion(
        this_transform[0], parent_global[0])
    return this_global_rot, this_global_pos


class BoneTransformation():
    """ Transform the bone at frame_no according to vmd motion,
    and stores those results.

    Predecessors of the bone are also transformed and stored.
    """

    def __init__(self, bone_defs, motion_defs,
                 mandatory_bone_names=None, subgraph=False):
        """ Constructor

        If subgraph == False, bones to be transformed are
        (bone in pmx) AND ((bone in vmd) OR (bone in mandatory_bones)).
        If subgraph == True,
        (mandatory_bones and it's predecessors in pmx) AND (bone in vmd).

        Args:
            bone_defs: {bone_index: pmxdef.bone}
            motion_defs: [vmdutil.bone]
            mandatory_bone_names: [bone name],
                by_default 'センター' is mandatory
            subgraph: boolean
        """
        self.bone_defs = bone_defs
        self.motion_defs = motion_defs
        self.mandatory_bone_names = (
            mandatory_bone_names[:]
            if mandatory_bone_names is not None else [])

        self.bone_name_to_index = pmxutil.make_name_dict(self.bone_defs)
        self.mandatory_bone_indexes = [
            self.bone_name_to_index[name]
            for name in self.mandatory_bone_names]

        self.motion_name_dict = vmdutil.make_name_dict(
            vmdutil.frames_to_dict(motion_defs), True)

        self.transform_bone_graph = self.make_bone_graph(subgraph)

        self.transform_bone_indexes = [
            bone_index for bone_index in self.transform_bone_graph.edges]
        self.transform_bone_names = [
            self.bone_defs[index].name_jp
            for index in self.transform_bone_indexes]
        self.leaf_indexes = [
            bone_index for bone_index in self.transform_bone_indexes if
            self.transform_bone_graph.out_degree(bone_index) == 0]

        self.motion_frame_dict = {  # {bone_name: {frame_no: motion_def}}
            bone_name: {
                motion.frame: motion
                for motion in self.motion_name_dict[bone_name]}
            for bone_name in self.transform_bone_names if
            bone_name in self.motion_name_dict}
        self.sorted_keyframes = {  # {bone_name: [frame_no]} for bisect
            bone_name:
            [frame.frame for frame in self.motion_name_dict[bone_name]]
            for bone_name in self.transform_bone_names if
            bone_name in self.motion_name_dict}

        # {frame_no: {bone_index: (global, local)}}
        self.transform_dict = dict()

    def make_bone_graph(self, subgraph):
        if len(self.mandatory_bone_names) > 0 and subgraph is True:
            bone_graph = pmxutil.make_sub_bone_link_graph(
                self.bone_defs, 0, self.mandatory_bone_indexes)
        else:
            # all bones
            bone_graph = pmxutil.make_all_bone_link_graph(self.bone_defs)
        bone_indexes = [index for index in bone_graph.edges]

        # remove nodes not in vmd or mandatory
        for node_index in bone_indexes:
            name = self.bone_defs[node_index].name_jp
            if (name != 'センター' and
                    name not in self.motion_name_dict and
                    name not in self.mandatory_bone_names):
                bone_graph.remove_node(node_index)

        return bone_graph

    def search(self, frame_no, bone_index=None):
        if bone_index is None:
            return self.transform_dict.get(frame_no)
        else:
            return self.transform_dict.get(frame_no, {}).get(bone_index)

    def insert(self, frame_no, bone_index, global_transform, local_transform):
        if frame_no in self.transform_dict:
            self.transform_dict[frame_no][bone_index] = (
                global_transform, local_transform)
        else:
            self.transform_dict[frame_no] = {
                bone_index: (global_transform, local_transform)}

    def delete(self, frame_no, bone_index=None):
        if frame_no in self.transform_dict:
            if bone_index is None:
                return self.transform_dict.pop(frame_no)
            else:
                if bone_index in self.transform_dict[frame_no]:
                    return self.transform_dict[frame_no].pop(bone_index)
                else:
                    return None
        else:
            return None

    def get_vmd_frame(self, frame_no, bone_name):
        # Return frame if the frame_no in vmd, otherwise return None
        d = self.motion_frame_dict.get(bone_name)
        return None if d is None else (
            self.motion_frame_dict[bone_name].get(frame_no))

    def get_vmd_index(self, frame_no, bone_name):
        # Return index or closest below index of the frame_no
        # in sorted list of vmd keyframes
        keys = self.sorted_keyframes[bone_name]
        index = bisect.bisect_left(keys, frame_no)
        if index <= len(keys) - 1 and keys[index] == frame_no:
            return index, True
        else:
            return index - 1, False

    def get_vmd_transform(self, frame_no, bone_index):
        bone_name = self.bone_defs[bone_index].name_jp
        if bone_name not in self.motion_frame_dict:  # bone not in vmd
            return vmdutil.QUATERNION_IDENTITY, (0, 0, 0)

        frame_dict = self.motion_frame_dict[bone_name]
        key_frames = self.sorted_keyframes[bone_name]
        bone_def = self.bone_defs[bone_index]
        vmd_index, is_key_frame = self.get_vmd_index(frame_no, bone_name)

        if is_key_frame:
            m = frame_dict[frame_no]
            rotation = m.rotation
            position = m.position
        else:
            if vmd_index < 0:
                first_frame = frame_dict[key_frames[0]]
                rotation = first_frame.rotation
                position = first_frame.position
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

    def do_transform(self, frame_no, bone_index, vmd_transform=None):
        """Return and store the global/local transformation of the bone
        at frame_no.

        If vmd_transform is not None, compute with it.
        Or compute with motion in vmd file.
        Returns:
            (global_transformation, vmd_transformation(local))
            Transformations consist of (rotation, position).
        """
        if bone_index not in self.transform_bone_indexes:
            return None
        if vmd_transform is None:
            transform = self.search(frame_no, bone_index)
            if transform is not None:
                return transform
            else:
                vmd_transform = self.get_vmd_transform(frame_no, bone_index)
        if (bone_index <= 0 or
                self.transform_bone_graph.in_degree(bone_index) <= 0):
            global_transform = (
                vmd_transform[0],
                vmdutil.add_v(
                    self.bone_defs[bone_index].position, vmd_transform[1]))
        else:
            parent_index = next(
                iter(self.transform_bone_graph.preds[bone_index]))
            parent_global, parent_vmd = self.do_transform(
                frame_no, parent_index)
            global_transform = get_global_transform(
                vmd_transform, self.bone_defs[bone_index],
                parent_vmd, self.bone_defs[parent_index], parent_global)
        self.insert(frame_no, bone_index, global_transform, vmd_transform)
        return global_transform, vmd_transform


class CameraTransformation():
    def __init__(self, motion_defs):
        self.motion_defs = motion_defs
        self.sorted_motions = sorted(motion_defs, key=lambda e: e.frame)
        self.motion_frame_dict = vmdutil.frames_to_dict(motion_defs)
        self.sorted_keyframes = [m.frame for m in self.sorted_motions]

    def get_vmd_index(self, frame_no):
        keys = self.sorted_keyframes
        index = bisect.bisect_left(keys, frame_no)
        if index <= len(keys) - 1 and keys[index] == frame_no:
            return index, True
        else:
            return index - 1, False

    def get_vmd_transform(self, frame_no):
        vmd_index, is_key_frame = self.get_vmd_index(frame_no)
        if is_key_frame:
            m = self.motion_frame_dict[frame_no][0]
            rotation = m.rotation
            position = m.position
            distance = m.distance
        else:
            key_frames = self.sorted_keyframes
            begin = self.motion_frame_dict[key_frames[vmd_index]][0]
            if vmd_index < len(key_frames) - 1:
                end = self.motion_frame_dict[key_frames[vmd_index + 1]][0]
                position = vmdutil.interpolate_position(
                    frame_no, begin, end, 'cameras')
                rotation = vmdutil.interpolate_rotation(
                    frame_no, begin, end, 'cameras')
                distance = vmdutil.interpolate_camera_distance(
                    frame_no, begin, end)
            else:
                rotation = begin.rotation
                position = begin.position
                distance = begin.distance
        return rotation, position, distance