import pygame
import sys
import pytmx
import random
pygame.init()
pygame.mixer.init()
from constants import *
from platform import *
from camera import *
from player import *
from map_loader import load_map
from enemy import Bacteria, Virus, Projectile, Boss



def play_level_music(level_index):
    pygame.mixer.music.stop()
    pygame.mixer.music.load(FON_MUSIC[level_index])
    pygame.mixer.music.set_volume(0.3)  # громкость (0.0 – 1.0)
    pygame.mixer.music.play(-1)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Map from Tiled")
clock = pygame.time.Clock()

# === Загрузка ассетов ===
background = pygame.image.load("assets/background-1.png").convert()
background = pygame.transform.scale(background, (SCREEN_WIDTH, SCREEN_HEIGHT))
character_sheet = pygame.image.load("assets/person.png").convert_alpha()
character_shift = pygame.image.load("assets/umbrella.png").convert_alpha()
ground = pygame.image.load("assets/ground.png").convert_alpha()
enemy_sheet = pygame.image.load("assets/enemies.png").convert_alpha()
shot_sheet = pygame.image.load("assets/fire.png").convert_alpha()
boss_sheet = pygame.image.load("assets/Boss-1.png").convert_alpha()

# === Функция для нарезки спрайтов ===
def get_sprite(sheet, x, y, w, h):
    sprite = pygame.Surface((w, h), pygame.SRCALPHA)
    sprite.blit(sheet, (0, 0), (x * w, y * h, w, h))
    return sprite

# === Спрайты персонажа ===
player_sprites = {
    "walk1": get_sprite(character_sheet, 0, 1, CHAR_SIZE, CHAR_SIZE),
    "walk2": get_sprite(character_sheet, 0, 2, CHAR_SIZE, CHAR_SIZE),
    "jump": get_sprite(character_sheet, 0, 3, CHAR_SIZE, CHAR_SIZE),
    "idle": get_sprite(character_sheet, 0, 0, CHAR_SIZE, CHAR_SIZE),
    "shift": get_sprite(character_shift , 0, 0, CHAR_SIZE, CHAR_SIZE)
}
# === Спрайты босса ===
boss_sprites = {
    "idle1": get_sprite(boss_sheet, 0, 0, 256, 256),
}

    # Нарезаем спрайты бактерии из enemies.png
    # Предполагаем: левый верхний (0,0) — idle, снизу (0, CHAR_SIZE) и (CHAR_SIZE, CHAR_SIZE) — walk1, walk2
tile_heart = get_sprite(ground, 13, 17, TILE_SIZE, TILE_SIZE)


# === Перезапуск ===
def restart_game(saved_coins=0, saved_diamonds=0):
    main(0, saved_coins, saved_diamonds)

# === Основная функция ===
def main(current_level=0, saved_coins=0, saved_diamonds=0):
    # Загружаем текущий уровень
    if current_level >= len(LEVELS):
        current_level = 0  # Циклим на первый уровень (или финальный экран)
    
    play_level_music(current_level)
    level_file = LEVELS[current_level]
    bg_path = BACKGROUNDS[current_level % len(BACKGROUNDS)]
    background = pygame.image.load(bg_path).convert()
    background = pygame.transform.scale(background, (SCREEN_WIDTH, SCREEN_HEIGHT))
    
    tmx_data, tiles, traps, platforms, enemy_objs = load_map(level_file)

    collectibles = []  # элементы: {"type":"coin"/"diamond","rect":Rect,"gid":gid,"value":int,"draw":(x,y)}
    for layer in tmx_data.visible_layers:
        if isinstance(layer, pytmx.TiledObjectGroup):
            lname = (getattr(layer, "name", "") or "").lower()
            if lname == "collectibles":
                for obj in layer:
                    oname = (getattr(obj, "name", "") or "").lower()
                    if oname in ("coin", "diamond"):
                        obj_w = int(obj.width) if getattr(obj, "width", None) else TILE_SIZE
                        obj_h = int(obj.height) if getattr(obj, "height", None) else TILE_SIZE
                        # rect для коллизии (top-left)
                        rect_x = int(obj.x)
                        rect_y = int(obj.y) - obj_h
                        rect = pygame.Rect(rect_x, rect_y, obj_w, obj_h)
                        props = getattr(obj, "properties", {}) or {}
                        # default value = 1 для всех (если нужно другое — задайте свойство value в Tiled)
                        value = int(props.get("value", 1))
                        gid = getattr(obj, "gid", None)

                        # рассчитываем корректную позицию для отрисовки аналогично общим tile-объектам
                        draw_x = rect_x
                        draw_y = rect_y
                        if gid:
                            img = tmx_data.get_tile_image_by_gid(gid)
                            if img:
                                tile_x = int(obj.x) // TILE_SIZE
                                tile_y = int(obj.y) // TILE_SIZE
                                draw_x = tile_x * TILE_SIZE
                                draw_y = tile_y * TILE_SIZE + TILE_SIZE - img.get_height()

                        collectibles.append({
                            "type": oname,
                            "rect": rect,
                            "gid": gid,
                            "value": value,
                            "draw": (draw_x, draw_y)
                        })
    print(f"Collectibles on map: {len(collectibles)}")


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
    player.coins = int(saved_coins)
    player.diamonds = int(saved_diamonds)
    camera = Camera()

    
    bacteria_sprites = {
    "idle": get_sprite(enemy_sheet, 0, 2, TILE_SIZE, TILE_SIZE),      # (0, 0)
    "walk1": get_sprite(enemy_sheet, 0, 2, TILE_SIZE, TILE_SIZE),      # (0, 128) в пикселях
    "walk2": get_sprite(enemy_sheet, 0, 2, TILE_SIZE, TILE_SIZE),
    }

    virus_sprites = {
    "idle": get_sprite(enemy_sheet, 1, 1, TILE_SIZE, TILE_SIZE),      # (0, 0)
    "walk1": get_sprite(enemy_sheet, 1, 1, TILE_SIZE, TILE_SIZE),      # (0, 128) в пикселях
    "walk2": get_sprite(enemy_sheet, 1, 1, TILE_SIZE, TILE_SIZE),
    }
    proj_img = get_sprite(shot_sheet, 0, 0, TILE_SIZE, TILE_SIZE)
    #proj_img = pygame.transform.scale(proj_img, (32, 32))
        
    enemies = []
    boss = None
    for eo in enemy_objs:
        if eo.get("name","").lower() == "bacteria":
            ex = eo["x"]
            ey = eo["y"] - TILE_SIZE
            enemies.append(Bacteria(ex, ey, bacteria_sprites))
        elif eo.get("name","").lower() == "virus":
            ex = eo["x"]
            ey = eo["y"] - TILE_SIZE
            enemies.append(Virus(ex, ey, virus_sprites))
        if eo.get("name","").lower() == "boss":  # <-- добавить поддержку босса
            print("Босс создан!")
            ex = eo["x"]
            ey = eo["y"] - 256  # босс большой (256x256)
            boss = Boss(ex, ey, boss_sprites)
    
    print(f"Создано врагов: {len(enemies)} (бактерий: {sum(1 for e in enemies if isinstance(e, Bacteria))}, вирусов: {sum(1 for e in enemies if isinstance(e, Virus))}), боссов: {1 if boss else 0})")
    print(f"Объекты врагов из карты: {enemy_objs}")

    # список снарядов (врагов)
    enemy_projectiles = []
    player_projectiles = []

    print(f"Уровень {current_level + 1}/{len(LEVELS)}")

    running = True
    level_complete = False
    
    while running and not level_complete:
        dt = 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # мировые координаты мыши
                mx, my = event.pos
                world_x = mx - camera.offset_x
                world_y = my - camera.offset_y
                px = player.hitbox.centerx
                py = player.hitbox.centery
                vec = pygame.Vector2(world_x - px, world_y - py)
                if vec.length() == 0:
                    vec = pygame.Vector2(1, 0)
                vec = vec.normalize()
                speed = 8.0
                vx = vec.x * speed
                vy = vec.y * speed
                p = Projectile(px, py, vx, vy, color=(255,220,80), life=3000, image=proj_img)
                player_projectiles.append(p)
        
# Обновляем снаряды игрока
        for proj in player_projectiles[:]:
            dead = proj.update(dt)
            hit_any = False
            for e in enemies[:]:
                if proj.rect.colliderect(e.hitbox):
                    try:
                        died = e.damage(1)
                    except Exception:
                        e.hp -= 1
                        died = e.hp <= 0
                    if died:
                        try:
                            ENEMY_DEATH_SOUND.play()
                            enemies.remove(e)
                        except ValueError:
                            pass
                    hit_any = True
                    break
            
            # Проверяем попадание в босса
            if not hit_any and boss and proj.rect.colliderect(boss.hitbox):
                try:
                    died = boss.damage(1)
                    if died:
                        boss = None  # босс убит
                except Exception:
                    pass
                hit_any = True
            
            if hit_any or dead:
                try:
                    player_projectiles.remove(proj)
                except ValueError:
                    pass

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
            # контакт враг - игрок (но НЕ если активна защита)
            if e.hitbox.colliderect(player.hitbox) and not player.shield_active:
                now = pygame.time.get_ticks()
                if now - player.last_hit_time > player.invincible_delay:
                    player.hp -= 1
                    player.last_hit_time = now
                    player.vel_y = -8  # отскок вверх

        if boss:
            boss.update(player, all_tiles, enemy_projectiles)
            # контакт босс - игрок
            if boss.hitbox.colliderect(player.hitbox) and not player.shield_active:
                now = pygame.time.get_ticks()
                if now - player.last_hit_time > player.invincible_delay:
                    player.hp -= 2  # босс наносит больше урона
                    player.last_hit_time = now
                    player.vel_y = -10

        # Обновляем снаряды врагов
        dt = 1
        for proj in enemy_projectiles[:]:
            dead = proj.update(dt)
            if proj.rect.colliderect(player.hitbox) and player.shield_active:
                # Если щит активен — игнорируем урон, но удаляем снаряд
                try:
                    enemy_projectiles.remove(proj)
                except ValueError:
                    pass
            elif proj.rect.colliderect(player.hitbox) and not player.shield_active:
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
        # --- Подбор коллектиблов ---
        for c in collectibles[:]:
            if c["rect"].colliderect(player.hitbox):
                if c["type"] == "coin":
                    player.coins += c["value"]
                    PICKUP_SOUND.play()
                else:
                    player.diamonds += c["value"]
                    PICKUP_SOUND.play()
                try:
                    collectibles.remove(c)
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
            LEVEL_COMPLETE_SOUND.play()
            print(f"Уровень {current_level + 1} завершён! Переход на уровень {current_level + 2}...")

        # 6. Проверяем смерть
        if player.hp <= 0:
            print("Игрок погиб! Перезагрузка уровня 1...")
            main(0, 0, 0)  # Возвращаемся на первый уровень
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
        if boss:
            boss.draw(screen, (camera.offset_x, camera.offset_y))


        # Рисуем снаряды врагов
        for proj in enemy_projectiles:
            proj.draw(screen, (camera.offset_x, camera.offset_y))

        for proj in player_projectiles:
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

                        # Пропускаем отрисовку коллектиблов — будем рисовать их через список collectibles
                        if layer_name == "collectibles" and obj_name in ("coin", "diamond"):
                            continue

                        img = tmx_data.get_tile_image_by_gid(gid)
                        if img:
                            # выравниваем позицию по сетке тайлов
                            tile_x = int(obj.x) // TILE_SIZE
                            tile_y = int(obj.y) // TILE_SIZE
                            draw_x = tile_x * TILE_SIZE + camera.offset_x
                            draw_y = tile_y * TILE_SIZE + camera.offset_y + TILE_SIZE - img.get_height()
                            screen.blit(img, (draw_x, draw_y))

        # Рисуем текущие (не собранные) коллектиблы
        for c in collectibles:
            gid = c.get("gid")
            if gid is not None:
                img = tmx_data.get_tile_image_by_gid(gid)
                if img:
                    draw_x, draw_y = c.get("draw", (c["rect"].x, c["rect"].y))
                    screen.blit(img, (draw_x + camera.offset_x, draw_y + camera.offset_y))
            else:
                # если без gid, рисуем простым прямоугольником (на случай)
                screen.fill((255, 215, 0), (c["rect"].x + camera.offset_x, c["rect"].y + camera.offset_y, c["rect"].width, c["rect"].height))

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

         # Счётчики коллектиблов
        font = pygame.font.Font(None, 36)
        coin_text = font.render(f"Coins: {player.coins}", True, (255, 215, 0))
        diamond_text = font.render(f"Diamonds: {player.diamonds}", True, (0, 200, 255))
        screen.blit(coin_text, (10, 60))
        screen.blit(diamond_text, (10, 100))
        
        # Номер уровня
        font = pygame.font.Font(None, 36)
        level_text = font.render(f"Level {current_level + 1}/{len(LEVELS)}", True, (255, 255, 255))
        screen.blit(level_text, (SCREEN_WIDTH - 300, 10))

        pygame.display.flip()
        clock.tick(FPS)

    # Переход на следующий уровень
    if level_complete:      
        main(current_level + 1, player.coins, player.diamonds)

if __name__ == "__main__":
    main(0, 0, 0)  # Начинаем с уровня 0 (level-1.tmx)

