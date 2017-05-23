from config import CONFIG
from ui import MainWindow
from common import loop

main_window = MainWindow(CONFIG)

if __name__ == "__main__":
    main_window.show()
    try:
        loop.run_until_complete(main_window.main_loop())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
