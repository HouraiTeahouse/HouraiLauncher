import common
import os
import sys
from unittest import TestCase, main
from unittest.case import _UnexpectedSuccess
from common import get_app, get_loop, set_app_icon, ICON_SIZES, sanitize_url,\
     inject_variables, GLOBAL_CONTEXT
from PyQt5.QtWidgets import QApplication
from quamash import QEventLoop
from util import tupperware, get_platform


launcher_endpoint = "https://patch.houraiteahouse.net/{project}/launcher\
/{platform}/{executable}"


class CommonTest(TestCase):

    def test_get_loop_fails_without_app(self):
        common.app = None
        common.loop = None
        try:
            loop = get_loop()
            raise _UnexpectedSuccess
        except NameError:
            pass

    def test_can_get_app(self):
        common.app = None
        app = get_app()
        self.assertTrue(app)

        # make sure if it is called again, the loop is the same object
        self.assertIs(get_app(), app)

    def test_can_get_loop(self):
        common.loop = None
        loop = get_loop()
        self.assertTrue(loop)

        # make sure if it is called again, the loop is the same object
        self.assertIs(get_loop(), loop)

    def test_cannot_set_icon_without_app(self):
        common.app = None
        try:
            set_app_icon()
            raise _UnexpectedSuccess
        except NameError:
            pass

    def test_app_icon_has_all_sizes(self):
        common.app = QApplication(sys.argv)
        common.loop = QEventLoop(common.app)
        set_app_icon()

        qicon_sizes = common.app_icon.availableSizes()
        self.assertEqual(len(ICON_SIZES), len(qicon_sizes))

        for q_size in qicon_sizes:
            self.assertTrue(q_size.height() == q_size.width())
            self.assertIn(q_size.height(), ICON_SIZES)

    def test_sanitize_url(self):
        self.assertEqual(
            sanitize_url("https://this is a test url.com"),
            "https://this-is-a-test-url.com")

    def _inject_variables_using_custom_context(self, context=None):
        if context:
            endpoint = inject_variables(launcher_endpoint, context)
        else:
            endpoint = inject_variables(launcher_endpoint)

        self.assertEqual(
            endpoint,
            "https://patch.houraiteahouse.net/{project}/launcher/%s/%s" %
            (get_platform(), os.path.basename(sys.executable)))

    def test_inject_variables_using_custom_context_dict(self):
        context = dict(
            platform=get_platform(),
            executable=os.path.basename(sys.executable)
            )
        self._inject_variables_using_custom_context(context)

    def test_inject_variables_using_custom_context_object(self):
        context = tupperware(dict(
            platform=get_platform(),
            executable=os.path.basename(sys.executable)
            ))
        self._inject_variables_using_custom_context(context)

    def test_inject_variables_using_global_context(self):
        self._inject_variables_using_custom_context()


if __name__ == "__main__":
    main()
