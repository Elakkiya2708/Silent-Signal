
import pygame
import random
import json
import math
import os
import io
import struct
import wave

pygame.init()

# ===================== CONFIGURATION =====================

WIDTH, HEIGHT = 1000, 700
HUD_HEIGHT = 80
FPS = 60
TILE = 40
SAVE_FILE = "silent_signal_save.json"

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SILENT SIGNAL | Survival Horror")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("consolas", 18)
SMALL = pygame.font.SysFont("consolas", 14)
TITLE = pygame.font.SysFont("consolas", 48, bold=True)
BIG = pygame.font.SysFont("consolas", 30, bold=True)

BLACK = (5, 7, 12)
WHITE = (230, 235, 240)
RED = (210, 45, 55)
GREEN = (65, 220, 125)
BLUE = (65, 170, 255)
YELLOW = (240, 200, 65)
PURPLE = (170, 90, 220)
GRAY = (85, 95, 110)
FLOOR = (24, 29, 37)
WALL = (55, 64, 78)

# ===================== SOUND GENERATION =====================

sounds = {}
muted = False


def make_tone(frequency=440, duration=0.12, volume=0.2):
    try:
        sample_rate = 22050
        frames = int(sample_rate * duration)
        raw = bytearray()

        for i in range(frames):
            fade = min(1, i / 500, (frames - i) / 500)
            value = int(
                32767 * volume * fade *
                math.sin(2 * math.pi * frequency * i / sample_rate)
            )
            raw.extend(struct.pack("<h", value))

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(raw)

        buffer.seek(0)
        return pygame.mixer.Sound(buffer)
    except (pygame.error, OSError, ValueError):
        return None


try:
    if pygame.mixer.get_init() is None:
        pygame.mixer.init()
except pygame.error:
    pass

sounds["sonar"] = make_tone(700, 0.18, 0.18)
sounds["shot"] = make_tone(100, 0.16, 0.28)
sounds["pickup"] = make_tone(850, 0.12, 0.16)
sounds["hurt"] = make_tone(65, 0.25, 0.3)
sounds["alert"] = make_tone(350, 0.22, 0.16)
sounds["boss"] = make_tone(45, 0.4, 0.35)
sounds["win"] = make_tone(950, 0.5, 0.18)


def play_sound(name):
    sound = sounds.get(name)
    if sound and not muted:
        try:
            sound.play()
        except pygame.error:
            pass


# ===================== GAME STATE =====================

game_state = "menu"
level = 1
health = 100
energy = 100
ammo = 12
score = 0
collected_data = 0
inventory = ["Pulse Blaster"]
powerups = {"health": 1, "speed": 0, "flashlight": 1}
message = "Find the exit. Stay silent."
message_timer = 240
chapter_intro = True
boss_mode = False
boss_health = 100

# Enemy AI tuning
ENEMY_VISION = 230
ENEMY_HEARING = 155
ENEMY_SPEED = 1.25
CHASE_SPEED = 2.05
SEARCH_SECONDS = 4.0

player = pygame.Rect(80, HUD_HEIGHT + 80, 24, 24)
player_speed = 3.0
last_player_position = player.center

walls = []
floor_tiles = []
items = []
bullets = []
particles = []
enemies = []
exit_rect = pygame.Rect(900, 600, 30, 30)
boss = None

mission_index = 0
missions = [
    "MISSION 1: Find the exit",
    "MISSION 2: Collect 3 data fragments",
    "MISSION 3: Survive the hunter",
    "MISSION 4: Defeat the boss",
    "MISSION 5: Escape the facility",
]


def notify(text, frames=180):
    global message, message_timer
    message = text
    message_timer = frames


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def line_of_sight(start, end):
    x1, y1 = start
    x2, y2 = end
    length = distance(start, end)
    steps = max(1, int(length / 5))

    for i in range(steps + 1):
        t = i / steps
        x = int(x1 + (x2 - x1) * t)
        y = int(y1 + (y2 - y1) * t)
        if is_wall_point(x, y):
            return False

    return True


# ===================== LEVEL GENERATION =====================

def is_wall_point(x, y):
    if x < 0 or y < HUD_HEIGHT or x >= WIDTH or y >= HEIGHT:
        return True

    return any(w.collidepoint(x, y) for w in walls)


def hits_wall(rect):
    return any(rect.colliderect(w) for w in walls)


def move_rect(rect, dx, dy):
    rect.x += int(dx)
    if hits_wall(rect):
        rect.x -= int(dx)

    rect.y += int(dy)
    if hits_wall(rect):
        rect.y -= int(dy)


def open_position(min_distance=100):
    for _ in range(500):
        x = random.randint(2, WIDTH // TILE - 3) * TILE + 8
        y = random.randint((HUD_HEIGHT // TILE) + 2, HEIGHT // TILE - 2) * TILE + 8
        rect = pygame.Rect(x, y, 24, 24)

        if not hits_wall(rect) and distance(rect.center, player.center) > min_distance:
            return rect

    return pygame.Rect(WIDTH - 100, HEIGHT - 100, 24, 24)


def new_level():
    global walls, floor_tiles, items, enemies, bullets, particles
    global player, exit_rect, boss, boss_mode, boss_health, ammo, energy

    walls = []
    floor_tiles = []
    items = []
    enemies = []
    bullets = []
    particles = []
    boss = None
    boss_mode = level >= 4
    boss_health = 100
    ammo = max(ammo, 8)
    energy = 100

    # Outer boundary
    for x in range(0, WIDTH, TILE):
        walls.append(pygame.Rect(x, HUD_HEIGHT, TILE, TILE))
        walls.append(pygame.Rect(x, HEIGHT - TILE, TILE, TILE))

    for y in range(HUD_HEIGHT, HEIGHT, TILE):
        walls.append(pygame.Rect(0, y, TILE, TILE))
        walls.append(pygame.Rect(WIDTH - TILE, y, TILE, TILE))

    # Random maze walls
    for _ in range(95 + level * 7):
        x = random.randrange(1, WIDTH // TILE - 1) * TILE
        y = random.randrange(3, HEIGHT // TILE - 1) * TILE
        candidate = pygame.Rect(x, y, TILE, TILE)

        if candidate.colliderect(pygame.Rect(40, HUD_HEIGHT + 40, 160, 160)):
            continue

        walls.append(candidate)

    player.update(70, HUD_HEIGHT + 70, 24, 24)

    # Clear a small starting area
    walls = [
        w for w in walls
        if not w.colliderect(pygame.Rect(40, HUD_HEIGHT + 40, 120, 120))
    ]

    exit_rect = open_position(300)
    exit_rect.size = (28, 28)

    # Data fragments and pickups
    for _ in range(3):
        items.append({"rect": open_position(100), "type": "data"})

    for _ in range(2):
        items.append({"rect": open_position(100), "type": "ammo"})

    items.append({"rect": open_position(100), "type": "health"})

    # Hunters
    for _ in range(min(2 + level, 6)):
        rect = open_position(240)
        enemies.append({
            "rect": rect,
            "state": "patrol",
            "target": rect.center,
            "last_seen": None,
            "search_timer": 0.0,
            "alert_cooldown": 0,
            "patrol_timer": random.randint(40, 120),
            "speed": ENEMY_SPEED + level * 0.06,
        })

    if boss_mode:
        boss_rect = open_position(350)
        boss = {
            "rect": pygame.Rect(boss_rect.x, boss_rect.y, 38, 38),
            "speed": 1.2 + level * 0.12,
            "attack_timer": 0,
        }
        notify("WARNING: HOSTILE ENTITY DETECTED!", 240)
    else:
        notify(f"CHAPTER {level}: THE FACILITY", 180)


# ===================== PARTICLES =====================

def spawn_particles(pos, color, count=8):
    for _ in range(count):
        particles.append({
            "x": float(pos[0]),
            "y": float(pos[1]),
            "vx": random.uniform(-2.5, 2.5),
            "vy": random.uniform(-2.5, 2.5),
            "life": random.randint(15, 35),
            "color": color,
        })


def update_particles():
    for p in particles[:]:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["life"] -= 1
        if p["life"] <= 0:
            particles.remove(p)


def draw_particles():
    for p in particles:
        pygame.draw.circle(
            screen, p["color"],
            (int(p["x"]), int(p["y"])),
            max(1, p["life"] // 10)
        )


# ===================== ADVANCED ENEMY AI =====================

def choose_patrol_target(enemy):
    for _ in range(100):
        x = random.randint(TILE, WIDTH - TILE)
        y = random.randint(HUD_HEIGHT + TILE, HEIGHT - TILE)
        if not is_wall_point(x, y):
            enemy["target"] = (x, y)
            enemy["patrol_timer"] = random.randint(60, 150)
            return

    enemy["target"] = enemy["rect"].center


def enemy_move_toward(enemy, target, speed):
    rect = enemy["rect"]
    dx = target[0] - rect.centerx
    dy = target[1] - rect.centery
    length = math.hypot(dx, dy)

    if length < 2:
        return

    vx = dx / length * speed
    vy = dy / length * speed

    old_x, old_y = rect.x, rect.y

    rect.x += round(vx)
    if hits_wall(rect):
        rect.x = old_x

    rect.y += round(vy)
    if hits_wall(rect):
        rect.y = old_y

    if rect.x == old_x and rect.y == old_y:
        choose_patrol_target(enemy)


def update_enemies(dt):
    global health

    for enemy in enemies:
        rect = enemy["rect"]
        player_distance = distance(rect.center, player.center)
        visible = (
            player_distance <= ENEMY_VISION
            and line_of_sight(rect.center, player.center)
        )

        # Sprinting, firing or nearby movement can attract enemies.
        heard = player_distance <= ENEMY_HEARING and (
            moving or firing_this_frame or sprinting
        )

        if visible:
            enemy["state"] = "chase"
            enemy["last_seen"] = player.center
            enemy["search_timer"] = SEARCH_SECONDS

            if enemy["alert_cooldown"] <= 0:
                play_sound("alert")
                enemy["alert_cooldown"] = 100

        elif heard:
            enemy["state"] = "investigate"
            enemy["target"] = player.center
            enemy["search_timer"] = SEARCH_SECONDS

        elif enemy["state"] == "chase":
            enemy["state"] = "search"
            enemy["search_timer"] = SEARCH_SECONDS

        enemy["alert_cooldown"] = max(0, enemy["alert_cooldown"] - 1)

        if enemy["state"] == "patrol":
            enemy["patrol_timer"] -= 1
            if distance(rect.center, enemy["target"]) < 20 or enemy["patrol_timer"] <= 0:
                choose_patrol_target(enemy)

            enemy_move_toward(enemy, enemy["target"], enemy["speed"])

        elif enemy["state"] == "investigate":
            enemy_move_toward(enemy, enemy["target"], enemy["speed"] * 1.15)

            if distance(rect.center, enemy["target"]) < 24:
                enemy["state"] = "search"
                enemy["search_timer"] = SEARCH_SECONDS

        elif enemy["state"] == "chase":
            enemy_move_toward(enemy, player.center, CHASE_SPEED + level * 0.05)

        elif enemy["state"] == "search":
            enemy["search_timer"] -= dt

            if enemy["last_seen"]:
                enemy_move_toward(enemy, enemy["last_seen"], enemy["speed"])

            if enemy["search_timer"] <= 0:
                enemy["state"] = "patrol"
                choose_patrol_target(enemy)

        if rect.colliderect(player):
            global damage_cooldown
            if damage_cooldown <= 0:
                health -= 10
                damage_cooldown = 50
                play_sound("hurt")
                spawn_particles(player.center, RED, 12)
                notify("THE HUNTER CAUGHT YOU!", 90)


# ===================== WEAPONS =====================

def fire_weapon():
    global ammo, energy

    if ammo <= 0:
        notify("OUT OF AMMO!", 60)
        return

    if energy < 8:
        notify("NOT ENOUGH ENERGY!", 60)
        return

    ammo -= 1
    energy -= 8
    play_sound("shot")

    mx, my = pygame.mouse.get_pos()
    dx, dy = mx - player.centerx, my - player.centery
    length = max(1, math.hypot(dx, dy))

    bullets.append({
        "x": float(player.centerx),
        "y": float(player.centery),
        "vx": dx / length * 10,
        "vy": dy / length * 10,
        "life": 45,
    })


def update_bullets():
    global score, boss_health

    for bullet in bullets[:]:
        bullet["x"] += bullet["vx"]
        bullet["y"] += bullet["vy"]
        bullet["life"] -= 1

        pos = (int(bullet["x"]), int(bullet["y"]))

        if bullet["life"] <= 0 or is_wall_point(*pos):
            bullets.remove(bullet)
            continue

        hit = False

        for enemy in enemies[:]:
            if enemy["rect"].collidepoint(pos):
                enemies.remove(enemy)
                score += 100
                spawn_particles(pos, PURPLE, 18)
                hit = True
                break

        if boss and boss["rect"].collidepoint(pos):
            boss_health -= 12
            spawn_particles(pos, RED, 8)
            hit = True

            if boss_health <= 0:
                spawn_particles(boss["rect"].center, YELLOW, 40)
                boss = None
                score += 500
                play_sound("win")
                notify("BOSS DEFEATED! FIND THE EXIT.", 240)

        if hit:
            bullets.remove(bullet)


# ===================== SONAR =====================

sonar_timer = 0


def use_sonar():
    global energy, sonar_timer

    if energy < 15:
        notify("SONAR ENERGY LOW!", 60)
        return

    energy -= 15
    sonar_timer = 75
    play_sound("sonar")
    notify("SONAR PING: SCANNING NEARBY HOSTILES", 90)


def draw_sonar():
    if sonar_timer > 0:
        radius = int((75 - sonar_timer) * 5 + 20)
        pygame.draw.circle(screen, BLUE, player.center, radius, 2)

        for enemy in enemies:
            if distance(player.center, enemy["rect"].center) < radius + 20:
                pygame.draw.circle(screen, RED, enemy["rect"].center, 18, 2)

        if boss:
            pygame.draw.circle(screen, PURPLE, boss["rect"].center, 24, 2)


# ===================== SAVE / LOAD =====================

def save_game():
    data = {
        "level": level,
        "health": health,
        "energy": energy,
        "ammo": ammo,
        "score": score,
        "collected_data": collected_data,
        "inventory": inventory,
        "powerups": powerups,
    }

    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        notify("GAME SAVED!", 90)
    except OSError:
        notify("SAVE FAILED!", 90)


def load_game():
    global level, health, energy, ammo, score, collected_data
    global inventory, powerups, game_state

    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        level = max(1, min(5, int(data.get("level", 1))))
        health = max(1, min(100, int(data.get("health", 100))))
        energy = max(0, min(100, int(data.get("energy", 100))))
        ammo = max(0, int(data.get("ammo", 12)))
        score = max(0, int(data.get("score", 0)))
        collected_data = max(0, int(data.get("collected_data", 0)))
        inventory = data.get("inventory", ["Pulse Blaster"])
        powerups = data.get("powerups", {"health": 1, "speed": 0, "flashlight": 1})

        new_level()
        game_state = "playing"
        notify("SAVE LOADED!", 90)

    except (OSError, ValueError, json.JSONDecodeError):
        notify("NO VALID SAVE FILE!", 120)


# ===================== PICKUPS & MISSIONS =====================

def collect_items():
    global health, ammo, energy, collected_data, score, player_speed

    for item in items[:]:
        if player.colliderect(item["rect"]):
            kind = item["type"]

            if kind == "data":
                collected_data += 1
                score += 50
                notify(f"DATA FRAGMENT FOUND: {collected_data}", 100)

            elif kind == "ammo":
                ammo += 6
                notify("AMMO +6", 70)

            elif kind == "health":
                health = min(100, health + 30)
                notify("HEALTH RESTORED", 70)

            items.remove(item)
            play_sound("pickup")
            spawn_particles(item["rect"].center, GREEN, 10)


def use_powerup(number):
    global health, player_speed, energy

    if number == 1 and powerups.get("health", 0) > 0:
        health = min(100, health + 40)
        powerups["health"] -= 1
        notify("MEDKIT USED")

    elif number == 2 and powerups.get("speed", 0) > 0:
        player_speed = 5.0
        powerups["speed"] -= 1
        notify("SPEED BOOST ACTIVATED", 180)

    elif number == 3 and powerups.get("flashlight", 0) > 0:
        energy = min(100, energy + 35)
        powerups["flashlight"] -= 1
        notify("ENERGY CELL USED")


def mission_text():
    if boss_mode and boss:
        return "MISSION: DEFEAT THE BOSS"
    if len(enemies) > 0:
        return "MISSION: SURVIVE THE HUNTER"
    if collected_data < 3:
        return f"MISSION: COLLECT DATA ({collected_data}/3)"
    return "MISSION: REACH THE EXIT"


# ===================== RENDERING =====================

def draw_text(text, x, y, color=WHITE, font=FONT):
    screen.blit(font.render(text, True, color), (x, y))


def draw_hud():
    pygame.draw.rect(screen, (12, 15, 23), (0, 0, WIDTH, HUD_HEIGHT))
    pygame.draw.line(screen, GRAY, (0, HUD_HEIGHT - 2), (WIDTH, HUD_HEIGHT - 2), 2)

    draw_text("SILENT SIGNAL", 16, 10, BLUE, BIG)
    draw_text(f"LVL {level}", 250, 14, YELLOW)
    draw_text(f"SCORE {score}", 340, 14, WHITE)
    draw_text(f"AMMO {ammo}", 485, 14, YELLOW)
    draw_text(f"DATA {collected_data}/3", 600, 14, GREEN)

    pygame.draw.rect(screen, (55, 20, 25), (16, 49, 160, 14))
    pygame.draw.rect(screen, RED, (16, 49, 160 * max(0, health) / 100, 14))
    draw_text("HP", 180, 45, WHITE, SMALL)

    pygame.draw.rect(screen, (20, 35, 55), (230, 49, 160, 14))
    pygame.draw.rect(screen, BLUE, (230, 49, 160 * max(0, energy) / 100, 14))
    draw_text("ENERGY", 395, 45, WHITE, SMALL)

    draw_text(mission_text(), 510, 47, GREEN, SMALL)


def draw_world():
    screen.fill(BLACK)

    # Floor grid
    for x in range(0, WIDTH, TILE):
        for y in range(HUD_HEIGHT, HEIGHT, TILE):
            pygame.draw.rect(screen, FLOOR, (x, y, TILE, TILE))
            pygame.draw.rect(screen, (31, 37, 46), (x, y, TILE, TILE), 1)

    for wall in walls:
        pygame.draw.rect(screen, WALL, wall)
        pygame.draw.rect(screen, (80, 90, 105), wall, 2)

    pygame.draw.rect(screen, GREEN, exit_rect)
    pygame.draw.rect(screen, WHITE, exit_rect, 2)

    for item in items:
        color = {
            "data": BLUE,
            "ammo": YELLOW,
            "health": GREEN,
        }[item["type"]]

        pygame.draw.rect(screen, color, item["rect"])
        pygame.draw.rect(screen, WHITE, item["rect"], 1)

    for enemy in enemies:
        rect = enemy["rect"]
        color = {
            "patrol": (160, 70, 80),
            "investigate": YELLOW,
            "chase": RED,
            "search": PURPLE,
        }.get(enemy["state"], RED)

        pygame.draw.rect(screen, color, rect)
        pygame.draw.circle(screen, WHITE, (rect.centerx, rect.centery), 4)

        # Enemy state indicator
        if enemy["state"] == "chase":
            pygame.draw.circle(screen, RED, rect.center, 16, 1)

    if boss:
        pygame.draw.rect(screen, PURPLE, boss["rect"])
        pygame.draw.rect(screen, RED, (boss["rect"].x, boss["rect"].y - 10, 40, 5))
        pygame.draw.rect(
            screen, GREEN,
            (boss["rect"].x, boss["rect"].y - 10, 40 * max(0, boss_health) / 100, 5)
        )

    for bullet in bullets:
        pygame.draw.circle(screen, YELLOW, (int(bullet["x"]), int(bullet["y"])), 4)

    # Player
    pygame.draw.rect(screen, BLUE, player)
    pygame.draw.rect(screen, WHITE, player, 2)

    mx, my = pygame.mouse.get_pos()
    pygame.draw.line(screen, BLUE, player.center, (mx, my), 1)

    draw_particles()
    draw_sonar()

    # Simple flashlight vignette
    darkness = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    darkness.fill((0, 0, 0, 170))

    if powerups.get("flashlight", 0) > 0:
        pygame.draw.circle(darkness, (0, 0, 0, 0), player.center, 135)

    screen.blit(darkness, (0, 0))

    # Draw the player over darkness
    pygame.draw.rect(screen, BLUE, player)
    pygame.draw.rect(screen, WHITE, player, 2)

    draw_hud()

    if message_timer > 0 and message:
        label = FONT.render(message, True, YELLOW)
        screen.blit(label, label.get_rect(center=(WIDTH // 2, HEIGHT - 25)))


def draw_menu():
    screen.fill((5, 8, 15))
    draw_text("SILENT SIGNAL", 230, 155, BLUE, TITLE)
    draw_text("A SURVIVAL HORROR EXPERIENCE", 270, 220, GRAY)

    options = [
        "ENTER - START GAME",
        "L - LOAD GAME",
        "M - TOGGLE SOUND",
        "ESC - QUIT",
    ]

    for i, option in enumerate(options):
        draw_text(option, 340, 330 + i * 42, WHITE)

    draw_text("WATCH THE SHADOWS. LISTEN FOR FOOTSTEPS.", 225, 570, RED)


def draw_game_over():
    screen.fill(BLACK)
    draw_text("SIGNAL LOST", 310, 230, RED, TITLE)
    draw_text(f"FINAL SCORE: {score}", 390, 320, WHITE, BIG)
    draw_text("ENTER - RETRY       ESC - MENU", 305, 400, YELLOW)


def draw_story():
    screen.fill(BLACK)
    draw_text("SILENT SIGNAL", 300, 130, BLUE, TITLE)
    draw_text(f"CHAPTER {level}", 430, 230, YELLOW, BIG)

    story = [
        "The facility has gone silent.",
        "Something is moving in the darkness.",
        "Collect the data and find an exit.",
        "Avoid the hunter. Save your ammunition.",
    ]

    for i, line in enumerate(story):
        draw_text(line, 245, 315 + i * 36, WHITE)

    draw_text("PRESS ENTER TO CONTINUE", 340, 525, GREEN)


# ===================== MAIN GAME =====================

moving = False
firing_this_frame = False
sprinting = False
damage_cooldown = 0
speed_boost_timer = 0


def start_game():
    global game_state, level, health, energy, ammo, score
    global collected_data, inventory, powerups, chapter_intro

    level = 1
    health = 100
    energy = 100
    ammo = 12
    score = 0
    collected_data = 0
    inventory = ["Pulse Blaster"]
    powerups = {"health": 1, "speed": 1, "flashlight": 1}
    chapter_intro = True
    new_level()
    game_state = "story"


running = True
start_game()
game_state = "menu"

while running:
    dt = clock.tick(FPS) / 1000.0

    if message_timer > 0:
        message_timer -= 1

    if sonar_timer > 0:
        sonar_timer -= 1

    if damage_cooldown > 0:
        damage_cooldown -= 1

    if speed_boost_timer > 0:
        speed_boost_timer -= 1
        if speed_boost_timer == 0:
            player_speed = 3.0

    firing_this_frame = False
    sprinting = False
    moving = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if game_state == "playing":
                    game_state = "menu"
                else:
                    running = False

            if event.key == pygame.K_m:
                muted = not muted
                notify("SOUND ON" if not muted else "SOUND OFF")

            if event.key == pygame.K_l:
                load_game()

            if event.key == pygame.K_p and game_state == "playing":
                save_game()

            if event.key == pygame.K_RETURN:
                if game_state == "menu":
                    start_game()
                elif game_state == "story":
                    game_state = "playing"
                elif game_state == "gameover":
                    start_game()
                elif game_state == "ending":
                    game_state = "menu"

            if game_state == "playing":
                if event.key == pygame.K_SPACE:
                    use_sonar()

                if event.key == pygame.K_1:
                    use_powerup(1)

                if event.key == pygame.K_2:
                    if powerups.get("speed", 0) > 0:
                        powerups["speed"] -= 1
                        player_speed = 5.0
                        speed_boost_timer = 240
                        notify("SPEED BOOST ACTIVATED")
                    else:
                        notify("NO SPEED BOOST LEFT")

                if event.key == pygame.K_3:
                    use_powerup(3)

        if event.type == pygame.MOUSEBUTTONDOWN and game_state == "playing":
            if event.button == 1:
                firing_this_frame = True
                fire_weapon()

    if game_state == "menu":
        draw_menu()

    elif game_state == "story":
        draw_story()

    elif game_state == "playing":
        keys = pygame.key.get_pressed()

        dx = 0
        dy = 0

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1

        if dx or dy:
            moving = True

        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            sprinting = True

        speed = player_speed * (1.5 if sprinting else 1.0)

        if dx and dy:
            speed *= 0.7071

        move_rect(player, dx * speed, dy * speed)

        # Restore energy gradually
        energy = min(100, energy + 0.025)

        update_enemies(dt)

        # Boss follows player and attacks at close range
        if boss:
            enemy_move_toward(boss, player.center, boss["speed"])
            boss["attack_timer"] -= 1

            if boss["rect"].colliderect(player) and boss["attack_timer"] <= 0:
                health -= 20
                boss["attack_timer"] = 55
                play_sound("boss")
                spawn_particles(player.center, RED, 20)
                notify("BOSS ATTACK!", 90)

        update_bullets()
        collect_items()
        update_particles()

        # Mission and exit
        if player.colliderect(exit_rect):
            if boss:
                notify("DEFEAT THE BOSS FIRST!", 90)
            elif collected_data < 3 and level >= 2:
                notify("COLLECT ALL 3 DATA FRAGMENTS!", 90)
            else:
                level += 1
                if level > 5:
                    game_state = "ending"
                    play_sound("win")
                else:
                    new_level()
                    game_state = "story"

        if health <= 0:
            health = 0
            game_state = "gameover"
            play_sound("hurt")

        draw_world()

    elif game_state == "gameover":
        draw_game_over()

    elif game_state == "ending":
        screen.fill(BLACK)
        draw_text("SIGNAL RESTORED", 250, 160, GREEN, TITLE)
        draw_text("YOU ESCAPED THE FACILITY", 300, 260, WHITE, BIG)
        draw_text(f"FINAL SCORE: {score}", 390, 335, YELLOW)
        draw_text("THE SILENCE WAS ONLY THE BEGINNING...", 235, 405, RED)
        draw_text("ENTER - MAIN MENU", 385, 520, WHITE)

    pygame.display.flip()

pygame.quit()

    # Boss energy projectiles
    for projectile in boss_projectiles:
        pygame.draw.circle(
            screen,
            (255, 70, 80),
            (int(projectile["x"]), int(projectile["y"])),
            7
        )

    # Boss minions
    for minion in boss_minions:
        pygame.draw.rect(screen, PURPLE, minion)
        pygame.draw.rect(screen, RED, minion, 2)

    # Boss phase health bar
    if boss:
        bar_width = 300
        bar_x = (WIDTH - bar_width) // 2
        bar_y = HUD_HEIGHT + 8

        pygame.draw.rect(
            screen, (50, 15, 20),
            (bar_x, bar_y, bar_width, 14)
        )
        pygame.draw.rect(
            screen, RED,
            (
                bar_x, bar_y,
                int(bar_width * max(0, boss_health) / 100),
                14
            )
        )
        pygame.draw.rect(
            screen, WHITE,
            (bar_x, bar_y, bar_width, 14), 1
        )

        phase_label = FONT.render(
            f"THE HUNTER - PHASE {boss_phase}",
            True, YELLOW
        )
        screen.blit(
            phase_label,
            (bar_x, bar_y + 18)
        )
