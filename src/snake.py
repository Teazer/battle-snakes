# -*- coding: utf-8 -*-
"""
Snake module.
"""

from pygame import Rect

from settings import (INVINCIBILITY_BLINK_RATE, MAX_HITPOINTS,
                      INIT_SPEED, MIN_SPEED, MAX_SPEED)
from utils import add_vecs, sub_vecs, normalize, m_distance

# -- Directions --
RIGHT = (+1, 0)
LEFT = (-1, 0)
UP = (0, -1)
DOWN = (0, +1)
DIRECTIONS = {'right': RIGHT, 'left': LEFT, 'up': UP, 'down': DOWN}

STRAIGHT1_V = Rect(20, 20, 10, 10)
STRAIGHT1_H = Rect(20, 30, 10, 10)
STRAIGHT2_V = Rect(30, 20, 10, 10)
STRAIGHT2_H = Rect(30, 30, 10, 10)

N = 0x1
E = 0x2
S = 0x4
W = 0x8
SE = S + E
SW = S + W
NE = N + E
NW = N + W

STRAIGHT = 0x10
VERTICAL = 0x20

# Maps vectors to their corresponding flags.
VEC_TO_DIRFLAG = {(0, -1): N, (1, 0): E, (0, 1): S, (-1, 0): W}

HEAD = {N: Rect(00, 00, 10, 10), S: Rect(10, 10, 10, 10),
        E: Rect(10, 00, 10, 10), W: Rect(00, 10, 10, 10)}

TAIL = {N: Rect(20, 00, 10, 10), S: Rect(30, 10, 10, 10),
        E: Rect(30, 00, 10, 10), W: Rect(20, 10, 10, 10)}

TURN = {SE: Rect(00, 20, 10, 10), SW: Rect(10, 20, 10, 10),
        NE: Rect(00, 30, 10, 10), NW: Rect(10, 30, 10, 10)}


def get_arrangement(snake, index, tilemap):

    """
    Get the arrangement of a snake part in relation to it's neighboring
    parts while taking the map and it's portals into account as well.
    This is to determine which part of the skin texture to use for
    rendering said part.
    """

    ax, ay = a = snake[index - 1]
    bx, by = b = snake[index]
    cx, cy = c = snake[index + 1]

    ba = sub_vecs(a, b)
    bc = sub_vecs(c, b)

    ba_apart = m_distance(a, b) > 1
    bc_apart = m_distance(c, b) > 1

    a_on_edge = tilemap.on_edge(a)

    if ba_apart:
        if a_on_edge:
            ba = normalize(ba)

        next_portal = None
        for portal in tilemap.portals.keys():
            if m_distance(portal, b) == 1:
                next_portal = portal
                break

        if next_portal:
            a = next_portal
            ax, ay = a
            ba = sub_vecs(a, b)

    if bc_apart:
        if a_on_edge:
            bc = normalize((-bc[0], -bc[1]))

        next_portal = None
        for portal in tilemap.portals.keys():
            if m_distance(portal, b) == 1:
                next_portal = portal
                break

        if next_portal:
            c = next_portal
            cx, cy = c
            bc = sub_vecs(c, b)

    if ax == bx == cx:
        return VERTICAL | STRAIGHT
    elif ay == by == cy:
        return STRAIGHT
    else:
        return VEC_TO_DIRFLAG[ba] | VEC_TO_DIRFLAG[bc]


class SnakeNormalState(object):

    """
    The state, the snake is normally in.
    """

    def __init__(self, snake):
        self.snake = snake

    def update(self, delta_time):
        """Update state."""
        self.snake.move()


class SnakeInvincibleState(object):

    """
    The state, the snake is in when it's invincible.
    """

    def __init__(self, snake, lifetime):
        self.snake = snake
        self.snake.isinvincible = True
        self.lifetime = lifetime
        self.elapsed_lifetime = 0.
        self.elapsed_blink = 0.

    def update(self, delta_time):
        """Update state."""
        self.elapsed_lifetime += delta_time
        self.elapsed_blink += delta_time

        if self.elapsed_blink >= INVINCIBILITY_BLINK_RATE:
            self.elapsed_blink -= INVINCIBILITY_BLINK_RATE
            self.snake.isvisible = not self.snake.isvisible

        if self.elapsed_lifetime >= self.lifetime:
            self.snake.change_state(SnakeNormalState(self.snake))

        self.snake.move()

    def leave(self):
        """Leave state."""
        self.snake.isinvincible = False
        self.snake.isvisible = True


class Snake(object):

    """
    Represents a snake.
    """

    def __init__(self, game, pos, skin, _id, killed_handler):
        self.game = game
        self.body_tag = '#p{0}-body'.format(_id)
        self.head_tag = '#p{0}-head'.format(_id)
        self.skin = skin
        self.body = [pos, (pos[0] + 1, pos[1])]
        self.heading = None
        self._hitpoints = MAX_HITPOINTS
        self._speed = INIT_SPEED
        self._speed_bonus = 0
        self.elapsed_t = 0.
        self.grow = 0
        self.isalive = True
        self.isvisible = True
        self.isinvincible = False
        self.ismoving = False
        self.curr_state = SnakeInvincibleState(self, 5)
        self.killed_event = killed_handler
        self.prev = self.body[:]
        self.prev_heading = self.heading

    @property
    def hitpoints(self):
        """Return hitpoints."""
        return self._hitpoints

    @hitpoints.setter
    def hitpoints(self, value):
        """Set hitpoints."""
        if value > MAX_HITPOINTS:
            self._hitpoints = MAX_HITPOINTS
        elif value < 0:
            self._hitpoints = 0
        else:
            self._hitpoints = value

    @property
    def speed(self):
        """Return speed."""
        return self._speed

    @speed.setter
    def speed(self, value):
        """Set speed."""
        if value > MAX_SPEED:
            self._speed = MAX_SPEED
        elif value < MIN_SPEED:
            self._speed = MIN_SPEED
        else:
            self._speed = value

    @property
    def speed_bonus(self):
        """Return speed bonus."""
        return self._speed_bonus

    @speed_bonus.setter
    def speed_bonus(self, value):
        """Set speed bonus."""
        self._speed_bonus = value

    def gain_speed(self, speed):
        """Increase (or decrease) speed."""
        self.speed += speed

    def gain_hitpoints(self, hitpoints):
        """Increase (or decrease) hitpoints."""
        self.hitpoints += hitpoints
        if self.hitpoints > MAX_HITPOINTS:
            self.hitpoints = MAX_HITPOINTS

    def set_heading(self, new_heading):
        """Set heading."""
        self.prev_heading = self.heading
        self.heading = (normalize(new_heading) if new_heading != (0, 0)
                        else new_heading)

    def change_state(self, new_state):
        """Transit to another state."""
        if hasattr(self.curr_state, 'leave'):
            self.curr_state.leave()
        self.curr_state = new_state

    def take_damage(self, dmg, dealt_by, setback=False,
                    invincible=False, invinc_lifetime=0, shrink=0, slowdown=0):
        """Take damage."""
        if not self.isinvincible:
            self.hitpoints -= dmg
            for _ in range(shrink):
                if len(self.body) == 2:
                    break
                if setback:
                    self.prev.pop()
                else:
                    self.body.pop()
            self.gain_speed(-slowdown)

        if setback:
            # Set the snake back to its previous position
            self.body = self.prev[:]
            xpos = 0
            ypos = 0
            if self.body[0][0] > self.body[1][0]:
                xpos = 1
            elif self.body[0][0] < self.body[1][0]:
                xpos = -1
            if self.body[0][1] > self.body[1][1]:
                ypos = 1
            elif self.body[0][1] < self.body[1][1]:
                ypos = -1
            self.set_heading((xpos, ypos))
            self.prev_heading = (xpos, ypos)

        if invincible and not self.isinvincible:
            self.change_state(SnakeInvincibleState(self, invinc_lifetime))

        if self.hitpoints <= 0:
            self.isalive = False
            self.killed_event(dealt_by)

    def respawn(self, pos):
        """Respawn snake."""
        self.body = [pos, (pos[0] + 1, pos[1])]
        self._speed = INIT_SPEED
        self.heading = None
        self.prev_heading = None
        self.ismoving = False
        self.isalive = True
        self.hitpoints = MAX_HITPOINTS
        self.change_state(SnakeInvincibleState(self, 3.5))
        self.elapsed_t = 0

    def update(self, delta_time):
        """Update snake."""
        if not self.isalive:
            return

        if self.ismoving:
            self.elapsed_t += delta_time

        self.curr_state.update(delta_time)

    def move(self):
        """Move snake."""
        if not self.ismoving:
            return

        self.body[0] = self.game.toroidal(self.body[0])
        # Move Snake
        if self.elapsed_t >= 1. / (self._speed + self._speed_bonus):
            self.prev = self.body[:]
            self.elapsed_t -= 1. / (self._speed + self._speed_bonus)
            self.body.insert(0, add_vecs(self.body[0], self.heading))
            if self.grow == 0:
                self.body.pop()
            elif self.grow > 0:
                self.grow -= 1
            elif self.grow < 0:
                for _ in range(-self.grow+1):
                    if len(self.body) == 2:
                        break
                    self.body.pop()
                self.grow = 0

    def draw(self):
        """Draw snake."""
        if not self.isalive:
            return
        if self.isvisible:
            body_len = len(self.body)
            area = None

            # Needs refactoring, indentation is way too deep...
            for index, part in enumerate(self.body):
                if index == 0:
                    if self.heading and self.heading != (0, 0):
                        area = HEAD[VEC_TO_DIRFLAG[self.heading]]
                    else:
                        area = HEAD[W]

                elif 0 < index < (body_len - 1):
                    argm = get_arrangement(self.body, index,
                                           self.game.tilemap)

                    if argm & STRAIGHT == STRAIGHT:
                        if argm & VERTICAL == VERTICAL:
                            if index % 2:
                                area = STRAIGHT1_V
                            else:
                                area = STRAIGHT2_V
                        else:
                            if index % 2:
                                area = STRAIGHT1_H
                            else:
                                area = STRAIGHT2_H
                    else:
                        area = TURN[argm & 15]
                else:
                    if self.heading and self.heading != (0, 0):
                        vec = sub_vecs(self.body[body_len-2],
                                       self.body[body_len-1])
                        area = TAIL[VEC_TO_DIRFLAG[normalize(vec)]]
                    else:
                        area = TAIL[W]

                self.game.graphics.draw(self.skin, part, area=area)

    def __setitem__(self, i, item):
        self.body[i] = item

    def __getitem__(self, i):
        return self.body[i]
