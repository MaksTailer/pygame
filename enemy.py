import pygame
from constants import TILE_SIZE, CHAR_SIZE

class Projectile:
    def __init__(self, x, y, vx, vy, color=(0,255,0), life=3000):
        self.pos = pygame.Vector2(x, y)
        self.v = pygame.Vector2(vx, vy)
        self.rect = pygame.Rect(int(x), int(y), 8, 8)
        self.color = color
        self.spawn_time = pygame.time.get_ticks()
        self.life = life

    def update(self, dt):
        self.pos += self.v * dt
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))
        return pygame.time.get_ticks() - self.spawn_time > self.life

    def draw(self, surf, offset):
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
        self.shoot_delay = 800  # мс (чаще стреляет, чем бактерия)
        self.last_shot = 0
        self.facing_right = True
        self.anim_frame = 0
        
        # Полёт (синусоида)
        self.flight_time = 0
        self.flight_speed = 2  # скорость горизонтального движения
        self.flight_amplitude = 20  # амплитуда синусоиды
        self.flight_frequency = 0.05  # частота колебаний
        self.start_x = x
        self.start_y = y

    def update(self, player, tiles, projectiles):
        import math
        now = pygame.time.get_ticks()
        
        # Отслеживание расстояния до игрока
        dx_to_player = (player.hitbox.centerx - self.hitbox.centerx)
        dy_to_player = (player.hitbox.centery - self.hitbox.centery)
        dist_to_player = math.sqrt(dx_to_player**2 + dy_to_player**2)
        
        # Полёт по синусоиде (горизонтальное движение + волна по Y)
        self.flight_time += 1
        move_x = self.flight_speed
        move_y = self.flight_amplitude * math.sin(self.flight_time * self.flight_frequency)
        
        self.hitbox.x += int(move_x)
        self.hitbox.y += int(move_y)
        
        # Разворот при столкновении со стеной
        for t in tiles:
            if isinstance(t, pygame.Rect) and t.colliderect(self.hitbox):
                self.flight_speed *= -1  # меняем направление
                self.hitbox.x -= int(move_x) * 2  # отскок назад
                break
        
        # Агрессия: если игрок близко и выше врага — активное преследование
        is_aggro = dist_to_player < 400 and dy_to_player < 300
        
        current_img = self.sprites.get("idle")
        
        # Стрельба хаотично или при агро
        if is_aggro:
            # при агро стреляем часто вниз
            shoot_delay = 400
        else:
            # иначе редко и хаотично
            shoot_delay = 1200
        
        if now - self.last_shot >= shoot_delay:
            # Стреляем вниз (или с небольшим разбросом в стороны при агро)
            if is_aggro and abs(dx_to_player) < 200:
                # прямо вниз если игрок под нами
                vx = 0
            else:
                # хаотично вниз в стороны
                import random
                vx = random.uniform(-0.1, 0.1)
            
            px = self.hitbox.centerx
            py = self.hitbox.centery
            proj = Projectile(px, py, vx, 0.25, color=(100, 255, 100))  # светло-зелёный
            projectiles.append(proj)
            self.last_shot = now
        
        # анимация (переключение спрайтов)
        self.anim_frame = (pygame.time.get_ticks() // 200) % 2
        current_img = self.sprites.get("walk1" if self.anim_frame == 0 else "walk2", self.sprites.get("idle"))
        
        # отражаем спрайт если летит влево
        if self.flight_speed < 0:
            current_img = pygame.transform.flip(current_img, True, False)
            self.facing_right = False
        else:
            self.facing_right = True
        
        self.image = current_img
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)

    def draw(self, surf, offset):
        draw_pos = (self.rect.x + offset[0], self.rect.y + offset[1])
        surf.blit(self.image, draw_pos)

    def damage(self, amount):
        self.hp -= amount
        return self.hp <= 0