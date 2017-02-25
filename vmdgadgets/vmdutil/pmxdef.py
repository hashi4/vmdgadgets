''' definition of structs for pmx file format
'''

from collections import namedtuple
from collections import Iterable
from itertools import chain
import struct

PMX_HEADER = b'PMX '
# utf-16: little endian, without BOM
PMX_ENCODING = {0: 'utf-16le', 1: 'utf-8'}
INDEX_FORMAT = {
    1: 'b',
    2: 'h',
    4: 'i',
}
INDEX_FORMAT_VERTEX = {
    1: 'B',
    2: 'H',
    4: 'i',  # signed
}


PMX_ELEMENTS = (
    'vertexes', 'faces', 'textures', 'materials',
    'bones', 'morphs', 'disp_nodes', 'rigid_bodies', 'joints',
    'soft_bodies',  # 2.1
)


def b_to_str(b, encoding=PMX_ENCODING[0]):
    return b.decode(encoding)


def unpack_string(buf, offset=0, encoding=PMX_ENCODING[0]):
    length = struct.unpack_from('<i', buf, offset)[0]
    size = struct.calcsize('<i')
    pack_format = '<{0}s'.format(length)
    s = struct.unpack_from(pack_format, buf, offset + size)[0]
    size += struct.calcsize(pack_format)
    return s.decode(encoding), size


def pack_string(s, encoding=PMX_ENCODING[0]):
    result = bytearray()
    b = s.encode(encoding)
    result += struct.pack('<i', len(b))
    result += b
    return result


def unpack_name(header, buf, offset=0):
    size = 0
    name_jp, s = unpack_string(buf, offset, PMX_ENCODING[header.encoding])
    size += s
    name_en, s = unpack_string(
        buf, offset + size, PMX_ENCODING[header.encoding])
    size += s
    return name_jp, name_en, size


def pack_name(header, p):
    result = bytearray()
    result += pack_string(p.name_jp, PMX_ENCODING[header.encoding])
    result += pack_string(p.name_en, PMX_ENCODING[header.encoding])
    return result


count_def = struct.Struct('<1i')
count = namedtuple('count', 'count')


def unpack_count(buf, offset=0):
    return count._make(count_def.unpack_from(buf, offset)), count_def.size


def pack_count(p):
    return count_def.pack(*p)


# ############
# header
# ############

header_def = struct.Struct('<4s1f9B')
header = namedtuple('header', [
    'header', 'version',  'eight', 'encoding', 'n_exuvs',
    'vertex_isize', 'texture_isize', 'material_isize', 'bone_isize',
    'morph_isize', 'rigid_body_isize'])


def unpack_header(buf, offset=0):
    return header._make(header_def.unpack_from(buf, offset)), header_def.size


def pack_header(p):
    return header_def.pack(*p)


def is_valid_header(header):
    return (
        header.header == PMX_HEADER and
        (round(header.version, 1) == 2.1 or round(header.version, 1) == 2.0))


def get_encoding(header):
    return PMX_ENCODING[header.encoding]


# ############
# model information
# ############
model_info = namedtuple(
    'model_info', 'name_jp, name_en, info_jp, info_en')


def unpack_model_info(header, buf, offset=0):
    strings = list()
    size = 0
    encoding = PMX_ENCODING[header.encoding]
    for field in model_info._fields:
        text, bufsiz = unpack_string(buf, offset + size, encoding)
        size += bufsiz
        strings.append(text)
    return model_info._make(strings), size


def pack_model_info(header, p):
    encoding = PMX_ENCODING[header.encoding]
    result = bytearray()
    for s in p:
        b = pack_string(s, encoding)
        result += b
    return result


# ############
# vertexes
# ############
vertex_fixed = struct.Struct('<3f3f2f')
vertex = namedtuple(
    'vertex',
    'position normal uv ex_uvs weight_type weight edge_mag')
# position, normal: (x, y, z)
# ex_uvs: ((x, y, z), (x, y, z)...)

WEIGHT_FORMAT = (
    '<1{0}',  # BDEF1
    '<1{0}1{0}1f',  # BDEF2
    '<1{0}1{0}1{0}1{0}1f1f1f1f',  # BDEF4
    '<1{0}1{0}1f3f3f3f',  # SDEF
    '<1{0}1{0}1{0}1{0}1f1f1f1f',  # QDEF
)

vertex_bdef1 = namedtuple('bdef1', 'bone1')
vertex_bdef2 = namedtuple('bdef2', 'bone1 bone2 weight1')
vertex_bdef4 = namedtuple(
    'bdef4', 'bone1 bone2 bone3 bone4 weight1 weight2 weight3 weight4')
vertex_sdef = namedtuple('sdef', 'bone1 bone2 weight1 c r0 r1')
vertex_qdef = namedtuple(
    'qdef', 'bone1 bone2 bone3 bone4 weight1 weight2 weight3 weight4')
WEIGHT_TUPLE = (
    vertex_bdef1, vertex_bdef2, vertex_bdef4, vertex_sdef, vertex_qdef
)


def flatten_composite(*p):
    for it in p:
        if isinstance(it, Iterable):
            for e in it:
                yield e
        else:
            yield it


def group_tuple(pack_format, p):
    # #### number < 10 #####
    index = 0
    result = list()
    for i in pack_format:
        if i.isdigit():
            n = int(i)
            if n == 1:
                result.append(p[index])
            else:
                result.append(p[index:index + n])
            index += n
    return tuple(result)


def unpack_vertexweight(weight_type, bone_isize, buf, offset):
    pack_format = WEIGHT_FORMAT[weight_type].format(
        INDEX_FORMAT[bone_isize])
    p = struct.unpack_from(pack_format, buf, offset)
    return WEIGHT_TUPLE[weight_type]._make(
            group_tuple(pack_format, p)), struct.calcsize(pack_format)


def pack_vertexweight(weight_type, bone_isize, p):
    pack_format = WEIGHT_FORMAT[weight_type].format(
        INDEX_FORMAT[bone_isize])
    return struct.pack(pack_format, *flatten_composite(*p))


def unpack_vertex(header, buf, offset=0):
    size = 0
    p = vertex_fixed.unpack_from(buf, offset)
    position, normal, uv = group_tuple(vertex_fixed.format.decode(), p)
    size += vertex_fixed.size

    ex_uvs = list()
    for i in range(header.n_exuvs):
        ex_uvs.append(
            struct.unpack_from('<4f', buf, offset + size))
        size += struct.calcsize('<4f')
    ex_uvs = tuple(ex_uvs)

    weight_type = struct.unpack_from('<1B', buf, offset + size)[0]
    size += struct.calcsize('<1B')

    weight, weight_size = unpack_vertexweight(
        weight_type, header.bone_isize, buf, offset + size)
    size += weight_size
    edge_mag = struct.unpack_from('<1f', buf, offset + size)[0]
    size += struct.calcsize('<1f')
    return (
        vertex(
            position, normal, uv, ex_uvs, weight_type,
            weight, edge_mag),
        size)


def pack_vertex(header, p):
    result = bytearray()
    leading_part = p.position + p.normal + p.uv
    result += vertex_fixed.pack(*leading_part)
    for uv in p.ex_uvs:
        result += struct.pack('<4f', *p)
    result += struct.pack('<1B', p.weight_type)
    result += pack_vertexweight(p.weight_type, header.bone_isize, p.weight)
    result += struct.pack('<1f', p.edge_mag)
    return result


# ############
# faces
# ############
FACE_FORMAT = '<3{0}'  # 1 // 3
# face = named_tuple('face' 'vertex')


def unpack_face(header, buf, offset=0):
    pack_format = FACE_FORMAT.format(
        INDEX_FORMAT_VERTEX[header.vertex_isize])
    return (struct.unpack_from(pack_format, buf, offset),
            struct.calcsize(pack_format))


def pack_face(header, p):
    pack_format = FACE_FORMAT.format(
        INDEX_FORMAT_VERTEX[header.vertex_isize])
    return struct.pack(pack_format, *p)


# ############
# textures
# ############
texture = namedtuple(
    'texture', 'path')


def unpack_texture(header, buf, offset=0):
    text, size = unpack_string(buf, offset, PMX_ENCODING[header.encoding])
    return texture(text), size


def pack_texture(header, p):
    return pack_string(*p, PMX_ENCODING[header.encoding])


# ############
# materials
# ############
material = namedtuple(
    'material',
    'name_jp name_en diffuse specular specular_coef ambient draw_flag ' +
    'edge_color edge_size texture sphere_texture sphere_mode ' +
    'toon_flag toon_texture memo n_face_vertexes')

material_fixed1 = struct.Struct('<4f3f1f3f1B4f1f')
material_fixed2 = struct.Struct('<2B')


def unpack_material_fixed1(buf, offset):
    p = material_fixed1.unpack_from(buf, offset)
    return group_tuple(
        material_fixed1.format.decode(), p), material_fixed1.size


def unpack_material(header, buf, offset=0):
    size = 0
    name_jp, name_en, s = unpack_name(header, buf, offset)
    size += s

    fixed1, fixed1_size = unpack_material_fixed1(
        buf, offset + size)
    size += fixed1_size

    index_format = '<1{0}'.format(INDEX_FORMAT[header.texture_isize])
    texture = struct.unpack_from(index_format, buf, offset + size)[0]
    size += struct.calcsize(index_format)
    sphere_texture = struct.unpack_from(index_format, buf, offset + size)[0]
    size += struct.calcsize(index_format)

    sphere_mode, toon_flag = material_fixed2.unpack_from(buf, offset + size)
    size += material_fixed2.size
    if 0 == toon_flag:
        toon_texture = struct.unpack_from(
            index_format, buf, offset + size)[0]
        size += struct.calcsize(index_format)
    else:  # 1
        toon_texture = struct.unpack_from('<1B', buf, offset + size)[0]
        size += struct.calcsize('<1B')
    memo, tex_len = unpack_string(
        buf, offset + size, PMX_ENCODING[header.encoding])
    size += tex_len
    n_face_vertexes = struct.unpack_from('<1i', buf, offset + size)[0]
    size += struct.calcsize('<1i')
    return material._make(
        (name_jp, name_en) + fixed1 +
        (texture, sphere_texture, sphere_mode, toon_flag, toon_texture) +
        (memo, n_face_vertexes)), size


def pack_material(header, p):
    result = bytearray()
    result += pack_name(header, p)
    result += material_fixed1.pack(
        *p.diffuse, *p.specular, p.specular_coef, *p.ambient, p.draw_flag,
        *p.edge_color, p.edge_size)
    index_format = '<1{0}'.format(INDEX_FORMAT[header.texture_isize])
    result += struct.pack(index_format, p.texture)
    result += struct.pack(index_format, p.sphere_texture)
    result += material_fixed2.pack(p.sphere_mode, p.toon_flag)
    if 0 == p.toon_flag:
        result += struct.pack(index_format, p.toon_texture)
    else:
        result += struct.pack('<1B', p.toon_texture)
    result += pack_string(p.memo, PMX_ENCODING[header.encoding])
    result += struct.pack('<1i', p.n_face_vertexes)
    return result


# ############
# bones
# ############
bone = namedtuple(
    'bone',
    # mandatory
    'name_jp name_en position parent transform_hierarchy flag disp_dir ' +
    # optional
    'additional_transform fixed_axis local_axises ex_parent ik'
)
bone_additional_transform = namedtuple(
   'bone_additional_transform', 'parent weight')
bone_ik = namedtuple(
    'bone_ik', 'target loop angle_per_loop n_links links')
bone_ik_link = namedtuple(
    'bone_ik_link',
    # mandatory
    'link_bone angle_is_limited ' +
    # optional
    'lower upper')
# upper, lower: (x, y, z)
BONE_DISP_DIR = 0x0001
BONE_CAN_ROTATE = 0x0002
BONE_CAN_TRANSLATE = 0x0004
BONE_CAN_DISP = 0x0008
BONE_CAN_OPERATE = 0x0010
BONE_IS_IK = 0x0020
BONE_APPLY_LOCAL = 0x0080
BONE_ADD_ROTATE = 0x0100
BONE_ADD_TRANSLATE = 0x0200
BONE_AXIS_IS_FIXED = 0x0400
BONE_ASSIGN_LOCAL_AXIES = 0x0800
BONE_TRANSFORM_AFTER_PHYSICS = 0x1000
BONE_EXTERNAL_PARENT = 0x2000


def unpack_bone_disp_dir(header, flag, buf, offset=0):
    if flag & BONE_DISP_DIR == BONE_DISP_DIR:  # bone index
        pack_format = '<1{0}'.format(INDEX_FORMAT[header.bone_isize])
        return struct.unpack_from(
            pack_format, buf, offset)[0], struct.calcsize(pack_format)
    else:  # coordinates
        return struct.unpack_from(
            '<3f', buf, offset), struct.calcsize('<3f')


def pack_bone_disp_dir(header, flag, p):
    if flag & BONE_DISP_DIR == BONE_DISP_DIR:  # bone index
        pack_format = '<1{0}'.format(INDEX_FORMAT[header.bone_isize])
        return struct.pack(pack_format, p)
    else:
        return struct.pack('<3f', *p)


def unpack_bone_additional_transform(header, flag, buf, offset=0):
    if flag & (BONE_ADD_ROTATE | BONE_ADD_TRANSLATE) > 0:
        pack_format = '<1{0}1f'.format(INDEX_FORMAT[header.bone_isize])
        return bone_additional_transform._make(
            struct.unpack_from(
                pack_format, buf, offset)), struct.calcsize(pack_format)
    else:
        return None, 0


def pack_bone_additional_transform(header, flag, p):
    if flag & (BONE_ADD_ROTATE | BONE_ADD_TRANSLATE) > 0:
        pack_format = '<1{0}1f'.format(INDEX_FORMAT[header.bone_isize])
        return struct.pack(pack_format, *p)
    else:
        return bytes()


def unpack_bone_fixed_axis(header, flag, buf, offset=0):
    if flag & BONE_AXIS_IS_FIXED == BONE_AXIS_IS_FIXED:
        return struct.unpack_from(
            '<3f', buf, offset), struct.calcsize('<3f')
    else:
        return None, 0


def pack_bone_fixed_axis(header, flag, p):
    if flag & BONE_AXIS_IS_FIXED == BONE_AXIS_IS_FIXED:
        return struct.pack('<3f', *p)
    else:
        return bytes()


def unpack_bone_local_axises(header, flag, buf, offset=0):
    pack_format = '<3f3f'
    if flag & BONE_ASSIGN_LOCAL_AXIES == BONE_ASSIGN_LOCAL_AXIES:
        p = struct.unpack_from(pack_format, buf, offset)
        return group_tuple(pack_format, p), struct.calcsize(pack_format)
    else:
        return None, 0


def pack_bone_local_axies(header, flag, p):
    if flag & BONE_ASSIGN_LOCAL_AXIES == BONE_ASSIGN_LOCAL_AXIES:
        return struct.pack('<3f3f', *chain.from_iterable(p))
    else:
        return bytes()


def unpack_bone_ex_parent(header, flag, buf, offset=0):
    if flag & BONE_EXTERNAL_PARENT == BONE_EXTERNAL_PARENT:
        return struct.unpack_from(
            '<1i', buff, offset), struct.calcsize('<1i')
    else:
        return None, 0


def pack_bone_ex_parent(header, flag, p):
    if flag & BONE_EXTERNAL_PARENT == BONE_EXTERNAL_PARENT:
        return struct.pack('<1i', p)
    else:
        return bytes()


def unpack_bone_ik(header, flag, buf, offset=0):
    index_format = '<1{0}'.format(INDEX_FORMAT[header.bone_isize])
    size = 0
    if flag & BONE_IS_IK == BONE_IS_IK:
        target = struct.unpack_from(index_format, buf, offset + size)[0]
        size += struct.calcsize(index_format)
        loop, angle_per_loop, n_links = struct.unpack_from(
            '<1i1f1i', buf, offset + size)
        size += struct.calcsize('<1i1f1i')
        links = list()
        for i in range(n_links):
            link_bone = struct.unpack_from(
                index_format, buf, offset + size)[0]
            size += struct.calcsize(index_format)
            angle_is_limited = struct.unpack_from(
                '<1B', buf, offset + size)[0]
            size += struct.calcsize('<1B')
            if angle_is_limited > 0:
                limit_angle = struct.unpack_from('<3f3f', buf, offset + size)
                size += struct.calcsize('<3f3f')
                lower = limit_angle[0:3]
                upper = limit_angle[3:6]
            else:
                lower = None
                upper = None
            links.append(bone_ik_link(
                link_bone, angle_is_limited, lower, upper))
        links = tuple(links)
        return bone_ik(
            target, loop, angle_per_loop, n_links, links), size
    else:
        return None, 0


def pack_bone_ik(header, flag, p):
    index_format = '<1{0}'.format(INDEX_FORMAT[header.bone_isize])
    if flag & BONE_IS_IK == BONE_IS_IK:
        result = bytearray()
        result += struct.pack(index_format, p.target)
        result += struct.pack(
            '<1i1f1i', p.loop, p.angle_per_loop, p.n_links)
        for link in p.links:
            result += struct.pack(index_format, link.link_bone)
            result += struct.pack('<1B', link.angle_is_limited)
            if link.angle_is_limited > 0:
                result += struct.pack('<3f3f', *link.lower, *link.upper)
        return result
    else:
        return bytes()


def unpack_bone(header, buf, offset=0):
    size = 0
    name_jp, name_en, s = unpack_name(header, buf, offset)
    size += s
    pack_format = '<3f1{0}1i1H'.format(INDEX_FORMAT[header.bone_isize])
    p = struct.unpack_from(pack_format, buf, offset + size)
    size += struct.calcsize(pack_format)
    position, parent, transform_hierarchy, flag = group_tuple(
        pack_format, p)

    disp_dir, s = unpack_bone_disp_dir(header, flag, buf, offset + size)
    size += s
    additional_transform, s = unpack_bone_additional_transform(
        header, flag, buf, offset + size)
    size += s
    fixed_axis, s = unpack_bone_fixed_axis(
        header, flag, buf, offset + size)
    size += s
    local_axies, s = unpack_bone_local_axises(
        header, flag, buf, offset + size)
    size += s
    ex_parent, s = unpack_bone_ex_parent(header, flag, buf, offset + size)
    size += s
    ik, s = unpack_bone_ik(header, flag, buf, offset + size)
    size += s
    return bone(
        name_jp, name_en, position, parent, transform_hierarchy, flag,
        disp_dir, additional_transform, fixed_axis,
        local_axies, ex_parent, ik), size


def pack_bone(header, p):
    result = bytearray()
    result += pack_name(header, p)
    result += struct.pack('<3f', *p.position)
    index_format = '<1{0}'.format(INDEX_FORMAT[header.bone_isize])
    result += struct.pack(index_format, p.parent)
    result += struct.pack('<1i', p.transform_hierarchy)
    result += struct.pack('<1H', p.flag)
    result += pack_bone_disp_dir(header, p.flag, p.disp_dir)
    result += pack_bone_additional_transform(
        header, p.flag, p.additional_transform)
    result += pack_bone_fixed_axis(header, p.flag, p.fixed_axis)
    result += pack_bone_local_axies(header, p.flag, p.local_axises)
    result += pack_bone_ex_parent(header, p.flag, p.ex_parent)
    result += pack_bone_ik(header, p.flag, p.ik)
    return result


# ############
# morphs
# ############
morph = namedtuple(
    'morph', 'name_jp name_en category morph_type n_offsets offsets')
morph_group = namedtuple(
    'morph_group', 'morph weight')
morph_vertex = namedtuple(
    'morph_vertex', 'vertex offset')
morph_bone = namedtuple(
    'morph_bone', 'bone translation rotation')
morph_uv = namedtuple(
    'morph_uv', 'vertex offset')
morph_material = namedtuple(
    'morph_material',
    'material operation diffuse specular specular_coef ' +
    'ambient edge_color edge_size texture_coef sphere_texture_coef ' +
    'toon_texture_coef')
morph_flip = namedtuple(
    'morph_flip', 'morph weight')
morph_impulse = namedtuple(
    'morph_impulse', 'rigid_body local verocity torque')
MORPH_FIXED_PACK = '<1B1B1i'
MORPH_GROUP_PACK = '<1{0}1f'
MORPH_VERTEX_PACK = '<1{0}3f'
MORPH_BONE_PACK = '<1{0}3f4f'
MORPH_UV_PACK = '<1{0}4f'
MORPH_MATERIAL_PACK = '<1{0}1B4f3f1f3f4f1f4f4f4f'
MORPH_FLIP_PACK = '<1{0}1f'
MORPH_IMPULSE_PACK = '<1{0}1B3f3f'


def unpack_group_morph(header, buf, offset=0):
    pack_format = MORPH_GROUP_PACK.format(INDEX_FORMAT[header.morph_isize])
    return (
        morph_group._make(struct.unpack_from(pack_format, buf, offset)),
        struct.calcsize(pack_format))


def pack_group_morph(header, p):
    pack_format = MORPH_GROUP_PACK.format(INDEX_FORMAT[header.morph_isize])
    return struct.pack(pack_format, *p)


def unpack_vertex_morph(header, buf, offset=0):
    pack_format = MORPH_VERTEX_PACK.format(
        INDEX_FORMAT_VERTEX[header.vertex_isize])
    p = struct.unpack_from(pack_format, buf, offset)
    return (
        morph_vertex._make(group_tuple(pack_format, p)),
        struct.calcsize(pack_format))


def pack_vertex_morph(header, p):
    pack_format = MORPH_VERTEX_PACK.format(
        INDEX_FORMAT_VERTEX[header.vertex_isize])
    return struct.pack(pack_format, *flatten_composite(*p))


def unpack_bone_morph(header, buf, offset=0):
    pack_format = MORPH_BONE_PACK.format(
        INDEX_FORMAT[header.bone_isize])
    p = struct.unpack_from(pack_format, buf, offset)
    return (
        morph_bone._make(group_tuple(pack_format, p)),
        struct.calcsize(pack_format))


def pack_bone_morph(header, p):
    pack_format = MORPH_BONE_PACK.format(
        INDEX_FORMAT[header.bone_isize])
    return struct.pack(pack_format, *flatten_composite(*p))


def unpack_uv_morph(header, buf, offset=0):
    pack_format = MORPH_UV_PACK.format(
        INDEX_FORMAT_VERTEX[header.vertex_isize])
    p = struct.unpack_from(pack_format, buf, offset)
    return (
        morph_uv._make(group_tuple(pack_format, p)),
        struct.calcsize(pack_format))


def pack_uv_morph(header, p):
    pack_format = MORPH_UV_PACK.format(
        INDEX_FORMAT_VERTEX[header.vertex_isize])
    return struct.pack(pack_format, *flatten_composite(*p))


def unpack_material_morph(header, buf, offset=0):
    pack_format = MORPH_MATERIAL_PACK.format(
        INDEX_FORMAT[header.material_isize])
    p = struct.unpack_from(pack_format, buf, offset)
    return (
        morph_material._make(group_tuple(pack_format, p)),
        struct.calcsize(pack_format))


def pack_material_morph(header, p):
    pack_format = MORPH_MATERIAL_PACK.format(
        INDEX_FORMAT[header.material_isize])
    return struct.pack(pack_format, *flatten_composite(*p))


def unpack_flip_morph(header, buf, offset=0):
    pack_format = MORPH_FLIP_PACK.format(INDEX_FORMAT[header.morph_isize])
    return (
        morph_flip._make(struct.unpack_from(pack_format, buf, offset)),
        struct.calcsize(pack_format))


def pack_flip_morph(header, p):
    pack_format = MORPH_FLIP_PACK.format(INDEX_FORMAT[header.morph_isize])
    return struct.pack(pack_format, *p)


def unpack_impulse_morph(header, buf, offset=0):
    pack_format = MORPH_IMPULSE_PACK.format(
        INDEX_FORMAT[header.rigid_body_isize])
    p = struct.unpack_from(pack_format, buf, offset)
    return (
        morph_impulse._make(group_tuple(pack_format, p)),
        struct.calcsize(pack_format))


def pack_impulse_morph(header, p):
    pack_format = MORPH_IMPULSE_PACK.format(
        INDEX_FORMAT[header.material_isize])
    return struct.pack(pack_format, *flatten_composite(*p))

MORPH_FUNCTIONS = (
    # 0 group morph
    (unpack_group_morph, pack_group_morph),
    # 1 vertex morph
    (unpack_vertex_morph, pack_vertex_morph),
    # 2 bone morph
    (unpack_bone_morph, pack_bone_morph),
    # 3 UV morph
    (unpack_uv_morph, pack_uv_morph),
    # 4 ex UV1 morph
    (unpack_uv_morph, pack_uv_morph),
    # 5 ex UV2 morph
    (unpack_uv_morph, pack_uv_morph),
    # 6 ex UV3 morph
    (unpack_uv_morph, pack_uv_morph),
    # 7 ex UV4 morph
    (unpack_uv_morph, pack_uv_morph),
    # 8 material morph
    (unpack_material_morph, pack_material_morph),
    # 9 flip morph
    (unpack_flip_morph, pack_flip_morph),
    # 10 impulse morph
    (unpack_impulse_morph, pack_impulse_morph),
)


def unpack_morph(header, buf, offset=0):
    size = 0
    name_jp, name_en, s = unpack_name(header, buf, offset)
    size += s
    category, morph_type, n_offsets = struct.unpack_from(
        MORPH_FIXED_PACK, buf, offset + size)
    size += struct.calcsize(MORPH_FIXED_PACK)
    offsets = list()
    for i in range(n_offsets):
        m, s = MORPH_FUNCTIONS[morph_type][0](header, buf, offset + size)
        offsets.append(m)
        size += s
    offsets = tuple(offsets)
    return morph(
        name_jp, name_en, category, morph_type, n_offsets, offsets), size


def pack_morph(header, p):
    result = bytearray()
    result += pack_name(header, p)
    result += struct.pack(
        MORPH_FIXED_PACK, p.category, p.morph_type, p.n_offsets)
    for offset in p.offsets:
        result += MORPH_FUNCTIONS[p.morph_type][1](header, offset)
    return result


# ############
# display nodes
# ############

disp_node = namedtuple(
    'disp_node', 'name_jp name_en ' +
    'is_special n_disp_node_items disp_node_items')
disp_node_item = namedtuple(
    'disp_node_item', 'item_type index')
DISP_NODE_FORMAT = '<1B1i'
DISP_NODE_SPECIAL = 1
DISP_NODE_NORMAL = 0
DISP_NODE_ITEM_BONE = 0
DISP_NODE_ITEM_MORPH = 1
DISP_NODE_0 = disp_node(
    'Root', 'Root', DISP_NODE_SPECIAL, 1,
    (disp_node_item(DISP_NODE_ITEM_BONE, 0),))
DISP_NODE_1 = disp_node(
    '表情', 'Exp', DISP_NODE_SPECIAL, 0, ())


def unpack_disp_node(header, buf, offset=0):
    size = 0
    name_jp, name_en, s = unpack_name(header, buf, offset)
    size += s

    is_special, n_disp_node_items = struct.unpack_from(
        DISP_NODE_FORMAT, buf, offset + size)
    size += struct.calcsize(DISP_NODE_FORMAT)
    disp_node_items = list()
    for i in range(n_disp_node_items):
        item_type = struct.unpack_from('<1B', buf, offset + size)[0]
        size += struct.calcsize('<1B')
        if item_type == DISP_NODE_ITEM_BONE:
            index_format = '<1{0}'.format(INDEX_FORMAT[header.bone_isize])
        else:
            index_format = '<1{0}'.format(INDEX_FORMAT[header.morph_isize])
        index = struct.unpack_from(index_format, buf, offset + size)[0]
        size += struct.calcsize(index_format)
        disp_node_items.append(disp_node_item(item_type, index))
    return disp_node(
        name_jp, name_en, is_special, n_disp_node_items,
        tuple(disp_node_items)), size


def pack_disp_node(header, p):
    result = bytearray()
    result += pack_name(header, p)
    result += struct.pack(DISP_NODE_FORMAT, p.is_special, p.n_disp_node_items)
    pack_format = '<1B1{0}'
    for item in p.disp_node_items:
        if item.item_type == DISP_NODE_ITEM_BONE:
            result += struct.pack(
                pack_format.format(INDEX_FORMAT[header.bone_isize]),
                *item)
        else:
            result += struct.pack(
                pack_format.format(INDEX_FORMAT[header.morph_isize]),
                *item)
    return result

# ###
# rigid bodies
# ###
rigid_body = namedtuple(
    'rigid_body', 'name_jp name_en bone group collision shape scale ' +
    'position rotation mass lin_damping ang_damping ' +
    'restitution friction rigid_body_type')

BODY_FORMAT = '<1{0}1B1H1B3f3f3f1f1f1f1f1f1B'


def unpack_rigid_body(header, buf, offset=0):
    size = 0
    name_jp, name_en, s = unpack_name(header, buf, offset)
    size += s

    pack_format = BODY_FORMAT.format(INDEX_FORMAT[header.bone_isize])
    body_val = group_tuple(
        pack_format, struct.unpack_from(pack_format, buf, offset + size))
    size += struct.calcsize(pack_format)
    return rigid_body._make((name_jp, name_en) + body_val), size


def pack_rigid_body(header, p):
    result = bytearray()
    result += pack_name(header, p)
    pack_format = BODY_FORMAT.format(INDEX_FORMAT[header.bone_isize])
    result += struct.pack(pack_format, *flatten_composite(*p[2:]))
    return result


# ####
# joints
# ####
joint = namedtuple(
    # mandatory
    'joint', 'name_jp name_en joint_type ' +
    # optional
    'rigid_body_a rigid_body_b position rotation ' +
    'lin_lower_limit lin_upper_limit ' +
    'ang_lower_limit ang_upper_limit ' +
    'lin_stiffness ang_stiffness')

JOINT_FORMAT = '<1{0}1{0}3f3f3f3f3f3f3f3f'
JOINT_6DOF_SPRING = 0
JOINT_6DOF = 1
JOINT_P2P = 2
JOINT_CONE_TWIST = 3
JOINT_SLIDER = 5
JOINT_HINGE = 6


def unpack_joint(header, buf, offset=0):
    size = 0
    name_jp, name_en, s = unpack_name(header, buf, offset)
    size += s

    joint_type = struct.unpack_from('<1B', buf, offset + size)[0]
    size += struct.calcsize('<1B')
    if JOINT_6DOF_SPRING == joint_type:
        pack_format = JOINT_FORMAT.format(
            INDEX_FORMAT[header.rigid_body_isize])
        joint_val = group_tuple(
            pack_format, struct.unpack_from(pack_format, buf, offset + size))
        size += struct.calcsize(pack_format)
    else:
        joint_val = (None,) * 10
    return joint._make((name_jp, name_en, joint_type) + joint_val), size


def pack_joint(header, p):
    result = bytearray()
    result += pack_name(header, p)
    result += struct.pack('<1B', p.joint_type)
    if JOINT_6DOF_SPRING == p.joint_type:
        pack_format = JOINT_FORMAT.format(
            INDEX_FORMAT[header.rigid_body_isize])
        result += struct.pack(pack_format, *flatten_composite(*p[3:]))
    return result


# ####
# soft bodies
# header.version >= 2.1
# ####
soft_body = namedtuple(
    'soft_body', 'name_jp name_en shape material_index group collision flag ' +
    'distance n_clusters total_mass contact_margin aero_model ' +
    'config cluster iteration material ' +
    'n_anchors anchors ' +
    'n_vertexes vertexes')
soft_body_config = namedtuple(
    'soft_body_config', 'VCF DP DG LF PR VC DF MT CHR KHR SHR AHR')
soft_body_cluster = namedtuple(
    'soft_body_cluster',
    'SRHR_CL SKHR_CL SSHR_CL SR_SPLT_CL SK_SPLT_CL SS_SPLT_CL')
soft_body_iteration = namedtuple(
    'soft_body_iteration', 'V_IT P_IT D_IT C_IT')
soft_body_material = namedtuple(
    'soft_body_material', 'LST AST VST')
soft_body_anchor = namedtuple(
    'soft_body_anchor', 'rigid_body local is_near')

SOFT_BODY_FORMAT = '<1B1{0}1B1H1B1i1i1f1f1i'  # m_index
SOFT_BODY_CONFIG_FORMAT = '<4f4f4f4f4f4f4f4f4f4f4f4f'
SOFT_BODY_CLUSTER_FORMAT = '<4f4f4f4f4f4f'
SOFT_BODY_ITERATION_FORMAT = '<4f4f4f4f'
SOFT_BODY_MATERIAL_FROMAT = '<4f4f4f'
SOFT_BODY_ANCHOR_FORAMT = '<1{0}1{0}1B'  # rigid_index, v_index
SOFT_BODY_VERTEX_FORMAT = '<1{0}'  # v_index


def unpack_soft_body(header, buf, offset=0):
    size = 0
    name_jp, s = unpack_string(buf, offset, PMX_ENCODING[header.encoding])
    size += s
    name_en, s = unpack_string(
        buf, offset + size, PMX_ENCODING[header.encoding])
    size += s

    pack_format = SOFT_BODY_FORMAT.format(
        INDEX_FORMAT[header.material_isize])
    soft_body_base = struct.unpack_from(pack_format, buf, offset + size)
    size += struct.calcsize(pack_format)

    config = soft_body_config._make(group_tuple(
        SOFT_BODY_CONFIG_FORMAT,
        struct.unpack_from(SOFT_BODY_CONFIG_FORMAT, buf, offset + size)))
    size += struct.calcsize(SOFT_BODY_CONFIG_FORMAT)

    cluster = soft_body_cluster._make(group_tuple(
        SOFT_BODY_CLUSTER_FORMAT,
        struct.unpack_from(SOFT_BODY_CLUSTER_FORMAT, buf, offset + size)))
    size += struct.calcsize(SOFT_BODY_CLUSTER_FORMAT)

    iteration = soft_body_iteration._make(group_tuple(
        SOFT_BODY_ITERATION_FORMAT,
        struct.unpack_from(SOFT_BODY_ITERATION_FORMAT, buf, offset + size)))
    size += struct.calcsize(SOFT_BODY_ITERATION_FORMAT)

    material = soft_body_material._make(group_tuple(
        SOFT_BODY_MATERIAL_FROMAT,
        struct.unpack_from(SOFT_BODY_MATERIAL_FROMAT, buf, offset + size)))
    size += struct.calcsize(SOFT_BODY_MATERIAL_FROMAT)

    n_anchors = struct.unpack_from('<1i', buf, offset + size)[0]
    size += struct.calcsize('<1i')
    anchors = list()
    pack_format = SOFT_BODY_ANCHOR_FORAMT.format(
        INDEX_FORMAT[header.rigid_body_isize],
        INDEX_FORMAT_VERTEX[header.vertex_isize])
    for i in range(n_anchors):
        anchor = struct.unpack_from(pack_format, buf, offset + size)
        size += struct.calcsize(pack_format)
        anchors.append(anchor)

    n_vertexes = struct.unpack_from('<1i', buf, offset + size)[0]
    size += struct.calcsize('<1i')
    vertexes = list()
    pack_format = SOFT_BODY_VERTEX_FORMAT.format(
        INDEX_FORMAT_VERTEX[header.vertex_isize])
    for i in range(n_vertexes):
        vertex = struct.unpack_from(pack_format, buf, offset + size)[0]
        size += struct.calcsize(pack_format)
        vertexes.append(vertex)
    return soft_body(
        name_jp, name_en, *soft_body_base, config, cluster, iteration,
        material, n_anchors, tuple(anchors), n_vertexes, tuple(vertexes))


def pack_soft_body(header, p):
    result = bytearray()
    result += pack_string(p.name_jp, PMX_ENCODING[header.encoding])
    result += pack_string(p.name_en, PMX_ENCODING[header.encoding])
    pack_format = SOFT_BODY_FORMAT.format(
        INDEX_FORMAT[header.material_isize])
    result += struct.pack(pack_format, *p[2:12])
    result += struct.pack(
        SOFT_BODY_CONFIG_FORMAT, *flatten_composite(*p.config))
    result += struct.pack(
        SOFT_BODY_CLUSTER_FORMAT, *flatten_composite(*p.cluster))
    result += struct.pack(
        SOFT_BODY_ITERATION_FORMAT, *flatten_composite(*p.iteration))
    result += struct.pack(
        SOFT_BODY_MATERIAL_FROMAT, *flatten_composite(*p.material))
    result += struct.pack('<1i', p.n_anchors)
    pack_format = SOFT_BODY_ANCHOR_FORAMT.format(
        INDEX_FORMAT[header.rigid_body_isize],
        INDEX_FORMAT_VERTEX[header.vertex_isize])
    for anchor in p.anchors:
        result += struct.pack(pack_format, *anchor)
    result += struct.pack('<1i', p.n_vertexes)
    pack_format = SOFT_BODY_VERTEX_FORMAT.format(
        INDEX_FORMAT_VERTEX[header.vertex_isize])
    for vertex in p.vertexes:
        result += struct.pack(pack_format, vertex)
    return result


# (pack, unpack)
PMX_IO_UTIL = {
    PMX_ELEMENTS[0]: (
        pack_vertex, unpack_vertex),
    PMX_ELEMENTS[1]: (
        pack_face, unpack_face),
    PMX_ELEMENTS[2]: (
        pack_texture, unpack_texture),
    PMX_ELEMENTS[3]: (
        pack_material, unpack_material),
    PMX_ELEMENTS[4]: (
        pack_bone, unpack_bone),
    PMX_ELEMENTS[5]: (
        pack_morph, unpack_morph),
    PMX_ELEMENTS[6]: (
        pack_disp_node, unpack_disp_node),
    PMX_ELEMENTS[7]: (
        pack_rigid_body, unpack_rigid_body),
    PMX_ELEMENTS[8]: (
        pack_joint, unpack_joint),
    PMX_ELEMENTS[9]: (
        pack_soft_body, unpack_soft_body),  # 2.1
}
