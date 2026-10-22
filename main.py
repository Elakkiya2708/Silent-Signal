import pygame
import sys
import math
import io
import struct
import wave
import random

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
ORANGE = (255, 165, 65)
PURPLE = (180, 100, 255)

title_font = pygame.font.Font(None, 64)
font = pygame.font.Font(None, 28)
small_font = pygame.font.Font(None, 22)

scene = "menu"
sound_on = True
difficulty = "Medium"

LEVEL = []
ROWS = COLS = 0
OX = OY = 0
player_x = player_y = 1
keys_found = 0
total_keys = 0
won = lost = False
pulse_radius = 0
pulse_active = False
enemy_timer = 0
enemies = []
level_number = 1

# AUDIO
AUDIO_AVAILABLE = True

try:
    pygame.mixer.init(
        frequency=22050,
        size=-16,
        channels=1,
        buffer=512
    )
except pygame.error:
    AUDIO_AVAILABLE = False

ambience_channel = None


def make_sound(duration, frequencies, volume=0.3, kind="tone"):
    sample_rate = 22050
    total = int(sample_rate * duration)
    frames = bytearray()

    for i in range(total):
        t = i / sample_rate
        progress = i / max(total - 1, 1)

        if kind == "ambience":
            fade = min(1.0, progress * 25, (1-progress) * 25)
            value = sum(
                math.sin(2 * math.pi * f * t)
                for f in frequencies
            ) / len(frequencies)
            value *= max(0.0, fade) * volume
        else:
            start_f, end_f = frequencies[0], frequencies[-1]
            phase = 2 * math.pi * (
                start_f * t
                + 0.5 * (end_f-start_f) * t * progress
            )
            value = math.sin(phase) * math.exp(-5*progress) * volume

        frames.extend(struct.pack(
            "<h",
            int(max(-1.0, min(1.0, value)) * 32767)
        ))

    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames)

    buffer.seek(0)
    return pygame.mixer.Sound(file=buffer)


if AUDIO_AVAILABLE:
    try:
        sonar_sound = make_sound(0.55, [950, 320], 0.65)
        stun_sound = make_sound(0.22, [620, 180], 0.5)
        ambience_sound = make_sound(
            4.0, [48, 61, 74], 0.20, "ambience"
        )
        ambience_sound.set_volume(0.45)
    except (pygame.error, ValueError):
        AUDIO_AVAILABLE = False
        sonar_sound = stun_sound = ambience_sound = None
else:
    sonar_sound = stun_sound = ambience_sound = None


def play_sonar():
    if AUDIO_AVAILABLE and sound_on and sonar_sound:
        sonar_sound.play()


def play_stun():
    if AUDIO_AVAILABLE and sound_on and stun_sound:
        stun_sound.play()


def start_ambience():
    global ambience_channel

    if (
        AUDIO_AVAILABLE and sound_on
        and ambience_sound and ambience_channel is None
    ):
        ambience_channel = ambience_sound.play(loops=-1)


def stop_ambience():
    global ambience_channel

    if ambience_channel is not None:
        ambience_channel.stop()
        ambience_channel = None


def update_audio():
    if not AUDIO_AVAILABLE:
        return

    if sound_on and scene == "game" and not won and not lost:
        start_ambience()
    else:
        stop_ambience()


# RANDOM MAZE
def generate_maze():
    global LEVEL, ROWS, COLS, OX, OY, TILE
    global player_x, player_y, total_keys
    global enemies, enemy_timer, keys_found
    global pulse_radius, pulse_active, won, lost

    size = min(11 + (level_number - 1) * 2, 23)

    if size % 2 == 0:
        size += 1

    ROWS = size
    COLS = size + 5

    if COLS % 2 == 0:
        COLS += 1

    TILE = max(
        24,
        min(50, (WIDTH-60)//COLS, (HEIGHT-150)//ROWS)
    )

    OX = (WIDTH-COLS*TILE)//2
    OY = (HEIGHT-ROWS*TILE)//2 + 8

    grid = [["#" for _ in range(COLS)] for _ in range(ROWS)]
    start = (1, 1)
    grid[1][1] = "."

    stack = [start]
    visited = {start}
    directions = [(2, 0), (-2, 0), (0, 2), (0, -2)]

    while stack:
        x, y = stack[-1]
        options = []
        random.shuffle(directions)

        for dx, dy in directions:
            nx, ny = x+dx, y+dy

            if (
                1 <= nx < COLS-1
                and 1 <= ny < ROWS-1
                and (nx, ny) not in visited
            ):
                options.append((nx, ny, dx, dy))

        if options:
            nx, ny, dx, dy = random.choice(options)
            grid[y+dy//2][x+dx//2] = "."
            grid[ny][nx] = "."
            visited.add((nx, ny))
            stack.append((nx, ny))
        else:
            stack.pop()

    distances = {start: 0}
    queue = [start]

    for x, y in queue:
        for dx, dy in ((1,0), (-1,0), (0,1), (0,-1)):
            nx, ny = x+dx, y+dy

            if (
                0 <= nx < COLS and 0 <= ny < ROWS
                and grid[ny][nx] != "#"
                and (nx, ny) not in distances
            ):
                distances[(nx, ny)] = distances[(x,y)] + 1
                queue.append((nx, ny))

    exit_x, exit_y = max(distances, key=distances.get)
    grid[exit_y][exit_x] = "E"

    floor_cells = [
        pos for pos, dist in distances.items()
        if pos != start
        and pos != (exit_x, exit_y)
        and dist >= 5
    ]

    random.shuffle(floor_cells)

    key_count = min(2 + (level_number-1)//3, 5)
    chosen_keys = floor_cells[:key_count]

    for x, y in chosen_keys:
        grid[y][x] = "K"

    enemy_cells = [
        pos for pos, dist in distances.items()
        if pos != start
        and pos != (exit_x, exit_y)
        and pos not in chosen_keys
        and dist >= 7
        and grid[pos[1]][pos[0]] == "."
    ]

    random.shuffle(enemy_cells)

    LEVEL = ["".join(row) for row in grid]
    player_x, player_y = start
    total_keys = len(chosen_keys)

    enemy_count = 1 + level_number // 2

    if difficulty == "Easy":
        enemy_count = max(1, enemy_count-1)
    elif difficulty == "Hard":
        enemy_count += 2

    enemy_count = min(enemy_count, len(enemy_cells), 10)

    enemies = [
        {
            "x": x,
            "y": y,
            "direction": random.choice([-1, 1]),
            "stun": 0
        }
        for x, y in enemy_cells[:enemy_count]
    ]

    keys_found = 0
    enemy_timer = 0
    pulse_radius = 0
    pulse_active = False
    won = lost = False


def cell_at(x, y):
    if x < 0 or x >= COLS or y < 0 or y >= ROWS:
        return "#"
    return LEVEL[y][x]


def move_player(dx, dy):
    global player_x, player_y, keys_found, won

    nx, ny = player_x+dx, player_y+dy
    cell = cell_at(nx, ny)

    if cell == "#":
        return

    if cell == "E" and keys_found < total_keys:
        return

    player_x, player_y = nx, ny

    if cell == "K":
        keys_found += 1

    if cell == "E":
        won = True


def sonar_pulse():
    global pulse_radius, pulse_active

    pulse_radius = 1
    pulse_active = True
    play_sonar()

    for enemy in enemies:
        distance = math.hypot(
            enemy["x"]-player_x,
            enemy["y"]-player_y
        ) * TILE

        if distance <= 250:
            was_stunned = enemy["stun"] <= 0
            enemy["stun"] = max(enemy["stun"], 150)

            if was_stunned:
                play_stun()


def update_enemies():
    global enemy_timer, lost

    enemy_timer += 1

    speed = {
        "Easy": 16,
        "Medium": 12,
        "Hard": 8
    }[difficulty]

    if enemy_timer >= speed:
        enemy_timer = 0

        for enemy in enemies:
            if enemy["stun"] > 0:
                continue

            distance = (
                abs(enemy["x"]-player_x)
                + abs(enemy["y"]-player_y)
            )

            step = None

            chase_range = {
                "Easy": 5,
                "Medium": 7,
                "Hard": 10
            }[difficulty]

            if distance <= chase_range:
                candidates = []

                if player_x < enemy["x"]:
                    candidates.append((-1, 0))
                elif player_x > enemy["x"]:
                    candidates.append((1, 0))

                if player_y < enemy["y"]:
                    candidates.append((0, -1))
                elif player_y > enemy["y"]:
                    candidates.append((0, 1))

                for dx, dy in candidates:
                    if cell_at(
                        enemy["x"]+dx,
                        enemy["y"]+dy
                    ) != "#":
                        step = (dx, dy)
                        break

            if step:
                enemy["x"] += step[0]
                enemy["y"] += step[1]
            else:
                nx = enemy["x"]+enemy["direction"]

                if cell_at(nx, enemy["y"]) == "#":
                    enemy["direction"] *= -1
                else:
                    enemy["x"] = nx

    for enemy in enemies:
        if enemy["stun"] > 0:
            enemy["stun"] -= 1

        if (
            enemy["x"] == player_x
            and enemy["y"] == player_y
            and enemy["stun"] <= 0
        ):
            lost = True


# DRAWING
def draw_text(text, font_obj, color, center):
    image = font_obj.render(text, True, color)
    screen.blit(image, image.get_rect(center=center))


def draw_button(text, rect, mouse_pos):
    color = (
        (20, 65, 85)
        if rect.collidepoint(mouse_pos)
        else (12, 30, 48)
    )

    pygame.draw.rect(screen, color, rect, border_radius=10)
    pygame.draw.rect(screen, CYAN, rect, 2, border_radius=10)
    draw_text(text, font, WHITE, rect.center)


def draw_maze():
    for y, row in enumerate(LEVEL):
        for x, cell in enumerate(row):
            rect = pygame.Rect(
                OX+x*TILE, OY+y*TILE,
                TILE-3, TILE-3
            )

            distance = math.hypot(
                x-player_x, y-player_y
            ) * TILE

            visible = (
                distance < 60
                or (pulse_active and distance < pulse_radius)
            )

            if cell == "#" and visible:
                pygame.draw.rect(
                    screen, WALL, rect, border_radius=4
                )
                pygame.draw.rect(
                    screen, (35, 75, 100), rect, 1
                )

            elif (
                cell == "K" and visible
                and keys_found < total_keys
            ):
                pygame.draw.circle(
                    screen, YELLOW, rect.center,
                    max(5, TILE//5)
                )
                pygame.draw.circle(
                    screen, WHITE, rect.center,
                    max(2, TILE//12)
                )

            elif cell == "E":
                color = GREEN if keys_found == total_keys else GREY
                pygame.draw.rect(
                    screen, color, rect, 3,
                    border_radius=4
                )

    for enemy in enemies:
        distance = math.hypot(
            enemy["x"]-player_x,
            enemy["y"]-player_y
        ) * TILE

        if distance < 60 or (
            pulse_active and distance < pulse_radius
        ):
            center = (
                OX+enemy["x"]*TILE+TILE//2,
                OY+enemy["y"]*TILE+TILE//2
            )

            color = ORANGE if enemy["stun"] > 0 else RED

            pygame.draw.circle(
                screen, color, center, max(7, TILE//3)
            )

            if enemy["stun"] > 0:
                pygame.draw.circle(
                    screen, CYAN, center,
                    max(10, TILE//2-2), 2
                )

    center = (
        OX+player_x*TILE+TILE//2,
        OY+player_y*TILE+TILE//2
    )

    pygame.draw.circle(screen, CYAN, center, max(7, TILE//3))
    pygame.draw.circle(screen, WHITE, center, max(3, TILE//8))


def draw_game():
    screen.fill(BG)

    draw_text(
        "SILENT SIGNAL", title_font, CYAN,
        (WIDTH//2, 35)
    )
    draw_text(f"LEVEL: {level_number}", font, WHITE, (100, 78))
    draw_text(
        f"KEYS: {keys_found}/{total_keys}",
        font, YELLOW, (100, 106)
    )
    draw_text(
        f"MODE: {difficulty.upper()}",
        small_font, PURPLE, (WIDTH-105, 78)
    )

    draw_maze()

    if pulse_active:
        center = (
            OX+player_x*TILE+TILE//2,
            OY+player_y*TILE+TILE//2
        )
        pygame.draw.circle(
            screen, CYAN, center, int(pulse_radius), 2
        )

    draw_text(
        "MOVE: WASD / ARROWS   SPACE: SONAR STUN   ESC: MENU",
        small_font, WHITE, (WIDTH//2, HEIGHT-20)
    )

    if won or lost:
        shade = pygame.Surface(
            (WIDTH, HEIGHT), pygame.SRCALPHA
        )
        shade.fill((0, 0, 0, 190))
        screen.blit(shade, (0, 0))

        message = (
            f"LEVEL {level_number} COMPLETE!"
            if won else "GAME OVER"
        )
        color = GREEN if won else RED

        draw_text(
            message, title_font, color,
            (WIDTH//2, HEIGHT//2-65)
        )

        draw_button(
            "NEXT LEVEL" if won else "TRY AGAIN",
            pygame.Rect(WIDTH//2-120, HEIGHT//2, 240, 52),
            pygame.mouse.get_pos()
        )


def draw_menu():
    screen.fill(BG)

    for radius in (80, 125, 170):
        pygame.draw.circle(
            screen, (10, 45, 65),
            (WIDTH//2, 190), radius, 2
        )

    draw_text(
        "SILENT SIGNAL", title_font, CYAN,
        (WIDTH//2, 180)
    )
    draw_text(
        "THE WORLD IS INVISIBLE. SOUND IS YOUR VISION.",
        small_font, WHITE, (WIDTH//2, 245)
    )

    mouse = pygame.mouse.get_pos()

    start_rect = pygame.Rect(WIDTH//2-130, 300, 260, 52)
    diff_rect = pygame.Rect(WIDTH//2-130, 366, 260, 48)
    sound_rect = pygame.Rect(WIDTH//2-130, 428, 260, 48)
    quit_rect = pygame.Rect(WIDTH//2-130, 490, 260, 48)

    draw_button("START ENDLESS GAME", start_rect, mouse)
    draw_button(
        f"DIFFICULTY: {difficulty.upper()}",
        diff_rect, mouse
    )
    draw_button(
        "SOUND: ON" if sound_on else "SOUND: OFF",
        sound_rect, mouse
    )
    draw_button("QUIT", quit_rect, mouse)

    draw_text(
        "Collect every key, stun enemies, reach the exit.",
        small_font, GREY, (WIDTH//2, 570)
    )

    return start_rect, diff_rect, sound_rect, quit_rect


# MAIN LOOP
generate_maze()
running = True

while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if scene == "game":
                    scene = "menu"
                else:
                    running = False

            elif scene == "game" and not won and not lost:
                if event.key in (pygame.K_w, pygame.K_UP):
                    move_player(0, -1)
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    move_player(0, 1)
                elif event.key in (pygame.K_a, pygame.K_LEFT):
                    move_player(-1, 0)
                elif event.key in (pygame.K_d, pygame.K_RIGHT):
                    move_player(1, 0)
                elif event.key == pygame.K_SPACE:
                    sonar_pulse()

        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            if scene == "menu":
                start_rect, diff_rect, sound_rect, quit_rect = draw_menu()

                if start_rect.collidepoint(event.pos):
                    level_number = 1
                    generate_maze()
                    scene = "game"

                elif diff_rect.collidepoint(event.pos):
                    options = ["Easy", "Medium", "Hard"]
                    difficulty = options[
                        (options.index(difficulty)+1) % len(options)
                    ]

                elif sound_rect.collidepoint(event.pos):
                    sound_on = not sound_on
                    if not sound_on:
                        stop_ambience()

                elif quit_rect.collidepoint(event.pos):
                    running = False

            elif scene == "game" and (won or lost):
                action_rect = pygame.Rect(
                    WIDTH//2-120, HEIGHT//2, 240, 52
                )

                if action_rect.collidepoint(event.pos):
                    if won:
                        level_number += 1

                    generate_maze()

    if scene == "game":
        if not won and not lost:
            update_enemies()

        if pulse_active:
            pulse_radius += 7

            if pulse_radius >= 330:
                pulse_radius = 0
                pulse_active = False

        update_audio()
        draw_game()

    else:
        update_audio()
        draw_menu()

    pygame.display.flip()

stop_ambience()
pygame.quit()
sys.exit()