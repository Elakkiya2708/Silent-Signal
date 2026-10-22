import json
import os
import random
import math
import pygame

# SILENT SIGNAL — Professional UI/UX Edition
# Controls: WASD/Arrows move | E interact | SPACE shoot
# H heal | F flashlight | F5 save | ESC pause

pygame.init()

WIDTH, HEIGHT, TILE, FPS = 1100, 700, 50, 60
COLS, ROWS = 22, 14
SAVE_FILE = "silent_signal_save.json"

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SILENT SIGNAL | Survival Horror")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("consolas", 20)
SMALL = pygame.font.SysFont("consolas", 15)
TINY = pygame.font.SysFont("consolas", 12)
TITLE = pygame.font.SysFont("consolas", 52, bold=True)
SUBTITLE = pygame.font.SysFont("consolas", 24, bold=True)

C = {
    "bg": (7, 10, 16),
    "panel": (17, 23, 33),
    "panel2": (24, 32, 44),
    "line": (57, 73, 91),
    "white": (229, 235, 242),
    "muted": (140, 154, 170),
    "red": (220, 59, 72),
    "red_dark": (92, 25, 36),
    "green": (74, 216, 151),
    "yellow": (243, 197, 87),
    "blue": (83, 174, 237),
    "purple": (177, 115, 233),
    "floor": (24, 32, 41),
    "wall": (46, 57, 70)
}

CHAPTERS = [
    ("THE SIGNAL", "Find the access key, activate the transmitter."),
    ("COLD STORAGE", "Recover the key and activate the security console."),
    ("THE SURVIVORS", "Find the key and restore life support."),
    ("BELOW GROUND", "Reach the control room and survive."),
    ("SILENT SIGNAL", "Defeat the Warden and activate the emergency lift.")
]


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def draw_text(surface, value, x, y, color=None, font=None):
    text = (font or FONT).render(
        str(value), True, color or C["white"]
    )
    surface.blit(text, (int(x), int(y)))


def panel(surface, rect, color=None, border=None, radius=12, width=1):
    pygame.draw.rect(
        surface, color or C["panel"], rect, border_radius=radius
    )
    if border:
        pygame.draw.rect(
            surface, border, rect, width, border_radius=radius
        )


def draw_bar(surface, x, y, w, h, value, maximum, color,
             background=(45, 51, 62)):
    pygame.draw.rect(
        surface, background, (x, y, w, h), border_radius=h // 2
    )
    fill = int(w * clamp(value / max(maximum, 1), 0, 1))
    if fill:
        pygame.draw.rect(
            surface, color, (x, y, fill, h), border_radius=h // 2
        )


def make_map():
    grid = [[1] * COLS for _ in range(ROWS)]

    # Main corridors
    for x in range(1, COLS - 1):
        grid[1][x] = 0
        grid[ROWS - 2][x] = 0

    for y in range(1, ROWS - 1):
        grid[y][1] = 0
        grid[y][COLS - 2] = 0

    for x in range(2, COLS - 2, 3):
        for y in range(1, ROWS - 1):
            grid[y][x] = 0

    for y in range(2, ROWS - 2, 3):
        for x in range(1, COLS - 1):
            grid[y][x] = 0

    # Connect nearby rooms and corridors
    for _ in range(30):
        x = random.randint(2, COLS - 3)
        y = random.randint(2, ROWS - 3)

        for xx in range(max(1, x - 1), min(COLS - 1, x + 2)):
            grid[y][xx] = 0

        for yy in range(max(1, y - 1), min(ROWS - 1, y + 2)):
            grid[yy][x] = 0

    return grid


class Button:
    def __init__(self, rect, label, action, hint=""):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.hint = hint

    def draw(self, surface, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)

        bg = (43, 53, 68) if hovered else C["panel2"]
        border = C["red"] if hovered else C["line"]

        panel(
            surface, self.rect, bg, border,
            8, 2 if hovered else 1
        )

        label = FONT.render(self.label, True, C["white"])
        surface.blit(label, label.get_rect(center=self.rect.center))

        if hovered and self.hint:
            draw_text(
                surface, self.hint,
                self.rect.x, self.rect.bottom + 5,
                C["muted"], TINY
            )

    def clicked(self, pos):
        return self.rect.collidepoint(pos)


class Game:
    def __init__(self):
        self.state = "menu"
        self.chapter = 0
        self.health = 100
        self.ammo = 30
        self.medkits = 2
        self.kills = 0
        self.flashlight = True
        self.sfx_on = True
        self.volume = 70
        self.notice = ""
        self.notice_time = 0
        self.menu_buttons = []
        self.pause_buttons = []
        self.settings_buttons = []
        self.choice = 0
        self.start_chapter(True)

    def say(self, message, seconds=2.5):
        self.notice = message
        self.notice_time = int(seconds * FPS)

    def floors(self):
        return [
            (x, y)
            for y in range(1, ROWS - 1)
            for x in range(1, COLS - 1)
            if self.grid[y][x] == 0
        ]

    def pick_floor(self, avoid=(), min_distance=0):
        candidates = [
            p for p in self.floors()
            if p not in avoid and distance(p, (1, 1)) >= min_distance
        ]
        return random.choice(candidates or self.floors())

    def start_chapter(self, reset_player=False):
        self.grid = make_map()
        self.player = [1.5 * TILE, 1.5 * TILE]

        self.key_tile = self.pick_floor(min_distance=4)
        self.terminal_tile = self.pick_floor(
            (self.key_tile,), min_distance=6
        )
        self.exit_tile = (COLS - 2, ROWS - 2)

        self.npc_tile = None
        if self.chapter == 2:
            self.npc_tile = self.pick_floor(
                (self.key_tile, self.terminal_tile, self.exit_tile),
                min_distance=4
            )

        self.has_key = False
        self.terminal_on = False
        self.enemies = []

        for _ in range(2 + self.chapter):
            p = self.pick_floor(
                (self.key_tile, self.terminal_tile, self.exit_tile),
                min_distance=6
            )
            self.enemies.append({
                "x": (p[0] + 0.5) * TILE,
                "y": (p[1] + 0.5) * TILE,
                "hp": 2 + self.chapter // 3,
                "cooldown": random.random()
            })

        self.boss = None

        if self.chapter == 4:
            p = self.pick_floor(
                (self.key_tile, self.terminal_tile, self.exit_tile),
                min_distance=9
            )
            self.boss = {
                "x": (p[0] + 0.5) * TILE,
                "y": (p[1] + 0.5) * TILE,
                "hp": 22,
                "max_hp": 22,
                "cooldown": 1.0
            }

        if reset_player:
            self.health = 100
            self.ammo = 30
            self.medkits = 2
            self.kills = 0

        self.say(
            f"CHAPTER {self.chapter + 1}: "
            f"{CHAPTERS[self.chapter][0]}"
        )

    def can_walk(self, x, y, radius=12):
        points = [
            (x - radius, y - radius),
            (x + radius, y - radius),
            (x - radius, y + radius),
            (x + radius, y + radius)
        ]

        for xx, yy in points:
            tx, ty = int(xx // TILE), int(yy // TILE)

            if not (0 <= tx < COLS and 0 <= ty < ROWS):
                return False

            if self.grid[ty][tx]:
                return False

        return True

    def move(self, dx, dy, dt):
        nx = self.player[0] + dx * 185 * dt
        ny = self.player[1] + dy * 185 * dt

        if self.can_walk(nx, self.player[1]):
            self.player[0] = nx

        if self.can_walk(self.player[0], ny):
            self.player[1] = ny

    def interact(self):
        p = (
            int(self.player[0] // TILE),
            int(self.player[1] // TILE)
        )

        if not self.has_key and distance(p, self.key_tile) < 1.3:
            self.has_key = True
            self.say("ACCESS KEY ACQUIRED")
            return

        if not self.terminal_on and distance(
            p, self.terminal_tile
        ) < 1.4:
            if self.chapter > 0 and not self.has_key:
                self.say("TERMINAL LOCKED — FIND THE ACCESS KEY")
                return

            self.terminal_on = True
            self.say("TERMINAL ONLINE — EXIT POWER RESTORED")
            return

        if self.npc_tile and distance(p, self.npc_tile) < 1.4:
            self.say(
                "SURVIVOR: The exit is marked. Don't stop moving."
            )
            return

        if distance(p, self.exit_tile) < 1.35:
            if self.boss and self.boss["hp"] > 0:
                self.say("LIFT SEALED — DEFEAT THE WARDEN")
            elif not self.has_key:
                self.say("EXIT LOCKED — FIND THE ACCESS KEY")
            elif not self.terminal_on:
                self.say("POWER OFFLINE — ACTIVATE THE TERMINAL")
            else:
                self.chapter += 1

                if self.chapter >= len(CHAPTERS):
                    self.state = "ending"
                    self.choice = 0
                else:
                    self.start_chapter()

            return

        self.say("NO INTERACTION NEARBY", 1.0)

    def shoot(self):
        if self.ammo <= 0:
            self.say("OUT OF AMMO")
            return

        self.ammo -= 1
        targets = self.enemies[:]

        if self.boss and self.boss["hp"] > 0:
            targets.append(self.boss)

        if not targets:
            self.say("NO HOSTILE TARGET", 0.7)
            return

        target = min(
            targets,
            key=lambda e: distance(
                self.player, (e["x"], e["y"])
            )
        )

        if distance(
            self.player, (target["x"], target["y"])
        ) > 270:
            self.say("TARGET OUT OF RANGE", 0.7)
            return

        target["hp"] -= 1

        if target is self.boss:
            self.say("WARDEN HIT", 0.5)

        elif target["hp"] <= 0:
            self.enemies.remove(target)
            self.kills += 1
            self.say("HOSTILE NEUTRALIZED", 0.7)

        else:
            self.say("HIT CONFIRMED", 0.5)

    def save(self):
        data = {
            "chapter": self.chapter,
            "health": self.health,
            "ammo": self.ammo,
            "medkits": self.medkits,
            "kills": self.kills,
            "volume": self.volume,
            "sfx_on": self.sfx_on
        }

        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)

            self.say("GAME SAVED SUCCESSFULLY")

        except OSError:
            self.say("SAVE FAILED — CHECK FILE PERMISSIONS")

    def load(self):
        if not os.path.exists(SAVE_FILE):
            self.say("NO SAVE FILE FOUND")
            return

        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)

            self.chapter = clamp(
                int(data.get("chapter", 0)),
                0, len(CHAPTERS) - 1
            )
            self.health = clamp(
                int(data.get("health", 100)), 1, 100
            )
            self.ammo = max(0, int(data.get("ammo", 30)))
            self.medkits = max(0, int(data.get("medkits", 2)))
            self.kills = max(0, int(data.get("kills", 0)))
            self.volume = clamp(
                int(data.get("volume", 70)), 0, 100
            )
            self.sfx_on = bool(data.get("sfx_on", True))

            self.start_chapter()
            self.state = "playing"
            self.say("SAVE LOADED — CHAPTER RESTARTED")

        except (OSError, ValueError, json.JSONDecodeError):
            self.say("SAVE FILE COULD NOT BE READ")

    def update(self, dt):
        if self.notice_time > 0:
            self.notice_time -= 1

        px, py = self.player

        for enemy in self.enemies:
            d = distance(
                (px, py), (enemy["x"], enemy["y"])
            )
            enemy["cooldown"] -= dt

            if d < 310:
                if d > 28:
                    vx = (px - enemy["x"]) / max(d, 1)
                    vy = (py - enemy["y"]) / max(d, 1)

                    nx = enemy["x"] + vx * (
                        70 + self.chapter * 7
                    ) * dt
                    ny = enemy["y"] + vy * (
                        70 + self.chapter * 7
                    ) * dt

                    if self.can_walk(nx, ny):
                        enemy["x"], enemy["y"] = nx, ny

                elif enemy["cooldown"] <= 0:
                    self.health -= 8
                    enemy["cooldown"] = 1.0
                    self.say("YOU HAVE BEEN HIT", 0.6)

        if self.boss and self.boss["hp"] > 0:
            boss = self.boss
            d = distance(
                (px, py), (boss["x"], boss["y"])
            )
            boss["cooldown"] -= dt

            if d > 46:
                vx = (px - boss["x"]) / max(d, 1)
                vy = (py - boss["y"]) / max(d, 1)

                nx = boss["x"] + vx * 58 * dt
                ny = boss["y"] + vy * 58 * dt

                if self.can_walk(nx, ny, 17):
                    boss["x"], boss["y"] = nx, ny

            elif boss["cooldown"] <= 0:
                self.health -= 15
                boss["cooldown"] = 1.25
                self.say("WARDEN STRIKE", 0.7)

        self.health = clamp(self.health, 0, 100)

        if self.health <= 0:
            self.state = "gameover"

    def draw_world(self):
        screen.fill(C["bg"])

        camx = clamp(
            self.player[0] - WIDTH / 2,
            0, COLS * TILE - WIDTH
        )
        camy = clamp(
            self.player[1] - HEIGHT / 2,
            0, ROWS * TILE - HEIGHT
        )

        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                rect = pygame.Rect(
                    int(x * TILE - camx),
                    int(y * TILE - camy),
                    TILE, TILE
                )

                color = C["wall"] if cell else C["floor"]
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (31, 40, 50), rect, 1)

        def pos(tile):
            return (
                int((tile[0] + 0.5) * TILE - camx),
                int((tile[1] + 0.5) * TILE - camy)
            )

        if not self.has_key:
            pygame.draw.circle(
                screen, C["yellow"], pos(self.key_tile), 10
            )

        if not self.terminal_on:
            tx, ty = pos(self.terminal_tile)
            pygame.draw.rect(
                screen, C["blue"], (tx, ty, 18, 18)
            )

        if self.npc_tile:
            pygame.draw.circle(
                screen, C["green"], pos(self.npc_tile), 11
            )

        ex, ey = pos(self.exit_tile)
        pygame.draw.rect(
            screen, (130, 91, 51),
            (ex - 15, ey - 15, 30, 30),
            border_radius=4
        )

        for enemy in self.enemies:
            ep = (
                int(enemy["x"] - camx),
                int(enemy["y"] - camy)
            )
            pygame.draw.circle(screen, C["red"], ep, 14)
            pygame.draw.circle(screen, C["red_dark"], ep, 6)

        if self.boss and self.boss["hp"] > 0:
            bp = (
                int(self.boss["x"] - camx),
                int(self.boss["y"] - camy)
            )
            pygame.draw.circle(screen, C["purple"], bp, 25)
            pygame.draw.circle(screen, C["red"], bp, 9)

        player_pos = (
            int(self.player[0] - camx),
            int(self.player[1] - camy)
        )
        pygame.draw.circle(screen, C["blue"], player_pos, 12)

        if self.flashlight:
            overlay = pygame.Surface(
                (WIDTH, HEIGHT), pygame.SRCALPHA
            )
            overlay.fill((0, 0, 0, 130))
            pygame.draw.circle(
                overlay, (0, 0, 0, 0),
                (WIDTH // 2, HEIGHT // 2), 170
            )
            screen.blit(overlay, (0, 0))

        self.draw_hud()

        if self.notice_time > 0:
            panel(
                screen,
                (130, HEIGHT - 61, WIDTH - 260, 42),
                (8, 12, 19), C["line"], 8
            )
            draw_text(
                screen, self.notice, 148, HEIGHT - 49,
                C["white"], SMALL
            )

    def draw_hud(self):
        pygame.draw.rect(screen, (10, 14, 21), (0, 0, WIDTH, 92))
        pygame.draw.line(
            screen, C["line"], (0, 91), (WIDTH, 91), 1
        )

        draw_text(
            screen, f"CHAPTER {self.chapter + 1:02}/05",
            20, 12, C["yellow"], SMALL
        )
        draw_text(
            screen, CHAPTERS[self.chapter][0],
            20, 34, C["white"], SUBTITLE
        )

        draw_text(screen, "OBJECTIVE", 430, 12, C["muted"], TINY)
        draw_text(
            screen, CHAPTERS[self.chapter][1],
            430, 34, C["white"], SMALL
        )

        draw_text(
            screen, f"HP {self.health:03}",
            810, 12, C["white"], SMALL
        )
        health_color = (
            C["green"] if self.health > 35 else C["red"]
        )
        draw_bar(
            screen, 810, 36, 118, 9,
            self.health, 100, health_color
        )

        draw_text(
            screen, f"AMMO {self.ammo:02}",
            945, 12, C["white"], SMALL
        )
        draw_text(
            screen,
            f"MED {self.medkits}  |  KILLS {self.kills}",
            810, 58, C["muted"], TINY
        )

        if self.boss and self.boss["hp"] > 0:
            draw_text(
                screen, "WARDEN",
                WIDTH // 2 - 38, 100, C["red"], SMALL
            )
            draw_bar(
                screen, WIDTH // 2 - 145, 121, 290, 10,
                self.boss["hp"], self.boss["max_hp"], C["red"]
            )

    def draw_menu(self, mouse_pos):
        screen.fill(C["bg"])

        for y in range(0, HEIGHT, 5):
            pygame.draw.line(
                screen, (10, 14, 21), (0, y), (WIDTH, y), 1
            )

        pygame.draw.circle(
            screen, (24, 18, 28), (WIDTH - 150, 170), 210
        )
        pygame.draw.circle(
            screen, (45, 18, 28), (WIDTH - 150, 170), 155, 2
        )
        pygame.draw.line(
            screen, C["red"], (70, 145), (170, 145), 4
        )

        draw_text(screen, "SILENT", 70, 160, C["white"], TITLE)
        draw_text(screen, "SIGNAL", 70, 213, C["red"], TITLE)
        draw_text(
            screen, "SURVIVE THE DARK. FIND THE TRUTH.",
            74, 282, C["muted"], SMALL
        )
        draw_text(
            screen, "SURVIVAL HORROR  /  STORY CAMPAIGN",
            74, 316, C["muted"], TINY
        )

        self.menu_buttons = [
            Button(
                (74, 390, 260, 48),
                "NEW GAME", "new", "Start a new story"
            ),
            Button(
                (74, 450, 260, 48),
                "CONTINUE / LOAD", "load", "Load saved chapter"
            ),
            Button(
                (74, 510, 260, 48),
                "SETTINGS", "settings", "Audio and display options"
            ),
            Button(
                (74, 570, 260, 48),
                "QUIT GAME", "quit", "Close Silent Signal"
            )
        ]

        for button in self.menu_buttons:
            button.draw(screen, mouse_pos)

        panel(
            screen, (620, 365, 395, 245),
            (14, 20, 29), C["line"], 12
        )
        draw_text(
            screen, "FIELD GUIDE", 648, 389,
            C["yellow"], SUBTITLE
        )

        controls = [
            "WASD / ARROWS   Move",
            "E               Interact",
            "SPACE           Fire weapon",
            "H               Use medkit",
            "F               Flashlight",
            "F5              Save game",
            "ESC             Pause"
        ]

        for i, line in enumerate(controls):
            draw_text(
                screen, line, 650, 431 + i * 23,
                C["white"], SMALL
            )

        draw_text(
            screen, "BUILD 1.4  |  SINGLE PLAYER",
            74, 655, C["muted"], TINY
        )

    def draw_pause(self, mouse_pos):
        self.draw_world()

        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((2, 4, 8, 205))
        screen.blit(shade, (0, 0))

        panel(
            screen, (WIDTH // 2 - 220, 125, 440, 465),
            (13, 19, 28), C["line"], 16, 2
        )

        draw_text(
            screen, "PAUSED", WIDTH // 2 - 91, 158,
            C["white"], TITLE
        )
        draw_text(
            screen, "YOUR SIGNAL IS ON HOLD",
            WIDTH // 2 - 112, 218, C["muted"], TINY
        )

        self.pause_buttons = [
            Button(
                (WIDTH // 2 - 150, 270, 300, 48),
                "RESUME", "resume"
            ),
            Button(
                (WIDTH // 2 - 150, 330, 300, 48),
                "SAVE GAME", "save"
            ),
            Button(
                (WIDTH // 2 - 150, 390, 300, 48),
                "SETTINGS", "settings"
            ),
            Button(
                (WIDTH // 2 - 150, 450, 300, 48),
                "MAIN MENU", "menu"
            )
        ]

        for button in self.pause_buttons:
            button.draw(screen, mouse_pos)

        draw_text(
            screen, "Press ESC to resume",
            WIDTH // 2 - 76, 540, C["muted"], SMALL
        )

    def draw_settings(self, mouse_pos):
        screen.fill(C["bg"])

        panel(
            screen, (WIDTH // 2 - 300, 95, 600, 510),
            (14, 20, 29), C["line"], 16, 2
        )

        draw_text(
            screen, "SETTINGS", WIDTH // 2 - 120, 125,
            C["white"], TITLE
        )
        draw_text(
            screen, "Audio options",
            WIDTH // 2 - 220, 215, C["yellow"], SUBTITLE
        )
        draw_text(
            screen, "Sound effects",
            WIDTH // 2 - 220, 265, C["white"]
        )

        draw_text(
            screen, "ON" if self.sfx_on else "OFF",
            WIDTH // 2 + 125, 265,
            C["green"] if self.sfx_on else C["red"]
        )

        draw_text(
            screen, "Master volume",
            WIDTH // 2 - 220, 315, C["white"]
        )
        draw_bar(
            screen, WIDTH // 2 - 220, 352, 360, 14,
            self.volume, 100, C["blue"]
        )
        draw_text(
            screen, f"{self.volume}%",
            WIDTH // 2 + 160, 345, C["white"], SMALL
        )

        self.settings_buttons = [
            Button(
                (WIDTH // 2 + 90, 250, 130, 42),
                "TOGGLE SFX", "sfx"
            ),
            Button(
                (WIDTH // 2 - 220, 390, 60, 42),
                "-", "vol_down"
            ),
            Button(
                (WIDTH // 2 + 80, 390, 60, 42),
                "+", "vol_up"
            ),
            Button(
                (WIDTH // 2 - 100, 490, 200, 48),
                "BACK", "back"
            )
        ]

        for button in self.settings_buttons:
            button.draw(screen, mouse_pos)

        draw_text(
            screen, "Use +/- to change the stored volume level.",
            WIDTH // 2 - 220, 430, C["muted"], SMALL
        )
        draw_text(
            screen,
            "Volume is stored in settings; no music file is bundled.",
            WIDTH // 2 - 220, 462, C["muted"], TINY
        )

    def handle_button(self, action):
        if action == "new":
            self.chapter = 0
            self.start_chapter(True)
            self.state = "playing"

        elif action == "load":
            self.load()

        elif action == "settings":
            self.previous_state = self.state
            self.state = "settings"

        elif action == "quit":
            self.state = "quit"

        elif action == "resume":
            self.state = "playing"

        elif action == "save":
            self.save()

        elif action == "menu":
            self.state = "menu"

        elif action == "back":
            self.state = getattr(self, "previous_state", "menu")

        elif action == "sfx":
            self.sfx_on = not self.sfx_on

        elif action == "vol_down":
            self.volume = clamp(self.volume - 10, 0, 100)

        elif action == "vol_up":
            self.volume = clamp(self.volume + 10, 0, 100)


game = Game()
running = True

while running:
    dt = min(clock.tick(FPS) / 1000.0, 0.04)
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            buttons = []

            if game.state == "menu":
                buttons = game.menu_buttons
            elif game.state == "pause":
                buttons = game.pause_buttons
            elif game.state == "settings":
                buttons = game.settings_buttons

            for button in buttons:
                if button.clicked(event.pos):
                    game.handle_button(button.action)
                    break

        elif event.type == pygame.KEYDOWN:
            if game.state == "menu":
                if event.key == pygame.K_RETURN:
                    game.handle_button("new")
                elif event.key == pygame.K_l:
                    game.handle_button("load")
                elif event.key == pygame.K_ESCAPE:
                    running = False

            elif game.state == "playing":
                if event.key == pygame.K_ESCAPE:
                    game.state = "pause"

                elif event.key == pygame.K_e:
                    game.interact()

                elif event.key == pygame.K_SPACE:
                    game.shoot()

                elif event.key == pygame.K_f:
                    game.flashlight = not game.flashlight

                elif event.key == pygame.K_F5:
                    game.save()

                elif event.key == pygame.K_h:
                    if game.medkits > 0 and game.health < 100:
                        game.medkits -= 1
                        game.health = min(100, game.health + 35)
                        game.say("MEDKIT USED  +35 HP")
                    else:
                        game.say("NO MEDKIT AVAILABLE")

            elif game.state == "pause":
                if event.key == pygame.K_ESCAPE:
                    game.state = "playing"

            elif game.state == "settings":
                if event.key == pygame.K_ESCAPE:
                    game.state = getattr(
                        game, "previous_state", "menu"
                    )

            elif game.state == "ending":
                if event.key in (pygame.K_1, pygame.K_2):
                    game.choice = (
                        1 if event.key == pygame.K_1 else 2
                    )

                elif (
                    event.key == pygame.K_RETURN
                    and game.choice
                ):
                    game.state = "menu"

            elif game.state == "gameover":
                if event.key == pygame.K_RETURN:
                    game.state = "menu"

                elif event.key == pygame.K_r:
                    game.chapter = 0
                    game.start_chapter(True)
                    game.state = "playing"

    if game.state == "playing":
        keys = pygame.key.get_pressed()

        dx = (
            int(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        )
        dy = (
            int(keys[pygame.K_s] or keys[pygame.K_DOWN])
            - int(keys[pygame.K_w] or keys[pygame.K_UP])
        )

        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071

        game.move(dx, dy, dt)
        game.update(dt)
        game.draw_world()

    elif game.state == "menu":
        game.draw_menu(mouse_pos)

    elif game.state == "pause":
        game.draw_pause(mouse_pos)

    elif game.state == "settings":
        game.draw_settings(mouse_pos)

    elif game.state == "ending":
        screen.fill(C["bg"])

        draw_text(
            screen, "SIGNAL RESTORED",
            WIDTH // 2 - 230, 150, C["green"], TITLE
        )
        draw_text(
            screen, "Choose the facility's fate",
            WIDTH // 2 - 150, 245, C["white"], SUBTITLE
        )
        draw_text(
            screen, "1 — Send distress signal and save survivors",
            WIDTH // 2 - 240, 320, C["yellow"]
        )
        draw_text(
            screen, "2 — Destroy the facility and end the threat",
            WIDTH // 2 - 240, 365, C["red"]
        )

        if game.choice:
            if game.choice == 1:
                outcome = "Rescue signal sent. Help is on the way."
            else:
                outcome = "Facility destroyed. The threat is gone."

            draw_text(
                screen, outcome, WIDTH // 2 - 190, 445,
                C["green"], SMALL
            )
            draw_text(
                screen, "Press ENTER to return to menu",
                WIDTH // 2 - 130, 500, C["muted"], SMALL
            )

    elif game.state == "gameover":
        screen.fill(C["bg"])

        draw_text(
            screen, "SIGNAL LOST",
            WIDTH // 2 - 165, 200, C["red"], TITLE
        )
        draw_text(
            screen, "The facility has claimed another victim.",
            WIDTH // 2 - 180, 280, C["muted"]
        )
        draw_text(
            screen, "ENTER — Main menu     R — Restart",
            WIDTH // 2 - 190, 365, C["white"], SMALL
        )
    elif game.state == "quit":
        running = False

    pygame.display.flip()

pygame.quit()
gfnhbjm