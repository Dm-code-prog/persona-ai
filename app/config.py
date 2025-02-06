import os

from platformdirs import user_data_dir
from os.path import join

DATA_PATH = join(user_data_dir('persona_ai', ensure_exists=True), 'data')
MEDIA_PATH = join(user_data_dir('persona_ai', ensure_exists=True), 'data', 'media')
PROJECTS_PATH = join(MEDIA_PATH, 'projects')

os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(MEDIA_PATH, exist_ok=True)