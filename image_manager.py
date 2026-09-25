import pygame
import os

# Use the project's assets directory for images
_BASE_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "assets", "images")

# Map element names to image filenames
_ELEMENT_IMAGE_MAP = {
    "earth": "earth.png",
    "fire": "fire.png",
    "paper": "paper.png",
    "rock": "rock.png",
    "scissors": "scissors.png",
    "water": "water.png",
}

_LOADED_IMAGES = {}
_IMAGES_LOADED = False

def load_element_images():
    """Loads all element PNG images into memory. Must be called after pygame.display.set_mode()."""
    global _IMAGES_LOADED
    if _IMAGES_LOADED:
        return

    for element, filename in _ELEMENT_IMAGE_MAP.items():
        path = os.path.join(_BASE_IMAGE_PATH, filename)
        if os.path.exists(path):
            try:
                # Must have display initialized before convert_alpha()
                image = pygame.image.load(path).convert_alpha()
                _LOADED_IMAGES[element] = image
                print(f"Loaded image for {element} from {path}")
            except pygame.error as e:
                print(f"Could not load image {path}: {e}")
        else:
            print(f"Image file not found for {element} at {path}")
    _IMAGES_LOADED = True

def get_element_image(element, size=None):
    """Retrieves a loaded image, scaled to the desired size."""
    image = _LOADED_IMAGES.get(element)
    if image:
        if size:
            return pygame.transform.scale(image, (size, size))
        return image
    return None

def are_images_loaded():
    return _IMAGES_LOADED and len(_LOADED_IMAGES) == len(_ELEMENT_IMAGE_MAP)