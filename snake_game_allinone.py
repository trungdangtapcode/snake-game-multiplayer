import numpy as np
import pygame
import pickle
import copy
import math
from collections import deque
import csv
import socket
import _thread
import threading
import uuid
YOUR_IP = "172.172.4.250"
YOUR_NAME = "sus"
JOIN_IP = "172.172.4.250"

#PATTERNS
config = {
    "width": 720,
    "height": 480,
    "screen_width": 720,
    "screen_height": 480,
    "FPS": 60,
    "tile_size": 40,
    "default_tile_size": 40,
    "client_time_refresh": 1 #doi khi la ca server =))
}
delta_time = 10**-6
FPS = config["FPS"]

class Game:
    def __init__(self, debug = False):
        self.debug = debug
        pygame.init()
        self.window = None
        if (not debug): 
            pygame.display.set_caption('Con ran nhung ko phai Taylor')
            self.window = pygame.display.set_mode((config["width"],config["height"]))
        self.clock = pygame.time.Clock()
        self.events = []

    def run(self):
        display = 0 if self.debug else 1
        # self.level = Level(self.window)
        self.level = MenuScreen(self.window)
        # self.level = LobbyScreen(self.window)

        isRun = True
        while isRun:
            self.events = pygame.event.get()
            for event in self.events:
                if (event.type == pygame.QUIT):
                    isRun = False
            global delta_time, FPS
            delta_time = self.clock.tick(config["FPS"])/1000
            FPS = self.clock.get_fps()
            if (display == 1): self.window.fill('black')
            self.level.update(display)
            if (display == 1): pygame.display.update()
    
    def play(self, player_id = 0, isMultiplayer = False, isHost = False, server = None, network = None, num_player = 4):
        self.level = Level(self.window, player_id, isMultiplayer, isHost, server, network, num_player)
    
    def menu(self):
        self.level = MenuScreen(self.window)
    
    def lobby(self):
        self.level = LobbyScreen(self.window)

class Level:
    def __init__(self, screen, player_id = 0, isMultiplayer = False, isHost = False, server = None, network = None, num_player = 4):
        self.screen = screen
        self.load_level_data()
        self.obstacle_tiles = copy.deepcopy(self.walls)
        if (not isMultiplayer): self.max_snakes = 1
        else: self.max_snakes = num_player
        self.snakes = [Snake(self.obstacle_tiles, self.foods, self.snake_pos[i], 0) for i in range(self.max_snakes)]
        self.camera_pos = pygame.math.Vector2(config["screen_width"],config["screen_height"])/2
        self.playable_id = player_id

        self.isMulplayer = isMultiplayer
        self.isHost = isHost
        self.server = server
        self.network = network
        self.get_name_list_current_time = 0
        self.get_name_list_return = ['']*self.max_snakes
        self.update_multiplayer_client_current_time = 0

    def load_level_data(self):
        self.walls = [pygame.math.Vector2(3,3)]
        self.foods = []
        self.max_food = 2
        self.snake_pos = []
        path = 'level_data.csv'
        layout = np.array(filekit.import_csv_layout(path))
        layout = layout.T
        for row_index, row in enumerate(layout):
            for col_index, col in enumerate(row):
                x = int(col)
                pos = pygame.math.Vector2(row_index,col_index)
                if (x==0): continue
                if (x==-1):
                    self.snake_pos.append(pos)
                if (x==1):
                    self.walls.append(pos)
        self.max_snakes = len(self.snake_pos)
        self.level_max_height = len(layout)
        self.level_max_width = len(layout[0])

    def update(self, display):
        # x = pygame.time.get_ticks()s #
        for i in range(self.max_snakes): self.snakes[i].core.playable = 0
        self.snakes[self.playable_id].core.playable = 1
        self.update_obstacles()
        if (not self.isMulplayer or self.isHost): self.update_foods()
        self.update_keyboard()
        # print('1',pygame.time.get_ticks()-x) #
        # x = pygame.time.get_ticks()
        #THIS SO FUCKING LAGGGGGGG
        for snake in self.snakes:
            snake.update(display)
        if (display): self.draw()
        # print('2',pygame.time.get_ticks()-x) #
        # x = pygame.time.get_ticks()
        self.camera_pos = self.snakes[self.playable_id].core.pos_tile
        keys = pygame.key.get_pressed()
        if (keys[pygame.K_r]):
            self.snake_reset()
        if (keys[pygame.K_ESCAPE]):
            self.quit_level()
        # print('3',pygame.time.get_ticks()-x) #
        x = pygame.time.get_ticks()
        if self.isMulplayer:
            if (self.isHost): self.update_multiplayer_host()
            else: self.update_multiplayer_client()
        # print('4',pygame.time.get_ticks()-x) #

        # print('======================')
        # for idx, snake in enumerate(self.snakes):
        #     print(f'snake {idx} is at {snake.core.pos_tile} dead = {snake.core.is_dead}')

    def update_multiplayer_host(self):
        pass

    def update_multiplayer_client(self):
        "send data, receive and update"
        self.update_multiplayer_client_current_time += delta_time
        if (self.update_multiplayer_client_current_time < config["client_time_refresh"]): return
        def __new_thread():
            # data = self.network.send(self.snakes[self.playable_id].core) #much memory
            data = self.network.send(self.snakes[self.playable_id].core.get_zip())
            self.foods.clear()
            for x in data['foods']: self.foods.append(x)
            for idx, x in enumerate(data['cores']):
                self.snakes[idx].core.set_zip(x)
        _thread.start_new_thread(__new_thread, ())
        self.update_multiplayer_client_current_time = 0

    def update_obstacles(self):
        self.obstacle_tiles.clear()
        self.obstacle_tiles.extend(self.walls)
        for snake in self.snakes:
            if snake.core.is_dead: continue
            self.obstacle_tiles.extend(snake.core.body_pos)

    def update_foods(self):
        #generate new food
        while (len(self.foods)<self.max_food):
            pos = np.random.randint(self.level_max_height), np.random.randint(self.level_max_width)
            pos = pygame.math.Vector2(pos)
            if (pos in self.foods or pos in self.obstacle_tiles): continue
            self.foods.append(pos)

    def update_keyboard(self):
        keys = pygame.key.get_pressed()
        #zoom in/zoom out
        if (keys[pygame.K_MINUS] and config["tile_size"] > 16):
            config["tile_size"] -= 1
        if (keys[pygame.K_EQUALS] and config["tile_size"] < 100):
            config["tile_size"] += 1

    def snake_reset(self, id = None):
        if (id==None): id = self.playable_id
        self.snakes[id] = Snake(self.obstacle_tiles, self.foods, self.snake_pos[id], id==self.playable_id)

    def draw_deadscreen(self):
        #tranfer blur screen
        snake = self.snakes[self.playable_id]
        if (not snake.core.is_dead): return
        ratio = snake.graphic.current_time_deadscreen/snake.graphic.time_deadscreen
        max_blur = 10
        radius = 1 + ratio*(max_blur-1)
        gamekit.gaussian_blur(self.screen,radius)

        #then print lose text
        if (ratio>=0.8):
            TEXT = Text("Loser :D", 35, "White", center = (config["screen_width"]/2,150))
            self.draw_sprite_absolute(TEXT)
            BUTTON = Button(margin = 30, center = (config["screen_width"]/2, 300), 
                text_input= "MENU", font=gamekit.get_font(18), base_color="White", hovering_color="Gray")
            BUTTON.update(self.screen)
            for event in game.events: 
                if event.type != pygame.MOUSEBUTTONDOWN: continue
                if not BUTTON.checkForInput(pygame.mouse.get_pos()): continue
                self.quit_level()

    def quit_level(self):
        if (self.isMulplayer):
            if (self.isHost): self.server.kill()
            else: self.network.kill()
        game.menu()

    def get_name_list(self): #multithread
        self.get_name_list_current_time += delta_time
        if (self.get_name_list_current_time>config["client_time_refresh"]):
            def __new_thread():
                if (self.isHost):
                    self.get_name_list_return = self.server.name_list
                else: self.get_name_list_return = self.network.send('get name list')
            _thread.start_new_thread(__new_thread, ())
            self.get_name_list_current_time = 0
        return self.get_name_list_return

    def draw(self):
        for snake in self.snakes:
            self.draw_snake(snake)

        for wall in self.walls:
            pos = wall*config["tile_size"]
            self.draw_sprite(Wall_graphic(pos))
        
        for food in self.foods:
            pos = food*config["tile_size"]
            self.draw_sprite(Food_graphic(pos))

        #draw name
        if (self.isMulplayer):
            name_list = self.get_name_list()
            for idx, (snake, name) in enumerate(zip(self.snakes, name_list)):
                name_text = Text(text = name, size = 10, color = 'Green' if idx==self.playable_id else 'White', 
                            center = snake.core.pos_tile*config["tile_size"]-config["tile_size"]*pygame.math.Vector2(-.5,0.6))
                self.draw_sprite(name_text)

        self.draw_ui()
        self.draw_deadscreen()

    def draw_sprite(self, sprite):
        camera_offset = self.camera_pos*config["tile_size"]-pygame.math.Vector2(config["screen_width"],config["screen_height"])/2
        pos = sprite.rect.topleft-camera_offset
        self.screen.blit(sprite.image, pos)

    def draw_sprite_absolute(self, sprite):
        self.screen.blit(sprite.image, sprite.rect)

    def draw_snake(self, snake):
        for sprite in snake.graphic.snake_body:
            self.draw_sprite(sprite)

    def draw_ui(self):
        #score
        max_length = 4
        if (self.isMulplayer):
            name_list = self.get_name_list()
            assert name_list != None, "Name list dang la NONE!"
            for idx in range(self.max_snakes):
                s = str(self.snakes[idx].core.score)
                SCORE_TEXT = Text(text = name_list[idx] + ': '+'0'*(max_length-len(s)) + s, size = 15, color = "White", topleft = (10,10+idx*20))
                self.draw_sprite_absolute(SCORE_TEXT)
        else:
            s = str(self.snakes[self.playable_id].core.score)
            SCORE_TEXT = Text(text = 'SCORE: '+'0'*(max_length-len(s)) + s, size = 15, color = "White", topleft = (10,10))
            self.draw_sprite_absolute(SCORE_TEXT)
        FPS_TEXT = Text(text = str(int(FPS)), size = 15, color = "White", topleft = (config["screen_width"]-100,10))
        self.draw_sprite_absolute(FPS_TEXT)

class Wall_graphic:
    def __init__(self, tile_pos):
        self.image = pygame.Surface((config["tile_size"], config["tile_size"]))
        self.image.fill((80, 80, 80))
        self.rect = self.image.get_rect(topleft = tile_pos)

class Food_graphic:
    def __init__(self, tile_pos):
        self.image = pygame.Surface((config["tile_size"], config["tile_size"]))
        self.image.fill((0, 200, 200))
        self.rect = self.image.get_rect(topleft = tile_pos)

class Snake:
    def __init__(self, obstacle_tiles, food_tiles, init_pos, playable = True):
        self.core = Snake_core(obstacle_tiles,food_tiles, init_pos,playable)
        self.graphic = Snake_graphic(self.core)
    
    def update(self, display):
        self.core.update()
        if (display): self.graphic.update()

class Snake_graphic:
    def __init__(self, core):
        self.core = core
        self.load_data()
        self.snake_body = []
        self.current_time_deadframe = 0
        self.current_index_deadbody = 2
        self.current_time_deadscreen = 0
    def load_data(self):
        self.dead_framerate = 12
        self.time_deadscreen = 3

    def update(self):
        head = self.core.pos_tile
        tail = head
        #if snake length not 1
        if (len(self.core.body_pos)>1):
            tail = copy.deepcopy(self.core.body_pos[0])
            vector_ratio = (head-self.core.body_pos[-1]).magnitude()
            tail += vector_ratio*(self.core.body_pos[1]-self.core.body_pos[0])
        #add to rendering list
        self.snake_body = [Snake_graphic_body(tile_pos*config["tile_size"]) for tile_pos in self.core.body_pos]
        self.snake_body[0] = Snake_graphic_body(tail*config["tile_size"])
        self.snake_body.append(Snake_graphic_body(head*config["tile_size"]))
        #crop
        self.update_dead()
        self.snake_body[-1].image = gamekit.surface_crop_intersect_proper(
            self.snake_body[-1].image,
            self.snake_body[-1].rect, self.snake_body[-2].rect)
        self.snake_body[0].image = gamekit.surface_crop_intersect_proper(
            self.snake_body[0].image,
            self.snake_body[0].rect, self.snake_body[1].rect)

    def update_dead(self):
        #update time
        if (not self.core.is_dead): return 
        self.current_time_deadframe += delta_time
        self.current_time_deadscreen += delta_time
        self.current_time_deadscreen = min(self.current_time_deadscreen,self.time_deadscreen)
        #clock TICK!
        if (self.current_time_deadframe>=1/self.dead_framerate):
            self.current_index_deadbody += 1
            self.current_time_deadframe = 0
        #draw the red
        for i in range(len(self.snake_body)-1,max(len(self.snake_body)-1-self.current_index_deadbody,-1),-1):
            self.snake_body[i].kill_body()
    
class Snake_graphic_body:
    def __init__(self, tile_pos):
        self.image = pygame.Surface((config["tile_size"], config["tile_size"]))
        self.image.fill((255, 255, 0))
        self.rect = self.image.get_rect(topleft = tile_pos)
    
    def kill_body(self):
        self.image.fill((255, 0, 0))
        self.image.set_alpha(100)

class Snake_core:
    def __init__(self, obstacle_tiles, food_tiles, init_pos, playable):
        self.direction = pygame.math.Vector2(1,0)
        self.tile_direction = pygame.math.Vector2(1,0)
        self.load_data()
        self.pos_tile = copy.deepcopy(init_pos)
        self.tile = round(self.pos_tile)
        self.available_hit_tile = 0
        self.body_pos = deque([self.tile,self.tile,self.tile]) #front = head >body> back = tail
        self.obstacle_tiles = obstacle_tiles
        self.food_tiles = food_tiles
        self.is_dead = False
        self.playable = playable
        self.hit_right, self.hit_left, self.hit_up, self.hit_down = False, False, False, False
        self.hit_sprint = False
        self.score = 0

    def load_data(self):
        self.speed = 6
        self.sprint_speed = 10
        self.dist_to_hit_tile = 0.1

    def update(self):
        if (self.is_dead): return
        if (self.playable): self.update_input_keyboard()
        self.update_tile_direct()
        self.update_position()
        self.update_collision()

    def update_tile_direct(self):
        new_direct = None
        if (self.hit_right):
            new_direct = pygame.math.Vector2(1,0)
        if (self.hit_left):
            new_direct = pygame.math.Vector2(-1,0)
        if (self.hit_up):
            new_direct = pygame.math.Vector2(0,-1)
        if (self.hit_down):
            new_direct = pygame.math.Vector2(0,1)
        if (new_direct and new_direct!=-self.direction):
            self.tile_direction = new_direct
    
    def update_input_keyboard(self):
        "playable only"
        keys = pygame.key.get_pressed()
        self.hit_right = (keys[pygame.K_d] or keys[pygame.K_RIGHT])
        self.hit_left = (keys[pygame.K_a] or keys[pygame.K_LEFT])
        self.hit_up = (keys[pygame.K_w] or keys[pygame.K_UP])
        self.hit_down = (keys[pygame.K_s] or keys[pygame.K_DOWN])
        self.hit_sprint = keys[pygame.K_LSHIFT]

    def update_input_controll(self):
        "for AI controll (etc. reinformcent)"
        pass

    def update_position(self):
        #new position
        speed = self.sprint_speed if self.hit_sprint else self.speed 
        self.pos_tile += speed*delta_time*self.direction
        self.tile = round(self.pos_tile)
        
        #get to tile
        if mathkit.vector_close(self.pos_tile,self.tile,self.dist_to_hit_tile) and self.available_hit_tile<=0:
            self.pos_tile = self.tile
            self.direction = self.tile_direction
            self.body_pos.append(mathkit.vector_round(self.tile)) #not need copy
            self.body_pos.popleft()
            self.available_hit_tile = 1
        elif not mathkit.vector_close(self.pos_tile,self.tile,1.5*self.dist_to_hit_tile): 
            self.available_hit_tile = -1
        
    def update_collision(self):
        #hit the wall,...
        for tile in self.obstacle_tiles:
            if not mathkit.rect11_collide(self.pos_tile,tile) or tile==self.body_pos[-1]: continue
            if len(self.body_pos)>1 and tile==self.body_pos[-2]: continue
            self.is_dead = True
        
        #eat food
        for idx in range(len(self.food_tiles)-1,-1,-1):
            tile = self.food_tiles[idx]
            if not mathkit.rect11_collide(self.pos_tile,tile) or tile==self.body_pos[-1]: continue
            self.body_pos.appendleft(self.body_pos[0])
            self.food_tiles.pop(idx)
            self.score += np.random.randint(10,15)

    def get_zip(self):
        dic = {}
        dic['body_pos'] = self.body_pos
        dic['pos_tile'] = self.pos_tile
        dic['tile_direction'] = self.tile_direction
        dic['direction'] = self.direction
        dic['is_dead'] = self.is_dead
        dic['available_hit_tile'] = self.available_hit_tile
        return dic
    
    def set_zip(self, dic):
        self.body_pos = dic['body_pos']
        self.pos_tile = dic['pos_tile']
        self.tile_direction = dic['tile_direction']
        self.direction = dic['direction']
        self.is_dead = dic['is_dead']
        self.available_hit_tile = dic['available_hit_tile']

class mathkit:
    def vector_close(a, b, eps = 1):
        diff = (a-b)
        return diff.magnitude()<eps
    
    def vector_floor(a):
        return pygame.math.Vector2(int(a.x),int(a.y))

    def vector_round(a):
        return pygame.math.Vector2(round(a.x),round(a.y))
    
    def rect11_collide(a, b):
        return a.x<b.x+1 and b.x<a.x+1 and a.y<b.y+1 and b.y<a.y+1

class filekit:
    def import_csv_layout(path):
        terrain_map = []
        with open(path) as level_map:
            layout = csv.reader(level_map,delimiter = ',')
            for row in layout:
                terrain_map.append(list(row))
            return terrain_map

class gamekit:
    def surface_crop(image, pos, size):
        cropped_image = pygame.Surface(image.get_size(),pygame.SRCALPHA)
        subsurface =  image.subsurface(pos,size)
        cropped_image.blit(subsurface, pos)
        return cropped_image

    def surface_crop_margin(image, top, left, bottom, right):
        top = min(max(top,0), image.get_rect().h)
        left = min(max(left, 0), image.get_rect().w)
        bottom = max(min(bottom,image.get_rect().h-top), 0)
        right = max(min(right,image.get_rect().w-left), 0)
        width = image.get_rect().w-left-right
        height = image.get_rect().h-top-bottom
        return gamekit.surface_crop(image, (left, top), (width, height)) 

    def surface_crop_intersect_proper(image, rect1, rect2):
        top, left, bottom, right = 0,0,0,0
        if rect1.y==rect2.y:
            if rect2.x>rect1.x:
                right = -rect2.left+rect1.right
                right *= 1
            else: left = rect2.right-rect1.left
        if rect1.x==rect2.x:
            if rect2.y>rect1.y:
                bottom = -rect2.top+rect1.bottom
            else: top = rect2.bottom-rect1.top
        return gamekit.surface_crop_margin(image, top, left, bottom, right)

    def get_font(size):
        return pygame.font.Font('font.ttf', size)
    
    def gaussian_blur(surface, radius):
        scaled_surface = pygame.transform.smoothscale(surface, (surface.get_width() // radius, surface.get_height() // radius))
        scaled_surface = pygame.transform.smoothscale(scaled_surface, (surface.get_width(), surface.get_height()))
        surface.fill('black')
        surface.blit(scaled_surface, (0,0))

class MenuScreen:
    def __init__(self, screen):
        self.screen = screen
    
    def update(self, display):
        if (not display): 
            game.play()
            return
        half_w = config["screen_width"]/2
        PLAY_TEXT = Text("Xin chao XD", 15, "White", center = (half_w, 100))
        SINGLEPLAYER_BUTTON = Button(margin = 10, bg_color = (100,100,100), center = (half_w, 200), 
                            text_input="SINGLEPLAYER", font=gamekit.get_font(15), base_color="#d7fcd4", hovering_color="Green")
        MULTIPLAYER_BUTTON = Button(margin = 10, bg_color = (100,100,100), center = (half_w, 250), 
                            text_input="MULTIPLAYER", font=gamekit.get_font(15), base_color="#d7fcd4", hovering_color="Green")

        self.draw_prite(PLAY_TEXT)
        self.draw_button(SINGLEPLAYER_BUTTON)
        self.draw_button(MULTIPLAYER_BUTTON)

        mouse = pygame.mouse.get_pos()
        for event in game.events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if SINGLEPLAYER_BUTTON.checkForInput(mouse):
                    game.play()
                if MULTIPLAYER_BUTTON.checkForInput(mouse):
                    game.lobby()

    def draw_prite(self, sprite):
        self.screen.blit(sprite.image, sprite.rect)

    def draw_button(self, button):
        button.update(self.screen)
        
class Text:
    def __init__(self, text, size, color = "Red", center = None, topleft = None):
        self.image = gamekit.get_font(size).render(text, False, color)
        if (center!=None):
            self.rect = self.image.get_rect(center = center)
        elif (topleft!=None):
            self.rect = self.image.get_rect(topleft = topleft)
        else: raise Exception("Dm topleft hay center")

class Button:
    def __init__(self, center, text_input, font, base_color, hovering_color,
                    image = None, bg_color = None, margin = 0):
        self.image = image
        self.font = font
        self.base_color, self.hovering_color = base_color, hovering_color
        self.text_input = text_input
        self.text = self.font.render(self.text_input, True, self.base_color)
        #image -> bg 1 color -> none 
        if self.image is None:
            if bg_color is None:
                self.image = pygame.Surface(self.text.get_size()+pygame.math.Vector2(margin, margin), pygame.SRCALPHA)
            else:
                self.image = pygame.Surface(self.text.get_size()+pygame.math.Vector2(margin, margin))
                self.image.fill(bg_color)
        self.rect = self.image.get_rect(center=center)
        self.text_rect = self.text.get_rect(center=center)

    def update(self, screen):
        mouse = pygame.mouse.get_pos()
        self.changeColor(mouse)
        if self.image is not None:
            screen.blit(self.image, self.rect)
        screen.blit(self.text, self.text_rect)

    def checkForInput(self, position):
        if position[0] in range(self.rect.left, self.rect.right) and position[1] in range(self.rect.top, self.rect.bottom):
            return True
        return False

    def changeColor(self, position):
        if position[0] in range(self.rect.left, self.rect.right) and position[1] in range(self.rect.top, self.rect.bottom):
            self.text = self.font.render(self.text_input, True, self.hovering_color)
        else:
            self.text = self.font.render(self.text_input, True, self.base_color)

class LobbyScreen:
    def __init__(self, screen):
        self.screen = screen
        self.room_ip = False
        self.is_host = False
        self.is_inRoom = False
        self.server = None
        self.network = None
        self.level_config = None #dict

        self.get_player_list_current_time = 0
        self.get_player_list_return = []
        self.ask_started_yet_current_time = 0
        self.ask_started_yet_return = False

    def show_rooms(self):
        "show all rooms available"
        LOBBY_TEXT = Text(text = "Multiplayer", size = 15, color = "White", center = (config["screen_width"]/2,50))
        self.draw_sprite(LOBBY_TEXT)
        CREATE_BUTTON = Button(margin = 20, bg_color = (100,100,100), center = (config["screen_width"]/2, 200), 
                text_input="CREATE", font=gamekit.get_font(20), base_color="#d7fcd4", hovering_color="Green")
        CREATE_BUTTON.update(self.screen)
        JOIN_BUTTON = Button(margin = 20, bg_color = (100,100,100), center = (config["screen_width"]/2, 300), 
                text_input="JOIN", font=gamekit.get_font(20), base_color="#d7fcd4", hovering_color="Green")
        JOIN_BUTTON.update(self.screen)
        EXIT_BUTTON = Button(margin = 20, bg_color = (100,100,100), center = (config["screen_width"]/2, 400), 
                text_input="EXIT", font=gamekit.get_font(20), base_color="#d7fcd4", hovering_color="Green")
        EXIT_BUTTON.update(self.screen)

        for event in game.events:
            if (event.type!=pygame.MOUSEBUTTONDOWN): continue
            if CREATE_BUTTON.checkForInput(pygame.mouse.get_pos()):
                self.create_room()
            if JOIN_BUTTON.checkForInput(pygame.mouse.get_pos()):
                # host = input('host: ')
                # port = int(input('port: '))
                host = JOIN_IP
                port = 5555
                addr = (host, port)
                self.join_room(addr)
            if EXIT_BUTTON.checkForInput(pygame.mouse.get_pos()):
                game.menu()

    def get_player_list(self):
        self.get_player_list_current_time += delta_time
        if (self.get_player_list_current_time > config["client_time_refresh"]): 
            def __new_thread():
                if (self.is_host):
                    x = [self.server.name_list[x]+' '+str(self.server.addr_list[x]) for x in range(len(self.server.addr_list))]
                else:
                    x = self.network.send('get player list in lobby')
                    if (x==None):
                        self.leave_room()
                self.get_player_list_return = x
            _thread.start_new_thread(__new_thread, ())
            self.get_player_list_current_time = 0
        return self.get_player_list_return
    
    def ask_started_yet(self):
        self.ask_started_yet_current_time += delta_time
        if (self.ask_started_yet_current_time > config["client_time_refresh"]):
            def __new_thread():
                self.ask_started_yet_return = self.network.send('game start yet')
            _thread.start_new_thread(__new_thread, ())
            self.get_player_list_current_time = 0
        return self.ask_started_yet_return
        
    def show_members(self):
        "in room already"
        PLAY_BUTTON = Button(margin = 20, bg_color = (100,100,100), center = (config["screen_width"]/6*5, 50), 
                            text_input="PLAY", font=gamekit.get_font(20), base_color="#d7fcd4", hovering_color="Green")
        BACK_BUTTON = Button(margin = 20, bg_color = (100,100,100), center = (config["screen_width"]/6, 50), 
                            text_input="BACK", font=gamekit.get_font(20), base_color="#d7fcd4", hovering_color="Green")
        if (self.is_host): PLAY_BUTTON.update(self.screen)
        BACK_BUTTON.update(self.screen)
        IP_TEXT = Text(text = "ROOM IP = " + self.room_ip, size = 15, color = "White", center = (config["screen_width"]/2,150))
        self.draw_sprite(IP_TEXT)

        for idx, addr in enumerate(self.get_player_list()):
            h_pos = 200 + idx*50
            player_text = Text(text = str(addr), size = 15, color = "White", center = (config["screen_width"]/2,h_pos))
            self.draw_sprite(player_text)

        for event in game.events:
            if (event.type!=pygame.MOUSEBUTTONDOWN): continue
            if PLAY_BUTTON.checkForInput(pygame.mouse.get_pos()):
                self.start_game()
            if BACK_BUTTON.checkForInput(pygame.mouse.get_pos()):
                self.leave_room()
        
        #self.is_inRoom because leave_room() run before
        if self.is_inRoom and not self.is_host:
            started = self.ask_started_yet()
            if (started):
                print("DUNG", started)
                self.start_game()

    def create_room(self):
        self.room_ip = YOUR_IP
        self.is_host = True
        self.is_inRoom = True
        self.server = Server()
        _thread.start_new_thread(self.server.open_request, ())
        
    def join_room(self, ip):
        self.room_ip = ip[0] #host
        self.is_host = False
        self.is_inRoom = True
        self.network = Network(ip)
        if (self.network.id == None): self.leave_room()
    
    def leave_room(self):
        if (self.is_host): self.server.kill()
        else: self.network.kill()
        self.room_ip = None
        self.is_host = False
        self.is_inRoom = False

    def start_game(self):
        if (self.is_host): 
            game.play(isMultiplayer = True, player_id = 0, isHost = self.is_host, server = self.server, network = self.network, num_player = len(self.get_player_list()))
            self.server.is_game_started = True
        else: game.play(isMultiplayer = True, player_id = self.network.id, isHost = self.is_host, server = self.server, network = self.network, num_player = len(self.get_player_list()))
    
    def update(self, display):
        if (not display): return
        if (self.is_inRoom):
            self.show_members()
        else: self.show_rooms()

    def draw_sprite(self, sprite):
        self.screen.blit(sprite.image, sprite.rect)

class Server:
    def __init__(self, name = YOUR_NAME):
        self.server = YOUR_IP
        self.port = 5555
        self.init_network()
        self.addr = (self.server, self.port)
        self.addr_list = [self.addr]
        self.conn_list = []
        self.name_list = [name]
        self.available_slot = list(range(1,4))
        self.run = True
        self.is_game_started = False

    def init_network(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.s.bind((self.server, self.port))
        except socket.error as e:
            print(e)
        self.s.listen()

    def open_request(self):
        "run this in another thread"
        while self.run:
            self.update()

    def send_all(self, data):
        "dont use :D"
        for conn in self.conn_list:
            conn.sendall(pickle.dumps(data))            

    def kill(self):
        self.run = False
        # self.s.shutdown(socket.SHUT_RDWR)
        self.s.close()
        for conn in self.conn_list:
            conn.close()

    def update(self):
        "call in private (self.open_request)"
        conn, addr = self.s.accept() 
        print("connected to: ", addr)
        if (len(self.available_slot)==0): return
        _thread.start_new_thread(self.threaded_client, (conn, addr,self.available_slot.pop(0)))
    
    def threaded_client(self, conn, addr, thread_player):
        "conn: obj, addr: tupple, thread_player = player_id"
        self.addr_list.append(addr) #client_socket.getpeername()
        self.conn_list.append(conn)
        self.name_list.append("")
        conn.send(pickle.dumps(thread_player))
        reply = ""
        while self.run:
            try:
                #SERVER LOGICC
                kernel_id, data = pickle.loads(conn.recv(4096))
                reply = data
                print("received ", data)
                if data == 'get player list in lobby':
                    reply = [self.name_list[x]+' '+str(self.addr_list[x]) for x in range(len(self.addr_list))]
                if data == 'get name list':
                    reply = self.name_list
                if data == 'game start yet':
                    reply = self.is_game_started
                if isinstance(data,tuple) and data[0]=='set name': #when client init connect (for the first time)
                    self.name_list[thread_player] = data[1]
                    reply = 'name seted'
                if isinstance(data, dict): #snake data
                    game.level.snakes[thread_player].core.set_zip(data)
                    reply = {}
                    reply['foods'] = game.level.foods
                    reply['cores'] = [x.core.get_zip() for x in game.level.snakes]
                if not data:
                    print('disconnected')
                    break
                print("sending ", reply)
            except:
                print("ERROR THREADED SERVER")
                break
            conn.sendall(pickle.dumps((kernel_id, reply)))
        print("connection closing")
        conn.close()
        self.addr_list.remove(addr)
        self.conn_list.remove(conn)

class Network:
    "for client"
    def __init__(self, addr, name = YOUR_NAME):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = addr #addr to server (host, port)
        self.id = self.connect()
        self.received = {}
        self.send(('set name',name))
        print('Connected, your id is ', self.id)

    def connect(self):
        "connect init"
        try:
            self.client.connect(self.addr)
            return pickle.loads(self.client.recv(4096))
        except socket.error as e:
            print('cant connect to server',e)
    
    def send(self, data):
        "send in multithread then make the that thread wait until kernel_id reply"
        try:
            kernel_id = uuid.uuid4()
            self.client.send(pickle.dumps((kernel_id,data)))
            x =  pickle.loads(self.client.recv(4096))
            self.received[x[0]] = x[1]
            while (kernel_id not in self.received):
                pass
            x = copy.deepcopy(self.received[kernel_id])
            del self.received[kernel_id]
            return x
        except socket.error as e:
            print(e)
    
    def kill(self):
        self.client.close()


game = Game(debug = False)
game.run()
