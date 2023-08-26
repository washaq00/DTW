gitimport pyaudio
import pygame
import os
import wave
import numpy as np
import matplotlib.pyplot as plt
import threading
pygame.font.init()
pygame.mixer.init()

class AudioConverter:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.params = {
            "format": pyaudio.paInt16,
            "channels": 1,
            "rate": 16000,
            "input": True,
            "output": False,
            "frames_per_buffer": 3200,
            "stream_callback" : None
        }
        self.audio_thread = threading.Thread()
        
    def __del__(self):
        self.stream.stop_stream()
        self.stream.close()  
        self.audio.terminate()

    def load(self, file_path):
        with wave.open(file_path, "rb") as wf:
            self.params["channels"] = wf.getnchannels()
            self.params["rate"] = wf.getframerate()
            self.params["format"] = self.audio.get_format_from_width(wf.getsampwidth())
            self.frames = wf.readframes(wf.getnframes())

    def save(self, file_path):
        if not self.frames:
            print("No audio in a buffer")
            return
        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(self.params["channels"])
            wf.setframerate(self.params["rate"])
            wf.setsampwidth(self.audio.get_sample_size(self.params["format"]))            
            wf.writeframes(self.frames)

    def play(self):
        self.params["input"] = False
        self.params["output"] = True
        self.stream = self.audio.open(**self.params)
        self.stream.write(self.frames)
    
    #Tak, powinno sie to zrobic z stream_callback ale nie chciało mi to działać więc poleciałem na pałę z threadami
    def play_other_thread(self):
        if self.audio_thread.is_alive():
            return
        self.audio_thread = threading.Thread(target=self.play)
        self.audio_thread.start()
        
    def record_other_thread(self, duration):
        if self.audio_thread.is_alive():
            return
        self.audio_thread = threading.Thread(target=self.record, args=(duration,))
        self.audio_thread.start()
    
    def record(self, duration):
        print("Recording...")
        frames = []
        self.params["input"] = True
        self.params["output"] = False
        stream = self.audio.open(**self.params)
        for i in range(0, int(self.params["rate"] / self.params["frames_per_buffer"] * duration)):
            frames.append(stream.read(self.params["frames_per_buffer"]))
        stream.stop_stream()
        stream.close()
        self.frames = b''.join(frames) #konwersja z listy na ciąg bytow

    def plot(self):
        signal = np.reshape(np.frombuffer(self.frames, dtype=np.int16), (-1, self.params["channels"]))
        time = np.arange(0, len(signal)) / self.params["rate"]
        for i in range(self.params["channels"]):
            plt.plot(time, signal[:, i])
        plt.title("Audio signal")
        plt.xlabel("Time [s]")
        plt.ylabel("Amplitude")
        plt.show()

recorder = AudioConverter()
recorder.load('test1.wav')

WINDOW_WIDTH, WINDOW_HEIGHT = 900, 500 # screen size
FPS = 60
IMG_WIDTH, IMG_HEIGHT = 50, 40
VELOCITY = 8
BULLET_VELOCITY = 10

WIN = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("DTW controlled game")

#loading
IMAGE = pygame.image.load(os.path.join('Assets', 'spaceship_red.png'));
IMAGE = pygame.transform.rotate(pygame.transform.scale(IMAGE, (IMG_WIDTH, IMG_HEIGHT)),180)
BACKGROUND_IMG = pygame.transform.scale(pygame.image.load(os.path.join('Assets', 'space.png')), (WINDOW_WIDTH, WINDOW_HEIGHT));
FIRE_SOUND = pygame.mixer.Sound(os.path.join('Assets', 'Gun+Silencer.mp3'))

#custom events
BULLET_OUT_OF_BOUNCE = pygame.USEREVENT + 1 #for testing

def draw_window(red, bullets, score):
    WIN.blit(BACKGROUND_IMG, (0, 0))
    font = pygame.font.SysFont('comicsans', 30)
    txt = font.render(f'Score: {score}', 1, pygame.Color("white"))
    WIN.blit(txt, (10, 10))
    if recorder.audio_thread.is_alive():
        txt = font.render('Processing audio...', 1, pygame.Color("white"))
    else:
        txt = font.render('Press "R" to play audio or "T" to record', 1, pygame.Color("white"))
    WIN.blit(txt, (10, 10 + font.get_height()))
    WIN.blit(IMAGE, (red.x, red.y))
    for bullet in bullets:
        pygame.draw.rect(WIN, pygame.Color("red"), bullet)
    pygame.display.update()

def handle_movement(player):
    keys_pressed = pygame.key.get_pressed()
    if keys_pressed[pygame.K_d] and player.x + VELOCITY < WINDOW_WIDTH - player.width: 
        player.x += VELOCITY
    if keys_pressed[pygame.K_a] and player.x - VELOCITY > 0:
        player.x -= VELOCITY
    if keys_pressed[pygame.K_w] and player.y - VELOCITY > 0:
        player.y -= VELOCITY
    if keys_pressed[pygame.K_s] and player.y + VELOCITY < WINDOW_HEIGHT - player.height:
        player.y += VELOCITY

def handle_bullets(bullets):
    for bullet in bullets:
        bullet.y -= BULLET_VELOCITY
        if bullet.y < 0:
            bullets.remove(bullet)
            pygame.event.post(pygame.event.Event(BULLET_OUT_OF_BOUNCE))
            
def print_opening_text(): # tak dla sportu napisana, bedzie do wywalenia potem
    txt = "Sterowanie WSAD\nSpacja strzal\nKlawisz R odpalenie audio\nT - nagraj glos"
    font = pygame.font.SysFont('comicsans', 60)
    words = [word.split(' ') for word in txt.splitlines(0)]
    space = font.size(' ')[0]
    x, y = (10, 10)
    for line in words:
        for word in line:
            word_surface = font.render(word, 0, pygame.Color("white"))
            word_width, word_height = word_surface.get_size()
            if x + word_width >= WINDOW_WIDTH:
                x = 10  
                y += word_height 
            WIN.blit(word_surface, (x, y))
            x += word_width + space
        x = 10 
        y += word_height 
    pygame.display.update()
    
def main():
    player = pygame.Rect(300, 200, IMG_WIDTH, IMG_HEIGHT)
    clock = pygame.time.Clock()
    running = True
    bullets = []
    score = 0
    close_menu = False
    print_opening_text()
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if close_menu == False:
                    close_menu = True
                if event.key == pygame.K_SPACE:
                    bullets.append(pygame.Rect(player.x + player.width/2 - 2, player.y, 4, 10))
                    FIRE_SOUND.play()
                if event.key == pygame.K_r:
                    recorder.play_other_thread()
                if event.key == pygame.K_t:
                    recorder.record_other_thread(3) #record for 3 sec
            if event.type == BULLET_OUT_OF_BOUNCE:
                score += 1
        if close_menu == False:
            continue
        handle_movement(player)
        handle_bullets(bullets)
        draw_window(player, bullets, score)
    pygame.quit()

if __name__ == "__main__":
    main()
