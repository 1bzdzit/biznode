"""
Instance Guard
==============
Prevents multiple installer instances from running simultaneously
by binding to a local TCP port (the cheapest cross-platform lock).
"""

import socket


class InstanceGuard:
    """
    Binds a socket to a localhost port as a process-level mutex.
    If the port is already bound, another instance is running.

    Usage:
        guard = InstanceGuard()
        if not guard.acquire():
            sys.exit("Another BizNode Installer is already running.")
        # ... do work ...
        guard.release()   # or just let the process exit
    """

    _GUARD_PORT = 19876  # arbitrary private port for installer lock

    def __init__(self, port: int = _GUARD_PORT):
        self._port = port
        self._sock: socket.socket | None = None

    def acquire(self) -> bool:
        """Try to acquire the lock. Returns True if successful."""
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            self._sock.bind(("127.0.0.1", self._port))
            self._sock.listen(1)
            return True
        except OSError:
            if self._sock:
                self._sock.close()
                self._sock = None
            return False

    def release(self):
        """Release the lock."""
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *_):
        self.release()
