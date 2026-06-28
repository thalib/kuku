import asyncio.base_events


def _noop_check_running(self):
    pass


asyncio.base_events.BaseEventLoop._check_running = _noop_check_running
