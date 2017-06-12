import os
import platform
import sys
from unittest import TestCase, main
from common import sanitize_url, inject_variables, GLOBAL_CONTEXT
from util import tupperware


launcher_endpoint = "https://patch.houraiteahouse.net/{project}/launcher\
/{platform}/{executable}"


class CommonTest(TestCase):

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
            (platform.system(), os.path.basename(sys.executable)))

    def test_inject_variables_using_custom_context_dict(self):
        context = dict(
            platform=platform.system(),
            executable=os.path.basename(sys.executable)
            )
        self._inject_variables_using_custom_context(context)

    def test_inject_variables_using_custom_context_object(self):
        context = tupperware(dict(
            platform=platform.system(),
            executable=os.path.basename(sys.executable)
            ))
        self._inject_variables_using_custom_context(context)

    def test_inject_variables_using_global_context(self):
        self._inject_variables_using_custom_context()


if __name__ == "__main__":
    main()
