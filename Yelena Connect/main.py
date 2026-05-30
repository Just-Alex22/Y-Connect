"""
main.py — Y-Connect System Tray Applet
Punto de entrada.
"""
from tray import YelenaTray

if __name__ == "__main__":
    app = YelenaTray()
    app.run()
