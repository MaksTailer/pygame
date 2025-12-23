import pygame
import math
from constants import TILE_SIZE, CHAR_SIZE
import random

class Projectile:
    def __init__(self, x, y, vx, vy, color=(0,255,0), life=3000, image=None, size=8):
        self.pos = pygame.Vector2(x, y)
        self.v = pygame.Vector2(vx, vy)
        self.color = color
        self.spawn_time = pygame.time.get_ticks()
        self.life = life
        self.image = image
        self.size = max(1, int(size))
        if self.image:
            # rect по центру изображения
            self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        else:
            # центрируем прямоугольник по позиции
            self.rect = pygame.Rect(int(self.pos.x) - self.size//2, int(self.pos.y) - self.size//2, self.size, self.size)

    def update(self, dt):
        self.pos += self.v * dt
        if self.image:
            self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        else:
            self.rect.center = (int(self.pos.x), int(self.pos.y))
        return pygame.time.get_ticks() - self.spawn_time > self.life

    def draw(self, surf, offset):
        if self.image:
            r = self.image.get_rect(center=(self.rect.centerx + offset[0], self.rect.centery + offset[1]))
            surf.blit(self.image, r.topleft)
        else:
            r = self.rect.move(offset[0], offset[1])
            pygame.draw.rect(surf, self.color, r)


class Boss:
    """Босс — большой вирус с усиленной атакой"""
    def __init__(self, x, y, sprites):
        self.hitbox = pygame.Rect(int(x), int(y), 256, 256)
        self.sprites = sprites
        self.image = self.sprites.get("idle1", pygame.Surface((256, 256)))
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)
        self.hp = 20
        self.max_hp = 20
        self.vel_y = 0
        self.gravity = 0.8
        self.on_ground = False
        self.facing_right = True

        self.shoot_delay = 1400   #  было 500
        self.last_shot = 0
        self.attack_phase = 0  # 0 = обычная атака, 1 = круговая атака
        self.phase_time = 0
        self.phase_duration = 3000  # 3 сек на фазу

    def update(self, player, tiles, projectiles):
        now = pygame.time.get_ticks()
        
        # гравитация + вертикальное движение
        self.vel_y += self.gravity
        if self.vel_y > 12:
            self.vel_y = 12
        
        self.hitbox.y += int(self.vel_y)
        self.on_ground = False
        
        for t in tiles:
            if isinstance(t, pygame.Rect) and t.colliderect(self.hitbox):
                if self.vel_y > 0:
                    self.hitbox.bottom = t.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.hitbox.top = t.bottom
                    self.vel_y = 0
        
        # логика фаз атаки (меняем каждые 3 сек)
        self.phase_time += 1
        if self.phase_time > self.phase_duration:
            self.attack_phase = (self.attack_phase + 1) % 2
            self.phase_time = 0
        
        # движение к игроку (горизонтальное)
        dx_to_player = player.hitbox.centerx - self.hitbox.centerx
        if abs(dx_to_player) > 50:
            move_dir = 1 if dx_to_player > 0 else -1
            self.hitbox.x += int(move_dir * 1.5)
            self.facing_right = move_dir > 0
        
        # столкновения с тайлами (горизонтальные)
        for t in tiles:
            if isinstance(t, pygame.Rect) and t.colliderect(self.hitbox):
                if dx_to_player > 0:
                    self.hitbox.right = t.left
                else:
                    self.hitbox.left = t.right
        
        # прыжок на игрока
        if self.on_ground and abs(dx_to_player) < 300:
            if random.random() < 0.01:  # 1% шанс каждый кадр
                self.vel_y = -16
                self.on_ground = False
        
        # атака (зависит от фазы)
        if self.attack_phase == 0:
            # обычная атака: в сторону игрока
            if now - self.last_shot >= self.shoot_delay:
                px = self.hitbox.centerx
                py = self.hitbox.centery
                vec = pygame.Vector2(player.hitbox.centerx - px, player.hitbox.centery - py)
                if vec.length() == 0:
                    vec = pygame.Vector2(1, 0)
                vec = vec.normalize()
                # даём боссу мощный, но редкий снаряд — увеличим размер в 4 раза
                proj_speed = 6
                proj_size = 8 * 4  # увеличение размера в 4 раза
                proj = Projectile(px, py, vec.x * proj_speed, vec.y * proj_speed, color=(215, 245, 20), size=proj_size)
                projectiles.append(proj)
                self.last_shot = now
        else:
            # круговая атака: стреляет во все стороны, реже и чуть медленнее
            if now - self.last_shot >= int(self.shoot_delay * 1.6):
                px = self.hitbox.centerx
                py = self.hitbox.centery
                num_projectiles = 8
                for i in range(num_projectiles):
                    angle = (i / num_projectiles) * 2 * math.pi
                    vx = math.cos(angle) * 4.5
                    vy = math.sin(angle) * 4.5
                    # круговые снаряды чуть меньше, но заметные
                    proj = Projectile(px, py, vx, vy, color=(200, 50, 200), size=16)
                    projectiles.append(proj)
                self.last_shot = now
        
        self.image = self.sprites.get("idle1", self.image)
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)

    def draw(self, surf, offset):
        draw_pos = (self.rect.x + offset[0], self.rect.y + offset[1])
        surf.blit(self.image, draw_pos)
        
        # рисуем полоску HP над боссом
        bar_width = self.rect.width
        bar_height = 10
        bar_x = draw_pos[0]
        bar_y = draw_pos[1] - 20
        pygame.draw.rect(surf, (255, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        hp_ratio = max(0, self.hp / self.max_hp)
        pygame.draw.rect(surf, (0, 255, 0), (bar_x, bar_y, bar_width * hp_ratio, bar_height))

    def damage(self, amount):
        self.hp -= amount
        return self.hp <= 0



class Bacteria:
    def __init__(self, x, y, sprites):
        self.hitbox = pygame.Rect(int(x), int(y), TILE_SIZE, TILE_SIZE)
        self.sprites = sprites
        self.image = self.sprites.get("idle", pygame.Surface((TILE_SIZE, TILE_SIZE)))
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)
        self.speed = 1.6
        self.hp = 3
        self.max_hp = self.hp
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
        # полоска HP
        bar_width = max(24, self.rect.width)
        bar_height = 6
        bar_x = draw_pos[0]
        bar_y = draw_pos[1] - 10
        pygame.draw.rect(surf, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height))
        hp_ratio = max(0, self.hp / getattr(self, "max_hp", max(1, self.hp)))
        pygame.draw.rect(surf, (0, 200, 0), (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))


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
        self.max_hp = self.hp
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
        # полоска HP
        bar_width = max(24, self.rect.width)
        bar_height = 6
        bar_x = draw_pos[0]
        bar_y = draw_pos[1] - 8
        pygame.draw.rect(surf, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height))
        hp_ratio = max(0, self.hp / getattr(self, "max_hp", max(1, self.hp)))
        pygame.draw.rect(surf, (0, 200, 0), (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))


    def damage(self, amount):
        self.hp -= amount
        return self.hp <= 0