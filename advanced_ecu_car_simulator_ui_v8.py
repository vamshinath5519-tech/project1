import pygame
import math
import random
from datetime import datetime
from collections import deque

# ============================================================
# ADVANCED ECU CAR SIMULATOR
# ------------------------------------------------------------
# Controls:
#
# Engine / Vehicle:
#   S              -> Start / Stop engine
#   UP Arrow       -> Accelerate
#   DOWN Arrow     -> Brake
#   LEFT Arrow     -> Steer left
#   RIGHT Arrow    -> Steer right
#   A              -> Gear up: R -> N -> 1 -> 2 -> 3 -> 4 -> 5 -> 6
#   Z              -> Gear down: 6 -> 5 -> 4 -> 3 -> 2 -> 1 -> N -> R
#   M              -> Toggle Drive Mode: CITY / TRACK
#
# Vehicle Features:
#   C              -> AC ON/OFF
#   D              -> Driver door open/close
#   P              -> Passenger door open/close
#   B              -> Seatbelt ON/OFF
#   H              -> Headlights ON/OFF
#   Q              -> Left indicator ON/OFF
#   E              -> Right indicator ON/OFF
#   X              -> Hazard lights ON/OFF
#   R              -> Rain ON/OFF
#   L              -> Parking sensor ON/OFF
#
# Fault / Test Simulation:
#   K              -> Simulate knock event
#   O              -> Simulate low oil
#   T              -> Simulate tire pressure drop
#   F              -> Simulate fuel pressure fault
#   SPACE          -> Reset faults / damage
#
# Quit:
#   ESC            -> Exit
# ============================================================

pygame.init()

# BUG 2 Fixed by team 1,3,5 - Use fullscreen/adaptive display mode instead of fixed window
# BUG 3 Fixed by team 1,3,5 - Use current display resolution scaling instead of hardcoded 1400x850
_display_info = pygame.display.Info()
NATIVE_W = _display_info.current_w if _display_info.current_w > 0 else 1400
NATIVE_H = _display_info.current_h if _display_info.current_h > 0 else 850
# Target design resolution; scale to fit the actual screen
DESIGN_W, DESIGN_H = 1400, 850
WIDTH  = min(NATIVE_W, DESIGN_W)
HEIGHT = min(NATIVE_H, DESIGN_H)
# Scale factors allow every draw position/size to adapt to the real display
SCALE_X = WIDTH  / DESIGN_W
SCALE_Y = HEIGHT / DESIGN_H
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Advanced Automotive ECU Simulator - Sensors, Logs, Graphs, Damage, Drive Modes")

clock = pygame.time.Clock()
FPS = 60

# Fonts
font = pygame.font.SysFont("Arial", 18)
small_font = pygame.font.SysFont("Arial", 15)
big_font = pygame.font.SysFont("Arial", 30, bold=True)
title_font = pygame.font.SysFont("Arial", 36, bold=True)

# Colors
WHITE = (245, 245, 245)
BLACK = (15, 15, 15)
DARK = (25, 25, 25)
DARK_GRAY = (45, 45, 45)
GRAY = (90, 90, 90)
LIGHT_GRAY = (170, 170, 170)
GREEN = (0, 220, 90)
RED = (230, 50, 50)
YELLOW = (245, 210, 20)
ORANGE = (255, 145, 0)
BLUE = (60, 140, 255)
CYAN = (0, 220, 220)
PURPLE = (180, 100, 255)

ROAD_GRAY = (80, 80, 80)
GRASS = (35, 120, 45)

# Simulation variables
car_x = 520
car_y = 610
car_angle = 0.0

speed = 0.0
rpm = 800.0
gear = 0  # -1 = Reverse, 0 = Neutral, 1..6 = Forward gears
max_gear = 6
min_gear = -1
reverse_speed_limit = -28.0

engine_on = False
drive_mode = "CITY"

ac_on = False
driver_door_open = False
passenger_door_open = False
seatbelt_on = False
headlights_on = False
left_indicator = False
right_indicator = False
hazard_on = False
rain_on = False
parking_sensor_on = False

# UI / safety state
# Used to prevent the ECU log from getting flooded every frame
# while a door-open drive interlock is active.
door_interlock_logged = False
neutral_drive_logged = False
infotainment_message = "Welcome. Press S to start engine."

brake_pressed = False
accelerator_pressed = False
knock_event = False

fuel_level = 100.0
fuel_flow = 0.0
fuel_pressure = 45.0
oil_level = 100.0
oil_pressure = 42.0
coolant_temp = 82.0
engine_temp = 85.0
ambient_temp = 28.0
battery_voltage = 12.6
battery_soc = 100.0

tire_pressure_fl = 34.0
tire_pressure_fr = 34.0
tire_pressure_rl = 34.0
tire_pressure_rr = 34.0

brake_fluid_pressure = 0.0
steering_angle_sensor = 0.0
yaw_rate = 0.0
lateral_accel = 0.0
gyro_x = 0.0
gyro_y = 0.0
gyro_z = 0.0

maf = 2.5
map_pressure = 35.0
tps = 0.0
o2_sensor = 0.45
camshaft_position = 0.0

vss = 0.0
abs_wheel_fl = 0.0
abs_wheel_fr = 0.0
abs_wheel_rl = 0.0
abs_wheel_rr = 0.0

gps_lat = 12.9716
gps_lon = 77.5946

radar_distance = 80.0
proximity_distance = 10.0
blind_spot_left = False
blind_spot_right = False
photo_lux = 800.0
rain_intensity = 0.0

# Visual rain drops. They are drawn only when rain_on is True.
rain_particles = [
    [random.randint(240, 800), random.randint(120, HEIGHT), random.randint(8, 18)]
    for _ in range(160)
]

lidar_object_distance = 70.0
camera_object_detected = False

traction_control_active = False
abs_active = False
crash_sensor_triggered = False
damage = 0.0

distance_km = 0.0
road_scroll = 0.0
indicator_timer = 0
indicator_visible = True

# AI / traffic vehicles on the road.
# The player car can overtake the TARGET by moving into another lane.
LANE_CENTERS = [360, 520, 680]
traffic_cars = [
    {"label": "TARGET", "x": 520, "y": 205.0, "w": 52, "h": 96, "speed": 42.0, "color": BLUE, "passed": False},
    {"label": "CAR A", "x": 360, "y": -70.0, "w": 48, "h": 88, "speed": 58.0, "color": PURPLE, "passed": False},
    {"label": "CAR B", "x": 680, "y": -260.0, "w": 48, "h": 88, "speed": 72.0, "color": ORANGE, "passed": False},
    {"label": "CAR C", "x": 360, "y": -520.0, "w": 48, "h": 88, "speed": 35.0, "color": CYAN, "passed": False},
]
traffic_collision_cooldown = 0
overtake_count = 0

# Logs and graphs
ecu_logs = deque(maxlen=18)
speed_history = deque(maxlen=120)
rpm_history = deque(maxlen=120)
temp_history = deque(maxlen=120)
fuel_history = deque(maxlen=120)
oil_history = deque(maxlen=120)
battery_history = deque(maxlen=120)

# Gear limits
gear_speed_limit = {
    1: 35,
    2: 60,
    3: 95,
    4: 135,
    5: 180,
    6: 230
}

gear_min_speed = {
    1: 0,
    2: 15,
    3: 35,
    4: 65,
    5: 100,
    6: 145
}


def get_gear_label():
    if gear == -1:
        return "R"
    if gear == 0:
        return "N"
    return str(gear)


def get_drive_direction_label():
    if speed < -0.5:
        return "REVERSE"
    if speed > 0.5:
        return "FORWARD"
    return "STOPPED"


def approach_zero(value, amount):
    """Move a signed value toward zero without crossing it."""
    if value > 0:
        return max(0, value - amount)
    if value < 0:
        return min(0, value + amount)
    return 0


def log_ecu(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    ecu_logs.appendleft(f"[{timestamp}] [{level}] {message}")


def draw_text(text, x, y, color=WHITE, selected_font=None):
    if selected_font is None:
        selected_font = font
    surface = selected_font.render(str(text), True, color)
    screen.blit(surface, (x, y))


def draw_box(x, y, w, h, title=None):
    pygame.draw.rect(screen, DARK, (x, y, w, h))
    pygame.draw.rect(screen, LIGHT_GRAY, (x, y, w, h), 1)
    if title:
        pygame.draw.rect(screen, DARK_GRAY, (x, y, w, 28))
        draw_text(title, x + 8, y + 5, YELLOW, small_font)


def clamp(value, low, high):
    return max(low, min(high, value))


# ------------------------------------------------------------
# Geometry helpers for realistic rotated-car drawing/collision
# ------------------------------------------------------------
def get_rotated_rect_points(cx, cy, w, h, angle_degrees):
    """Return the 4 corner points of a rotated rectangle."""
    angle_rad = math.radians(angle_degrees)
    half_w = w / 2
    half_h = h / 2

    local_points = [
        (-half_w, -half_h),
        (half_w, -half_h),
        (half_w, half_h),
        (-half_w, half_h),
    ]

    rotated_points = []
    for px, py in local_points:
        rx = px * math.cos(angle_rad) - py * math.sin(angle_rad)
        ry = px * math.sin(angle_rad) + py * math.cos(angle_rad)
        rotated_points.append((cx + rx, cy + ry))

    return rotated_points


def get_player_car_polygon():
    """Current visual polygon of the player car; used for collision too."""
    return get_rotated_rect_points(car_x, car_y, 48, 90, car_angle)


def get_axis_normal(p1, p2):
    """Return a perpendicular axis for SAT polygon collision."""
    edge_x = p2[0] - p1[0]
    edge_y = p2[1] - p1[1]
    return (-edge_y, edge_x)


def project_polygon(points, axis):
    """Project polygon points onto an axis."""
    axis_x, axis_y = axis
    values = [point[0] * axis_x + point[1] * axis_y for point in points]
    return min(values), max(values)


def polygons_intersect(poly_a, poly_b):
    """Convex polygon collision using Separating Axis Theorem."""
    polygons = (poly_a, poly_b)

    for polygon in polygons:
        for i in range(len(polygon)):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % len(polygon)]
            axis = get_axis_normal(p1, p2)

            # Avoid divide-by-zero axes.
            axis_length = math.hypot(axis[0], axis[1])
            if axis_length == 0:
                continue

            axis = (axis[0] / axis_length, axis[1] / axis_length)
            min_a, max_a = project_polygon(poly_a, axis)
            min_b, max_b = project_polygon(poly_b, axis)

            if max_a < min_b or max_b < min_a:
                return False

    return True


def traffic_vehicle_polygon(vehicle):
    """Traffic vehicles are vertical rectangles, returned as polygon points."""
    left = vehicle["x"] - vehicle["w"] / 2
    top = vehicle["y"]
    right = vehicle["x"] + vehicle["w"] / 2
    bottom = vehicle["y"] + vehicle["h"]
    return [(left, top), (right, top), (right, bottom), (left, bottom)]


def get_drive_parameters():
    if drive_mode == "CITY":
        return {
            "acceleration": 0.16,
            "brake_force": 0.42,
            "steering_response": 1.0,
            "fuel_multiplier": 0.85,
            "traction_sensitivity": 0.7,
            "max_speed": 160
        }
    else:
        return {
            "acceleration": 0.28,
            "brake_force": 0.55,
            "steering_response": 1.35,
            "fuel_multiplier": 1.45,
            "traction_sensitivity": 1.25,
            "max_speed": 230
        }


def draw_road():
    global road_scroll

    screen.fill(GRASS)

    # Main road
    pygame.draw.rect(screen, ROAD_GRAY, (250, 120, 540, 730))

    # Road borders
    pygame.draw.line(screen, WHITE, (250, 120), (250, HEIGHT), 5)
    pygame.draw.line(screen, WHITE, (790, 120), (790, HEIGHT), 5)

    # Side red/white rumble strips
    strip_h = 40
    # Signed speed means forward scrolls one way and reverse scrolls the other way.
    road_scroll = (road_scroll + speed * 0.08) % (strip_h * 2)

    for y in range(120, HEIGHT + 100, strip_h):
        yy = y + road_scroll
        color = RED if (y // strip_h) % 2 == 0 else WHITE
        pygame.draw.rect(screen, color, (225, yy, 20, strip_h))
        pygame.draw.rect(screen, color, (795, yy, 20, strip_h))

    # Lane markings
    for y in range(120, HEIGHT + 100, 80):
        moving_y = y + road_scroll
        pygame.draw.line(screen, WHITE, (520, moving_y), (520, moving_y + 45), 4)

    # Traffic vehicles are drawn separately so they can move independently.


def draw_vehicle_sprite(x, y, w, h, color, label):
    """Draws a vertical traffic vehicle centered at x/y."""
    rect = pygame.Rect(int(x - w / 2), int(y), int(w), int(h))
    pygame.draw.rect(screen, color, rect, border_radius=5)
    pygame.draw.rect(screen, BLACK, rect, 2, border_radius=5)

    # Windshield / direction marker
    pygame.draw.circle(screen, CYAN, (rect.centerx, rect.y + 16), 6)

    # Rear lights
    pygame.draw.circle(screen, RED, (rect.x + 11, rect.bottom - 12), 4)
    pygame.draw.circle(screen, RED, (rect.right - 11, rect.bottom - 12), 4)

    draw_text(label, rect.x - 2, rect.bottom + 5, WHITE, small_font)


def draw_traffic():
    """Draw all AI traffic vehicles on the road."""
    for vehicle in traffic_cars:
        draw_vehicle_sprite(
            vehicle["x"], vehicle["y"], vehicle["w"], vehicle["h"], vehicle["color"], vehicle["label"]
        )


def update_traffic_and_overtake():
    """Move traffic, detect overtakes, and use polygon-based crash detection."""
    global damage, speed, crash_sensor_triggered, radar_distance, lidar_object_distance
    global camera_object_detected, traffic_collision_cooldown, overtake_count

    player_poly = get_player_car_polygon()
    nearest_ahead = None

    if traffic_collision_cooldown > 0:
        traffic_collision_cooldown -= 1

    for vehicle in traffic_cars:
        # Relative motion: when the player is faster than the traffic car,
        # that car appears to come downward and can be overtaken.
        relative_speed = max(0, speed - vehicle["speed"])
        vehicle["y"] += relative_speed * 0.045

        rect = pygame.Rect(
            int(vehicle["x"] - vehicle["w"] / 2),
            int(vehicle["y"]),
            int(vehicle["w"]),
            int(vehicle["h"]),
        )
        vehicle_poly = traffic_vehicle_polygon(vehicle)

        # Distance to vehicles ahead for radar/lidar/camera.
        if rect.centery < car_y:
            distance_px = car_y - rect.centery
            lane_offset = abs(car_x - rect.centerx)
            # Prefer same/near lane objects for forward radar relevance.
            if lane_offset < 130:
                if nearest_ahead is None or distance_px < nearest_ahead:
                    nearest_ahead = distance_px

        # Collision now matches the rotated player car polygon instead of
        # a fixed unrotated rectangle. This avoids false misses/hits while turning.
        if polygons_intersect(player_poly, vehicle_poly) and traffic_collision_cooldown == 0:
            relative_impact_speed = abs(speed - vehicle["speed"])
            side_offset = abs(car_x - vehicle["x"])

            # More overlap in the same lane = stronger impact.
            overlap_factor = 1.0 if side_offset < 35 else 0.65
            impact = max(8, relative_impact_speed * 0.45 * overlap_factor)

            damage = clamp(damage + impact, 0, 100)
            speed *= 0.40
            crash_sensor_triggered = damage > 25
            traffic_collision_cooldown = 45
            log_ecu(f"Collision with {vehicle['label']} - polygon impact detected", "FAULT")

        # Overtake event: target has moved behind the player without collision.
        if vehicle["label"] == "TARGET" and not vehicle["passed"] and rect.top > car_y + 90:
            vehicle["passed"] = True
            overtake_count += 1
            log_ecu("Target vehicle overtaken successfully", "INFO")

        # BUG 12 Fixed by team 1,3,5 - AI-to-AI collision PREVENTION with physical separation
        # Each vehicle pair is checked; on overlap the slower car is pushed down (away)
        # so cars never visually overlap. A cooldown per-pair prevents log spam.
        for other in traffic_cars:
            if other is vehicle:
                continue
            # Rough AABB pre-check before expensive SAT (performance guard)
            dx = abs(vehicle["x"] - other["x"])
            dy = abs((vehicle["y"] + vehicle["h"] / 2) - (other["y"] + other["h"] / 2))
            if dx > (vehicle["w"] + other["w"]) or dy > (vehicle["h"] + other["h"]):
                continue  # clearly separated, skip SAT
            other_poly = traffic_vehicle_polygon(other)
            if polygons_intersect(vehicle_poly, other_poly):
                relative_ai_speed = abs(vehicle["speed"] - other["speed"])
                # Push the slower/behind car further down to break the overlap
                separation = vehicle["h"] * 0.6 + other["h"] * 0.6
                if vehicle["y"] >= other["y"]:
                    vehicle["y"] = other["y"] + separation
                else:
                    other["y"] = vehicle["y"] + separation
                # Equalise speeds slightly so they stop catching each other
                avg_speed = (vehicle["speed"] + other["speed"]) / 2
                vehicle["speed"] = avg_speed
                other["speed"]   = avg_speed * 0.92
                if relative_ai_speed > 3:
                    log_ecu(
                        f"AI separation: {vehicle['label']} & {other['label']} pushed apart ({relative_ai_speed:.1f} km/h diff)",
                        "FAULT"
                    )

        # Recycle traffic vehicles to keep the road populated.
        if vehicle["y"] > HEIGHT + 140:
            lane = random.choice(LANE_CENTERS)
            vehicle["x"] = lane
            vehicle["y"] = random.uniform(-520, -120)
            vehicle["speed"] = random.uniform(35, 85)
            vehicle["passed"] = False
            if vehicle["label"] == "TARGET":
                vehicle["x"] = 520
                vehicle["speed"] = random.uniform(38, 55)

        if vehicle["y"] < -650:
            vehicle["y"] = random.uniform(-500, -150)

    if nearest_ahead is None:
        radar_distance = 100.0
        lidar_object_distance = 100.0
        camera_object_detected = False
    else:
        radar_distance = clamp(nearest_ahead * 0.18, 3, 100)
        lidar_object_distance = clamp(radar_distance + random.uniform(-2.5, 2.5), 3, 120)
        camera_object_detected = radar_distance < 60

def draw_rain_effect():
    """Draw animated rain streaks over the driving area only.

    Toggle using R. This version is deliberately more visible for
    classroom/demo use and does not cover the ECU panels.
    """
    global rain_particles

    if not rain_on:
        return

    # Dark wet-weather overlay on the driving area only.
    overlay = pygame.Surface((790, HEIGHT - 120), pygame.SRCALPHA)
    overlay.fill((15, 25, 40, 75))
    screen.blit(overlay, (0, 120))

    # Stronger rain, slants more as vehicle speed increases.
    # Use absolute speed so rain still looks correct when reversing.
    abs_speed = abs(speed)
    wind_slant = -6 - min(abs_speed * 0.04, 8)
    rain_speed = 10 + min(abs_speed * 0.07, 16)

    for drop in rain_particles:
        x, y, length = drop
        pygame.draw.line(
            screen,
            (175, 210, 255),
            (int(x), int(y)),
            (int(x + wind_slant), int(y + length)),
            2,
        )

        drop[0] += wind_slant * 0.22
        drop[1] += rain_speed

        if drop[1] > HEIGHT or drop[0] < 220 or drop[0] > 815:
            drop[0] = random.randint(240, 800)
            drop[1] = random.randint(120, 170)
            drop[2] = random.randint(12, 26)

    # Simple windshield/wiper sweep feel near player car.
    pygame.draw.arc(screen, (210, 235, 255), (430, 520, 185, 125), math.radians(205), math.radians(338), 3)
    pygame.draw.arc(screen, (120, 170, 220), (425, 515, 195, 135), math.radians(205), math.radians(338), 1)



def draw_car():
    angle_rad = math.radians(car_angle)

    car_length = 90
    car_width = 48
    rotated = get_player_car_polygon()

    # Car color changes with damage
    if damage < 30:
        car_color = RED
    elif damage < 70:
        car_color = ORANGE
    else:
        car_color = (120, 20, 20)

    # Local direction vectors. These are used for every visual part attached
    # to the car, so headlights, brake lights and indicators rotate together.
    forward_x = math.sin(angle_rad)
    forward_y = -math.cos(angle_rad)
    right_x = math.cos(angle_rad)
    right_y = math.sin(angle_rad)

    # Headlight beam is drawn before the car body, so it appears to come
    # from the front of the vehicle without covering the body.
    if headlights_on or photo_lux < 250:
        left_light_x = car_x + forward_x * 42 - right_x * 15
        left_light_y = car_y + forward_y * 42 - right_y * 15
        right_light_x = car_x + forward_x * 42 + right_x * 15
        right_light_y = car_y + forward_y * 42 + right_y * 15

        beam_length = 165
        beam_spread = 38

        left_far_x = left_light_x + forward_x * beam_length
        left_far_y = left_light_y + forward_y * beam_length
        right_far_x = right_light_x + forward_x * beam_length
        right_far_y = right_light_y + forward_y * beam_length

        left_beam = [
            (left_light_x, left_light_y),
            (left_far_x - right_x * beam_spread, left_far_y - right_y * beam_spread),
            (left_far_x + right_x * beam_spread * 0.35, left_far_y + right_y * beam_spread * 0.35),
        ]

        right_beam = [
            (right_light_x, right_light_y),
            (right_far_x - right_x * beam_spread * 0.35, right_far_y - right_y * beam_spread * 0.35),
            (right_far_x + right_x * beam_spread, right_far_y + right_y * beam_spread),
        ]

        beam_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(beam_layer, (255, 255, 130, 70), left_beam)
        pygame.draw.polygon(beam_layer, (255, 255, 130, 70), right_beam)
        pygame.draw.line(beam_layer, (255, 255, 170, 95), (left_light_x, left_light_y), (left_far_x, left_far_y), 2)
        pygame.draw.line(beam_layer, (255, 255, 170, 95), (right_light_x, right_light_y), (right_far_x, right_far_y), 2)
        screen.blit(beam_layer, (0, 0))

    # Car body
    pygame.draw.polygon(screen, car_color, rotated)
    pygame.draw.polygon(screen, BLACK, rotated, 2)

    # Front marker / windshield
    front_x = car_x + forward_x * 35
    front_y = car_y + forward_y * 35
    pygame.draw.circle(screen, BLUE, (int(front_x), int(front_y)), 8)

    # Brake lights
    rear_left_x = car_x - forward_x * 35 - right_x * 15
    rear_left_y = car_y - forward_y * 35 - right_y * 15
    rear_right_x = car_x - forward_x * 35 + right_x * 15
    rear_right_y = car_y - forward_y * 35 + right_y * 15

    brake_color = RED if brake_pressed else (100, 0, 0)
    pygame.draw.circle(screen, brake_color, (int(rear_left_x), int(rear_left_y)), 6)
    pygame.draw.circle(screen, brake_color, (int(rear_right_x), int(rear_right_y)), 6)

    # Headlamp bulbs after body, fixed to the car front.
    if headlights_on or photo_lux < 250:
        left_light_x = car_x + forward_x * 42 - right_x * 15
        left_light_y = car_y + forward_y * 42 - right_y * 15
        right_light_x = car_x + forward_x * 42 + right_x * 15
        right_light_y = car_y + forward_y * 42 + right_y * 15
        pygame.draw.circle(screen, YELLOW, (int(left_light_x), int(left_light_y)), 5)
        pygame.draw.circle(screen, YELLOW, (int(right_light_x), int(right_light_y)), 5)

    # Indicators, attached to car sides instead of fixed screen offsets.
    show_left = hazard_on or left_indicator
    show_right = hazard_on or right_indicator

    if indicator_visible:
        if show_left:
            indicator_x = car_x - right_x * 30 + forward_x * 5
            indicator_y = car_y - right_y * 30 + forward_y * 5
            pygame.draw.circle(screen, YELLOW, (int(indicator_x), int(indicator_y)), 6)
        if show_right:
            indicator_x = car_x + right_x * 30 + forward_x * 5
            indicator_y = car_y + right_y * 30 + forward_y * 5
            pygame.draw.circle(screen, YELLOW, (int(indicator_x), int(indicator_y)), 6)

    # Door open visual, also attached to car-local side vectors.
    if driver_door_open:
        hinge_x = car_x - right_x * 24 - forward_x * 8
        hinge_y = car_y - right_y * 24 - forward_y * 8
        door_x = hinge_x - right_x * 48 - forward_x * 25
        door_y = hinge_y - right_y * 48 - forward_y * 25
        pygame.draw.line(screen, CYAN, (hinge_x, hinge_y), (door_x, door_y), 4)
    if passenger_door_open:
        hinge_x = car_x + right_x * 24 - forward_x * 8
        hinge_y = car_y + right_y * 24 - forward_y * 8
        door_x = hinge_x + right_x * 48 - forward_x * 25
        door_y = hinge_y + right_y * 48 - forward_y * 25
        pygame.draw.line(screen, CYAN, (hinge_x, hinge_y), (door_x, door_y), 4)

def update_vehicle(keys):
    global speed, rpm, car_x, car_y, car_angle
    global brake_pressed, accelerator_pressed
    global engine_on
    global engine_temp, coolant_temp, oil_level, oil_pressure
    global fuel_level, fuel_flow, fuel_pressure
    global battery_voltage, battery_soc
    global steering_angle_sensor, yaw_rate, lateral_accel
    global gyro_x, gyro_y, gyro_z
    global maf, map_pressure, tps, o2_sensor, camshaft_position
    global vss, abs_wheel_fl, abs_wheel_fr, abs_wheel_rl, abs_wheel_rr
    global brake_fluid_pressure, rain_intensity, photo_lux
    global radar_distance, proximity_distance, lidar_object_distance
    global camera_object_detected, blind_spot_left, blind_spot_right
    global traction_control_active, abs_active, crash_sensor_triggered
    global damage, distance_km, knock_event
    global gps_lat, gps_lon
    global door_interlock_logged, neutral_drive_logged

    params = get_drive_parameters()

    # Door-open interlock blocks throttle input.
    brake_pressed = keys[pygame.K_DOWN]
    # BUG 10 Fixed by team 1,3,5 - Brake overrides throttle when both are pressed
    accelerator_pressed = keys[pygame.K_UP] and not driver_door_open and not passenger_door_open and not brake_pressed

    if not engine_on:
        if abs(speed) > 0:
            speed = approach_zero(speed, 0.08)
        rpm = max(0, rpm - 20)
        battery_soc -= 0.002 if headlights_on or ac_on else 0.0005
        battery_soc = clamp(battery_soc, 0, 100)
        battery_voltage = 11.5 + battery_soc / 100 * 1.2
        return

    # ------------------------------------------------------------
    # Door safety interlock
    # If any door is open, the vehicle must not accelerate.
    # If a door opens while moving, ECU applies braking until stop.
    # ------------------------------------------------------------
    if driver_door_open or passenger_door_open:
        accelerator_pressed = False
        tps = 0
        traction_control_active = False
        abs_active = False

        if abs(speed) > 0:
            speed = approach_zero(speed, 0.8)
            brake_fluid_pressure = clamp(brake_fluid_pressure + 10, 0, 120)

            if not door_interlock_logged:
                log_ecu("Door open - drive inhibited, braking applied", "FAULT")
                door_interlock_logged = True
        else:
            brake_fluid_pressure = clamp(brake_fluid_pressure - 3, 0, 120)

            if not door_interlock_logged:
                log_ecu("Door open - drive inhibited", "FAULT")
                door_interlock_logged = True

        rpm = 850 if engine_on else 0
        vss = abs(speed)

        # Keep wheel-speed sensors coherent while interlock is active.
        abs_wheel_fl = abs(speed)
        abs_wheel_fr = abs(speed)
        abs_wheel_rl = abs(speed)
        abs_wheel_rr = abs(speed)

        return
    else:
        door_interlock_logged = False

    abs_speed = abs(speed)

    if not seatbelt_on and abs_speed > 10:
        log_ecu("Seatbelt warning active", "WARN")

    # Throttle position
    if accelerator_pressed:
        tps += 3.5
    else:
        tps -= 2.5

    tps = clamp(tps, 0, 100)

    # Acceleration / torque delivery by gear.
    # gear = -1 Reverse, 0 Neutral, 1..6 Forward gears.
    # Neutral allows engine revving but does not drive the wheels.
    if accelerator_pressed and fuel_level > 0 and damage < 95:
        if gear > 0:
            current_limit = gear_speed_limit[gear]
            max_forward_speed = min(params["max_speed"], current_limit)

            if speed < max_forward_speed:
                speed += params["acceleration"] * gear * (1 - damage / 160)
            else:
                speed += params["acceleration"] * 0.12

        elif gear == -1:
            if speed > reverse_speed_limit:
                speed -= params["acceleration"] * 1.25 * (1 - damage / 160)
            else:
                speed -= params["acceleration"] * 0.08

        else:
            # Neutral: no wheel torque, but RPM rises through TPS logic.
            if not neutral_drive_logged:
                log_ecu("Neutral gear - throttle revs engine without vehicle drive", "INFO")
                neutral_drive_logged = True
    else:
        neutral_drive_logged = False

    # Braking always moves the signed vehicle speed toward zero.
    if brake_pressed:
        speed = approach_zero(speed, params["brake_force"])
        brake_fluid_pressure = clamp(brake_fluid_pressure + 8, 0, 120)

        if abs(speed) > 60 and random.random() < 0.01:
            abs_active = True
            log_ecu("ABS modulation active", "INFO")
    else:
        brake_fluid_pressure = clamp(brake_fluid_pressure - 5, 0, 120)
        abs_active = False

    # Natural drag / rolling resistance moves signed speed toward zero.
    drag = 0.025 if drive_mode == "TRACK" else 0.04
    if not accelerator_pressed:
        speed = approach_zero(speed, drag)

    # Rain reduces grip and gently bleeds speed in both directions.
    if rain_on and abs(speed) > 50:
        speed = approach_zero(speed, 0.005)

    speed = clamp(speed, reverse_speed_limit, params["max_speed"])
    abs_speed = abs(speed)

    # Steering
    turn_strength = 0
    if abs_speed > 1:
        turn_strength = max(1.2, 5.5 - abs_speed / 55) * params["steering_response"]

    if keys[pygame.K_LEFT]:
        car_angle -= turn_strength
        steering_angle_sensor = clamp(steering_angle_sensor - 3.5, -45, 45)
    elif keys[pygame.K_RIGHT]:
        car_angle += turn_strength
        steering_angle_sensor = clamp(steering_angle_sensor + 3.5, -45, 45)
    else:
        steering_angle_sensor *= 0.88

    car_angle %= 360

    # Car movement
    # BUG 4 Fixed by team 1,3,5 - Prevent unrealistic sideways driving at 90 degrees.
    # Forward contribution is scaled by cos(steering_angle) so the car cannot
    # drive at full speed sideways when the angle is near 90 degrees.
    angle_rad = math.radians(car_angle)

    movement_speed = abs(speed)

    if speed >= 0:
        direction = 1
    else:
        direction = -1

    car_x += math.sin(angle_rad) * movement_speed * 0.028 * direction
    car_y -= math.cos(angle_rad) * movement_speed * 0.028 * direction

    # Road side collision / damage.
    # Uses the rotated car polygon, not just car_x center. This means the car
    # gets detected when a corner hits the boundary while turning.
    player_poly = get_player_car_polygon()
    min_car_x = min(point[0] for point in player_poly)
    max_car_x = max(point[0] for point in player_poly)

    if min_car_x < 250:
        car_x += 250 - min_car_x
        if abs(speed) > 20:
            damage += abs(speed) * 0.03
            crash_sensor_triggered = damage > 35
            speed *= 0.82
            log_ecu("Left side impact / rotated body boundary hit", "FAULT")

    if max_car_x > 790:
        car_x -= max_car_x - 790
        if abs(speed) > 20:
            damage += abs(speed) * 0.03
            crash_sensor_triggered = damage > 35
            speed *= 0.82
            log_ecu("Right side impact / rotated body boundary hit", "FAULT")

    car_y = clamp(car_y, 430, 780)
    damage = clamp(damage, 0, 100)

    if damage > 80:
        speed *= 0.98
        log_ecu("Severe vehicle damage limiting performance", "FAULT")

    # VSS and ABS wheel speed sensors
    vss = abs_speed
    abs_wheel_fl = abs_speed + random.uniform(-0.5, 0.5)
    abs_wheel_fr = abs_speed + random.uniform(-0.5, 0.5)
    abs_wheel_rl = abs_speed + random.uniform(-0.8, 0.8)
    abs_wheel_rr = abs_speed + random.uniform(-0.8, 0.8)

    # Wheel slip / traction control
    wheel_delta = abs(abs_wheel_fl - abs_wheel_rl)
    traction_control_active = False

    if accelerator_pressed and gear > 0 and abs_speed > 40 and abs(steering_angle_sensor) > 25:
        if random.random() < 0.04 * params["traction_sensitivity"]:
            traction_control_active = True
            speed = approach_zero(speed, 0.4)
            log_ecu("Traction control intervention", "INFO")

    if rain_on and accelerator_pressed and gear > 0 and abs_speed > 35:
        if random.random() < 0.02:
            traction_control_active = True
            speed = approach_zero(speed, 0.6)
            log_ecu("Traction control active due to low grip", "WARN")

    # RPM
    gear_factor = {
        -1: 120,
        1: 105,
        2: 82,
        3: 64,
        4: 50,
        5: 39,
        6: 33  # BUG 9 Fixed by team 1,3,5 - Adjusted 6th gear RPM mapping to reach rev limiter correctly
    }

    if gear == 0:
        # Neutral: RPM responds mainly to throttle, not road speed.
        rpm = 850 + tps * 48
    else:
        rpm = 800 + abs_speed * gear_factor[gear] + tps * 12

        if gear > 1 and abs_speed < gear_min_speed[gear]:
            rpm -= 450

    if damage > 60:
        rpm += random.uniform(-150, 200)

    rpm = clamp(rpm, 650, 7600)

    # Fuel calculations
    load_factor = 0.5 + (rpm / 7600) + (tps / 100)
    fuel_flow = 0.15 + load_factor * params["fuel_multiplier"]

    if ac_on:
        fuel_flow += 0.18

    if traction_control_active:
        fuel_flow += 0.05

    fuel_level -= fuel_flow * 0.00055
    fuel_level = clamp(fuel_level, 0, 100)

    if fuel_level <= 0:
        speed = approach_zero(speed, 0.2)
        rpm -= 100
        log_ecu("Fuel empty - engine starvation", "FAULT")

    # Fuel pressure
    fuel_pressure += random.uniform(-0.25, 0.25)
    fuel_pressure = clamp(fuel_pressure, 0, 55)

    if fuel_pressure < 25:
        log_ecu("Fuel pressure below threshold", "FAULT")
        speed *= 0.995

    # Engine, coolant, oil
    # BUG 11 Fixed by team 1,3,5 - Gradual thermal inertia temperature model:
    #   A "target temperature" is computed from engine load each frame.
    #   engine_temp drifts slowly toward that target (thermal inertia factor 0.003).
    #   This gives a smooth, realistic rise and fall — never instant jumps.
    #   Normal idle/cruise settles at ~88-93 C.
    #   Crash damage pushes the target up; heavy damage can reach 130 C over time.
    #   At 130 C the ECU performs emergency engine shutdown.

    # Target temperature based on engine load and conditions
    target_temp = 88.0 + (rpm / 7600) * 15.0 + (tps / 100.0) * 8.0  # 88-111 C range

    # Ram-air cooling lowers target when moving
    if abs_speed > 10:
        target_temp -= abs_speed * 0.04       # ~4 C less per 100 km/h

    # AC adds load → slightly higher target
    if ac_on:
        target_temp += 5.0

    # Crash damage degrades cooling → target rises proportionally
    if damage > 30:
        target_temp += (damage - 30) * 0.5   # +0.5 C per 1% damage above 30

    target_temp = clamp(target_temp, 70.0, 140.0)

    # Thermal inertia: temperature drifts toward target slowly (0.003 per frame)
    # At 60 FPS this means ~1 C change every ~5-6 seconds under normal conditions
    engine_temp += (target_temp - engine_temp) * 0.003
    engine_temp = clamp(engine_temp, 70.0, 130.0)

    # Emergency engine shutdown at 130 C overheat
    if engine_temp >= 130.0:
        engine_on = False
        engine_temp = 130.0
        log_ecu("OVERHEAT: Engine auto-shutdown at 130 C - allow cooling before restart", "FAULT")

    # Warning at 110 C
    if engine_temp > 110.0:
        log_ecu(f"Engine temp critical: {engine_temp:.1f} C - reduce load", "WARN")

    coolant_temp = clamp(engine_temp - random.uniform(2, 6), 65.0, 125.0)

    oil_level -= rpm * 0.00000005

    if rpm > 5500:
        oil_level -= 0.001

    oil_level = clamp(oil_level, 0, 100)

    oil_pressure = 15 + rpm / 140
    if oil_level < 25:
        oil_pressure *= 0.55
        log_ecu("Low oil level causing oil pressure drop", "FAULT")

    oil_pressure = clamp(oil_pressure, 0, 85)

    # Battery
    if engine_on:
        battery_soc += 0.004
    if headlights_on:
        battery_soc -= 0.002
    if ac_on:
        battery_soc -= 0.0015

    battery_soc = clamp(battery_soc, 0, 100)
    battery_voltage = 12.1 + battery_soc / 100 * 1.1
    if engine_on:
        battery_voltage += 1.0
    battery_voltage = clamp(battery_voltage, 10.5, 14.6)

    # Sensor calculations
    maf = clamp(2.0 + rpm / 700 + tps / 14, 1, 160)
    map_pressure = clamp(25 + tps * 0.65 + rpm / 250, 20, 105)
    o2_sensor = clamp(0.1 + (tps / 100) * 0.8 + random.uniform(-0.03, 0.03), 0.05, 0.95)
    camshaft_position = (camshaft_position + rpm * 0.015) % 720

    if knock_event:
        log_ecu("Knock sensor detected abnormal combustion", "FAULT")
        rpm -= 100
        knock_event = False

    # Gyroscope, yaw, lateral
    yaw_rate = steering_angle_sensor * speed * 0.015
    lateral_accel = abs(steering_angle_sensor) * abs_speed * 0.0009

    gyro_x = random.uniform(-0.02, 0.02)
    gyro_y = lateral_accel
    gyro_z = yaw_rate

    # Rain and photo sensors
    rain_intensity = 70.0 if rain_on else 0.0
    photo_lux = 120.0 if headlights_on else 850.0
    if rain_on:
        photo_lux -= 120

    # Radar, proximity, blind spot, lidar/camera
    radar_distance = clamp(115 - abs_speed * 0.28 + random.uniform(-2, 2), 12, 120)
    lidar_object_distance = clamp(radar_distance + random.uniform(-3, 3), 10, 130)
    proximity_distance = clamp(12 - abs_speed * 0.035 + random.uniform(-0.2, 0.2), 0.5, 12)

    camera_object_detected = radar_distance < 55
    blind_spot_left = random.random() < 0.008 if abs_speed > 25 else False
    blind_spot_right = random.random() < 0.008 if abs_speed > 25 else False

    if blind_spot_left:
        log_ecu("Blind spot warning: LEFT", "WARN")
    if blind_spot_right:
        log_ecu("Blind spot warning: RIGHT", "WARN")

    if radar_distance < 20 and abs_speed > 40:
        log_ecu("Forward collision warning", "WARN")

    if parking_sensor_on and proximity_distance < 3:
        log_ecu("Parking proximity alert", "INFO")

    # Tire pressure gradual behavior
    for name, pressure in [
        ("FL", tire_pressure_fl),
        ("FR", tire_pressure_fr),
        ("RL", tire_pressure_rl),
        ("RR", tire_pressure_rr)
    ]:
        if pressure < 28:
            log_ecu(f"TPMS low pressure: {name}", "WARN")

    # GPS movement
    gps_lat += (speed / 3600) * 0.00001
    gps_lon += math.sin(angle_rad) * (speed / 3600) * 0.00001

    # Distance
    distance_km += abs_speed / 3600 / FPS

    # BUG 8 Fixed by team 1,3,5 - Add speed-limit warning based on drive mode
    speed_limit = 60 if drive_mode == "CITY" else 120
    if abs(speed) > speed_limit and gear > 0:
        log_ecu(f"Speed limit exceeded: {abs(speed):.1f} km/h (limit {speed_limit} km/h in {drive_mode} mode)", "WARN")

    # Alerts
    # BUG 1 Fixed by team 1,3,5 - Gear-aware RPM warning instead of flat 6200 threshold
    gear_redline = {-1: 4500, 1: 6800, 2: 6500, 3: 6200, 4: 6000, 5: 5800, 6: 5500}
    redline_threshold = gear_redline.get(gear, 6200)
    if rpm > redline_threshold:
        log_ecu(f"High RPM in gear {get_gear_label()} - shift up recommended ({rpm:.0f} rpm)", "WARN")

    if engine_temp > 110:
        log_ecu("High engine temperature", "WARN")

    if fuel_level < 15:
        log_ecu("Low fuel level", "WARN")

    if battery_voltage < 11.8:
        log_ecu("Low battery voltage", "WARN")

    if crash_sensor_triggered:
        log_ecu("Crash sensor triggered - airbag event possible", "FAULT")


def update_graphs():
    speed_history.append(abs(speed))
    rpm_history.append(rpm / 40)
    temp_history.append(engine_temp)
    fuel_history.append(fuel_level)
    oil_history.append(oil_level)
    battery_history.append(battery_soc)


def draw_graph(history, x, y, w, h, label, max_value, color):
    draw_box(x, y, w, h, label)

    if len(history) < 2:
        return

    points = []
    data = list(history)

    for i, value in enumerate(data):
        px = x + 5 + i * ((w - 10) / max(1, len(data) - 1))
        py = y + h - 8 - clamp(value / max_value, 0, 1) * (h - 38)
        points.append((px, py))

    if len(points) >= 2:
        pygame.draw.lines(screen, color, False, points, 2)

    latest = data[-1]
    draw_text(f"{latest:.1f}", x + w - 60, y + 5, WHITE, small_font)


def draw_dashboard():
    draw_box(810, 10, 570, 215, "ECU DASHBOARD")

    engine_color = GREEN if engine_on else RED
    mode_color = CYAN if drive_mode == "CITY" else ORANGE

    draw_text(f"ENGINE       : {'ON' if engine_on else 'OFF'}", 825, 45, engine_color)
    draw_text(f"DRIVE MODE   : {drive_mode}", 825, 70, mode_color)
    draw_text(f"GEAR         : {get_gear_label()}", 825, 95)
    draw_text(f"SPEED / VSS  : {abs(speed):.1f} km/h", 825, 120)
    draw_text(f"DIRECTION    : {get_drive_direction_label()}", 825, 145, CYAN if speed < -0.5 else WHITE)
    draw_text(f"RPM          : {rpm:.0f}", 825, 170)
    draw_text(f"DAMAGE       : {damage:.1f} %", 825, 195, RED if damage > 40 else WHITE)
    draw_text(f"OVERTAKES    : {overtake_count}", 1050, 195, GREEN if overtake_count > 0 else WHITE, small_font)

    draw_text(f"ENGINE TEMP  : {engine_temp:.1f} C", 1050, 45, ORANGE if engine_temp > 105 else WHITE)
    draw_text(f"COOLANT TEMP : {coolant_temp:.1f} C", 1050, 70)
    draw_text(f"FUEL LEVEL   : {fuel_level:.1f} %", 1050, 95, RED if fuel_level < 15 else WHITE)
    draw_text(f"OIL LEVEL    : {oil_level:.1f} %", 1050, 120, RED if oil_level < 25 else WHITE)
    draw_text(f"BATTERY      : {battery_voltage:.1f} V", 1050, 145)
    draw_text(f"AC           : {'ON' if ac_on else 'OFF'}", 1050, 170, BLUE if ac_on else WHITE)
    # BUG 7 Fixed by team 1,3,5 - Add distance display and improved distance tracking
    draw_text(f"DISTANCE     : {distance_km:.3f} km", 825, 218, CYAN, small_font)


def draw_sensor_panel():
    draw_box(810, 210, 570, 285, "LIVE SENSOR DATA")

    left_x = 825
    right_x = 1090
    y = 245
    gap = 22

    sensor_lines_left = [
        f"O2 Sensor              : {o2_sensor:.2f} V",
        f"Fuel Flow              : {fuel_flow:.2f} L/hr",
        f"Fuel Pressure          : {fuel_pressure:.1f} psi",
        f"Steering Angle         : {steering_angle_sensor:.1f} deg",
        f"TPMS FL/FR             : {tire_pressure_fl:.1f} / {tire_pressure_fr:.1f} psi",
        f"TPMS RL/RR             : {tire_pressure_rl:.1f} / {tire_pressure_rr:.1f} psi",
        f"Rain Sensor            : {rain_intensity:.0f} %",
        f"Photo Sensor           : {photo_lux:.0f} lux",
        f"Radar Distance         : {radar_distance:.1f} m",
        f"Proximity Sensor       : {proximity_distance:.1f} m",
        f"Blind Spot L/R         : {blind_spot_left} / {blind_spot_right}",
    ]

    sensor_lines_right = [
        f"Gyro X/Y/Z             : {gyro_x:.2f}/{gyro_y:.2f}/{gyro_z:.2f}",
        f"Yaw Rate               : {yaw_rate:.2f}",
        f"Lateral Accel          : {lateral_accel:.2f} g",
        f"MAF                    : {maf:.1f} g/s",
        f"MAP                    : {map_pressure:.1f} kPa",
        f"TPS                    : {tps:.1f} %",
        f"Camshaft Position      : {camshaft_position:.1f} deg",
        f"Brake Fluid Pressure   : {brake_fluid_pressure:.1f} bar",
        f"Lidar Distance         : {lidar_object_distance:.1f} m",
        f"Camera Object          : {camera_object_detected}",
        f"GPS                    : {gps_lat:.5f}, {gps_lon:.5f}",
    ]

    for line in sensor_lines_left:
        color = WHITE
        if "TPMS" in line and min(tire_pressure_fl, tire_pressure_fr, tire_pressure_rl, tire_pressure_rr) < 28:
            color = RED
        draw_text(line, left_x, y, color, small_font)
        y += gap

    y = 245
    for line in sensor_lines_right:
        color = WHITE
        if "Brake Fluid" in line and brake_fluid_pressure > 80:
            color = ORANGE
        draw_text(line, right_x, y, color, small_font)
        y += gap


def draw_status_panel():
    """Top-left vehicle status and controls panel.

    This version avoids the earlier overlap by using a fixed 3-column grid
    for body status and a separate two-line control legend at the bottom.
    """
    draw_box(20, 10, 770, 135, "CONTROLS / VEHICLE BODY STATUS")

    status_items = [
        ("Driver Door", "OPEN" if driver_door_open else "CLOSED", RED if driver_door_open else GREEN),
        ("Passenger Door", "OPEN" if passenger_door_open else "CLOSED", RED if passenger_door_open else GREEN),
        ("Seatbelt", "ON" if seatbelt_on else "OFF", GREEN if seatbelt_on else ORANGE),
        ("Headlights", "ON" if headlights_on else "OFF", GREEN if headlights_on else WHITE),
        ("Left Ind", "ON" if left_indicator else "OFF", YELLOW if left_indicator else WHITE),
        ("Right Ind", "ON" if right_indicator else "OFF", YELLOW if right_indicator else WHITE),
        ("Hazard", "ON" if hazard_on else "OFF", RED if hazard_on else WHITE),
        ("Rain", "ON" if rain_on else "OFF", CYAN if rain_on else WHITE),
        ("Parking", "ON" if parking_sensor_on else "OFF", GREEN if parking_sensor_on else WHITE),
    ]

    col_x = [35, 285, 535]
    row_y = [45, 70, 95]

    for index, (label, value, color) in enumerate(status_items):
        x = col_x[index % 3]
        y = row_y[index // 3]
        draw_text(f"{label:<15}: {value}", x, y, color, small_font)

    # Separate control legend area. Keeping this away from status rows
    # makes the top UI readable even on 1366/1400 px wide displays.
    pygame.draw.rect(screen, BLACK, (30, 116, 750, 20))
    draw_text("S Start/Stop | A/Z Gear: R-N-1-6 | M City/Track | C AC | D/P Doors | B Belt",
              38, 118, WHITE, small_font)
    draw_text("H Lights | Q/E Indicators | X Hazard | R Rain | L Parking | SPACE Reset",
              420, 118, WHITE, small_font)


def draw_infotainment_console():
    # Moved down so it does not fight with the top status panel.
    draw_box(20, 155, 220, 250, "INFOTAINMENT CONSOLE")

    y = 190

    engine_status = "Running" if engine_on else "Stopped"
    ac_status = "ON" if ac_on else "OFF"
    mode_status = drive_mode
    belt_status = "Fastened" if seatbelt_on else "Not Fastened"
    gear_status = get_gear_label()

    if driver_door_open or passenger_door_open:
        safety_message = "DOOR OPEN - DRIVE LOCKED"
        safety_color = RED
    elif not seatbelt_on and abs(speed) > 10:
        safety_message = "SEATBELT WARNING"
        safety_color = ORANGE
    elif fuel_level < 15:
        safety_message = "LOW FUEL"
        safety_color = ORANGE
    elif engine_temp > 105:
        safety_message = "ENGINE HOT"
        safety_color = RED
    elif damage > 40:
        safety_message = "DAMAGE WARNING"
        safety_color = ORANGE
    else:
        safety_message = "SYSTEM NORMAL"
        safety_color = GREEN

    draw_text(f"Engine   : {engine_status}", 35, y, GREEN if engine_on else RED, small_font)
    y += 24
    draw_text(f"Mode     : {mode_status}", 35, y, CYAN if drive_mode == "CITY" else ORANGE, small_font)
    y += 24
    draw_text(f"Gear     : {gear_status}", 35, y, YELLOW if gear == 0 else CYAN if gear == -1 else WHITE, small_font)
    y += 24
    draw_text(f"AC       : {ac_status}", 35, y, BLUE if ac_on else WHITE, small_font)
    y += 24
    draw_text(f"Seatbelt : {belt_status}", 35, y, GREEN if seatbelt_on else ORANGE, small_font)
    y += 24
    draw_text(f"Fuel     : {fuel_level:.1f} %", 35, y, RED if fuel_level < 15 else WHITE, small_font)
    y += 24
    draw_text(f"Temp     : {engine_temp:.1f} C", 35, y, RED if engine_temp > 105 else WHITE, small_font)
    y += 35

    pygame.draw.rect(screen, BLACK, (35, y, 190, 55))
    pygame.draw.rect(screen, safety_color, (35, y, 190, 55), 2)

    draw_text("SAFETY STATUS", 55, y + 8, safety_color, small_font)
    draw_text(safety_message, 45, y + 30, safety_color, small_font)


def draw_ecu_logs():
    draw_box(810, 505, 570, 330, "LIVE ECU LOGS WITH TIME STAMPS")

    y = 540
    for log in list(ecu_logs):
        color = WHITE
        if "[WARN]" in log:
            color = YELLOW
        if "[FAULT]" in log:
            color = RED
        if "[INFO]" in log:
            color = CYAN

        draw_text(log, 825, y, color, small_font)
        y += 17


def draw_graph_panel():

    graph_h = 60

    top_row_y = HEIGHT - 190
    bottom_row_y = HEIGHT - 105

    draw_graph(speed_history,   20,  top_row_y,    250, graph_h, "Speed / VSS",    230, GREEN)
    draw_graph(rpm_history,    290,  top_row_y,    250, graph_h, "RPM Scaled",     190, YELLOW)
    draw_graph(oil_history,    560,  top_row_y,    220, graph_h, "Oil Level",      100, BLUE)

    draw_graph(temp_history,    20,  bottom_row_y, 250, graph_h, "Engine Temp",    130, ORANGE)
    draw_graph(fuel_history,   290,  bottom_row_y, 250, graph_h, "Fuel Level",     100, CYAN)
    draw_graph(battery_history,560,  bottom_row_y, 220, graph_h, "Battery SOC",    100, PURPLE)

def draw_speedometer():
    # Smaller and moved down to avoid overlap with the infotainment console.
    center_x, center_y = 95, 590
    radius = 60

    pygame.draw.circle(screen, BLACK, (center_x, center_y), radius + 5)
    pygame.draw.circle(screen, DARK_GRAY, (center_x, center_y), radius)

    draw_text("SPEED", center_x - 30, center_y - 28, WHITE, small_font)
    draw_text(f"{abs(speed):.0f}", center_x - 22, center_y - 5, GREEN, big_font)
    draw_text("km/h", center_x - 22, center_y + 35, WHITE, small_font)
    if speed < -0.5:
        draw_text("REV", center_x - 15, center_y + 52, CYAN, small_font)

    needle_angle = -130 + (abs(speed) / 230) * 260
    angle_rad = math.radians(needle_angle)

    nx = center_x + math.cos(angle_rad) * 48
    ny = center_y + math.sin(angle_rad) * 48

    pygame.draw.line(screen, RED, (center_x, center_y), (nx, ny), 3)


def draw_rpm_meter():
    # Smaller and separated from the speedometer.
    center_x, center_y = 220, 590
    radius = 60

    pygame.draw.circle(screen, BLACK, (center_x, center_y), radius + 5)
    pygame.draw.circle(screen, DARK_GRAY, (center_x, center_y), radius)

    draw_text("RPM", center_x - 20, center_y - 28, WHITE, small_font)
    draw_text(f"{rpm:.0f}", center_x - 36, center_y - 5, YELLOW, big_font)

    needle_angle = -130 + (rpm / 7600) * 260
    angle_rad = math.radians(needle_angle)

    nx = center_x + math.cos(angle_rad) * 48
    ny = center_y + math.sin(angle_rad) * 48

    pygame.draw.line(screen, YELLOW, (center_x, center_y), (nx, ny), 3)


def reset_faults():
    global damage, crash_sensor_triggered, knock_event
    global fuel_pressure, oil_level, engine_temp, coolant_temp
    global tire_pressure_fl, tire_pressure_fr, tire_pressure_rl, tire_pressure_rr

    damage = 0
    crash_sensor_triggered = False
    knock_event = False
    fuel_pressure = 45
    oil_level = 100
    tire_pressure_fl = 34
    tire_pressure_fr = 34
    tire_pressure_rl = 34
    tire_pressure_rr = 34
    global engine_temp, coolant_temp
    engine_temp = 85.0
    coolant_temp = 82.0
    log_ecu("Faults and damage reset - temperature normalised", "INFO")


def handle_keydown(event):
    global engine_on, gear, drive_mode
    global ac_on, driver_door_open, passenger_door_open, seatbelt_on
    global headlights_on, left_indicator, right_indicator, hazard_on
    global rain_on, parking_sensor_on, knock_event
    global oil_level, fuel_pressure
    global tire_pressure_fl, tire_pressure_fr, tire_pressure_rl, tire_pressure_rr
    global speed, rpm

    if event.key == pygame.K_ESCAPE:
        return False

    if event.key == pygame.K_s:
        engine_on = not engine_on
        if engine_on:
            rpm = 850
            log_ecu("Engine started", "INFO")
        else:
            log_ecu("Engine stopped", "INFO")

    elif event.key == pygame.K_a:
        if gear < max_gear:
            # Block shifting from Reverse/Neutral into forward gear while rolling backward.
            if gear == 0 and speed < -2:
                log_ecu("Shift to forward gear blocked while reversing", "WARN")
            else:
                gear += 1
                log_ecu(f"Gear shifted up to {get_gear_label()}", "INFO")

    elif event.key == pygame.K_z:
        if gear > min_gear:
            # Block shifting into Reverse while moving forward.
            if gear == 0 and speed > 2:
                log_ecu("Shift to Reverse blocked while moving forward", "WARN")
            # BUG 5 Fixed by team 1,3,5 - Block unsafe downshift at excessive speed
            elif gear > 1 and speed > gear_speed_limit.get(gear - 1, 0):
                log_ecu(
                    f"Unsafe downshift to gear {gear - 1} blocked - speed {speed:.1f} exceeds limit {gear_speed_limit.get(gear - 1, 0)} km/h",
                    "WARN"
                )
            else:
                gear -= 1
                log_ecu(f"Gear shifted down to {get_gear_label()}", "INFO")

    elif event.key == pygame.K_m:
        drive_mode = "TRACK" if drive_mode == "CITY" else "CITY"
        log_ecu(f"Drive mode changed to {drive_mode}", "INFO")

    elif event.key == pygame.K_c:
        ac_on = not ac_on
        log_ecu(f"AC {'ON' if ac_on else 'OFF'}", "INFO")

    elif event.key == pygame.K_d:
        driver_door_open = not driver_door_open
        log_ecu(f"Driver door {'OPEN' if driver_door_open else 'CLOSED'}", "INFO")

    elif event.key == pygame.K_p:
        passenger_door_open = not passenger_door_open
        log_ecu(f"Passenger door {'OPEN' if passenger_door_open else 'CLOSED'}", "INFO")

    elif event.key == pygame.K_b:
        seatbelt_on = not seatbelt_on
        log_ecu(f"Seatbelt {'ON' if seatbelt_on else 'OFF'}", "INFO")

    elif event.key == pygame.K_h:
        headlights_on = not headlights_on
        log_ecu(f"Headlights {'ON' if headlights_on else 'OFF'}", "INFO")

    elif event.key == pygame.K_q:
        left_indicator = not left_indicator
        if left_indicator:
            right_indicator = False
        log_ecu(f"Left indicator {'ON' if left_indicator else 'OFF'}", "INFO")

    elif event.key == pygame.K_e:
        right_indicator = not right_indicator
        if right_indicator:
            left_indicator = False
        log_ecu(f"Right indicator {'ON' if right_indicator else 'OFF'}", "INFO")

    elif event.key == pygame.K_x:
        hazard_on = not hazard_on
        log_ecu(f"Hazard lights {'ON' if hazard_on else 'OFF'}", "INFO")

    elif event.key == pygame.K_r:
        rain_on = not rain_on
        log_ecu(f"Rain condition {'ON' if rain_on else 'OFF'}", "INFO")

    elif event.key == pygame.K_l:
        parking_sensor_on = not parking_sensor_on
        log_ecu(f"Parking sensor {'ON' if parking_sensor_on else 'OFF'}", "INFO")

    elif event.key == pygame.K_k:
        knock_event = True
        log_ecu("Manual knock event injected", "FAULT")

    elif event.key == pygame.K_o:
        oil_level = max(5, oil_level - 30)
        log_ecu("Low oil fault injected", "FAULT")

    elif event.key == pygame.K_t:
        tire_pressure_fl -= 7
        tire_pressure_rr -= 5
        log_ecu("TPMS pressure drop fault injected", "FAULT")

    elif event.key == pygame.K_f:
        fuel_pressure = 18
        log_ecu("Fuel pressure fault injected", "FAULT")

    elif event.key == pygame.K_SPACE:
        reset_faults()

    return True


def update_indicator_blink():
    global indicator_timer, indicator_visible

    indicator_timer += 1
    if indicator_timer > 25:
        indicator_timer = 0
        indicator_visible = not indicator_visible



def draw_distance_meter():
    """BUG 11 Fixed by team 1,3,5 - Prominent distance covered meter on-screen.
    Shows total km driven. Turns orange above 1 km, green always visible."""
    x, y, w, h = 350, 145, 190, 38
    pygame.draw.rect(screen, DARK, (x, y, w, h))
    pygame.draw.rect(screen, CYAN, (x, y, w, h), 2)
    label = "DIST COVERED"
    val   = f"{distance_km:.3f} km"
    draw_text(label, x + 8,  y + 4,  CYAN, small_font)
    draw_text(val,   x + 8,  y + 20, GREEN if distance_km < 1.0 else ORANGE, font)


def draw_temp_meter():
    """BUG 11 Fixed by team 1,3,5 - Visual temperature bar.
    Green 70-95, orange 95-110, red 110-130. Flashes red near shutdown."""
    x, y, w, h = 560, 145, 210, 38
    pygame.draw.rect(screen, DARK, (x, y, w, h))
    pygame.draw.rect(screen, LIGHT_GRAY, (x, y, w, h), 1)
    draw_text("ENGINE TEMP", x + 6, y + 4, WHITE, small_font)

    bar_w = int((engine_temp - 70) / (130 - 70) * (w - 16))
    bar_w = max(0, min(bar_w, w - 16))

    if engine_temp < 95:
        bar_color = GREEN
    elif engine_temp < 110:
        bar_color = ORANGE
    else:
        bar_color = RED

    pygame.draw.rect(screen, bar_color, (x + 8, y + 22, bar_w, 10))
    draw_text(f"{engine_temp:.1f} C", x + w - 65, y + 18, bar_color, small_font)
    if engine_temp >= 125:
        draw_text("OVERHEAT!", x + 8, y + 20, RED, small_font)

def main():
    running = True

    log_ecu("ECU simulation initialized", "INFO")
    log_ecu("Press S to start engine", "INFO")

    while running:
        clock.tick(FPS)

        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                running = handle_keydown(event)

        update_indicator_blink()
        update_vehicle(keys)
        update_traffic_and_overtake()
        update_graphs()

        draw_road()
        draw_status_panel()
        draw_infotainment_console()
        draw_traffic()
        draw_car()
        draw_rain_effect()
        draw_speedometer()
        draw_rpm_meter()
        draw_distance_meter()
        draw_temp_meter()
        draw_graph_panel()
        draw_dashboard()
        draw_sensor_panel()
        draw_ecu_logs()

        pygame.display.update()

    pygame.quit()


if __name__ == "__main__":
    main()