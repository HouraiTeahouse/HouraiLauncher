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
        with mock.patch('download.open', mock.mock_open()) as m:
            download_file(
                test_url, test_path, self._download_inc, session, test_hash)

        session = self.session_mock
        responses = session.responses
        self.assertIn(test_url, responses)
        self.assertEqual(1, len(responses[test_url]))
        self.assertEqual(len(session.data), self.downloaded_bytes)
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

        with mock.patch('download.open', mock.mock_open()) as m:
            downloader.download_file(session)

        session = self.session_mock
        responses = session.responses
        self.assertIn(test_url, responses)
        self.assertEqual(1, len(responses[test_url]))
        self.assertEqual(len(session.data), downloader.downloaded_bytes)
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

    setUp = DownloadFileTest.setUp

    tearDown = DownloadFileTest.tearDown


if __name__ == "__main__":
    main()
