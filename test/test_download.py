import asyncio
import requests
import time
from async_unittest import AsyncTestCase, async_patch, TestCase, mock, main
from concurrent import futures
from download import download_file, Download, DownloadTracker


class ResponseMock(object):
    data = b''
    _json = None
    _text = None
    status_code = requests.codes['ok']

    def __init__(self, data):
        self.data = data

    def iter_content(self, chunk_size):
        assert chunk_size > 0
        for i in range(0, len(self.data), chunk_size):
            yield self.data[i: i + chunk_size]

    def raise_for_status(self):
        pass

    @property
    def text(self):
        if self._text is None:
            self._text = self.data.decode(encoding='utf8')
        return self._text

    def json(self):
        if self._json is None:
            self._json = eval(self.data)
        return self._json


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

    def __enter__(self, *args, **kwargs):
        pass

    def __exit__(self, *args, **kwargs):
        pass


class FutureMock(object):
    mock_done = False
    done_call_target_count = 3
    done_call_count = 0

    def done(self):
        self.done_call_count += 1
        return self.done_call_count >= self.done_call_target_count


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


class DownloadTrackerTest(AsyncTestCase):
    download_tracker = None
    progress_bar = ProgressBarMock()
    executor = futures.ThreadPoolExecutor()
    _loop = asyncio.new_event_loop()

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

        # test the return for when the progress_bar is None
        self.download_tracker.progress_bar = None
        self.download_tracker.update()

    def test_download_tracker_can_execute_requests(self):
        tracker = self.download_tracker
        test_download_1 = Download('', '', 2048)
        test_download_2 = Download('', '', 4096)
        test_download_3 = Download('', '', 8192)
        tracker.downloads = (test_download_1, test_download_2, test_download_3)

        with mock.patch('download.Download.download_file') as m:
            # the truthyness of m._is_coroutine is True for some reason.
            # it must be False or else the executor will see it as a coroutine
            m._is_coroutine = False
            mock_session = object()
            self.run_async(tracker._execute_requests, self.loop, mock_session)
            m.assert_called_with(mock_session)

        self.assertEqual(m.call_count, 3)

    def test_download_tracker_can_run(self):
        tracker = self.download_tracker
        future_mock = FutureMock()

        async def run(*args, **kwargs):
            tracker.run(*args, **kwargs)

        with mock.patch('asyncio.get_event_loop',
                        return_value=self.loop) as m1,\
                mock.patch('download.DownloadTracker._execute_requests',
                           return_value=future_mock) as m2:
            tracker.progress_bar = None
            mock_session = object()

            self.run_async(run, mock_session)
            m2.assert_called_with(self.loop, session=mock_session)

        self.assertEqual(future_mock.done_call_count, 3)

    def test_download_tracker_can_run_async(self):
        tracker = self.download_tracker
        future_mock = FutureMock()

        with mock.patch('asyncio.get_event_loop',
                        return_value=self.loop) as m1,\
                mock.patch('download.DownloadTracker._execute_requests',
                           return_value=future_mock) as m2,\
                async_patch('asyncio.sleep') as m3:
            tracker.progress_bar = None
            mock_session = object()

            self.run_async(tracker.run_async, mock_session)
            m2.assert_called_with(self.loop, session=mock_session)

        self.assertEqual(future_mock.done_call_count, 3)


if __name__ == "__main__":
    main()
