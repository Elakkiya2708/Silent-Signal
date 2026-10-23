
import os
import json
import math
import random
import pygame

pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

# =====================================================
# SILENT SIGNAL - ADVANCED HORROR SURVIVAL
# =====================================================

W, H = 1100, 700
TILE, FPS = 50, 60
COLS, ROWS = 22, 14
SAVE_FILE = "silent_signal_save.json"

screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("SILENT SIGNAL - Nightmare Protocol")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("consolas", 19)
SMALL = pygame.font.SysFont("consolas", 14)
TITLE = pygame.font.SysFont("georgia", 62, bold=True)
RED = (205, 30, 42)
WHITE = (235, 235, 235)
GREEN = (65, 210, 125)
BLACK = (5, 6, 9)

def draw_text(surface, value, font, color, x, y, center=False):
    image = font.render(str(value), True, color)
    rect = image.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(image, rect)

def dist(x1, y1, x2, y2):
    return math.hypot(x1 - x2, y1 - y2)

def load_sfx(filename):
    path = os.path.join("assets", filename)
    try:
        if pygame.mixer.get_init() and os.path.exists(path):
            return pygame.mixer.Sound(path)
    except pygame.error:
        pass
    return None

SFX = {
    "shot": load_sfx("shot.wav"),
    "hit": load_sfx("hit.wav"),
    "scare": load_sfx("jumpscare.wav"),
    "boss": load_sfx("boss.wav"),
}

def play_sfx(name):
    sound = SFX.get(name)
    if sound:
        try:
            sound.play()
        except pygame.error:
            pass

# =====================================================
# MAPS
# # = wall, P = player, E = enemy, K = key, X = exit
# =====================================================

MAPS = [
[
"######################",
"#P....#..............#",
"#.##..#.####.#####...#",
"#.....#......#.......#",
"###.######.#.#.####..#",
"#..........#.#.......#",
"#.##########.#######.#",
"#..........E........#",
"#.####.###########..#",
"#......#............#",
"#.####.#.##########..#",
"#....K.#..........X.#",
"#...................#",
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
"#...........K.....X..#",
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
"#.........K........X.#",
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
"#....K.....#.......X.#",
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
"#....K.............X.#",
"#....................#",
"######################",
]
]

MAPS = [[row.ljust(COLS, "#")[:COLS] for row in layout]
        for layout in MAPS]

CHAPTER_NAMES = [
    "ABANDONED HOSPITAL",
    "SILENT SCHOOL",
    "FORGOTTEN BASEMENT",
    "BLOOD MOON FOREST",
    "THE SIGNAL SOURCE",
]

MISSIONS = [
    "Find the exit. Eliminate the entity.",
    "Recover the key and survive the hunt.",
    "Investigate the basement and escape.",
    "Defeat the hunter and reach the exit.",
    "Destroy the source. Defeat THE SIGNAL.",
]

# =====================================================
# GAME
# =====================================================

class Game:
    def __init__(self):
        self.state = "menu"
        self.settings = {"flashlight": True, "shake": True}
        self.reset()

    def reset(self):
        self.chapter = 0
        self.health = 100
        self.ammo = 20
        self.medkits = 3
        self.score = 0
        self.kills = 0
        self.has_key = False
        self.flashlight = True
        self.light_energy = 100
        self.shake = 0
        self.blood = 0
        self.scare_timer = 0
        self.message = ""
        self.message_timer = 0
        self.bullets = []
        self.particles = []
        self.load_chapter(0)

    def say(self, msg):
        self.message = msg
        self.message_timer = 150

    def load_chapter(self, index):
        self.chapter = index
        self.walls = set()
        self.items = []
        self.has_key = False
        self.bullets = []
        self.particles = []

        layout = MAPS[index]
        self.exit_tile = (COLS - 2, ROWS - 3)
        self.player_x = TILE * 1.5
        self.player_y = TILE * 1.5

        for y, row in enumerate(layout):
            for x, ch in enumerate(row):
                if ch == "#":
                    self.walls.add((x, y))
                elif ch == "P":
                    self.player_x = x * TILE + TILE / 2
                    self.player_y = y * TILE + TILE / 2
                elif ch == "E":
                    self.enemy = {
                        "x": x * TILE + TILE / 2,
                        "y": y * TILE + TILE / 2,
                        "hp": 100 + index * 20,
                        "maxhp": 100 + index * 20,
                        "alive": True,
                        "mode": "patrol",
                        "patrol_x": x * TILE + TILE / 2,
                        "patrol_y": y * TILE + TILE / 2,
                        "attack_cd": 0,
                        "special_cd": 100,
                    }
                elif ch == "K":
                    self.items.append({
                        "type": "key",
                        "x": x * TILE + TILE / 2,
                        "y": y * TILE + TILE / 2,
                    })
                elif ch == "X":
                    self.exit_tile = (x, y)

        self.boss = index == 4
        if self.boss:
            self.enemy["hp"] = 450
            self.enemy["maxhp"] = 450
            self.enemy["speed"] = 1.65
            self.say("FINAL MISSION: DESTROY THE SIGNAL")
        else:
            self.enemy["speed"] = 1.0 + index * 0.15
            self.say(CHAPTER_NAMES[index])

    def tile(self, x, y):
        return int(x // TILE), int(y // TILE)

    def wall_at(self, x, y):
        return self.tile(x, y) in self.walls

    def can_move(self, x, y):
        r = 12
        return not any(
            self.wall_at(x + dx, y + dy)
            for dx, dy in [(-r, 0), (r, 0), (0, -r), (0, r)]
        )

    def move_entity(self, entity, tx, ty, speed):
        dx, dy = tx - entity["x"], ty - entity["y"]
        d = max(1, math.hypot(dx, dy))
        nx = entity["x"] + dx / d * speed
        ny = entity["y"] + dy / d * speed

        if self.can_move(nx, entity["y"]):
            entity["x"] = nx
        if self.can_move(entity["x"], ny):
            entity["y"] = ny

    def line_of_sight(self, x1, y1, x2, y2):
        d = dist(x1, y1, x2, y2)
        steps = max(1, int(d / 10))
        for i in range(1, steps):
            t = i / steps
            x = x1 + (x2 - x1) * t
            y = y1 + (y2 - y1) * t
            if self.wall_at(x, y):
                return False
        return True

    # Gunshots make enemies investigate the shot location.
    def shoot(self):
        if self.ammo <= 0:
            self.say("OUT OF AMMO!")
            return

        self.ammo -= 1
        play_sfx("shot")

        # Shot noise alerts the enemy, even if it cannot see the player.
        self.enemy["mode"] = "investigate"
        self.enemy["target_x"] = self.player_x
        self.enemy["target_y"] = self.player_y

        e = self.enemy
        d = dist(self.player_x, self.player_y, e["x"], e["y"])

        if e["alive"] and d < 330 and self.line_of_sight(
            self.player_x, self.player_y, e["x"], e["y"]
        ):
            damage = random.randint(28, 42)
            e["hp"] -= damage
            self.score += 10
            self.shake = 5
            self.say(f"HIT! -{damage} HP")
            self.spawn_particles(e["x"], e["y"], RED, 10)

            if e["hp"] <= 0:
                e["alive"] = False
                self.kills += 1
                self.score += 150 if self.boss else 100
                self.say("BOSS DESTROYED!" if self.boss else "ENTITY ELIMINATED")
                self.spawn_particles(e["x"], e["y"], (255, 80, 50), 30)
        else:
            self.say("SHOT MISSED - ENTITY ALERTED")

    def spawn_particles(self, x, y, color, amount):
        for _ in range(amount):
            self.particles.append({
                "x": x, "y": y,
                "vx": random.uniform(-3, 3),
                "vy": random.uniform(-3, 3),
                "life": random.randint(15, 40),
                "color": color,
            })

    def update_particles(self):
        for p in self.particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            if p["life"] <= 0:
                self.particles.remove(p)

    def interact(self):
        px, py = self.player_x, self.player_y

        for item in self.items[:]:
            if dist(px, py, item["x"], item["y"]) < 42:
                if item["type"] == "key":
                    self.has_key = True
                    self.items.remove(item)
                    self.say("KEY ACQUIRED - FIND THE EXIT")
                    self.score += 50
                    return

        tx, ty = self.tile(px, py)
        ex, ey = self.exit_tile

        if abs(tx - ex) <= 1 and abs(ty - ey) <= 1:
            if self.enemy["alive"]:
                self.say("DEFEAT THE ENTITY FIRST!")
            elif not self.has_key:
                self.say("LOCKED! FIND THE KEY!")
            elif self.chapter < 4:
                self.load_chapter(self.chapter + 1)
            else:
                self.state = "ending"
            return

        self.say("NOTHING TO INTERACT WITH")

    def heal(self):
        if self.medkits > 0 and self.health < 100:
            self.medkits -= 1
            self.health = min(100, self.health + 40)
            self.say("HEALTH RESTORED")
        else:
            self.say("NO MEDKITS OR HEALTH IS FULL")

    # Advanced enemy states:
    # patrol -> investigate -> chase -> attack
    def update_enemy(self):
        e = self.enemy
        if not e["alive"]:
            return

        px, py = self.player_x, self.player_y
        d = dist(px, py, e["x"], e["y"])
        visible = self.line_of_sight(px, py, e["x"], e["y"])

        if e["attack_cd"] > 0:
            e["attack_cd"] -= 1
        if e["special_cd"] > 0:
            e["special_cd"] -= 1

        if visible and d < (540 if self.boss else 350):
            e["mode"] = "chase"
            e["target_x"], e["target_y"] = px, py

        if e["mode"] == "patrol":
            tx, ty = e["patrol_x"], e["patrol_y"]
            if dist(e["x"], e["y"], tx, ty) < 20:
                e["patrol_x"] = clamp(
                    e["x"] + random.randint(-140, 140), TILE, W - TILE
                )
                e["patrol_y"] = clamp(
                    e["y"] + random.randint(-140, 140), TILE, H - TILE
                )
            self.move_entity(e, e["patrol_x"], e["patrol_y"], 0.55)

        elif e["mode"] == "investigate":
            tx = e.get("target_x", px)
            ty = e.get("target_y", py)
            self.move_entity(e, tx, ty, 1.2)
            if dist(e["x"], e["y"], tx, ty) < 25:
                e["mode"] = "patrol"

        elif e["mode"] == "chase":
            speed = (1.65 if self.boss else 1.0 + self.chapter * 0.15)
            if self.boss and e["hp"] < e["maxhp"] * 0.5:
                speed *= 1.45
            self.move_entity(e, px, py, speed)

        # Normal melee attack.
        if d < 34 and e["attack_cd"] == 0:
            damage = 14 if not self.boss else 22
            self.health -= damage
            self.blood = 18
            self.shake = 12
            e["attack_cd"] = 55
            play_sfx("hit")
            self.say(f"YOU TOOK {damage} DAMAGE!")

        # Boss special attack: red pulse damages the player at range.
        if self.boss and d < 230 and e["special_cd"] == 0:
            self.say("BOSS SPECIAL ATTACK!")
            self.shake = 15
            self.spawn_particles(e["x"], e["y"], RED, 35)

            if self.line_of_sight(px, py, e["x"], e["y"]):
                self.health -= 18
                self.blood = 25

            e["special_cd"] = 150
            play_sfx("boss")

        # Random jumpscare when the enemy gets very close.
        now = pygame.time.get_ticks()
        if d < 100 and now - self.last_scare > 12000:
            self.scare_timer = 35
            self.last_scare = now
            play_sfx("scare")

        if self.health <= 0:
            self.health = 0
            self.state = "gameover"

    def save(self):
        data = {
            "chapter": self.chapter,
            "health": self.health,
            "ammo": self.ammo,
            "medkits": self.medkits,
            "score": self.score,
            "kills": self.kills,
        }
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.say("GAME SAVED")
        except OSError:
            self.say("SAVE FAILED")

    def load(self):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            ch = int(data.get("chapter", 0))
            if not 0 <= ch <= 4:
                raise ValueError("Invalid chapter")

            self.load_chapter(ch)
            self.health = clamp(int(data.get("health", 100)), 1, 100)
            self.ammo = max(0, int(data.get("ammo", 20)))
            self.medkits = max(0, int(data.get("medkits", 3)))
            self.score = max(0, int(data.get("score", 0)))
            self.kills = max(0, int(data.get("kills", 0)))
            self.state = "playing"
            self.say("GAME LOADED")
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.say("NO VALID SAVE FOUND")

    def update(self):
        self.shake = max(0, self.shake - 1)
        self.blood = max(0, self.blood - 1)
        self.scare_timer = max(0, self.scare_timer - 1)
        self.message_timer = max(0, self.message_timer - 1)

        self.update_particles()

        if self.state != "playing":
            return

        keys = pygame.key.get_pressed()
        dx = dy = 0
        speed = 3

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += speed

        if dx and dy:
            dx *= 0.707
            dy *= 0.707

        if self.can_move(self.player_x + dx, self.player_y):
            self.player_x += dx
        if self.can_move(self.player_x, self.player_y + dy):
            self.player_y += dy

        if self.flashlight:
            self.light_energy = max(0, self.light_energy - 0.02)
            if self.light_energy == 0:
                self.flashlight = False
                self.say("FLASHLIGHT BATTERY EMPTY")
        else:
            self.light_energy = min(100, self.light_energy + 0.05)

        self.update_enemy()

    # =================================================
    # RENDERING
    # =================================================

    def draw_world(self):
        screen.fill((8, 10, 13))

        ox = random.randint(-self.shake, self.shake) if self.shake and self.settings["shake"] else 0
        oy = random.randint(-self.shake, self.shake) if self.shake and self.settings["shake"] else 0

        cam_x = clamp(self.player_x - W // 2, 0, COLS * TILE - W)
        cam_y = clamp(self.player_y - H // 2, 0, ROWS * TILE - H)

        for y in range(ROWS):
            for x in range(COLS):
                rect = pygame.Rect(
                    x * TILE - cam_x + ox,
                    y * TILE - cam_y + oy, TILE, TILE
                )
                if (x, y) in self.walls:
                    pygame.draw.rect(screen, (25, 29, 34), rect)
                    pygame.draw.rect(screen, (43, 46, 51), rect, 2)
                else:
                    pygame.draw.rect(screen, (13, 16, 19), rect)
                    pygame.draw.line(
                        screen, (20, 23, 26),
                        rect.topleft, rect.bottomright, 1
                    )

        # Exit.
        ex, ey = self.exit_tile
        er = pygame.Rect(ex * TILE - cam_x + ox,
                         ey * TILE - cam_y + oy, TILE, TILE)
        pygame.draw.rect(screen, (45, 10, 16), er)
        pygame.draw.rect(screen, RED if self.has_key else (110, 60, 35), er, 3)
        draw_text(screen, "X", FONT, WHITE, er.centerx, er.centery, True)

        # Key pickups.
        for item in self.items:
            ix = int(item["x"] - cam_x + ox)
            iy = int(item["y"] - cam_y + oy)
            pygame.draw.circle(screen, (240, 200, 40), (ix, iy), 9)
            pygame.draw.circle(screen, (255, 245, 130), (ix, iy), 4)

        # Enemy and boss.
        e = self.enemy
        if e["alive"]:
            exs = int(e["x"] - cam_x + ox)
            eys = int(e["y"] - cam_y + oy)
            size = 29 if self.boss else 18

            pygame.draw.ellipse(
                screen, (75, 4, 12),
                (exs - size, eys - size, size * 2, size * 2)
            )
            pygame.draw.circle(screen, (255, 0, 12), (exs - 7, eys - 4), 4)
            pygame.draw.circle(screen, (255, 0, 12), (exs + 7, eys - 4), 4)

            # Enemy health bar.
            bar_w = 95 if self.boss else 55
            bx = exs - bar_w // 2
            by = eys - size - 17
            pygame.draw.rect(screen, (45, 10, 10), (bx, by, bar_w, 7))
            pygame.draw.rect(
                screen, RED,
                (bx, by, int(bar_w * max(0, e["hp"]) / e["maxhp"]), 7)
            )

            if self.boss:
                draw_text(screen, "THE SIGNAL", SMALL, RED, exs, by - 19, True)

        # Player.
        px = int(self.player_x - cam_x + ox)
        py = int(self.player_y - cam_y + oy)
        pygame.draw.circle(screen, (175, 185, 185), (px, py), 12)
        pygame.draw.circle(screen, WHITE, (px + 4, py - 3), 3)

        # Particles.
        for p in self.particles:
            pygame.draw.circle(
                screen, p["color"],
                (int(p["x"] - cam_x + ox), int(p["y"] - cam_y + oy)),
                max(1, p["life"] // 8)
            )

        self.draw_darkness(px, py)
        self.draw_hud()

    def draw_darkness(self, px, py):
        darkness = pygame.Surface((W, H), pygame.SRCALPHA)
        darkness.fill((0, 0, 0, 220))

        if self.settings["flashlight"] and self.flashlight:
            radius = max(45, int(175 * self.light_energy / 100))
            mask = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.circle(mask, (0, 0, 0, 0), (px, py), radius)
            darkness.blit(mask, (0, 0),
                          special_flags=pygame.BLEND_RGBA_MIN)

        screen.blit(darkness, (0, 0))

        # Edge vignette.
        for i in range(7):
            margin = i * 24
            pygame.draw.rect(
                screen, (0, 0, 0, 0),
                (margin, margin, W - margin * 2, H - margin * 2), 1
            )

        if self.blood > 0:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((130, 0, 10, min(120, self.blood * 5)))
            screen.blit(overlay, (0, 0))

    def draw_hud(self):
        pygame.draw.rect(screen, (7, 9, 12), (0, 0, W, 88))
        pygame.draw.line(screen, (100, 20, 30), (0, 87), (W, 87), 2)

        draw_text(screen, "SILENT SIGNAL", FONT, WHITE, 15, 10)
        draw_text(screen, f"CHAPTER {self.chapter + 1}/5",
                  SMALL, RED, 15, 42)

        draw_text(screen, "HP", SMALL, WHITE, 240, 17)
        pygame.draw.rect(screen, (55, 15, 18), (270, 18, 145, 14))
        pygame.draw.rect(
            screen, RED, (270, 18, int(145 * self.health / 100), 14)
        )

        draw_text(screen, f"AMMO {self.ammo}", SMALL, WHITE, 440, 16)
        draw_text(screen, f"MEDKITS {self.medkits}", SMALL, GREEN, 440, 43)
        draw_text(screen, f"SCORE {self.score}", SMALL,
                  (225, 190, 85), 570, 16)

        draw_text(screen, "KEY: " + ("YES" if self.has_key else "NO"),
                  SMALL, (240, 200, 80), 700, 16)

        draw_text(screen, "LIGHT", SMALL, WHITE, 830, 16)
        pygame.draw.rect(screen, (40, 40, 40), (890, 18, 125, 12))
        pygame.draw.rect(
            screen, GREEN if self.light_energy > 30 else RED,
            (890, 18, int(125 * self.light_energy / 100), 12)
        )

        draw_text(screen, "WASD MOVE | SPACE SHOOT | E INTERACT",
                  SMALL, (160, 165, 170), 240, 53)
        draw_text(screen, "F LIGHT | H HEAL | F5 SAVE | ESC PAUSE",
                  SMALL, (160, 165, 170), 240, 70)

        if self.message_timer > 0:
            panel = pygame.Surface((650, 40), pygame.SRCALPHA)
            panel.fill((5, 5, 8, 220))
            screen.blit(panel, (W // 2 - 325, 100))
            draw_text(screen, self.message, FONT, (255, 95, 100),
                      W // 2, 120, True)

        # Mission objective.
        draw_text(screen, "MISSION: " + MISSIONS[self.chapter],
                  SMALL, (215, 205, 185), 18, H - 28)

    def draw_jumpscare(self):
        screen.fill((18, 0, 3))
        cx, cy = W // 2, H // 2
        pygame.draw.ellipse(screen, (70, 8, 15),
                            (cx - 180, cy - 240, 360, 480))
        pygame.draw.ellipse(screen, BLACK,
                            (cx - 125, cy - 130, 85, 100))
        pygame.draw.ellipse(screen, BLACK,
                            (cx + 40, cy - 130, 85, 100))
        pygame.draw.ellipse(screen, RED,
                            (cx - 100, cy - 95, 45, 24))
        pygame.draw.ellipse(screen, RED,
                            (cx + 55, cy - 95, 45, 24))
        pygame.draw.ellipse(screen, BLACK,
                            (cx - 90, cy + 15, 180, 145))
        draw_text(screen, "RUN.", TITLE, RED, cx, H - 65, True)

    def draw_menu(self):
        screen.fill((5, 6, 9))
        for i in range(15):
            x = (i * 79 + pygame.time.get_ticks() // 30) % W
            pygame.draw.circle(screen, (20, 22, 28), (x, i * 43), 2)

        draw_text(screen, "SILENT", TITLE, WHITE, W // 2, 135, True)
        draw_text(screen, "SIGNAL", TITLE, RED, W // 2, 205, True)
        draw_text(screen, "THE DARKNESS IS LISTENING",
                  SMALL, (140, 140, 150), W // 2, 255, True)

        mouse = pygame.mouse.get_pos()
        actions = [
            ("NEW GAME", "new"),
            ("CONTINUE / LOAD", "load"),
            ("SETTINGS", "settings"),
            ("QUIT", "quit"),
        ]

        for i, (label, action) in enumerate(actions):
            r = pygame.Rect(W // 2 - 150, 315 + i * 62, 300, 46)
            hover = r.collidepoint(mouse)
            pygame.draw.rect(screen, (55, 15, 22) if hover else (17, 20, 25), r)
            pygame.draw.rect(screen, RED if hover else (75, 80, 88), r, 2)
            draw_text(screen, label, FONT, WHITE, r.centerx, r.centery, True)

            if pygame.mouse.get_pressed()[0] and hover:
                if action == "new":
                    self.reset()
                    self.last_scare = pygame.time.get_ticks()
                    self.state = "playing"
                elif action == "load":
                    self.load()
                elif action == "settings":
                    self.previous_state = "menu"
                    self.state = "settings"
                elif action == "quit":
                    self.state = "quit"

    def draw_pause(self):
        self.draw_world()
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        draw_text(screen, "PAUSED", TITLE, WHITE, W // 2, 190, True)
        mouse = pygame.mouse.get_pos()

        for i, (label, action) in enumerate([
            ("RESUME", "resume"),
            ("SAVE GAME", "save"),
            ("SETTINGS", "settings"),
            ("MAIN MENU", "menu"),
        ]):
            r = pygame.Rect(W // 2 - 140, 280 + i * 62, 280, 45)
            hover = r.collidepoint(mouse)
            pygame.draw.rect(screen, (55, 15, 22) if hover else (18, 21, 26), r)
            pygame.draw.rect(screen, RED if hover else (80, 85, 95), r, 2)
            draw_text(screen, label, FONT, WHITE, r.centerx, r.centery, True)

            if pygame.mouse.get_pressed()[0] and hover:
                if action == "resume":
                    self.state = "playing"
                elif action == "save":
                    self.save()
                elif action == "settings":
                    self.previous_state = "pause"
                    self.state = "settings"
                elif action == "menu":
                    self.state = "menu"
                pygame.time.wait(160)

    def draw_settings(self):
        screen.fill((6, 8, 11))
        draw_text(screen, "SETTINGS", TITLE, WHITE, W // 2, 150, True)
        mouse = pygame.mouse.get_pos()

        options = [
            ("FLASHLIGHT: " + ("ON" if self.settings["flashlight"] else "OFF"),
             "light"),
            ("SCREEN SHAKE: " + ("ON" if self.settings["shake"] else "OFF"),
             "shake"),
            ("BACK", "back"),
        ]

        for i, (label, action) in enumerate(options):
            r = pygame.Rect(W // 2 - 210, 280 + i * 80, 420, 52)
            hover = r.collidepoint(mouse)
            pygame.draw.rect(screen, (50, 15, 22) if hover else (18, 21, 26), r)
            pygame.draw.rect(screen, RED if hover else (80, 85, 95), r, 2)
            draw_text(screen, label, FONT, WHITE, r.centerx, r.centery, True)

            if pygame.mouse.get_pressed()[0] and hover:
                if action == "light":
                    self.settings["flashlight"] = not self.settings["flashlight"]
                elif action == "shake":
                    self.settings["shake"] = not self.settings["shake"]
                else:
                    self.state = self.previous_state
                pygame.time.wait(160)

    def draw_end(self):
        screen.fill((3, 3, 5))
        draw_text(screen, "SIGNAL TERMINATED", TITLE, RED, W // 2, 240, True)
        draw_text(screen, "YOU SURVIVED THE NIGHTMARE",
                  FONT, WHITE, W // 2, 330, True)
        draw_text(screen, f"FINAL SCORE: {self.score}",
                  FONT, (225, 190, 80), W // 2, 390, True)
        draw_text(screen, "PRESS ENTER TO RETURN TO MENU",
                  SMALL, WHITE, W // 2, 500, True)

    def draw_gameover(self):
        screen.fill((8, 0, 2))
        draw_text(screen, "YOU ARE DEAD", TITLE, RED, W // 2, 250, True)
        draw_text(screen, "R - RETRY | ENTER - MENU",
                  FONT, WHITE, W // 2, 420, True)

    # =================================================
    # EVENTS AND MAIN LOOP
    # =================================================

    def handle_key(self, key):
        if self.state == "playing":
            if key == pygame.K_ESCAPE:
                self.state = "pause"
            elif key == pygame.K_SPACE:
                self.shoot()
            elif key == pygame.K_e:
                self.interact()
            elif key == pygame.K_h:
                self.heal()
            elif key == pygame.K_f:
                self.flashlight = not self.flashlight
            elif key == pygame.K_F5:
                self.save()

        elif self.state == "pause":
            if key == pygame.K_ESCAPE:
                self.state = "playing"

        elif self.state == "settings":
            if key == pygame.K_ESCAPE:
                self.state = self.previous_state

        elif self.state == "gameover":
            if key == pygame.K_r:
                self.reset()
                self.last_scare = pygame.time.get_ticks()
                self.state = "playing"
            elif key == pygame.K_RETURN:
                self.state = "menu"

        elif self.state == "ending" and key == pygame.K_RETURN:
            self.state = "menu"

    def run(self):
        self.last_scare = pygame.time.get_ticks()
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

            if self.state == "menu":
                self.draw_menu()
            elif self.state == "playing":
                if self.scare_timer > 0:
                    self.draw_jumpscare()
                else:
                    self.draw_world()
            elif self.state == "pause":
                self.draw_pause()
            elif self.state == "settings":
                self.draw_settings()
            elif self.state == "gameover":
                self.draw_gameover()
            elif self.state == "ending":
                self.draw_end()
            elif self.state == "quit":
                running = False

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    Game().run()
