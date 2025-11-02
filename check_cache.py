import appdata
import os
paths = appdata.AppDataPaths('mathtranslate')
cache_dir = os.path.join(paths.app_data_path, 'cache')
print('Cache dir:', cache_dir)
print('Exists:', os.path.exists(cache_dir))
if os.path.exists(cache_dir):
    print('Contents:', os.listdir(cache_dir))