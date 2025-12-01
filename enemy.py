import pygame
from constants import TILE_SIZE,CHAR_SIZE

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
        # позиционируем по сетке, хитбокс размером TILE_SIZE
        self.hitbox = pygame.Rect(int(x), int(y), TILE_SIZE, TILE_SIZE)
        self.sprites = sprites  # словарь спрайтов {"idle", "walk1", "walk2"}
        self.image = self.sprites.get("idle", pygame.Surface((TILE_SIZE, TILE_SIZE)))
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)
        self.speed = 1.6
        self.hp = 3
        self.shoot_delay = 1200  # мс
        self.last_shot = 0
        self.facing_right = True
        self.anim_frame = 0  # для переключения walk1/walk2

    def update(self, player, tiles, projectiles):
        now = pygame.time.get_ticks()
        # простая дистанция агро
        dx = (player.hitbox.centerx - self.hitbox.centerx)
        dy = abs(player.hitbox.centery - self.hitbox.centery)
        
        current_img = self.sprites.get("idle")
        
        if abs(dx) < 800 and dy < 128:
            # движение по X к игроку
            vx = self.speed if dx > 0 else -self.speed
            self.hitbox.x += int(vx)
            self.facing_right = vx > 0
            
            # простая горизонтальная коллизия с tiles
            for t in tiles:
                if isinstance(t, pygame.Rect) and t.colliderect(self.hitbox):
                    if vx > 0:
                        self.hitbox.right = t.left
                    elif vx < 0:
                        self.hitbox.left = t.right
            
            # анимация ходьбы (переключаем walk1/walk2)
            self.anim_frame = (pygame.time.get_ticks() // 200) % 2
            current_img = self.sprites.get("walk1" if self.anim_frame == 0 else "walk2", self.sprites.get("idle"))
            
            # стрельба по горизонтали к игроку
            if now - self.last_shot >= self.shoot_delay:
                dir_sign = 1 if dx > 0 else -1
                px = self.hitbox.centerx + dir_sign * (TILE_SIZE//2 + 4)
                py = self.hitbox.centery - 4
                proj = Projectile(px, py, dir_sign * 0.35, 0, color=(0,220,0))
                projectiles.append(proj)
                self.last_shot = now

        # отражаем спрайт, если враг смотрит влево
        if not self.facing_right:
            current_img = pygame.transform.flip(current_img, True, False)
        
        self.image = current_img
        self.rect = self.image.get_rect(topleft=self.hitbox.topleft)

    def draw(self, surf, offset):
        draw_pos = (self.rect.x + offset[0], self.rect.y + offset[1])
        surf.blit(self.image, draw_pos)

    def damage(self, amount):
        self.hp -= amount
        return self.hp <= 0  # True если убит