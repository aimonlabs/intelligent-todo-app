import sys
import os
import subprocess

def run_command(cmd):
    try:
        output = subprocess.check_output(cmd, shell=True, text=True)
        return output.strip()
    except Exception as e:
        return f"Error: {e}"

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Python path (sys.path):")
for path in sys.path:
    print(f"  - {path}")

print("\nChecking for autogen module:")
try:
    import autogen
    print(f"Autogen imported successfully from: {autogen.__file__}")
    print(f"Autogen version: {autogen.__version__ if hasattr(autogen, '__version__') else 'unknown'}")
except ImportError as e:
    print(f"Failed to import autogen: {e}")

print("\nPip list output:")
print(run_command(f"{sys.executable} -m pip list | grep -i autogen"))

print("\nEnvironment variables:")
for key, value in os.environ.items():
    if "path" in key.lower():
        print(f"  {key}: {value}") 