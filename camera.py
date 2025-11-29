import pygame
from constants import *

class Camera:
    def __init__(self):
        self.offset_x = 0
        self.offset_y = 0

    def update(self, player):
        # Следим за игроком по X и Y
        self.offset_x = -(player.rect.x - SCREEN_WIDTH // 2)
        self.offset_y = -(player.rect.y - SCREEN_HEIGHT // 2)