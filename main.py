import pygame
import sys
import pytmx
import random
from constants import *
from platform import *
from camera import *
from player import *
from map_loader import load_map
from enemy import Bacteria, Virus

pygame.init()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Map from Tiled")
clock = pygame.time.Clock()

# === Загрузка ассетов ===
background = pygame.image.load("assets/background-1.png").convert()
background = pygame.transform.scale(background, (SCREEN_WIDTH, SCREEN_HEIGHT))
character_sheet = pygame.image.load("assets/characters.png").convert_alpha()
ground = pygame.image.load("assets/ground.png").convert_alpha()
enemy_sheet = pygame.image.load("assets/enemies.png").convert_alpha()

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

    
    # Нарезаем спрайты бактерии из enemies.png
    # Предполагаем: левый верхний (0,0) — idle, снизу (0, CHAR_SIZE) и (CHAR_SIZE, CHAR_SIZE) — walk1, walk2
tile_heart = get_sprite(ground, 13, 17, TILE_SIZE, TILE_SIZE)


# === Перезапуск ===
def restart_game():
    main()

# === Основная функция ===
def main(current_level=0):
    # Загружаем текущий уровень
    if current_level >= len(LEVELS):
        current_level = 0  # Циклим на первый уровень (или финальный экран)
    
    level_file = LEVELS[current_level]
    tmx_data, tiles, traps, platforms, enemy_objs = load_map(level_file)


    # --- Сбор портала выхода ---
    exit_portal = None
    for layer in tmx_data.visible_layers:
        if isinstance(layer, pytmx.TiledObjectGroup):
            if layer.name.lower() == "exit":  # Ищем слой с именем "Exit"
                for obj in layer:
                    # Объект может быть с gid (спрайт) или без, берём его координаты
                    exit_portal = pygame.Rect(
                        int(obj.x), 
                        int(obj.y), 
                        int(obj.width) if obj.width else TILE_SIZE, 
                        int(obj.height) if obj.height else TILE_SIZE
                    )
                    print(f"Портал найден на уровне {current_level + 1}: {exit_portal}")
                    break
            if exit_portal:
                break

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
            elif name in ("Quicksand", "Sand"):
                quicksand_layer = layer
                for x, y, gid in layer:
                    if gid != 0:
                        quicksand_rects.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

    map_pixel_height = tmx_data.height * tmx_data.tileheight
    player = Player(100, 300, map_pixel_height, player_sprites)
    camera = Camera()

    
    bacteria_sprites = {
    "idle": get_sprite(enemy_sheet, 0, 0, TILE_SIZE, TILE_SIZE),      # (0, 0)
    "walk1": get_sprite(enemy_sheet, 0, 1, TILE_SIZE, TILE_SIZE),      # (0, 128) в пикселях
    "walk2": get_sprite(enemy_sheet, 0, 2, TILE_SIZE, TILE_SIZE),
    }

    virus_sprites = {
    "idle": get_sprite(enemy_sheet, 3, 6, TILE_SIZE, TILE_SIZE),      # (0, 0)
    "walk1": get_sprite(enemy_sheet, 3, 6, TILE_SIZE, TILE_SIZE),      # (0, 128) в пикселях
    "walk2": get_sprite(enemy_sheet, 7, 3, TILE_SIZE, TILE_SIZE),
    }
        
    enemies = []
    for eo in enemy_objs:
        if eo.get("name","").lower() == "bacteria":
            ex = eo["x"]
            ey = eo["y"] - TILE_SIZE
            enemies.append(Bacteria(ex, ey, bacteria_sprites))
        elif eo.get("name","").lower() == "virus":
            ex = eo["x"]
            ey = eo["y"] - TILE_SIZE
            enemies.append(Virus(ex, ey, virus_sprites))
    
    print(f"Создано врагов: {len(enemies)} (бактерий: {sum(1 for e in enemies if isinstance(e, Bacteria))}, вирусов: {sum(1 for e in enemies if isinstance(e, Virus))})")
    print(f"Объекты врагов из карты: {enemy_objs}")

    # список снарядов (врагов)
    enemy_projectiles = []

    print(f"Уровень {current_level + 1}/{len(LEVELS)}")

    running = True
    level_complete = False
    
    while running and not level_complete:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 1. Обновляем платформы
        for platform in platforms:
            platform.update()

        # 2. Формируем поверхность для коллизий
        all_tiles = tiles.copy()
        for platform in platforms:
            top_surface = pygame.Rect(platform.rect.x, platform.rect.y - 1, platform.rect.width, 2)
            all_tiles.append(top_surface)

        if quicksand_rects:
            all_tiles.extend(quicksand_rects)

        # 3. Вычисляем состояние (вода/пески)
        feet = pygame.Rect(player.hitbox.x, player.hitbox.bottom, player.hitbox.width, 2)
        in_water = any(w.colliderect(feet) for w in water_rects) if water_rects else False
        in_quicksand = any(q.colliderect(feet) for q in quicksand_rects) if quicksand_rects else False
        
        player.update(all_tiles, traps, in_water, in_quicksand)

        # Обновляем врагов
        for e in enemies:
            e.update(player, all_tiles, enemy_projectiles)
            # контакт враг - игрок
            if e.hitbox.colliderect(player.hitbox):
                now = pygame.time.get_ticks()
                if now - player.last_hit_time > player.invincible_delay:
                    player.hp -= 1
                    player.last_hit_time = now
                    player.vel_y = -8  # отскок вверх

        # Обновляем снаряды врагов
        dt = 1
        for proj in enemy_projectiles[:]:
            dead = proj.update(dt)
            if proj.rect.colliderect(player.hitbox):
                now = pygame.time.get_ticks()
                if now - player.last_hit_time > player.invincible_delay:
                    player.hp -= 1
                    player.last_hit_time = now
                try:
                    enemy_projectiles.remove(proj)
                except ValueError:
                    pass
            elif dead:
                try:
                    enemy_projectiles.remove(proj)
                except ValueError:
                    pass

        # 4. Применяем движение платформ
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

        # 5. Проверяем выход из уровня
        if exit_portal and player.hitbox.colliderect(exit_portal):
            level_complete = True
            print(f"Уровень {current_level + 1} завершён! Переход на уровень {current_level + 2}...")

        # 6. Проверяем смерть
        if player.hp <= 0:
            print("Игрок погиб! Перезагрузка уровня 1...")
            main(0)  # Возвращаемся на первый уровень
            return

        camera.update(player)

        # === ОТРИСОВКА ===
        screen.blit(background, (0, 0))

        for layer in tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        screen.blit(tile, (x * TILE_SIZE + camera.offset_x, y * TILE_SIZE + camera.offset_y))

        for platform in platforms:
            platform.draw(screen, (camera.offset_x, camera.offset_y))



        screen.blit(player.image, (player.rect.x + camera.offset_x, player.rect.y + camera.offset_y))
        for e in enemies:
            e.draw(screen, (camera.offset_x, camera.offset_y))

        # Рисуем снаряды врагов
        for proj in enemy_projectiles:
            proj.draw(screen, (camera.offset_x, camera.offset_y))




        for layer in tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledObjectGroup):
                for obj in layer:
                    gid = getattr(obj, "gid", None)
                    if gid:
                        # Пропускаем отрисовку tile-объектов платформ
                        layer_name = (getattr(layer, "name", "") or "").lower()
                        obj_name = (getattr(obj, "name", "") or "").lower()
                        if layer_name in ("movingplatform", "movingplatforms", "platforms") or obj_name == "movingplatform":
                            continue

                        # Пропускаем tile-объекты с именем "exit" (портал рисуется отдельно через зелёный контур)
                        if obj_name == "exit":
                            continue

                        img = tmx_data.get_tile_image_by_gid(gid)
                        if img:
                            # выравниваем позицию по сетке тайлов
                            tile_x = int(obj.x) // TILE_SIZE
                            tile_y = int(obj.y) // TILE_SIZE
                            draw_x = tile_x * TILE_SIZE + camera.offset_x
                            draw_y = tile_y * TILE_SIZE + camera.offset_y + TILE_SIZE - img.get_height()
                            screen.blit(img, (draw_x, draw_y))


        # Слой воды (рисовать поверх игрока)
        if water_layer is not None:
            for x, y, gid in water_layer:
                tile = tmx_data.get_tile_image_by_gid(gid)
                if tile:
                    screen.blit(tile, (x * TILE_SIZE + camera.offset_x, y * TILE_SIZE + camera.offset_y))

        # Слой песков (если хотите видеть их поверх/под игроком)
        if quicksand_layer is not None:
            for x, y, gid in quicksand_layer:
                tile = tmx_data.get_tile_image_by_gid(gid)
                if tile:
                    screen.blit(tile, (x * TILE_SIZE + camera.offset_x, y * TILE_SIZE + camera.offset_y))

        # HUD
        for i in range(player.hp):
            screen.blit(tile_heart, (10 + i * 40, 10))
        
        # Номер уровня
        font = pygame.font.Font(None, 36)
        level_text = font.render(f"Level {current_level + 1}/{len(LEVELS)}", True, (255, 255, 255))
        screen.blit(level_text, (SCREEN_WIDTH - 300, 10))

        pygame.display.flip()
        clock.tick(FPS)

    # Переход на следующий уровень
    if level_complete:
        main(current_level + 1)

if __name__ == "__main__":
    main(0)  # Начинаем с уровня 0 (level-1.tmx)

