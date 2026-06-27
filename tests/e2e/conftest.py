import os
import socket
import tempfile
import threading
import time

import pytest
import uvicorn

CHROMIUM_PATH = "/snap/chromium/current/usr/lib/chromium-browser/chrome"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {
        **browser_type_launch_args,
        "executable_path": CHROMIUM_PATH,
        "headless": True,
        "args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
    }


@pytest.fixture(scope="session")
def live_server_url():
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp_db.close()

    from app import config, database

    config.DB_PATH = tmp_db.name
    database._db = None

    port = _find_free_port()
    uv_config = uvicorn.Config(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="error",
    )
    server = uvicorn.Server(uv_config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)

    base_url = f"http://127.0.0.1:{port}"
    yield base_url

    server.should_exit = True
    thread.join(timeout=5)

    try:
        os.unlink(tmp_db.name)
    except OSError:
        pass


@pytest.fixture
def server_url(live_server_url):
    return live_server_url


@pytest.fixture
def page(browser, server_url):
    context = browser.new_context()
    pg = context.new_page()
    pg._server_url = server_url
    yield pg
    pg.close()
    context.close()


@pytest.fixture
def page_goto(page, server_url):
    def _goto(path: str = "/"):
        page.goto(f"{server_url}{path}")
        page.wait_for_load_state("networkidle")
        return page

    return _goto


@pytest.fixture
def api(server_url):
    import httpx2
    return httpx2.Client(base_url=server_url, timeout=10.0)
