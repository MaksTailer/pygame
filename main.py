import pygame
import sys
import pytmx
import random

pygame.init()

# Настройки окна
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
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
    def __init__(self, x, y, map_height):
        super().__init__()
        self.image = player_sprites["idle"]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_y = 0
        self.on_ground = False
        self.hp = 10
        self.facing_right = True
        self.last_hit_time = 0
        self.invincible_delay = 1000
        self.map_height = map_height  # высота карты в пикселях
        self.fall_start_time = None   # время начала падения за пределы карты

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

        # Если игрок ниже границы карты — отслеживаем длительность падения
        if self.rect.top > self.map_height:
            if not self.on_ground:
                if self.fall_start_time is None:
                    self.fall_start_time = now
                elif now - self.fall_start_time > 3000:  # 3000 мс = 3 секунды
                    self.hp = 0
                    restart_game()
            else:
                # если каким-то образом оказался на земле, сбрасываем таймер падения
                self.fall_start_time = None
        else:
            # если вернулся в пределы карты — сбрасываем таймер
            self.fall_start_time = None

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
    platforms = []

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

        # Объектные слои (для платформ)
        elif isinstance(layer, pytmx.TiledObjectGroup):
            if layer.name.lower() == "movingplatforms":
                for obj in layer:
                    print(f"Объект: {obj.name}, image: {obj.image}, размер: {obj.width}x{obj.height}")
                    rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
                    direction = obj.properties.get("direction", "horizontal")
                    speed = int(obj.properties.get("speed", 2))
                    distance = int(obj.properties.get("distance", 128))
                    
                    # Получаем изображение объекта (если оно есть)
                    image = None
                    if obj.image:
                        image = obj.image.convert_alpha()

                    platforms.append(MovingPlatform(rect, direction, speed, distance, image))

    return tmx_data, tiles, traps, platforms


class MovingPlatform:
    def __init__(self, rect, direction, speed, distance, image=None):
        self.start_pos = pygame.Vector2(rect.topleft)
        self.rect = rect
        self.direction = direction
        self.speed = speed
        self.distance = distance
        self.offset = 0.0
        self.forward = True
        self.last_move = pygame.Vector2(0, 0)
        self.image = image
        
        # Масштабируем изображение под размер прямоугольника
        if self.image:
            self.image = pygame.transform.scale(self.image, (self.rect.width, self.rect.height))

    def update(self):
        # Сохраняем старую позицию
        old_x = self.rect.x
        old_y = self.rect.y
        
        move = self.speed if self.forward else -self.speed
        
        if self.direction == "horizontal":
            self.rect.x += move
            self.offset += move
        elif self.direction == "vertical":
            self.rect.y += move
            self.offset += move
        
        # Вычисляем, на сколько сдвинулась платформа
        self.last_move = pygame.Vector2(self.rect.x - old_x, self.rect.y - old_y)
        
        # Смена направления при достижении расстояния
        if abs(self.offset) >= self.distance:
            self.forward = not self.forward
            self.offset = 0

    def draw(self, surface, camera_offset):
        """Рисует платформу с учётом камеры"""
        screen_x = self.rect.x + camera_offset[0]
        screen_y = self.rect.y + camera_offset[1]
        
        if self.image:
            # Отрисовываем изображение
            surface.blit(self.image, (screen_x, screen_y))
        else:
            # Если нет изображения, рисуем цветной прямоугольник
            draw_rect = pygame.Rect(screen_x, screen_y, self.rect.width, self.rect.height)
            pygame.draw.rect(surface, (160, 100, 40), draw_rect)

# === Основная функция ===
def main():
    tmx_data, tiles, traps, platforms = load_map("assets/2map.tmx")

    map_pixel_height = tmx_data.height * tmx_data.tileheight
    player = Player(100, 300, map_pixel_height)
    camera = Camera()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 1. Сначала обновляем платформы
        for platform in platforms:
            platform.update()
        
        # 2. Добавляем только тайлы в коллизии (БЕЗ платформ!)
        all_tiles = tiles.copy()
        
        # 3. Добавляем только верхние поверхности платформ
        for platform in platforms:
            # Создаём тонкий прямоугольник только для верхней части платформы
            top_surface = pygame.Rect(
                platform.rect.x,
                platform.rect.y - 1,
                platform.rect.width,
                2  # Тонкая полоска для коллизии
            )
            all_tiles.append(top_surface)
        
        # 4. Обновляем игрока с учётом всех поверхностей
        player.update(all_tiles, traps)
        
        # 5. Применяем движение платформы к игроку
        for platform in platforms:
            on_platform = (
                player.rect.bottom >= platform.rect.top - 5 and
                player.rect.bottom <= platform.rect.top + 15 and
                player.rect.left < platform.rect.right and
                player.rect.right > platform.rect.left and
                player.vel_y >= 0
            )
            
            if on_platform:
                player.rect.x += int(platform.last_move.x)
                player.rect.y += int(platform.last_move.y)

        camera.update(player)

        # === ОТРИСОВКА ===
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

        # Отрисовка движущихся платформ
        for platform in platforms:
            pygame.draw.rect(
                screen,
                (160, 100, 40),
                (
                    platform.rect.x + camera.offset_x,
                    platform.rect.y + camera.offset_y,
                    platform.rect.width,
                    platform.rect.height
                )
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
