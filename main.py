import json
import os
import random
import math
import pygame

pygame.init()

WIDTH, HEIGHT, TILE, FPS = 1000, 650, 50, 60
COLS, ROWS = 20, 13
SAVE = "silent_signal_save.json"

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Silent Signal")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("consolas", 20)
SMALL = pygame.font.SysFont("consolas", 15)
BIG = pygame.font.SysFont("consolas", 44)

BLACK = (8, 10, 15)
WHITE = (225, 232, 238)
FLOOR = (25, 32, 40)
WALL = (47, 56, 67)
RED = (210, 55, 65)
GREEN = (80, 210, 140)
YELLOW = (235, 195, 75)
BLUE = (80, 165, 230)
PURPLE = (170, 105, 220)

CHAPTERS = [
    ("The Signal", "Find the key and activate the transmitter."),
    ("Cold Storage", "Recover the key and activate the security console."),
    ("The Survivors", "Find the key and restore life support."),
    ("Below Ground", "Reach the control room and escape the creatures."),
    ("Silent Signal", "Defeat the Warden and activate the emergency lift.")
]


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def text(s, x, y, color=WHITE, font=FONT):
    screen.blit(font.render(str(s), True, color), (x, y))


def clamp(n, a, b):
    return max(a, min(b, n))


def make_map():
    # Connected corridors
    grid = [[1] * COLS for _ in range(ROWS)]

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

    for _ in range(24):
        x = random.randint(2, COLS - 3)
        y = random.randint(2, ROWS - 3)

        for xx in range(max(1, x - 1), min(COLS - 1, x + 2)):
            grid[y][xx] = 0

        for yy in range(max(1, y - 1), min(ROWS - 1, y + 2)):
            grid[yy][x] = 0

    return grid


class Game:
    def __init__(self):
        self.state = "menu"
        self.chapter = 0
        self.health = 100
        self.ammo = 30
        self.medkits = 2
        self.kills = 0
        self.flash = True
        self.notice = "Press ENTER to start."
        self.notice_time = 0

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

    def pick(self, avoid=(), far=0):
        options = [
            p for p in self.floors()
            if p not in avoid and dist(p, (1, 1)) >= far
        ]
        return random.choice(options or self.floors())

    def start_chapter(self, new_game=False):
        self.grid = make_map()
        self.player = [1.5 * TILE, 1.5 * TILE]

        self.key = self.pick(far=4)
        self.terminal = self.pick((self.key,), far=6)
        self.exit = (COLS - 2, ROWS - 2)

        self.npc = (
            self.pick((self.key, self.terminal, self.exit), far=4)
            if self.chapter == 2 else None
        )

        self.has_key = False
        self.terminal_on = False
        self.enemies = []

        for _ in range(2 + self.chapter):
            p = self.pick((self.key, self.terminal, self.exit), far=6)

            self.enemies.append({
                "x": (p[0] + 0.5) * TILE,
                "y": (p[1] + 0.5) * TILE,
                "hp": 2 + self.chapter // 3,
                "cool": 0
            })

        self.boss = None

        if self.chapter == 4:
            p = self.pick(
                (self.key, self.terminal, self.exit), far=9
            )

            self.boss = {
                "x": (p[0] + 0.5) * TILE,
                "y": (p[1] + 0.5) * TILE,
                "hp": 22,
                "max": 22,
                "cool": 1
            }

        if new_game:
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
            tx = int(xx // TILE)
            ty = int(yy // TILE)

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

        if not self.has_key and dist(p, self.key) < 1.25:
            self.has_key = True
            self.say("Access key collected.")
            return

        if not self.terminal_on and dist(p, self.terminal) < 1.35:
            if self.chapter > 0 and not self.has_key:
                self.say("Terminal locked. Find the access key first.")
                return

            self.terminal_on = True
            self.say("Terminal activated. Exit power restored.")
            return

        if self.npc and dist(p, self.npc) < 1.4:
            self.say("SURVIVOR: The exit is marked. Keep moving.")
            return

        if dist(p, self.exit) < 1.3:
            if self.boss and self.boss["hp"] > 0:
                self.say("The lift is sealed. Defeat the Warden.")
                return

            if not self.has_key:
                self.say("Exit locked. Find the access key.")
                return

            if not self.terminal_on:
                self.say("Exit power is offline. Activate the terminal.")
                return

            self.chapter += 1

            if self.chapter >= len(CHAPTERS):
                self.state = "ending"
                self.choice = 0
            else:
                self.start_chapter()

            return

        self.say("Nothing to interact with nearby.", 1)

    def shoot(self):
        if self.ammo <= 0:
            self.say("Out of ammo!")
            return

        self.ammo -= 1
        targets = self.enemies[:]

        if self.boss and self.boss["hp"] > 0:
            targets.append(self.boss)

        if not targets:
            self.say("No target in sight.", 0.7)
            return

        target = min(
            targets,
            key=lambda e: dist(
                self.player, (e["x"], e["y"])
            )
        )

        if dist(self.player, (target["x"], target["y"])) > 260:
            self.say("Target out of range.", 0.7)
            return

        target["hp"] -= 1

        if target is self.boss:
            self.say("Warden hit!", 0.5)

        elif target["hp"] <= 0:
            self.enemies.remove(target)
            self.kills += 1
            self.say("Hostile neutralized.", 0.6)

        else:
            self.say("Hit confirmed.", 0.5)

    def update(self, dt):
        if self.notice_time > 0:
            self.notice_time -= 1

        px, py = self.player

        for enemy in self.enemies:
            d = dist(
                (px, py),
                (enemy["x"], enemy["y"])
            )

            enemy["cool"] -= dt

            if d < 300:
                if d > 27:
                    vx = (px - enemy["x"]) / max(d, 1)
                    vy = (py - enemy["y"]) / max(d, 1)

                    nx = enemy["x"] + vx * (68 + self.chapter * 7) * dt
                    ny = enemy["y"] + vy * (68 + self.chapter * 7) * dt

                    if self.can_walk(nx, ny):
                        enemy["x"] = nx
                        enemy["y"] = ny

                elif enemy["cool"] <= 0:
                    self.health -= 8
                    enemy["cool"] = 1.0
                    self.say("A creature strikes you!", 0.6)

        if self.boss and self.boss["hp"] > 0:
            boss = self.boss
            d = dist(
                (px, py),
                (boss["x"], boss["y"])
            )

            boss["cool"] -= dt

            if d > 45:
                vx = (px - boss["x"]) / max(d, 1)
                vy = (py - boss["y"]) / max(d, 1)

                nx = boss["x"] + vx * 56 * dt
                ny = boss["y"] + vy * 56 * dt

                if self.can_walk(nx, ny, 17):
                    boss["x"] = nx
                    boss["y"] = ny

            elif boss["cool"] <= 0:
                self.health -= 15
                boss["cool"] = 1.25
                self.say("WARDEN ATTACK!", 0.7)

        self.health = clamp(self.health, 0, 100)

        if self.health <= 0:
            self.state = "gameover"

    def save(self):
        data = {
            "chapter": self.chapter,
            "health": self.health,
            "ammo": self.ammo,
            "medkits": self.medkits,
            "kills": self.kills
        }

        with open(SAVE, "w", encoding="utf-8") as f:
            json.dump(data, f)

        self.say("Progress saved.")

    def load(self):
        if not os.path.exists(SAVE):
            self.say("No save found.")
            return

        try:
            with open(SAVE, encoding="utf-8") as f:
                data = json.load(f)

            self.chapter = clamp(
                int(data.get("chapter", 0)), 0, 4
            )
            self.health = clamp(
                int(data.get("health", 100)), 1, 100
            )
            self.ammo = max(0, int(data.get("ammo", 30)))
            self.medkits = max(0, int(data.get("medkits", 2)))
            self.kills = max(0, int(data.get("kills", 0)))

            self.start_chapter()
            self.state = "playing"
            self.say(
                "Save loaded. Chapter restarts at its beginning."
            )

        except (OSError, ValueError, json.JSONDecodeError):
            self.say("Save file is invalid.")

    def draw(self):
        screen.fill(BLACK)

        camx = clamp(
            self.player[0] - WIDTH / 2,
            0, COLS * TILE - WIDTH
        )
        camy = clamp(
            self.player[1] - HEIGHT / 2,
            0, ROWS * TILE - HEIGHT
        )

        for y, row in enumerate(self.grid):
            for x, value in enumerate(row):
                rect = pygame.Rect(
                    int(x * TILE - camx),
                    int(y * TILE - camy),
                    TILE, TILE
                )

                pygame.draw.rect(
                    screen, WALL if value else FLOOR, rect
                )
                pygame.draw.rect(
                    screen, (32, 40, 49), rect, 1
                )

        def pos(tile):
            return (
                int((tile[0] + 0.5) * TILE - camx),
                int((tile[1] + 0.5) * TILE - camy)
            )

        if not self.has_key:
            pygame.draw.circle(
                screen, YELLOW, pos(self.key), 10
            )

        if not self.terminal_on:
            pygame.draw.rect(
                screen, BLUE, (*pos(self.terminal), 18, 18)
            )

        if self.npc:
            pygame.draw.circle(
                screen, GREEN, pos(self.npc), 11
            )

        exit_rect = pygame.Rect(
            self.exit[0] * TILE - camx + 7,
            self.exit[1] * TILE - camy + 7,
            36, 36
        )
        pygame.draw.rect(screen, (130, 90, 48), exit_rect)

        for enemy in self.enemies:
            pygame.draw.circle(
                screen, RED,
                (int(enemy["x"] - camx),
                 int(enemy["y"] - camy)),
                14
            )

        if self.boss and self.boss["hp"] > 0:
            pygame.draw.circle(
                screen, PURPLE,
                (int(self.boss["x"] - camx),
                 int(self.boss["y"] - camy)),
                25
            )

            pygame.draw.rect(
                screen, (40, 20, 25),
                (WIDTH // 2 - 170, 82, 340, 14)
            )

            pygame.draw.rect(
                screen, RED,
                (
                    WIDTH // 2 - 170, 82,
                    int(340 * self.boss["hp"] / self.boss["max"]),
                    14
                )
            )

            text("WARDEN", WIDTH // 2 - 38, 99, WHITE, SMALL)

        pygame.draw.circle(
            screen, BLUE,
            (int(self.player[0] - camx),
             int(self.player[1] - camy)),
            12
        )

        if self.flash:
            overlay = pygame.Surface(
                (WIDTH, HEIGHT), pygame.SRCALPHA
            )
            overlay.fill((0, 0, 0, 115))
            pygame.draw.circle(
                overlay, (0, 0, 0, 0),
                (WIDTH // 2, HEIGHT // 2), 165
            )
            screen.blit(overlay, (0, 0))

        pygame.draw.rect(
            screen, (12, 16, 22), (0, 0, WIDTH, 76)
        )

        text(
            f"CH {self.chapter + 1}/5  "
            f"{CHAPTERS[self.chapter][0]}",
            14, 7, YELLOW
        )

        text(
            f"HP {self.health:3}   AMMO {self.ammo}   "
            f"MEDKITS {self.medkits}   KILLS {self.kills}",
            14, 40, WHITE, SMALL
        )

        text(
            f"KEY {'YES' if self.has_key else 'NO'} | "
            f"TERMINAL {'ON' if self.terminal_on else 'OFF'}",
            510, 40, WHITE, SMALL
        )

        if self.notice_time > 0:
            pygame.draw.rect(
                screen, (5, 8, 12),
                (125, HEIGHT - 55, WIDTH - 250, 38)
            )
            text(
                self.notice, 140, HEIGHT - 45,
                WHITE, SMALL
            )


game = Game()
running = True

while running:
    dt = min(clock.tick(FPS) / 1000, 0.04)

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False

        if ev.type == pygame.KEYDOWN:
            if game.state == "menu":
                if ev.key == pygame.K_RETURN:
                    game.chapter = 0
                    game.start_chapter(True)
                    game.state = "playing"

                elif ev.key == pygame.K_l:
                    game.load()

                elif ev.key == pygame.K_ESCAPE:
                    running = False

            elif game.state == "playing":
                if ev.key == pygame.K_ESCAPE:
                    game.save()
                    game.state = "menu"

                elif ev.key == pygame.K_e:
                    game.interact()

                elif ev.key == pygame.K_SPACE:
                    game.shoot()

                elif ev.key == pygame.K_f:
                    game.flash = not game.flash

                elif ev.key == pygame.K_F5:
                    game.save()

                elif ev.key == pygame.K_h:
                    if game.medkits and game.health < 100:
                        game.medkits -= 1
                        game.health = min(100, game.health + 35)
                        game.say("Medkit used: +35 HP")
                    else:
                        game.say(
                            "No medkits available or HP is full."
                        )

            elif game.state == "ending":
                if ev.key in (pygame.K_1, pygame.K_2):
                    game.choice = (
                        1 if ev.key == pygame.K_1 else 2
                    )

                elif ev.key == pygame.K_RETURN and game.choice:
                    game.state = "menu"

            elif game.state == "gameover":
                if ev.key == pygame.K_RETURN:
                    game.state = "menu"

                elif ev.key == pygame.K_r:
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
        game.draw()

    elif game.state == "menu":
        screen.fill(BLACK)
        text("SILENT SIGNAL", 285, 145, RED, BIG)
        text("A survival horror experience", 345, 205)
        text("ENTER - New game", 370, 300)
        text("L - Load save", 370, 340)
        text("ESC - Quit", 370, 380)

        text(
            "WASD move | E interact | SPACE shoot | "
            "H heal | F flashlight | F5 save",
            130, 535, WHITE, SMALL
        )

    elif game.state == "ending":
        screen.fill(BLACK)
        text("SIGNAL RESTORED", 280, 130, GREEN, BIG)
        text("Choose the facility's fate:", 345, 230)
        text(
            "1 - Send distress signal and save survivors",
            245, 300, YELLOW
        )
        text(
            "2 - Destroy the facility and end the threat",
            245, 345, RED
        )

        if game.choice:
            text(
                "Ending selected. Press ENTER for menu.",
                320, 440, GREEN, SMALL
            )

    elif game.state == "gameover":
        screen.fill(BLACK)
        text("SIGNAL LOST", 335, 200, RED, BIG)
        text("ENTER - Menu     R - Restart", 340, 330)

    pygame.display.flip()

pygame.quit()