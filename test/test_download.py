import requests
from unittest import TestCase, main, mock
from download import download_file, Download, DownloadTracker


class ResponseMock(object):
    data = b''
    status_code = requests.codes['ok']

    def __init__(self, data):
        self.data = data

    def iter_content(self, chunk_size):
        assert chunk_size > 0
        for i in range(0, len(self.data), chunk_size):
            yield self.data[i: i + chunk_size]

    def raise_for_status(self):
        pass

    def json(self):
        return eval(self.data)


class SessionMock(object):
    responses = None
    data = None

    def __init__(self, data=b''):
        self.responses = {}
        self.data = data

    def get(self, url, **kwargs):
        responses = self.responses[url] = self.responses.get(url, [])
        response = ResponseMock(self.data)
        responses.append(response)
        return response


class ExecutorMock(object):
    pass


class ProgressBarMock(object):
    minimum = 0
    maximum = 0
    value = 0

    def setMinimum(self, val):
        self.minimum = val

    def setMaximum(self, val):
        self.maximum = val

    def setValue(self, val):
        self.value = val


class DownloadFileTest(TestCase):
    session_mock = None
    downloaded_bytes = 0

    def setUp(self):
        self.session_mock = SessionMock()
        requests.real_get = requests.get
        requests.get = self.session_mock.get

    def tearDown(self):
        requests.get = requests.real_get
        del requests.real_get
        del self.session_mock
        if hasattr(self, "downloaded_bytes"):
            self.downloaded_bytes = 0

    def _download_inc(self, block):
        self.downloaded_bytes += len(block)

    def _call_download(self, test_path, test_url,
                       test_data=b'', test_hash=None, session=None):
        self.session_mock.data = test_data
        with mock.patch('download.open', mock.mock_open()) as m:
            download_file(
                test_url, test_path, self._download_inc, session, test_hash)

        responses = self.session_mock.responses
        self.assertIn(test_url, responses)
        self.assertEqual(1, len(responses[test_url]))
        self.assertEqual(len(test_data), self.downloaded_bytes)
        m.assert_called_once_with(test_path, 'wb+')

    def test_download_file_4kb_of_0xff(self):
        test_path = "4kb_0xff_0.bin"
        test_url = "http://test-url.com/%s" % test_path
        test_data = b'\xff'*4*(1024**2)
        test_hash = (
            "cd3517473707d59c3d915b52a3e16213cadce80d9ffb2b4371958fb7acb51a08"
            )
        self._call_download(test_path, test_url, test_data, test_hash,
                            self.session_mock)

    def test_download_file_empty_file(self):
        test_path = "empty_0.bin"
        test_url = "http://test-url.com/%s" % test_path
        test_hash = (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            )
        self._call_download(test_path, test_url, b'', test_hash,
                            self.session_mock)

    def test_download_file_bad_hash(self):
        test_path = "empty_1.bin"
        test_url = "http://test-url.com/%s" % test_path
        test_hash = "badhash"
        self._call_download(test_path, test_url, b'', test_hash,
                            self.session_mock)

    def test_download_file_no_session_provided(self):
        test_path = "4kb_0xff_1.bin"
        test_url = "http://test-url.com/%s" % test_path
        test_data = b'\xff'*4*(1024**2)
        self._call_download(test_path, test_url, test_data)


class DownloadTest(TestCase):
    session_mock = None

    setUp = DownloadFileTest.setUp

    tearDown = DownloadFileTest.tearDown

    def _call_download(self, test_path, test_url,
                       test_data=b'', test_hash=None, session=None):
        downloader = Download(test_path, test_url, len(test_data))
        self.session_mock.data = test_data

        with mock.patch('download.open', mock.mock_open()) as m:
            downloader.download_file(session)

        responses = self.session_mock.responses
        self.assertIn(test_url, responses)
        self.assertEqual(1, len(responses[test_url]))
        self.assertEqual(len(test_data), downloader.downloaded_bytes)
        m.assert_called_once_with(test_path, 'wb+')

    test_download_4kb_of_0xff = DownloadFileTest.\
        test_download_file_4kb_of_0xff

    test_download_empty_file = DownloadFileTest.\
        test_download_file_empty_file

    test_download_bad_hash = DownloadFileTest.\
        test_download_file_bad_hash

    test_download_no_session_provided = DownloadFileTest.\
        test_download_file_no_session_provided


class DownloadTrackerTest(TestCase):
    download_tracker = None
    progress_bar = ProgressBarMock()
    executor = ExecutorMock()

    def setUp(self):
        self.session_mock = SessionMock()
        requests.real_get = requests.get
        requests.get = self.session_mock.get
        self.download_tracker = DownloadTracker(
            self.progress_bar, self.executor)

    def tearDown(self):
        requests.get = requests.real_get
        del requests.real_get
        del self.session_mock

    def test_download_tracker_can_update(self):
        self.download_tracker.update()

    def test_download_tracker_can_add_downloads(self):
        for path, url, size in [("path1", "url1", 1337),
                                ("path2", "url2", 1412)]:
            self.download_tracker.add_download(path, url, size)
            d = self.download_tracker.downloads[-1]
            self.assertEqual(d.url, url)
            self.assertEqual(d.file_path, path)
            self.assertEqual(d.total_size, size)

    def test_download_tracker_can_clear_downloads(self):
        downloads = self.download_tracker.downloads
        download_futures = self.download_tracker.download_futures
        for i in range(0, 4096, 1024):
            self.download_tracker.add_download("url%s" % i, "path%s" % i, i)
            download_futures.append(None)

        self.assertEqual(len(downloads), 4)
        self.assertEqual(len(download_futures), 4)
        self.download_tracker.clear()
        self.assertEqual(len(downloads), 0)
        self.assertEqual(len(download_futures), 0)

    def test_download_tracker_updates_properly(self):
        test_download_1 = Download('', '', 2048)
        test_download_2 = Download('', '', 4096)
        test_download_1.downloaded_bytes = 1337
        test_download_2.downloaded_bytes = 1412
        self.download_tracker.downloads = (test_download_1, test_download_2)
        self.download_tracker.update()

        self.assertEqual(self.progress_bar.maximum, 2048+4096)
        self.assertEqual(self.progress_bar.value, 1337+1412)

    # TODO:
    # write unittests for _execute_requests, run, and run_async

if __name__ == "__main__":
    main()
