from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

#window
window_width, window_height = 1000, 800
GRID_LENGTH = 600
camera_y_offset = 800
camera_x_angle = 0
fovY = 120
current_level = 1

#player
player_x, player_y = -460, -460
player_size = 20
move_speed = 3.5
crouch_speed = 1.0
walk_angle = 0
is_moving = False
is_crouching = False
player_rotation = 0
target_rotation = 0
player_bullet_hits = 0
is_player_dead = False
bullets_remaining = 3

# Global movement
move_dx, move_dy = 0, 0
current_key = None
frame_counter = 0

#Knife attack
knife_swing_angle = 0
is_knife_swinging = False
knife_swing_speed = 5

# Diamond for level 2
diamond_spawned = False
diamond_collected = False
diamond_x = 0
diamond_y = 0
diamond_float_angle = 0


class BulletPickup:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.z = 60  # Float above ground
        self.float_angle = 0
        self.active = True
        self.pickup_range = 40
        
    def update(self):
        # Float animation
        self.float_angle += 3
        if self.float_angle >= 360:
            self.float_angle = 0
        
        # Check if player is close enough to pick up
        distance = ((self.x - player_x)**2 + (self.y - player_y)**2) ** 0.5
        if distance <= self.pickup_range:
            self.collect()
    
    def collect(self):
        global bullets_remaining
        if self.active:
            bullets_remaining += 1
            self.active = False
    
    def draw(self):
        if not self.active:
            return
            
        glPushMatrix()
        # Apply floating motion
        float_offset = self.float_angle * 3.14159 / 180.0
        import math
        float_y = math.sin(float_offset) * 5
        
        glTranslatef(self.x, self.y, self.z + float_y)
        glColor3f(1, 1, 1)  # White color
        
        # Draw sphere using gluSphere
        quadric = gluNewQuadric()
        gluSphere(quadric, 8, 16, 16)
        
        glPopMatrix()


class Bullet:
    def __init__(self, x, y, direction_angle, speed=8):
        self.x = x
        self.y = y
        self.speed = speed
        import math
        angle_rad = math.radians(direction_angle)
        self.dx = math.cos(angle_rad)*speed
        self.dy = math.sin(angle_rad)*speed
        self.active = True
        

    def update(self):
        if not self.active:
            return
        self.x += self.dx
        self.y += self.dy
        
        #boundary collision
        if (self.x< -GRID_LENGTH-100 or self.x> GRID_LENGTH+100 or 
            self.y< -GRID_LENGTH-100 or self.y> GRID_LENGTH+100):
            self.active = False
            return
            
        #wall collision
        walls = maze_walls_level1 if current_level==1 else maze_walls_level2
        for (x1, y1, x2, y2) in walls:
            if x1 == x2:
                if abs(self.x-x1)< 15 and min(y1, y2)<= self.y<= max(y1, y2):
                    self.active = False
                    return
            if y1 == y2:
                if abs(self.y - y1)< 15 and min(x1, x2)<= self.x<= max(x1, x2):
                    self.active = False
                    return
                    
        #outer boundary(grey wall) collision
        wall_thickness = 40
        half_len = GRID_LENGTH
        gap_size = 120
        
        block2_x, block2_y = get_block_center(2)
        block100_x, block100_y = get_block_center(100)
        
        if abs(self.y-(-half_len))< wall_thickness/2:
            if not (abs(self.x-block2_x)< gap_size/2):
                self.active = False
                return
        if abs(self.y-half_len)< wall_thickness/2:
            if not (abs(self.x-block100_x)< gap_size/2):
                self.active = False
                return
        if abs(self.x-(-half_len))< wall_thickness/2:
            self.active = False
            return
        if abs(self.x-half_len)< wall_thickness/2:
            self.active = False
            return
    
    def draw(self):
        if not self.active:
            return
        glPushMatrix()
        glTranslatef(self.x, self.y, 20)
        glScalef(8, 8, 8)
        glColor3f(1, 1, 0)
        draw_unit_cube()
        glPopMatrix()




class Projectile:       #enemy's
    def __init__(self, x, y, direction_x, direction_y, speed=40.0):
        self.x = x
        self.y = y
        self.direction_x = direction_x
        self.direction_y = direction_y
        self.speed = speed
        self.lifetime = 300

    def update(self):
        global player_bullet_hits, is_player_dead

        self.x += self.direction_x*self.speed
        self.y += self.direction_y*self.speed
        self.lifetime -= 1

        #bounds
        if (self.x< -GRID_LENGTH-100 or self.x> GRID_LENGTH+100 or
            self.y< -GRID_LENGTH-100 or self.y > GRID_LENGTH+100):
            return False

        #wall collisions
        walls = maze_walls_level1 if current_level == 1 else maze_walls_level2
        for (x1, y1, x2, y2) in walls:
            if x1 == x2:
                if abs(self.x-x1)< 10 and min(y1, y2)<= self.y<= max(y1, y2):
                    return False
            if y1 == y2:
                if abs(self.y-y1)< 10 and min(x1, x2)<= self.x<= max(x1, x2):
                    return False

        # player collision
        if not is_player_dead:
            player_hit_radius = 20
            if (abs(self.x-player_x)< player_hit_radius and
                abs(self.y-player_y)< player_hit_radius):
                player_bullet_hits += 1
                if player_bullet_hits>= 30:
                    is_player_dead = True
                return False

        if self.lifetime<= 0:
            return False

        return True

    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, 20)
        glColor3f(1.0, 0.0, 0.0)
        glScalef(3, 3, 3)
        draw_unit_cube()
        glPopMatrix()

# Global lists
bullets = []
projectiles = []
bullet_pickups = []

def get_block_center(block_number):
    grid_size = 120
    row = (block_number-1)//10
    col = (block_number-1)%10
    x = -GRID_LENGTH+ col* grid_size+ grid_size/2
    y = -GRID_LENGTH+ row* grid_size+ grid_size/2
    return x, y


def get_safe_patrol_blocks(center_block):
    grid_size = 120
    row = (center_block-1)//10
    col = (center_block-1)%10
    
    # Get all possible adjacent blocks (only cardinal directions)
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    possible_blocks = []
    
    for dr, dc in directions:
        new_row = row + dr
        new_col = col + dc
        if 0 <= new_row < 10 and 0 <= new_col < 10:
            new_block = new_row * 10 + new_col + 1
            possible_blocks.append(new_block)
    
    # Check which blocks are safe (no wall collision)
    safe_blocks = []
    for block in possible_blocks:
        block_x, block_y = get_block_center(block)
        if is_position_safe_for_patrol(block_x, block_y):
            safe_blocks.append(block)
    
    # Return exactly 3 safe blocks (or less if not available)
    return safe_blocks[:3]


def is_position_safe_for_patrol(x, y):
    margin = 30
    
    # Check boundary
    if x < -GRID_LENGTH + margin or x > GRID_LENGTH - margin:
        return False
    if y < -GRID_LENGTH + margin or y > GRID_LENGTH - margin:
        return False
    
    # Check maze walls for level 2
    for (x1, y1, x2, y2) in maze_walls_level2:
        if x1 == x2 and abs(x - x1) < margin and min(y1, y2) <= y <= max(y1, y2):
            return False
        if y1 == y2 and abs(y - y1) < margin and min(x1, x2) <= x <= max(x1, x2):
            return False
    
    return True


class Enemy:
    def __init__(self, block_number):
        self.block_number = block_number
        self.original_x, self.original_y = get_block_center(block_number)
        self.x, self.y = self.original_x, self.original_y
        self.prev_x, self.prev_y = self.x, self.y
        self.rotation = 0
        self.target_rotation = 0
        self.last_rotation_frame = 0
        self.rotation_hold_frames = 450
        
        #chase&return st
        self.is_chasing = False
        self.is_returning = False
        self.chase_start_frame = 0
        self.chase_duration_frames = 180
        
        #movement&detection
        self.speed = 0.2
        self.return_speed = 0.3
        self.detection_range_standing = 3*120
        self.detection_range_crouching = 1*120
        self.walk_angle = 0
        
        #paths tracking
        self.movement_path = []
        self.path_index = 0
        
        #pathsfinding
        self.stuck_counter = 0
        self.avoid_direction_x = 0
        self.avoid_direction_y = 0
        self.avoid_timer = 0
        
        #death
        self.is_dead = False
        self.death_rotation = 0
        self.death_frame = 0
        self.pickup_spawned = False
        
        #health
        self.health = 3
        self.max_health = 3
        
        #firing
        self.is_firing = False
        self.fire_cooldown = 0
        self.fire_rate = 30
        self.last_player_seen_frame = 0
        
        #bullet-triggered movement
        self.bullet_alerted = False
        self.bullet_source_x = 0
        self.bullet_source_y = 0
        self.bullet_alert_frame = 0
        
        # Patrolling - initialize but don't activate until level 2
        self.is_patrolling = False
        self.patrol_blocks = []
        self.patrol_target_index = 0
        self.patrol_timer = 0
        self.patrol_wait_time = 120
        self.is_returning_to_origin = False
        self.patrol_target_x = 0
        self.patrol_target_y = 0

    def initialize_patrol(self):
        """Initialize patrolling for level 2"""
        if current_level == 2 and not self.is_dead:
            self.is_patrolling = True
            self.patrol_blocks = get_safe_patrol_blocks(self.block_number)
            self.patrol_target_index = 0
            self.patrol_timer = 0
            self.is_returning_to_origin = False
            
            if self.patrol_blocks:
                target_block = self.patrol_blocks[0]
                self.patrol_target_x, self.patrol_target_y = get_block_center(target_block)

    def reset(self):
        self.x, self.y = self.original_x, self.original_y
        self.prev_x, self.prev_y = self.x, self.y
        self.rotation = 0
        self.target_rotation = 0
        self.last_rotation_frame = 0
        
        self.is_chasing = False
        self.is_returning = False
        self.chase_start_frame = 0
        
        self.walk_angle = 0
        self.movement_path = []
        self.path_index = 0
        
        self.stuck_counter = 0
        self.avoid_direction_x = 0
        self.avoid_direction_y = 0
        self.avoid_timer = 0
        
        self.is_dead = False
        self.death_rotation = 0
        self.death_frame = 0
        self.pickup_spawned = False
        
        self.health = 3
        
        self.is_firing = False
        self.fire_cooldown = 0
        self.last_player_seen_frame = 0
        
        self.bullet_alerted = False
        self.bullet_source_x = 0
        self.bullet_source_y = 0
        self.bullet_alert_frame = 0
        
        # Reset patrolling
        self.is_patrolling = False
        self.patrol_blocks = []
        self.patrol_target_index = 0
        self.patrol_timer = 0
        self.is_returning_to_origin = False

    def take_damage(self, bullet_x, bullet_y):
        if self.is_dead:
            return
            
        self.health -= 1
        
        if not self.bullet_alerted:
            self.bullet_alerted = True
            self.bullet_source_x = bullet_x
            self.bullet_source_y = bullet_y
            self.bullet_alert_frame = frame_counter
        
        if self.health<= 0:
            self.kill_enemy()

    def kill_enemy(self):
        global bullet_pickups
        if not self.is_dead:
            self.is_dead = True
            self.death_frame = frame_counter
            self.is_chasing = False
            self.is_returning = False
            self.bullet_alerted = False
            self.is_firing = False
            self.is_patrolling = False
            
            # Spawn bullet pickup
            if not self.pickup_spawned:
                pickup = BulletPickup(self.x, self.y)
                bullet_pickups.append(pickup)
                self.pickup_spawned = True

    def get_facing_direction(self):
        if self.rotation == 0:    
            return (1, 0)
        elif self.rotation == 90: 
            return (0, 1)
        elif self.rotation == 180: 
            return (-1, 0)
        else:                     
            return (0, -1)

    def can_see_player(self, px, py):
        if self.is_dead:
            return False
            
        face_dx, face_dy = self.get_facing_direction()
        to_player_x = px-self.x
        to_player_y = py-self.y
        
        distance_to_player = (to_player_x**2 + to_player_y**2) ** 0.5
        if distance_to_player == 0:
            return False

        norm_to_player_x = to_player_x/distance_to_player
        norm_to_player_y = to_player_y/distance_to_player

        dot_product = face_dx* norm_to_player_x+ face_dy* norm_to_player_y
        
        if dot_product < 0.7:
            return False

        
        if face_dx > 0:
            if to_player_x<= 0:
                return False
            if abs(to_player_y)> abs(to_player_x)* 0.3:
                return False
        elif face_dx< 0:
            if to_player_x>= 0:
                return False
            if abs(to_player_y)> abs(to_player_x)*0.3:
                return False
        elif face_dy> 0:
            if to_player_y<= 0:
                return False
            if abs(to_player_x)> abs(to_player_y)*0.3:
                return False
        elif face_dy< 0:
            if to_player_y>= 0:
                return False
            if abs(to_player_x)> abs(to_player_y)*0.3:
                return False

        return self.check_line_of_sight(px, py)

    def check_line_of_sight(self, px, py):
        dx = px - self.x
        dy = py - self.y
        distance = (dx**2 + dy**2)**0.5
        
        if distance < 10:
            return True
            
        steps = int(distance / 10)
        if steps == 0:
            return True
            
        step_x = dx/steps
        step_y = dy/steps

        walls = maze_walls_level1 if current_level == 1 else maze_walls_level2
        
        for i in range(1, steps):
            check_x = self.x + step_x * i
            check_y = self.y + step_y * i

            for (x1, y1, x2, y2) in walls:
                if x1 == x2:
                    if abs(check_x - x1) < 15 and min(y1, y2) <= check_y <= max(y1, y2):
                        return False
                if y1 == y2:
                    if abs(check_y - y1) < 15 and min(x1, x2) <= check_x <= max(x1, x2):
                        return False

        return True

    def fire_at_player(self, px, py):
        global projectiles, frame_counter
        
        if self.fire_cooldown > 0 or self.is_dead:
            return
            
        dx = px - self.x
        dy = py - self.y
        distance = (dx**2 + dy**2) ** 0.5
        
        if distance > 0:
            norm_dx = dx / distance
            norm_dy = dy / distance
            
            gun_offset_x, gun_offset_y = self.get_gun_position()
            projectile = Projectile(
                self.x + gun_offset_x, 
                self.y + gun_offset_y, 
                norm_dx, 
                norm_dy
            )
            projectiles.append(projectile)
            
            self.fire_cooldown = self.fire_rate
    
    def get_gun_position(self):
        face_dx, face_dy = self.get_facing_direction()
        return face_dx * 15, face_dy * 15

    def try_move_to_target(self, target_x, target_y, speed, record_path=False):
        if self.is_dead:
            return True
            
        to_target_x = target_x - self.x
        to_target_y = target_y - self.y
        distance = (to_target_x**2 + to_target_y**2) ** 0.5
        
        if distance < 15:
            return True
            
        if distance > 0:
            norm_x = to_target_x / distance
            norm_y = to_target_y / distance
        else:
            return True
            
        move_x = norm_x * speed
        move_y = norm_y * speed
        
        new_x = self.x + move_x
        new_y = self.y + move_y
        
        if self.can_move(new_x, new_y):
            if record_path:
                self.movement_path.append((self.x, self.y))
            
            self.x = new_x
            self.y = new_y
            self.stuck_counter = 0
            self.avoid_timer = 0
            return False
            
        # Obstacle avoidance logic
        self.stuck_counter += 1
        
        if self.stuck_counter > 20:
            directions = [(speed, 0), (-speed, 0), (0, speed), (0, -speed)]
            for dx, dy in directions:
                test_x = self.x + dx
                test_y = self.y + dy
                if self.can_move(test_x, test_y):
                    if record_path:
                        self.movement_path.append((self.x, self.y))
                        
                    self.x = test_x
                    self.y = test_y
                    self.stuck_counter = 0
                    return False
                    
        return False

    def retrace_exact_path(self):
        if self.is_dead:
            return
            
        if not self.movement_path:
            reached_home = self.try_move_to_target(self.original_x, self.original_y, self.return_speed, record_path=False)
            if reached_home:
                self.is_returning = False
                self.x = self.original_x
                self.y = self.original_y
                self.stuck_counter = 0
                # Resume patrolling if in level 2
                if current_level == 2:
                    self.initialize_patrol()
            return
            
        if self.path_index < len(self.movement_path):
            target_x, target_y = self.movement_path[-(self.path_index + 1)]
            
            distance_to_target = ((self.x - target_x)**2 + (self.y - target_y)**2) ** 0.5
            
            if distance_to_target < 5:
                self.x, self.y = target_x, target_y
                self.path_index += 1
                
                if self.path_index >= len(self.movement_path):
                    final_distance = ((self.x - self.original_x)**2 + (self.y - self.original_y)**2) ** 0.5
                    if final_distance < 15:
                        self.is_returning = False
                        self.x = self.original_x
                        self.y = self.original_y
                        self.movement_path = []
                        self.path_index = 0
                        self.stuck_counter = 0
                        # Resume patrolling if in level 2
                        if current_level == 2:
                            self.initialize_patrol()
                    else:
                        self.try_move_to_target(self.original_x, self.original_y, self.return_speed, record_path=False)
            else:
                if distance_to_target > 0:
                    norm_x = (target_x - self.x) / distance_to_target
                    norm_y = (target_y - self.y) / distance_to_target
                    
                    new_x = self.x + norm_x * self.return_speed * 0.7
                    new_y = self.y + norm_y * self.return_speed * 0.7
                    
                    if self.can_move(new_x, new_y):
                        self.x = new_x
                        self.y = new_y
                    else:
                        self.path_index += 1

    def patrol_update(self):
        """Handle patrolling behavior for level 2 enemies - 3 blocks only"""
        if not self.is_patrolling or not self.patrol_blocks or self.is_dead:
            return False
        
        # If returning to origin after patrol cycle
        if self.is_returning_to_origin:
            reached_origin = self.try_move_to_target(self.original_x, self.original_y, self.speed * 0.8, record_path=False)
            if reached_origin:
                self.x = self.original_x
                self.y = self.original_y
                self.is_returning_to_origin = False
                self.patrol_target_index = 0
                self.patrol_timer = 0
                # Start patrol cycle again
                if self.patrol_blocks:
                    target_block = self.patrol_blocks[0]
                    self.patrol_target_x, self.patrol_target_y = get_block_center(target_block)
            
            # Update rotation to face movement direction
            to_origin_x = self.original_x - self.x
            to_origin_y = self.original_y - self.y
            if abs(to_origin_x) > abs(to_origin_y):
                self.target_rotation = 0 if to_origin_x > 0 else 180
            else:
                self.target_rotation = 90 if to_origin_y > 0 else 270
            return True
            
        # Get current patrol target
        if self.patrol_target_index >= len(self.patrol_blocks):
            # Completed all patrol blocks, return to origin
            self.is_returning_to_origin = True
            return True
            
        target_block = self.patrol_blocks[self.patrol_target_index]
        target_x, target_y = get_block_center(target_block)
        self.patrol_target_x, self.patrol_target_y = target_x, target_y
        
        # Move towards target
        distance = ((self.x - target_x)**2 + (self.y - target_y)**2) ** 0.5
        
        if distance < 25:
            # Reached patrol point, wait
            self.patrol_timer += 1
            if self.patrol_timer >= self.patrol_wait_time:
                # Move to next patrol point
                self.patrol_target_index += 1
                self.patrol_timer = 0
        else:
            # Move towards patrol target
            self.try_move_to_target(target_x, target_y, self.speed * 0.6, record_path=False)
            
            # Update rotation to face movement direction
            to_target_x = target_x - self.x
            to_target_y = target_y - self.y
            if abs(to_target_x) > abs(to_target_y):
                self.target_rotation = 0 if to_target_x > 0 else 180
            else:
                self.target_rotation = 90 if to_target_y > 0 else 270
                
        return True

    def update(self, px, py, player_crouching):
        global frame_counter, is_player_dead
        
        if self.is_dead:
            death_progress = min((frame_counter - self.death_frame) / 60.0, 1.0)
            self.death_rotation = death_progress * 90
            return

        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        to_player_x = px - self.x
        to_player_y = py - self.y
        distance = (to_player_x**2 + to_player_y**2) ** 0.5
        detection_range = self.detection_range_crouching if player_crouching else self.detection_range_standing
        
        can_see_player_now = distance <= detection_range and self.can_see_player(px, py)

        moved_this_update = False

        # Handle bullet-triggered movement
        if self.bullet_alerted and not self.is_chasing and not self.is_returning:
            self.is_patrolling = False  # Stop patrolling when investigating
            if frame_counter - self.bullet_alert_frame < 180:
                reached_source = self.try_move_to_target(self.bullet_source_x, self.bullet_source_y, self.speed, record_path=True)
                if not reached_source:
                    moved_this_update = True
                    
                to_source_x = self.bullet_source_x - self.x
                to_source_y = self.bullet_source_y - self.y
                if abs(to_source_x) > abs(to_source_y):
                    self.target_rotation = 0 if to_source_x > 0 else 180
                else:
                    self.target_rotation = 90 if to_source_y > 0 else 270
            else:
                self.bullet_alerted = False
                self.is_returning = True
                self.path_index = 0

        elif self.is_returning:
            self.retrace_exact_path()
            moved_this_update = True
            self.is_firing = False
                
            if self.movement_path and self.path_index < len(self.movement_path):
                target_x, target_y = self.movement_path[-(self.path_index + 1)]
                to_target_x = target_x - self.x
                to_target_y = target_y - self.y
            else:
                to_target_x = self.original_x - self.x
                to_target_y = self.original_y - self.y
                
            if abs(to_target_x) > abs(to_target_y):
                self.target_rotation = 0 if to_target_x > 0 else 180
            else:
                self.target_rotation = 90 if to_target_y > 0 else 270

        elif self.is_chasing:
            self.is_patrolling = False  # Stop patrolling when chasing
            if can_see_player_now:
                self.chase_start_frame = frame_counter
                self.chase_duration_frames = 180 + (frame_counter % 120)

            if not can_see_player_now and frame_counter - self.chase_start_frame > self.chase_duration_frames:
                self.is_chasing = False
                self.is_returning = True
                self.path_index = 0
                self.stuck_counter = 0
            else:
                reached_player = self.try_move_to_target(px, py, self.speed, record_path=True)
                
                if not reached_player:
                    moved_this_update = True
                    
                if abs(to_player_x) > abs(to_player_y):
                    self.target_rotation = 0 if to_player_x > 0 else 180
                else:
                    self.target_rotation = 90 if to_player_y > 0 else 270
        else:
            # Normal patrolling or stationary behavior
            if current_level == 2 and not self.is_dead:
                # Handle patrolling for level 2
                patrol_moved = self.patrol_update()
                if patrol_moved:
                    moved_this_update = True
            else:
                # Level 1 behavior - rotate periodically
                if frame_counter - self.last_rotation_frame > self.rotation_hold_frames:
                    rotations = [0, 90, 180, 270]
                    current_index = rotations.index(self.target_rotation) if self.target_rotation in rotations else 0
                    self.target_rotation = rotations[(current_index + 1) % 4]
                    self.last_rotation_frame = frame_counter

            if can_see_player_now:
                self.is_chasing = True
                self.chase_start_frame = frame_counter
                self.chase_duration_frames = 180 + (frame_counter % 120)
                self.movement_path = []
                self.path_index = 0
                self.stuck_counter = 0
                self.is_patrolling = False

        # Firing logic
        if is_player_dead:
            self.is_firing = False
            if self.is_chasing:
                self.is_chasing = False
                self.is_returning = True
                self.path_index = 0
                self.stuck_counter = 0
        else:
            if can_see_player_now:
                self.is_firing = True
                self.last_player_seen_frame = frame_counter
                self.fire_at_player(px, py)
            else:
                if frame_counter - self.last_player_seen_frame > 10:
                    self.is_firing = False

        self.rotation = self.smooth_rotation(self.rotation, self.target_rotation, 3.0)

        if moved_this_update:
            self.walk_angle += 12
        else:
            self.walk_angle += 1.5
        if self.walk_angle >= 360:
            self.walk_angle -= 360

        self.prev_x, self.prev_y = self.x, self.y

    def smooth_rotation(self, current, target, speed):
        if target is None:
            return current

        current = current % 360
        target = target % 360

        diff = target - current
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360

        if abs(diff) < speed:
            return target
        return current + (speed if diff > 0 else -speed)

    def can_move(self, nx, ny):
        margin = 25
        if nx < -GRID_LENGTH + margin or nx > GRID_LENGTH - margin:
            return False
        if ny < -GRID_LENGTH + margin or ny > GRID_LENGTH - margin:
            return False

        walls = maze_walls_level1 if current_level == 1 else maze_walls_level2
        for (x1, y1, x2, y2) in walls:
            if x1 == x2 and abs(nx - x1) < 25 and min(y1, y2) <= ny <= max(y1, y2):
                return False
            if y1 == y2 and abs(ny - y1) < 25 and min(x1, x2) <= nx <= max(x1, x2):
                return False
        return True

# Create enemies for both levels
enemies_level1 = [
    Enemy(35),
    Enemy(50),
    Enemy(65)
]

enemies_level2 = [
    Enemy(30),
    Enemy(37),
    Enemy(74),
    Enemy(44),
    Enemy(69)
]

# Maze definitions
maze_walls_level1 = [(-400, -500, -400, -100), (-400, 100, -400, 500),
                     (-200, -500, -200, -200), (-200, 0, -200, 300), (-200, 500, -200, 500),
                     (0, -500, 0, -300), (0, -100, 0, 100), (0, 300, 0, 500),
                     (200, -500, 200, -200), (200, 100, 200, 400),
                     (400, -400, 400, -100), (400, 200, 400, 500),
                     (-500, -300, -300, -300), (-100, -300, 100, -300), (300, -300, 500, -300),
                     (-500, 0, -300, 0), (-100, 0, 100, 0), (300, 0, 500, 0),
                     (-500, 300, -300, 300), (-100, 300, 100, 300), (300, 300, 500, 300)]

maze_walls_level2 = [
    (-500, -560, -500, -120), (-500, 160, -500, 560),
    (-300, -560, -300, -240), (-300, -40, -300, 240), (-300, 440, -300, 560),
    (-100, -560, -100, -360), (-100, -160, -100, 160), (-100, 360, -100, 560),
    (100, -560, 100, -480), (100, -280, 100, -80), (100, 120, 100, 320), (100, 520, 100, 560),
    (300, -560, 300, -320), (300, -120, 300, 80), (300, 280, 300, 560),
    (500, -560, 500, -400), (500, -200, 500, 0), (500, 200, 500, 560),
    (-160, -400, 40, -400), (240, -400, 560, -400),
    (-560, -200, -460, -200), (-260, -200, 60, -200), (260, -200, 560, -200),
    (-560, 0, -340, 0), (-140, 0, 140, 0), (340, 0, 560, 0),
    (-560, 200, -520, 200), (-320, 200, -120, 200), (80, 200, 300, 200), (500, 200, 560, 200),
    (-560, 400, -200, 400), (0, 400, 200, 400), (400, 400, 560, 400),
    (-300, -600, -300, -240), (-100, -600, -100, -360), (100, -600, 100, -480),
    (300, -600, 300, -320), (500, -600, 500, -400)]

# Helper functions
def get_current_enemies():
    """Get enemies for the current level"""
    return enemies_level1 if current_level == 1 else enemies_level2

def all_enemies_dead():
    """Check if all enemies in current level are dead"""
    current_enemies = get_current_enemies()
    for enemy in current_enemies:
        if not enemy.is_dead:
            return False
    return True

def spawn_diamond():
    """Spawn diamond at random location in level 2"""
    global diamond_spawned, diamond_x, diamond_y
    if not diamond_spawned and current_level == 2:
        import random
        # Generate random position within grid bounds
        diamond_x = random.randint(-GRID_LENGTH + 100, GRID_LENGTH - 100)
        diamond_y = random.randint(-GRID_LENGTH + 100, GRID_LENGTH - 100)
        diamond_spawned = True

def update_diamond():
    """Update diamond floating animation and check for collection"""
    global diamond_float_angle, diamond_collected
    if diamond_spawned and not diamond_collected:
        diamond_float_angle += 5
        if diamond_float_angle >= 360:
            diamond_float_angle = 0
        
        # Check if player is close enough to collect
        distance = ((diamond_x - player_x)**2 + (diamond_y - player_y)**2) ** 0.5
        if distance <= 40:
            diamond_collected = True

def draw_diamond():
    """Draw the diamond"""
    if not diamond_spawned or diamond_collected:
        return
    
    glPushMatrix()
    # Apply floating motion
    float_offset = diamond_float_angle * 3.14159 / 180.0
    import math
    float_y = math.sin(float_offset) * 10
    
    glTranslatef(diamond_x, diamond_y, 80 + float_y)
    glRotatef(diamond_float_angle * 2, 0, 0, 1)  # Rotate around Z axis
    glColor3f(0, 1, 1)  # Cyan color
    
    # Draw diamond shape using scaled cube
    glScalef(15, 15, 20)
    draw_unit_cube()
    glPopMatrix()

def initialize_level_enemies():
    """Initialize enemies for the current level"""
    current_enemies = get_current_enemies()
    for enemy in current_enemies:
        if current_level == 2:
            enemy.initialize_patrol()
        else:
            enemy.is_patrolling = False

def restart_game():
    """Reset all game variables to initial state"""
    global player_x, player_y, player_bullet_hits, is_player_dead, current_level, bullets_remaining
    global walk_angle, is_moving, is_crouching, player_rotation, target_rotation
    global move_dx, move_dy, current_key, frame_counter, knife_swing_angle
    global is_knife_swinging, knife_swing_speed, bullets, projectiles, bullet_pickups
    global diamond_spawned, diamond_collected, diamond_x, diamond_y, diamond_float_angle
    
    # Reset player state
    player_x, player_y = -460, -460
    player_bullet_hits = 0
    is_player_dead = False
    current_level = 1
    bullets_remaining = 3
    
    # Reset player movement and animation
    walk_angle = 0
    is_moving = False
    is_crouching = False
    player_rotation = 0
    target_rotation = 0
    move_dx, move_dy = 0, 0
    current_key = None
    frame_counter = 0
    
    # Reset knife state
    knife_swing_angle = 0
    is_knife_swinging = False
    knife_swing_speed = 5
    
    # Reset diamond state
    diamond_spawned = False
    diamond_collected = False
    diamond_x = 0
    diamond_y = 0
    diamond_float_angle = 0
    
    # Clear all projectiles, bullets, and pickups
    bullets.clear()
    projectiles.clear()
    bullet_pickups.clear()
    
    # Reset all enemies in both levels
    for enemy in enemies_level1:
        enemy.reset()
    for enemy in enemies_level2:
        enemy.reset()

def update_bullets():
    global bullets
    
    for bullet in bullets[:]:
        if not bullet.active:
            bullets.remove(bullet)
            continue
            
        bullet.update()
        
        if not bullet.active:
            continue
            
        current_enemies = get_current_enemies()
        for enemy in current_enemies:
            if enemy.is_dead:
                continue
                
            distance = ((bullet.x - enemy.x)**2 + (bullet.y - enemy.y)**2) ** 0.5
            if distance < 25:
                enemy.take_damage(bullet.x, bullet.y)
                bullet.active = False
                break

def update_projectiles():
    global projectiles
    active_projectiles = []
    
    for projectile in projectiles:
        if projectile.update():
            active_projectiles.append(projectile)
    
    projectiles = active_projectiles

def update_bullet_pickups():
    """Update all bullet pickups"""
    global bullet_pickups
    active_pickups = []
    
    for pickup in bullet_pickups:
        pickup.update()
        if pickup.active:
            active_pickups.append(pickup)
    
    bullet_pickups = active_pickups

def calculate_target_rotation(dx, dy):
    if dx == 0 and dy == 0: return None
    angle = 0
    if dx > 0 and dy == 0: angle = 0
    elif dx > 0 and dy > 0: angle = 45
    elif dx == 0 and dy > 0: angle = 90
    elif dx < 0 and dy > 0: angle = 135
    elif dx < 0 and dy == 0: angle = 180
    elif dx < 0 and dy < 0: angle = 225
    elif dx == 0 and dy < 0: angle = 270
    elif dx > 0 and dy < 0: angle = 315
    return angle

def smooth_rotation(current, target, speed=5.0):
    if target is None: return current
    current = current % 360
    target = target % 360
    diff = target - current
    if diff > 180: diff -= 360
    elif diff < -180: diff += 360
    if abs(diff) < speed: return target
    return current + (speed if diff > 0 else -speed)

def check_knife_kills():
    global player_x, player_y, is_knife_swinging
    
    if not is_knife_swinging or is_player_dead:
        return
        
    kill_range = 1 * 120
    
    current_enemies = get_current_enemies()
    for enemy in current_enemies:
        if enemy.is_dead:
            continue
            
        distance_to_enemy = ((player_x - enemy.x)**2 + (player_y - enemy.y)**2) ** 0.5
        
        if distance_to_enemy <= kill_range:
            enemy.kill_enemy()

def check_level_transition():
    global current_level, player_x, player_y

    gap_size = 120
    transition_threshold = 60

    if current_level == 1:
        block100_x, block100_y = get_block_center(100)
        gap_center_x = block100_x
        gap_center_y = GRID_LENGTH
        # Only allow transition if all enemies are dead
        if (abs(player_x - gap_center_x) < transition_threshold and
            abs(player_y - gap_center_y) < transition_threshold and
            all_enemies_dead()):
            current_level = 2
            block2_x, block2_y = get_block_center(2)
            player_x, player_y = block2_x, block2_y
            # Initialize patrolling for level 2 enemies
            initialize_level_enemies()

    elif current_level == 2:
        block100_x, block100_y = get_block_center(100)
        gap_center_x = block100_x
        gap_center_y = GRID_LENGTH
        # In level 2, check if diamond is collected instead of just enemies dead
        if (abs(player_x - gap_center_x) < transition_threshold and
            abs(player_y - gap_center_y) < transition_threshold and
            diamond_collected):
            # Game complete - could add victory screen here
            pass

# Drawing functions
def draw_unit_cube():
    vertices = [(-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
                (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)]
    faces = [(0,1,2,3),(4,5,6,7),(0,1,5,4),(2,3,7,6),(1,2,6,5),(0,3,7,4)]
    glBegin(GL_QUADS)
    for face in faces:
        for v in face:
            glVertex3f(*vertices[v])
    glEnd()

def draw_enemy(enemy):
    glPushMatrix()
    glTranslatef(enemy.x, enemy.y, 0)
    glRotatef(enemy.rotation, 0, 0, 1)
    
    if enemy.is_dead:
        glRotatef(enemy.death_rotation, 1, 0, 0)
    
    glTranslatef(0, 0, 30)

    # Health indicator
    if not enemy.is_dead and enemy.health < enemy.max_health:
        glPushMatrix()
        glTranslatef(0, 0, 50)
        for i in range(enemy.health):
            glPushMatrix()
            glTranslatef((i - 1) * 8, 0, 0)
            glScalef(4, 4, 4)
            glColor3f(0, 1, 0)
            draw_unit_cube()
            glPopMatrix()
        glPopMatrix()

    # Torso
    glPushMatrix()
    glScalef(18, 15, 35)
    if enemy.is_dead:
        glColor3f(0.5, 0, 0)
    elif enemy.is_firing:
        glColor3f(1, 0.5, 0)
    elif enemy.is_patrolling:
        glColor3f(0.8, 0.4, 0)  # Different color when patrolling
    else:
        glColor3f(1, 0, 0)
    draw_unit_cube()
    glPopMatrix()

    # Head
    glPushMatrix()
    glTranslatef(0, 0, 35)
    glScalef(12, 12, 12)
    if enemy.is_dead:
        glColor3f(0.8, 0.7, 0.5)
    else:
        glColor3f(1, 0.8, 0.6)
    draw_unit_cube()
    glPopMatrix()

    # Arms
    if enemy.is_dead:
        swing = 0
    else:
        swing = (enemy.walk_angle % 360) * 12 / 30
        if swing > 180: swing = 360 - swing
        swing = swing - 90 if swing > 90 else swing
    
    arm_z_pos = 18
    for y_mult, rot_mult in [(14, 1), (-14, -1)]:
        glPushMatrix()
        glTranslatef(0, y_mult, arm_z_pos)
        if not enemy.is_dead:
            glRotatef(swing*rot_mult, 1, 0, 0)
        glScalef(4, 12, 14)
        if enemy.is_dead:
            glColor3f(0.5, 0, 0)
        else:
            glColor3f(1, 0, 0)
        draw_unit_cube()
        glPopMatrix()

    # Legs
    leg_z_scale = 20
    leg_z_pos = -5
    if enemy.is_dead:
        leg_swing = 0
    else:
        leg_swing = swing * 1.5
        
    for y_mult, rot_mult in [(6, -1), (-6, 1)]:
        glPushMatrix()
        glTranslatef(0, y_mult, leg_z_pos)
        if not enemy.is_dead:
            glRotatef(leg_swing*rot_mult, 1, 0, 0)
        glScalef(8, 8, leg_z_scale)
        glColor3f(0, 0, 0)
        draw_unit_cube()
        glPopMatrix()

    # Gun
    glPushMatrix()
    glTranslatef(12, 0, 10)
    glScalef(15, 3, 3)
    if enemy.is_firing:
        glColor3f(1, 1, 0)
    else:
        glColor3f(0.2, 0.2, 0.2)
    draw_unit_cube()
    glPopMatrix()

    glPopMatrix()

def draw_exit_carpet(x, y):
    glPushMatrix()
    glTranslatef(x, y, 1)
    glScalef(40, 40, 2)
    
    # Change color based on victory condition
    if current_level == 1:
        # Level 1: all enemies must be dead
        if all_enemies_dead():
            glColor3f(1, 0, 0)  # Red when player can proceed
        else:
            glColor3f(0.5, 0.5, 0.5)  # Gray when blocked
    elif current_level == 2:
        # Level 2: diamond must be collected
        if diamond_collected:
            glColor3f(1, 0, 0)  # Red when player can proceed
        else:
            glColor3f(0.5, 0.5, 0.5)  # Gray when blocked
    
    draw_unit_cube()
    glPopMatrix()

def draw_player():
    global walk_angle, player_rotation, knife_swing_angle, knife_swing_speed, is_knife_swinging
    glPushMatrix()
    glTranslatef(player_x, player_y, 0)
    
    if is_player_dead:
        glRotatef(90, 1, 0, 0)
        glTranslatef(0, 0, -15)
        glColor3f(0.5, 0, 0)
        glScalef(20, 10, 40)
        draw_unit_cube()
        glPopMatrix()
        return
    else:
        glRotatef(player_rotation, 0, 0, 1)
        glTranslatef(0, 0, 25 if is_crouching else 40)

    # Torso
    glPushMatrix()
    glScalef(20, 10, 25 if is_crouching else 40)
    glColor3f(0, 0, 1)
    draw_unit_cube()
    glPopMatrix()

    # Head
    glPushMatrix()
    glTranslatef(0, 0, 30 if is_crouching else 50)
    glScalef(15, 15, 12 if is_crouching else 15)
    glColor3f(1, 0.8, 0.6)
    draw_unit_cube()
    glPopMatrix()

    # Arms - animated
    swing = (walk_angle % 360) * 15 / 24 if is_moving else (walk_angle % 360) * 5 / 72
    if swing > 180:
        swing = 360 - swing
    swing = swing - 90 if swing > 90 else swing

    arm_height = 20 if is_crouching else 30
    arm_z_scale = 15 if is_crouching else 20

    # Handle knife swinging animation
    if is_knife_swinging:
        knife_swing_angle += knife_swing_speed
        if knife_swing_angle > 45:
            knife_swing_speed = -knife_swing_speed
        elif knife_swing_angle < -45:
            knife_swing_speed = -knife_swing_speed

    # Left arm with knife
    glPushMatrix()
    glTranslatef(0, -15, arm_height)
    glRotatef((swing * -1) + knife_swing_angle, 1, 0, 0)
    
    glPushMatrix()
    glScalef(5, 20, arm_z_scale)
    glColor3f(0, 0, 1)
    draw_unit_cube()
    glPopMatrix()
    
    # Knife
    glPushMatrix()
    glTranslatef(0, 0, arm_z_scale)
    glRotatef(90, 0, 1, 0)
    glScalef(3, 3, 25)
    glColor3f(0.7, 0.7, 0.7)
    draw_unit_cube()
    glPopMatrix()
    
    glPopMatrix()

    # Right arm
    glPushMatrix()
    glTranslatef(0, 15, arm_height)
    glRotatef(swing * 1, 1, 0, 0)
    
    glPushMatrix()
    glScalef(5, 20, arm_z_scale)
    glColor3f(0, 0, 1)
    draw_unit_cube()
    glPopMatrix()
    
    glPopMatrix()

    # Cannon
    glPushMatrix()
    glTranslatef(0, 15, arm_height)
    glTranslatef(12, 0, 0)
    glRotatef(90, 0, 1, 0)
    glScalef(3, 3, 25)
    glColor3f(0.5, 0.5, 0.2)
    draw_unit_cube()
    glPopMatrix()

    # Legs
    leg_z_scale = 20 if is_crouching else 30
    leg_z_pos = -5 if is_crouching else 0
    for y_mult, rot_mult in [(8, -1), (-8, 1)]:
        glPushMatrix()
        glTranslatef(0, y_mult, leg_z_pos)
        glRotatef(swing * rot_mult, 1, 0, 0)
        glScalef(10, 10, leg_z_scale)
        glColor3f(0.5, 0.2, 0.2)
        draw_unit_cube()
        glPopMatrix()

    glPopMatrix()

def draw_floor_and_boundary():
    grid_size = 120
    grid_number = 1

    for row in range(10):
        for col in range(10):
            i = -GRID_LENGTH + col * grid_size
            j = -GRID_LENGTH + row * grid_size

            glColor3f(0.35, 0.17, 0)
            glBegin(GL_QUADS)
            glVertex3f(i, j, 0)
            glVertex3f(i + grid_size, j, 0)
            glVertex3f(i + grid_size, j + grid_size, 0)
            glVertex3f(i, j + grid_size, 0)
            glEnd()

            center_x = i + grid_size / 2
            center_y = j + grid_size / 2
            glColor3f(0.35,0.17,0)
            glRasterPos2f(center_x, center_y)
            for char in str(grid_number):
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

            grid_number += 1

    if current_level in [1, 2]:
        block100_x, block100_y = get_block_center(100)
        draw_exit_carpet(block100_x, block100_y)

def draw_outer_boundary(level):
    wall_height = 100
    wall_thickness = 40
    half_len = GRID_LENGTH
    gap_size = 120

    glColor3f(0.5, 0.5, 0.5)

    def wall_segment(cx, cy, sx, sy):
        glPushMatrix()
        glTranslatef(cx, cy, wall_height/2)
        glScalef(sx, sy, wall_height)
        draw_unit_cube()
        glPopMatrix()

    block2_x, block2_y = get_block_center(2)
    block100_x, block100_y = get_block_center(100)
    
    wall_segment((-half_len + block2_x - gap_size/2)/2, -half_len,
                 block2_x - gap_size/2 - (-half_len), wall_thickness)
    wall_segment((block2_x + gap_size/2 + half_len)/2, -half_len,
                 half_len - (block2_x + gap_size/2), wall_thickness)
    wall_segment((-half_len + block100_x - gap_size/2)/2, half_len,
                 block100_x - gap_size/2 - (-half_len), wall_thickness)
    wall_segment((block100_x + gap_size/2 + half_len)/2, half_len,
                 half_len - (block100_x + gap_size/2), wall_thickness)
    wall_segment(-half_len, 0, wall_thickness, 2*half_len)
    wall_segment(half_len, 0, wall_thickness, 2*half_len)

def draw_maze(walls):
    wall_height = 80
    wall_thickness = 20
    for (x1, y1, x2, y2) in walls:
        cx, cy = (x1+x2)/2, (y1+y2)/2
        length = ((x2-x1)**2 + (y2-y1)**2) ** 0.5
        glPushMatrix()
        glTranslatef(cx, cy, wall_height/2)
        glScalef(wall_thickness, length, wall_thickness) if x1==x2 else glScalef(length, wall_thickness, wall_height)
        glColor3f(0, 0.6, 0)
        draw_unit_cube()
        glPopMatrix()

def draw_health_display():
    global player_bullet_hits, bullets_remaining, is_player_dead
    
    # Set up 2D rendering for HUD
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Display health
    health_percentage = max(0, (30 - player_bullet_hits) / 30.0)
    health_text = f"Health: {int(health_percentage * 100)}%"
    
    glColor3f(1, 0, 0) if health_percentage < 0.3 else glColor3f(1, 1, 0) if health_percentage < 0.7 else glColor3f(0, 1, 0)
    glRasterPos2f(10, window_height - 30)
    for char in health_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Display bullets remaining
    bullets_text = f"Bullets: {bullets_remaining}"
    glColor3f(1, 1, 1) if bullets_remaining > 0 else glColor3f(1, 0, 0)
    glRasterPos2f(10, window_height - 60)
    for char in bullets_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Display current level
    level_text = f"Level: {current_level}"
    glColor3f(1, 1, 1)
    glRasterPos2f(10, window_height - 90)
    for char in level_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Display enemies remaining for current level
    current_enemies = get_current_enemies()
    enemies_alive = sum(1 for enemy in current_enemies if not enemy.is_dead)
    enemies_text = f"Enemies Remaining: {enemies_alive}"
    glColor3f(1, 0.5, 0) if enemies_alive > 0 else glColor3f(0, 1, 0)
    glRasterPos2f(10, window_height - 120)
    for char in enemies_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Display diamond status for level 2
    if current_level == 2:
        if diamond_spawned:
            diamond_text = "Diamond: Collected" if diamond_collected else "Diamond: Find and collect it!"
            glColor3f(0, 1, 0) if diamond_collected else glColor3f(0, 1, 1)
        else:
            diamond_text = "Diamond: Kill all enemies to spawn"
            glColor3f(1, 0.5, 0)
        glRasterPos2f(10, window_height - 150)
        for char in diamond_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Display restart instruction (always visible)
    restart_text = "Press R to restart"
    glColor3f(0.7, 0.7, 0.7)
    glRasterPos2f(10, window_height - 180)
    for char in restart_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Display death message if player is dead
    if is_player_dead:
        death_text = "YOU DIED! Press R to restart"
        glColor3f(1, 0, 0)
        glRasterPos2f(window_width//2 - 120, window_height//2)
        for char in death_text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Display victory message
    if not is_player_dead:
        if current_level == 1 and all_enemies_dead():
            victory_text = "Level 1 Complete! Proceed to exit"
            glColor3f(0, 1, 0)
            glRasterPos2f(window_width//2 - 150, window_height//2 + 50)
            for char in victory_text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
        elif current_level == 2 and diamond_collected:
            victory_text = "You Win! Game Complete!"
            glColor3f(0, 1, 0)
            glRasterPos2f(window_width//2 - 150, window_height//2 + 50)
            for char in victory_text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    # Restore projection and modelview matrices
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

def fire_bullet():
    """Fire a bullet in the direction the player is facing"""
    global bullets, bullets_remaining, player_rotation
    
    if bullets_remaining <= 0 or is_player_dead:
        return
    
    # Calculate bullet starting position (in front of player)
    import math
    angle_rad = math.radians(player_rotation)
    start_x = player_x + math.cos(angle_rad) * 30
    start_y = player_y + math.sin(angle_rad) * 30
    
    # Create and add bullet
    bullet = Bullet(start_x, start_y, player_rotation)
    bullets.append(bullet)
    bullets_remaining -= 1

def setup_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, window_width/window_height, 1, 5000)

    zoom_factor = 0.7
    angle_rad = camera_x_angle * 3.14159 / 180.0
    cam_x = camera_y_offset * zoom_factor * (1.0 if camera_x_angle == 0 else -1.0 if camera_x_angle == 180 else 0.0)
    cam_y = camera_y_offset * zoom_factor * (1.0 if camera_x_angle == 90 else -1.0 if camera_x_angle == 270 else 0.0)
    
    if camera_x_angle not in [0, 90, 180, 270]:
        cam_x = camera_y_offset * zoom_factor * 0.707 if camera_x_angle in [45, 315] else camera_y_offset * zoom_factor * -0.707
        cam_y = camera_y_offset * zoom_factor * 0.707 if camera_x_angle in [45, 135] else camera_y_offset * zoom_factor * -0.707
    
    gluLookAt(cam_x, cam_y, 420, 0, 0, 0, 0, 0, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def can_move(nx, ny):
    margin = 25
    gap_size = 120

    block2_x, block2_y = get_block_center(2)
    block100_x, block100_y = get_block_center(100)

    in_bottom_gap = (abs(nx - block2_x) < gap_size/2 and ny < -GRID_LENGTH + margin)
    in_top_gap = (abs(nx - block100_x) < gap_size/2 and ny > GRID_LENGTH - margin)

    if not (in_bottom_gap or in_top_gap):
        if nx < -GRID_LENGTH + margin or nx > GRID_LENGTH - margin:
            return False
        if ny < -GRID_LENGTH + margin or ny > GRID_LENGTH - margin:
            return False

    walls = maze_walls_level1 if current_level==1 else maze_walls_level2
    for (x1, y1, x2, y2) in walls:
        if x1==x2 and abs(nx-x1)<20 and min(y1, y2)<=ny<=max(y1, y2):
            return False
        if y1==y2 and abs(ny-y1)<20 and min(x1, x2)<=nx<=max(x1, x2):
            return False
    return True

def mouseClick(button, state, x, y):
    global is_knife_swinging

    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        is_knife_swinging = True
    elif button == GLUT_LEFT_BUTTON and state == GLUT_UP:
        is_knife_swinging = False
    elif button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        fire_bullet()

def handle_key_release():
    global move_dx, move_dy, current_key
    if current_key not in [b"w", b"a", b"s", b"d"]:
        move_dx, move_dy = 0, 0

def keyboardListener(key, x, y):
    global move_dx, move_dy, is_crouching, current_key, target_rotation, current_level
    current_key = key

    # Check for restart key (works both when dead and alive)
    if key == b"r":
        restart_game()
        return

    if key == b"c":
        is_crouching = not is_crouching
        move_dx, move_dy = 0, 0
        return

    current_speed = crouch_speed if is_crouching else move_speed

    if key == b"s":
        move_dx, move_dy = current_speed, 0
        target_rotation = calculate_target_rotation(move_dx, move_dy)
    elif key == b"d":
        move_dx, move_dy = 0, current_speed
        target_rotation = calculate_target_rotation(move_dx, move_dy)
    elif key == b"w":
        move_dx, move_dy = -current_speed, 0
        target_rotation = calculate_target_rotation(move_dx, move_dy)
    elif key == b"a":
        move_dx, move_dy = 0, -current_speed
        target_rotation = calculate_target_rotation(move_dx, move_dy)
    elif key == b"p":
        current_level = 2 if current_level == 1 else 1
        move_dx, move_dy = 0, 0
        initialize_level_enemies()  # Initialize enemies for new level
    else:
        move_dx, move_dy = 0, 0

def specialKeyListener(key, x, y):
    global camera_y_offset, camera_x_angle
    if key == 101: camera_y_offset += 20
    elif key == 103: camera_y_offset -= 20
    elif key == 100: camera_x_angle -= 5
    elif key == 102: camera_x_angle += 5

def showScreen():
    global walk_angle, player_x, player_y, is_moving, player_rotation, target_rotation, current_key, frame_counter

    frame_counter += 1

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, window_width, window_height)
    setup_camera()

    if not is_player_dead:
        player_rotation = smooth_rotation(player_rotation, target_rotation)

        nx, ny = player_x + move_dx, player_y + move_dy
        is_moving = (move_dx != 0 or move_dy != 0)
        if is_moving and can_move(nx, ny):
            player_x, player_y = nx, ny
            walk_angle += 10
        else:
            walk_angle += 1
        if walk_angle >= 360: walk_angle = 0
    else:
        is_moving = False

    update_bullets()
    update_projectiles()
    update_bullet_pickups()
    check_knife_kills()

    # Update enemies for current level
    current_enemies = get_current_enemies()
    for enemy in current_enemies:
        enemy.update(player_x, player_y, is_crouching)

    # Spawn diamond in level 2 when all enemies are dead
    if current_level == 2 and all_enemies_dead() and not diamond_spawned:
        spawn_diamond()
    
    # Update diamond
    update_diamond()

    check_level_transition()
    handle_key_release()
    current_key = None

    draw_floor_and_boundary()
    draw_outer_boundary(current_level)

    if current_level==1:
        draw_maze(maze_walls_level1)
    elif current_level==2:
        draw_maze(maze_walls_level2)

    # Draw enemies for current level
    current_enemies = get_current_enemies()
    for enemy in current_enemies:
        draw_enemy(enemy)

    draw_player()
    
    for bullet in bullets:
        bullet.draw()
    
    for projectile in projectiles:
        projectile.draw()
    
    # Draw bullet pickups
    for pickup in bullet_pickups:
        pickup.draw()
    
    # Draw diamond if spawned
    draw_diamond()
    
    draw_health_display()

    glutSwapBuffers()

def main():
    global enemies_level1, enemies_level2

    enemies_level1 = [
        Enemy(35),
        Enemy(50),
        Enemy(65)
    ]

    enemies_level2 = [
        Enemy(30),
        Enemy(37),
        Enemy(74),
        Enemy(44),
        Enemy(69)
    ]

    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(window_width, window_height)
    glutCreateWindow(b"Merged Maze Combat Game")

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseClick)
    glutIdleFunc(showScreen)

    glutMainLoop()

if __name__ == "__main__":
    main()