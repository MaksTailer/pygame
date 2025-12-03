import pygame
import pytmx
from platform import MovingPlatform 
from constants import TILE_SIZE

def load_map(filename):
    tmx_data = pytmx.load_pygame(filename, pixelalpha=True)
    tiles = []
    traps = []
    platforms = []
    enemies = []  # список объектов врагов (словарь с полями name,x,y)

    for layer in tmx_data.visible_layers:
        if isinstance(layer, pytmx.TiledTileLayer):
            for x, y, gid in layer:
                if gid != 0:
                    name = getattr(layer, "name", "").lower()
                    # считаем Ground и Sand как коллизии
                    if name in ("ground", "sand"):
                        tiles.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
                    elif name == "traps":
                        traps.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        elif isinstance(layer, pytmx.TiledObjectGroup):
            # объекты: платформы/враги/portal/...
            for obj in layer:
                oname = getattr(obj, "name", "") or ""
                oname_lower = oname.lower()
                # враги: объект с именем "Bacteria"
                if oname_lower == "bacteria":
                    enemies.append({"name":"Bacteria","x":int(obj.x),"y":int(obj.y)})
                elif oname_lower == "virus":
                    enemies.append({"name":"Virus","x":int(obj.x),"y":int(obj.y)})
            
                # --- Платформы: более надёжное определение/корректное позиционирование ---
                obj_type = (getattr(obj, "type", None) or "").lower()
                layer_name = getattr(layer, "name", "") or ""
                layer_name = layer_name.lower()

                is_moving_platform = (
                    obj_type == "movingplatform"
                    or oname_lower == "movingplatform"
                    or layer_name in ("movingplatform", "movingplatforms", "platforms")
                )

                if is_moving_platform:
                    # ширина/высота объекта (если не заданы — используем TILE_SIZE)
                    obj_w = int(obj.width) if getattr(obj, "width", None) else TILE_SIZE
                    obj_h = int(obj.height) if getattr(obj, "height", None) else TILE_SIZE

                    # Если объект — tile/object с gid, возьмём изображение
                    gid = getattr(obj, "gid", None)
                    image = None
                    if gid:
                        image = tmx_data.get_tile_image_by_gid(gid)
                        # pytmx возвращает Surface; преобразуем в pygame.Surface если нужно
                        # (обычно get_tile_image_by_gid уже возвращает Surface)
                    
                    # Учитываем, что для tile-объекта obj.y указывает на нижнюю границу,
                    # поэтому сдвигаем y вверх на высоту объекта
                    rect_x = int(obj.x)
                    rect_y = int(obj.y) - obj_h if gid else int(obj.y)

                    rect = pygame.Rect(rect_x, rect_y, obj_w, obj_h)

                    # чтение свойств direction/speed/distance из obj.properties, если есть
                    props = getattr(obj, "properties", {}) or {}
                    direction = props.get("direction", "horizontal")
                    try:
                        speed = float(props.get("speed", 1))
                    except Exception:
                        speed = 1.0
                    try:
                        distance = float(props.get("distance", TILE_SIZE))
                    except Exception:
                        distance = TILE_SIZE

                    platforms.append(MovingPlatform(rect, direction, speed, distance, image=image, name=oname))
    return tmx_data, tiles, traps, platforms, enemies