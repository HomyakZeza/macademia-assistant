import colorsys
from enum import Enum


class ColorCategory(str, Enum):
    NONE = "none"
    GRAY = "gray"
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    OTHER = "other"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 8:
        h = h[2:]
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def classify_color(hex_color: str | None) -> ColorCategory:
    if not hex_color:
        return ColorCategory.NONE

    try:
        r, g, b = _hex_to_rgb(hex_color)
    except (ValueError, IndexError):
        return ColorCategory.OTHER

    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    h_deg = h * 360
    s_pct = s * 100
    v_pct = v * 100

    # Белый
    if s_pct < 5 and v_pct > 95:
        return ColorCategory.NONE

    # Чёрный
    if v_pct < 5:
        return ColorCategory.NONE

    # Серый
    if s_pct < 8:
        return ColorCategory.GRAY

    # Красный
    if h_deg < 20 or h_deg >= 345:
        return ColorCategory.RED
    # Оранжевый
    if h_deg < 40:
        return ColorCategory.ORANGE
    # Желтый
    if h_deg < 80:
        return ColorCategory.YELLOW
    # Зеленый
    if h_deg < 170:
        return ColorCategory.GREEN
    #Голубой
    if h_deg < 260:
        return ColorCategory.BLUE

    return ColorCategory.OTHER


def describe(hex_color: str | None) -> str:
    return f"{hex_color!r:10} → {classify_color(hex_color).value}"