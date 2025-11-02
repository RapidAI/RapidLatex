import os
import os

def _read_file(filename):
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, filename), encoding="utf-8") as f:
        return f.read().strip()

__version__ = _read_file("version.txt")
__author__ = _read_file("author.txt")
import appdata
app_paths = appdata.AppDataPaths('mathtranslate')
app_dir = app_paths.app_data_path
os.makedirs(app_dir, exist_ok=True)

import cache
import config
import translate
import tencentcloud
import encoding
import process_latex
import process_text
import update
import translate_tex
import translate_arxiv
from translate_tex import main as tex_main
from translate_arxiv import main as arxiv_main
