"""
PyInstaller hook for NumPy

Ensures NumPy is bundled correctly with all its binary modules.
"""

from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    is_module_satisfies,
    get_module_file_attribute,
)
from PyInstaller.compat import is_win

import os

# Collect all NumPy submodules
hiddenimports = collect_submodules('numpy')

# Critical NumPy internal modules that must be included
hiddenimports += [
    'numpy._core',
    'numpy._core.multiarray',
    'numpy._core.umath',
    'numpy.core',
    'numpy.core.multiarray',
    'numpy.core.umath',
    'numpy.linalg',
    'numpy.linalg.lapack_lite',
    'numpy.fft',
    'numpy.polynomial',
    'numpy.random',
    'numpy.testing',
]

# Collect NumPy data files (includes any necessary DLLs)
datas = collect_data_files('numpy', include_py_files=False)

# On Windows, ensure MKL DLLs are included if available
if is_win:
    try:
        import numpy
        numpy_path = os.path.dirname(numpy.__file__)
        # Look for MKL DLLs in the NumPy directory
        mkl_dlls = [
            'mkl_core.dll',
            'mkl_intel_thread.dll',
            'mkl_rt.dll',
            'libiomp5md.dll',
        ]
        for dll in mkl_dlls:
            dll_path = os.path.join(numpy_path, '..', 'DLLs', dll)
            if os.path.exists(dll_path):
                datas.append((dll_path, '.'))
    except:
        pass
