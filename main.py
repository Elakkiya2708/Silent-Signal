
import pygame
import sys
import math

pygame.init()

# Window
WIDTH, HEIGHT = 1000, 650
TILE = 50
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SILENT SIGNAL | Echoes in the Dark")
clock = pygame.time.Clock()

# Colors
BG = (5, 8, 20)
CYAN = (0, 230, 255)
WHITE = (240, 245, 255)
WALL = (24, 43, 65)
GREEN = (50, 255, 150)
GREY = (100, 130, 150)

title_font = pygame.font.Font(None, 54)
font = pygame.font.Font(None, 25)

# # = Wall, P = Player, E = Exit
maze = [
    "##################",
    "#P....#..........#",
    "#.##..#.####.###.#",
    "#......#....#....#",
    "####.#.####.#.##.#",
    "#....#......#....#",
    "#.######.####.##.#",
    "#...............E#",
    "##################",
]

ROWS = len(maze)
COLS = len(maze[0])

OFFSET_X = (WIDTH - COLS * TILE) // 2
OFFSET_Y = (HEIGHT - ROWS * TILE) // 2

player_x, player_y = 1, 1
pulse_radius = 0
pulse_active = False
won = False


def is_wall(x, y):
    if x < 0 or x >= COLS or y < 0 or y >= ROWS:
        return True
    return maze[y][x] == "#"


def move_player(dx, dy):
    global player_x, player_y, won

    nx = player_x + dx
    ny = player_y + dy

    if not is_wall(nx, ny):
        player_x, player_y = nx, ny

        if maze[ny][nx] == "E":
            won = True


def draw_maze():
    for y, row in enumerate(maze):
        for x, cell in enumerate(row):
            rect = pygame.Rect(
                OFFSET_X + x * TILE,
                OFFSET_Y + y * TILE,
                TILE - 3,
                TILE - 3,
            )

            distance = math.hypot(
                x - player_x, y - player_y
            ) * TILE

            # Nearby tiles and sonar-revealed tiles
            visible = distance < 65 or distance < pulse_radius

            if cell == "#" and visible:
                pygame.draw.rect(
                    screen, WALL, rect, border_radius=5
                )
                pygame.draw.rect(
                    screen, (35, 75, 100), rect,
                    1, border_radius=5
                )

            elif cell == "E":
                if visible:
                    pygame.draw.rect(
                        screen, GREEN, rect, 3,
                        border_radius=5
                    )
                    label = font.render("EXIT", True, GREEN)
                    screen.blit(label, label.get_rect(center=rect.center))

    px = OFFSET_X + player_x * TILE + TILE // 2
    py = OFFSET_Y + player_y * TILE + TILE // 2

    pygame.draw.circle(screen, CYAN, (px, py), 15)
    pygame.draw.circle(screen, WHITE, (px, py), 5)


def draw_sonar():
    if pulse_active and pulse_radius > 0:
        px = OFFSET_X + player_x * TILE + TILE // 2
        py = OFFSET_Y + player_y * TILE + TILE // 2

        pygame.draw.circle(
            screen, CYAN, (px, py), int(pulse_radius), 2
        )


def draw_ui():
    title = title_font.render("SILENT SIGNAL", True, CYAN)
    screen.blit(title, (25, 18))

    controls = font.render(
        "MOVE: WASD / ARROWS     SONAR: SPACE     QUIT: ESC",
        True, WHITE
    )
    screen.blit(controls, (25, 68))

    if won:
        message = title_font.render("YOU ESCAPED!", True, GREEN)
    else:
        message = font.render(
            "Find the exit. Use sound to reveal the maze.",
            True, GREY
        )

    screen.blit(
        message,
        message.get_rect(center=(WIDTH // 2, HEIGHT - 35))
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

            elif not won:
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

    if pulse_active:
        pulse_radius += 6

        if pulse_radius > 330:
            pulse_radius = 0
            pulse_active = False

    screen.fill(BG)
    draw_maze()
    draw_sonar()
    draw_ui()

    pygame.display.flip()

pygame.quit()
sys.exit()
