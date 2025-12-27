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
    """Босс — умный вирус с многофазной атакой и тактикой"""
    def __init__(self, x, y, sprites, hp=None):
        self.hitbox = pygame.Rect(int(x), int(y), 256, 256)
        self.sprites = sprites
        self.image = self.sprites.get("idle1", pygame.Surface((256, 256)))
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)
        self.max_hp = int(hp) if hp is not None else 40  # увеличена сложность
        self.hp = self.max_hp
        self.vel_y = 0
        self.gravity = 0.8
        self.on_ground = False
        self.facing_right = True

        # Фазы боя
        self.phase = 0  # 0=обычная, 1=агрессивная, 2=берсерк
        self.phase_hp_thresholds = [1.0, 0.66, 0.33]  # переход на 66% и 33% HP
        self.phase_change_time = 0
        
        # Атака
        self.shoot_delay = 1200
        self.last_shot = 0
        self.attack_type = 0  # 0=волна, 1=спираль, 2=боковая, 3=прямая
        self.attack_sequence = 0  # счётчик атак для чередования
        self.attack_cooldown = 0
        
        # Движение и тактика
        self.move_pattern = 0  # 0=преследование, 1=отступление, 2=боковое движение
        self.pattern_timer = 0
        self.pattern_duration = 180  # кадров на один паттерн
        self.last_player_x = 0
        self.dodge_cooldown = 0
        self.jump_charge = 0

    def update(self, player, tiles, projectiles):
        now = pygame.time.get_ticks()
        
        # === ФАЗЫ ===
        hp_ratio = self.hp / self.max_hp
        new_phase = 0
        if hp_ratio <= 0.33:
            new_phase = 2  # берсерк (очень опасен)
        elif hp_ratio <= 0.66:
            new_phase = 1  # агрессивный
        
        if new_phase != self.phase:
            self.phase = new_phase
            self.phase_change_time = now
            self.attack_sequence = 0
        
        # === ГРАВИТАЦИЯ И КОЛЛИЗИИ ===
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
        
        # === ТАКТИКА ДВИЖЕНИЯ ===
        dx_to_player = player.hitbox.centerx - self.hitbox.centerx
        dy_to_player = player.hitbox.centery - self.hitbox.centery
        dist_to_player = abs(dx_to_player)
        
        self.pattern_timer += 1
        if self.pattern_timer >= self.pattern_duration:
            self.pattern_timer = 0
            # выбираем паттерн в зависимости от фазы
            if self.phase == 0:
                self.move_pattern = random.choice([0, 1])  # преследование или отступление
            elif self.phase == 1:
                self.move_pattern = random.choice([0, 2])  # преследование или боковое
            else:  # phase 2 (берсерк)
                self.move_pattern = 0  # почти всегда преследуем
        
        # применяем паттерн движения
        move_speed = 1.5 + (self.phase * 0.4)  # скорость зависит от фазы
        
        if self.move_pattern == 0:
            # преследование: идём к игроку
            if dist_to_player > 80:
                move_dir = 1 if dx_to_player > 0 else -1
                self.hitbox.x += int(move_dir * move_speed)
                self.facing_right = move_dir > 0
        
        elif self.move_pattern == 1:
            # отступление: отходим назад (если близко)
            if dist_to_player < 200:
                move_dir = 1 if dx_to_player > 0 else -1
                self.hitbox.x -= int(move_dir * move_speed * 0.8)
                self.facing_right = move_dir > 0
        
        elif self.move_pattern == 2:
            # боковое движение: ходим взад-вперёд сбоку от игрока
            side_dir = 1 if self.phase_change_time % 400 < 200 else -1
            self.hitbox.x += int(side_dir * move_speed * 0.6)
            self.facing_right = side_dir > 0
        
        # избегаем застревания в стенах
        for t in tiles:
            if isinstance(t, pygame.Rect) and t.colliderect(self.hitbox):
                if dx_to_player > 0:
                    self.hitbox.right = t.left
                else:
                    self.hitbox.left = t.right
        
        # умный прыжок (на игрока или уход от атаки)
        if self.on_ground:
            should_jump = False
            if self.phase >= 1 and dist_to_player < 300:
                # в боевых фазах часто прыгаем для манёвра
                if random.random() < (0.015 * (self.phase + 1)):
                    should_jump = True
            elif self.phase == 0 and random.random() < 0.008:
                should_jump = True
            
            if should_jump:
                jump_power = -16 if self.phase == 2 else -15
                self.vel_y = jump_power
                self.on_ground = False
        
        # === АТАКА (фаза-зависимая) ===
        shoot_delay_base = 1400 - (self.phase * 200)  # чем выше фаза, тем чаще стреляет
        
        if now - self.last_shot >= shoot_delay_base:
            self.attack_sequence = (self.attack_sequence + 1) % (3 + self.phase)
            
            px = self.hitbox.centerx
            py = self.hitbox.centery
            
            if self.phase == 0:
                # обычная фаза: чередуем волну и прямую атаку
                if self.attack_sequence % 2 == 0:
                    self._shoot_wave(px, py, player, projectiles)
                else:
                    self._shoot_direct(px, py, player, projectiles)
            
            elif self.phase == 1:
                # агрессивная фаза: чередуем волну, прямую и боковую
                if self.attack_sequence % 3 == 0:
                    self._shoot_wave(px, py, player, projectiles)
                elif self.attack_sequence % 3 == 1:
                    self._shoot_direct(px, py, player, projectiles)
                else:
                    self._shoot_sides(px, py, projectiles)
            
            else:  # phase 2
                # берсерк: комбо атак — волна + спираль + прямая
                if self.attack_sequence % 4 == 0:
                    self._shoot_wave(px, py, player, projectiles)
                elif self.attack_sequence % 4 == 1:
                    self._shoot_spiral(px, py, projectiles)
                elif self.attack_sequence % 4 == 2:
                    self._shoot_direct(px, py, player, projectiles)
                else:
                    self._shoot_sides(px, py, projectiles)
            
            self.last_shot = now
        
        # визуал
        self.image = self.sprites.get("idle1", self.image)
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)

    def _shoot_direct(self, px, py, player, projectiles):
        """Прямая атака в сторону игрока"""
        vec = pygame.Vector2(player.hitbox.centerx - px, player.hitbox.centery - py)
        if vec.length() == 0:
            vec = pygame.Vector2(1, 0)
        vec = vec.normalize()
        speed = 6 + self.phase
        proj = Projectile(px, py, vec.x * speed, vec.y * speed, 
                         color=(255, 100 + self.phase * 50, 20), size=8 * 4)
        projectiles.append(proj)

    def _shoot_wave(self, px, py, player, projectiles):
        """Волна снарядов"""
        num_proj = 5 + self.phase * 2
        for i in range(num_proj):
            angle = (i / num_proj) * 2 * math.pi
            vx = math.cos(angle) * (5 + self.phase * 0.5)
            vy = math.sin(angle) * (5 + self.phase * 0.5)
            proj = Projectile(px, py, vx, vy, color=(200, 80, 200), size=12)
            projectiles.append(proj)

    def _shoot_spiral(self, px, py, projectiles):
        """Спиральная атака"""
        num_proj = 8
        time_offset = pygame.time.get_ticks() / 100.0
        for i in range(num_proj):
            angle = (i / num_proj) * 2 * math.pi + time_offset
            vx = math.cos(angle) * 5.5
            vy = math.sin(angle) * 5.5
            proj = Projectile(px, py, vx, vy, color=(100, 255, 200), size=14)
            projectiles.append(proj)

    def _shoot_sides(self, px, py, projectiles):
        """Боковая атака (слева и справа)"""
        for side in [-1, 1]:
            vx = side * 7
            vy = -2
            proj = Projectile(px, py, vx, vy, color=(255, 200, 100), size=16)
            projectiles.append(proj)

    def draw(self, surf, offset):
        draw_pos = (self.rect.x + offset[0], self.rect.y + offset[1])
        surf.blit(self.image, draw_pos)
        
        # полоска HP
        bar_width = self.rect.width
        bar_height = 12
        bar_x = draw_pos[0]
        bar_y = draw_pos[1] - 25
        
        # фон
        pygame.draw.rect(surf, (80, 20, 20), (bar_x, bar_y, bar_width, bar_height))
        
        # цвет в зависимости от фазы
        if self.phase == 0:
            color = (0, 200, 0)
        elif self.phase == 1:
            color = (255, 150, 0)
        else:
            color = (255, 0, 0)
        
        hp_ratio = max(0, self.hp / self.max_hp)
        pygame.draw.rect(surf, color, (bar_x, bar_y, bar_width * hp_ratio, bar_height))
        pygame.draw.rect(surf, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 2)
        
        # фаза-индикатор
        phase_text = pygame.font.Font(None, 20).render(
            f"Phase {self.phase + 1}", True, color
        )
        surf.blit(phase_text, (bar_x, bar_y - 22))

    def damage(self, amount):
        self.hp -= amount
        return self.hp <= 0


class Bacteria:
    def __init__(self, x, y, sprites, hp=None):
        self.hitbox = pygame.Rect(int(x), int(y), TILE_SIZE, TILE_SIZE)
        self.sprites = sprites
        self.image = self.sprites.get("idle", pygame.Surface((TILE_SIZE, TILE_SIZE)))
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)
        self.speed = 1.6
        self.max_hp = int(hp) if hp is not None else 3
        self.hp = self.max_hp
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
    def __init__(self, x, y, sprites, hp=None):
        self.hitbox = pygame.Rect(int(x), int(y), TILE_SIZE, TILE_SIZE)
        self.sprites = sprites
        self.image = self.sprites.get("idle", pygame.Surface((TILE_SIZE, TILE_SIZE)))
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)
        self.max_hp = int(hp) if hp is not None else 2
        self.hp = self.max_hp
        self.shoot_delay = 800
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