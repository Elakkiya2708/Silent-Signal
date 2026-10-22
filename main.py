
import pygame
import sys
import math

pygame.init()

WIDTH, HEIGHT = 1000, 650
TILE = 50
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SILENT SIGNAL")
clock = pygame.time.Clock()

BG = (5, 8, 20)
CYAN = (0, 230, 255)
WHITE = (240, 245, 255)
WALL = (24, 43, 65)
GREEN = (50, 255, 150)
RED = (255, 65, 90)
YELLOW = (255, 215, 70)
GREY = (130, 150, 170)

title_font = pygame.font.Font(None, 52)
font = pygame.font.Font(None, 25)

# # wall, P player, K key, E exit, M enemy
maze = [
    "##################",
    "#P...#..........E#",
    "#.##.#.####.###..#",
    "#....K.....#.....#",
    "####.#####.#.##..#",
    "#......#...#.....#",
    "#.####.#.#####.#.#",
    "#..M...#....K...M#",
    "##################",
]

ROWS = len(maze)
COLS = len(maze[0])

OX = (WIDTH - COLS * TILE) // 2
OY = (HEIGHT - ROWS * TILE) // 2

player_x, player_y = 1, 1
keys_found = 0
total_keys = sum(row.count("K") for row in maze)
won = False
lost = False

pulse_radius = 0
pulse_active = False
pulse_max = 330

enemies = [
    {"x": 3, "y": 7, "direction": 1},
    {"x": 16, "y": 7, "direction": -1},
]
enemy_timer = 0


def cell_at(x, y):
    if x < 0 or x >= COLS or y < 0 or y >= ROWS:
        return "#"
    return maze[y][x]


def move_player(dx, dy):
    global player_x, player_y, keys_found, won

    nx, ny = player_x + dx, player_y + dy
    cell = cell_at(nx, ny)

    if cell == "#":
        return

    if cell == "E" and keys_found < total_keys:
        return

    player_x, player_y = nx, ny

    if cell == "K":
        maze[ny] = maze[ny][:nx] + "." + maze[ny][nx + 1:]
        keys_found += 1

    if cell == "E":
        won = True


def update_enemies():
    global enemy_timer, lost

    enemy_timer += 1

    if enemy_timer >= 12:
        enemy_timer = 0

        for enemy in enemies:
            nx = enemy["x"] + enemy["direction"]

            if cell_at(nx, enemy["y"]) == "#":
                enemy["direction"] *= -1
            else:
                enemy["x"] = nx

    for enemy in enemies:
        if enemy["x"] == player_x and enemy["y"] == player_y:
            lost = True


def draw_maze():
    for y, row in enumerate(maze):
        for x, cell in enumerate(row):
            rect = pygame.Rect(
                OX + x * TILE,
                OY + y * TILE,
                TILE - 3,
                TILE - 3,
            )

            distance = math.hypot(
                x - player_x, y - player_y
            ) * TILE

            visible = distance < 60 or (
                pulse_active and distance < pulse_radius
            )

            if cell == "#" and visible:
                pygame.draw.rect(
                    screen, WALL, rect, border_radius=5
                )
                pygame.draw.rect(
                    screen, (35, 75, 100), rect, 1,
                    border_radius=5
                )

            elif cell == "K" and visible:
                cx, cy = rect.center
                pygame.draw.circle(
                    screen, YELLOW, (cx, cy), 9
                )
                pygame.draw.circle(
                    screen, WHITE, (cx, cy), 4
                )

            elif cell == "E":
                pygame.draw.rect(
                    screen,
                    GREEN if keys_found == total_keys else GREY,
                    rect, 3, border_radius=5
                )

            # Enemies are only visible within sonar range
            for enemy in enemies:
                ex, ey = enemy["x"], enemy["y"]
                enemy_distance = math.hypot(
                    ex - player_x, ey - player_y
                ) * TILE

                if (ex == x and ey == y and
                        (enemy_distance < 60 or
                         (pulse_active and
                          enemy_distance < pulse_radius))):
                    pygame.draw.circle(
                        screen, RED, rect.center, 14
                    )

    px = OX + player_x * TILE + TILE // 2
    py = OY + player_y * TILE + TILE // 2
    pygame.draw.circle(screen, CYAN, (px, py), 14)
    pygame.draw.circle(screen, WHITE, (px, py), 5)


def draw_pulse():
    if pulse_active:
        px = OX + player_x * TILE + TILE // 2
        py = OY + player_y * TILE + TILE // 2
        pygame.draw.circle(
            screen, CYAN, (px, py), int(pulse_radius), 2
        )


def draw_ui():
    title = title_font.render("SILENT SIGNAL", True, CYAN)
    screen.blit(title, (25, 15))

    controls = font.render(
        "MOVE: WASD/ARROWS   SONAR: SPACE   QUIT: ESC",
        True, WHITE
    )
    screen.blit(controls, (25, 58))

    key_text = font.render(
        f"KEYS: {keys_found}/{total_keys}", True, YELLOW
    )
    screen.blit(key_text, (25, 92))

    if won:
        message = "ESCAPED! YOU WIN!"
        color = GREEN
    elif lost:
        message = "CAUGHT! Close and restart the game."
        color = RED
    elif keys_found < total_keys:
        message = "Find every key, avoid enemies, then reach EXIT."
        color = GREY
    else:
        message = "All keys collected! Find the EXIT."
        color = GREEN

    status = font.render(message, True, color)
    screen.blit(
        status,
        status.get_rect(center=(WIDTH // 2, HEIGHT - 25))
    )


running = True

while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            elif not won and not lost:
                if event.key in (pygame.K_w, pygame.K_UP):
                    move_player(0, -1)
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    move_player(0, 1)
                elif event.key in (pygame.K_a, pygame.K_LEFT):
                    move_player(-1, 0)
                elif event.key in (pygame.K_d, pygame.K_RIGHT):
                    move_player(1, 0)
                elif event.key == pygame.K_SPACE:
                    pulse_radius = 1
                    pulse_active = True

    if not won and not lost:
        update_enemies()

    if pulse_active:
        pulse_radius += 7
        if pulse_radius >= pulse_max:
            pulse_radius = 0
            pulse_active = False

    screen.fill(BG)
    draw_maze()
    draw_pulse()
    draw_ui()

    if won or lost:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        result = "YOU ESCAPED!" if won else "GAME OVER"
        color = GREEN if won else RED
        result_text = title_font.render(result, True, color)
        screen.blit(
            result_text,
            result_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        )

    pygame.display.flip()

pygame.quit()
sys.exit()
