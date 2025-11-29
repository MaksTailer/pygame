import pygame
from constants import *
# ...existing code...
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, map_height, sprites):
        super().__init__()
        self.sprites = sprites
        self.image = self.sprites["idle"]
        # визуальный rect (для отрисовки) — будет синхронизирован с хитбоксом
        self.rect = self.image.get_rect(topleft=(x, y))
        # ФИЗИЧЕСКИЙ хитбокс (размер под тайл)
        self.hitbox = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
        self.vel_y = 0
        self.on_ground = False
        self.hp = 10
        self.facing_right = True
        self.last_hit_time = 0
        self.invincible_delay = 1000
        self.map_height = map_height  # высота карты в пикселях
        self.fall_start_time = None   # время начала падения за пределы карты

# ...existing code...
    def update(self, tiles, traps, in_water=False, in_quicksand=False):
        import pygame
        keys = pygame.key.get_pressed()
        dx = 0

        # базовая скорость перемещения (вне воды и зыбучих песков)
        base_speed = 5
        if in_water:
            base_speed = max(1, int(base_speed * 0.5))
        elif in_quicksand:
            base_speed = max(1, int(base_speed * 0.25))

        # Движение и анимация — используем base_speed
        if keys[pygame.K_LEFT]:
            dx = -base_speed
            current_img = self.sprites["walk1"] if pygame.time.get_ticks() // 200 % 2 == 0 else self.sprites["walk2"]
            self.facing_right = False
        elif keys[pygame.K_RIGHT]:
            dx = base_speed
            current_img = self.sprites["walk1"] if pygame.time.get_ticks() // 200 % 2 == 0 else self.sprites["walk2"]
            self.facing_right = True
        else:
            current_img = self.sprites["idle"]

        # Прыжок (сила прыжка не уменьшается)
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = -15
            self.on_ground = False
            current_img = self.sprites["jump"]

        # Гравитация
        self.vel_y += 1
        if self.vel_y > 10:
            self.vel_y = 10
        dy = self.vel_y

        # Сбрасываем состояние на землю
        self.on_ground = False

        # Горизонтальная коллизия по хитбоксу
        future_rect_x = self.hitbox.copy()
        future_rect_x.x += dx
        for tile in tiles:
            if isinstance(tile, pygame.Rect) and tile.colliderect(future_rect_x):
                if dx > 0:
                    self.hitbox.right = tile.left
                elif dx < 0:
                    self.hitbox.left = tile.right
                dx = 0
                break

        # Вертикальная коллизия по хитбоксу
        future_rect_y = self.hitbox.copy()
        future_rect_y.y += dy
        for tile in tiles:
            if isinstance(tile, pygame.Rect) and tile.colliderect(future_rect_y):
                if dy > 0:
                    self.hitbox.bottom = tile.top
                    self.vel_y = 0
                    self.on_ground = True
                elif dy < 0:
                    self.hitbox.top = tile.bottom
                    self.vel_y = 0
                dy = 0
                break

        # Проверка ловушек
        now = pygame.time.get_ticks()
        for trap in traps:
            trect = trap if isinstance(trap, pygame.Rect) else getattr(trap, "rect", None)
            if isinstance(trect, pygame.Rect):
                trap_collision = trect.inflate(-40, -40)
                if trap_collision.colliderect(self.hitbox):
                    if now - self.last_hit_time > self.invincible_delay:
                        self.hp -= 1
                        self.last_hit_time = now
                        if self.hp <= 0:
                            try:
                                restart_game()
                            except NameError:
                                pygame.event.post(pygame.event.Event(pygame.QUIT))

        # Применяем движения к хитбоксу
        self.hitbox.x += dx
        self.hitbox.y += dy

        # Если игрок ниже границы карты — отслеживаем длительность падения
        if self.hitbox.top > self.map_height:
            if not self.on_ground:
                if self.fall_start_time is None:
                    self.fall_start_time = now
                elif now - self.fall_start_time > 3000:
                    self.hp = 0
                    try:
                        restart_game()
                    except NameError:
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
            else:
                self.fall_start_time = None
        else:
            self.fall_start_time = None

        # Синхронизируем визуальный rect с хитбоксом
        if not self.facing_right:
            self.image = pygame.transform.flip(current_img, True, False)
        else:
            self.image = current_img
        self.rect = self.image.get_rect(midbottom=self.hitbox.midbottom)