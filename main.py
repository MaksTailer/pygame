import pygame
import sys
import pytmx

pygame.init()

# Настройки окна
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 64
CHAR_SIZE = 128
FPS = 60

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Map from Tiled")
clock = pygame.time.Clock()

# === Загрузка ассетов ===
background = pygame.image.load("assets/background.png").convert()
background = pygame.transform.scale(background, (SCREEN_WIDTH, SCREEN_HEIGHT))
character_sheet = pygame.image.load("assets/characters.png").convert_alpha()
ground = pygame.image.load("assets/ground.png").convert_alpha()

# === Функция для нарезки спрайтов ===
def get_sprite(sheet, x, y, w, h):
    sprite = pygame.Surface((w, h), pygame.SRCALPHA)
    sprite.blit(sheet, (0, 0), (x * w, y * h, w, h))
    return sprite

# === Спрайты персонажа ===
player_sprites = {
    "walk1": get_sprite(character_sheet, 0, 0, CHAR_SIZE, CHAR_SIZE),
    "walk2": get_sprite(character_sheet, 0, 1, CHAR_SIZE, CHAR_SIZE),
    "jump": get_sprite(character_sheet, 0, 3, CHAR_SIZE, CHAR_SIZE),
    "idle": get_sprite(character_sheet, 0, 5, CHAR_SIZE, CHAR_SIZE)
}

tile_heart = get_sprite(ground, 13, 17, TILE_SIZE, TILE_SIZE)

# === Игровые классы ===
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = player_sprites["idle"]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_y = 0
        self.on_ground = False
        self.hp = 10
        self.facing_right = True
        self.last_hit_time = 0
        self.invincible_delay = 1000

    def update(self, tiles, traps):
        keys = pygame.key.get_pressed()
        dx = 0

        if keys[pygame.K_LEFT]:
            dx = -5
            self.image = player_sprites["walk1"] if pygame.time.get_ticks() // 200 % 2 == 0 else player_sprites["walk2"]
            self.facing_right = False
        elif keys[pygame.K_RIGHT]:
            dx = 5
            self.image = player_sprites["walk1"] if pygame.time.get_ticks() // 200 % 2 == 0 else player_sprites["walk2"]
            self.facing_right = True
        else:
            self.image = player_sprites["idle"]

        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = -15
            self.on_ground = False
            self.image = player_sprites["jump"]

        # Гравитация
        self.vel_y += 1
        if self.vel_y > 10:
            self.vel_y = 10
        dy = self.vel_y

        # Проверка столкновений с землёй
        self.on_ground = False
        for tile in tiles:
            if tile.colliderect(self.rect.x, self.rect.y + dy, self.rect.width, self.rect.height):
                if self.vel_y > 0:
                    dy = tile.top - self.rect.bottom
                    self.vel_y = 0
                    self.on_ground = True
            if tile.colliderect(self.rect.x + dx, self.rect.y, self.rect.width, self.rect.height):
                dx = 0

        # Проверка ловушек
        now = pygame.time.get_ticks()
        for trap in traps:
            trap_collision = trap.inflate(-40, -40)
            if trap_collision.colliderect(self.rect):
                if now - self.last_hit_time > self.invincible_delay:
                    self.hp -= 1
                    self.last_hit_time = now
                    if self.hp <= 0:
                        restart_game()

        self.rect.x += dx
        self.rect.y += dy

        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)

class Camera:
    def __init__(self):
        self.offset_x = 0
        self.offset_y = 0

    def update(self, player):
        # Следим за игроком по X и Y
        self.offset_x = -(player.rect.x - SCREEN_WIDTH // 2)
        self.offset_y = -(player.rect.y - SCREEN_HEIGHT // 2)


# === Перезапуск ===
def restart_game():
    main()

# === Загрузка карты из Tiled ===
def load_map(filename):
    tmx_data = pytmx.load_pygame(filename, pixelalpha=True)
    tiles = []
    traps = []

    # Слои
    for layer in tmx_data.visible_layers:
        if isinstance(layer, pytmx.TiledTileLayer):
            for x, y, gid in layer:
                tile = tmx_data.get_tile_image_by_gid(gid)
                if tile:
                    world_x = x * tmx_data.tilewidth
                    world_y = y * tmx_data.tileheight

                    if layer.name.lower() == "ground":
                        tiles.append(pygame.Rect(world_x, world_y, TILE_SIZE, TILE_SIZE))
                    elif layer.name.lower() == "traps":
                        traps.append(pygame.Rect(world_x, world_y, TILE_SIZE, TILE_SIZE))
    return tmx_data, tiles, traps

# === Основная функция ===
def main():
    tmx_data, tiles, traps = load_map("assets/2map.tmx")

    player = Player(100, 300)
    camera = Camera()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        player.update(tiles, traps)
        camera.update(player)

        # Отрисовка фона
        screen.blit(background, (0, 0))

        # Отрисовка тайлов
        for layer in tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        screen.blit(
                            tile,
                            (x * TILE_SIZE + camera.offset_x, y * TILE_SIZE + camera.offset_y)
                        )


        # Игрок
        screen.blit(player.image, (player.rect.x + camera.offset_x, player.rect.y + camera.offset_y))


        # Жизни
        for i in range(player.hp):
            screen.blit(tile_heart, (10 + i * 40, 10))

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
