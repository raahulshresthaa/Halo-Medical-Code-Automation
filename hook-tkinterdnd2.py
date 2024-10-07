# hook-tkinterdnd2.py
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('tkinterdnd2')
# this is to handle the 'drag and drop' feature when exporting to an exe