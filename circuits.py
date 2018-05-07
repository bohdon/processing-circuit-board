
import random
import math


BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (180, 30, 0)
GREEN = (110, 180, 30)
BG_COLOR = 204

BOARD = None

DIRECTIONS = [
    PVector(1, 0),
    PVector(1, -1),
    PVector(0, -1),
    PVector(-1, -1),
    PVector(-1, 0),
    PVector(-1, 1),
    PVector(0, 1),
    PVector(1, 1),
]


def vector_equal(a, b):
    return (int(a.x) == int(b.x) and
            int(a.y) == int(b.y))


def vector_dist(a, b):
    return (b - a).mag()


def get_direction_index(current_dir):
    for i, direction in enumerate(DIRECTIONS):
        if vector_equal(current_dir, direction):
            return i
    print('Not a valid direction: {0}'.format(current_dir))


def get_valid_turn_dirs(current_dir):
    index = get_direction_index(current_dir)
    if index is not None:
        return [
            DIRECTIONS[index],
            DIRECTIONS[index - 1],
            DIRECTIONS[(index + 1) % len(DIRECTIONS)]
        ]
    return []


def dot(a, b):
    mag_a = a.mag()
    mag_b = b.mag()
    if mag_a == 0 or mag_b == 0:
        return -1
    a_norm = PVector(a.x / mag_a, a.y / mag_a)
    b_norm = PVector(b.x / mag_b, b.y / mag_b)
    return a_norm.x * b_norm.x + a_norm.y * b_norm.y


def normalize(vector):
    result = PVector(vector.x, vector.y)
    if result.x != 0:
        result.x = math.copysign(1, result.x)
    if result.y != 0:
        result.y = math.copysign(1, result.y)
    return result


def delta_direction(pt_a, pt_b):
    delta = pt_b - pt_a
    return normalize(delta)


def is_point_visible(pt):
    return not hasattr(pt, 'visible') or getattr(pt, 'visible')


class Socket(object):
    def __init__(self, point, direction):
        self.point = point
        self.direction = direction

    def rotate_direction(self):
        self.direction = PVector(-self.direction.y, self.direction.x)

    def auto_set_direction(self, target_pt):
        delta = target_pt - self.point
        if abs(delta.x) > abs(delta.y):
            self.direction.x = math.copysign(1, delta.x)
            self.direction.y = 0
        else:
            self.direction.x = 0
            self.direction.y = math.copysign(1, delta.y)


class SocketPair(object):
    def __init__(self, start, end):
        if not isinstance(start, Socket):
            raise TypeError("start must be a Socket")
        if not isinstance(end, Socket):
            raise TypeError("end must be a Socket")
        self.start = start
        self.end = end
        self.line = ConnectionLine(self)

    def auto_set_directions(self, board):
        self.start.auto_set_direction(board.grid_size * 0.5)
        self.end.auto_set_direction(board.grid_size * 0.5)


class ConnectionLine(object):
    def __init__(self, socket_pair):
        self.socket_pair = socket_pair
        self.weight = 3
        self.points = []

    @property
    def start(self):
        return self.socket_pair.start

    @property
    def end(self):
        return self.socket_pair.end

    def reset(self):
        self.points = []

    def tick(self, board):
        if not self.points:
            self.points.append(self.start.point)
        else:
            last_pt = self.points[-1]
            if len(self.points) > 1:
                last_dir = delta_direction(self.points[-2], last_pt)
            else:
                last_dir = self.start.direction
            next_pt = self.find_next_point(last_pt, last_dir, board)
            self.points.append(next_pt)

    def get_straight_delta(self):
        delta = self.end.point - self.start.point
        return abs(abs(delta.x) - abs(delta.y))

    def is_blocked(self, pt, direction, board):
        target_pt = pt + direction
        if board.is_point_occupied(target_pt):
            return True

        # if direction is diagonal,
        # check if there is a line between the
        # surrounding corners
        is_diagonal = abs(direction.x) > 0 and abs(direction.y) > 0
        if is_diagonal:
            dir_x = PVector(direction.x, 0)
            dir_y = PVector(0, direction.y)
            pt_x = pt + dir_x
            pt_y = pt + dir_y
            if board.is_line_occupied(pt_x, pt_y):
                return True

    def get_best_dir(self, options, target_dir, score_dir):
        if not options:
            return target_dir

        best_score = 0
        best_dir = None
        for this_dir in options:
            score = score_dir(this_dir)
            if score > best_score:
                best_score = score
                best_dir = this_dir

        if best_dir is None:
            return target_dir
        else:
            return best_dir

    def find_next_point(self, last_pt, last_dir, board):
        # travel straight for half of the available
        # straight delta at the start
        straight_delta = self.get_straight_delta()
        straight_start = round(straight_delta * 0.5)

        if len(self.points) < straight_start:
            # attempt to go in the start direction
            target_dir = self.start.direction
        else:
            # go towards the end point
            target_dir = delta_direction(last_pt, self.end.point)

        def score_dir(direction):
            score = 0
            # 0.5 for blocked
            if not self.is_blocked(last_pt, direction, board):
                score += 0.1
            # 0..2 for directionality towards target
            score += dot(direction, target_dir) + 1
            return score

        turn_dirs = get_valid_turn_dirs(last_dir)

        if vector_dist(last_pt, self.end.point) < 5:
            # go directly to target, without fail
            next_dir = target_dir
        else:
            next_dir = self.get_best_dir(turn_dirs, target_dir, score_dir)

        next_pt = last_pt + next_dir
        if self.is_blocked(last_pt, next_dir, board):
            next_pt.visible = False
        return next_pt

    def is_complete(self):
        return (len(self.points) >= 2 and
                vector_equal(self.points[0], self.start.point) and
                vector_equal(self.points[-1], self.end.point))


class CircuitConnector(object):

    def __init__(self, canvas_size):
        self.canvas_size = canvas_size
        self.cell_size = PVector(10, 10)
        self.grid_size = PVector(
            int(self.canvas_size.x / self.cell_size.x),
            int(self.canvas_size.y / self.cell_size.y))
        self.dot_size = 4
        self.socket_size = 10
        self.socket_pairs = []
        self.fill_points = []
        self.dirty = False

    def is_point_occupied(self, pt):
        if pt in self.fill_points:
            return True
        for socket in self.socket_pairs:
            if (vector_equal(socket.start.point, pt) or
                    vector_equal(socket.end.point, pt)):
                return True
            if pt in socket.line.points:
                return True
        return False

    def is_line_occupied(self, pt_a, pt_b):
        for socket in self.socket_pairs:
            if pt_a in socket.line.points:
                index = socket.line.points.index(pt_a)
                if index > 0:
                    prev_pt = socket.line.points[index - 1]
                    if vector_equal(prev_pt, pt_b):
                        return True
                if index < (len(socket.line.points) - 1):
                    next_pt = socket.line.points[index + 1]
                    if vector_equal(next_pt, pt_b):
                        return True

    def add_socket_pair(self, start, end):
        self.socket_pairs.append(SocketPair(start, end))

    def get_pt_location(self, grid_pt):
        return PVector(grid_pt.x * self.cell_size.x,
                       grid_pt.y * self.cell_size.y)

    def get_pt_from_location(self, location):
        return PVector(round(location.x / self.cell_size.x),
                       round(location.y / self.cell_size.y))

    def get_random_pt(self):
        x = random.randrange(0, self.grid_size.x)
        y = random.randrange(0, self.grid_size.y)
        pt = PVector(x, y)
        return pt

    def get_random_socket_direction(self):
        dirs = (
            (1, 0), (0, 1),
            (-1, 0), (0, -1),
        )
        return PVector(*dirs[random.randrange(0, len(dirs))])

    def get_random_socket(self):
        point = self.get_random_pt()
        direction = self.get_random_socket_direction()
        return Socket(point, direction)

    def set_point_occupied(self, pt, occupied):
        if occupied:
            if not self.is_point_occupied(pt):
                self.fill_points.append(pt)
                self.dirty = True
        else:
            if pt in self.fill_points:
                self.fill_points.remove(pt)
                self.dirty = True

    def randomize_sockets(self):
        count = random.randrange(2, 8)
        self.socket_pairs = []
        for i in range(count):
            start = self.get_random_socket()
            end = self.get_random_socket()
            pair = SocketPair(start, end)
            self.socket_pairs.append(pair)

    def rotate_socket(self, pt):
        for socket_pair in self.socket_pairs:
            if vector_equal(socket_pair.start.point, pt):
                socket_pair.start.rotate_direction()
                self.dirty = True
                return
            if vector_equal(socket_pair.end.point, pt):
                socket_pair.end.rotate_direction()
                self.dirty = True
                return

    def set_line_weight(self, pt, weight):
        for socket_pair in self.socket_pairs:
            if pt in socket_pair.line.points:
                socket_pair.line.weight = weight

    def reset_lines(self):
        for socket in self.socket_pairs:
            socket.line.reset()

    def are_all_lines_complete(self):
        for socket in self.socket_pairs:
            if not socket.line.is_complete():
                return False
        return True

    def socket_iter(self):
        def sort_socket(a, b):
            return -cmp(a.line.weight, b.line.weight)

        pairs = self.socket_pairs[:]
        # random.shuffle(pairs)
        pairs.sort(sort_socket)
        for socket in pairs:
            yield socket

    def tick_connection_lines(self):
        for socket in self.socket_iter():
            if not socket.line.is_complete():
                socket.line.tick(self)
                self.dirty = True
                return

    def tick_until_finished(self):
        for socket in self.socket_iter():
            while not socket.line.is_complete():
                socket.line.tick(self)
                self.dirty = True

    def rebuild_connection_lines(self):
        self.reset_lines()
        self.tick_until_finished()

    def draw_point(self, grid_pt, radius, weight):
        pt = self.get_pt_location(grid_pt)
        strokeWeight(weight)
        ellipse(pt.x, pt.y, radius, radius)

    def draw_line(self, start_pt, end_pt, weight):
        start = self.get_pt_location(start_pt)
        end = self.get_pt_location(end_pt)
        strokeWeight(weight)
        line(start.x, start.y, end.x, end.y)

    def draw_if_dirty(self):
        if self.dirty:
            self.draw()

    def draw(self, skip_grid=True):
        self.dirty = False
        background(204)
        if not skip_grid:
            self.draw_grid()
        for socket_pair in self.socket_pairs:
            self.draw_socket_pair(socket_pair)
            self.draw_connecting_line(socket_pair.line)
        self.draw_fill_points()

    def draw_grid(self):
        stroke(*BLACK)
        fill(*BLACK)
        for x in range(int(self.grid_size.x)):
            for y in range(int(self.grid_size.y)):
                self.draw_point(PVector(x, y), 1, 1)

    def draw_fill_points(self):
        stroke(*BLACK)
        fill(*BLACK)
        for pt in self.fill_points:
            self.draw_point(pt, 1, 1)

    def draw_socket_pair(self, socket_pair):
        start = socket_pair.start
        end = socket_pair.end
        stroke(*GREEN)
        self.draw_line(start.point, start.point + start.direction, 10)
        stroke(*RED)
        self.draw_line(end.point, end.point + end.direction, 10)

    def draw_connecting_line(self, line):
        stroke(*BLACK)
        fill(*BLACK)
        for i in range(len(line.points)):
            if i == 0:
                continue
            last_pt = line.points[i - 1]
            pt = line.points[i]
            if not is_point_visible(last_pt):
                if is_point_visible(pt):
                    self.draw_point(pt, self.dot_size, line.weight * 0.5)
                continue
            if not is_point_visible(pt):
                if is_point_visible(last_pt):
                    self.draw_point(last_pt, self.dot_size, line.weight * 0.5)
                continue
            self.draw_line(last_pt, pt, line.weight)


def setup():
    size(960, 540)
    global BOARD
    BOARD = CircuitConnector(PVector(960, 540))


def draw():
    pass


def keyPressed():
    print("pressed %s %d" % (key, keyCode))
    global BOARD
    if BOARD:
        mouse_pt = BOARD.get_pt_from_location(PVector(mouseX, mouseY))

    # line weight
    if keyCode == 49:  # 1
        BOARD.set_line_weight(mouse_pt, 3)
        BOARD.rebuild_connection_lines()
        BOARD.draw()
    elif keyCode == 50:  # 2
        BOARD.set_line_weight(mouse_pt, 5)
        BOARD.rebuild_connection_lines()
        BOARD.draw()
    elif keyCode == 51:  # 3
        BOARD.set_line_weight(mouse_pt, 9)
        BOARD.rebuild_connection_lines()
        BOARD.draw()

    elif keyCode == 67:  # C
        # clear board
        BOARD = CircuitConnector(PVector(960, 540))
        BOARD.draw()
    elif keyCode == 70:  # F
        # fill point
        BOARD.set_point_occupied(mouse_pt, True)
        BOARD.draw_if_dirty()
    elif keyCode == 69:  # E
        # erase
        BOARD.set_point_occupied(mouse_pt, False)
        BOARD.draw_if_dirty()

    elif keyCode == 82:  # R
        # rotate nearby socket
        BOARD.rotate_socket(mouse_pt)
        if BOARD.dirty:
            BOARD.rebuild_connection_lines()
            BOARD.draw()

    # drawing
    elif keyCode == 8:  # backspace
        # reset lines
        BOARD.reset_lines()
        BOARD.draw()
    elif keyCode == 39:  # right
        BOARD.tick_connection_lines()
        BOARD.draw_if_dirty()
    elif keyCode == 32:  # Space
        # tick lines til finished
        BOARD.rebuild_connection_lines()
        BOARD.draw()
    elif keyCode == 10:  # Enter
        # randomize and generate all lines
        BOARD.randomize_sockets()
        BOARD.rebuild_connection_lines()
        BOARD.draw()


def keyReleased():
    print("released %s %d" % (key, keyCode))


def mousePressed():
    print("mousePressed")
    global BOARD
    start = Socket(
        BOARD.get_pt_from_location(PVector(mouseX, mouseY)),
        PVector(1, 0)
    )
    end = Socket(
        PVector(start.point.x + 1, start.point.y),
        PVector(1, 0)
    )
    BOARD.add_socket_pair(start, end)
    BOARD.draw()


def mouseDragged():
    # print("mouseDragged {0}, {1}".format(mouseX, mouseY))
    global BOARD
    pair = BOARD.socket_pairs[-1]
    pair.end.point = BOARD.get_pt_from_location(PVector(mouseX, mouseY))
    pair.auto_set_directions(BOARD)
    BOARD.draw(skip_grid=True)


def mouseReleased():
    print("mouseReleased")
    global BOARD
    pair = BOARD.socket_pairs[-1]
    pair.end.point = BOARD.get_pt_from_location(PVector(mouseX, mouseY))
    pair.auto_set_directions(BOARD)
    BOARD.draw()
