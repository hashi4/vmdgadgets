import sys
import math
import argparse
from collections import defaultdict

import vmdutil
from vmdutil import pmxutil
from vmdutil import pmxdef


EPS = 1e-10
# box
BOX_V = [
    (-1.0, -1.0, -1.0), (-1.0, -1.0, 1.0), (-1.0, 1.0, 1.0),
    (-1.0, 1.0, -1.0), (1.0, 1.0, 1.0), (1.0, 1.0, -1.0),
    (1.0, -1.0, 1.0), (1.0, -1.0, -1.0)
]
N_U = 0.5773503184318542
BOX_N = [
    (-N_U, -N_U, -N_U), (-N_U, -N_U, N_U), (-N_U, N_U, N_U),
    (-N_U, N_U, -N_U), (N_U, N_U, N_U), (N_U, N_U, -N_U),
    (N_U, -N_U, N_U), (N_U, -N_U, -N_U)
]
BOX_F = [
    (0, 1, 2), (2, 3, 0), (3, 2, 4), (4, 5, 3), (5, 4, 6), (6, 7, 5),
    (1, 0, 7), (7, 6, 1), (1, 6, 4), (4, 2, 1), (0, 3, 5), (5, 7, 0)
]


def eps(v):
    return v if abs(v) > EPS else 0.0


def sphere(radius, lati, longi, half=False):
    vr = math.pi * 2 / longi
    lati = lati if lati % 2 == 0 else lati - 1
    hr = math.pi / lati
    hrange = range(1, lati) if half is False else range(1, lati // 2 + 1)

    normals = [(0.0, 1.0, 0.0)]
    for h in hrange:
        y = math.cos(h * hr)
        for v in range(longi):
            rxz = math.sin(h * hr)
            x = math.sin(v * vr) * rxz
            z = math.cos(v * vr) * rxz
            normals.append(tuple([p for p in map(eps, (x, y, z))]))
    if half is False:
        normals.append((0.0, -1.0, 0.0))
    vertexes = [tuple([radius * p for p in n]) for n in normals]

    hrange = range(lati - 1) if half is False else range(lati // 2 - 1)
    faces = list()
    for v in range(longi):
        c = v + 1
        next = c + 1 if v < longi - 1 else 1
        faces.append((0, c, next))
    bottom = (lati - 1) * longi + 1
    for h in hrange:
        vstart = longi * h + 1
        for v in range(longi):
            c = vstart + v
            next = c + 1 if v < longi - 1 else vstart
            if half is True or h < lati - 2:
                faces.append((c, c + longi, next))
                faces.append((next, c + longi, next + longi))
            else:
                faces.append((c, bottom, next))
    return vertexes, normals, faces


def capsule(radius, height, d=8):
    d = d if d % 2 == 0 else d - 1
    s = sphere(radius, d, d)
    v1 = s[0][:(1 + d * d // 2)]
    v1 = [(x, y + height / 2, z) for (x, y, z) in v1]
    v2 = s[0][(1 + d * (d // 2 - 1)):]
    v2 = [(x, y - height / 2, z) for (x, y, z) in v2]
    n1 = s[1][:(1 + d * d // 2)]
    n2 = s[1][(1 + d * (d // 2 - 1)):]
    f1 = s[2][:d + d * (d - 2)]
    f2 = s[2][d + d * (d - 2):]
    f2 = [tuple([i + d for i in m]) for m in f2]
    fi = list()
    start = 1 + d * (d // 2 - 1)
    for v in range(d):
        c = v + start
        next = c + 1 if v < d - 1 else start
        fi.append((c, c + d, next))
        fi.append((next, c + d, next + d))
    vertexes = v1 + v2
    normals = n1 + n2
    faces = f1 + fi + f2
    return vertexes, normals, faces


def corn(radius, from_v, to_v, d=8):
    def return_sphere():
        s = sphere(radius, d, d)
        vertexes = [(x + from_v[0], y + from_v[1], z + from_v[2])
                    for (x, y, z) in s[0]]
        return vertexes, s[1], s[2]

    if to_v is None:
        return return_sphere()

    dir_v = vmdutil.sub_v(to_v, from_v)
    angle = vmdutil.angle_v((0, 1, 0), dir_v)
    if angle is None:
        return return_sphere()

    half_sphere = sphere(radius, d, d, True)
    vertexes = [(x, -y, z) for (x, y, z) in half_sphere[0]]
    normals = [(x, -y, z) for (x, y, z) in half_sphere[1]]
    length = vmdutil.norm_v(dir_v)
    faces = [(f[0], f[2], f[1]) for f in half_sphere[2]]
    vertexes.append((0, length, 0))
    normals.append((0, 1, 0))
    n_vertexes = len(vertexes)

    # insert faces
    for i in range(n_vertexes - d - 1, n_vertexes - 2):
        faces.append((i, i + 1, n_vertexes - 1))
    faces.append((n_vertexes - 2, n_vertexes - d - 1, n_vertexes - 1))
    if (abs(angle) < EPS):
        pass
    else:
        if (abs(math.pi - angle) < EPS):
            q = vmdutil.quaternion((0, 0, 1), math.pi)
        else:
            c = vmdutil.cross_v3((0, 1, 0), dir_v)
            q = vmdutil.quaternion(c, angle)
        vertexes = [tuple(vmdutil.rotate_v3q(v, q)) for v in vertexes]
        normals = [tuple(vmdutil.rotate_v3q(v, q)) for v in normals]
    # translate
    vertexes = [(x + from_v[0], y + from_v[1], z + from_v[2])
                for (x, y, z) in vertexes]
    return vertexes, normals, faces


def transform(v, scale, translation, rotation):
    # scale
    v = [i * j for i, j in zip(v, scale)]
    # rotate
    quaternion = vmdutil.euler_to_quaternion(rotation)
    v = vmdutil.rotate_v3q(v, quaternion)
    # translate
    v = vmdutil.add_v(v, translation)
    return tuple(v)


def make_sphere_shape(scale, translation, rotation):
    vertexes, normals, faces = sphere(scale[0], 8, 8)
    vertexes = [transform(
        v, (1, 1, 1), translation, rotation) for v in vertexes]
    normals = [transform(
        n, (1, 1, 1), (0, 0, 0), rotation) for n in normals]
    return vertexes, normals, faces


def make_box_shape(scale, translation, rotation):
    vertexes = [transform(v, scale, translation, rotation) for v in BOX_V]
    normals = [transform(n, (1, 1, 1), (0, 0, 0), rotation) for n in BOX_N]
    faces = BOX_F
    return vertexes, normals, faces


def make_capsul_shape(scale, translation, rotation):
    vertexes, normals, faces = capsule(scale[0], scale[1], 8)
    vertexes = [transform(
        v, (1, 1, 1), translation, rotation) for v in vertexes]
    normals = [transform(
        n, (1, 1, 1), (0, 0, 0), rotation) for n in normals]
    return vertexes, normals, faces


RIGID_BODY_BUILDER = [make_sphere_shape, make_box_shape, make_capsul_shape]


def make_rigid_body_model(index, pmx):
    rigid_body = pmx.get_elements('rigid_bodies')[index]
    weight = pmxdef.vertex_bdef1(bone1=rigid_body.bone)
    vertex_base = pmxdef.vertex(
        position=(0, 0, 0), normal=(0, 0, 0),
        uv=(0, 0), ex_uvs=(), weight_type=0, weight=weight, edge_mag=1.0)
    vertexes, normals, faces = RIGID_BODY_BUILDER[rigid_body.shape](
        rigid_body.scale, rigid_body.position, rigid_body.rotation)

    return ([
        vertex_base._replace(position=i, normal=j)
        for i, j in zip(vertexes, normals)],
        faces)


def make_joint_model(index, pmx):
    joint = pmx.get_elements('joints')[index]
    weight_bone = pmx.get_elements('rigid_bodies')[joint.rigid_body_a].bone
    weight = pmxdef.vertex_bdef1(bone1=weight_bone)
    vertex_base = pmxdef.vertex(
        position=(0, 0, 0), normal=(0, 0, 0),
        uv=(0, 0), ex_uvs=(), weight_type=0, weight=weight, edge_mag=1.0)
    vertexes = [transform(
        v, (0.15, 0.15, 0.15), joint.position, joint.rotation) for v in BOX_V]
    normals = [transform(
        n, (1, 1, 1), (0, 0, 0), joint.rotation) for n in BOX_N]
    return ([
        vertex_base._replace(position=i, normal=j)
        for i, j in zip(vertexes, normals)],
        BOX_F)


def make_bone_model(index, pmx):
    bones = pmx.get_elements('bones')
    disp_dir = bones[index].disp_dir
    top_weight = None
    if tuple == type(disp_dir):
        if disp_dir == (0, 0, 0):
            to_v = None
        else:
            to_v = vmdutil.add_v(bones[index].position, disp_dir)
    else:
        if disp_dir == -1:
            to_v = None
        else:
            to_v = bones[disp_dir].position
            top_weight = disp_dir
    vertexes, normals, faces = corn(0.1, bones[index].position, to_v)
    weight = pmxdef.vertex_bdef1(bone1=index)
    vertex_base = pmxdef.vertex(
        position=(0, 0, 0), normal=(0, 0, 0),
        uv=(0, 0), ex_uvs=(), weight_type=0, weight=weight, edge_mag=1.0)
    pmx_vertexes = [
        vertex_base._replace(position=i, normal=j)
        for i, j in zip(vertexes, normals)]
    if top_weight is not None:
        pmx_vertexes[-1] = pmx_vertexes[-1]._replace(
            weight=pmxdef.vertex_bdef1(bone1=top_weight))
    return pmx_vertexes, faces


MODEL_BUILDER = {
    'bones': make_bone_model, 'rigid_bodies': make_rigid_body_model,
    'joints': make_joint_model}


def make_model(v_index, kind, pmx, criteria=None):
    elements = pmx.get_elements(kind)
    vertexes = list()
    faces = list()
    for index, element in enumerate(elements):
        if criteria is None or criteria(index, element) is True:
            v, f = MODEL_BUILDER[kind](index, pmx)
            vertexes.extend(v)
            faces.extend([tuple([i + v_index for i in face]) for face in f])
            v_index += len(v)
    return vertexes, faces


def original_info(pmx):
    vertexes = pmx.get_elements('vertexes')
    faces = pmx.get_elements('faces')
    materials = pmx.get_elements('materials')
    return vertexes, faces, materials


def alpha_morph(m_indexes, name):
    offsets = list()
    for m_index in m_indexes:
        mat = pmxdef.morph_material(
            m_index, operation=0, diffuse=(1.0, 1.0, 1.0, 0.0),
            specular=(1.0, 1.0, 1.0), specular_coef=1.0,
            ambient=(1.0, 1.0, 1.0), edge_color=(1.0, 1.0, 1.0, 0.0),
            edge_size=1.0, texture_coef=(1.0, 1.0, 1.0, 0.0),
            sphere_texture_coef=(1.0, 1.0, 1.0, 0.0),
            toon_texture_coef=(1.0, 1.0, 1.0, 0.0))
        offsets.append(mat)
    offsets = tuple(offsets)
    morph = pmxdef.morph(
        name_jp=name, name_en='', category=4,
        morph_type=8, n_offsets=len(offsets), offsets=offsets)
    return morph


def make_rigid_bodies(v_index, m_index, pmx):
    def criteria(group, index, e):
        return e.group == group

    body_groups = {body.group for body in pmx.get_elements('rigid_bodies')}
    materials = list()
    vertexes = list()
    faces = list()
    morphs = list()
    last_material = m_index
    for group in body_groups:
        a_vertexes, a_faces = make_model(
            v_index, 'rigid_bodies', pmx, lambda p, q: criteria(group, p, q))
        v_index += len(a_vertexes)
        a_material = pmxdef.material(
            name_jp='剛体{}'.format(group + 1),
            name_en='',
            diffuse=(0.8, 0.4, 0.0, 1.0), specular=(0.0, 0.0, 0.0),
            specular_coef=5.0, ambient=(0.8, 0.4, 0.0), draw_flag=30,
            edge_color=(0.0, 0.0, 0.0, 1.0), edge_size=1.0, texture=-1,
            sphere_texture=-1, sphere_mode=0, toon_flag=1, toon_texture=0,
            memo='', n_face_vertexes=len(a_faces * 3))
        materials.append(a_material)
        morphs.append(alpha_morph([m_index], a_material.name_jp + '_off'))
        m_index += 1
        vertexes.extend(a_vertexes)
        faces.extend(a_faces)
    morphs.append(alpha_morph(range(last_material, m_index), '全剛体_off'))
    return vertexes, faces, materials, morphs


def make_joints(v_index, m_index, pmx):
    vertexes, faces = make_model(v_index, 'joints', pmx, lambda p, q: True)
    v_index += len(vertexes)
    material = pmxdef.material(
        name_jp='ジョイント',
        name_en='',
        diffuse=(0.8, 0.8, 0.2, 1.0), specular=(0.0, 0.0, 0.0),
        specular_coef=5.0, ambient=(0.8, 0.8, 0.2), draw_flag=30,
        edge_color=(0.0, 0.0, 0.0, 1.0), edge_size=1.0, texture=-1,
        sphere_texture=-1, sphere_mode=0, toon_flag=1, toon_texture=0,
        memo='', n_face_vertexes=len(faces * 3))
    morph = alpha_morph([m_index], material.name_jp + '_off')
    m_index += 1
    return vertexes, faces, [material], [morph]


def make_bones(v_index, m_index, pmx):
    rigid_bodies = pmx.get_elements('rigid_bodies')
    bones_under_physics = {
        body.bone for body in rigid_bodies if body.rigid_body_type > 0}

    def is_phy_bone(index, b):
        return index in bones_under_physics

    def is_disp_bone(index, b):
        return b.flag & pmxdef.BONE_CAN_DISP == pmxdef.BONE_CAN_DISP

    def criteria1(index, b):
        return is_disp_bone(index, b) and is_phy_bone(index, b)

    def criteria2(index, b):
        return is_disp_bone(index, b) and not is_phy_bone(index, b)

    vertexes1, faces1 = make_model(v_index, 'bones', pmx, criteria1)
    v_index += len(vertexes1)
    material1 = pmxdef.material(
        name_jp='物理骨',
        name_en='',
        diffuse=(0.2, 0.2, 0.6, 1.0), specular=(0.0, 0.0, 0.0),
        specular_coef=5.0, ambient=(0.2, 0.2, 0.6), draw_flag=30,
        edge_color=(0.0, 0.0, 0.0, 1.0), edge_size=1.0, texture=-1,
        sphere_texture=-1, sphere_mode=0, toon_flag=1, toon_texture=0,
        memo='', n_face_vertexes=len(faces1 * 3))
    morph1 = alpha_morph([m_index], material1.name_jp + '_off')
    m_index += 1
    vertexes2, faces2 = make_model(v_index, 'bones', pmx, criteria2)
    v_index += len(vertexes2)
    material2 = material1._replace(
        name_jp='非物理骨', n_face_vertexes=len(faces2 * 3))
    morph2 = alpha_morph([m_index], material2.name_jp + '_off')
    m_index += 1

    return (vertexes1 + vertexes2, faces1 + faces2,
            [material1, material2], [morph1, morph2])


def offset_morphs(morphs, m_offset):
    for index, morph in enumerate(morphs):
        if morph.morph_type == 8:  # material
            offsets = [
                offset._replace(material=offset.material + m_offset)
                for offset in morph.offsets]
            morphs[index] = morph._replace(offsets=tuple(offsets))
    return morphs


def fill_bones(pmx):
    bones = pmx.get_elements('bones')
    joints = pmx.get_elements('joints')
    bone_names = {bone.name_jp: index for index, bone in enumerate(bones)}
    rigid_bodies = pmx.get_elements('rigid_bodies')
    bone_index = len(bones)
    b_dict = defaultdict(list)
    for index, joint in enumerate(joints):
        b_dict[joint.rigid_body_b].append(index)

    def set_bone(body_index, path=None):
        nonlocal bone_index
        if path is None:
            path = {body_index}
        elif body_index in path:
            return None  # loop
        else:
            path.add(body_index)
        body = rigid_bodies[body_index]
        if body.name_jp not in bone_names:
            joint_indexes = b_dict.get(body_index, [])
            if 0 == len(joint_indexes):
                parent = bone_names['センター']
            else:
                parents = list()
                for joint_index in joint_indexes:
                    joint = joints[joint_index]
                    a_body = rigid_bodies[joint.rigid_body_a]
                    if a_body.bone == -1:
                        parent = set_bone(joint.rigid_body_a, path)
                        if parent is not None:
                            parents.append(parent)
                    else:
                        parents.append(a_body.bone)
                parent = min(parents) if len(parents) > 0 else bone_names[
                    'センター']
            bones.append(pmxdef.bone(
                name_jp=body.name_jp, name_en=body.name_en,
                position=body.position, parent=parent, transform_hierarchy=0,
                flag=6, disp_dir=(0.0, 0.0, 0.0), additional_transform=None,
                fixed_axis=None, local_axises=None, ex_parent=None, ik=None))
            target_index = bone_index
            bone_index += 1
        else:
            target_index = bone_names[body.name_jp]
        rigid_bodies[body_index] = rigid_bodies[body_index]._replace(
            bone=target_index)
        return target_index

    for index, body in enumerate(rigid_bodies):
        if -1 == body.bone:
            set_bone(index)

    pmx.set_elements('bones', bones)
    pmx.set_elements('rigid_bodies', rigid_bodies)
    return pmx


def make_brj_pmx(pmx):
    # material_order = ['bones', 'original', 'joints', 'rigid_bodies']
    # material_order = ['bones', 'rigid_bodies']
    material_order = ['bones', 'original', 'rigid_bodies']

    pmx = fill_bones(pmx)
    if 'original' in material_order:
        new_vertexes = pmx.get_elements('vertexes')[:]  # copy
        v_index = pmx.counts['vertexes'].count
        morph_added = [len(pmx.get_elements('morphs')), 0]
    else:
        new_vertexes = list()
        v_index = 0
        morph_added = [0, 0]
    new_faces = list()
    original_morphs = list()
    new_materials = list()
    new_morphs = list()
    m_index = 0
    for material_group in material_order:
        if 'original' == material_group:
            if 0 == m_index:
                original_morphs.extend(pmx.get_elements('morphs'))
            else:
                original_morphs.extend(offset_morphs(
                    pmx.get_elements('morphs'), m_index))
            len_mat = len(pmx.get_elements('materials'))
            original_materials = [i + m_index for i in range(len_mat)]
            new_morphs.append(alpha_morph(original_materials, 'モデル_off'))
            morph_added[1] += 1
            new_materials.extend(pmx.get_elements('materials'))
            m_index += pmx.counts['materials'].count
            new_faces.extend(pmx.get_elements('faces'))
        else:
            if 'rigid_bodies' == material_group:
                a_vertexes, a_faces, a_materials, a_morphs = make_rigid_bodies(
                    v_index, m_index, pmx)
            elif 'joints' == material_group:
                a_vertexes, a_faces, a_materials, a_morphs = make_joints(
                    v_index, m_index, pmx)
            elif 'bones' == material_group:
                a_vertexes, a_faces, a_materials, a_morphs = make_bones(
                    v_index, m_index, pmx)
            v_index += len(a_vertexes)
            m_index += len(a_materials)
            new_vertexes.extend(a_vertexes)
            new_faces.extend(a_faces)
            new_materials.extend(a_materials)
            new_morphs.extend(a_morphs)
            morph_added[1] += len(a_morphs)

    pmx.set_elements('vertexes', new_vertexes)
    pmx.set_elements('faces', new_faces)
    pmx.set_elements('materials', new_materials)
    pmx.set_elements('morphs', original_morphs + new_morphs)

    additional_items = [pmxdef.disp_node_item(
        item_type=1, index=morph_added[0] + i)
        for i in range(morph_added[1])]
    disp_nodes = pmx.get_elements('disp_nodes')
    # expression
    if 'original' in material_order:
        new_items = disp_nodes[1].disp_node_items + tuple(additional_items)
    else:
        new_items = tuple(additional_items)
    disp_nodes[1] = disp_nodes[1]._replace(
        n_disp_node_items=len(new_items), disp_node_items=new_items)
    pmx.set_elements('disp_nodes', disp_nodes)
    return pmx


def make_argumentparser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'infile', nargs='?', type=argparse.FileType('rb'),
        default=sys.stdin.buffer, help='input pmx')
    parser.add_argument(
        'outfile', nargs='?', type=argparse.FileType('wb'),
        default=sys.stdout.buffer, help='output pmx')
    return parser


if __name__ == '__main__':
    parser = make_argumentparser()
    args = parser.parse_args()
    pmx = pmxutil.Pmxio()
    pmx.load_fd(args.infile)
    pmx = make_brj_pmx(pmx)
    pmx.store_fd(args.outfile)
