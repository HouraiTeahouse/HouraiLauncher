import os
import platform
import sys
from unittest import TestCase, main
from common import sanitize_url, inject_variables, GLOBAL_CONTEXT


launcher_endpoint = "https://patch.houraiteahouse.net/{project}/launcher\
/{platform}/{executable}"


class CommonTest(TestCase):

    def test_sanitize_url(self):
        self.assertEqual(
            sanitize_url("https://this is a test url.com"),
            "https://this-is-a-test-url.com")

    def test_inject_variables_using_custom_context(self, custom_context=True):
        if custom_context:
            context = dict(
                platform=platform.system(),
                executable=os.path.basename(sys.executable)
                )
            endpoint = inject_variables(launcher_endpoint, context)
        else:
            endpoint = inject_variables(launcher_endpoint)

        self.assertEqual(
            endpoint,
            "https://patch.houraiteahouse.net/{project}/launcher/%s/%s" %
            (platform.system(),os.path.basename(sys.executable) ))

    def test_inject_variables_using_global_context(self):
        self.test_inject_variables_using_custom_context(False)


if __name__ == "__main__":
    main()
