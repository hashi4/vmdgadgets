EPS = 0.000001

# Cubic bezier curves
BEZIER3 = [[-1, 3, -3, 1], [3, -6, 3, 0], [-3, 3, 0, 0], [1, 0, 0, 0]]
# bezier(t) = [t**3, t**2, t, 1] dot BEZIER3 dot [control-points]


def _A(x): return sum([i * j for i, j in zip(BEZIER3[0], x)])


def _B(x): return sum([i * j for i, j in zip(BEZIER3[1], x)])


def _C(x): return sum([i * j for i, j in zip(BEZIER3[2], x)])


def _D(x): return sum([i * j for i, j in zip(BEZIER3[3], x)])


def bezier3f(control_points, t):
    t2 = t * t
    t3 = t2 * t
    x = control_points
    return t3 * _A(x) + t2 * _B(x) + t * _C(x) + _D(x)


def bezier3f_dt(control_points, t):
    t2 = t * t
    x = control_points
    return 3 * t2 * _A(x) + 2 * t * _B(x) + _C(x)


def _n(f, fd, t):
    x = f(t)
    if abs(x) < EPS:
        return t
    else:
        return _n(f, fd, t - (x / fd(t)))


def bezier3f_x2t(control_points, x):
    init = 0.5

    def f(t):
        return bezier3f(control_points, t) - x

    def fd(t):
        return bezier3f_dt(control_points, t)

    return _n(f, fd, init)
