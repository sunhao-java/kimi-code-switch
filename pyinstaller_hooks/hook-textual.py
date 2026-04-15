from PyInstaller.utils.hooks import collect_data_files, collect_submodules


# Textual widgets are loaded lazily via module-level __getattr__, which PyInstaller
# does not detect from static imports alone.
datas = collect_data_files("textual")
hiddenimports = collect_submodules("textual")
