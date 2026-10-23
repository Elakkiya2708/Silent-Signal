
import os
import json
import math
import random
import pygame

# =========================================================
# SILENT SIGNAL - HORROR EDITION
# =========================================================

pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

WIDTH, HEIGHT = 1100, 700
FPS = 60
TILE = 50
COLS, ROWS = 22, 14
SAVE_FILE = "silent_signal_save.json"

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SILENT SIGNAL | Horror Survival")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("consolas", 20)
SMALL = pygame.font.SysFont("consolas", 15)
TITLE = pygame.font.SysFont("georgia", 66, bold=True)
BIG = pygame.font.SysFont("consolas", 34, bold=True)

BLACK = (5, 6, 9)
WHITE = (230, 230, 230)
RED = (190, 25, 35)
GREEN = (65, 200, 120)
GREY = (70, 75, 82)
DARK = (15, 18, 22)

# Optional audio files:
# assets/jumpscare.wav
# assets/chase.wav
# assets/hit.wav
# assets/ambient.wav

sounds = {}

def load_sound(name, filename):
    path = os.path.join("assets", filename)
    try:
        if pygame.mixer.get_init() and os.path.exists(path):
            sounds[name] = pygame.mixer.Sound(path)
    except pygame.error:
        pass

load_sound("jumpscare", "jumpscare.wav")
load_sound("chase", "chase.wav")
load_sound("hit", "hit.wav")
load_sound("ambient", "ambient.wav")

def play_sound(name):
    try:
        if name in sounds:
            sounds[name].play()
    except pygame.error:
        pass

def text(surface, value, font, color, x, y, center=False):
    image = font.render(str(value), True, color)
    rect = image.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(image, rect)

def clamp(value, low, high):
    return max(low, min(value, high))

def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

# =========================================================
# GAME DATA
# =========================================================

CHAPTERS = [
    "THE ABANDONED HOSPITAL",
    "THE SILENT SCHOOL",
    "THE FORGOTTEN BASEMENT",
    "THE BLOOD MOON FOREST",
    "THE SIGNAL SOURCE",
]

MAPS = [
    [
        "######################",
        "#P....#..............#",
        "#.##..#.####.#####...#",
        "#.....#......#.......#",
        "###.######.#.#.####..#",
        "#..........#.#.......#",
        "#.##########.#######.#",
        "#...........E.......#",
        "#.####.###########..#",
        "#......#............#",
        "#.####.#.##########..#",
        "#......#...........X.#",
        "#....................#",
        "######################",
    ],
    [
        "######################",
        "#P........#..........#",
        "#.######..#.#######..#",
        "#...........#........#",
        "#####.#######.####...#",
        "#.................E..#",
        "#.########.#########.#",
        "#........#...........#",
        "#.######.#.########..#",
        "#........#...........#",
        "#.##############.##..#",
        "#.................X..#",
        "#....................#",
        "######################",
    ],
    [
        "######################",
        "#P....#..............#",
        "###.#.#.###########..#",
        "#...#.................#",
        "#.##########.######..#",
        "#..........#.........#",
        "#.######...#.#########",
        "#......#...#.........#",
        "#.####.#.##########..#",
        "#......#............E#",
        "#.###############.#..#",
        "#..................X.#",
        "#....................#",
        "######################",
    ],
    [
        "######################",
        "#P...............#...#",
        "#.########.#######...#",
        "#........#...........#",
        "######.#.##########..#",
        "#......#.........E...#",
        "#.###############....#",
        "#....................#",
        "#.##########.#######.#",
        "#..........#.........#",
        "#.########.#.#######.#",
        "#..........#.......X.#",
        "#....................#",
        "######################",
    ],
    [
        "######################",
        "#P..................#",
        "#.#######.#########..#",
        "#.......#............#",
        "#######.###########..#",
        "#....................#",
        "#.###############.####",
        "#........E...........#",
        "#.###########.######.#",
        "#....................#",
        "#.###############.##.#",
        "#..................X.#",
        "#....................#",
        "######################",
    ],
]

# Normalize row lengths so maps are always safe.
for map_index, layout in enumerate(MAPS):
    MAPS[map_index] = [
        row.ljust(COLS, "#")[:COLS] for row in layout
    ]

# =========================================================
# VISUAL EFFECTS
# =========================================================

class Effects:
    def __init__(self):
        self.shake = 0
        self.flash = 0
        self.blood = 0
        self.jumpscare = 0
        self.vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.fog = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.make_vignette()

    def make_vignette(self):
        self.vignette.fill((0, 0, 0, 0))
        for i in range(12):
            margin = i * 22
            alpha = min(180, 12 + i * 15)
            pygame.draw.rect(
                self.vignette,
                (0, 0, 0, alpha),
                (margin, margin, WIDTH - 2 * margin, HEIGHT - 2 * margin),
                width=25,
            )

    def trigger_jumpscare(self):
        self.jumpscare = 70
        self.shake = 18
        self.flash = 10
        play_sound("jumpscare")

    def damage(self):
        self.blood = 25
        self.shake = 12
        play_sound("hit")

    def update(self):
        self.shake = max(0, self.shake - 1)
        self.flash = max(0, self.flash - 1)
        self.blood = max(0, self.blood - 1)
        self.jumpscare = max(0, self.jumpscare - 1)

    def offset(self):
        if self.shake:
            return (
                random.randint(-self.shake, self.shake),
                random.randint(-self.shake, self.shake),
            )
        return (0, 0)

    def draw_blood(self, surface):
        if self.blood <= 0:
            return

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        alpha = min(140, self.blood * 5)
        pygame.draw.rect(
            overlay, (150, 0, 10, alpha), (0, 0, WIDTH, HEIGHT), 24
        )

        for _ in range(8):
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT)
            pygame.draw.circle(
                overlay, (130, 0, 10, alpha), (x, y),
                random.randint(2, 9)
            )

        surface.blit(overlay, (0, 0))

    def draw_jumpscare(self, surface):
        if self.jumpscare <= 0:
            return

        # Procedural monster face: no external image required.
        surface.fill((18, 0, 4))

        pulse = 1 if self.jumpscare % 8 < 4 else 0
        cx, cy = WIDTH // 2, HEIGHT // 2

        pygame.draw.ellipse(
            surface, (65, 10, 17),
            (cx - 185, cy - 250, 370, 500)
        )

        pygame.draw.ellipse(
            surface, (8, 3, 7),
            (cx - 135, cy - 170, 100, 120)
        )
        pygame.draw.ellipse(
            surface, (8, 3, 7),
            (cx + 35, cy - 170, 100, 120)
        )

        eye_color = (255, 20, 15) if pulse else (210, 0, 0)
        pygame.draw.ellipse(
            surface, eye_color,
            (cx - 110, cy - 125, 55, 35)
        )
        pygame.draw.ellipse(
            surface, eye_color,
            (cx + 55, cy - 125, 55, 35)
        )

        pygame.draw.ellipse(
            surface, (0, 0, 0),
            (cx - 100, cy + 15, 200, 155)
        )

        for i in range(7):
            tx = cx - 78 + i * 25
            pygame.draw.polygon(
                surface, (230, 220, 205),
                [(tx, cy + 20), (tx + 12, cy + 20),
                 (tx + 6, cy + 65)]
            )

        text(surface, "DON'T LOOK AWAY", BIG, (255, 35, 35),
             cx, HEIGHT - 70, center=True)

# =========================================================
# MAIN GAME
# =========================================================

class SilentSignal:
    def __init__(self):
        self.state = "menu"
        self.settings = {"flashlight": True, "screen_shake": True}
        self.effects = Effects()
        self.reset_game()

    def reset_game(self):
        self.chapter = 0
        self.health = 100
        self.ammo = 12
        self.medkits = 2
        self.score = 0
        self.kills = 0
        self.player_speed = 3
        self.flashlight_on = True
        self.flashlight_energy = 100
        self.enemy = None
        self.boss = False
        self.jumpscare_cooldown = 0
        self.message = ""
        self.message_timer = 0
        self.start_chapter(0)

    def start_chapter(self, chapter):
        self.chapter = chapter
        self.map_data = MAPS[chapter][:]
        self.walls = set()
        self.items = []
        self.exit_pos = (COLS - 2, ROWS - 2)

        for y, row in enumerate(self.map_data):
            for x, char in enumerate(row):
                if char == "#":
                    self.walls.add((x, y))
                elif char == "P":
                    self.px, self.py = x * TILE + TILE // 2, y * TILE + TILE // 2
                elif char == "E":
                    self.enemy = {
                        "x": x * TILE + TILE // 2,
                        "y": y * TILE + TILE // 2,
                        "health": 65 + chapter * 12,
                        "speed": 1.0 + chapter * 0.15,
                        "alive": True,
                    }
                elif char == "X":
                    self.exit_pos = (x, y)

        self.boss = chapter == 4
        if self.boss and self.enemy:
            self.enemy["health"] += 100

        self.last_jumpscare = pygame.time.get_ticks()
        self.flashlight_energy = max(40, self.flashlight_energy)
        self.message = CHAPTERS[chapter]
        self.message_timer = 180

    def tile_at(self, px, py):
        return int(px // TILE), int(py // TILE)

    def is_wall(self, px, py):
        tx, ty = self.tile_at(px, py)
        return (tx, ty) in self.walls

    def can_move_to(self, x, y):
        radius = 13
        return not any(
            self.is_wall(x + dx, y + dy)
            for dx, dy in [
                (-radius, 0), (radius, 0), (0, -radius), (0, radius)
            ]
        )

    def move_player(self, dx, dy):
        if self.can_move_to(self.px + dx, self.py):
            self.px += dx
        if self.can_move_to(self.px, self.py + dy):
            self.py += dy

    def show_message(self, message):
        self.message = message
        self.message_timer = 150

    def shoot(self):
        if self.ammo <= 0:
            self.show_message("OUT OF AMMO!")
            return

        self.ammo -= 1

        if not self.enemy or not self.enemy["alive"]:
            return

        d = distance((self.px, self.py),
                    (self.enemy["x"], self.enemy["y"]))

        if d < 300:
            self.enemy["health"] -= 35
            self.score += 10

            if self.enemy["health"] <= 0:
                self.enemy["alive"] = False
                self.kills += 1
                self.score += 100
                self.show_message("ENTITY ELIMINATED")
            else:
                self.show_message("TARGET HIT")
        else:
            self.show_message("SHOT MISSED")

    def interact(self):
        tx, ty = self.tile_at(self.px, self.py)

        # Pickups appear dynamically.
        for item in self.items[:]:
            if distance((self.px, self.py), item["pos"]) < 40:
                if item["type"] == "ammo":
                    self.ammo += 6
                    self.show_message("AMMO +6")
                elif item["type"] == "medkit":
                    self.medkits += 1
                    self.show_message("MEDKIT +1")
                self.items.remove(item)
                return

        ex, ey = self.exit_pos
        if abs(tx - ex) <= 1 and abs(ty - ey) <= 1:
            if self.enemy and self.enemy["alive"]:
                self.show_message("DEFEAT THE ENTITY FIRST")
                return

            if self.chapter < len(CHAPTERS) - 1:
                self.start_chapter(self.chapter + 1)
            else:
                self.state = "ending"
            return

        self.show_message("NOTHING TO INTERACT WITH")

    def heal(self):
        if self.medkits > 0 and self.health < 100:
            self.medkits -= 1
            self.health = min(100, self.health + 40)
            self.show_message("HEALTH RESTORED")
        else:
            self.show_message("NO MEDKITS AVAILABLE")

    def save_game(self):
        data = {
            "chapter": self.chapter,
            "health": self.health,
            "ammo": self.ammo,
            "medkits": self.medkits,
            "score": self.score,
            "kills": self.kills,
        }
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
            self.show_message("GAME SAVED")
        except OSError:
            self.show_message("SAVE FAILED")

    def load_game(self):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)

            chapter = int(data.get("chapter", 0))
            if not 0 <= chapter < len(CHAPTERS):
                raise ValueError("Invalid chapter")

            self.start_chapter(chapter)
            self.health = clamp(int(data.get("health", 100)), 1, 100)
            self.ammo = max(0, int(data.get("ammo", 12)))
            self.medkits = max(0, int(data.get("medkits", 2)))
            self.score = max(0, int(data.get("score", 0)))
            self.kills = max(0, int(data.get("kills", 0)))
            self.state = "playing"
            self.show_message("SAVE LOADED")
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.show_message("NO VALID SAVE FOUND")

    def update_enemy(self):
        if not self.enemy or not self.enemy["alive"]:
            return

        ex, ey = self.enemy["x"], self.enemy["y"]
        dx, dy = self.px - ex, self.py - ey
        dist = max(1, math.hypot(dx, dy))

        if dist < 450:
            speed = self.enemy["speed"]
            nx = ex + dx / dist * speed
            ny = ey + dy / dist * speed

            if self.can_move_to(nx, ey):
                self.enemy["x"] = nx
            if self.can_move_to(self.enemy["x"], ny):
                self.enemy["y"] = ny

        if dist < 36:
            self.health -= 0.4
            if random.random() < 0.025:
                self.effects.damage()

        if dist < 240 and random.random() < 0.002:
            now = pygame.time.get_ticks()
            if now - self.last_jumpscare > 8000:
                self.effects.trigger_jumpscare()
                self.last_jumpscare = now

        if self.health <= 0:
            self.health = 0
            self.state = "gameover"

    def update(self):
        self.effects.update()

        if self.message_timer > 0:
            self.message_timer -= 1

        if self.state != "playing":
            return

        keys = pygame.key.get_pressed()
        dx = dy = 0

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= self.player_speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += self.player_speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= self.player_speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += self.player_speed

        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071

        self.move_player(dx, dy)

        if self.flashlight_on:
            self.flashlight_energy = max(0, self.flashlight_energy - 0.015)
        else:
            self.flashlight_energy = min(100, self.flashlight_energy + 0.035)

        if self.flashlight_energy <= 0:
            self.flashlight_on = False

        self.update_enemy()

    # =====================================================
    # DRAWING
    # =====================================================

    def draw_world(self):
        screen.fill((9, 11, 14))
        ox, oy = self.effects.offset() if self.settings["screen_shake"] else (0, 0)

        # Camera follows the player.
        cam_x = clamp(self.px - WIDTH // 2, 0, COLS * TILE - WIDTH)
        cam_y = clamp(self.py - HEIGHT // 2, 0, ROWS * TILE - HEIGHT)

        for y in range(ROWS):
            for x in range(COLS):
                rect = pygame.Rect(
                    x * TILE - cam_x + ox,
                    y * TILE - cam_y + oy,
                    TILE, TILE
                )

                if (x, y) in self.walls:
                    pygame.draw.rect(screen, (25, 28, 33), rect)
                    pygame.draw.rect(screen, (42, 46, 52), rect, 2)
                else:
                    pygame.draw.rect(screen, (13, 16, 19), rect)
                    pygame.draw.rect(screen, (20, 23, 27), rect, 1)

                    # Random floor cracks.
                    if (x * 7 + y * 13) % 11 == 0:
                        pygame.draw.line(
                            screen, (27, 29, 32),
                            (rect.x + 8, rect.y + 10),
                            (rect.x + 28, rect.y + 30), 1
                        )

        # Exit.
        ex, ey = self.exit_pos
        exit_rect = pygame.Rect(
            ex * TILE - cam_x + ox,
            ey * TILE - cam_y + oy,
            TILE, TILE
        )
        pygame.draw.rect(screen, (40, 15, 18), exit_rect)
        pygame.draw.rect(screen, RED, exit_rect, 3)
        text(screen, "X", BIG, RED, exit_rect.centerx,
             exit_rect.centery, center=True)

        # Items.
        for item in self.items:
            ix, iy = item["pos"]
            color = (220, 180, 40) if item["type"] == "ammo" else GREEN
            pygame.draw.circle(
                screen, color,
                (int(ix - cam_x + ox), int(iy - cam_y + oy)), 8
            )

        # Enemy.
        if self.enemy and self.enemy["alive"]:
            ex, ey = self.enemy["x"], self.enemy["y"]
            sx, sy = int(ex - cam_x + ox), int(ey - cam_y + oy)

            pulse = 3 if pygame.time.get_ticks() % 500 < 250 else 0
            pygame.draw.ellipse(
                screen, (65, 5, 12),
                (sx - 19 - pulse, sy - 24 - pulse,
                 38 + pulse * 2, 48 + pulse * 2)
            )
            pygame.draw.circle(screen, (255, 0, 15), (sx - 7, sy - 5), 4)
            pygame.draw.circle(screen, (255, 0, 15), (sx + 7, sy - 5), 4)

            if self.boss:
                text(screen, "THE SIGNAL", SMALL, RED, sx, sy - 45,
                     center=True)

        # Player.
        sx = int(self.px - cam_x + ox)
        sy = int(self.py - cam_y + oy)
        pygame.draw.circle(screen, (180, 190, 190), (sx, sy), 13)
        pygame.draw.circle(screen, (30, 35, 40), (sx, sy), 13, 2)
        pygame.draw.circle(screen, (230, 230, 190), (sx + 4, sy - 3), 3)

        self.draw_fog(cam_x, cam_y, sx, sy, ox, oy)
        self.draw_hud()

    def draw_fog(self, cam_x, cam_y, sx, sy, ox, oy):
        # Dark overlay with a moving flashlight opening.
        darkness = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        darkness.fill((0, 0, 0, 224))

        if self.settings["flashlight"] and self.flashlight_on:
            flicker = random.randint(0, 12)
            radius = int(175 * self.flashlight_energy / 100) - flicker
            radius = max(30, radius)

            mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(mask, (0, 0, 0, 0), (sx, sy), radius)
            pygame.draw.circle(
                mask, (0, 0, 0, 55), (sx, sy), radius + 25, 22
            )
            darkness.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

            # A subtle forward cone.
            keys = pygame.key.get_pressed()
            fx, fy = 1, 0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                fx = -1
            elif keys[pygame.K_w] or keys[pygame.K_UP]:
                fx, fy = 0, -1
            elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
                fx, fy = 0, 1

            points = [
                (sx, sy),
                (sx + fx * radius + fy * radius * 0.55,
                 sy + fy * radius - fx * radius * 0.55),
                (sx + fx * radius + fy * radius * -0.55,
                 sy + fy * radius - fx * radius * -0.55),
            ]
            pygame.draw.polygon(mask, (0, 0, 0, 0), points)
            darkness.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        screen.blit(darkness, (0, 0))

        # Fog wisps.
        fog = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        t = pygame.time.get_ticks() * 0.015
        for i in range(7):
            x = int((i * 193 + t * (i % 3 + 1)) % (WIDTH + 150)) - 75
            y = int((i * 97 + math.sin(t + i) * 60) % HEIGHT)
            pygame.draw.ellipse(
                fog, (130, 140, 150, 12),
                (x, y, 170, 35)
            )
        screen.blit(fog, (0, 0))

        # Permanent edge darkness.
        screen.blit(self.effects.vignette, (0, 0))

        if self.effects.flash > 0:
            flash = pygame.Surface((WIDTH, HEIGHT))
            flash.fill((255, 255, 255))
            flash.set_alpha(self.effects.flash * 18)
            screen.blit(flash, (0, 0))

        self.effects.draw_blood(screen)

    def draw_hud(self):
        pygame.draw.rect(screen, (8, 10, 13), (0, 0, WIDTH, 83))
        pygame.draw.line(screen, (80, 20, 27), (0, 82), (WIDTH, 82), 2)

        text(screen, "SILENT SIGNAL", FONT, (220, 220, 220), 18, 12)
        text(screen, f"CHAPTER {self.chapter + 1}/5",
             SMALL, (200, 70, 75), 18, 43)

        # Health bar.
        text(screen, "HP", SMALL, WHITE, 290, 15)
        pygame.draw.rect(screen, (50, 15, 18), (325, 17, 160, 15))
        pygame.draw.rect(
            screen, RED, (325, 17, int(160 * self.health / 100), 15)
        )
        text(screen, str(int(self.health)), SMALL, WHITE, 490, 15)

        text(screen, f"AMMO: {self.ammo}", SMALL, WHITE, 555, 15)
        text(screen, f"MEDKITS: {self.medkits}", SMALL, GREEN, 555, 43)
        text(screen, f"SCORE: {self.score}", SMALL, (220, 190, 80), 720, 15)

        energy_color = GREEN if self.flashlight_energy > 30 else RED
        text(screen, "LIGHT", SMALL, WHITE, 840, 15)
        pygame.draw.rect(screen, (40, 40, 40), (900, 18, 120, 12))
        pygame.draw.rect(
            screen, energy_color,
            (900, 18, int(120 * self.flashlight_energy / 100), 12)
        )

        text(screen, "WASD MOVE | E INTERACT | SPACE SHOOT",
             SMALL, (150, 155, 160), 290, 53)
        text(screen, "F LIGHT | H HEAL | F5 SAVE | ESC PAUSE",
             SMALL, (150, 155, 160), 290, 66)

        if self.message_timer > 0 and self.message:
            panel = pygame.Surface((620, 42), pygame.SRCALPHA)
            panel.fill((5, 5, 8, 210))
            screen.blit(panel, (WIDTH // 2 - 310, 100))
            text(screen, self.message, FONT, (230, 70, 80),
                 WIDTH // 2, 121, center=True)

    def button(self, label, rect, mouse_pos, selected=False):
        hover = rect.collidepoint(mouse_pos)
        color = (65, 20, 27) if hover or selected else (18, 21, 26)
        border = (220, 45, 55) if hover or selected else (85, 90, 100)
        pygame.draw.rect(screen, color, rect, border_radius=5)
        pygame.draw.rect(screen, border, rect, 2, border_radius=5)
        text(screen, label, FONT, WHITE, rect.centerx, rect.centery,
             center=True)
        return hover

    def draw_background(self):
        screen.fill((5, 7, 10))

        for i in range(20):
            x = (i * 71 + pygame.time.get_ticks() // 30) % WIDTH
            y = (i * 43) % HEIGHT
            pygame.draw.circle(screen, (20, 23, 28), (x, y), 1)

        pygame.draw.rect(
            screen, (10, 12, 16), (WIDTH // 2 - 330, 40, 660, 620),
            border_radius=14
        )
        pygame.draw.rect(
            screen, (65, 20, 28), (WIDTH // 2 - 330, 40, 660, 620),
            2, border_radius=14
        )

    def draw_menu(self):
        self.draw_background()
        mouse = pygame.mouse.get_pos()

        text(screen, "SILENT", TITLE, (215, 215, 220),
             WIDTH // 2, 125, center=True)
        text(screen, "SIGNAL", TITLE, (180, 25, 40),
             WIDTH // 2, 195, center=True)
        text(screen, "THE DARKNESS IS LISTENING",
             SMALL, (145, 145, 150), WIDTH // 2, 245, center=True)

        buttons = [
            ("NEW GAME", "new"),
            ("CONTINUE / LOAD", "load"),
            ("SETTINGS", "settings"),
            ("QUIT", "quit"),
        ]

        for i, (label, action) in enumerate(buttons):
            rect = pygame.Rect(WIDTH // 2 - 150, 310 + i * 65, 300, 48)
            self.button(label, rect, mouse)
            if pygame.mouse.get_pressed()[0] and rect.collidepoint(mouse):
                if action == "new":
                    self.reset_game()
                    self.state = "playing"
                elif action == "load":
                    self.load_game()
                elif action == "settings":
                    self.state = "settings"
                elif action == "quit":
                    self.state = "quit"

        text(screen, "A HORROR SURVIVAL EXPERIENCE",
             SMALL, (100, 100, 110), WIDTH // 2, 625, center=True)

    def draw_pause(self):
        self.draw_world()
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))

        mouse = pygame.mouse.get_pos()
        text(screen, "PAUSED", TITLE, WHITE, WIDTH // 2, 170, center=True)

        options = [
            ("RESUME", "resume"),
            ("SAVE GAME", "save"),
            ("SETTINGS", "settings"),
            ("MAIN MENU", "menu"),
        ]

        for i, (label, action) in enumerate(options):
            rect = pygame.Rect(WIDTH // 2 - 150, 275 + i * 62, 300, 46)
            self.button(label, rect, mouse)
            if pygame.mouse.get_pressed()[0] and rect.collidepoint(mouse):
                if action == "resume":
                    self.state = "playing"
                elif action == "save":
                    self.save_game()
                elif action == "settings":
                    self.state = "settings"
                elif action == "menu":
                    self.state = "menu"

    def draw_settings(self):
        self.draw_background()
        mouse = pygame.mouse.get_pos()

        text(screen, "SETTINGS", TITLE, WHITE,
             WIDTH // 2, 130, center=True)

        options = [
            ("FLASHLIGHT: " + ("ON" if self.settings["flashlight"] else "OFF"),
             "flashlight"),
            ("SCREEN SHAKE: " + ("ON" if self.settings["screen_shake"] else "OFF"),
             "shake"),
            ("BACK", "back"),
        ]

        for i, (label, action) in enumerate(options):
            rect = pygame.Rect(WIDTH // 2 - 210, 280 + i * 80, 420, 55)
            self.button(label, rect, mouse)
            if pygame.mouse.get_pressed()[0] and rect.collidepoint(mouse):
                if action == "flashlight":
                    self.settings["flashlight"] = not self.settings["flashlight"]
                elif action == "shake":
                    self.settings["screen_shake"] = not self.settings["screen_shake"]
                elif action == "back":
                    self.state = "pause" if self.previous_state == "pause" else "menu"
                pygame.time.wait(160)

        text(screen, "ESC TO RETURN",
             SMALL, (150, 150, 155), WIDTH // 2, 550, center=True)

    def draw_ending(self):
        screen.fill((3, 3, 5))
        text(screen, "SIGNAL TERMINATED", TITLE, (200, 30, 40),
             WIDTH // 2, 230, center=True)
        text(screen, "YOU SURVIVED THE DARKNESS",
             FONT, WHITE, WIDTH // 2, 325, center=True)
        text(screen, f"FINAL SCORE: {self.score}",
             BIG, (220, 190, 100), WIDTH // 2, 385, center=True)
        text(screen, "PRESS ENTER TO RETURN TO MENU",
             SMALL, GREY, WIDTH // 2, 500, center=True)

    def draw_gameover(self):
        screen.fill((5, 0, 2))
        text(screen, "YOU ARE DEAD", TITLE, RED,
             WIDTH // 2, 240, center=True)
        text(screen, "THE SIGNAL CLAIMED ANOTHER SOUL",
             FONT, (170, 100, 100), WIDTH // 2, 330, center=True)
        text(screen, "R - RETRY     ENTER - MAIN MENU",
             SMALL, WHITE, WIDTH // 2, 440, center=True)

    # =====================================================
    # INPUT
    # =====================================================

    def handle_key(self, key):
        if self.state == "menu":
            if key == pygame.K_RETURN:
                self.reset_game()
                self.state = "playing"
            return

        if self.state == "playing":
            if key == pygame.K_ESCAPE:
                self.previous_state = "pause"
                self.state = "pause"
            elif key == pygame.K_SPACE:
                self.shoot()
            elif key == pygame.K_e:
                self.interact()
            elif key == pygame.K_h:
                self.heal()
            elif key == pygame.K_f:
                self.flashlight_on = not self.flashlight_on
            elif key == pygame.K_F5:
                self.save_game()

        elif self.state == "pause":
            if key == pygame.K_ESCAPE:
                self.state = "playing"

        elif self.state == "settings":
            if key == pygame.K_ESCAPE:
                self.state = getattr(self, "previous_state", "menu")

        elif self.state == "ending":
            if key == pygame.K_RETURN:
                self.state = "menu"

        elif self.state == "gameover":
            if key == pygame.K_r:
                self.reset_game()
                self.state = "playing"
            elif key == pygame.K_RETURN:
                self.state = "menu"

    def run(self):
        running = True

        while running:
            clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == "playing":
                        self.shoot()

            self.update()

            if self.effects.jumpscare > 0 and self.state == "playing":
                self.effects.draw_jumpscare(screen)
            elif self.state == "menu":
                self.draw_menu()
            elif self.state == "playing":
                self.draw_world()
            elif self.state == "pause":
                self.draw_pause()
            elif self.state == "settings":
                self.draw_settings()
            elif self.state == "ending":
                self.draw_ending()
            elif self.state == "gameover":
                self.draw_gameover()
            elif self.state == "quit":
                running = False

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    game = SilentSignal()
    game.run()
