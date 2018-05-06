
import random
import math


BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (180, 30, 0)
GREEN = (110, 180, 30)
BG_COLOR = 204

BOARD = None


def normalize(vector):
    result = PVector(vector.x, vector.y)
    if result.x != 0:
        result.x = math.copysign(1, result.x)
    if result.y != 0:
        result.y = math.copysign(1, result.y)
    return result


class Socket(object):
    def __init__(self, point, direction):
        self.point = point
        self.direction = direction

    def update_direction(self, target_pt):
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

    def update_directions(self, board):
        self.start.update_direction(board.grid_size * 0.5)
        self.end.update_direction(board.grid_size * 0.5)


class ConnectionLine(object):
    def __init__(self, socket_pair):
        self.socket_pair = socket_pair
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
            next_pt = self.find_next_point(last_pt, board)
            self.points.append(next_pt)

    def find_next_point(self, last_pt, board):
        next_pt = PVector(last_pt.x, last_pt.y)
        delta = self.end.point - next_pt
        if delta.x != 0:
            next_pt.x += math.copysign(1, delta.x)
        if delta.y != 0:
            next_pt.y += math.copysign(1, delta.y)
        return next_pt

    def is_complete(self):
        return (len(self.points) >= 2 and
                self.points[0] == self.start.point and
                self.points[-1] == self.end.point)


class CircuitConnector(object):

    def __init__(self, canvas_size):
        self.canvas_size = canvas_size
        self.cell_size = PVector(20, 20)
        self.grid_size = PVector(
            int(self.canvas_size.x / self.cell_size.x),
            int(self.canvas_size.y / self.cell_size.y))
        self.dot_size = 5
        self.line_weight = 4
        self.socket_size = 10
        self.socket_pairs = []

    def is_point_occupied(self, pt):
        for socket in self.socket_pairs:
            if socket.start.point == pt or socket.end.point == pt:
                return True
            if pt in socket.line.points:
                return True
        return False

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

    def randomize_sockets(self):
        count = random.randrange(2, 5)
        self.socket_pairs = []
        for i in range(count):
            start = self.get_random_socket()
            end = self.get_random_socket()
            pair = SocketPair(start, end)
            self.socket_pairs.append(pair)

    def reset_lines(self):
        for socket in self.socket_pairs:
            socket.line.reset()

    def are_all_lines_complete(self):
        for socket in self.socket_pairs:
            if not socket.line.is_complete():
                return False
        return True

    def tick_connection_lines(self):
        for socket in self.socket_pairs:
            if not socket.line.is_complete():
                socket.line.tick(self)

    def undo_last_tick(self):
        for socket in self.socket_pairs:
            if socket.line.points:
                socket.line.points.pop()

    def tick_until_finished(self):
        while not self.are_all_lines_complete():
            self.tick_connection_lines()

    def draw_point(self, grid_pt, radius, weight):
        pt = self.get_pt_location(grid_pt)
        strokeWeight(weight)
        fill(BG_COLOR)
        ellipse(pt.x, pt.y, radius, radius)

    def draw_line(self, start_pt, end_pt, weight=None):
        if weight is None:
            weight = self.line_weight
        start = self.get_pt_location(start_pt)
        end = self.get_pt_location(end_pt)
        strokeWeight(weight)
        noFill()
        line(start.x, start.y, end.x, end.y)

    def draw(self, skip_grid=False):
        background(204)
        if not skip_grid:
            self.draw_grid()
        for socket_pair in self.socket_pairs:
            self.draw_socket_pair(socket_pair)
            self.draw_connecting_line(socket_pair.line)

    def draw_grid(self):
        stroke(*BLACK)
        for x in range(int(self.grid_size.x)):
            for y in range(int(self.grid_size.y)):
                self.draw_point(PVector(x, y), 1, 1)

    def draw_socket_pair(self, socket_pair):
        start = socket_pair.start
        end = socket_pair.end
        stroke(*GREEN)
        self.draw_line(start.point, start.point + start.direction, 10)
        stroke(*RED)
        self.draw_line(end.point, end.point + end.direction, 10)

    def draw_connecting_line(self, line):
        stroke(*BLACK)
        for i in range(len(line.points)):
            if i == 0:
                continue
            last_pt = line.points[i - 1]
            pt = line.points[i]
            self.draw_line(last_pt, pt)


def setup():
    size(960, 540)
    global BOARD
    BOARD = CircuitConnector(PVector(960, 540))


def draw():
    pass


def keyPressed():
    print("pressed %s %d" % (key, keyCode))
    global BOARD
    if keyCode == 49:  # 1
        # clear board
        BOARD = CircuitConnector(PVector(960, 540))
        BOARD.draw()
    elif keyCode == 50:  # 2
        # randomize sockets
        BOARD.randomize_sockets()
        BOARD.draw()
    elif keyCode == 8:  # left
        # reset lines
        BOARD.reset_lines()
        BOARD.draw()
    elif keyCode == 37:  # right
        BOARD.undo_last_tick()
        BOARD.draw()
    elif keyCode == 39:  # right
        # tick lines
        BOARD.tick_connection_lines()
        BOARD.draw()
    elif keyCode == 32:  # Space
        # tick lines til finished
        BOARD.tick_until_finished()
        BOARD.draw()
    elif keyCode == 10:  # Enter
        # randomize and generate all lines
        BOARD.randomize_sockets()
        BOARD.tick_until_finished()
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
    pair.update_directions(BOARD)
    BOARD.draw(skip_grid=True)


def mouseReleased():
    print("mouseReleased")
    global BOARD
    pair = BOARD.socket_pairs[-1]
    pair.end.point = BOARD.get_pt_from_location(PVector(mouseX, mouseY))
    pair.update_directions(BOARD)
    BOARD.draw()
