"""
PyInstaller hook for PIL/Pillow to prevent NumPy conflicts

This hook ensures NumPy is imported before PIL tries to use it.
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect PIL submodules
hiddenimports = collect_submodules('PIL')

# Add NumPy as a hidden import for PIL (critical!)
# This ensures NumPy is bundled and available when PIL needs it
hiddenimports += [
    'numpy',
    'numpy._core',
    'numpy._core.multiarray',
    'numpy.core',
    'numpy.core.multiarray',
]

# Collect PIL data files (like fonts, etc)
datas = collect_data_files('PIL', include_py_files=False)
