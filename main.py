
import pygame
import random
import sys
import math
from collections import deque

pygame.init()

# ---------------- SETTINGS ----------------
WIDTH, HEIGHT = 900, 700
HUD = 80
TILE = 40
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Silent Signal - Boss Fight")
clock = pygame.time.Clock()

WHITE = (240, 240, 240)
BLACK = (8, 10, 17)
WALL = (36, 43, 59)
FLOOR = (17, 22, 32)
CYAN = (45, 225, 240)
RED = (235, 55, 75)
ORANGE = (255, 155, 40)
GREEN = (70, 235, 140)
PURPLE = (170, 75, 235)
GOLD = (255, 220, 80)

font = pygame.font.SysFont("consolas", 20)
big_font = pygame.font.SysFont("consolas", 44, bold=True)
small_font = pygame.font.SysFont("consolas", 15)

# ---------------- GAME STATE ----------------
level = 1
state = "menu"
keys_collected = 0
total_keys = 3

maze = []
ROWS = 15
COLS = 19

player = pygame.Rect(0, 0, 22, 22)
player_speed = 3.0
player_health = 100

boss_x = 0.0
boss_y = 0.0
boss_health = 100
boss_max_health = 100
boss_speed = 1.0
boss_stun = 0
boss_attack_timer = 0

sonar_timer = 0
sonar_radius = 0
sonar_active = False
sonar_cooldown = 0

keys = []
exit_rect = pygame.Rect(0, 0, TILE, TILE)
message = ""
message_timer = 0


# ---------------- MAZE GENERATION ----------------
def generate_maze():
    global maze, ROWS, COLS

    ROWS = min(15 + (level - 1) * 2, 25)
    COLS = min(19 + (level - 1) * 2, 31)

    if ROWS % 2 == 0:
        ROWS += 1
    if COLS % 2 == 0:
        COLS += 1

    maze = [[1 for _ in range(COLS)] for _ in range(ROWS)]

    stack = [(1, 1)]
    maze[1][1] = 0

    while stack:
        x, y = stack[-1]
        options = []

        for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
            nx, ny = x + dx, y + dy

            if (1 <= nx < COLS - 1 and
                    1 <= ny < ROWS - 1 and
                    maze[ny][nx] == 1):
                options.append((nx, ny, dx, dy))

        if options:
            nx, ny, dx, dy = random.choice(options)
            maze[y + dy // 2][x + dx // 2] = 0
            maze[ny][nx] = 0
            stack.append((nx, ny))
        else:
            stack.pop()

    return (1, 1)


def farthest_cell(start):
    queue = deque([(start[0], start[1], 0)])
    visited = {(start[0], start[1])}
    farthest = start
    max_dist = 0

    while queue:
        x, y, dist = queue.popleft()

        if dist > max_dist:
            max_dist = dist
            farthest = (x, y)

        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy

            if (0 <= nx < COLS and 0 <= ny < ROWS
                    and maze[ny][nx] == 0
                    and (nx, ny) not in visited):
                visited.add((nx, ny))
                queue.append((nx, ny, dist + 1))

    return farthest


def cell_center(cell):
    x, y = cell
    return x * TILE + TILE // 2, y * TILE + TILE // 2


def random_floor(excluded, min_distance=0):
    options = []

    for y in range(1, ROWS - 1):
        for x in range(1, COLS - 1):
            if maze[y][x] != 0 or (x, y) in excluded:
                continue

            distance = abs(x - 1) + abs(y - 1)
            if distance >= min_distance:
                options.append((x, y))

    if not options:
        return (1, 1)

    return random.choice(options)


def show_message(text, duration=150):
    global message, message_timer
    message = text
    message_timer = duration


def new_level():
    global player, player_health, keys_collected, total_keys
    global keys, exit_rect, boss_x, boss_y
    global boss_health, boss_max_health, boss_speed
    global boss_stun, boss_attack_timer, sonar_cooldown
    global sonar_active, sonar_timer, sonar_radius

    start = generate_maze()

    px, py = cell_center(start)
    player = pygame.Rect(px - 11, py - 11, 22, 22)

    end = farthest_cell(start)
    ex, ey = cell_center(end)
    exit_rect = pygame.Rect(ex - 15, ey - 15, 30, 30)

    total_keys = min(3 + (level - 1) // 2, 6)
    keys_collected = 0
    keys = []

    excluded = {start, end}

    for _ in range(total_keys):
        cell = random_floor(excluded, min_distance=4)
        excluded.add(cell)
        kx, ky = cell_center(cell)
        keys.append(pygame.Rect(kx - 8, ky - 8, 16, 16))

    # Boss guards the exit
    boss_cell = random_floor(excluded, min_distance=5)
    boss_x, boss_y = map(float, cell_center(boss_cell))

    boss_max_health = 100 + (level - 1) * 30
    boss_health = boss_max_health
    boss_speed = min(0.8 + level * 0.12, 2.0)

    boss_stun = 0
    boss_attack_timer = 0
    sonar_cooldown = 0
    sonar_active = False
    sonar_timer = 0
    sonar_radius = 0
    player_health = 100

    show_message(f"LEVEL {level} - FIND KEYS AND DEFEAT THE BOSS!")


# ---------------- COLLISION ----------------
def is_wall_pixel(x, y):
    col = int(x // TILE)
    row = int(y // TILE)

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


# ---------------- BOSS AI ----------------
def boss_update():
    global boss_x, boss_y, boss_stun, boss_attack_timer
    global player_health, state

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

        next_x = boss_x + vx
        next_y = boss_y + vy

        # Check boss collision with maze walls
        if not is_wall_pixel(next_x - 17, boss_y - 17) and \
                not is_wall_pixel(next_x + 17, boss_y + 17):
            boss_x = next_x

        if not is_wall_pixel(boss_x - 17, next_y - 17) and \
                not is_wall_pixel(boss_x + 17, next_y + 17):
            boss_y = next_y

    if boss_attack_timer > 0:
        boss_attack_timer -= 1

    boss_rect = pygame.Rect(int(boss_x - 17), int(boss_y - 17), 34, 34)

    if player.colliderect(boss_rect) and boss_attack_timer <= 0:
        player_health -= 15
        boss_attack_timer = 50
        show_message("THE BOSS HIT YOU!", 45)

        if player_health <= 0:
            player_health = 0
            state = "lost"


# ---------------- SONAR ----------------
def use_sonar():
    global sonar_active, sonar_timer, sonar_radius
    global sonar_cooldown, boss_health, boss_stun

    if sonar_cooldown > 0:
        return

    sonar_active = True
    sonar_timer = 22
    sonar_radius = 0
    sonar_cooldown = 100

    px, py = player.center
    distance = math.hypot(px - boss_x, py - boss_y)

    # Sonar damages and stuns boss in range
    if distance <= 190 and boss_health > 0:
        boss_health = max(0, boss_health - 25)
        boss_stun = 75
        show_message("SONAR HIT! BOSS STUNNED!", 70)

        if boss_health <= 0:
            show_message("BOSS DEFEATED! FIND THE EXIT!", 150)
    else:
        show_message("SONAR PULSE RELEASED!", 35)


# ---------------- DRAWING ----------------
def draw_maze():
    for y in range(ROWS):
        for x in range(COLS):
            rect = pygame.Rect(x * TILE, y * TILE + HUD, TILE, TILE)

            if maze[y][x] == 1:
                pygame.draw.rect(screen, WALL, rect)
                pygame.draw.rect(screen, (51, 62, 80), rect, 1)
            else:
                pygame.draw.rect(screen, FLOOR, rect)
                pygame.draw.rect(screen, (25, 32, 44), rect, 1)


def draw_hud():
    pygame.draw.rect(screen, (10, 14, 23), (0, 0, WIDTH, HUD))

    screen.blit(font.render("SILENT SIGNAL", True, CYAN), (15, 10))
    screen.blit(small_font.render(f"LEVEL: {level}", True, WHITE), (15, 43))
    screen.blit(
        small_font.render(f"KEYS: {keys_collected}/{total_keys}", True, GOLD),
        (130, 43)
    )

    # Player health bar
    screen.blit(small_font.render("YOU", True, WHITE), (300, 10))
    pygame.draw.rect(screen, RED, (350, 12, 150, 14))
    pygame.draw.rect(
        screen, GREEN,
        (350, 12, int(150 * player_health / 100), 14)
    )

    # Boss health bar
    screen.blit(small_font.render("BOSS", True, WHITE), (525, 10))
    pygame.draw.rect(screen, (75, 25, 38), (585, 12, 200, 14))

    health_width = int(200 * boss_health / boss_max_health)
    if health_width > 0:
        pygame.draw.rect(
            screen, PURPLE, (585, 12, health_width, 14)
        )

    sonar_text = "READY" if sonar_cooldown <= 0 else "RECHARGING"
    sonar_color = CYAN if sonar_cooldown <= 0 else ORANGE
    screen.blit(
        small_font.render(f"SONAR [SPACE]: {sonar_text}", True, sonar_color),
        (300, 43)
    )


def draw_game():
    screen.fill(BLACK)
    draw_maze()
    draw_hud()

    # Keys
    for key in keys:
        pygame.draw.circle(screen, GOLD, key.center, 8)
        pygame.draw.circle(screen, WHITE, key.center, 3)

    # Exit
    exit_color = GREEN if boss_health <= 0 and keys_collected == total_keys else RED
    pygame.draw.rect(screen, exit_color, exit_rect, border_radius=5)
    pygame.draw.rect(screen, WHITE, exit_rect, 2, border_radius=5)

    # Boss
    if boss_health > 0:
        boss_rect = pygame.Rect(int(boss_x - 17), int(boss_y - 17), 34, 34)

        if boss_stun > 0:
            boss_color = ORANGE
        else:
            boss_color = PURPLE

        pygame.draw.rect(screen, boss_color, boss_rect, border_radius=7)
        pygame.draw.rect(screen, RED, boss_rect, 2, border_radius=7)

        # Boss eyes
        pygame.draw.circle(screen, WHITE, (int(boss_x - 7), int(boss_y - 4)), 4)
        pygame.draw.circle(screen, WHITE, (int(boss_x + 7), int(boss_y - 4)), 4)
        pygame.draw.circle(screen, BLACK, (int(boss_x - 7), int(boss_y - 4)), 2)
        pygame.draw.circle(screen, BLACK, (int(boss_x + 7), int(boss_y - 4)), 2)

        if boss_stun > 0:
            screen.blit(
                small_font.render("STUNNED", True, ORANGE),
                (int(boss_x - 35), int(boss_y - 35))
            )

    # Player
    pygame.draw.rect(screen, CYAN, player, border_radius=5)
    pygame.draw.rect(screen, WHITE, player, 2, border_radius=5)

    # Sonar wave
    if sonar_active:
        pygame.draw.circle(
            screen, CYAN, player.center, int(sonar_radius), 2
        )

    # Message
    if message_timer > 0:
        text = font.render(message, True, GOLD)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT - 35))


def draw_center_screen(title, subtitle, hint):
    screen.fill(BLACK)

    title_surface = big_font.render(title, True, CYAN)
    screen.blit(
        title_surface,
        (WIDTH // 2 - title_surface.get_width() // 2, 200)
    )

    sub = font.render(subtitle, True, WHITE)
    screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 290))

    help_text = small_font.render(hint, True, GOLD)
    screen.blit(
        help_text,
        (WIDTH // 2 - help_text.get_width() // 2, 365)
    )


# ---------------- MAIN LOOP ----------------
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
                if event.key == pygame.K_SPACE:
                    use_sonar()
                elif event.key == pygame.K_ESCAPE:
                    state = "menu"

            elif state in ("won", "lost"):
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if state == "won":
                        level += 1
                    new_level()
                    state = "playing"
                elif event.key == pygame.K_ESCAPE:
                    state = "menu"

    if state == "playing":
        movement = pygame.key.get_pressed()
        dx = 0
        dy = 0

        if movement[pygame.K_a] or movement[pygame.K_LEFT]:
            dx -= player_speed
        if movement[pygame.K_d] or movement[pygame.K_RIGHT]:
            dx += player_speed
        if movement[pygame.K_w] or movement[pygame.K_UP]:
            dy -= player_speed
        if movement[pygame.K_s] or movement[pygame.K_DOWN]:
            dy += player_speed

        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071

        move_player(dx, dy)

        if sonar_cooldown > 0:
            sonar_cooldown -= 1

        if sonar_active:
            sonar_timer -= 1
            sonar_radius += 10

            if sonar_timer <= 0:
                sonar_active = False

        if message_timer > 0:
            message_timer -= 1

        # Collect keys
        for key in keys[:]:
            if player.colliderect(key):
                keys.remove(key)
                keys_collected += 1
                show_message("KEY COLLECTED!", 45)

        # Boss AI
        if boss_health > 0:
            boss_update()

        # Exit is available only after collecting keys and defeating boss
        if player.colliderect(exit_rect):
            if keys_collected < total_keys:
                show_message("COLLECT ALL KEYS FIRST!", 45)
            elif boss_health > 0:
                show_message("DEFEAT THE BOSS FIRST!", 45)
            else:
                state = "won"

    if state == "menu":
        draw_center_screen(
            "SILENT SIGNAL",
            "BOSS FIGHT - ENDLESS MAZE",
            "ENTER: START  |  WASD / ARROWS: MOVE  |  SPACE: SONAR"
        )

    elif state == "playing":
        draw_game()

    elif state == "won":
        draw_center_screen(
            "LEVEL CLEARED!",
            f"You survived level {level}!",
            "ENTER / SPACE: NEXT LEVEL  |  ESC: MENU"
        )

    elif state == "lost":
        draw_center_screen(
            "YOU WERE CAUGHT",
            f"You reached level {level}",
            "ENTER / SPACE: RETRY  |  ESC: MENU"
        )

    pygame.display.flip()

pygame.quit()
sys.exit()
