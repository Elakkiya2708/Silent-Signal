
import pygame
import random
import math
import sys
from collections import deque

pygame.init()

# =============== SETTINGS ===============
WIDTH, HEIGHT = 900, 700
HUD = 90
TILE = 36
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Silent Signal - Inventory & Power-ups")
clock = pygame.time.Clock()

WHITE = (240, 245, 255)
BLACK = (5, 7, 14)
WALL = (37, 45, 62)
FLOOR = (15, 20, 30)
CYAN = (40, 225, 245)
RED = (240, 55, 75)
GREEN = (60, 230, 130)
GOLD = (255, 215, 65)
PURPLE = (180, 70, 240)
ORANGE = (255, 155, 40)

font = pygame.font.SysFont("consolas", 19)
small = pygame.font.SysFont("consolas", 14)
big = pygame.font.SysFont("consolas", 45, bold=True)

# =============== GAME VARIABLES ===============
state = "menu"
level = 1

ROWS, COLS = 17, 21
maze = []

player = pygame.Rect(0, 0, 22, 22)
player_speed = 2.7
player_health = 100

boss_x = 0.0
boss_y = 0.0
boss_health = 100
boss_max_health = 100
boss_speed = 0.9
boss_stun = 0
boss_attack = 0

keys = []
keys_collected = 0
total_keys = 3
exit_rect = pygame.Rect(0, 0, TILE, TILE)

# Inventory slots:
# 1 = Health pack, 2 = Speed boost, 3 = Flashlight
inventory = {"health": 0, "speed": 0, "flashlight": 0}
powerups = []

speed_timer = 0
flashlight_timer = 0
sonar_cooldown = 0
sonar_wave = 0
sonar_active = False

message = ""
message_timer = 0


# =============== HELPER FUNCTIONS ===============
def show_message(text, duration=120):
    global message, message_timer
    message = text
    message_timer = duration


def cell_center(cell):
    x, y = cell
    return x * TILE + TILE // 2, y * TILE + TILE // 2 + HUD


def generate_maze():
    global maze, ROWS, COLS

    ROWS = min(17 + (level - 1) * 2, 25)
    COLS = min(21 + (level - 1) * 2, 31)

    if ROWS % 2 == 0:
        ROWS += 1
    if COLS % 2 == 0:
        COLS += 1

    maze = [[1] * COLS for _ in range(ROWS)]
    maze[1][1] = 0
    stack = [(1, 1)]

    while stack:
        x, y = stack[-1]
        options = []

        for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
            nx, ny = x + dx, y + dy
            if (1 <= nx < COLS - 1 and
                    1 <= ny < ROWS - 1 and maze[ny][nx] == 1):
                options.append((nx, ny, dx, dy))

        if options:
            nx, ny, dx, dy = random.choice(options)
            maze[y + dy // 2][x + dx // 2] = 0
            maze[ny][nx] = 0
            stack.append((nx, ny))
        else:
            stack.pop()


def farthest_cell(start=(1, 1)):
    queue = deque([(start[0], start[1], 0)])
    visited = {start}
    farthest = start
    max_dist = 0

    while queue:
        x, y, distance = queue.popleft()

        if distance > max_dist:
            max_dist = distance
            farthest = (x, y)

        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < COLS and 0 <= ny < ROWS
                    and maze[ny][nx] == 0
                    and (nx, ny) not in visited):
                visited.add((nx, ny))
                queue.append((nx, ny, distance + 1))

    return farthest


def random_floor(excluded, min_distance=0):
    options = []

    for y in range(1, ROWS - 1):
        for x in range(1, COLS - 1):
            if maze[y][x] != 0 or (x, y) in excluded:
                continue

            distance = abs(x - 1) + abs(y - 1)
            if distance >= min_distance:
                options.append((x, y))

    return random.choice(options) if options else (1, 1)


def is_wall_pixel(x, y):
    col = int(x // TILE)
    row = int((y - HUD) // TILE)

    if row < 0 or row >= ROWS or col < 0 or col >= COLS:
        return True

    return maze[row][col] == 1


def move_player(dx, dy):
    player.x += round(dx)
    corners = [
        (player.left, player.top),
        (player.right - 1, player.top),
        (player.left, player.bottom - 1),
        (player.right - 1, player.bottom - 1)
    ]

    if any(is_wall_pixel(x, y) for x, y in corners):
        player.x -= round(dx)

    player.y += round(dy)
    corners = [
        (player.left, player.top),
        (player.right - 1, player.top),
        (player.left, player.bottom - 1),
        (player.right - 1, player.bottom - 1)
    ]

    if any(is_wall_pixel(x, y) for x, y in corners):
        player.y -= round(dy)


# =============== LEVEL SETUP ===============
def new_level():
    global player, player_health, keys, keys_collected, total_keys
    global exit_rect, boss_x, boss_y, boss_health, boss_max_health
    global boss_speed, boss_stun, boss_attack, powerups
    global inventory, speed_timer, flashlight_timer
    global sonar_cooldown, sonar_active, sonar_wave

    generate_maze()

    sx, sy = cell_center((1, 1))
    player = pygame.Rect(sx - 11, sy - 11, 22, 22)

    end_cell = farthest_cell()
    ex, ey = cell_center(end_cell)
    exit_rect = pygame.Rect(ex - 14, ey - 14, 28, 28)

    excluded = {(1, 1), end_cell}

    total_keys = min(3 + (level - 1) // 2, 6)
    keys_collected = 0
    keys = []

    for _ in range(total_keys):
        cell = random_floor(excluded, 4)
        excluded.add(cell)
        kx, ky = cell_center(cell)
        keys.append(pygame.Rect(kx - 7, ky - 7, 14, 14))

    boss_cell = random_floor(excluded, 6)
    excluded.add(boss_cell)
    boss_x, boss_y = map(float, cell_center(boss_cell))

    boss_max_health = 100 + (level - 1) * 25
    boss_health = boss_max_health
    boss_speed = min(0.8 + level * 0.1, 1.8)
    boss_stun = 0
    boss_attack = 0

    # Power-ups are picked up and stored in inventory
    powerups = []
    kinds = ["health", "speed", "flashlight", "health", "speed"]

    for kind in kinds:
        cell = random_floor(excluded, 3)
        excluded.add(cell)
        x, y = cell_center(cell)
        powerups.append({
            "kind": kind,
            "rect": pygame.Rect(x - 10, y - 10, 20, 20)
        })

    inventory = {"health": 0, "speed": 0, "flashlight": 0}
    player_health = 100
    speed_timer = 0
    flashlight_timer = 0
    sonar_cooldown = 0
    sonar_active = False
    sonar_wave = 0

    show_message(f"LEVEL {level}: COLLECT KEYS, POWER-UPS AND DEFEAT BOSS!")


# =============== INVENTORY ===============
def activate_powerup(slot):
    global player_health, speed_timer, flashlight_timer

    if slot == 1:
        if inventory["health"] > 0:
            if player_health >= 100:
                show_message("HEALTH ALREADY FULL!")
                return

            player_health = min(100, player_health + 40)
            inventory["health"] -= 1
            show_message("HEALTH PACK USED: +40 HP!")

        else:
            show_message("NO HEALTH PACK! FIND GREEN POWER-UPS.")

    elif slot == 2:
        if inventory["speed"] > 0:
            speed_timer = 600
            inventory["speed"] -= 1
            show_message("SPEED BOOST ACTIVATED!")

        else:
            show_message("NO SPEED BOOST! FIND BLUE POWER-UPS.")

    elif slot == 3:
        if inventory["flashlight"] > 0:
            flashlight_timer = 900
            inventory["flashlight"] -= 1
            show_message("FLASHLIGHT ACTIVATED!")

        else:
            show_message("NO FLASHLIGHT! FIND YELLOW POWER-UPS.")


def collect_powerups():
    global powerups

    for item in powerups[:]:
        if player.colliderect(item["rect"]):
            kind = item["kind"]
            inventory[kind] += 1
            powerups.remove(item)

            names = {
                "health": "HEALTH PACK",
                "speed": "SPEED BOOST",
                "flashlight": "FLASHLIGHT"
            }
            show_message(f"PICKED UP: {names[kind]}!")


# =============== SONAR ===============
def use_sonar():
    global sonar_cooldown, sonar_active, sonar_wave
    global boss_health, boss_stun

    if sonar_cooldown > 0:
        show_message("SONAR RECHARGING!")
        return

    sonar_cooldown = 100
    sonar_active = True
    sonar_wave = 0

    px, py = player.center
    distance = math.hypot(px - boss_x, py - boss_y)

    if boss_health > 0 and distance <= 190:
        boss_health = max(0, boss_health - 25)
        boss_stun = 75
        show_message("SONAR HIT! BOSS STUNNED!")

        if boss_health == 0:
            show_message("BOSS DEFEATED! NOW FIND THE EXIT!", 180)
    else:
        show_message("SONAR PULSE RELEASED!")


# =============== BOSS AI ===============
def update_boss():
    global boss_x, boss_y, boss_stun, boss_attack
    global player_health, state

    if boss_health <= 0:
        return

    if boss_stun > 0:
        boss_stun -= 1
        return

    px, py = player.center
    dx = px - boss_x
    dy = py - boss_y
    distance = math.hypot(dx, dy)

    if distance > 2:
        vx = dx / distance * boss_speed
        vy = dy / distance * boss_speed

        nx = boss_x + vx
        ny = boss_y + vy

        if (not is_wall_pixel(nx - 15, boss_y - 15)
                and not is_wall_pixel(nx + 15, boss_y + 15)):
            boss_x = nx

        if (not is_wall_pixel(boss_x - 15, ny - 15)
                and not is_wall_pixel(boss_x + 15, ny + 15)):
            boss_y = ny

    if boss_attack > 0:
        boss_attack -= 1

    boss_rect = pygame.Rect(
        int(boss_x - 16), int(boss_y - 16), 32, 32
    )

    if player.colliderect(boss_rect) and boss_attack == 0:
        player_health -= 15
        boss_attack = 50
        show_message("BOSS ATTACKED YOU!")

        if player_health <= 0:
            player_health = 0
            state = "lost"


# =============== DRAWING ===============
def draw_maze():
    for y in range(ROWS):
        for x in range(COLS):
            rect = pygame.Rect(x * TILE, y * TILE + HUD, TILE, TILE)

            if maze[y][x]:
                pygame.draw.rect(screen, WALL, rect)
                pygame.draw.rect(screen, (52, 62, 80), rect, 1)
            else:
                pygame.draw.rect(screen, FLOOR, rect)
                pygame.draw.rect(screen, (25, 31, 42), rect, 1)


def draw_bar(x, y, width, height, value, maximum, color):
    pygame.draw.rect(screen, (70, 25, 38), (x, y, width, height))
    fill = int(width * max(0, value) / maximum)
    if fill:
        pygame.draw.rect(screen, color, (x, y, fill, height))


def draw_hud():
    pygame.draw.rect(screen, (9, 13, 23), (0, 0, WIDTH, HUD))

    screen.blit(font.render("SILENT SIGNAL", True, CYAN), (12, 8))
    screen.blit(small.render(f"LEVEL {level}", True, WHITE), (12, 38))
    screen.blit(
        small.render(f"KEYS {keys_collected}/{total_keys}", True, GOLD),
        (100, 38)
    )

    screen.blit(small.render("PLAYER HP", True, WHITE), (220, 8))
    draw_bar(305, 10, 125, 13, player_health, 100, GREEN)

    screen.blit(small.render("BOSS HP", True, WHITE), (450, 8))
    draw_bar(520, 10, 145, 13, boss_health, boss_max_health, PURPLE)

    screen.blit(small.render("INVENTORY", True, CYAN), (220, 37))
    screen.blit(
        small.render(f"1: Health x{inventory['health']}", True, GREEN),
        (315, 37)
    )
    screen.blit(
        small.render(f"2: Speed x{inventory['speed']}", True, CYAN),
        (465, 37)
    )
    screen.blit(
        small.render(f"3: Light x{inventory['flashlight']}", True, GOLD),
        (610, 37)
    )

    sonar_status = "READY" if sonar_cooldown == 0 else "RECHARGING"
    screen.blit(
        small.render(f"SPACE: SONAR ({sonar_status})", True, ORANGE),
        (220, 61)
    )

    if speed_timer > 0:
        screen.blit(
            small.render(f"SPEED {speed_timer // FPS}s", True, CYAN),
            (465, 61)
        )

    if flashlight_timer > 0:
        screen.blit(
            small.render(f"LIGHT {flashlight_timer // FPS}s", True, GOLD),
            (610, 61)
        )


def draw_powerups():
    for item in powerups:
        rect = item["rect"]
        kind = item["kind"]

        colors = {
            "health": GREEN,
            "speed": CYAN,
            "flashlight": GOLD
        }

        pygame.draw.rect(screen, colors[kind], rect, border_radius=5)
        pygame.draw.rect(screen, WHITE, rect, 2, border_radius=5)

        letters = {
            "health": "H",
            "speed": "S",
            "flashlight": "F"
        }
        label = small.render(letters[kind], True, BLACK)
        screen.blit(label, (
            rect.centerx - label.get_width() // 2,
            rect.centery - label.get_height() // 2
        ))


def draw_game():
    screen.fill(BLACK)
    draw_maze()
    draw_hud()

    for key in keys:
        pygame.draw.circle(screen, GOLD, key.center, 7)
        pygame.draw.circle(screen, WHITE, key.center, 2)

    exit_color = GREEN if (
        boss_health <= 0 and keys_collected == total_keys
    ) else RED

    pygame.draw.rect(screen, exit_color, exit_rect, border_radius=5)
    pygame.draw.rect(screen, WHITE, exit_rect, 2, border_radius=5)

    draw_powerups()

    if boss_health > 0:
        boss_rect = pygame.Rect(
            int(boss_x - 16), int(boss_y - 16), 32, 32
        )
        boss_color = ORANGE if boss_stun > 0 else PURPLE
        pygame.draw.rect(screen, boss_color, boss_rect, border_radius=7)
        pygame.draw.rect(screen, RED, boss_rect, 2, border_radius=7)

        pygame.draw.circle(
            screen, WHITE, (int(boss_x - 6), int(boss_y - 4)), 4
        )
        pygame.draw.circle(
            screen, WHITE, (int(boss_x + 6), int(boss_y - 4)), 4
        )

    pygame.draw.rect(screen, CYAN, player, border_radius=5)
    pygame.draw.rect(screen, WHITE, player, 2, border_radius=5)

    if sonar_active:
        pygame.draw.circle(
            screen, CYAN, player.center, int(sonar_wave), 2
        )

    # Darkness overlay. Flashlight gives a larger visible area.
    radius = 220 if flashlight_timer > 0 else 115

    darkness = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    darkness.fill((0, 0, 0, 238))

    pygame.draw.circle(
        darkness, (0, 0, 0, 0), player.center, radius
    )

    # Also reveal a small area around the boss.
    if boss_health > 0:
        pygame.draw.circle(
            darkness, (0, 0, 0, 0),
            (int(boss_x), int(boss_y)), 40
        )

    screen.blit(darkness, (0, 0))

    # Redraw the HUD over the darkness.
    draw_hud()

    if message_timer > 0:
        label = font.render(message, True, GOLD)
        screen.blit(
            label,
            (WIDTH // 2 - label.get_width() // 2, HEIGHT - 28)
        )


def center_screen(title, subtitle, instructions):
    screen.fill(BLACK)

    title_img = big.render(title, True, CYAN)
    screen.blit(
        title_img,
        (WIDTH // 2 - title_img.get_width() // 2, 190)
    )

    sub = font.render(subtitle, True, WHITE)
    screen.blit(
        sub, (WIDTH // 2 - sub.get_width() // 2, 275)
    )

    for i, line in enumerate(instructions):
        text = small.render(line, True, GOLD)
        screen.blit(
            text,
            (WIDTH // 2 - text.get_width() // 2, 340 + i * 27)
        )


# =============== MAIN LOOP ===============
running = True

while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if state == "menu":
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    level = 1
                    new_level()
                    state = "playing"

            elif state == "playing":
                if event.key == pygame.K_ESCAPE:
                    state = "menu"
                elif event.key == pygame.K_SPACE:
                    use_sonar()
                elif event.key == pygame.K_1:
                    activate_powerup(1)
                elif event.key == pygame.K_2:
                    activate_powerup(2)
                elif event.key == pygame.K_3:
                    activate_powerup(3)

            elif state in ("won", "lost"):
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if state == "won":
                        level += 1
                    new_level()
                    state = "playing"
                elif event.key == pygame.K_ESCAPE:
                    state = "menu"

    if state == "playing":
        pressed = pygame.key.get_pressed()

        dx = 0
        dy = 0

        if pressed[pygame.K_a] or pressed[pygame.K_LEFT]:
            dx -= 1
        if pressed[pygame.K_d] or pressed[pygame.K_RIGHT]:
            dx += 1
        if pressed[pygame.K_w] or pressed[pygame.K_UP]:
            dy -= 1
        if pressed[pygame.K_s] or pressed[pygame.K_DOWN]:
            dy += 1

        speed = player_speed * (1.7 if speed_timer > 0 else 1)

        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071

        move_player(dx * speed, dy * speed)

        if speed_timer > 0:
            speed_timer -= 1

        if flashlight_timer > 0:
            flashlight_timer -= 1

        if sonar_cooldown > 0:
            sonar_cooldown -= 1

        if sonar_active:
            sonar_wave += 10
            if sonar_wave >= 220:
                sonar_active = False

        if message_timer > 0:
            message_timer -= 1

        # Collect keys
        for key in keys[:]:
            if player.colliderect(key):
                keys.remove(key)
                keys_collected += 1
                show_message("KEY COLLECTED!")

        # Collect power-ups
        collect_powerups()

        # Update boss
        update_boss()

        # Exit checks
        if player.colliderect(exit_rect):
            if keys_collected < total_keys:
                show_message("COLLECT ALL KEYS FIRST!", 45)
            elif boss_health > 0:
                show_message("DEFEAT THE BOSS FIRST!", 45)
            else:
                state = "won"

    if state == "menu":
        center_screen(
            "SILENT SIGNAL",
            "BOSS FIGHT + INVENTORY",
            [
                "ENTER: START GAME",
                "WASD / ARROWS: MOVE",
                "SPACE: SONAR ATTACK",
                "1: HEALTH  |  2: SPEED  |  3: FLASHLIGHT",
                "COLLECT KEYS, DEFEAT THE BOSS AND ESCAPE"
            ]
        )

    elif state == "playing":
        draw_game()

    elif state == "won":
        center_screen(
            "LEVEL CLEARED!",
            f"You escaped level {level}",
            [
                "ENTER / SPACE: NEXT LEVEL",
                "ESC: MAIN MENU"
            ]
        )

    elif state == "lost":
        center_screen(
            "YOU WERE CAUGHT!",
            f"Level reached: {level}",
            [
                "ENTER / SPACE: RETRY LEVEL",
                "ESC: MAIN MENU"
            ]
        )

    pygame.display.flip()

pygame.quit()
sys.exit()
