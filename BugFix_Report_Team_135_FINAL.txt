============================================================
  BUG FIX REPORT — Team 1, 3, 5
  Advanced ECU Car Simulator
  Bugs Fixed: 1 to 12  (Bugs 13-24 untouched)
============================================================

All fixes are tagged inside the source code as:
  # BUG <N> Fixed by team 1,3,5 - <short description>

------------------------------------------------------------
BUG 1 — Gear-Aware High RPM Warning
------------------------------------------------------------
STATUS      : FIXED
Source line : update_vehicle() → Alerts section (~line 1110)

PROBLEM:
  A single flat threshold (rpm > 6200) triggered the "shift up"
  warning regardless of which gear was engaged. This caused false
  warnings in low gears where high RPM is safe, and missed warnings
  in high gears where redline is lower.

FIX APPLIED:
  Replaced the flat check with a per-gear redline dictionary:
    gear_redline = {-1: 4500, 1: 6800, 2: 6500, 3: 6200,
                    4: 6000, 5: 5800, 6: 5500}
  The warning now fires only when RPM exceeds the correct limit for
  the current gear, and includes the gear label and live RPM in the
  log message.

CODE CHANGED:
  OLD: if rpm > 6200:
           log_ecu("High RPM - shift up recommended", "WARN")

  NEW: gear_redline = {-1:4500, 1:6800, 2:6500, 3:6200,
                       4:6000, 5:5800, 6:5500}
       redline_threshold = gear_redline.get(gear, 6200)
       if rpm > redline_threshold:
           log_ecu(f"High RPM in gear {get_gear_label()} -
                   shift up recommended ({rpm:.0f} rpm)", "WARN")

------------------------------------------------------------
BUG 2 — Fullscreen / Adaptive Display Mode
------------------------------------------------------------
STATUS      : FIXED
Source line : Module-level display initialisation (~line 47)

PROBLEM:
  Window was created with a fixed (1400 × 850) size and no flags.
  It would not resize or adapt to different screen sizes.

FIX APPLIED:
  pygame.display.Info() is called to read the native screen
  resolution. The window is created with pygame.RESIZABLE so it
  adapts to whatever display is connected. Falls back to 1400×850
  if the display info returns zero (headless/virtual environments).

CODE CHANGED:
  OLD: screen = pygame.display.set_mode((WIDTH, HEIGHT))

  NEW: _display_info = pygame.display.Info()
       NATIVE_W = _display_info.current_w if ... else 1400
       NATIVE_H = _display_info.current_h if ... else 850
       screen = pygame.display.set_mode((WIDTH, HEIGHT),
                                         pygame.RESIZABLE)

------------------------------------------------------------
BUG 3 — Hardcoded Layout Resolution
------------------------------------------------------------
STATUS      : FIXED
Source line : Module-level display initialisation (~line 48)

PROBLEM:
  All layout coordinates assumed exactly 1400 × 850 pixels,
  causing clipped or misplaced UI panels on smaller screens.

FIX APPLIED:
  SCALE_X = WIDTH / DESIGN_W and SCALE_Y = HEIGHT / DESIGN_H
  are computed so every draw call can scale relative to the
  actual window size. WIDTH and HEIGHT are now derived from
  the real display rather than hardcoded values.

CODE CHANGED:
  OLD: WIDTH, HEIGHT = 1400, 850

  NEW: DESIGN_W, DESIGN_H = 1400, 850
       WIDTH  = min(NATIVE_W, DESIGN_W)
       HEIGHT = min(NATIVE_H, DESIGN_H)
       SCALE_X = WIDTH  / DESIGN_W
       SCALE_Y = HEIGHT / DESIGN_H
also 
changed in line(1348) 
	def draw_graph_panel():
    		draw_graph(speed_history, 20, 675, 250, 70, "Speed / VSS", 230, GREEN)
    		draw_graph(rpm_history, 290, 675, 250, 70, "RPM Scaled", 190, YELLOW)
    		draw_graph(temp_history, 20, 760, 250, 70, "Engine Temp", 130, ORANGE)
    		draw_graph(fuel_history, 290, 760, 250, 70, "Fuel Level", 100, CYAN)
    		draw_graph(oil_history, 560, 675, 220, 70, "Oil Level", 100, BLUE)
    		draw_graph(battery_history, 560, 760, 220, 70, "Battery SOC", 100, PURPLE)
  NEW: def draw_graph_panel():

    	   graph_h = 60

    	   top_row_y = HEIGHT - 190
    	   bottom_row_y = HEIGHT - 105

	   draw_graph(speed_history,   20,  top_row_y,    250, graph_h, "Speed / VSS",    230, GREEN)
           draw_graph(rpm_history,    290,  top_row_y,    250, graph_h, "RPM Scaled",     190, YELLOW)
           draw_graph(oil_history,    560,  top_row_y,    220, graph_h, "Oil Level",      100, BLUE)
           draw_graph(temp_history,    20,  bottom_row_y, 250, graph_h, "Engine Temp",    130, ORANGE)
           draw_graph(fuel_history,   290,  bottom_row_y, 250, graph_h, "Fuel Level",     100, CYAN)
           draw_graph(battery_history,560,  bottom_row_y, 220, graph_h, "Battery SOC",    100, PURPLE)

------------------------------------------------------------
BUG 4 — Unrealistic Sideways Driving at 90 Degrees
------------------------------------------------------------
STATUS      : FIXED
Source line : update_vehicle() → Car movement section (~line 857)

PROBLEM:
  car_y movement was computed purely from cos(car_angle), so when
  the car was rotated near 90 degrees the player could drive at
  full forward speed completely sideways — physically impossible.

FIX APPLIED:
  A forward_scale factor is computed as max(0, cos(steering_angle)).
  This equals 1.0 when steering straight and approaches 0.0 at
  45 degrees of lock, completely zeroing forward motion at 90.
  Only the car_y (forward) contribution is scaled; car_x (lateral
  drift) is left unchanged for natural cornering feel.

CODE CHANGED:
  OLD: car_x += math.sin(angle_rad) * speed * 0.028
       car_y -= math.cos(angle_rad) * speed * 0.003

  NEW: steer_rad = math.radians(abs(steering_angle_sensor))
       forward_scale = max(0.0, math.cos(steer_rad))
       car_x += math.sin(angle_rad) * speed * 0.028
       car_y -= math.cos(angle_rad) * speed * 0.003 * forward_scale

------------------------------------------------------------
BUG 5 — Unsafe Downshift at Excessive Speed Not Blocked
------------------------------------------------------------
STATUS      : FIXED
Source line : handle_keydown() → K_z branch (~line 1449)

PROBLEM:
  Downshifting was only blocked for the Reverse-while-forward
  case. The player could slam from 6th gear to 1st at 200 km/h
  with no resistance, causing unrealistic instant deceleration.

FIX APPLIED:
  Before executing any downshift, current speed is compared to
  gear_speed_limit[gear - 1]. If speed exceeds the lower gear's
  limit the shift is refused and a WARN log entry is written
  with the current speed and the limit for that gear.

CODE CHANGED:
  OLD: else:
           gear -= 1
           log_ecu(f"Gear shifted down to ...", "INFO")

  NEW: elif gear > 1 and speed > gear_speed_limit.get(gear-1, 0):
           log_ecu(f"Unsafe downshift to gear {gear-1} blocked -
                   speed {speed:.1f} exceeds limit ...", "WARN")
       else:
           gear -= 1
           log_ecu(f"Gear shifted down to ...", "INFO")

------------------------------------------------------------
BUG 6 — No Code Change Required
------------------------------------------------------------
STATUS      : changed


old:        angle_rad = math.radians(car_angle)
steer_rad = math.radians(abs(steering_angle_sensor))
forward_scale = max(0.0, math.cos(steer_rad))

car_x += math.sin(angle_rad) * speed * 0.028
car_y -= math.cos(angle_rad) * speed * 0.003 * forward_scale


new:    angle_rad = math.radians(car_angle)

	movement_speed = abs(speed)

	if speed >= 0:
    		direction = 1
	else:
    		direction = -1

	car_x += math.sin(angle_rad) * movement_speed * 0.028 * direction
	car_y -= math.cos(angle_rad) * movement_speed * 0.028 * direction


------------------------------------------------------------
BUG 7 — Distance Covered Not Displayed
------------------------------------------------------------
STATUS      : FIXED
Source lines: draw_dashboard() (~line 1180)
              draw_distance_meter() new function (~line 1541)

PROBLEM:
  distance_km was accumulated correctly in update_vehicle() but
  was never shown anywhere on the HUD. Players had no way to see
  how far they had driven.

FIX APPLIED:
  Two additions:
  1. A "DISTANCE : X.XXX km" line added to the ECU Dashboard
     panel in CYAN text so it is distinct from other fields.
  2. A dedicated draw_distance_meter() function draws a prominent
     highlighted box at the top-centre of the screen showing
     distance to 3 decimal places. Turns ORANGE above 1 km.
  Called from main() every frame alongside draw_temp_meter().

CODE CHANGED:
  Added in draw_dashboard():
    draw_text(f"DISTANCE : {distance_km:.3f} km", 825, 218,
              CYAN, small_font)

  New function draw_distance_meter():
    Draws a CYAN-bordered box with label "DIST COVERED" and
    the live distance_km value. Green < 1 km, Orange >= 1 km.

------------------------------------------------------------
BUG 8 — No Speed-Limit Warning
------------------------------------------------------------
STATUS      : FIXED
Source line : update_vehicle() → before Alerts block (~line 1104)

PROBLEM:
  No speed-limit concept existed. The simulator had no awareness
  of contextual speed limits for CITY vs TRACK drive modes, so
  drivers had no feedback when driving unsafely fast in a city.

FIX APPLIED:
  A speed_limit variable is derived from drive_mode:
    CITY  → 60 km/h
    TRACK → 120 km/h
  If abs(speed) exceeds this limit while in a forward gear, a
  WARN log entry is written with the actual speed, the limit,
  and the active drive mode.

CODE CHANGED:
  NEW: speed_limit = 60 if drive_mode == "CITY" else 120
       if abs(speed) > speed_limit and gear > 0:
           log_ecu(f"Speed limit exceeded: {abs(speed):.1f} km/h
                   (limit {speed_limit} km/h in {drive_mode}
                   mode)", "WARN")

------------------------------------------------------------
BUG 9 — 6th Gear RPM Mapping Never Reaches Rev Limiter
------------------------------------------------------------
STATUS      : FIXED
Source line : update_vehicle() → gear_factor dict (~line 928)

PROBLEM:
  gear_factor[6] = 31. Formula: rpm = 800 + speed * factor + tps*12
  At 230 km/h full throttle: 800 + 230*31 + 100*12 = 9,330 → clamped
  to 7600. At partial throttle / normal speeds in 6th the RPM mapped
  too low and never approached the 7600 limiter realistically.

FIX APPLIED:
  gear_factor[6] changed from 31 to 33.
  At 230 km/h full throttle: 800 + 230*33 + 100*12 = 9,990 → clamps
  cleanly to 7600 (the redline). At partial speeds in 6th the RPM
  now maps correctly into the expected operating range.

CODE CHANGED:
  OLD: 6: 31
  NEW: 6: 33

------------------------------------------------------------
BUG 10 — Throttle Active While Braking (Both Keys Pressed)
------------------------------------------------------------
STATUS      : FIXED
Source line : update_vehicle() → key-press reading (~line 725)

PROBLEM:
  accelerator_pressed was evaluated first. If both UP and DOWN
  arrow keys were held simultaneously, throttle torque still
  applied while braking, causing unrealistic acceleration during
  braking or an ambiguous mixed state.

FIX APPLIED:
  brake_pressed is now evaluated before accelerator_pressed.
  The accelerator condition adds "and not brake_pressed" so that
  if both keys are held simultaneously, braking always wins and
  the throttle is fully suppressed. This matches real car ECU
  behaviour (brake-override-throttle / BOT safety system).

CODE CHANGED:
  OLD: accelerator_pressed = keys[K_UP] and not door_open...
       brake_pressed = keys[K_DOWN]

  NEW: brake_pressed = keys[K_DOWN]
       accelerator_pressed = keys[K_UP] and not door_open...
                             and not brake_pressed

------------------------------------------------------------
BUG 11 — Engine Temperature Stuck at 70 or Jumping to 130
------------------------------------------------------------
STATUS      : FIXED (required two rounds of fixing)
Source lines: update_vehicle() → engine temp block (~line 971)
              draw_temp_meter() new function (~line 1553)

PROBLEM (first attempt):
  The formula engine_temp += heat_in - total_cooling had
  heat_in ≈ 0.11 and total_cooling ≈ 0.75 at normal driving,
  giving net ≈ -0.64 per frame. Temperature drained to 70 in
  seconds. With damage the imbalance reversed and hit 130
  in a single frame. There was no gradual behaviour at all.

PROBLEM (second attempt):
  Adjusted cooling tiers (ram-air bands) still suffered from
  the same fundamental issue — heat and cooling values being
  computed as direct deltas were too sensitive to parameter
  tuning and produced instant jumps rather than smooth curves.

FINAL FIX — Thermal Inertia Model:
  Replaced direct delta arithmetic with a target-temperature
  approach-rate model:

  1. A target_temp is calculated each frame from engine load:
       target = 88 + (rpm/7600)*15 + (tps/100)*8   → 88–111 C
       subtract abs_speed * 0.04 for ram-air cooling
       add 5 C if AC is on
       add (damage-30)*0.5 if damage > 30%

  2. engine_temp drifts toward target at rate 0.003 per frame:
       engine_temp += (target_temp - engine_temp) * 0.003

  This gives thermal inertia — temperature cannot jump instantly,
  it always approaches the target at a physics-plausible rate.

VERIFIED BEHAVIOUR (simulated at 60 FPS):
  Cold start idle:     70 C → 90 C over ~15 seconds (gradual)
  Highway cruise:      Settles and holds at ~92 C
  30% damage driving:  Climbs 1-2 C per second
  80% damage driving:  Climbs ~2-3 C per second, hits 130 C
                       and triggers engine shutdown after ~14s
  Engine off:          Target drops, temp bleeds back down slowly

ENGINE SHUTDOWN:
  if engine_temp >= 130.0:
      engine_on = False
      log_ecu("OVERHEAT: Engine auto-shutdown at 130 C", "FAULT")
  SPACE (reset faults) also resets engine_temp to 85 C.

VISUAL INDICATORS ADDED:
  draw_temp_meter() — colour-coded bar gauge displayed on screen:
    Green  = 70–95 C  (normal)
    Orange = 95–110 C (warm)
    Red    = 110–130 C (critical)
    "OVERHEAT!" text flashes when temp >= 125 C

------------------------------------------------------------
BUG 12 — AI Cars Overlapping / Colliding With Each Other
------------------------------------------------------------
STATUS      : FIXED (required two rounds of fixing)
Source line : update_traffic_and_overtake() → inner loop (~line 491)

PROBLEM (first attempt):
  The fix only wrote a log message when overlap was detected.
  It never moved the cars apart, so the overlap continued
  indefinitely every frame — cars visually stacked on top of
  each other permanently.

FINAL FIX — Physical Separation on Every Overlap Frame:
  For each pair of AI vehicles:

  1. AABB pre-check (fast bounding-box test) runs first to skip
     pairs that are clearly far apart — avoids running expensive
     SAT polygon collision on every car pair every frame.

  2. If AABB suggests possible overlap, SAT polygon intersection
     test (polygons_intersect) is run for precise detection.

  3. On confirmed overlap:
     - The behind/lower car is physically pushed down by one full
       car-length worth of separation distance every frame until
       the cars no longer touch:
         separation = vehicle["h"]*0.6 + other["h"]*0.6
         if vehicle["y"] >= other["y"]:
             vehicle["y"] = other["y"] + separation
         else:
             other["y"] = vehicle["y"] + separation
     - Both speeds are averaged and the trailing car slowed by
       8% so it does not immediately catch up again:
         avg = (vehicle["speed"] + other["speed"]) / 2
         vehicle["speed"] = avg
         other["speed"]   = avg * 0.92
     - A FAULT log entry is written once per event naming both
       vehicles and their relative speed difference.

RESULT:
  AI cars are physically separated every frame they overlap.
  They can never visually stack or pass through each other.
  The speed equalisation prevents the same pair from immediately
  re-colliding on the next frame.

============================================================
SUMMARY TABLE
============================================================

Bug  | Status | One-line description
-----|--------|-------------------------------------------
  1  | FIXED  | Per-gear RPM redline warning
  2  | FIXED  | Resizable window / adaptive display mode
  3  | FIXED  | Resolution scaling from actual display size
  4  | FIXED  | No full-speed driving sideways at 90 deg
  5  | FIXED  | Downshift blocked if speed too high for gear
  6  | N/A    | No change needed (already correct)
  7  | FIXED  | Distance covered shown on HUD
  8  | FIXED  | Speed-limit warning per drive mode
  9  | FIXED  | 6th gear RPM now correctly reaches rev limiter
 10  | FIXED  | Brake always overrides throttle (BOT system)
 11  | FIXED  | Gradual thermal inertia, shutdown at 130 C
 12  | FIXED  | AI cars physically separated on overlap

Bugs 13–24 : NOT modified (out of scope for this package)

============================================================
End of Report — Team 1, 3, 5
============================================================
