import os
import sys

# Base application directory
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "overlay_viewer_config.json")
TEMP_IMG_DIR = os.path.join(BASE_DIR, "temp_images")