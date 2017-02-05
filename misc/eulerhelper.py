import sys
sys.path.append('../vmdgadgets')
import vmdutil

import functools
def alt_dot_v(v1, v2):
    return functools.reduce(
        lambda i, j: i + j, [x * y for x, y in zip(v1, v2)])
vmdutil.vmdutil.dot_v = alt_dot_v
vmdutil.dot_v = alt_dot_v

class strexp():
    def __init__(self, val):
        self.val = val
    def __mul__(self, other):
        if other.val == '0' or self.val == '0':
            return strexp('0')
        elif other.val == '1':
            return self
        elif self.val == '1':
            return other
        else:
            return strexp('(' + self.val + ')*(' + other.val + ')')

    def __add__(self, other):
        if other.val == '0':
            return self
        elif self.val == '0':
            return other
        else:
            return strexp(self.val + '+' + other.val)

    def __sub__(self, other):
        if other.val == '0':
            return self
        elif self.val == '0':
            return strexp('-' + other.val)
        else:
            return strexp(self.val + '-' + other.val)

    def __neg__(self):
        return strexp('-' + self.val)
    def __repr__(self):
        return self.val


if __name__ == '__main__':
    zero = strexp('0')
    one = strexp('1')
    p = [strexp('sp'), zero, zero, strexp('cp')] # q(1, 0, 0, wx)
    y = [zero, strexp('sy'), zero, strexp('cy')]
    r = [zero, zero, strexp('sr'), strexp('cr')]
    o = vmdutil.multiply_quaternion(
            vmdutil.multiply_quaternion(r, p), y)
    print('euler2quaternion of z-x-y(global)')
    print(o)
    print()


    # rotx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    # roty = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    # rotz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    cx = strexp('cx')
    cy = strexp('cy')
    cz = strexp('cz')
    sx = strexp('sx')
    sy = strexp('sy')
    sz = strexp('sz')
    print('euler2matrix of z-x-y(global)')
    o = vmdutil.dot_m(
            vmdutil.dot_m(
                [[cz, -sz, zero], [sz, cz, zero], [zero, zero, one]],
                [[one, zero, zero], [zero, cx, -sx], [zero, sx, cx]]),
            [[cy, zero, sy], [zero, one, zero], [-sy, zero, cy]])
    for r in o:
        print(r)
