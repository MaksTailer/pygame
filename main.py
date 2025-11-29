import pygame
import sys
import pytmx
import random
from constants import *
from platform import *
from camera import *
from player import *
from map_loader import load_map

pygame.init()

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


# === Перезапуск ===
def restart_game():
    main()

# === Основная функция ===
# ...existing code...
def main():
    tmx_data, tiles, traps, platforms = load_map("assets/2map.tmx")

    # --- Сбор прямоугольников воды и зыбучих песков (одним проходом) ---
    water_layer = None
    water_rects = []
    quicksand_layer = None
    quicksand_rects = []
    for layer in tmx_data.visible_layers:
        if isinstance(layer, pytmx.TiledTileLayer):
            name = getattr(layer, "name", "")
            if name == "Water":
                water_layer = layer
                for x, y, gid in layer:
                    if gid != 0:
                        water_rects.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            elif name == "Quicksand":
                quicksand_layer = layer
                for x, y, gid in layer:
                    if gid != 0:
                        quicksand_rects.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

    map_pixel_height = tmx_data.height * tmx_data.tileheight
    player = Player(100, 300, map_pixel_height, player_sprites)
    camera = Camera()

    print("TILE_SIZE:", TILE_SIZE, "CHAR_SIZE:", CHAR_SIZE, "player.image.size:", player.image.get_size(), "player.rect:", player.rect.size)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 1. Обновляем платформы
        for platform in platforms:
            platform.update()

        # 2. Формируем поверхность для коллизий (тайлы + верх платформ)
        all_tiles = tiles.copy()
        for platform in platforms:
            top_surface = pygame.Rect(platform.rect.x, platform.rect.y - 1, platform.rect.width, 2)
            all_tiles.append(top_surface)

        # Добавляем quicksand_rects в список коллизий — чтобы песок был "землёй"
        if quicksand_rects:
            all_tiles.extend(quicksand_rects)

        # 3. Вычисляем, в воде/на песках ли хитбокс игрока (до обновления)
        in_water = any(w.colliderect(player.hitbox) for w in water_rects) if water_rects else False
        in_quicksand = any(q.colliderect(player.hitbox) for q in quicksand_rects) if quicksand_rects else False

        # 4. Обновляем игрока с флагами среды
        player.update(all_tiles, traps, in_water, in_quicksand)

        # 5. Применяем движение платформ к игроку (по hitbox)
        for platform in platforms:
            on_platform = (
                player.hitbox.bottom >= platform.rect.top - 5 and
                player.hitbox.bottom <= platform.rect.top + 15 and
                player.hitbox.left < platform.rect.right and
                player.hitbox.right > platform.rect.left and
                player.vel_y >= 0
            )
            if on_platform:
                player.hitbox.x += int(platform.last_move.x)
                player.hitbox.y += int(platform.last_move.y)
                player.rect = player.image.get_rect(midbottom=player.hitbox.midbottom)

        camera.update(player)

        # === ОТРИСОВКА ===
        screen.blit(background, (0, 0))

        # Отрисовка тайлов
        for layer in tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        screen.blit(tile, (x * TILE_SIZE + camera.offset_x, y * TILE_SIZE + camera.offset_y))

        # Платформы
        for platform in platforms:
            platform.draw(screen, (camera.offset_x, camera.offset_y))

        # Игрок (рисуем один раз)
        screen.blit(player.image, (player.rect.x + camera.offset_x, player.rect.y + camera.offset_y))

        # Контур хитбокса игрока для отладки
        pr = player.hitbox.copy()
        pr.x += camera.offset_x; pr.y += camera.offset_y
        pygame.draw.rect(screen, (255, 0, 0), pr, 2)

        # Слой воды рисуем поверх игрока (если есть)
        if water_layer is not None:
            for x, y, gid in water_layer:
                tile = tmx_data.get_tile_image_by_gid(gid)
                if tile:
                    screen.blit(tile, (x * TILE_SIZE + camera.offset_x, y * TILE_SIZE + camera.offset_y))

        # Слой зыбучих песков (опционально можно рисовать поверх или под игроком)
        if quicksand_layer is not None:
            for x, y, gid in quicksand_layer:
                tile = tmx_data.get_tile_image_by_gid(gid)
                if tile:
                    screen.blit(tile, (x * TILE_SIZE + camera.offset_x, y * TILE_SIZE + camera.offset_y))

        # Жизни
        for i in range(player.hp):
            screen.blit(tile_heart, (10 + i * 40, 10))

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
