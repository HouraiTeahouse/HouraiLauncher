import config
import logging
import os
from ui import MainWindow
from common import get_app, get_loop, set_app_icon

app = get_app()
loop = get_loop()
set_app_icon()
main_window = MainWindow(config.load_config())

if __name__ == '__main__':
    main_window.show()
    try:
        loop.run_until_complete(main_window.main_loop())
        loop.run_forever()
    except RuntimeError as e:
        logging.exception(e)
    except Exception as e:
        print('Hello')
        logging.exception(e)
        raise
    finally:
        loop.close()
