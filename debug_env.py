
import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"Python Path: {sys.path}")

try:
    import simpleui
    print(f"SimpleUI found at: {simpleui.__file__}")
except ImportError as e:
    print(f"Error importing simpleui: {e}")

try:
    import django
    print(f"Django found at: {django.__file__}")
except ImportError as e:
    print(f"Error importing django: {e}")
