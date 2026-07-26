import subprocess

def build():
    print("Building with PyInstaller...")
    subprocess.run([
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--icon=assets/icon.ico",
        "--name=AIChat",
        "src/main.py"
    ])

if __name__ == "__main__":
    build()