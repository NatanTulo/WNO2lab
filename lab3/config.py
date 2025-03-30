from PyQt5.QtGui import QColor

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# Ustawienia komórek
DEFAULT_CELL_RADIUS = 30
POINTS_PER_STRENGTH = 10

# Kolory komórek
COLOR_PLAYER = QColor(0, 200, 100)
COLOR_ENEMY = QColor(200, 50, 50)
COLOR_NEUTRAL = QColor(200, 150, 0)

# Ustawienia przycisku przełącznika
SWITCH_BUTTON_WIDTH = 60
SWITCH_BUTTON_HEIGHT = 30
COLOR_SWITCH_ON = QColor(0, 150, 136)
COLOR_SWITCH_OFF = QColor(200, 200, 200)

# Ustawienia menu
MENU_TITLE_FONT_SIZE = 36
MENU_LEVEL_TITLE_FONT_SIZE = 24
MENU_SWITCH_LABEL_FONT_SIZE = 16
MENU_TITLE_Y_POSITION = 100
MENU_LEVEL_BUTTON_WIDTH = 300

# Ustawienia sceny gry
FRAME_INTERVAL_MS = 16
POINTS_INTERVAL_MS = 2000
TURN_TIMER_INTERVAL_MS = 1000
TURN_DURATION_SECONDS = 10

# Ustawienia edytora
EDITOR_GRID_SIZE = 50

# Dodane ustawienia czcionek
FONT_FAMILY = "Arial"
BUTTON_FONT_SIZE = 14
EDITOR_TITLE_FONT_SIZE = 24
EDITOR_SUBTITLE_FONT_SIZE = 16
EDITOR_INSTRUCTION_FONT_SIZE = 12
GAME_TURN_FONT_SIZE = 16
GAME_OVER_FONT_SIZE = 36

FREEZE_DURATION_SECONDS = 10  # Czas trwania zamrożenia w sekundach

# Dodane stałe powerupów
POWERUP_FREEZE = "mrożący"
POWERUP_TAKEOVER = "przejmujący"
POWERUP_ADD_POINTS = "punktujący"
POWERUP_NEW_CELL = "stawiający"  # Nowy powerup do dodania nowej komórki

# Dodana stała określająca maksymalną odległość dla kopiowania komórki 
NEW_CELL_COPY_RANGE_FACTOR = 5  # Maksymalna odległość = 5 * promień komórki