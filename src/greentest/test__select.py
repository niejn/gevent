import _six as six
import sys
import os
import errno
from gevent import select, socket
import gevent.core
import greentest
import unittest


class TestSelect(greentest.GenericWaitTestCase):

    def wait(self, timeout):
        select.select([], [], [], timeout)


if sys.platform != 'win32':

    class TestSelectRead(greentest.GenericWaitTestCase):

        def wait(self, timeout):
            r, w = os.pipe()
            try:
                select.select([r], [], [], timeout)
            finally:
                os.close(r)
                os.close(w)

        # Issue #12367: http://www.freebsd.org/cgi/query-pr.cgi?pr=kern/155606
        @unittest.skipIf(sys.platform.startswith('freebsd'),
                         'skip because of a FreeBSD bug: kern/155606')
        def test_errno(self):
            # Backported from test_select.py in 3.4
            with open(__file__, 'rb') as fp:
                fd = fp.fileno()
                fp.close()
                try:
                    select.select([fd], [], [], 0)
                except OSError as err:
                    # Python 3
                    self.assertEqual(err.errno, errno.EBADF)
                except select.error as err: # pylint:disable=duplicate-except
                    # Python 2 (select.error is OSError on py3)
                    self.assertEqual(err.args[0], errno.EBADF)
                else:
                    self.fail("exception not raised")


    if hasattr(select, 'poll'):

        class TestPollRead(greentest.GenericWaitTestCase):
            def wait(self, timeout):
                # On darwin, the read pipe is reported as writable
                # immediately, for some reason. So we carefully register
                # it only for read events (the default is read and write)
                r, w = os.pipe()
                try:
                    poll = select.poll()
                    poll.register(r, select.POLLIN)
                    poll.poll(timeout * 1000)
                finally:
                    poll.unregister(r)
                    os.close(r)
                    os.close(w)

            def test_unregister_never_registered(self):
                # "Attempting to remove a file descriptor that was
                # never registered causes a KeyError exception to be
                # raised."
                poll = select.poll()
                self.assertRaises(KeyError, poll.unregister, 5)

            @unittest.skipIf(hasattr(gevent.core, 'libuv'),
                             "Depending on whether the fileno is reused or not this either crashes or does nothing."
                             "libuv won't open a watcher for a closed file on linux.")
            def test_poll_invalid(self):
                with open(__file__, 'rb') as fp:
                    fd = fp.fileno()

                    poll = select.poll()
                    poll.register(fd, select.POLLIN)
                    # Close after registering; libuv refuses to even
                    # create a watcher if it would get EBADF (so this turns into
                    # a test of whether or not we successfully initted the watcher).
                    fp.close()
                    result = poll.poll(0)
                    self.assertEqual(result, [(fd, select.POLLNVAL)]) # pylint:disable=no-member

class TestSelectTypes(greentest.TestCase):

    def test_int(self):
        sock = socket.socket()
        select.select([int(sock.fileno())], [], [], 0.001)

    if hasattr(six.builtins, 'long'):
        def test_long(self):
            sock = socket.socket()
            select.select(
                [six.builtins.long(sock.fileno())], [], [], 0.001)

    def test_string(self):
        self.switch_expected = False
        self.assertRaises(TypeError, select.select, ['hello'], [], [], 0.001)


if __name__ == '__main__':
    greentest.main()
