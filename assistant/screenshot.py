from datetime import datetime
from pathlib import Path

from PIL import ImageGrab

from config import settings


def take_screenshot() -> Path:
    settings.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"print_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
    path = settings.SCREENSHOTS_DIR / filename
    image = ImageGrab.grab()
    image.save(path)
    return path
