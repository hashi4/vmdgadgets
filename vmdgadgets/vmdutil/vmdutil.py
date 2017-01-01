'''utilites for handling vmd files and motions

'''
import math
import bisect
from collections import defaultdict
from . import vmddef
from . import vmdbezier


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
        cp = vmddef.get_bone_controlpoints(end)
    elif element == 'cameras':
        cp = vmddef.get_camera_controlpoints(end)
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
# import functools
# def dot_v(*p):
#    return sum([functools.reduce(lambda x, y : x * y, c) for c in zip(*p)]])


def cross_v3(v1, v2):
    def e(x, y):
        return v1[x] * v2[y] - v1[y] * v2[x]

    return [e(*p) for p in [[(i + j) % 3 for j in range(1, 3)]
            for i in range(3)]]


def scale_v(v, scale):
    return map(lambda x: x * scale, v)


def add_v(v1, v2):
    return [a + b for a, b in zip(v1, v2)]


def sub_v(a, b):
    return [a - b for a, b in zip(a, b)]


def rotate_v2(v, rad):
    c = math.cos(rad)
    s = math.sin(rad)
    return (c * v[0] - s * v[1], s * v[0] + c * v[1])


def normalize_v(v):
    n = sum(map(lambda i: i ** 2, v))
    if 1.0 == n:
        return v
    n = math.sqrt(n)
    return map(lambda i: i / n, v)


def transpose_m(m):
    return [[i[j] for i in m] for j in range(len(m[0]))]


def dot_m(m1, m2):
    m1t = transpose_m(m1)
    return [[dot_v(i, j) for j in m1t] for i in m2]


def quaternion(v, rad):
    c = math.cos(rad / 2)
    s = math.sin(rad / 2)
    return (v[0] * s, v[1] * s, v[2] * s, c)


def conjugate_q(q):
    return (-q[0], -q[1], -q[2], q[3])


def multiply_quaternion(a, b):
    wa = a[3]
    wb = b[3]
    va = (a[0], a[1], a[2])
    vb = (b[0], b[1], b[2])
    wr = wa * wb - dot_v(va, vb)
    vr = add_v(scale_v(vb, wa), scale_v(va, wb))
    vr = add_v(vr, cross_v3(va, vb))
    return (vr[0], vr[1], vr[2], wr)


def mirror_quaternion(rotation, plane='yz'):
    if 'yz' == plane:
        return (-rotation[0], rotation[1], rotation[2], -rotation[3])
    else:  # not impelemnted
        return None


def compose_quaternion(current, v, rad, local=True):
    v = normalize_v(v)
    r = quaternion(v, rad)
    return (
        multiply_quaternion(current, r) if local else
        multiply_quaternion(r, current))


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
