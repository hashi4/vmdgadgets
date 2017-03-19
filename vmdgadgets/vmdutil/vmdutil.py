'''utilites for handling vmd files and motions

'''
import math
import bisect
from collections import defaultdict
from collections import Iterable
from . import vmddef
from . import vmdbezier

EPS = 1e-10
QUATERNION_IDENTITY = (0, 0, 0, 1)


def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)


class Vmdio:
    '''class for input/output, get/set infomation of vmd file
    '''
    def __init__(self):
        # header
        self.header = vmddef.header(
            vmddef.HEADER1, b'')
        self.counts = {}
        self.frames = {}
        for element in vmddef.VMD_ELEMENTS:
            self.counts[element] = vmddef.count(0)
            self.frames[element] = []

    def get_frames(self, element):
        return self.frames[element]

    def set_frames(self, element, o):
        self.counts[element] = vmddef.count(len(o))
        self.frames[element] = o

    def read_bytes(self):
        offset = 0
        filesize = len(self.buf)
        # header
        self.header = vmddef.unpack_header(self.buf, offset)
        offset += vmddef.header_def.size
        # frames
        for element in vmddef.VMD_ELEMENTS:
            if filesize <= offset:
                self.counts[element] = vmddef.count(0)
                continue
            self.counts[element] = vmddef.unpack_count(
                self.buf, offset)
            offset += vmddef.count_def.size
            io_util = vmddef.VMD_IO_UTIL[element]
            for index in range(self.counts[element].count):
                frame = io_util[2](self.buf, offset)
                self.frames[element].append(frame)
                offset += io_util[0](frame)

    def load(self, filename):
        if len(self.counts.keys()) > 0:
            self.__init__()
        f = open(filename, 'rb')
        self.buf = f.read()
        f.close()
        del f
        self.read_bytes()

    def load_fd(self, reader):
        if len(self.counts.keys()) > 0:
            self.__init__()
        self.buf = reader.read()
        self.read_bytes()

    def copy(self):
        p = Vmdio()
        # header
        p.header = self.header
        # frames
        for element in vmddef.VMD_ELEMENTS:
            p.counts[element] = self.counts[element]
            p.frames[element] = self.frames[element].copy()
        return p

    def to_bytes(self):
        buf = bytearray()
        # header
        buf += vmddef.pack_header(self.header)
        # frames
        for element in vmddef.VMD_ELEMENTS:
            io_util = vmddef.VMD_IO_UTIL[element]
            count = vmddef.count(len(self.frames[element]))
            buf += vmddef.pack_count(count)
            for frame in self.frames[element]:
                buf += io_util[1](frame)
        return buf

    def store(self, filename):
        buf = self.to_bytes()
        f = open(filename, 'wb')
        f.write(buf)
        f.close()

    def store_fd(self, writer):
        buf = self.to_bytes()
        writer.write(buf)

    def normalize(self):
        motion_dict = make_motion_dict(self)
        for element in vmddef.VMD_ELEMENTS:
            new_frames = normalize_frames(motion_dict[element])
            self.counts[element] = vmddef.count(len(new_frames))
            self.frames[element] = new_frames


def frames_to_dict(frames):
    d = defaultdict(list)
    for frame in frames:
        d[frame.frame].append(frame)
    return d


def make_motion_dict(vmd):
    frame_dict = {}
    for i in vmddef.VMD_ELEMENTS:
        frame_dict[i] = frames_to_dict(vmd.get_frames(i))
    return frame_dict


def compare_frame(f1, f2):
    f2d = f2._replace(frame=f1.frame)
    return f1 == f2d


def remove_redundant_frames(frames):
    length = len(frames)
    if (length > 2):
        new_list = list()
        new_list.append(frames[0])
        for i in range(1, length - 1):
            if (compare_frame(frames[i - 1], frames[i]) and
                compare_frame(frames[i], frames[i + 1])):
                pass
            else:
                new_list.append(frames[i])
        new_list.append(frames[length - 1])
        return new_list
    else:
        return frames


def make_name_dict(frame_dict, decode=False):
    frame_nos = sorted(frame_dict.keys())
    name_dict = defaultdict(list)
    for frame_no in frame_nos:
        for frame in frame_dict[frame_no]:
            name = frame.name if not decode else b_to_str(frame.name)
            name_dict[name].append(frame)
    return name_dict


def normalize_frames(frame_dict):
    if (len(frame_dict)) > 0:
        sample_frame = frame_dict.values().__iter__().__next__()
        if ('name' in sample_frame[0]._fields):
            name_dict = make_name_dict(frame_dict)
            new_frames = list()
            for key in name_dict.keys():
                new_frames.extend(remove_redundant_frames(name_dict[key]))
            return new_frames
        else:
            frame_nos = sorted(frame_dict.keys())
            frames = [frame_dict[frame][0] for frame in frame_nos]
            new_frames = remove_redundant_frames(frames)
            return new_frames
    else:
        return list()


def b_to_str(b):
    zero = b.find(b'\0')  # throw out 0xfd
    if zero >= 0:
        b = b[:zero]
    try:
        return b.decode(vmddef.ENCODING)
    except UnicodeDecodeError:
        return b[:-1].decode(vmddef.ENCODING)


def is_vmd_header(header):
    return b_to_str(header.header) == b_to_str(vmddef.HEADER1)


def is_camera_header(header):
    return b_to_str(header.model_name) == b_to_str(
        vmddef.HEADER2_CAMERA)


def camera_direction(euler_angles, magnitude=1.0):
    # [0]: pitch, [1]: yaw, [2]: roll
    t = math.cos(euler_angles[0])
    result = (-math.sin(euler_angles[1]) * t,
              math.sin(euler_angles[0]),
              math.cos(euler_angles[1]) * t)
    return [i * magnitude for i in result]


def adjacent_difference(l, op=lambda x1, x2: x1 - x2):
    return [op(l[index+1], l[index]) for index in range(len(l) - 1)]


def get_interval(frame_no, frame_dict):
    keys = sorted(frame_dict.keys())
    if frame_no < keys[0]:
        return None, 0
    if frame_no > keys[-1]:
        return keys[-1], None
    if frame_no in keys:
        return (frame_no, frame_no)
    index = bisect.bisect_right(keys, frame_no)
    return keys[index - 1], keys[index]


def interpolate_position(frame_no, begin, end, element='bones'):
    if element == 'bones':
        cp = vmddef.bone_vmdformat_to_controlpoints(end.interpolation)
    elif element == 'cameras':
        cp = vmddef.camera_vmdformat_to_controlpoints(end.interpolation)
    else:
        return None
    cpf = [[p[axis] / 127.0 for p in cp] for axis in range(len(cp[0]))]
    bx = (frame_no - begin.frame) / (end.frame - begin.frame)
    result = []
    for axis in range(3):  # X, Y, Z
        begin_pos = begin.position[axis]
        end_pos = end.position[axis]
        pos_delta = end_pos - begin_pos
        xcp = [0.0, cpf[axis][0], cpf[axis][2], 1.0]
        t = vmdbezier.bezier3f_x2t(xcp, bx)
        ycp = [0.0, cpf[axis][1], cpf[axis][3], 1.0]
        by = vmdbezier.bezier3f(ycp, t)
        result.append(begin_pos + pos_delta * by)
    return result


def get_frame_position(frame_no, frame_dict, element='bones'):
    begin, end = get_interval(frame_no, frame_dict)
    if begin is None or end is None:
        return None
    if begin == end:
        return frame_dict[begin].position
    return interpolate_position(
        frame_no, frame_dict[begin], frame_dict[end], element)


def get_all_position_in_interval(frame_dict, begin, end, element='bones'):
    r = end - begin
    result = list()
    for frame_no in range(1, r):
        result.append(interpolate_position(
            frame_no, frame_dict[begin], frame_dict[end], element))
    return result


LERP_CONTROLPOINTS = [20, 20, 107, 107]
PARABOLA1_CONTROLPOINTS = [
    int(round(x * 127, 0))
    for outer in vmdbezier.PARABOLA1[1:3] for x in outer]
PARABOLA2_CONTROLPOINTS = [
    int(round(x * 127, 0))
    for outer in vmdbezier.PARABOLA2[1:3] for x in outer]
SINE1_CONTROLPOINTS = [
    int(round(x * 127, 0))
    for outer in
    [(p[0] / vmdbezier.SINE1[3][0], p[1]) for p in vmdbezier.SINE1[1:3]]
    for x in outer]
SINE2_CONTROLPOINTS = [
    int(round(x * 127, 0))
    for outer in
    [(p[0] / vmdbezier.SINE2[3][0], p[1]) for p in vmdbezier.SINE2[1:3]]
    for x in outer]


# in place of numpy


def dot_v(v1, v2):
    return sum([i * j for i, j in zip(v1, v2)])


def cross_v3(v1, v2):
    def e(x, y):
        return v1[x] * v2[y] - v1[y] * v2[x]

    return [e(*p) for p in [[(i + j) % 3 for j in range(1, 3)]
            for i in range(3)]]


def scale_v(v, scale):
    return [i * scale for i in v]


def add_v(v1, v2):
    return [a + b for a, b in zip(v1, v2)]


def sub_v(a, b):
    return [a - b for a, b in zip(a, b)]


def rotate_v2(v, rad):
    c = math.cos(rad)
    s = math.sin(rad)
    return [c * v[0] - s * v[1], s * v[0] + c * v[1]]


def norm_v(v):
    r = math.sqrt(dot_v(v, v))
    return r if r > EPS else 0


def normalize_v(v):
    n = dot_v(v, v)
    n = math.sqrt(n)
    if n > EPS:
        return [i / n for i in v]
    else:
        return v


def bool2sign(b):
    return 1 if b else -1


def project_v(v, axis):
    v = list(v)
    if isinstance(axis, Iterable):  # axis = vector
        norm2 = dot_v(axis, axis)
        if 0 == norm2:
            return None
        m = dot_v(v, axis) / norm2
        return [m * i for i in axis]
    else:  # axis = 0:x or 1:y, 2:z
        axis = axis if axis > 0 else 0
        axis = axis if axis < len(v) - 1 else len(v) - 1
        return [0 for i in v[:axis]] + [v[axis]] + [0 for i in v[axis + 1:]]


def project_to_plane_v(v, axis):
        return sub_v(v, project_v(v, axis))


def angle_v(v1, v2):
    n1 = norm_v(v1)
    n2 = norm_v(v2)
    if 0 == n1 or 0 == n2:
        return None
    else:
        return math.atan2(
            norm_v(cross_v3(v1, v2)), dot_v(v1, v2))


def lerp_v(v1, v2, t):
    vr = scale_v(sub_v(v2, v1), t)
    return add_v(v1, vr)


def look_at(v1dir, v1up, v2, gup=None):
    v2proj = project_to_plane_v(v2, v1up)
    yaw_angle = angle_v(v1dir, v2proj)
    if yaw_angle:
        yaw_sign = 1 if dot_v(cross_v3(v1dir, v2proj), v1up) >= 0 else -1
    else:
        yaw_angle = 0
        yaw_sign = 1
    pitch_angle = angle_v(v2, v2proj)
    if pitch_angle:
        v2x = cross_v3(v1up, v2proj)
        pitch_sign = 1 if dot_v(cross_v3(v2, v2proj), v2x) >= 0 else -1
    else:
        pitch_angle = 0
        pitch_sign = 1
    if gup:
        v1up_proj = project_to_plane_v(v1up, v2)
        gup_proj = project_to_plane_v(gup, v2)
        roll_angle = angle_v(v1up_proj, gup_proj)
        roll_sign = 1 if dot_v(cross_v3(gup_proj, v1up_proj), v2) >= 0 else -1
    else:
        roll_angle = 0
        roll_sign = 1
    return (pitch_angle * pitch_sign,
            yaw_angle * yaw_sign,
            roll_angle * roll_sign)


def look_at_fixed_axis(v1dir, v1up, v2, gup=None):
    v1proj = project_to_plane_v(v1dir, v1up)
    v2proj = project_to_plane_v(v2, v1up)
    angle = angle_v(v1proj, v2proj)
    if angle:
        sign = 1 if dot_v(cross_v3(v1dir, v2proj), v1up) >= 0 else -1
    else:
        angle = 0
        sign = 1
    return angle * sign


def transpose_m(m):
    return [[i[j] for i in m] for j in range(len(m[0]))]


def dot_m(m1, m2):
    m1t = transpose_m(m1)
    return [[dot_v(i, j) for j in m1t] for i in m2]


def quaternion(v, rad):
    norm = norm_v(v)
    c = math.cos(rad / 2)
    s = math.sin(rad / 2)
    if norm == 0:
        norm = 1
    return [i * s / norm for i in v] + [c]


def conjugate_q(q):
    return [-q[0], -q[1], -q[2], q[3]]


def inverse_q(q):
    return scale_v(conjugate_q(q), 1 / norm_v(q))


def multiply_quaternion(b, a):
    wa = a[3]
    wb = b[3]
    va = (a[0], a[1], a[2])
    vb = (b[0], b[1], b[2])
    wr = wa * wb - dot_v(va, vb)
    vr = add_v(add_v(scale_v(vb, wa), scale_v(va, wb)), cross_v3(va, vb))
    return vr + [wr]


def mirror_quaternion(rotation, plane='yz'):
    if 'yz' == plane:
        return [-rotation[0], rotation[1], rotation[2], -rotation[3]]
    else:  # not impelemnted
        return None


def compose_quaternion(current, v, rad, local=True):
    r = quaternion(v, rad)
    return (
        multiply_quaternion(r, current) if local else
        multiply_quaternion(current, r))


def rotate_v3q(v, q):
    v = list(v) + [0]
    return multiply_quaternion(
        multiply_quaternion(conjugate_q(q), v), q)[:3]


def diff_q(q1, q2):
    return multiply_quaternion(inverse_q(q1), q2)


def quaternion_to_matrix(q):
    i, j, k, w = q
    return [
        [1 - 2 * (j * j + k * k), 2 * (i * j - k * w), 2 * (i * k + j * w)],
        [2 * (i * j + k * w), 1 - 2 * (i * i + k * k), 2 * (j * k - i * w)],
        [2 * (i * k - j * w), 2 * (j * k + i * w), 1 - 2 * (i * i + j * j)]
    ]


def euler_to_quaternion(euler):  # zxy -> quaternion
    pitch, yaw, roll = euler
    cy = math.cos(yaw / 2.0)
    cp = math.cos(pitch / 2.0)
    cr = math.cos(roll / 2.0)
    sy = math.sin(yaw / 2.0)
    sp = math.sin(pitch / 2.0)
    sr = math.sin(roll / 2.0)

    x = cp * sy * sr + cy * cr * sp
    y = cp * cr * sy - cy * sp * sr
    z = cp * cy * sr - cr * sp * sy
    w = sp * sy * sr + cp * cy * cr

    return x, y, z, w


def e2q(pitch, yaw, roll):  # another zxy
    ry = quaternion((0, 1, 0), yaw)
    rp = quaternion((1, 0, 0), pitch)
    rr = quaternion((0, 0, 1), roll)
    return multiply_quaternion(
        multiply_quaternion(rr, rp), ry)


def euler_to_matrix(euler):
    x, y, z = euler
    cx = math.cos(x)
    cy = math.cos(y)
    cz = math.cos(z)
    sx = math.sin(x)
    sy = math.sin(y)
    sz = math.sin(z)
    return [
        [cy * cz + sy * sx * sz, cy * -sz + sy * sx * cz, sy * cx],
        [cx * sz, cx * cz, -sx],
        [-sy * cz + cy * sx * sz, sy * sz + cy * sx * cz, cy * cx]
    ]


def quaternion_to_euler(q):  # for debug
    m = quaternion_to_matrix(q)
    # -sx = m[1][2]
    # sy/cy = m[0][2]/m[2][2]
    # sz/cz = m[1][0]/m[1][1]
    # if -sx == 0
    return (
        -math.asin(m[1][2]), math.atan2(m[0][2], m[2][2]),
        math.atan2(m[1][0], m[1][1]))


def slerp_q(q1, q2, t):
    dot = dot_v(q1, q2)
    if dot < 0:
        qx = [-i for i in q2]
        dot = -dot
    else:
        qx = q2
    if dot < 0.995:
        angle = math.acos(dot)
        # (q1 * sin(angle * (1-t)) + qx * sin(angle * t))/sin(angle)
        return scale_v(add_v(
            scale_v(q1, math.sin(angle * (1 - t))),
            scale_v(qx, math.sin(angle * t))), 1 / math.sin(angle))
    else:
        return lerp_v(q1, qx, t)


def scale_q(q, t):
    return slerp_q(QUATERNION_IDENTITY, q, t)


def interpolate_rotation(frame_no, begin, end, element='bones'):
    if element == 'bones':
        cp = vmddef.bone_vmdformat_to_controlpoints(end.interpolation)
    elif element == 'cameras':
        cp = vmddef.camera_vmdformat_to_controlpoints(end.interpolation)
    else:
        return None
    cpf = [[p[axis] / 127.0 for p in cp] for axis in range(len(cp[0]))]
    bx = (frame_no - begin.frame) / (end.frame - begin.frame)
    xcp = [0.0, cpf[3][0], cpf[3][2], 1.0]
    t = vmdbezier.bezier3f_x2t(xcp, bx)
    ycp = [0.0, cpf[3][1], cpf[3][3], 1.0]
    by = vmdbezier.bezier3f(ycp, t)
    if 'bones' == element:
        return slerp_q(begin.rotation, end.rotation, by)
    else:
        return lerp_v(begin.rotation, end.rotation, by)


def interpolate_camera_distance(frame_no, begin, end):
    cp = vmddef.camera_vmdformat_to_controlpoints(end.interpolation)
    cpf = [[p[axis] / 127.0 for p in cp] for axis in range(len(cp[0]))]
    bx = (frame_no - begin.frame) / (end.frame - begin.frame)
    xcp = [0.0, cpf[4][0], cpf[4][2], 1.0]
    t = vmdbezier.bezier3f_x2t(xcp, bx)
    ycp = [0.0, cpf[4][1], cpf[4][3], 1.0]
    by = vmdbezier.bezier3f(ycp, t)
    return lerp_v([begin.distance], [end.distance], by)[0]


def mirror_frame(frame, plane='yz'):
    if 'yz' == plane:
        pos = (-frame.position[0], frame.position[1], frame.position[2])
        if 'name' in frame._fields:
            rotation = mirror_quaternion(frame.rotation, plane)
            new_name = b_to_str(frame.name)
            if new_name[0] == vmddef.RIGHT:
                new_name = vmddef.LEFT + new_name[1:]
            elif new_name[0] == vmddef.LEFT:
                new_name = vmddef.RIGHT + new_name[1:]
            new_name = new_name.encode(vmddef.ENCODING)
            return frame._replace(
                name=new_name, position=pos, rotation=rotation)
        else:
            # camera
            rotation = (frame.rotation[0], -frame.rotation[1],
                        frame.rotation[2])
            return frame._replace(position=pos, rotation=rotation)
    else:
        return None  # not implemented


def pp_q(q):  # for debug
    e = quaternion_to_euler(q)
    return [round(math.degrees(x), 4) for x in e]
