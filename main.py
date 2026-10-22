
import pygame
import random
import json
import os
import math
import io
import wave
import struct

pygame.init()

try:
    pygame.mixer.init()
except pygame.error:
    pass

WIDTH, HEIGHT = 1000, 700
HUD = 76
FPS = 60
TILE = 40
SAVE_FILE = "silent_signal_save.json"

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SILENT SIGNAL - Story Campaign")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("consolas", 17)
SMALL = pygame.font.SysFont("consolas", 13)
BIG = pygame.font.SysFont("consolas", 30, bold=True)
TITLE = pygame.font.SysFont("consolas", 48, bold=True)

BLACK = (5, 7, 12)
WHITE = (230, 235, 240)
RED = (220, 45, 60)
GREEN = (65, 220, 125)
BLUE = (65, 165, 255)
YELLOW = (240, 200, 65)
PURPLE = (180, 80, 225)
GRAY = (90, 100, 115)
FLOOR = (23, 29, 38)
WALL = (55, 65, 80)

# -------------------- SOUND --------------------

muted = False
sounds = {}


def create_sound(freq=440, duration=0.15, volume=0.2):
    if not pygame.mixer.get_init():
        return None

    try:
        rate = 22050
        count = int(rate * duration)
        data = bytearray()

        for i in range(count):
            fade = min(1, i / 400, (count - i) / 400)
            value = int(
                32767 * volume * fade *
                math.sin(2 * math.pi * freq * i / rate)
            )
            data.extend(struct.pack("<h", value))

        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(data)

        buffer.seek(0)
        return pygame.mixer.Sound(buffer)

    except (pygame.error, OSError, ValueError):
        return None


for name, freq in {
    "pickup": 800,
    "shot": 110,
    "hurt": 65,
    "sonar": 650,
    "alert": 300,
    "door": 220,
    "win": 950,
}.items():
    sounds[name] = create_sound(freq)


def play_sound(name):
    sound = sounds.get(name)
    if sound and not muted:
        try:
            sound.play()
        except pygame.error:
            pass


# -------------------- CAMPAIGN --------------------

CHAPTERS = {
    1: {
        "name": "THE AWAKENING",
        "lines": [
            "You wake up inside an abandoned research facility.",
            "Emergency lights flicker across the corridor.",
            "Find the access card and reach the exit.",
        ],
    },
    2: {
        "name": "THE SIGNAL",
        "lines": [
            "A strange signal is coming from the lower laboratory.",
            "The facility's security system is still active.",
            "Find the data fragments and unlock the security door.",
        ],
    },
    3: {
        "name": "THE SURVIVOR",
        "lines": [
            "Someone is alive inside this facility.",
            "A survivor says the creatures fear the pulse weapon.",
            "Help the survivor and recover the access codes.",
        ],
    },
    4: {
        "name": "THE HUNTER",
        "lines": [
            "The source of the signal has found you.",
            "The Hunter is protecting the final laboratory.",
            "Defeat it and reach the control room.",
        ],
    },
    5: {
        "name": "SILENT SIGNAL",
        "lines": [
            "The signal controls the entire facility.",
            "Disable the terminal to stop the transmission.",
            "Your final choice will decide what happens next.",
        ],
    },
}

# -------------------- STATE --------------------

state = "menu"
level = 1
health = 100
energy = 100
ammo = 15
score = 0
data_count = 0
keycard = False
terminal_solved = False
survivor_helped = False
boss_health = 100
boss_phase = 1
ending_choice = 0

inventory = ["Pulse Blaster"]
powerups = {"medkit": 2, "speed": 1, "energy": 2}

player = pygame.Rect(70, HUD + 70, 24, 24)
player_speed = 3.0

walls = []
items = []
enemies = []
bullets = []
particles = []

boss = None
npc = None
keycard_item = None
terminal = None
locked_door = None
exit_rect = pygame.Rect(900, 600, 30, 30)

message = ""
message_timer = 0
story_page = 0
dialogue = []
dialogue_index = 0
damage_cooldown = 0
sonar_timer = 0
speed_timer = 0
shake_timer = 0
firing = False
moving = False
sprinting = False


def notify(text, frames=180):
    global message, message_timer
    message = text
    message_timer = frames


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# -------------------- MAP --------------------

def wall_at(x, y):
    if x < 0 or x >= WIDTH or y < HUD or y >= HEIGHT:
        return True
    return any(w.collidepoint(x, y) for w in walls)


def blocked(rect):
    return any(rect.colliderect(w) for w in walls)


def move_rect(rect, dx, dy):
    rect.x += round(dx)
    if blocked(rect):
        rect.x -= round(dx)

    rect.y += round(dy)
    if blocked(rect):
        rect.y -= round(dy)


def random_position(min_dist=100):
    for _ in range(500):
        x = random.randrange(1, WIDTH // TILE - 1) * TILE + 8
        y = random.randrange(3, HEIGHT // TILE - 1) * TILE + 8
        r = pygame.Rect(x, y, 24, 24)

        if not blocked(r) and dist(r.center, player.center) > min_dist:
            return r

    return pygame.Rect(WIDTH - 100, HEIGHT - 100, 24, 24)


def generate_level():
    global walls, items, enemies, bullets, particles
    global boss, npc, keycard_item, terminal, locked_door
    global exit_rect, boss_health, boss_phase, data_count
    global keycard, terminal_solved, survivor_helped

    walls = []
    items = []
    enemies = []
    bullets = []
    particles = []

    boss = None
    npc = None
    keycard_item = None
    terminal = None
    locked_door = None

    boss_health = 100
    boss_phase = 1
    data_count = 0
    keycard = False
    terminal_solved = False
    survivor_helped = False

    player.update(70, HUD + 70, 24, 24)

    # Outer walls
    for x in range(0, WIDTH, TILE):
        walls.append(pygame.Rect(x, HUD, TILE, TILE))
        walls.append(pygame.Rect(x, HEIGHT - TILE, TILE, TILE))

    for y in range(HUD, HEIGHT, TILE):
        walls.append(pygame.Rect(0, y, TILE, TILE))
        walls.append(pygame.Rect(WIDTH - TILE, y, TILE, TILE))

    # Procedural obstacles
    for _ in range(55 + level * 8):
        x = random.randrange(2, WIDTH // TILE - 2) * TILE
        y = random.randrange(3, HEIGHT // TILE - 2) * TILE
        r = pygame.Rect(x, y, TILE, TILE)

        if r.colliderect(pygame.Rect(40, HUD + 40, 160, 160)):
            continue

        walls.append(r)

    # Always keep a central corridor clear
    walls = [
        w for w in walls
        if not w.colliderect(pygame.Rect(420, HUD + 40, 160, HEIGHT - HUD - 80))
    ]

    # Keycard and terminal
    keycard_item = random_position(130)
    keycard_item.size = (20, 20)

    terminal = random_position(160)
    terminal.size = (30, 30)

    # Locked door before exit
    locked_door = pygame.Rect(800, HEIGHT - 120, 24, 80)

    # Exit
    exit_rect = pygame.Rect(900, HEIGHT - 90, 30, 30)

    # Data fragments
    for _ in range(3):
        r = random_position(100)
        items.append({"rect": r, "type": "data"})

    # Health and ammunition
    for kind in ("health", "ammo", "ammo"):
        items.append({"rect": random_position(100), "type": kind})

    # Enemy hunters
    for _ in range(min(level + 1, 5)):
        r = random_position(230)
        enemies.append({
            "rect": r,
            "state": "patrol",
            "target": r.center,
            "last_seen": None,
            "timer": random.randint(60, 150),
        })

    # Survivor NPC in chapter 3
    if level == 3:
        npc = random_position(180)
        npc.size = (26, 30)

    # Boss in chapter 4
    if level == 4:
        r = random_position(300)
        boss = {
            "rect": pygame.Rect(r.x, r.y, 44, 44),
            "timer": 70,
            "speed": 1.4,
        }

    notify(f"CHAPTER {level}: {CHAPTERS[level]['name']}", 200)


# -------------------- STORY & DIALOGUE --------------------

def begin_campaign():
    global level, health, energy, ammo, score
    global inventory, powerups, state, story_page

    level = 1
    health = 100
    energy = 100
    ammo = 15
    score = 0
    inventory = ["Pulse Blaster"]
    powerups = {"medkit": 2, "speed": 1, "energy": 2}
    story_page = 0

    generate_level()
    state = "story"


def open_dialogue(lines):
    global dialogue, dialogue_index, state
    dialogue = lines
    dialogue_index = 0
    state = "dialogue"


def advance_dialogue():
    global dialogue_index, state, survivor_helped, score

    dialogue_index += 1

    if dialogue_index >= len(dialogue):
        if level == 3 and not survivor_helped:
            survivor_helped = True
            score += 150
            inventory.append("Survivor Access Code")
            notify("SURVIVOR HELPED: +150 SCORE", 180)

        state = "playing"


def use_terminal():
    global terminal_solved, score, energy

    if terminal_solved:
        notify("TERMINAL ALREADY DISABLED")
        return

    if not keycard:
        notify("ACCESS DENIED: KEYCARD REQUIRED")
        return

    open_dialogue([
        "SECURITY TERMINAL: ACCESS GRANTED.",
        "A warning appears on the screen.",
        "The signal is connected to the central control room.",
        "Press ENTER to disable this terminal.",
    ])


def complete_terminal():
    global terminal_solved, score, energy, state

    terminal_solved = True
    score += 100
    energy = min(100, energy + 30)
    play_sound("door")
    notify("TERMINAL DISABLED! +100 SCORE", 180)
    state = "playing"


# -------------------- ENEMY AI --------------------

def move_toward(rect, target, speed):
    dx = target[0] - rect.centerx
    dy = target[1] - rect.centery
    length = max(1, math.hypot(dx, dy))

    old_x, old_y = rect.x, rect.y

    rect.x += round(dx / length * speed)
    if blocked(rect):
        rect.x = old_x

    rect.y += round(dy / length * speed)
    if blocked(rect):
        rect.y = old_y

    if rect.x == old_x and rect.y == old_y:
        return False

    return True


def visible_to_enemy(enemy):
    start = enemy["rect"].center
    end = player.center

    if dist(start, end) > 230:
        return False

    length = max(1, int(dist(start, end) / 6))

    for i in range(length + 1):
        t = i / length
        x = int(start[0] + (end[0] - start[0]) * t)
        y = int(start[1] + (end[1] - start[1]) * t)

        if wall_at(x, y):
            return False

    return True


def update_enemies():
    global health, damage_cooldown

    for enemy in enemies:
        r = enemy["rect"]

        if visible_to_enemy(enemy):
            enemy["state"] = "chase"
            enemy["last_seen"] = player.center

        elif enemy["state"] == "chase":
            enemy["state"] = "search"
            enemy["timer"] = 180

        if enemy["state"] == "patrol":
            enemy["timer"] -= 1

            if enemy["timer"] <= 0 or dist(r.center, enemy["target"]) < 20:
                target = random_position(0)
                enemy["target"] = target.center
                enemy["timer"] = random.randint(60, 150)

            move_toward(r, enemy["target"], 1.0)

        elif enemy["state"] == "chase":
            move_toward(r, player.center, 1.9 + level * 0.1)

        elif enemy["state"] == "search":
            enemy["timer"] -= 1
            if enemy["last_seen"]:
                move_toward(r, enemy["last_seen"], 1.2)

            if enemy["timer"] <= 0:
                enemy["state"] = "patrol"

        if r.colliderect(player) and damage_cooldown <= 0:
            health -= 10
            damage_cooldown = 55
            play_sound("hurt")
            notify("THE HUNTER CAUGHT YOU!", 90)


# -------------------- WEAPONS --------------------

def fire_weapon():
    global ammo, energy, firing

    if ammo <= 0:
        notify("OUT OF AMMO!")
        return

    if energy < 5:
        notify("ENERGY LOW!")
        return

    ammo -= 1
    energy -= 5
    firing = True
    play_sound("shot")

    mx, my = pygame.mouse.get_pos()
    dx = mx - player.centerx
    dy = my - player.centery
    length = max(1, math.hypot(dx, dy))

    bullets.append({
        "x": float(player.centerx),
        "y": float(player.centery),
        "vx": dx / length * 10,
        "vy": dy / length * 10,
        "life": 50,
    })


def update_bullets():
    global boss_health, score, boss

    for b in bullets[:]:
        b["x"] += b["vx"]
        b["y"] += b["vy"]
        b["life"] -= 1

        x, y = int(b["x"]), int(b["y"])

        if b["life"] <= 0 or wall_at(x, y):
            bullets.remove(b)
            continue

        hit = False

        for enemy in enemies[:]:
            if enemy["rect"].collidepoint(x, y):
                enemies.remove(enemy)
                score += 75
                hit = True
                break

        if boss and boss["rect"].collidepoint(x, y):
            weak_point = pygame.Rect(
                boss["rect"].centerx - 8,
                boss["rect"].top - 8,
                16, 16
            )

            damage = 25 if weak_point.collidepoint(x, y) else 12
            boss_health -= damage
            hit = True

            if weak_point.collidepoint(x, y):
                notify("WEAK POINT HIT!", 60)

            if boss_health <= 0:
                boss_health = 0
                score += 1000
                boss = None
                play_sound("win")
                notify("HUNTER DEFEATED! +1000 SCORE", 240)

        if hit:
            bullets.remove(b)


# -------------------- ITEMS --------------------

def collect_items():
    global health, ammo, energy, data_count, score, keycard

    if keycard_item and player.colliderect(keycard_item):
        keycard = True
        inventory.append("Security Keycard")
        keycard_item.update(-100, -100, 1, 1)
        score += 100
        play_sound("pickup")
        notify("SECURITY KEYCARD ACQUIRED!", 180)

    for item in items[:]:
        if player.colliderect(item["rect"]):
            kind = item["type"]

            if kind == "data":
                data_count += 1
                score += 50
                notify(f"DATA FRAGMENT {data_count}/3")

            elif kind == "health":
                health = min(100, health + 30)
                notify("HEALTH +30")

            elif kind == "ammo":
                ammo += 8
                notify("AMMO +8")

            items.remove(item)
            play_sound("pickup")


def use_powerup(number):
    global health, energy, player_speed, speed_timer

    if number == 1 and powerups["medkit"] > 0:
        powerups["medkit"] -= 1
        health = min(100, health + 40)
        notify("MEDKIT USED")

    elif number == 2 and powerups["speed"] > 0:
        powerups["speed"] -= 1
        player_speed = 5
        speed_timer = 240
        notify("SPEED BOOST ACTIVATED")

    elif number == 3 and powerups["energy"] > 0:
        powerups["energy"] -= 1
        energy = min(100, energy + 40)
        notify("ENERGY CELL USED")


# -------------------- BOSS --------------------

def update_boss():
    global health, boss_health, boss_phase, damage_cooldown

    if not boss:
        return

    r = boss["rect"]
    boss_phase = 1 if boss_health > 65 else 2 if boss_health > 30 else 3

    move_toward(r, player.center, boss["speed"] + boss_phase * 0.25)
    boss["timer"] -= 1

    if r.colliderect(player) and boss["timer"] <= 0:
        health -= 15 + boss_phase * 3
        boss["timer"] = 65
        play_sound("hurt")
        notify("BOSS ATTACK!", 75)

    # Visual boss energy blast is represented by a fast direct strike.
    if boss_phase >= 2 and boss["timer"] <= 0:
        if dist(r.center, player.center) < 220:
            health -= 5
            notify("ENERGY BLAST!", 60)
        boss["timer"] = 80


# -------------------- SAVE / LOAD --------------------

def save_game():
    data = {
        "level": level,
        "health": health,
        "energy": energy,
        "ammo": ammo,
        "score": score,
        "inventory": inventory,
        "powerups": powerups,
    }

    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        notify("GAME SAVED!")
    except OSError:
        notify("SAVE FAILED!")


def load_game():
    global level, health, energy, ammo, score
    global inventory, powerups, state

    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        level = max(1, min(5, int(data.get("level", 1))))
        health = max(1, min(100, int(data.get("health", 100))))
        energy = max(0, min(100, int(data.get("energy", 100))))
        ammo = max(0, int(data.get("ammo", 15)))
        score = max(0, int(data.get("score", 0)))
        inventory = data.get("inventory", ["Pulse Blaster"])
        powerups = data.get(
            "powerups",
            {"medkit": 2, "speed": 1, "energy": 2}
        )

        generate_level()
        state = "story"
        notify("SAVE LOADED!")

    except (OSError, ValueError, json.JSONDecodeError):
        notify("NO VALID SAVE FOUND!")


# -------------------- DRAWING --------------------

def draw_text(text, x, y, color=WHITE, font=FONT):
    screen.blit(font.render(text, True, color), (x, y))


def draw_hud():
    pygame.draw.rect(screen, (10, 14, 22), (0, 0, WIDTH, HUD))
    draw_text("SILENT SIGNAL", 12, 8, BLUE, BIG)
    draw_text(f"CHAPTER {level}", 265, 14, YELLOW)
    draw_text(f"SCORE {score}", 385, 14)
    draw_text(f"AMMO {ammo}", 520, 14, YELLOW)
    draw_text(f"DATA {data_count}/3", 645, 14, GREEN)

    pygame.draw.rect(screen, (65, 20, 25), (14, 51, 150, 12))
    pygame.draw.rect(screen, RED, (14, 51, 150 * max(0, health) / 100, 12))
    draw_text("HP", 170, 47, WHITE, SMALL)

    pygame.draw.rect(screen, (15, 35, 60), (225, 51, 150, 12))
    pygame.draw.rect(screen, BLUE, (225, 51, 150 * max(0, energy) / 100, 12))
    draw_text("ENERGY", 380, 47, WHITE, SMALL)

    draw_text("E: INTERACT   P: SAVE   SPACE: SONAR", 510, 48, GRAY, SMALL)


def draw_game():
    screen.fill(BLACK)

    for x in range(0, WIDTH, TILE):
        for y in range(HUD, HEIGHT, TILE):
            pygame.draw.rect(screen, FLOOR, (x, y, TILE, TILE))
            pygame.draw.rect(screen, (31, 38, 48), (x, y, TILE, TILE), 1)

    for w in walls:
        pygame.draw.rect(screen, WALL, w)
        pygame.draw.rect(screen, GRAY, w, 1)

    # Locked door
    if locked_door:
        door_color = GREEN if keycard else RED
        pygame.draw.rect(screen, door_color, locked_door)

    pygame.draw.rect(screen, GREEN, exit_rect)

    if keycard_item and keycard_item.x >= 0:
        pygame.draw.rect(screen, YELLOW, keycard_item)

    if terminal:
        pygame.draw.rect(
            screen, GREEN if terminal_solved else BLUE, terminal
        )

    for item in items:
        color = {
            "data": BLUE,
            "health": GREEN,
            "ammo": YELLOW,
        }[item["type"]]
        pygame.draw.rect(screen, color, item["rect"])

    for enemy in enemies:
        color = RED if enemy["state"] == "chase" else (150, 65, 80)
        pygame.draw.rect(screen, color, enemy["rect"])

    if npc:
        pygame.draw.rect(screen, GREEN, npc)
        draw_text("NPC", npc.x - 5, npc.y - 18, GREEN, SMALL)

    if boss:
        pygame.draw.rect(screen, PURPLE, boss["rect"])
        pygame.draw.rect(screen, RED, (350, HUD + 8, 300, 12))
        pygame.draw.rect(
            screen, GREEN,
            (350, HUD + 8, 300 * max(0, boss_health) / 100, 12)
        )
        draw_text(f"THE HUNTER - PHASE {boss_phase}", 365, HUD + 24, YELLOW, SMALL)

    for b in bullets:
        pygame.draw.circle(screen, YELLOW, (int(b["x"]), int(b["y"])), 4)

    pygame.draw.rect(screen, BLUE, player)
    pygame.draw.rect(screen, WHITE, player, 2)

    draw_hud()

    if message_timer > 0:
        draw_text(message, 230, HEIGHT - 28, YELLOW)

    # Small light circle around the player
    darkness = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    darkness.fill((0, 0, 0, 155))
    pygame.draw.circle(darkness, (0, 0, 0, 0), player.center, 125)
    screen.blit(darkness, (0, 0))

    # Keep player visible above the darkness layer
    pygame.draw.rect(screen, BLUE, player)
    pygame.draw.rect(screen, WHITE, player, 2)


def draw_menu():
    screen.fill((5, 8, 15))
    draw_text("SILENT SIGNAL", 220, 145, BLUE, TITLE)
    draw_text("STORY-DRIVEN SURVIVAL HORROR", 270, 215, GRAY)

    draw_text("ENTER - NEW CAMPAIGN", 350, 330, WHITE)
    draw_text("L - LOAD SAVED GAME", 350, 375, WHITE)
    draw_text("M - SOUND ON/OFF", 350, 420, WHITE)
    draw_text("ESC - QUIT", 350, 465, WHITE)


def draw_story():
    screen.fill(BLACK)
    chapter = CHAPTERS[level]

    draw_text("CHAPTER " + str(level), 370, 105, YELLOW, BIG)
    draw_text(chapter["name"], 280, 155, BLUE, TITLE)

    for i, line in enumerate(chapter["lines"]):
        draw_text(line, 140, 290 + i * 48, WHITE)

    draw_text("PRESS ENTER TO BEGIN", 345, 530, GREEN)


def draw_dialogue():
    draw_game()

    panel = pygame.Rect(80, 425, 840, 210)
    pygame.draw.rect(screen, (8, 12, 22), panel)
    pygame.draw.rect(screen, BLUE, panel, 2)

    if dialogue:
        draw_text(dialogue[dialogue_index], 110, 475, WHITE, FONT)

    draw_text("ENTER - CONTINUE", 370, 570, YELLOW)


def draw_ending():
    screen.fill(BLACK)
    draw_text("THE FINAL SIGNAL", 235, 110, BLUE, TITLE)
    draw_text("The control terminal offers two choices:", 245, 210, WHITE)

    draw_text("1 - DESTROY THE SIGNAL", 310, 310, GREEN)
    draw_text("2 - TRANSMIT THE SIGNAL", 310, 370, RED)
    draw_text("Choose 1 or 2", 410, 465, YELLOW)


# -------------------- GAME LOOP --------------------

begin_campaign()
state = "menu"
running = True

while running:
    clock.tick(FPS)

    if message_timer > 0:
        message_timer -= 1

    if damage_cooldown > 0:
        damage_cooldown -= 1

    if speed_timer > 0:
        speed_timer -= 1
        if speed_timer == 0:
            player_speed = 3.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if state == "playing":
                    state = "menu"
                else:
                    running = False

            if event.key == pygame.K_m:
                muted = not muted
                notify("SOUND OFF" if muted else "SOUND ON")

            if event.key == pygame.K_RETURN:
                if state == "menu":
                    begin_campaign()

                elif state == "story":
                    state = "playing"

                elif state == "dialogue":
                    if level == 2 and not terminal_solved:
                        complete_terminal()
                    else:
                        advance_dialogue()

                elif state == "ending":
                    if ending_choice == 1:
                        notify("THE SIGNAL IS DESTROYED. YOU ARE FREE.", 300)
                    elif ending_choice == 2:
                        notify("THE SIGNAL ESCAPES INTO THE WORLD.", 300)
                    state = "menu"

                elif state == "gameover":
                    begin_campaign()

            if event.key == pygame.K_l:
                load_game()

            if event.key == pygame.K_p and state == "playing":
                save_game()

            if state == "playing":
                if event.key == pygame.K_1:
                    use_powerup(1)

                elif event.key == pygame.K_2:
                    use_powerup(2)

                elif event.key == pygame.K_3:
                    use_powerup(3)

                elif event.key == pygame.K_SPACE:
                    if energy >= 15:
                        energy -= 15
                        sonar_timer = 60
                        play_sound("sonar")
                        notify("SONAR PING!", 60)

                elif event.key == pygame.K_e:
                    near_terminal = terminal and player.inflate(35, 35).colliderect(terminal)
                    near_npc = npc and player.inflate(35, 35).colliderect(npc)

                    if keycard_item and player.inflate(15, 15).colliderect(keycard_item):
                        keycard = True
                        keycard_item.update(-100, -100, 1, 1)
                        inventory.append("Security Keycard")
                        notify("KEYCARD COLLECTED!")

                    elif near_terminal:
                        if keycard:
                            use_terminal()
                        else:
                            notify("KEYCARD REQUIRED!")

                    elif near_npc:
                        open_dialogue([
                            "SURVIVOR: You came for the signal, didn't you?",
                            "SURVIVOR: The keycard is your way forward.",
                            "SURVIVOR: Do not trust the transmission.",
                        ])

                    elif locked_door and player.inflate(30, 30).colliderect(locked_door):
                        if keycard:
                            locked_door = None
                            play_sound("door")
                            notify("SECURITY DOOR UNLOCKED!")
                        else:
                            notify("LOCKED: SECURITY KEYCARD REQUIRED")

            if state == "ending":
                if event.key == pygame.K_1:
                    ending_choice = 1
                elif event.key == pygame.K_2:
                    ending_choice = 2

        if event.type == pygame.MOUSEBUTTONDOWN and state == "playing":
            if event.button == 1:
                fire_weapon()

    if state == "menu":
        draw_menu()

    elif state == "story":
        draw_story()

    elif state == "dialogue":
        draw_dialogue()

    elif state == "playing":
        keys = pygame.key.get_pressed()

        dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(
            keys[pygame.K_a] or keys[pygame.K_LEFT]
        )
        dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(
            keys[pygame.K_w] or keys[pygame.K_UP]
        )

        moving = bool(dx or dy)
        sprinting = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])

        speed = player_speed * (1.45 if sprinting else 1.0)

        if dx and dy:
            speed *= 0.707

        move_rect(player, dx * speed, dy * speed)

        energy = min(100, energy + 0.025)

        if sonar_timer > 0:
            sonar_timer -= 1

        update_enemies()
        update_bullets()
        collect_items()

        if boss:
            update_boss()

        # Exit requires the keycard and, in later chapters, terminal completion.
        if player.colliderect(exit_rect):
            if boss:
                notify("DEFEAT THE HUNTER FIRST!", 90)
            elif not keycard:
                notify("FIND THE SECURITY KEYCARD!", 90)
            elif level >= 2 and not terminal_solved:
                notify("DISABLE THE SECURITY TERMINAL!", 90)
            else:
                level += 1

                if level > 5:
                    state = "ending"
                    ending_choice = 0
                    play_sound("win")
                else:
                    generate_level()
                    state = "story"

        if health <= 0:
            health = 0
            state = "gameover"

        draw_game()

    elif state == "ending":
        draw_ending()

    elif state == "gameover":
        screen.fill(BLACK)
        draw_text("SIGNAL LOST", 300, 200, RED, TITLE)
        draw_text(f"FINAL SCORE: {score}", 380, 300, WHITE, BIG)
        draw_text("ENTER - RESTART   ESC - QUIT", 300, 400, YELLOW)

    pygame.display.flip()

pygame.quit()
