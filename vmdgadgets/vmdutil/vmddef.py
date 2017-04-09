'''definition of structs for vmdfile
'''
from collections import namedtuple
import struct
import codecs

ENCODING = 'shift-jis'
LEFT = '左'
RIGHT = '右'

# # pragma pack (1)
#
# typedef struct VmdHeader_t {
#     char vmdHeader[30]; // "Vocaloid Motion Data 0002"
#     char vmdModelName[20];
# } VmdHeader;
header_def = struct.Struct('<30s20s')
header = namedtuple('header', 'header model_name')
HEADER1 = codecs.encode(u'Vocaloid Motion Data 0002', 'shift-jis')
HEADER2_CAMERA = codecs.encode(u'カメラ・照明\0on Data', 'shift-jis')


def unpack_header(buf, offset=0):
    return header._make(
        header_def.unpack_from(buf, offset))


def pack_header(p):
    return header_def.pack(*p)


#
# typedef struct VmdCount_t {
#     uint32_t count;
# } VmdCount;
#
count_def = struct.Struct('<1I')
count = namedtuple('count', 'count')


def unpack_count(buf, offset=0):
    return count._make(
        count_def.unpack_from(buf, offset))


def pack_count(p):
    return count_def.pack(*p)


# typedef struct VmdBoneFrame_t {
#     char name[15];
#     uint32_t frame;
#     float position[3];
#     float rotatation[4];
#     uint8_t interpolation[64];
# } VmdBoneFrame;
#
bone_def = struct.Struct('<15s1I3f4f64B')
bone = namedtuple(
    'bone',
    'name frame position rotation interpolation')


def unpack_bone(buf, offset=0):
    bf = bone_def.unpack_from(buf, offset)
    return bone._make(
        (bf[0], bf[1], bf[2:5], bf[5:9], bf[9:]))


def pack_bone(p):
    expanded = (p.name, p.frame) + p.position + p.rotation + p.interpolation
    return bone_def.pack(*expanded)


def bone_vmdformat_to_controlpoints(interpolation):
    '''
        byte[64] -> [
            c1x[X,Y,Z,R], c1y[X,Y,Z,R],
            c2x[X,Y,Z,R], c2y[X,Y,Z,R]
        ]
    '''
    pos = [0, 4, 8, 12]
    offset = 16
    result = [[interpolation[i + offset * j] for j in range(4)] for i in pos]
    return result


BONE_LERP_CONTROLPOINTS = [
    [20, 20, 20, 20], [20, 20, 20, 20],
    [107, 107, 107, 107], [107, 107, 107, 107]]

BONE_LERP_INTERPOLATION = (
    20, 20, 0, 0, 20, 20, 20, 20,
    107, 107, 107, 107, 107, 107, 107, 107,
    20, 20, 20, 20, 20, 20, 20,
    107, 107, 107, 107, 107, 107, 107, 107,
    0,
    20, 20, 20, 20, 20, 20,
    107, 107, 107, 107, 107, 107, 107, 107,
    0, 0,
    20, 20, 20, 20, 20,
    107, 107, 107, 107, 107, 107, 107, 107,
    0, 0, 0)


def bone_controlpoints_to_vmdformat(control_points):
    '''
        c1x[X,Y,Z,R], c1y[X,Y,Z,R], c2x[X,Y,Z,R], c2y[X,Y,Z,R]
        ->
        c1x[X,Y,   ], 00,00, c1y[X,Y,Z,R],
        c2x[X,Y,Z,R], c2y[X,Y,Z,R],

        c1x[  Y,Z,R], c1y[X,Y,Z,R],
        c2x[X,Y,Z,R], c2y[X,Y,Z,R],
        00,
        c1x[    Z,R], c1y[X,Y,Z,R],
        c2x[X,Y,Z,R], c2y[X,Y,Z,R],
        00, 00,
        c1x[      R], c1y[X,Y,Z,R],
        c2x[X,Y,Z,R], c2y[X,Y,Z,R],
        00,00,00(?),
    '''
    result = list()
    c = control_points
    c13 = c[1] + c[2] + c[3]
    result.extend(c[0][:2])
    result.extend([0, 0] + c13)
    result.extend(c[0][1:] + c13)
    result.append(0)
    result.extend(c[0][2:] + c13)
    result.extend([0, 0])
    result.extend(c[0][3:] + c13)
    result.extend([0, 0, 0])
    return tuple(result)


BONE_SAMPLE = bone(
    '全ての親'.encode(ENCODING), 0, (0, 0, 0),
    (0, 0, 0, 1), BONE_LERP_INTERPOLATION)


# typedef struct VmdMorphFrame_t {
#     char name[15];
#     uint32_t frame;
#     float weight;
# } VmdMorphFrame;
#
morph_def = struct.Struct('<15s1I1f')
morph = namedtuple('morph', 'name frame weight')


def unpack_morph(buf, offset=0):
    return morph._make(
        morph_def.unpack_from(buf, offset))


def pack_morph(p):
    return morph_def.pack(*p)


# typedef struct VmdCameraFrame {
#     uint32_t frame;
#     float distance;
#     float position[3];
#     float rotation[3];
#     uint8_t interpolation[24];
#     uint32_t viewingAngle;
#     uint8_t perspective;
# } VmdCameraFrame;
camera_def = struct.Struct('<1I1f3f3f24B1I1B')
camera = namedtuple(
    'camera',
    'frame distance position rotation interpolation angle_of_view perspective')


def unpack_camera(buf, offset=0):
    cf = camera_def.unpack_from(buf, offset)
    return camera._make(
        (cf[0], cf[1], cf[2:5], cf[5:8], cf[8:32], cf[32], cf[33]))


def pack_camera(p):
    expanded = (p.frame, p.distance)\
        + p.position + p.rotation + p.interpolation\
        + (p.angle_of_view, p.perspective)
    return camera_def.pack(*expanded)


def camera_vmdformat_to_controlpoints(interpolation):
    '''
        byte[24] -> [
            c1x[X,Y,Z,R,D,V], c1y[X,Y,Z,R,D,V],
            c2x[X,Y,Z,R,D,V], c2y[X,Y,Z,R,D,V]
        ]
    '''
    result = [[interpolation[i * 4 + j] for i in range(6)] for j in range(4)]
    return [result[0], result[2], result[1], result[3]]


CAMERA_LERP_CONTROLPOINTS = [
    [20, 20, 20, 20, 20, 20], [20, 20, 20, 20, 20, 20],
    [107, 107, 107, 107, 107, 107], [107, 107, 107, 107, 107, 107]]

CAMERA_LERP_INTERPOLATION = (
    20, 107, 20, 107, 20, 107, 20, 107,
    20, 107, 20, 107, 20, 107, 20, 107,
    20, 107, 20, 107, 20, 107, 20, 107)


def camera_controlpoints_to_vmdformat(control_points):
    '''
        c1x[X,Y,Z,R,D,V], c1y[X,Y,Z,R,D,V],
        c2x[X,Y,Z,R,D,V], c2y][X,Y,Z,R,D,V]
        ->
        X[c1x, c2x, c1y, c2y], Y[c1x, c2x, c1y, c2y],
        Z[c1x, c2x, c1y, c2y], R[c1x, c2x, c1y, c2y],
        D[c1x, c2x, c1y, c2y], V[c1x, c2x, c1y, c2y]
    '''
    cp = [control_points[0], control_points[2],
          control_points[1], control_points[3]]
    return tuple([cp[i][j] for j in range(6) for i in range(4)])


CAMERA_SAMPLE = camera(
    0, -45, (0, 10, 0), (0, 0, 0), CAMERA_LERP_INTERPOLATION, 30, 0)


#
# typedef struct VmdLightFrame_t {
#     uint32_t frame;
#     float rgb[3];
#     float direction[3];
# } VmdLightFrame;

light_def = struct.Struct('<1I3f3f')
light = namedtuple('light', 'frame rgb direction')


def unpack_light(buf, offset=0):
    lf = light_def.unpack_from(buf, offset)
    return light._make(
        (lf[0], lf[1:4], lf[4:7]))


def pack_light(p):
    expanded = (p.frame,) + p.rgb + p.direction
    return light_def.pack(*expanded)


LIGHT_SAMPLE = light(
    frame=0, rgb=(0.6019999980926514, 0.6019999980926514, 0.6019999980926514),
    direction=(-0.5, -1.0, 0.5))
#
# typedef struct VmdSelfShadowFrame_t {
#     uint32_t frame;
#     uint8_t type;
#     float distance;
# } VmdSelfShadow;

selfshadow_def = struct.Struct('<1I1B1f')
selfshadow = namedtuple(
    'selfshadow', 'frame type distance')


def unpack_selfshadow(buf, offset=0):
    return selfshadow._make(
        selfshadow_def.unpack_from(buf, offset))


def pack_selfshadow(p):
    return selfshadow_def.pack(*p)


# typedef struct VmdIKInfo_t {
#     char name[20];
#     uint8_t on_off;
# } VmdIKInfo;
ikinfo_def = struct.Struct('<20s1B')
ikinfo = namedtuple('ikinfo', 'name on_off')


def unpack_ikinfo(buf, offset=0):
    return ikinfo._make(
        ikinfo_def.unpack_from(buf, offset))


def pack_ikinfo(p):
    return ikinfo_def.pack(*p)


# typedef struct VmdShowIKFrame_t {
#     uint32_t frame;
#     uint8_t show;
#     uint32_t ik_count;
#     VmdIKInfo iks[];
# } VmdShowIKFrame;
# # pragma pack()
showik_def = struct.Struct('<1I1B1I')
showik = namedtuple('showik', 'frame show ik_count iks')


def unpack_showik(buf, offset=0):
    ikf = showik_def.unpack_from(buf, offset)
    offset += showik_def.size
    iks = []
    for i in range(ikf[2]):
        iks.append(unpack_ikinfo(buf, offset))
        offset += ikinfo_def.size
    return showik._make((*ikf, tuple(iks)))


def pack_showik(p):
    buf = bytearray()
    ikf = p[:-1]
    iks = p[-1]
    buf += showik_def.pack(*ikf)
    for ik in iks:
        buf += pack_ikinfo(ik)
    return buf


dummy_struct = struct.Struct('')


def dummy_unpack(buf, offset=0):
    return (),


def dummy_pack(p):
    return b''


VMD_ELEMENTS = (
    'bones', 'morphs', 'cameras', 'lights',
    'selfshadows', 'showiks')

# (size, pack, unpack)
VMD_IO_UTIL = {
    VMD_ELEMENTS[0]: (
        lambda f: bone_def.size,
        pack_bone, unpack_bone),
    VMD_ELEMENTS[1]: (
        lambda f: morph_def.size,
        pack_morph, unpack_morph),
    VMD_ELEMENTS[2]: (
        lambda f: camera_def.size,
        pack_camera, unpack_camera),
    VMD_ELEMENTS[3]: (
        lambda f: light_def.size,
        pack_light, unpack_light),
    VMD_ELEMENTS[4]: (
        lambda f: selfshadow_def.size,
        pack_selfshadow, unpack_selfshadow),
    VMD_ELEMENTS[5]: (
        lambda f: showik_def.size +
        f.ik_count * ikinfo_def.size,
        pack_showik, unpack_showik),
}
