''' Make a Graphviz dot file of (rigid_body_a)->[joint]->(rigid_body_b) graph.
'''

import sys
import argparse
from collections import defaultdict
from vmdutil import pmxutil

BODY_STYLE = {0: 'solid', 1: 'dashed', 2: 'dotted'}
FONT = 'meiryo'


def make_argumentparser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'infile', nargs='?', type=argparse.FileType('rb'),
        default=sys.stdin.buffer, help='pmx filepath',)
    parser.add_argument(
        'outfile', nargs='?', type=argparse.FileType('wb'),
        default=sys.stdout.buffer,
        help='dot file')
    return parser


def utf8out(string, stream):
    stream.write(string.encode('utf-8'))


def make_graph(pmx):
    joints = pmx.get_elements('joints')
    bodies = pmx.get_elements('rigid_bodies')
    bones = pmx.get_elements('bones')

    def body_dict(body):
        return {
            't': 'body', 'name': body.name_jp,
            'body_type': body.rigid_body_type,
            'bone': str(body.bone) + (
                ': ' + bones[body.bone].name_jp) if body.bone >= 0 else ''}

    nodes = {}
    edges = defaultdict(set)
    for index, joint in enumerate(joints):
        s = 'J' + str(index)
        ba = 'B' + str(joint.rigid_body_a)
        bb = 'B' + str(joint.rigid_body_b)
        nodes[s] = {'t': 'joint', 'name': joint.name_jp}
        body_a = bodies[joint.rigid_body_a]
        body_b = bodies[joint.rigid_body_b]
        nodes[ba] = body_dict(body_a)
        nodes[bb] = body_dict(body_b)
        edges[ba].add(s)
        edges[s].add(bb)
    return nodes, edges


def print_graph(nodes, edges, s):
    def node_label(node, attr):
        if attr['t'] == 'joint':
            return '{}: {}'.format(node[1:], attr['name'])
        else:  # 'rigid body'
            return '{}: {}\n[{}]'.format(
                node[1:], attr['name'], attr['bone'])

    for node in nodes:
        d = nodes[node]
        utf8out('\t{} [shape = {}, label=\"{}\", style=\"{}\"]\n'.format(
            node, 'box' if d['t'] == 'joint' else 'ellipse',
            node_label(node, d),
            BODY_STYLE[d['body_type']] if d['t'] == 'body' else 'solid'),
            s)
    for f in edges:
        for t in edges[f]:
            utf8out('\t{} -> {}\n'.format(f, t), s)


def print_dot(nodes, edges, s):
    utf8out('digraph Joint_Body_Graph {\n', s)
    utf8out('node[fontname=\"{}\"]\n'.format(FONT), s)
    print_graph(nodes, edges, s)
    utf8out('}\n', s)
    return


if __name__ == '__main__':
    parser = make_argumentparser()
    args = parser.parse_args()
    pmx = pmxutil.Pmxio()
    pmx.load_fd(args.infile)
    nodes, edges = make_graph(pmx)
    print_dot(nodes, edges, args.outfile)
