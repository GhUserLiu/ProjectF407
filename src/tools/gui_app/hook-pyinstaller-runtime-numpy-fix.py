"""
PyInstaller runtime hook to fix NumPy CPU dispatcher issues

This hook MUST run BEFORE any other code that might import NumPy.
It ensures NumPy is imported once and completely.

The issue: When multiple libraries (openpyxl, PIL, sklearn) import NumPy,
the CPU dispatcher gets initialized multiple times, causing:
"RuntimeError: CPU dispatcher tracer already initialized"

The fix: Import NumPy here, in the runtime hook, before any other imports.
"""

import os
import sys

print("[INFO] NumPy runtime hook - Starting initialization...")

# Step 1: Set environment variables FIRST
os.environ['NUMPY_ALLOW_CPU_FEATURES'] = '0'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'

# Step 2: Import NumPy IMMEDIATELY and COMPLETELY
# This prevents other libraries from partially initializing NumPy
try:
    # Force import of NumPy's critical modules
    import numpy
    import numpy._core
    import numpy._core.multiarray
    import numpy._core.umath

    # Verify NumPy is working
    _test = numpy.array([1, 2, 3])

    # Mark NumPy as fully initialized
    numpy._initialized = True

    print(f"[INFO] NumPy {numpy.__version__} imported successfully via runtime hook")
except Exception as e:
    print(f"[ERROR] NumPy import failed: {e}", file=sys.stderr)
    # Don't crash - let the application handle missing NumPy

print("[INFO] NumPy runtime hook completed")
