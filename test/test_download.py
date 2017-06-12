import requests
from unittest import TestCase, main
from download import download_file, Download, DownloadTracker


class DownloadTest(TestCase):
    def setUp(self):
        # replace functions in the requests library with mocks
        pass

    def tearDown(self):
        # replace the mocks in the requests library with the real ones
        pass


if __name__ == "__main__":
    main()
