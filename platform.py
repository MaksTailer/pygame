import pygame

class MovingPlatform:
    def __init__(self, rect, direction, speed, distance, image=None, name=None):
        self.name = name
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
            target_w, target_h = max(1, int(self.rect.width)), max(1, int(self.rect.height))
            # масштабируем только если размеры отличаются
            if self.image.get_size() != (target_w, target_h):
                self.image = pygame.transform.scale(self.image, (target_w, target_h))


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