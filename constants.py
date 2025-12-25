import pygame

# Настройки окна
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900
TILE_SIZE = 64
CHAR_SIZE = 128
FPS = 60

LEVELS = [
    "assets/level-1.tmx",
    "assets/level-2.tmx",
    "assets/level-3.tmx",
    "assets/level-4.tmx",
    "assets/level-5.tmx",
    "assets/level-6.tmx",
    "assets/level-7.tmx",
    "assets/level-8.tmx",
    "assets/level-9.tmx",
    "assets/level-10.tmx"
]
BACKGROUNDS = [
    "assets/background-1.png",
    "assets/background-2.png",
    "assets/background-3.png",
    "assets/background-4.png",
    "assets/background-4.png",
    "assets/background-4.png",
    "assets/background-4.png",
    "assets/background-4.png",
    "assets/background-4.png",
    "assets/background-4.png"
]
FON_MUSIC=[
    "assets/music/l1.mp3",
    "assets/music/l2.mp3",
    "assets/music/l3.mp3",
    "assets/music/l4.mp3",
    "assets/music/l5.mp3",
    "assets/music/l6.mp3",
    "assets/music/l7.mp3",
    "assets/music/l8.mp3",
    "assets/music/l9.mp3"
]
CURRENT_LEVEL = 0

# Загружаем звуки
SHOOT_SOUND = pygame.mixer.Sound("assets/music/shoot.mp3")
HIT_SOUND = pygame.mixer.Sound("assets/music/damage2.mp3")
ENEMY_DEATH_SOUND = pygame.mixer.Sound("assets/music/kill.mp3")
LEVEL_COMPLETE_SOUND = pygame.mixer.Sound("assets/music/portal.mp3")
PICKUP_SOUND = pygame.mixer.Sound("assets/music/selection.mp3")
HEAL_SOUND = pygame.mixer.Sound("assets/music/heal.mp3")

# Громкость
SHOOT_SOUND.set_volume(2)
HIT_SOUND.set_volume(2)
ENEMY_DEATH_SOUND.set_volume(2)
LEVEL_COMPLETE_SOUND.set_volume(2)
PICKUP_SOUND.set_volume(2)
HEAL_SOUND.set_volume(2)

