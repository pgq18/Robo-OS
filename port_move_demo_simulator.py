#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HAROS • Port Logistics Free-Move v9c (Windows / pygame)

- No roads. Free manual control with collision avoidance.
- Only the selected car responds to arrows (others are force-stopped unless bouncing from exit).
- Releasing arrows stops immediately; exit bounce ends with zero velocity.
- 3 transfer points (T1..T3), 4 cars; Exit A/B auto-unload & short reverse.
"""

import math
import time
from typing import List, Tuple, Optional, Dict

import pygame
from robot_arm.robot_agent import RobotAgent as RobotArm
from robot_dog.robot_agent import RobotAgent as RobotDog

# ---------------------------- Layout / Style ----------------------------
W, H = 1280, 800
FPS = 60

CAR_R = 18
CAR_W, CAR_L = 26, 44
SAFE_DIST = CAR_R * 2.0 * 0.95

COL_BG     = (10, 12, 16)
COL_ZONE   = (30, 36, 48)
COL_DOCK_TINT = (60, 90, 120, 80)

COL_EXIT_A = (0, 170, 255)
COL_EXIT_B = (255, 140, 80)

COL_HAROS  = (70, 210, 255)
COL_EDGE   = (0, 120, 255)
COL_TEXT   = (230, 240, 255)
COL_PANEL  = (15, 18, 28, 180)

SPEEDS = {'slow': 80.0, 'medium': 140.0, 'fast': 220.0}

# ---------------------------- Cargo / Arms ----------------------------
class CargoItem:
    def __init__(self, t_id: str, idx: int, kind: str):
        self.t_id=t_id
        self.idx=idx
        self.kind=kind  # 'A' or 'B'
        self.name = f"Cargo{kind}-{t_id}-{idx}"

def fixed_AB_distribution(count:int, phase:int=0)->List[str]:
    return ['A' if (i+phase)%2==0 else 'B' for i in range(count)]

class Arm(RobotArm):
    def __init__(self, name: str, docker_name:str, base_pos: Tuple[int,int], dock_rect: pygame.Rect, queue: List[CargoItem], config_path:str="./robot_arm/robot_agent_config.yaml"):
        super().__init__(name, docker_name, [], config_path)
        self.name=name
        self.dock_name = docker_name
        self.base_pos=base_pos
        self.dock_rect=dock_rect
        self.queue=queue
        ret = self.set_scene_properties(item=docker_name, objects=[q.name for q in queue])
        if ret is not True:
            print(ret)
            print(f"Error: Failed to set scene properties for {docker_name}")

    def set_cars(self, cars: List["Car"]):
        self.cars=cars

    def draw(self, screen: pygame.Surface, selected: bool=False):
        x,y=self.base_pos
        base_r=18
        pygame.draw.circle(screen,(60,70,90),(x,y),base_r)
        pygame.draw.circle(screen, COL_EDGE if selected else (40,50,70),(x,y),base_r,2)
        shoulder_len=30; forearm_len=24
        t=pygame.time.get_ticks()*0.002 + (hash(self.name)%100)
        ang1=-0.4 + 0.2*math.sin(t)
        ang2= 0.9 + 0.2*math.cos(t*1.2)
        sx=x+int(math.cos(ang1)*shoulder_len); sy=y+int(math.sin(ang1)*shoulder_len)
        ex=sx+int(math.cos(ang2)*forearm_len);  ey=sy+int(math.sin(ang2)*forearm_len)
        pygame.draw.line(screen, COL_HAROS, (x,y), (sx,sy), 6)
        pygame.draw.line(screen, COL_HAROS, (sx,sy), (ex,ey), 6)
        pygame.draw.circle(screen, (255,230,120), (ex,ey), 4)

        tint=pygame.Surface(self.dock_rect.size, pygame.SRCALPHA); tint.fill(COL_DOCK_TINT)
        screen.blit(tint, self.dock_rect.topleft)

        font=pygame.font.SysFont("Consolas,Menlo,Arial",18)
        qa=sum(1 for c in self.queue if c.kind=='A'); qb=sum(1 for c in self.queue if c.kind=='B')
        s=font.render(f"{self.name}  A:{qa}  B:{qb}", True, COL_TEXT)
        screen.blit(s, (self.dock_rect.left, self.dock_rect.top-22))
        
        # 绘制队列中的 CargoItem 对象
        cargo_font = pygame.font.SysFont("Consolas,Menlo,Arial", 14)
        for i, cargo in enumerate(self.queue[:5]):  # 只显示前5个货物
            cargo_col = (0,220,255) if cargo.kind=='A' else (255,160,60)
            cargo_text = f"{cargo.t_id}-{cargo.idx}{cargo.kind}"
            cargo_surf = cargo_font.render(cargo_text, True, cargo_col)
            screen.blit(cargo_surf, (self.dock_rect.left + 10, self.dock_rect.top + 20 + i*20))

    def nearest_car_in_dock(self, cars: List["Car"]) -> Optional["Car"]:
        best=None; best_d2=1e12
        for c in cars:
            if self.dock_rect.collidepoint(c.x,c.y) and c.cargo is None:
                d2=(c.x-self.base_pos[0])**2 + (c.y-self.base_pos[1])**2
                if d2<best_d2: best_d2=d2; best=c
        return best

    def pop_next(self, kind: Optional[str]) -> Optional[CargoItem]:
        if not self.queue: return None
        if kind in ('A','B'):
            for i,c in enumerate(self.queue):
                if c.kind==kind: return self.queue.pop(i)
            return None
        return self.queue.pop(0)

    def load(self, kind: Optional[str]=None) -> Optional["Car"]:
        car = self.nearest_car_in_dock(self.cars)
        if car is None or car.cargo is not None:
            return None
        item=self.pop_next(kind)
        if item is None:
            return None
        car.cargo=item
        return car

    def load_object(self, kind: Optional[str]=None):
        print(">>>>>>>> Task load_object started <<<<<<<<")
        car = self.load(kind)
        if car:
            self.set_scene_properties(item=self.dock_name, objects=[q.name for q in self.queue])
            car.master_memory.add_object_to_robot(car.name, [car.cargo.name])
            return True, f'Robot arm successfully grasped the object with kind {kind} and placed it.'
        else:
            return False, f'No object with kind {kind} to load.'

# ---------------------------- Exit zones ----------------------------
class ExitBay:
    def __init__(self, name: str, rect: pygame.Rect, color: Tuple[int,int,int], kind: str):
        self.name=name
        self.rect=rect
        self.color=color
        self.kind=kind
        self.cargo: Optional[CargoItem]=None

    def draw(self, screen: pygame.Surface):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=12)
        pygame.draw.rect(screen, (0,0,0), self.rect, 2, border_radius=12)
        font=pygame.font.SysFont("Arial", 20, bold=True)
        label = "Exit A (Export)" if self.name=='A' else "Exit B (Export)"
        s=font.render(label, True, (0,0,0))
        screen.blit(s, (self.rect.centerx - s.get_width()//2, self.rect.centery - s.get_height()//2))

# ---------------------------- Car ----------------------------
class Car(RobotDog):
    def __init__(self, idx:int, x:int, y:int, navigate_position:str, current_position:str='Parking Area', config_path:str="./robot_dog/robot_agent_config.yaml"):
        super().__init__(f"dog{idx}", current_position, navigate_position, config_path)
        self.name=f"dog{idx}"
        self.idx=idx; self.x=float(x); self.y=float(y)
        self.vx=0.0; self.vy=0.0
        self.heading=0.0  # radians
        self.speed_mode='slow'
        self.cargo: Optional[CargoItem]=None
        self.mode='manual'         # 'manual' or 'goto'
        self.goto: Optional[Tuple[float,float]]=None
        self.bounce_t=0.0
        self.exit_bays:Dict[str, ExitBay] = None
        self.docks:Dict[str, Arm] = None

    def set_exit_bays(self, exit_bays: Dict[str, ExitBay]):
        self.exit_bays=exit_bays

    def set_docks(self, docks: Dict[str, Arm]):
        self.docks=docks

    def set_speed_mode(self, mode:str):
        if mode in SPEEDS:
            self.speed_mode=mode

    def stop(self):
        self.vx=self.vy=0.0
        self.mode='manual'
        self.goto=None

    def set_goto(self, p:Tuple[float,float]):
        self.goto=p
        self.mode='goto'

    def navigate_to_where(self, location: str):
        print(">>>>>>>> Task navigate_to_where started <<<<<<<<")
        if location == "Dock1":
            p = self.master_memory.get_item_property(location, 'location')
            self.goto = (p[0]+(self.idx-1)*60, p[1])
            self.mode = 'goto'
        elif location == "Dock2":
            p = self.master_memory.get_item_property(location, 'location')
            self.goto = (p[0]+(self.idx-1)*60, p[1])
            self.mode = 'goto'
        elif location == "Exit Bay A":
            p = self.master_memory.get_item_property(location, 'location')
            self.goto = (p[0]+(self.idx-1)*60, p[1])
            self.mode = 'goto'
        elif location == "Exit Bay B":
            p = self.master_memory.get_item_property(location, 'location')
            self.goto = (p[0]+(self.idx-1)*60, p[1])
            self.mode = 'goto'
        else:
            print(f"Invalid location: {location}")
            return False, f"Invalid location: {location}"
        while self.mode == 'goto':
            time.sleep(0.1)
        self.master_memory.update_robot_position(self.name, location)
        return True, f'Robot dog successfully navigated to {location}.'

    def unload_object(self):
        print(">>>>>>>> Task unload_object started <<<<<<<<")
        bay_around, cargo = self.unload()
        if cargo:
            self.master_memory.remove_object_from_robot(self.name, cargo.name)
            self.master_memory.update_item_property(bay_around.name, 'objects', [cargo.name])
        return True, 'Object has been unloaded from the robot dog.'

    def exit_bay_around(self, exit_bays: List[ExitBay]):
        """
        返回车辆当前所在位置的出口区域
        """
        for e in exit_bays:
            if e.rect.collidepoint(self.x, self.y):
                return e
        return None

    def unload(self):
        """
        在任意位置卸载货物，返回被卸载的货物
        """
        cargo = self.cargo
        self.cargo = None
        bay_around = self.exit_bay_around(self.exit_bays.values())
        if bay_around is not None:
            bay_around.cargo = cargo
        return bay_around, cargo

    def draw(self, screen: pygame.Surface, selected: bool=False):
        body=pygame.Surface((CAR_L, CAR_W), pygame.SRCALPHA)
        pygame.draw.rect(body,(30,30,30),(6,1,10,6), border_radius=2)
        pygame.draw.rect(body,(30,30,30),(6,CAR_W-7,10,6), border_radius=2)
        pygame.draw.rect(body,(30,30,30),(CAR_L-16,1,10,6), border_radius=2)
        pygame.draw.rect(body,(30,30,30),(CAR_L-16,CAR_W-7,10,6), border_radius=2)
        pygame.draw.rect(body, COL_HAROS, (0,6,CAR_L-12,CAR_W-12), border_radius=6)
        pygame.draw.rect(body, (0,90,200), (0,6,CAR_L-12,CAR_W-12), width=2, border_radius=6)
        if self.cargo is not None:
            col=(0,220,255) if self.cargo.kind=='A' else (255,160,60)
            pygame.draw.rect(body, col, (CAR_L-22,8,16,CAR_W-16), border_radius=3)
            pygame.draw.rect(body, (80,70,60), (CAR_L-22,8,16,CAR_W-16), width=1, border_radius=3)
        if selected: pygame.draw.rect(body,(255,255,255),(0,0,CAR_L,CAR_W), width=2, border_radius=8)
        img=pygame.transform.rotate(body, -math.degrees(self.heading))
        rect=img.get_rect(center=(int(self.x), int(self.y)))
        screen.blit(img, rect.topleft)
        font=pygame.font.SysFont("Arial",14,bold=True)
        s=font.render(f"car-{self.idx}", True, COL_TEXT)
        screen.blit(s,(rect.centerx - s.get_width()//2, rect.top-16))

        # 显示 CargoItem 信息
        if self.cargo is not None:
            cargo_font = pygame.font.SysFont("Arial", 12)
            cargo_text = f"{self.cargo.t_id}-{self.cargo.idx}{self.cargo.kind}"
            cargo_surface = cargo_font.render(cargo_text, True, COL_TEXT)
            screen.blit(cargo_surface, (rect.centerx - cargo_surface.get_width()//2, rect.bottom + 2))

    # ---------------------------- Scene ----------------------------
class Scene:
    def __init__(self):
        # Exits
        self.exitA=ExitBay('A', pygame.Rect(W//2-240, 40, 480, 44), COL_EXIT_A, 'A')
        self.exitB=ExitBay('B', pygame.Rect(W//2-240, H-84, 480, 44), COL_EXIT_B, 'B')

        # Cars
        self.cars: List[Car]=[]
        # spawn = [(self.exitA.rect.left+80, self.exitA.rect.bottom+120),
        #          (self.exitA.rect.centerx, self.exitA.rect.bottom+170),
        #          (self.exitA.rect.right-80, self.exitA.rect.bottom+120),
        #          (W//2-200, H//2)]
        spawn = [
            (self.exitA.rect.left+80, self.exitA.rect.bottom+120),
            (W//2-200, H//2)
            ]
        for i,(x,y) in enumerate(spawn, start=1):
            car = Car(i,x,y, navigate_position=['Dock1', 'Dock2', 'Exit Bay A', 'Exit Bay B'])
            car.set_exit_bays({"Exit Bay A": self.exitA, "Exit Bay B": self.exitB})
            self.cars.append(car)

        # Transfer points
        self.arms: List[Arm]=[]
        self._add_arm('arm1', "Dock1", base=(220, 130), dock=pygame.Rect(150, 170, 220, 80), count=3, phase=0)
        self._add_arm('arm2', "Dock2", base=(W-220, H//2+40), dock=pygame.Rect(W-360, H//2-10, 220, 80), count=5, phase=1)
        # self._add_arm('T3', base=(W//2, H-160), dock=pygame.Rect(W//2-120, H-240, 240, 80), count=7, phase=0)
        for car in self.cars:
            car.set_docks({"Dock1": self.arms[0], "Dock2": self.arms[1]})

        self.selected_group='car'; self.sel_index=0
        self.hud=True; self.keys_held=set()
        self.delivered={'A':0,'B':0}

    def _add_arm(self, name:str, docker_name:str, base:Tuple[int,int], dock:pygame.Rect, count:int, phase:int):
        kinds=fixed_AB_distribution(count, phase=phase)
        q=[CargoItem(name,i+1,kinds[i]) for i in range(count)]
        arm = Arm(name, docker_name, base, dock, q)
        arm.set_cars(self.cars)
        self.arms.append(arm)

    # API
    def select_car(self, i:int): self.selected_group='car'; self.sel_index=max(0,min(len(self.cars)-1,i-1))
    def select_arm(self, i:int): self.selected_group='arm'; self.sel_index=max(0,min(len(self.arms)-1,i-1))
    def set_car_speed(self, i:int, mode:str): self.cars[i-1].set_speed_mode(mode)
    def command_arm_load(self, t_name:str, target_car:Optional[int]=None, kind:Optional[str]=None):
        arm = next((a for a in self.arms if a.name==t_name), None)
        if arm is None: return None
        if target_car is not None:
            car=self.cars[target_car-1]
            if arm.dock_rect.collidepoint(car.x,car.y) and car.cargo is None:
                item=arm.pop_next(kind)
                if item: car.cargo=item
                return item
            return None
        return arm.load(self.cars, kind=kind)

    # Input
    def handle_event(self, e):
        if e.type==pygame.KEYDOWN:
            self.keys_held.add(e.key)
            if e.key in (pygame.K_ESCAPE, pygame.K_q): pygame.event.post(pygame.event.Event(pygame.QUIT))
            if e.key==pygame.K_TAB:
                if self.selected_group=='car':
                    if self.sel_index < len(self.cars)-1: self.sel_index += 1
                    else: self.selected_group, self.sel_index='arm', 0
                else:
                    if self.sel_index < len(self.arms)-1: self.sel_index += 1
                    else: self.selected_group, self.sel_index='car', 0
            if pygame.K_1 <= e.key <= pygame.K_9:
                i=min(4, e.key - pygame.K_0); self.select_car(i)
            if e.key in (pygame.K_F1,pygame.K_F2,pygame.K_F3):
                self.select_arm({pygame.K_F1:1,pygame.K_F2:2,pygame.K_F3:3}[e.key])
            if e.key==pygame.K_h: self.hud=not self.hud

            if self.selected_group=='car':
                car=self.cars[self.sel_index]
                if e.key==pygame.K_s: car.stop()
                if e.key==pygame.K_z: car.set_speed_mode('slow')
                if e.key==pygame.K_x: car.set_speed_mode('medium')
                if e.key==pygame.K_c: car.set_speed_mode('fast')
                if e.key==pygame.K_d: car.unload()
            else:
                arm=self.arms[self.sel_index]
                if e.key==pygame.K_SPACE: arm.load(kind=None)
                if e.key==pygame.K_a: arm.load(kind='A')
                if e.key==pygame.K_b: arm.load(kind='B')

        elif e.type==pygame.KEYUP:
            if e.key in self.keys_held: self.keys_held.remove(e.key)
            # immediate stop when arrow keys are released (for selected car)
            if self.selected_group=='car' and e.key in (pygame.K_LEFT,pygame.K_RIGHT,pygame.K_UP,pygame.K_DOWN):
                car=self.cars[self.sel_index]
                arrows={pygame.K_LEFT,pygame.K_RIGHT,pygame.K_UP,pygame.K_DOWN}
                if len(self.keys_held & arrows)==0:
                    car.vx=0.0; car.vy=0.0

        elif e.type==pygame.MOUSEBUTTONDOWN and e.button==3:
            if self.selected_group=='car':
                car=self.cars[self.sel_index]; car.set_goto(e.pos)

    # Physics
    def _avoid_overlap(self, i:int, nx:float, ny:float) -> Tuple[float,float]:
        for j,other in enumerate(self.cars):
            if j==i: continue
            dx=nx-other.x; dy=ny-other.y
            d=math.hypot(dx,dy)
            if d < SAFE_DIST:
                if d==0: dx,dy=1.0,0.0; d=1.0
                push=(SAFE_DIST - d) + 1.0
                nx += (dx/d)*push
                ny += (dy/d)*push
        margin=CAR_R+4
        nx=min(W-margin, max(margin, nx))
        ny=min(H-margin, max(margin, ny))
        return nx,ny

    def _update_exit_logic(self, car:"Car", dt:float):
        if car.bounce_t > 0:
            before=car.bounce_t
            car.bounce_t = max(0.0, car.bounce_t - dt)
            if before>0 and car.bounce_t==0.0:
                car.vx=0.0; car.vy=0.0
            return
        for bay in (self.exitA, self.exitB):
            if bay.cargo is not None:
                if bay.cargo.kind == bay.kind:
                    bay.cargo = None
                    self.delivered[bay.kind]+=1
                else:
                    bay.cargo = None

    def update(self, dt:float):
        # Force-stop all non-selected cars (strict focus)
        for idx,c in enumerate(self.cars):
            if not (self.selected_group=='car' and idx==self.sel_index):
                if c.mode=='manual' and c.bounce_t<=0:
                    c.vx=0.0; c.vy=0.0

        # Handle selected car input and goto
        for idx,c in enumerate(self.cars):
            if self.selected_group=='car' and idx==self.sel_index:
                vx=vy=0.0
                if pygame.K_LEFT in self.keys_held:  vx -= 1
                if pygame.K_RIGHT in self.keys_held: vx += 1
                if pygame.K_UP in self.keys_held:    vy -= 1
                if pygame.K_DOWN in self.keys_held:  vy += 1
                arrows_held = (vx!=0 or vy!=0)
                if arrows_held:
                    norm=(vx**2+vy**2)**0.5; vx/=norm; vy/=norm
                    c.vx, c.vy = vx, vy
                    c.heading = math.atan2(vy, vx)
                    c.mode='manual'; c.goto=None
                else:
                    if c.bounce_t<=0 and c.mode=='manual':
                        c.vx=0.0; c.vy=0.0
            if c.mode=='goto' and c.goto is not None:
                dx=c.goto[0]-c.x; dy=c.goto[1]-c.y
                dist=math.hypot(dx,dy)
                if dist < 6:
                    c.mode='manual'; c.goto=None; c.vx=c.vy=0.0
                else:
                    c.vx, c.vy = dx/dist, dy/dist
                    c.heading = math.atan2(c.vy, c.vx)

        # Integrate movement with avoidance
        for i,c in enumerate(self.cars):
            sp=SPEEDS[c.speed_mode]
            if c.bounce_t>0: sp*=0.85
            nx=c.x + c.vx*sp*dt
            ny=c.y + c.vy*sp*dt
            nx,ny = self._avoid_overlap(i, nx, ny)
            c.x,c.y = nx,ny
            self._update_exit_logic(c, dt)

    # Draw
    def draw(self, screen: pygame.Surface):
        screen.fill(COL_BG)
        pygame.draw.rect(screen, COL_ZONE, pygame.Rect(40, 120, W-80, H-240), border_radius=18)
        self.exitA.draw(screen); self.exitB.draw(screen)
        for i,arm in enumerate(self.arms):
            arm.draw(screen, selected=(self.selected_group=='arm' and self.sel_index==i))
        for i,car in enumerate(self.cars):
            car.draw(screen, selected=(self.selected_group=='car' and self.sel_index==i))
        self._draw_hud(screen)

    def _draw_hud(self, screen: pygame.Surface):
        panel=pygame.Surface((W,34), pygame.SRCALPHA); panel.fill(COL_PANEL); screen.blit(panel,(0,0))
        font=pygame.font.SysFont("Consolas,Menlo,Courier New,Arial", 18)
        if self.selected_group=='car':
            car=self.cars[self.sel_index]
            cargo=f"{car.cargo.t_id}-{car.cargo.idx}{car.cargo.kind}" if car.cargo else "none"
            # left=f"Scene: Port Free-Move v9c | Agent: car-{car.idx} speed={car.speed_mode} | Cargo: {cargo}"
            left=f"Scene: Port Free-Move v9c | Agent: car-{car.idx} | Cargo: {cargo}"
        else:
            arm=self.arms[self.sel_index]; qa=sum(1 for c in arm.queue if c.kind=='A'); qb=sum(1 for c in arm.queue if c.kind=='B')
            # left=f"Scene: Port Free-Move v9c | Agent: {arm.name} | Queue A:{qa} B:{qb} (A/B choose type, SPACE queue)"
            left=f"Scene: Port Free-Move v9c | Agent: {arm.name} | Queue A:{qa} B:{qb}"
        screen.blit(font.render(left, True, COL_TEXT), (16,6))

        d=font.render(f"Delivered A:{self.delivered.get('A',0)}  B:{self.delivered.get('B',0)}", True, COL_TEXT)
        screen.blit(d, (W//2 + d.get_width()//2, 6))

# ---------------------------- Main ----------------------------
def main():
    pygame.init()
    pygame.display.set_caption("HAROS • Port Logistics Free-Move v9c")
    screen=pygame.display.set_mode((W,H), pygame.SCALED|pygame.RESIZABLE)
    clock=pygame.time.Clock()
    sc=Scene(); last=time.perf_counter(); run=True
    while run:
        now=time.perf_counter(); dt=now-last; last=now
        for e in pygame.event.get():
            if e.type==pygame.QUIT: run=False
            elif e.type==pygame.VIDEORESIZE: pass
            else: sc.handle_event(e)
        sc.update(dt); sc.draw(screen); pygame.display.flip(); clock.tick(FPS)
    pygame.quit()

if __name__=="__main__":
    main()
