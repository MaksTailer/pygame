import pygame
from constants import *


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, map_height, sprites):
        super().__init__()
        self.sprites = sprites
        self.image = self.sprites["idle"]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.hitbox = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
        self.vel_y = 0
        self.on_ground = False
        self.hp = 10
        self.facing_right = True
        self.last_hit_time = 0
        self.invincible_delay = 1000
        self.map_height = map_height
        self.fall_start_time = None

        # Счётчики коллектиблов
        self.coins = 0
        self.diamonds = 0

        # Shift-способность (защита)
        self.shield_active = False
        self.shield_start_time = 0
        self.shield_duration = 3000  # 3 сек неуязвимости
        self.shield_cooldown = 20000  # 20 сек перезарядка
        self.shield_last_used = -self.shield_cooldown  # чтобы можно было активировать сразу

        self.mana = 1.0 if self.diamonds > 0 else 0.0
        self.mana_duration_ms = 10_000  # 10 секунд полного расхода
        self.mana_drain_per_ms = 1.0 / self.mana_duration_ms
        self.last_mana_tick = pygame.time.get_ticks()

        # Параметры оружия/снарядов (по умолчанию)
        self.projectile_damage = 1
        self.proj_img = None  # при подборе ammo устано


    def update(self, tiles, traps, in_water=False, in_quicksand=False):
        import pygame
        keys = pygame.key.get_pressed()
        dx = 0

        # базовая скорость
        base_speed = 5
        if in_water:
            base_speed = max(1, int(base_speed * 0.5))
        elif in_quicksand:
            base_speed = max(1, int(base_speed * 0.25))

        # ==== МАНА / ЩИТ ====
        now = pygame.time.get_ticks()
        elapsed = max(0, now - getattr(self, "last_mana_tick", now))
        self.last_mana_tick = now

        shift_pressed = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        # Если держим Shift и есть манa — включаем щит и расходуем
        if shift_pressed and self.mana > 0:
            self.shield_active = True
            # тянем ману
            self.mana -= elapsed * self.mana_drain_per_ms
            if self.mana <= 0:
                # манa закончилась
                self.mana = 0.0
                self.shield_active = False
                # если есть алмазы — потребляем 1 и восстанавливаем ману автоматически
                if self.diamonds > 0:
                    self.diamonds -= 1
                    self.mana = 1.0
                    # сразу начинаем тянуть из вновь заполненной полоски
                    # уменьшение по оставшемуся elapsed (не критично)
                    self.mana -= 0  # (можно учесть остаток, но опустим)
        else:
            # если Shift отпущен — выключаем щит
            if not shift_pressed:
                self.shield_active = False
            # если манa = 0 и есть алмазы — автоматически заряжаем (один алмаз = одна полная полоса)
            if self.mana <= 0 and self.diamonds > 0:
                self.diamonds -= 1
                self.mana = 1.0

        # Ограничения и коректность
        if self.mana < 0:
            self.mana = 0.0
        if self.mana > 1:
            self.mana = 1.0

        # анимация/движение
        current_img = self.sprites["idle"]
        if keys[pygame.K_a]:
            print("AAAAAAA")
            dx = -base_speed
            current_img = self.sprites["walk1"] if pygame.time.get_ticks() // 200 % 2 == 0 else self.sprites["walk2"]
            self.facing_right = False
        elif keys[pygame.K_d]:
            print("DDDDDDdd")
            dx = base_speed
            current_img = self.sprites["walk1"] if pygame.time.get_ticks() // 200 % 2 == 0 else self.sprites["walk2"]
            self.facing_right = True
        elif self.shield_active:
            current_img = self.sprites["shift"]

        # прыжок (запрещаем на зыбучих песках)
        if keys[pygame.K_SPACE] and self.on_ground and not in_quicksand:
            self.vel_y = -15
            self.on_ground = False
            current_img = self.sprites.get("jump", current_img)

        # гравитация
        self.vel_y += 1
        if self.vel_y > 10:
            self.vel_y = 10
        dy = self.vel_y

        # горизонтальная коллизия (по hitbox)
        future_x = self.hitbox.copy()
        future_x.x += dx
        for tile in tiles:
            if isinstance(tile, pygame.Rect) and tile.colliderect(future_x):
                if dx > 0:
                    self.hitbox.right = tile.left
                elif dx < 0:
                    self.hitbox.left = tile.right
                dx = 0
                break

        # вертикальная коллизия (по hitbox)
        future_y = self.hitbox.copy()
        future_y.y += dy
        collided_vert = False
        for tile in tiles:
            if isinstance(tile, pygame.Rect) and tile.colliderect(future_y):
                collided_vert = True
                if dy > 0:
                    # падаем вниз — ставим на поверхность и считаем на земле
                    self.hitbox.bottom = tile.top
                    self.vel_y = 0
                    self.on_ground = True
                elif dy < 0:
                    self.hitbox.top = tile.bottom
                    self.vel_y = 0
                dy = 0
                break

        # применяем движение
        self.hitbox.x += dx
        self.hitbox.y += dy

        # Если не было вертикального столкновения — проверяем опору точечно (под центром ступни).
        # Это гарантирует, что при стоянии на краю (частичная опора) будет корректно обнаружено наличие/отсутствие земли.
        on_ground_precise = False
        # небольшая область под ногами
        foot_rect = pygame.Rect(self.hitbox.left + 2, self.hitbox.bottom, max(1, self.hitbox.width - 4), 3)
        for tile in tiles:
            if not isinstance(tile, pygame.Rect):
                continue
            # 1) прямое пересечение небольшой области под ногами
            if tile.colliderect(foot_rect):
                on_ground_precise = True
                break
            # 2) дополнительно проверяем точки по краям — чтобы не потерять опору на краю тайла
            if tile.collidepoint((self.hitbox.left + 2, self.hitbox.bottom + 1)) or \
               tile.collidepoint((self.hitbox.right - 2, self.hitbox.bottom + 1)) or \
               tile.collidepoint((self.hitbox.centerx, self.hitbox.bottom + 1)):
                on_ground_precise = True
                break
        self.on_ground = on_ground_precise

        # ловушки (по hitbox)
        now = pygame.time.get_ticks()
        for trap in traps:
            trect = trap if isinstance(trap, pygame.Rect) else getattr(trap, "rect", None)
            if isinstance(trect, pygame.Rect):
                if trect.colliderect(self.hitbox):
                    if now - self.last_hit_time > self.invincible_delay:
                        self.hp -= 1
                        #HIT_SOUND.play()
                        self.last_hit_time = now
                        if self.hp <= 0:
                            try:
                                restart_game()
                            except NameError:
                                pygame.event.post(pygame.event.Event(pygame.QUIT))

        # падение за карту
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

        # синхронизация визуала с хитбоксом
        if not self.facing_right:
            self.image = pygame.transform.flip(current_img, True, False)
        else:
            self.image = current_img
        self.rect = self.image.get_rect(midbottom=self.hitbox.midbottom)
# ...existing code...