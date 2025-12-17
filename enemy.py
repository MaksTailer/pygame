import pygame
import math
from constants import TILE_SIZE, CHAR_SIZE

class Projectile:
    def __init__(self, x, y, vx, vy, color=(0,255,0), life=3000, image=None):
        self.pos = pygame.Vector2(x, y)
        self.v = pygame.Vector2(vx, vy)
        self.color = color
        self.spawn_time = pygame.time.get_ticks()
        self.life = life
        self.image = image
        if self.image:
            # rect по центру изображения
            self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        else:
            self.rect = pygame.Rect(int(x), int(y), 8, 8)

    def update(self, dt):
        self.pos += self.v * dt
        if self.image:
            self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        else:
            self.rect.topleft = (int(self.pos.x), int(self.pos.y))
        return pygame.time.get_ticks() - self.spawn_time > self.life

    def draw(self, surf, offset):
        if self.image:
            r = self.image.get_rect(center=(self.rect.centerx + offset[0], self.rect.centery + offset[1]))
            surf.blit(self.image, r.topleft)
        else:
            r = self.rect.move(offset[0], offset[1])
            pygame.draw.rect(surf, self.color, r)

class Bacteria:
    def __init__(self, x, y, sprites):
        self.hitbox = pygame.Rect(int(x), int(y), TILE_SIZE, TILE_SIZE)
        self.sprites = sprites
        self.image = self.sprites.get("idle", pygame.Surface((TILE_SIZE, TILE_SIZE)))
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)
        self.speed = 1.6
        self.hp = 3
        self.shoot_delay = 1200
        self.last_shot = 0
        self.facing_right = True
        self.anim_frame = 0
        
        # Физика
        self.vel_y = 0
        self.on_ground = False
        self.jump_power = -12
        self.gravity = 0.6

    def check_ground(self, tiles):
        """Проверяем, есть ли земля под врагом"""
        feet = pygame.Rect(self.hitbox.x, self.hitbox.bottom, self.hitbox.width, 2)
        for t in tiles:
            if isinstance(t, pygame.Rect) and t.colliderect(feet):
                return True
        return False

    # ...existing code...
    def can_move_forward(self, tiles, dx):
        """Проверяем, может ли враг пройти в сторону (нет обрыва или стены).
        Останавливается на краю (последний тайл перед пропастью)."""
        dir_sign = 1 if dx >= 0 else -1

        # 1) проверка на стену непосредственно перед врагом (малый шаг)
        future_x = self.hitbox.copy()
        future_x.x += int(dir_sign * max(1, abs(dx)))
        for t in tiles:
            if isinstance(t, pygame.Rect) and t.colliderect(future_x):
                # есть стена — проверяем, можно ли прыгнуть на неё на 1 тайл вверх
                if t.bottom <= self.hitbox.bottom and t.bottom >= self.hitbox.bottom - TILE_SIZE:
                    return True, "jump"
                return False, None

        # 2) проверка на пропасть: смотрим за 1 тайл вперед (последний безопасный тайл)
        stop_tiles_before_cliff = 1  # останавливаться на краю (1 тайл)
        look_ahead_tiles = stop_tiles_before_cliff
        # берём центральную X позицию и смотрим на точку за look_ahead_tiles тайлов
        check_x_center = self.hitbox.centerx + dir_sign * (look_ahead_tiles * TILE_SIZE)
        # приводим к индексу тайла и формируем прямоугольник под ногами этого тайла
        tile_x = int(check_x_center) // TILE_SIZE
        cliff_check = pygame.Rect(tile_x * TILE_SIZE, self.hitbox.bottom, TILE_SIZE, TILE_SIZE)

        has_ground = False
        for t in tiles:
            if isinstance(t, pygame.Rect) and t.colliderect(cliff_check):
                has_ground = True
                break

        if not has_ground:
            return False, None  # впереди пропасть — не идём (останавливаемся на краю)

        return True, None
# ...existing code...

    def update(self, player, tiles, projectiles):
        now = pygame.time.get_ticks()
        dx_to_player = (player.hitbox.centerx - self.hitbox.centerx)
        dy_to_player = abs(player.hitbox.centery - self.hitbox.centery)
        
        current_img = self.sprites.get("idle")
        
        # гравитация
        self.vel_y += self.gravity
        if self.vel_y > 10:
            self.vel_y = 10
        
        # применяем вертикальное движение и коллизии
        self.hitbox.y += int(self.vel_y)
        self.on_ground = False
        
        for t in tiles:
            if isinstance(t, pygame.Rect) and t.colliderect(self.hitbox):
                if self.vel_y > 0:  # падаем вниз
                    self.hitbox.bottom = t.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:  # летим вверх
                    self.hitbox.top = t.bottom
                    self.vel_y = 0
        
        # преследование
        if abs(dx_to_player) < 800 and dy_to_player < 200:
            direction = 1 if dx_to_player > 0 else -1
            can_move, action = self.can_move_forward(tiles, int(direction * self.speed))
            
            if can_move or action == "jump":
                # движемся
                self.hitbox.x += int(direction * self.speed)
                self.facing_right = direction > 0
                
                # прыжок на ступеньку вверх
                if action == "jump" and self.on_ground:
                    self.vel_y = self.jump_power
                    self.on_ground = False
                
                # анимация ходьбы
                self.anim_frame = (pygame.time.get_ticks() // 200) % 2
                current_img = self.sprites.get("walk1" if self.anim_frame == 0 else "walk2", self.sprites.get("idle"))
                
                # стрельба
                if now - self.last_shot >= self.shoot_delay:
                    px = self.hitbox.centerx + direction * (TILE_SIZE//2 + 4)
                    py = self.hitbox.centery - 4
                    proj = Projectile(px, py, direction * 0.35, 0, color=(0, 220, 0))
                    projectiles.append(proj)
                    self.last_shot = now
        
        # отражаем спрайт если смотрит влево
        if not self.facing_right:
            current_img = pygame.transform.flip(current_img, True, False)
        
        self.image = current_img
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)

    def draw(self, surf, offset):
        draw_pos = (self.rect.x + offset[0], self.rect.y + offset[1])
        surf.blit(self.image, draw_pos)

    def damage(self, amount):
        self.hp -= amount
        return self.hp <= 0
    

class Virus:
    def __init__(self, x, y, sprites):
        self.hitbox = pygame.Rect(int(x), int(y), TILE_SIZE, TILE_SIZE)
        self.sprites = sprites
        self.image = self.sprites.get("idle", pygame.Surface((TILE_SIZE, TILE_SIZE)))
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)
        self.hp = 2
        self.shoot_delay = 800  # базовый интервал
        self.last_shot = 0
        self.facing_right = True
        self.anim_frame = 0

        # Полёт / патруль
        self.start_x = x
        self.start_y = y  # фиксированная высота патруля
        self.patrol_radius = TILE_SIZE * 6  # радиус патруля (по X) — можно изменить
        self.patrol_speed = 1.2
        self.patrol_dir = 1

        # Синусоидальная атака
        self.flight_time = 0
        self.flight_amplitude = 18
        self.flight_frequency = 0.08
        self.chase_speed = 2.6  # скорость при преследовании

        # агро-параметры
        self.aggro_distance_x = TILE_SIZE * 10  # если игрок ближе по X — агро
        self.aggro_distance_y = TILE_SIZE * 6   # по Y — ограничение агро

    def update(self, player, tiles, projectiles):
        now = pygame.time.get_ticks()

        dx_to_player = player.hitbox.centerx - self.hitbox.centerx
        dy_to_player = player.hitbox.centery - self.hitbox.centery
        abs_dx = abs(dx_to_player)
        abs_dy = abs(dy_to_player)

        # состояние: патруль или агро
        aggro = (abs_dx <= self.aggro_distance_x and abs_dy <= self.aggro_distance_y)

        self.flight_time += 1

        if not aggro:
            # ПАТРУЛЬ: летим ровно на start_y, туда-обратно в пределах patrol_radius
            move_x = self.patrol_speed * self.patrol_dir
            self.hitbox.x += int(move_x)
            # держим фиксированную высоту
            self.hitbox.y = int(self.start_y)

            # при достижении границ радиуса — разворачиваемся
            cx = self.hitbox.centerx
            if cx < self.start_x - self.patrol_radius or cx > self.start_x + self.patrol_radius:
                # откат назад и смена направления
                self.patrol_dir *= -1
                self.hitbox.x += int(self.patrol_speed * self.patrol_dir) * 2

            # при столкновении со стеной — разворачиваемся
            for t in tiles:
                if isinstance(t, pygame.Rect) and t.colliderect(self.hitbox):
                    # откат и смена направления
                    if self.patrol_dir > 0:
                        self.hitbox.right = t.left
                    else:
                        self.hitbox.left = t.right
                    self.patrol_dir *= -1
                    break

            # визуал: смотрим по направлению патруля
            self.facing_right = self.patrol_dir > 0

            shoot_delay = max(self.shoot_delay, 1200)  # редко стреляет в патруле

        else:
            # AGGRO: преследуем игрока, движение по X к игроку + синусоида по Y
            # простая логика: направиться в сторону игрока с ограничением скорости
            dir_sign = 1 if dx_to_player > 0 else -1
            desired_speed = min(self.chase_speed, max(0.6, abs_dx / (TILE_SIZE * 2)))
            move_x = desired_speed * dir_sign
            move_y = self.flight_amplitude * math.sin(self.flight_time * self.flight_frequency)

            self.hitbox.x += int(move_x)
            self.hitbox.y = int(self.start_y + move_y)

            # при столкновении со стеной — откатываемся и пробуем перелететь (простая логика: развернуться)
            for t in tiles:
                if isinstance(t, pygame.Rect) and t.colliderect(self.hitbox):
                    if move_x > 0:
                        self.hitbox.right = t.left
                    else:
                        self.hitbox.left = t.right
                    # слегка отступаем и чуть меняем высоту, чтобы не застрять
                    self.hitbox.y -= TILE_SIZE // 2
                    break

            self.facing_right = move_x > 0

            # более частая стрельба при агро
            shoot_delay = 400

            # Атака: стреляем в направлении игрока
            if now - self.last_shot >= shoot_delay:
                px = self.hitbox.centerx
                py = self.hitbox.centery
                vec = pygame.Vector2(player.hitbox.centerx - px, player.hitbox.centery - py)
                if vec.length() == 0:
                    vec = pygame.Vector2(1, 0)
                vec = vec.normalize()
                proj_speed = 5.0
                vx = vec.x * proj_speed
                vy = vec.y * proj_speed
                proj = Projectile(px, py, vx, vy, color=(150, 255, 120))
                projectiles.append(proj)
                self.last_shot = now

        # Анимация (простая)
        self.anim_frame = (pygame.time.get_ticks() // 200) % 2
        current_img = self.sprites.get("walk1" if self.anim_frame == 0 else "walk2", self.sprites.get("idle"))

        # отражение спрайта по направлению движения
        if not self.facing_right:
            current_img = pygame.transform.flip(current_img, True, False)

        self.image = current_img
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)


    def draw(self, surf, offset):
        draw_pos = (self.rect.x + offset[0], self.rect.y + offset[1])
        surf.blit(self.image, draw_pos)

    def damage(self, amount):
        self.hp -= amount
        return self.hp <= 0