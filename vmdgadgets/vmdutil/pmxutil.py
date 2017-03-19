import heapq
from .import pmxdef


class Bonegraph():
    # {parent: {child: {n: {key: attr}}}}
    def __init__(self):
        self.edges = {}
        self.preds = {}

    def add_edge(self, a, b, **attr):
        if a not in self.edges:
            self.edges[a] = {}
        if b not in self.edges:
            self.edges[b] = {}
        if b not in self.edges[a]:
            self.edges[a][b] = {}

        if b not in self.preds:
            self.preds[b] = {}
        if a not in self.preds:
            self.preds[a] = {}
        if a not in self.preds[b]:
            self.preds[b][a] = {}

        l = len(self.edges[a][b])
        self.edges[a][b][l] = {}
        self.preds[b][a][l] = {}
        for key in attr:
            self.edges[a][b][l][key] = attr[key]
            self.preds[b][a][l][key] = attr[key]
        return

    def remove_edge(self, a, b):
        if a in self.edges and b in self.edges[a]:
            del self.edges[a][b]
            del self.preds[b][a]
        return

    def remove_node(self, n, reconnect=True):
        preds = self.preds[n]
        edges = self.edges[n]
        if reconnect:
            for pred in preds:
                for edge in edges:
                        self.add_edge(pred, edge)
        for pred in preds:
            del self.edges[pred][n]
        for edge in edges:
            del self.preds[edge][n]
        del self.edges[n]
        del self.preds[n]
        return

    def in_degree(self, node=None):
        if node is None:
            return [(node, self.in_degree(node)) for node in self.preds]
        else:
            return sum([len(self.preds[node][i]) for i in self.preds[node]])

    def out_degree(self, node=None):
        if node is None:
            return [(node, self.out_degree(node)) for node in self.edges]
        else:
            return sum([len(self.edges[node][i]) for i in self.edges[node]])

    def is_descendant(self, a, b, c=None):
        if c == None:
            c = a
        elif c == a:
            return False
        for edge in self.edges[a]:
            if b == edge:
                return True
            if self.is_descendant(edge, b, c):
                return True
        return False

    def t_sort(self):
        roots = [node for node, degree in self.in_degree() if degree == 0]
        children = {
            node: degree for node, degree in self.in_degree() if degree > 0}
        heapq.heapify(roots)
        result = list()
        while len(roots) > 0:
            node = heapq.heappop(roots)
            for child in self.edges[node]:
                children[child] -= len(self.edges[node][child])
                if children[child] == 0:
                    heapq.heappush(roots, child)
                    del children[child]
            result.append(node)
        if len(children) > 0:
            return None
        else:
            return result


class Pmxio():
    def __init__(self):
        vindex = pmxdef.INDEX_FORMAT_VERTEX[1]
        index = pmxdef.INDEX_FORMAT[1]
        self.header = pmxdef.header(
            pmxdef.PMX_HEADER, 2.0, 8, pmxdef.PMX_ENCODING[0], 0,
            vindex, index, index, index, index, index)
        self.counts = {}
        self.elements = {}
        for element in pmxdef.PMX_ELEMENTS:
            self.counts[element] = pmxdef.count(0)
            self.elements[element] = []

    def get_elements(self, element):
        return self.elements[element]

    def set_elements(self, element, o):
        self.counts[element] = pmxdef.count(len(o))
        self.elements[element] = o

    def read_bytes(self):
        offset = 0
        filesize = len(self.buf)
        # header
        self.header, size = pmxdef.unpack_header(self.buf, offset)
        offset += size
        # model info
        self.model_info, size = pmxdef.unpack_model_info(
            self.header, self.buf, offset)
        offset += size
        # others
        for element in pmxdef.PMX_ELEMENTS:
            if filesize <= offset:
                self.counts[element] = pmxdef.count(0)
                continue
            c, size = pmxdef.unpack_count(self.buf, offset)
            offset += size
            if element == 'faces':
                c = c._replace(count=c.count // 3)
            self.counts[element] = c
            for index in range(self.counts[element].count):
                obj, size = pmxdef.PMX_IO_UTIL[element][1](
                    self.header, self.buf, offset)
                offset += size
                self.elements[element].append(obj)

    def load(self, filename):
        if len(self.counts) > 0:
            self.__init__()
        f = open(filename, 'rb')
        self.buf = f.read()
        f.close()
        del f
        self.read_bytes()

    def load_fd(self, reader):
        if len(self.counts) > 0:
            self.__init__()
        self.buf = reader.read()
        self.read_bytes()

    def to_bytes(self):
        buf = bytearray()
        # header
        buf += pmxdef.pack_header(self.header)
        # model info
        buf += pmxdef.pack_model_info(self.header, self.model_info)
        # others
        for element in pmxdef.PMX_ELEMENTS[:-1]:
            count = len(self.elements[element])
            if 'faces' == element:
                count *= 3
            count = pmxdef.count(count)
            buf += pmxdef.pack_count(count)
            for obj in self.elements[element]:
                buf += pmxdef.PMX_IO_UTIL[element][0](self.header, obj)
        return buf

    def store(self, filename):
        buf = self.to_bytes()
        f = open(filename, 'wb')
        f.write(buf)
        f.close()

    def store_fd(self, writer):
        buf = self.to_bytes()
        writer.write(buf)


def make_name_dict(elements):
    result = dict()
    for index, element in enumerate(elements):
        result[element.name_jp] = index
    return result


def make_bone_link(
        bones, from_index, to_index, criteria=None, bone_list=None):
    if bone_list is None:
        bone_list = list()
    if criteria is None or criteria(bones[from_index]):
        bone_list.append(from_index)
    parent = bones[from_index].parent
    if parent == to_index or parent == 0:
        if criteria is None or criteria(bones[parent]):
            bone_list.append(parent)
        return bone_list
    else:
        return make_bone_link(bones, parent, to_index, criteria, bone_list)


def make_all_bone_link_graph(
    bones, criteria=None, bone_graph=None):
    if bone_graph is None:
        bone_graph = Bonegraph()
    for bone_index, bone_def in enumerate(bones):
        if bone_def.parent > 0 and (criteria is None or criteria(bone_def)):
            bone_graph.add_edge(bone_def.parent, bone_index)
    return bone_graph


def make_sub_bone_link_graph(
    bones, from_index, to_indexes, criteria=None, bone_graph=None):
    if bone_graph is None:
        bone_graph = Bonegraph()
    parents = set()
    nodes = [node for node in bone_graph.edges]
    for to_index in to_indexes:
        to_bone = bones[to_index]
        if to_index >= from_index and (criteria is None or criteria(to_bone)):
            if to_bone.parent >= from_index:
                bone_graph.add_edge(to_bone.parent, to_index)
            if (to_bone.parent != from_index and
                to_bone.parent not in nodes):
                parents.add(to_bone.parent)
    if len(parents) > 0:
        return make_sub_bone_link_graph(
            bones, from_index, parents, criteria, bone_graph)
    else:
        return bone_graph


def get_transform_order(indexes, all_bones):
    def first_key(i):
        return all_bones[i].flag & pmxdef.BONE_TRANSFORM_AFTER_PHYSICS

    def second_key(i):
        return all_bones[i].transform_hierarchy

    def third_key(i):
        return i

    def key_func(i):
        return first_key(i), second_key(i), third_key(i)

    return sorted(indexes, key=key_func)
