
import pygame
import random
import math
import json
import os
import sys
import io
import wave
import struct
from collections import deque

# =====================================================
# SILENT SIGNAL - HORROR SURVIVAL WITH SOUND
# =====================================================

pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()

WIDTH, HEIGHT = 900, 700
HUD = 100
TILE = 32
FPS = 60
SAVE_FILE = "silent_signal_save.json"

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SILENT SIGNAL | Horror Survival")
clock = pygame.time.Clock()

WHITE = (240, 245, 255)
BLACK = (5, 7, 13)
WALL = (38, 45, 60)
FLOOR = (17, 21, 30)
CYAN = (40, 225, 245)
RED = (240, 45, 70)
GREEN = (65, 235, 130)
GOLD = (255, 215, 65)
PURPLE = (175, 70, 235)
ORANGE = (255, 145, 35)
BLUE = (75, 150, 255)

font = pygame.font.SysFont("consolas", 18)
small = pygame.font.SysFont("consolas", 14)
big = pygame.font.SysFont("consolas", 43, bold=True)

# =====================================================
# PROCEDURAL AUDIO - NO EXTERNAL FILES REQUIRED
# =====================================================

SOUND_AVAILABLE = pygame.mixer.get_init() is not None
sound_on = True
sounds = {}
ambient_channel = None


def make_sound(freq=440, duration=0.2, volume=0.3,
               wave_type="sine", slide=0, noise=0.0):
    """Generate a short sound effect in memory."""
    if not SOUND_AVAILABLE:
        return None

    rate = 22050
    count = max(1, int(rate * duration))
    buffer = io.BytesIO()

    try:
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)

            samples = bytearray()

            for i in range(count):
                t = i / rate
                progress = i / count
                current_freq = max(20, freq + slide * progress)

                if wave_type == "square":
                    sample = 1.0 if math.sin(
                        2 * math.pi * current_freq * t
                    ) >= 0 else -1.0
                elif wave_type == "saw":
                    sample = 2 * (
                        (current_freq * t) % 1.0
                    ) - 1.0
                else:
                    sample = math.sin(
                        2 * math.pi * current_freq * t
                    )

                if noise:
                    sample = sample * (1 - noise) + (
                        random.uniform(-1, 1) * noise
                    )

                # Fade at both ends to avoid audio clicks.
                fade_in = min(1.0, i / max(1, rate * 0.015))
                fade_out = min(
                    1.0, (count - i) / max(1, rate * 0.04)
                )

                sample *= volume * fade_in * fade_out
                sample = max(-1, min(1, sample))
                samples.extend(struct.pack("<h", int(sample * 32767)))

            wav.writeframes(samples)

        buffer.seek(0)
        return pygame.mixer.Sound(file=buffer)

    except (pygame.error, OSError, ValueError):
        return None


def init_sounds():
    global sounds

    sounds = {
        "sonar": make_sound(180, 0.45, 0.45, "sine", 900),
        "pulse": make_sound(700, 0.20, 0.35, "square", -400),
        "boss_hit": make_sound(100, 0.35, 0.45, "saw", -65, 0.15),
        "boss_attack": make_sound(130, 0.25, 0.4, "square", -60),
        "key": make_sound(880, 0.18, 0.28, "sine", 350),
        "data": make_sound(600, 0.28, 0.28, "sine", 700),
        "health": make_sound(520, 0.30, 0.30, "sine", 480),
        "speed": make_sound(300, 0.30, 0.30, "saw", 850),
        "flashlight": make_sound(420, 0.25, 0.28, "sine", 250),
        "save": make_sound(600, 0.14, 0.25, "sine", 200),
        "win": make_sound(440, 0.65, 0.30, "sine", 600),
        "lose": make_sound(240, 0.75, 0.38, "saw", -180),
        "jumpscare": make_sound(85, 0.70, 0.60, "saw", 900, 0.55),
        "footstep": make_sound(75, 0.055, 0.10, "sine", -20),
        "pickup": make_sound(500, 0.12, 0.22, "sine", 250),
    }


def play_sound(name):
    if not sound_on or not SOUND_AVAILABLE:
        return

    sound = sounds.get(name)
    if sound:
        try:
            sound.play()
        except pygame.error:
            pass


def start_ambience():
    """Loop a quiet, low-frequency horror drone."""
    global ambient_channel

    if not SOUND_AVAILABLE or not sound_on:
        return

    if ambient_channel is not None:
        try:
            ambient_channel.stop()
        except pygame.error:
            pass

    ambient = make_sound(
        48, 3.0, 0.12, "sine", 7, noise=0.12
    )

    if ambient:
        try:
            ambient_channel = pygame.mixer.Channel(0)
            ambient_channel.play(ambient, loops=-1)
            ambient_channel.set_volume(0.55)
            # Keep a reference so the generated Sound stays alive.
            sounds["ambient"] = ambient
        except pygame.error:
            ambient_channel = None


def toggle_sound():
    global sound_on

    sound_on = not sound_on

    if not SOUND_AVAILABLE:
        show_message("AUDIO DEVICE UNAVAILABLE")
        return

    if sound_on:
        start_ambience()
        show_message("SOUND ON")
    else:
        pygame.mixer.stop()
        show_message("SOUND MUTED")


if SOUND_AVAILABLE:
    init_sounds()
    start_ambience()


# =====================================================
# GAME STATE
# =====================================================

state = "menu"
level = 1

ROWS, COLS = 17, 23
maze = []

player = pygame.Rect(0, 0, 20, 20)
player_health = 100
player_speed = 2.5
player_energy = 100

boss_x = 0.0
boss_y = 0.0
boss_health = 100
boss_max_health = 100
boss_speed = 0.8
boss_stun = 0
boss_attack_timer = 0

keys = []
data_files = []
total_keys = 3
keys_collected = 0
data_collected = 0
total_data = 2

exit_rect = pygame.Rect(0, 0, TILE, TILE)

inventory = {"health": 0, "speed": 0, "flashlight": 0}
powerups = []

speed_timer = 0
flashlight_timer = 0
sonar_cooldown = 0
sonar_active = False
sonar_radius = 0
pulse_cooldown = 0

message = ""
message_timer = 0
shake_timer = 0
jumpscare_timer = 0
jumpscare_cooldown = 600
flash_timer = 0

footstep_timer = 0
story_text = []
story_index = 0


# =====================================================
# UTILITIES
# =====================================================

def show_message(text, duration=120):
    global message, message_timer
    message = text
    message_timer = duration


def cell_center(cell):
    x, y = cell
    return x * TILE + TILE // 2, y * TILE + TILE // 2 + HUD


def is_wall_pixel(x, y):
    col = int(x // TILE)
    row = int((y - HUD) // TILE)

    if row < 0 or row >= ROWS or col < 0 or col >= COLS:
        return True

    return maze[row][col] == 1


def random_floor(excluded, min_distance=0):
    candidates = []

    for y in range(1, ROWS - 1):
        for x in range(1, COLS - 1):
            if maze[y][x] != 0 or (x, y) in excluded:
                continue

            distance = abs(x - 1) + abs(y - 1)
            if distance >= min_distance:
                candidates.append((x, y))

    return random.choice(candidates) if candidates else (1, 1)


def farthest_cell(start=(1, 1)):
    queue = deque([(start[0], start[1], 0)])
    visited = {start}
    farthest = start
    maximum = 0

    while queue:
        x, y, dist = queue.popleft()

        if dist > maximum:
            maximum = dist
            farthest = (x, y)

        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy

            if (0 <= nx < COLS and 0 <= ny < ROWS
                    and maze[ny][nx] == 0
                    and (nx, ny) not in visited):
                visited.add((nx, ny))
                queue.append((nx, ny, dist + 1))

    return farthest


# =====================================================
# MAZE
# =====================================================

def generate_maze():
    global ROWS, COLS, maze

    ROWS = min(17 + (level - 1) * 2, 23)
    COLS = min(23 + (level - 1) * 2, 31)

    if ROWS % 2 == 0:
        ROWS += 1
    if COLS % 2 == 0:
        COLS += 1

    while COLS * TILE > WIDTH:
        COLS -= 2

    while ROWS * TILE > HEIGHT - HUD:
        ROWS -= 2

    maze = [[1] * COLS for _ in range(ROWS)]
    maze[1][1] = 0
    stack = [(1, 1)]

    while stack:
        x, y = stack[-1]
        choices = []

        for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
            nx, ny = x + dx, y + dy

            if (1 <= nx < COLS - 1 and
                    1 <= ny < ROWS - 1 and maze[ny][nx] == 1):
                choices.append((nx, ny, dx, dy))

        if choices:
            nx, ny, dx, dy = random.choice(choices)
            maze[y + dy // 2][x + dx // 2] = 0
            maze[ny][nx] = 0
            stack.append((nx, ny))
        else:
            stack.pop()


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


# =====================================================
# STORY AND MISSIONS
# =====================================================

def get_story():
    if level == 1:
        return [
            "CHAPTER 1: THE SIGNAL",
            "You wake inside an abandoned research facility.",
            "A strange signal echoes through dark corridors.",
            "Collect access keys and recover missing research data.",
            "An experiment is hunting you. Find a way out."
        ]

    return [
        f"CHAPTER {level}: DEEPER INTO THE FACILITY",
        "The signal grows louder in this new sector.",
        "The security experiment has become more dangerous.",
        "Recover the data and unlock the exit.",
        "Survive the facility. Discover the truth."
    ]


def current_mission():
    if keys_collected < total_keys:
        return "MISSION 1: COLLECT ACCESS KEYS"

    if data_collected < total_data:
        return "MISSION 2: RECOVER RESEARCH DATA"

    if boss_health > 0:
        return "MISSION 3: DEFEAT THE EXPERIMENT"

    return "MISSION 4: ESCAPE THROUGH THE EXIT"


def start_story():
    global state, story_text, story_index
    story_text = get_story()
    story_index = 0
    state = "story"


# =====================================================
# LEVEL SETUP
# =====================================================

def new_level():
    global player, player_health, player_energy
    global keys, data_files, keys_collected, data_collected
    global total_keys, total_data, exit_rect
    global boss_x, boss_y, boss_health, boss_max_health
    global boss_speed, boss_stun, boss_attack_timer
    global powerups, inventory, speed_timer, flashlight_timer
    global sonar_cooldown, sonar_active, sonar_radius
    global pulse_cooldown, jumpscare_timer, jumpscare_cooldown
    global footstep_timer, shake_timer, flash_timer

    generate_maze()

    sx, sy = cell_center((1, 1))
    player = pygame.Rect(sx - 10, sy - 10, 20, 20)

    end_cell = farthest_cell()
    ex, ey = cell_center(end_cell)
    exit_rect = pygame.Rect(ex - 13, ey - 13, 26, 26)

    excluded = {(1, 1), end_cell}

    total_keys = min(3 + (level - 1) // 2, 6)
    total_data = min(2 + (level - 1) // 3, 4)
    keys_collected = 0
    data_collected = 0
    keys = []
    data_files = []

    for _ in range(total_keys):
        cell = random_floor(excluded, 4)
        excluded.add(cell)
        x, y = cell_center(cell)
        keys.append(pygame.Rect(x - 6, y - 6, 12, 12))

    for _ in range(total_data):
        cell = random_floor(excluded, 5)
        excluded.add(cell)
        x, y = cell_center(cell)
        data_files.append(pygame.Rect(x - 7, y - 7, 14, 14))

    boss_cell = random_floor(excluded, 7)
    excluded.add(boss_cell)
    boss_x, boss_y = map(float, cell_center(boss_cell))

    boss_max_health = 100 + (level - 1) * 25
    boss_health = boss_max_health
    boss_speed = min(0.75 + level * 0.09, 1.7)
    boss_stun = 0
    boss_attack_timer = 0

    powerups = []

    for kind in ["health", "speed", "flashlight", "health", "speed"]:
        cell = random_floor(excluded, 3)
        excluded.add(cell)
        x, y = cell_center(cell)
        powerups.append({
            "kind": kind,
            "rect": pygame.Rect(x - 9, y - 9, 18, 18)
        })

    inventory = {"health": 0, "speed": 0, "flashlight": 0}
    player_health = 100
    player_energy = 100
    speed_timer = 0
    flashlight_timer = 0
    sonar_cooldown = 0
    sonar_active = False
    sonar_radius = 0
    pulse_cooldown = 0
    jumpscare_timer = 0
    jumpscare_cooldown = 600
    footstep_timer = 0
    shake_timer = 0
    flash_timer = 0

    show_message(f"CHAPTER {level}: THE SIGNAL CONTINUES", 180)


# =====================================================
# INVENTORY AND POWER-UPS
# =====================================================

def activate_powerup(slot):
    global player_health, speed_timer, flashlight_timer

    if slot == 1:
        if inventory["health"] <= 0:
            show_message("NO HEALTH PACK AVAILABLE!")
        elif player_health >= 100:
            show_message("HEALTH IS ALREADY FULL!")
        else:
            player_health = min(100, player_health + 40)
            inventory["health"] -= 1
            play_sound("health")
            show_message("HEALTH PACK USED: +40 HP!")

    elif slot == 2:
        if inventory["speed"] <= 0:
            show_message("NO SPEED BOOST AVAILABLE!")
        else:
            speed_timer = 600
            inventory["speed"] -= 1
            play_sound("speed")
            show_message("SPEED BOOST ACTIVATED!")

    elif slot == 3:
        if inventory["flashlight"] <= 0:
            show_message("NO FLASHLIGHT AVAILABLE!")
        else:
            flashlight_timer = 900
            inventory["flashlight"] -= 1
            play_sound("flashlight")
            show_message("FLASHLIGHT ACTIVATED!")


def collect_powerups():
    for item in powerups[:]:
        if player.colliderect(item["rect"]):
            kind = item["kind"]
            inventory[kind] += 1
            powerups.remove(item)
            play_sound(kind)
            show_message(f"POWER-UP COLLECTED: {kind.upper()}!")


# =====================================================
# SONAR AND PULSE WEAPON
# =====================================================

def use_sonar():
    global sonar_cooldown, sonar_active, sonar_radius
    global boss_health, boss_stun, shake_timer

    if sonar_cooldown > 0:
        show_message("SONAR IS RECHARGING!")
        return

    sonar_cooldown = 100
    sonar_active = True
    sonar_radius = 0
    play_sound("sonar")

    px, py = player.center
    distance = math.hypot(px - boss_x, py - boss_y)

    if boss_health > 0 and distance <= 190:
        boss_health = max(0, boss_health - 25)
        boss_stun = 75
        shake_timer = 8
        play_sound("boss_hit")
        show_message("SONAR HIT! BOSS STUNNED!")

        if boss_health == 0:
            play_sound("win")
            show_message("BOSS DEFEATED! FIND THE EXIT!", 180)
    else:
        show_message("SONAR PULSE RELEASED!")


def use_pulse_weapon():
    global player_energy, pulse_cooldown
    global boss_health, boss_stun, shake_timer

    if pulse_cooldown > 0:
        show_message("WEAPON RECHARGING!")
        return

    if player_energy < 25:
        show_message("NOT ENOUGH ENERGY!")
        return

    player_energy -= 25
    pulse_cooldown = 45
    play_sound("pulse")

    px, py = player.center
    distance = math.hypot(px - boss_x, py - boss_y)

    if boss_health > 0 and distance <= 150:
        boss_health = max(0, boss_health - 15)
        boss_stun = max(boss_stun, 20)
        shake_timer = 5
        play_sound("boss_hit")
        show_message("PULSE WEAPON HIT THE BOSS!")

        if boss_health == 0:
            play_sound("win")
            show_message("BOSS DEFEATED!", 180)
    else:
        show_message("PULSE FIRED - NO TARGET IN RANGE!")


# =====================================================
# BOSS AI
# =====================================================

def update_boss():
    global boss_x, boss_y, boss_stun
    global boss_attack_timer, player_health, state, shake_timer

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

        if (not is_wall_pixel(nx - 14, boss_y - 14)
                and not is_wall_pixel(nx + 14, boss_y + 14)):
            boss_x = nx

        if (not is_wall_pixel(boss_x - 14, ny - 14)
                and not is_wall_pixel(boss_x + 14, ny + 14)):
            boss_y = ny

    if boss_attack_timer > 0:
        boss_attack_timer -= 1

    boss_rect = pygame.Rect(
        int(boss_x - 15), int(boss_y - 15), 30, 30
    )

    if player.colliderect(boss_rect) and boss_attack_timer <= 0:
        player_health -= 15
        boss_attack_timer = 55
        shake_timer = 10
        play_sound("boss_attack")
        show_message("THE EXPERIMENT ATTACKED YOU!")

        if player_health <= 0:
            player_health = 0
            play_sound("lose")
            state = "lost"


# =====================================================
# SAVE AND LOAD
# =====================================================

def save_game():
    data = {
        "level": level,
        "player_health": player_health,
        "player_energy": player_energy,
        "keys_collected": keys_collected,
        "data_collected": data_collected,
        "inventory": inventory
    }

    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

        play_sound("save")
        show_message("PROGRESS SAVED!")

    except OSError:
        show_message("COULD NOT SAVE GAME!")


def load_game():
    global level

    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        level = max(1, int(data.get("level", 1)))
        new_level()
        show_message("CHAPTER LOADED. START PLAYING!", 180)
        return True

    except (OSError, ValueError, json.JSONDecodeError):
        show_message("NO VALID SAVE FOUND!")
        return False


# =====================================================
# DRAWING
# =====================================================

def draw_bar(x, y, width, height, value, maximum, color):
    pygame.draw.rect(screen, (75, 25, 38), (x, y, width, height))
    fill = int(width * max(0, value) / max(1, maximum))

    if fill > 0:
        pygame.draw.rect(screen, color, (x, y, fill, height))


def draw_maze():
    for y in range(ROWS):
        for x in range(COLS):
            rect = pygame.Rect(
                x * TILE, y * TILE + HUD, TILE, TILE
            )

            if maze[y][x] == 1:
                pygame.draw.rect(screen, WALL, rect)
                pygame.draw.rect(screen, (53, 62, 78), rect, 1)
            else:
                pygame.draw.rect(screen, FLOOR, rect)
                pygame.draw.rect(screen, (25, 31, 41), rect, 1)


def draw_hud():
    pygame.draw.rect(screen, (8, 12, 21), (0, 0, WIDTH, HUD))

    screen.blit(font.render("SILENT SIGNAL", True, CYAN), (12, 7))
    screen.blit(small.render(f"CHAPTER {level}", True, WHITE), (12, 34))
    screen.blit(
        small.render(f"KEYS {keys_collected}/{total_keys}", True, GOLD),
        (12, 56)
    )
    screen.blit(
        small.render(f"DATA {data_collected}/{total_data}", True, BLUE),
        (12, 76)
    )

    screen.blit(small.render("HEALTH", True, WHITE), (190, 8))
    draw_bar(250, 10, 110, 12, player_health, 100, GREEN)

    screen.blit(small.render("BOSS", True, WHITE), (380, 8))
    draw_bar(425, 10, 120, 12, boss_health, boss_max_health, PURPLE)

    screen.blit(small.render("ENERGY", True, WHITE), (565, 8))
    draw_bar(630, 10, 100, 12, player_energy, 100, CYAN)

    screen.blit(small.render("INVENTORY", True, CYAN), (190, 35))
    screen.blit(
        small.render(f"1 Health x{inventory['health']}", True, GREEN),
        (285, 35)
    )
    screen.blit(
        small.render(f"2 Speed x{inventory['speed']}", True, CYAN),
        (425, 35)
    )
    screen.blit(
        small.render(f"3 Light x{inventory['flashlight']}", True, GOLD),
        (555, 35)
    )

    screen.blit(
        small.render(
            "SPACE Sonar | F Pulse | P Save | L Load | M Sound | ESC Menu",
            True, ORANGE
        ),
        (190, 63)
    )

    status = "ON" if sound_on else "OFF"
    screen.blit(
        small.render(f"SOUND: {status} | {current_mission()}", True, WHITE),
        (190, 82)
    )


def draw_powerups():
    for item in powerups:
        kind = item["kind"]
        color = {
            "health": GREEN,
            "speed": CYAN,
            "flashlight": GOLD
        }[kind]

        pygame.draw.rect(
            screen, color, item["rect"], border_radius=4
        )

        letter = {
            "health": "H",
            "speed": "S",
            "flashlight": "F"
        }[kind]

        label = small.render(letter, True, BLACK)
        screen.blit(label, (
            item["rect"].centerx - label.get_width() // 2,
            item["rect"].centery - label.get_height() // 2
        ))


def draw_game():
    screen.fill(BLACK)
    draw_maze()

    for key in keys:
        pygame.draw.circle(screen, GOLD, key.center, 6)
        pygame.draw.circle(screen, WHITE, key.center, 2)

    for data in data_files:
        pygame.draw.rect(screen, BLUE, data, border_radius=3)
        pygame.draw.rect(screen, WHITE, data, 1, border_radius=3)

    draw_powerups()

    exit_color = (
        GREEN if keys_collected == total_keys
        and data_collected == total_data and boss_health <= 0
        else RED
    )

    pygame.draw.rect(screen, exit_color, exit_rect, border_radius=4)
    pygame.draw.rect(screen, WHITE, exit_rect, 2, border_radius=4)

    if boss_health > 0:
        boss_rect = pygame.Rect(
            int(boss_x - 15), int(boss_y - 15), 30, 30
        )

        color = ORANGE if boss_stun > 0 else PURPLE
        pygame.draw.rect(screen, color, boss_rect, border_radius=6)
        pygame.draw.rect(screen, RED, boss_rect, 2, border_radius=6)

        pygame.draw.circle(
            screen, WHITE, (int(boss_x - 6), int(boss_y - 4)), 3
        )
        pygame.draw.circle(
            screen, WHITE, (int(boss_x + 6), int(boss_y - 4)), 3
        )

    pygame.draw.rect(screen, CYAN, player, border_radius=5)
    pygame.draw.rect(screen, WHITE, player, 2, border_radius=5)

    if sonar_active:
        pygame.draw.circle(
            screen, CYAN, player.center, int(sonar_radius), 2
        )

    # Darkness and flashlight
    darkness = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    darkness.fill((0, 0, 0, 238))

    radius = 225 if flashlight_timer > 0 else 115
    pygame.draw.circle(
        darkness, (0, 0, 0, 0), player.center, radius
    )

    if boss_health > 0:
        pygame.draw.circle(
            darkness, (0, 0, 0, 0),
            (int(boss_x), int(boss_y)), 36
        )

    screen.blit(darkness, (0, 0))

    if flash_timer > 0:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((150, 0, 15, 65))
        screen.blit(overlay, (0, 0))

    draw_hud()

    if message_timer > 0:
        label = font.render(message, True, GOLD)
        screen.blit(
            label,
            (WIDTH // 2 - label.get_width() // 2, HEIGHT - 26)
        )

    # Jumpscare
    if jumpscare_timer > 0:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((60, 0, 10, 190))
        screen.blit(overlay, (0, 0))

        face = pygame.Rect(
            WIDTH // 2 - 115, HEIGHT // 2 - 120, 230, 240
        )

        pygame.draw.ellipse(screen, (15, 0, 5), face)
        pygame.draw.ellipse(screen, RED, face, 5)

        pygame.draw.ellipse(
            screen, WHITE, (face.x + 35, face.y + 55, 55, 55)
        )
        pygame.draw.ellipse(
            screen, WHITE, (face.x + 140, face.y + 55, 55, 55)
        )

        pygame.draw.circle(
            screen, RED, (face.x + 62, face.y + 82), 15
        )
        pygame.draw.circle(
            screen, RED, (face.x + 167, face.y + 82), 15
        )

        pygame.draw.ellipse(
            screen, RED, (face.x + 55, face.y + 135, 120, 65)
        )

        pygame.draw.rect(
            screen, WHITE, (face.x + 75, face.y + 140, 20, 28)
        )
        pygame.draw.rect(
            screen, WHITE, (face.x + 130, face.y + 140, 20, 28)
        )


def draw_center(title, subtitle, lines):
    screen.fill(BLACK)

    title_img = big.render(title, True, CYAN)
    screen.blit(
        title_img,
        (WIDTH // 2 - title_img.get_width() // 2, 175)
    )

    sub = font.render(subtitle, True, WHITE)
    screen.blit(
        sub, (WIDTH // 2 - sub.get_width() // 2, 250)
    )

    for i, line in enumerate(lines):
        img = small.render(line, True, GOLD)
        screen.blit(
            img,
            (WIDTH // 2 - img.get_width() // 2, 315 + i * 26)
        )


# =====================================================
# MAIN GAME LOOP
# =====================================================

running = True

while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_m:
                toggle_sound()

            if state == "menu":
                if event.key == pygame.K_RETURN:
                    level = 1
                    new_level()
                    start_story()

                elif event.key == pygame.K_l:
                    if load_game():
                        start_story()

                elif event.key == pygame.K_ESCAPE:
                    running = False

            elif state == "story":
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    story_index += 1

                    if story_index >= len(story_text):
                        state = "playing"
                        show_message("MISSION STARTED!", 100)

                elif event.key == pygame.K_ESCAPE:
                    state = "menu"

            elif state == "playing":
                if event.key == pygame.K_ESCAPE:
                    state = "menu"

                elif event.key == pygame.K_SPACE:
                    use_sonar()

                elif event.key == pygame.K_f:
                    use_pulse_weapon()

                elif event.key == pygame.K_1:
                    activate_powerup(1)

                elif event.key == pygame.K_2:
                    activate_powerup(2)

                elif event.key == pygame.K_3:
                    activate_powerup(3)

                elif event.key == pygame.K_p:
                    save_game()

                elif event.key == pygame.K_l:
                    load_game()

            elif state in ("won", "lost", "ending"):
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if state == "won":
                        level += 1
                        new_level()
                        start_story()

                    elif state == "lost":
                        new_level()
                        state = "playing"

                    elif state == "ending":
                        state = "menu"

                elif event.key == pygame.K_ESCAPE:
                    state = "menu"

    if state == "playing":
        pressed = pygame.key.get_pressed()
        dx = dy = 0

        if pressed[pygame.K_a] or pressed[pygame.K_LEFT]:
            dx -= 1
        if pressed[pygame.K_d] or pressed[pygame.K_RIGHT]:
            dx += 1
        if pressed[pygame.K_w] or pressed[pygame.K_UP]:
            dy -= 1
        if pressed[pygame.K_s] or pressed[pygame.K_DOWN]:
            dy += 1

        speed = player_speed * (1.65 if speed_timer > 0 else 1)

        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071

        old_position = player.topleft
        move_player(dx * speed, dy * speed)

        # Footstep sound only when actually moving.
        if player.topleft != old_position:
            footstep_timer += 1

            if footstep_timer >= 16:
                play_sound("footstep")
                footstep_timer = 0
        else:
            footstep_timer = 0

        if speed_timer > 0:
            speed_timer -= 1

        if flashlight_timer > 0:
            flashlight_timer -= 1

        if sonar_cooldown > 0:
            sonar_cooldown -= 1

        if pulse_cooldown > 0:
            pulse_cooldown -= 1

        player_energy = min(100, player_energy + 0.08)

        if sonar_active:
            sonar_radius += 10
            if sonar_radius >= 220:
                sonar_active = False

        if message_timer > 0:
            message_timer -= 1

        if shake_timer > 0:
            shake_timer -= 1

        if flash_timer > 0:
            flash_timer -= 1

        if jumpscare_timer > 0:
            jumpscare_timer -= 1

        if jumpscare_cooldown > 0:
            jumpscare_cooldown -= 1
        elif random.random() < 0.001:
            jumpscare_timer = 30
            jumpscare_cooldown = 900
            flash_timer = 12
            play_sound("jumpscare")
            show_message("SOMETHING IS WATCHING YOU...", 100)

        # Collect keys
        for key in keys[:]:
            if player.colliderect(key):
                keys.remove(key)
                keys_collected += 1
                play_sound("key")
                show_message("ACCESS KEY RECOVERED!")

        # Collect research data
        for data in data_files[:]:
            if player.colliderect(data):
                data_files.remove(data)
                data_collected += 1
                play_sound("data")
                show_message("RESEARCH DATA RECOVERED!")

        collect_powerups()
        update_boss()

        if player.colliderect(exit_rect):
            if keys_collected < total_keys:
                show_message("MISSION: FIND ALL ACCESS KEYS!", 45)

            elif data_collected < total_data:
                show_message("MISSION: RECOVER ALL RESEARCH DATA!", 45)

            elif boss_health > 0:
                show_message("MISSION: DEFEAT THE EXPERIMENT!", 45)

            elif level >= 5:
                play_sound("win")
                state = "ending"

            else:
                play_sound("win")
                state = "won"

    if state == "menu":
        draw_center(
            "SILENT SIGNAL",
            "HORROR SURVIVAL - SOUND EDITION",
            [
                "ENTER: NEW STORY",
                "L: LOAD SAVED CHAPTER",
                "WASD / ARROWS: MOVE",
                "SPACE: SONAR | F: PULSE WEAPON",
                "1 HEALTH | 2 SPEED | 3 FLASHLIGHT",
                "P: SAVE | M: SOUND ON/OFF | ESC: QUIT"
            ]
        )

    elif state == "story":
        screen.fill(BLACK)

        title = story_text[0]
        title_img = big.render(title, True, RED)
        screen.blit(
            title_img,
            (WIDTH // 2 - title_img.get_width() // 2, 155)
        )

        for i, line in enumerate(story_text[1:]):
            text_img = font.render(line, True, WHITE)
            screen.blit(
                text_img,
                (WIDTH // 2 - text_img.get_width() // 2, 245 + i * 35)
            )

        prompt = small.render("ENTER / SPACE: CONTINUE", True, GOLD)
        screen.blit(
            prompt,
            (WIDTH // 2 - prompt.get_width() // 2, 480)
        )

    elif state == "playing":
        draw_game()

    elif state == "won":
        draw_center(
            "CHAPTER CLEARED",
            f"You survived chapter {level}",
            [
                "All objectives completed.",
                "ENTER / SPACE: NEXT CHAPTER",
                "ESC: MAIN MENU"
            ]
        )

    elif state == "lost":
        draw_center(
            "SIGNAL LOST",
            f"You were caught in chapter {level}",
            [
                "ENTER / SPACE: RETRY CHAPTER",
                "ESC: MAIN MENU"
            ]
        )

    elif state == "ending":
        draw_center(
            "THE SIGNAL ENDS",
            "You escaped the research facility.",
            [
                "The experiment is silent.",
                "The recovered data reveals the truth.",
                "You survived the first five chapters.",
                "ENTER / SPACE: MAIN MENU"
            ]
        )

    # Screen shake
    if state == "playing" and shake_timer > 0:
        offset_x = random.randint(-4, 4)
        offset_y = random.randint(-4, 4)
        frame = screen.copy()
        screen.fill(BLACK)
        screen.blit(frame, (offset_x, offset_y))

    pygame.display.flip()

pygame.quit()
sys.exit()
