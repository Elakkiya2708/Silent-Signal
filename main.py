
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

title_font = pygame.font.Font(None, 64)
font = pygame.font.Font(None, 28)
small_font = pygame.font.Font(None, 22)

LEVEL = [
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

ROWS = len(LEVEL)
COLS = len(LEVEL[0])
OX = (WIDTH - COLS * TILE) // 2
OY = (HEIGHT - ROWS * TILE) // 2

scene = "menu"
sound_on = True
player_x, player_y = 1, 1
keys_found = 0
total_keys = 2
won = False
lost = False
pulse_radius = 0
pulse_active = False
enemy_timer = 0
enemies = []


def reset_game():
    global player_x, player_y, keys_found
    global won, lost, pulse_radius, pulse_active
    global enemies, enemy_timer

    player_x, player_y = 1, 1
    keys_found = 0
    won = lost = False
    pulse_radius = 0
    pulse_active = False
    enemy_timer = 0

    enemies = [
        {"x": 3, "y": 7, "direction": 1},
        {"x": 16, "y": 7, "direction": -1},
    ]


def cell_at(x, y):
    if x < 0 or x >= COLS or y < 0 or y >= ROWS:
        return "#"
    return LEVEL[y][x]


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


def draw_text(text, font_obj, color, center):
    image = font_obj.render(text, True, color)
    screen.blit(image, image.get_rect(center=center))


def draw_button(text, rect, mouse_pos):
    color = (20, 65, 85) if rect.collidepoint(mouse_pos) else (12, 30, 48)
    pygame.draw.rect(screen, color, rect, border_radius=10)
    pygame.draw.rect(screen, CYAN, rect, 2, border_radius=10)
    draw_text(text, font, WHITE, rect.center)


def draw_maze():
    for y, row in enumerate(LEVEL):
        for x, cell in enumerate(row):
            rect = pygame.Rect(
                OX + x * TILE, OY + y * TILE,
                TILE - 3, TILE - 3
            )

            distance = math.hypot(
                x - player_x, y - player_y
            ) * TILE

            visible = distance < 60 or (
                pulse_active and distance < pulse_radius
            )

            if cell == "#" and visible:
                pygame.draw.rect(screen, WALL, rect, border_radius=5)
                pygame.draw.rect(screen, (35, 75, 100), rect, 1)

            elif cell == "K" and visible and keys_found < total_keys:
                pygame.draw.circle(screen, YELLOW, rect.center, 9)
                pygame.draw.circle(screen, WHITE, rect.center, 3)

            elif cell == "E":
                exit_color = GREEN if keys_found == total_keys else GREY
                pygame.draw.rect(screen, exit_color, rect, 3, border_radius=5)

    for enemy in enemies:
        distance = math.hypot(
            enemy["x"] - player_x,
            enemy["y"] - player_y
        ) * TILE

        if distance < 60 or (pulse_active and distance < pulse_radius):
            center = (
                OX + enemy["x"] * TILE + TILE // 2,
                OY + enemy["y"] * TILE + TILE // 2
            )
            pygame.draw.circle(screen, RED, center, 14)

    center = (
        OX + player_x * TILE + TILE // 2,
        OY + player_y * TILE + TILE // 2
    )
    pygame.draw.circle(screen, CYAN, center, 14)
    pygame.draw.circle(screen, WHITE, center, 5)


def draw_game():
    screen.fill(BG)

    draw_text("SILENT SIGNAL", title_font, CYAN, (WIDTH // 2, 40))
    draw_text(
        f"KEYS: {keys_found}/{total_keys}",
        font, YELLOW, (100, 95)
    )

    draw_maze()

    if pulse_active:
        center = (
            OX + player_x * TILE + TILE // 2,
            OY + player_y * TILE + TILE // 2
        )
        pygame.draw.circle(
            screen, CYAN, center, int(pulse_radius), 2
        )

    draw_text(
        "MOVE: WASD / ARROWS    SPACE: SONAR    ESC: MENU",
        small_font, WHITE, (WIDTH // 2, HEIGHT - 18)
    )

    if won or lost:
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 185))
        screen.blit(shade, (0, 0))

        draw_text(
            "YOU ESCAPED!" if won else "GAME OVER",
            title_font, GREEN if won else RED,
            (WIDTH // 2, HEIGHT // 2 - 65)
        )

        draw_button(
            "PLAY AGAIN",
            pygame.Rect(WIDTH // 2 - 110, HEIGHT // 2, 220, 52),
            pygame.mouse.get_pos()
        )


def draw_menu():
    screen.fill(BG)

    # Decorative sonar rings
    for radius in (80, 125, 170):
        pygame.draw.circle(
            screen, (10, 45, 65),
            (WIDTH // 2, 205), radius, 2
        )

    draw_text("SILENT SIGNAL", title_font, CYAN, (WIDTH // 2, 190))
    draw_text(
        "THE WORLD IS INVISIBLE. SOUND IS YOUR VISION.",
        small_font, WHITE, (WIDTH // 2, 255)
    )

    mouse = pygame.mouse.get_pos()

    start_rect = pygame.Rect(WIDTH // 2 - 120, 330, 240, 55)
    sound_rect = pygame.Rect(WIDTH // 2 - 120, 400, 240, 48)
    quit_rect = pygame.Rect(WIDTH // 2 - 120, 462, 240, 48)

    draw_button("START GAME", start_rect, mouse)
    draw_button(
        "SOUND: ON" if sound_on else "SOUND: OFF",
        sound_rect, mouse
    )
    draw_button("QUIT", quit_rect, mouse)

    draw_text(
        "Collect all keys. Avoid enemies. Find the exit.",
        small_font, GREY, (WIDTH // 2, 555)
    )

    return start_rect, sound_rect, quit_rect


reset_game()
running = True

while running:
    clock.tick(FPS)
    mouse = pygame.mouse.get_pos()

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
    pulse_radius = 1
    pulse_active = True
    play_sonar()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if scene == "menu":
                start_rect, sound_rect, quit_rect = draw_menu()

                if start_rect.collidepoint(event.pos):
                    reset_game()
                    scene = "game"
                elif sound_rect.collidepoint(event.pos):
    sound_on = not sound_on

    if not sound_on:
        stop_ambience()
                elif quit_rect.collidepoint(event.pos):
                    running = False

            elif scene == "game" and (won or lost):
                replay_rect = pygame.Rect(
                    WIDTH // 2 - 110, HEIGHT // 2, 220, 52
                )
                if replay_rect.collidepoint(event.pos):
                    reset_game()

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
        draw_menu()

    pygame.display.flip()

pygame.quit()
sys.exit()

# Audio setup
AUDIO_AVAILABLE = True

try:
    pygame.mixer.init()
except pygame.error:
    AUDIO_AVAILABLE = False

sound_on = True

def play_sound(frequency=700, duration=120):
    """Generate a simple sonar beep without external audio files."""
    if not AUDIO_AVAILABLE or not sound_on:
        return

    # Placeholder for generated audio.
    # Pygame mixer can play loaded sounds; this function is safe
    # when no audio assets are present.
    pass

import io
import math
import struct
import wave

# Audio setup: generate sound without external files
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    AUDIO_AVAILABLE = True
except pygame.error:
    AUDIO_AVAILABLE = False

sound_on = True
ambience_channel = None


def make_sound(duration, frequencies, volume=0.3, kind="tone"):
    """Generate a sound procedurally using the standard library."""
    sample_rate = 22050
    total = int(sample_rate * duration)
    frames = bytearray()

    for i in range(total):
        t = i / sample_rate
        progress = i / max(total - 1, 1)

        if kind == "ambience":
            # Soft fade at the start and end for a smoother loop
            fade = min(1.0, progress * 25, (1.0 - progress) * 25)
            envelope = max(0.0, fade) * (
                0.75 + 0.25 * math.sin(2 * math.pi * 0.25 * t)
            )
            value = sum(
                math.sin(2 * math.pi * f * t) for f in frequencies
            ) / len(frequencies)
            value *= envelope * volume
        else:
            # Sonar chirp that falls in pitch and fades away
            envelope = math.exp(-5 * progress)
            start_f = frequencies[0]
            end_f = frequencies[-1]
            current_f = start_f + (end_f - start_f) * progress
            value = math.sin(2 * math.pi * current_f * t)
            value *= envelope * volume

        sample = int(max(-1.0, min(1.0, value)) * 32767)
        frames.extend(struct.pack("<h", sample))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames)

    return pygame.mixer.Sound(file=io.BytesIO(buffer.getvalue()))


if AUDIO_AVAILABLE:
    sonar_sound = make_sound(
        0.55, [950, 320], volume=0.65
    )
    ambience_sound = make_sound(
        4.0, [48, 61, 74], volume=0.20, kind="ambience"
    )
    sonar_sound.set_volume(0.65)
    ambience_sound.set_volume(0.45)
else:
    sonar_sound = None
    ambience_sound = None


def play_sonar():
    if AUDIO_AVAILABLE and sound_on:
        sonar_sound.play()


def start_ambience():
    global ambience_channel

    if AUDIO_AVAILABLE and sound_on and ambience_channel is None:
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
