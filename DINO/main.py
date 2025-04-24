# -*- coding: utf-8 -*-
import pygame
import sys
import random
import os

# --- Initialize Pygame and Mixer ---
pygame.init()
pygame.mixer.init() # Initialize the mixer for music

# --- Constants ---
WIDTH, HEIGHT = 800, 300
GROUND_HEIGHT = HEIGHT - 50
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (100, 100, 100)
DARK_GREY = (50, 50, 50)
LIGHT_GREY = (200, 200, 200)

# Theme Constants
THEME_CHANGE_SCORE_INTERVAL = 2500

# Player Constants
GRAVITY = 0.8
JUMP_HEIGHT = -15
DUCK_OFFSET_Y = 20

# Obstacle Constants
OBSTACLE_INITIAL_SPEED = 5
OBSTACLE_SPEED_INCREASE_INTERVAL = 500
OBSTACLE_SPEED_INCREASE_AMOUNT = 0.5
OBSTACLE_INITIAL_SPAWN_DELAY = 120
OBSTACLE_MIN_SPAWN_DELAY = 60
PTERODACTYL_MIN_SCORE = 300
PTERODACTYL_CHANCE = 0.25
SWOOPING_PTERODACTYL_CHANCE = 0.4
KAMIKAZE_MIN_SCORE = 600
KAMIKAZE_CHANCE = 0.07
LEVITATING_CACTUS_MIN_SCORE = 450
LEVITATING_CACTUS_CHANCE = 0.10
PTERODACTYL_HEIGHTS = [GROUND_HEIGHT - 65, GROUND_HEIGHT - 95]

# Image Scaling Sizes
DINO_SIZE = (44, 47)
DINO_DUCK_SIZE = (59, 30)
CACTUS_SIZE = (25, 50)
PTERODACTYL_SIZE = (46, 40)

# Snow Constants
NUM_SNOWFLAKES = 150
SNOW_COLOR = LIGHT_GREY

# --- Setup ---
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Dino Run Advanced")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 24)

# --- Load and Scale Images ---
def load_and_scale_image(filename, size):
    """Loads an image, scales it, and handles errors."""
    try:
        image = pygame.image.load(filename).convert_alpha()
        image = pygame.transform.scale(image, size)
        return image
    except pygame.error as e:
        print(f"Error loading or scaling image: {filename} - {e}")
        print(f"Make sure '{filename}' is in the same folder as the script ({os.getcwd()}).")
        pygame.quit(); sys.exit()

# Load images
dino_normal_img = load_and_scale_image("dino.png.png", DINO_SIZE)
dino_duck_img = load_and_scale_image("dino_duck.png.png", DINO_DUCK_SIZE)
cactus_img = load_and_scale_image("cactus.png.png", CACTUS_SIZE)
pterodactyl_img = load_and_scale_image("pterodactyl.png.png", PTERODACTYL_SIZE)

# --- Load Music ---
MUSIC_FILENAME = "background_music.ogg"
try:
    pygame.mixer.music.load(MUSIC_FILENAME)
    print(f"Loaded music: {MUSIC_FILENAME}")
except pygame.error as e:
    print(f"Error loading music file '{MUSIC_FILENAME}': {e}")
    print("Music will not play.")
# --- End Music Load ---

# --- Player Variables ---
dino_current_img = dino_normal_img
dino_rect = dino_current_img.get_rect(midbottom=(100, GROUND_HEIGHT))
player_y_velocity = 0
is_jumping = False
is_ducking = False
on_ground = True
# --- NEW: Track if ducking was initiated by touch ---
touch_ducking = False
# --- End Touch Ducking Track ---

# --- Obstacle Class (Includes Levitating Cactus) ---
class Obstacle:
    def __init__(self, type):
        self.type = type
        self.passed = False

        if self.type == 'cactus':
            self.image = cactus_img
            self.rect = self.image.get_rect(midbottom=(WIDTH + random.randint(50, 150), GROUND_HEIGHT))
        elif self.type == 'pterodactyl' or self.type == 'swooping_pterodactyl':
            self.image = pterodactyl_img
            spawn_height = random.choice(PTERODACTYL_HEIGHTS)
            self.rect = self.image.get_rect(midbottom=(WIDTH + random.randint(50, 150), spawn_height))
            if self.type == 'swooping_pterodactyl':
                self.is_swooping = False; self.swoop_target_y = GROUND_HEIGHT - DINO_SIZE[1] - random.randint(5, 20)
                self.swoop_speed = random.uniform(1.8, 3.2); self.swoop_trigger_x = WIDTH * random.uniform(0.55, 0.75)
            else: self.is_swooping = False
        elif self.type == 'kamikaze_pterodactyl':
            self.image = pterodactyl_img
            self.rect = self.image.get_rect(midtop=(WIDTH + random.randint(70, 200), random.randint(5, 25)))
            self.dive_speed = random.uniform(5.0, 7.5); self.on_ground = False
        elif self.type == 'levitating_cactus':
            self.image = cactus_img
            self.rect = self.image.get_rect(midbottom=(WIDTH + random.randint(50, 150), GROUND_HEIGHT))
            self.is_launching = False; self.is_levitating = False
            self.launch_trigger_x = WIDTH * random.uniform(0.4, 0.75)
            self.target_y = random.randint(HEIGHT // 2 - 10, HEIGHT // 2 + 30)
            self.launch_speed = random.uniform(4.0, 6.5)

    def update(self, speed, player_rect):
        self.rect.x -= speed # Horizontal movement

        # Vertical/State movements
        if self.type == 'swooping_pterodactyl':
            if not self.is_swooping and self.rect.centerx < self.swoop_trigger_x: self.is_swooping = True
            if self.is_swooping:
                if self.rect.bottom < self.swoop_target_y:
                    self.rect.y += self.swoop_speed
                    if self.rect.bottom > self.swoop_target_y: self.rect.bottom = self.swoop_target_y
        elif self.type == 'kamikaze_pterodactyl':
            if not self.on_ground:
                self.rect.y += self.dive_speed
                if self.rect.bottom >= GROUND_HEIGHT: self.rect.bottom = GROUND_HEIGHT; self.on_ground = True
        elif self.type == 'levitating_cactus':
            if not self.is_levitating:
                if self.is_launching:
                    self.rect.y -= self.launch_speed
                    if self.rect.centery <= self.target_y:
                        self.rect.centery = self.target_y; self.is_launching = False; self.is_levitating = True
                elif self.rect.centerx < self.launch_trigger_x: self.is_launching = True

    def draw(self, surface): surface.blit(self.image, self.rect)
# --- End of Obstacle Class ---

# --- Game State Variables ---
obstacles = []; obstacle_spawn_timer = 0; obstacle_spawn_delay = OBSTACLE_INITIAL_SPAWN_DELAY
obstacle_speed = OBSTACLE_INITIAL_SPEED; score = 0; high_score = 0; game_active = True

# --- Theme State Variables ---
is_dark_mode = False; current_bg_color = WHITE; current_fg_color = BLACK; current_line_color = BLACK

# --- Snowflakes List ---
snowflakes = []
for _ in range(NUM_SNOWFLAKES):
    x = random.randint(0, WIDTH); y = random.randint(-HEIGHT, HEIGHT)
    dx = random.uniform(-0.3, 0.3); dy = random.uniform(0.8, 1.8); size = random.randint(1, 3)
    snowflakes.append([x, y, dx, dy, size])

# --- Functions ---
def draw_text(text, font_to_use, color, surface, x, y, center=False):
    textobj = font_to_use.render(text, True, color); textrect = textobj.get_rect()
    if center: textrect.center = (x, y)
    else: textrect.topleft = (x, y)
    surface.blit(textobj, textrect)

def update_theme(current_score):
    global is_dark_mode, current_bg_color, current_fg_color, current_line_color
    theme_level = current_score // THEME_CHANGE_SCORE_INTERVAL; should_be_dark = (theme_level % 2) == 1
    if should_be_dark != is_dark_mode:
        is_dark_mode = should_be_dark
        if is_dark_mode: current_bg_color, current_fg_color, current_line_color = DARK_GREY, LIGHT_GREY, LIGHT_GREY
        else: current_bg_color, current_fg_color, current_line_color = WHITE, BLACK, BLACK

def reset_game():
    global high_score, obstacles, score, obstacle_speed, obstacle_spawn_delay, game_active
    global player_y_velocity, is_jumping, is_ducking, on_ground, dino_rect, dino_current_img
    global is_dark_mode, current_bg_color, current_fg_color, current_line_color, touch_ducking

    obstacles.clear();
    if score > high_score: high_score = score
    score = 0; obstacle_speed = OBSTACLE_INITIAL_SPEED; obstacle_spawn_delay = OBSTACLE_INITIAL_SPAWN_DELAY
    dino_rect = dino_normal_img.get_rect(midbottom=(100, GROUND_HEIGHT)); dino_current_img = dino_normal_img
    player_y_velocity = 0; is_jumping = False; is_ducking = False; on_ground = True; touch_ducking = False # Reset touch ducking state
    is_dark_mode = False; current_bg_color = WHITE; current_fg_color = BLACK; current_line_color = BLACK
    game_active = True

def update_and_draw_snow(surface):
    for flake in snowflakes:
        flake[0] += flake[2]; flake[1] += flake[3]
        pygame.draw.circle(surface, SNOW_COLOR, (int(flake[0]), int(flake[1])), flake[4])
        if flake[1] > HEIGHT + 10 or flake[0] < -10 or flake[0] > WIDTH + 10:
            flake[1] = random.randint(-50, -10); flake[0] = random.randint(0, WIDTH)

# --- Main Game Loop ---
# --- Start Music Playback ---
if pygame.mixer.get_init():
    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.play(loops=-1)
# --- End Start Music ---

running = True
while running:
    # --- Event Handling (Keyboard and NEW Touch/Mouse) ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

        # --- Touch / Mouse Input ---
        if event.type == pygame.MOUSEBUTTONDOWN:
            touch_pos = event.pos
            if game_active:
                # Tap Right Half = Jump
                if touch_pos[0] >= WIDTH // 2:
                    if on_ground and not is_ducking:
                         player_y_velocity = JUMP_HEIGHT; is_jumping = True; on_ground = False
                # Tap Left Half = Start Ducking
                elif touch_pos[0] < WIDTH // 2:
                    if on_ground:
                        is_ducking = True
                        touch_ducking = True # Flag that ducking started via touch
            else: # Game Over Screen - Tap anywhere to restart
                reset_game()
                # Break from event loop after restart? Optional, maybe not needed.

        if event.type == pygame.MOUSEBUTTONUP:
             # If ducking was started by touch, stop ducking on release
             if touch_ducking:
                  is_ducking = False
                  touch_ducking = False # Reset flag

        # --- Keyboard Input ---
        if event.type == pygame.KEYDOWN:
            if game_active:
                if (event.key == pygame.K_SPACE or event.key == pygame.K_UP) and on_ground and not is_ducking:
                    player_y_velocity = JUMP_HEIGHT; is_jumping = True; on_ground = False
                elif (event.key == pygame.K_DOWN or event.key == pygame.K_s) and on_ground:
                    is_ducking = True
                    touch_ducking = False # Ensure keyboard ducking doesn't get stuck by touch release
            else: # Game Over Screen
                 if event.key == pygame.K_SPACE: reset_game()

        if event.type == pygame.KEYUP:
             if game_active:
                 if (event.key == pygame.K_DOWN or event.key == pygame.K_s) and not touch_ducking: # Only stop duck if it wasn't touch initiated
                     is_ducking = False
    # --- End Event Handling ---


    # --- Game Active Logic ---
    if game_active:
        # Updates (Score, Speed, Theme)
        score += 1
        score_level = score // OBSTACLE_SPEED_INCREASE_INTERVAL
        new_speed = OBSTACLE_INITIAL_SPEED + score_level * OBSTACLE_SPEED_INCREASE_AMOUNT
        if new_speed > obstacle_speed: obstacle_speed = new_speed
        update_theme(score)

        # Drawing (Background, Snow, Ground)
        screen.fill(current_bg_color)
        if is_dark_mode: update_and_draw_snow(screen)
        pygame.draw.line(screen, current_line_color, (0, GROUND_HEIGHT), (WIDTH, GROUND_HEIGHT), 2)

        # Player Physics & State
        player_y_velocity += GRAVITY; dino_rect.y += player_y_velocity
        if dino_rect.bottom >= GROUND_HEIGHT:
            dino_rect.bottom = GROUND_HEIGHT; player_y_velocity = 0; is_jumping = False; on_ground = True

        # Ducking Image Switch (Important: Handle state before image switch)
        current_img_before_duck_check = dino_current_img # Store current image
        target_img = dino_normal_img
        if is_ducking and on_ground:
            target_img = dino_duck_img

        if dino_current_img != target_img:
             dino_current_img = target_img
             current_bottom = dino_rect.bottom # Preserve bottom position
             dino_rect = dino_current_img.get_rect(midbottom=(dino_rect.centerx, current_bottom))
             if dino_rect.bottom > GROUND_HEIGHT: dino_rect.bottom = GROUND_HEIGHT # Re-snap just in case


        # Obstacle Spawning
        obstacle_spawn_timer += 1
        if obstacle_spawn_timer >= obstacle_spawn_delay:
            obstacle_spawn_timer = 0; obstacle_type = 'cactus'
            spawned_special = False
            if score >= KAMIKAZE_MIN_SCORE and random.random() < KAMIKAZE_CHANCE:
                 obstacle_type = 'kamikaze_pterodactyl'; spawned_special = True
            elif score >= LEVITATING_CACTUS_MIN_SCORE and random.random() < LEVITATING_CACTUS_CHANCE:
                 obstacle_type = 'levitating_cactus'; spawned_special = True

            if not spawned_special:
                if score >= PTERODACTYL_MIN_SCORE and random.random() < PTERODACTYL_CHANCE:
                    if random.random() < SWOOPING_PTERODACTYL_CHANCE: obstacle_type = 'swooping_pterodactyl'
                    else: obstacle_type = 'pterodactyl'

            new_obstacle = Obstacle(obstacle_type)
            can_spawn = True
            if obstacles:
                last_obstacle = obstacles[-1]; min_dist = 150 + obstacle_speed * 5
                if WIDTH - last_obstacle.rect.right < min_dist: can_spawn = False
            if can_spawn:
                obstacles.append(new_obstacle)
                obstacle_spawn_delay = max(OBSTACLE_MIN_SPAWN_DELAY, OBSTACLE_INITIAL_SPAWN_DELAY - (score // 150))
            else: obstacle_spawn_timer = int(obstacle_spawn_delay * 0.3)

        # Obstacle Update, Draw, Collide, Score
        new_obstacles_list = []
        collision_detected = False
        for obs in list(obstacles):
            obs.update(obstacle_speed, dino_rect); obs.draw(screen)
            if obs.rect.right > 0 and obs.rect.top < HEIGHT + 20:
                 new_obstacles_list.append(obs)
                 if not collision_detected and dino_rect.colliderect(obs.rect):
                     game_active = False; collision_detected = True
            elif not obs.passed and obs.rect.right < dino_rect.left:
                 score += 10; obs.passed = True
        if not game_active: continue
        obstacles = new_obstacles_list

        # Draw Player & Scores
        screen.blit(dino_current_img, dino_rect)
        draw_text(f"Score: {score}", small_font, current_fg_color, screen, WIDTH - 150, 10)
        draw_text(f"HI: {high_score}", small_font, current_fg_color, screen, WIDTH - 150, 30)

    # --- Game Over Screen ---
    else:
        screen.fill(current_bg_color)
        if is_dark_mode: update_and_draw_snow(screen)
        current_final_score = score; display_high = max(current_final_score, high_score)
        draw_text("GAME OVER", font, current_fg_color, screen, WIDTH // 2, HEIGHT // 2 - 50, center=True)
        draw_text(f"Your Score: {current_final_score}", small_font, current_fg_color, screen, WIDTH // 2, HEIGHT // 2, center=True)
        draw_text(f"High Score: {display_high}", small_font, current_fg_color, screen, WIDTH // 2, HEIGHT // 2 + 30, center=True)
        draw_text("Press SPACE or TAP to Restart", small_font, current_fg_color, screen, WIDTH // 2, HEIGHT // 2 + 70, center=True) # Updated text

    # --- Display Update ---
    pygame.display.flip()
    clock.tick(FPS)

# --- Cleanup ---
if pygame.mixer.get_init(): pygame.mixer.music.stop()
pygame.quit()
sys.exit()