import pygame
import pytmx
from platform import MovingPlatform 
from constants import TILE_SIZE

def load_map(filename):
    tmx_data = pytmx.load_pygame(filename, pixelalpha=True)
    tiles = []
    traps = []
    platforms = []

    for layer in tmx_data.visible_layers:
        if isinstance(layer, pytmx.TiledTileLayer):
            for x, y, gid in layer:
                tile = tmx_data.get_tile_image_by_gid(gid)
                if tile and layer.name.lower() == "ground":
                    tiles.append(pygame.Rect(x * tmx_data.tilewidth, y * tmx_data.tileheight, TILE_SIZE, TILE_SIZE))
                elif tile and layer.name.lower() == "traps":
                    traps.append(pygame.Rect(x * tmx_data.tilewidth, y * tmx_data.tileheight, TILE_SIZE, TILE_SIZE))

        elif isinstance(layer, pytmx.TiledObjectGroup):
            if layer.name.lower() == "movingplatforms":
                for obj in layer:
                    image = obj.image.convert_alpha() if obj.image else None
                    if image:
                        w = int(round(obj.width)) if getattr(obj, "width", 0) else image.get_width()
                        h = int(round(obj.height)) if getattr(obj, "height", 0) else image.get_height()
                        x = int(round(obj.x))
                        y = int(round(obj.y - h))
                    else:
                        w = int(obj.width) if obj.width else int(tmx_data.tilewidth)
                        h = int(obj.height) if obj.height else int(tmx_data.tileheight)
                        x = int(obj.x)
                        y = int(obj.y)
                    rect = pygame.Rect(x, y, w, h)
                    direction = str(obj.properties.get("direction", "horizontal"))
                    speed = int(obj.properties.get("speed", 2))
                    distance = int(obj.properties.get("distance", 128))
                    name = obj.name or obj.properties.get("name")
                    platforms.append(MovingPlatform(rect, direction, speed, distance, image, name))
    return tmx_data, tiles, traps, platforms