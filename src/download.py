import asyncio
import hashlib
import logging
import time
from util import CHUNK_SIZE

def download_file(url,
                  path,
                  block_fun=None,
                  session=None,
                  filehash=None):
    logging.info('Downloading %s from %s...' % (path, url))
    hasher = hashlib.sha256()
    with open(path, 'wb+') as downloaded_file:
        if session:
            response = session.get(url, stream=True)
        else:
            response = requests.get(url, stream=True)
        logging.info('Response: %s (%s)' %
                     (response.status_code, url))
        for block in response.iter_content(CHUNK_SIZE):
            logging.info('Downloaded chunk of (size: %s, %s)' %
                         (len(block), path))
            if block_fun is not None:
                block_fun(block)
            downloaded_file.write(block)
            hasher.update(block)
    download_hash = hasher.hexdigest()
    if filehash is not None and download_hash != filehash:
        logging.error('File downoad hash mismatch: (%s) \n'
                      '   Expected: %s \n'
                      '   Actual: %s' % (path, filehash, download_hash))
    logging.info('Done downloading: %s' % path)
    return response.status_code


class Download(object):

    def __init__(self, path, url, download_size):
        self.url = url
        self.file_path = path
        self.total_size = download_size
        self.downloaded_bytes = 0

    def download_file(self, session=None):
        def inc_fun(block):
            self.downloaded_bytes += len(block)
        return download_file(self.url,
                             self.file_path,
                             block_fun=inc_fun,
                             session=session)


class DownloadTracker(object):

    def __init__(self, progress_bar, executor=None):
        self.downloads = []
        self.download_futures = []
        self.progress_bar = progress_bar
        self.executor = executor

    def __iter__(self):
        return self.downloads.__iter__()

    @property
    def total_size(self):
        return sum(download.total_size for download in self)

    @property
    def downloaded_bytes(self):
        return sum(download.downloaded_bytes for download in self)

    def clear(self):
        self.downloads.clear()
        self.download_futures.clear()

    def add_download(self, *args):
        self.downloads.append(Download(*args))

    def update(self):
        if self.progress_bar is None:
            return
        download_size = self.total_size
        if download_size <= 0:
            return
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(download_size)
        self.progress_bar.setValue(self.downloaded_bytes)

    def _execute_requests(self, loop, session=None):
        return asyncio.gather(*[loop.run_in_executor(
            self.executor, download.download_file, session)
            for download in self.downloads])

    def run(self, session=None):
        loop = asyncio.get_event_loop()
        all_downloads = self._execute_requests(loop, session=session)
        while not all_downloads.done():
            loop.call_soon_threadsafe(self.update)
            time.sleep(0.1)

    async def run_async(self, session=None):
        loop = asyncio.get_event_loop()
        all_downloads = self._execute_requests(loop, session=session)
        while not all_downloads.done():
            loop.call_soon_threadsafe(self.update)
            await asyncio.sleep(0.1)
