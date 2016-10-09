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


def get_bone_controlpoints(p):
    '''
        byte[64] -> [
            c1x[X,Y,Z,R], c1y[X,Y,Z,R],
            c2x[X,Y,Z,R], c2y[X,Y,Z,R]
        ]
    '''
    points = p.interpolation
    pos = [0, 4, 8, 12]
    offset = 16
    result = [[points[i + offset * j] for j in range(4)] for i in pos]
    return result

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
    'frame distance position rotation interpolation viewing_angle perspective')


def unpack_camera(buf, offset=0):
    cf = camera_def.unpack_from(buf, offset)
    return camera._make(
        (cf[0], cf[1], cf[2:5], cf[5:8], cf[8:32], cf[32], cf[33]))


def pack_camera(p):
    expanded = (p.frame, p.distance)\
        + p.position + p.rotation + p.interpolation\
        + (p.viewing_angle, p.perspective)
    return camera_def.pack(*expanded)


def get_camera_controlpoints(p):
    '''
        byte[24] -> [
            c1x[X,Y,Z,R,D,V], c1y[X,Y,Z,R,D,V],
            c2x[X,Y,Z,R,D,V], c2y[X,Y,Z,R,D,V]
        ]
    '''
    points = p.interpolation
    result = [[points[i * 4 + j] for i in range(6)] for j in range(4)]
    return [result[0], result[2], result[1], result[3]]
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
