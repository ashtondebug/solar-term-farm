"""Start AgriVerse after MicroPython boot.

The stock ESP32 boot.py does not start main.py on this board, so without this
file a reset leaves the board at the REPL and the TFT/button tasks never run.
"""

try:
    import main
    main.main()
except Exception as exc:
    print("boot: main failed:", exc)
