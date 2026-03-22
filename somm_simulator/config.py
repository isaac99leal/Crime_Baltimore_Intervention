"""Game configuration constants."""

# Display
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 30
GAME_TITLE = "Somm Simulator"

# Colors (elegant dark theme)
COLOR_BG = (18, 18, 24)
COLOR_BG_PANEL = (28, 28, 38)
COLOR_BG_PANEL_HOVER = (38, 38, 52)
COLOR_BG_PANEL_SELECTED = (48, 38, 42)
COLOR_TEXT = (235, 225, 210)           # Warm cream
COLOR_TEXT_DIM = (160, 150, 135)       # Muted
COLOR_TEXT_BRIGHT = (255, 248, 235)    # Bright cream
COLOR_ACCENT = (140, 30, 50)          # Burgundy/wine red
COLOR_ACCENT_LIGHT = (180, 60, 75)    # Lighter burgundy
COLOR_GOLD = (200, 170, 80)           # Gold for highlights
COLOR_SUCCESS = (70, 160, 90)
COLOR_WARNING = (200, 160, 50)
COLOR_DANGER = (180, 50, 50)
COLOR_BORDER = (60, 55, 65)
COLOR_SCROLLBAR = (80, 75, 85)

# Wine colors for display
WINE_COLOR_RED = (130, 20, 35)
WINE_COLOR_WHITE = (220, 200, 120)
WINE_COLOR_ROSE = (200, 120, 130)
WINE_COLOR_SPARKLING = (230, 220, 160)
WINE_COLOR_FORTIFIED = (100, 30, 20)
WINE_COLOR_DESSERT = (210, 180, 80)

# Font sizes
FONT_SIZE_TITLE = 36
FONT_SIZE_HEADING = 24
FONT_SIZE_BODY = 18
FONT_SIZE_SMALL = 14
FONT_SIZE_TINY = 12

# Game balance
STARTING_BUDGET = 15000.0
BASE_WINE_MARKUP = 3.0         # 3x wholesale cost
CELLAR_CAPACITY_START = 200    # Bottles
TABLES_START = 8
SERVICE_NIGHTS_PER_WEEK = 5

# Career thresholds
CAREER_STAGES = {
    "assistant_sommelier": {
        "title": "Assistant Sommelier",
        "wine_list_size": 50,
        "tables": 8,
        "reputation_needed": 0,
    },
    "sommelier": {
        "title": "Sommelier",
        "wine_list_size": 200,
        "tables": 15,
        "reputation_needed": 500,
    },
    "head_sommelier": {
        "title": "Head Sommelier",
        "wine_list_size": 500,
        "tables": 20,
        "reputation_needed": 2000,
    },
    "beverage_director": {
        "title": "Beverage Director",
        "wine_list_size": 1000,
        "tables": 30,
        "reputation_needed": 5000,
    },
}

# Tasting profile ranges
PROFILE_MIN = 1.0
PROFILE_MAX = 5.0

# Vintage range
OLDEST_VINTAGE = 1970
NEWEST_VINTAGE = 2023
