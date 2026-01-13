import asyncio
import os
import threading

import aiohttp

from pagopar import _http

__all__ = ("Application", "initialize_app", "get_app", "close_app")

_DEFAULT_APP_NAME = "<DEFAULT>"
_APP_LOCK = threading.Lock()

_apps: dict[str, "Application"] = {}


class Application:
    __slots__ = (
        "_name",
        "_private_token",
        "_public_token",
        "_session",
        "_session_lock",
        "proxy",
    )

    def __init__(
        self,
        name: str,
        private_token: str,
        public_token: str,
        proxy: str | None
    ) -> None:
        self._name = name
        self._private_token = private_token
        self._public_token = public_token
        self._session: aiohttp.ClientSession | None = None
        self._session_lock = threading.Lock()
        self.proxy = proxy

    @property
    def name(self) -> str:
        return self._name

    @property
    def private_token(self) -> str:
        return self._private_token

    @property
    def public_token(self) -> str:
        return self._public_token

    @property
    def session(self) -> aiohttp.ClientSession:
        with self._session_lock:
            if not self._session or self._session.closed:
                self._session = _http.create_session(self.proxy)
            return self._session

    def __del__(self) -> None:
        with self._session_lock:
            session = self._session
        if session and not session.closed:
            coro = session.close()
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(coro)
                return
            if loop.is_running():
                loop.create_task(coro)
            else:
                loop.run_until_complete(coro)


def initialize_app(
    private_token: str | None = None,
    public_token: str | None = None,
    *,
    proxy: str | None = None,
    name: str = _DEFAULT_APP_NAME,
) -> Application:
    if private_token is None or public_token is None:
        private_token = os.getenv("PAGOPAR_PRIVATE_TOKEN", private_token)
        public_token = os.getenv("PAGOPAR_PUBLIC_TOKEN", public_token)

    if not (private_token and public_token):
        raise RuntimeError("Missing pagopar commerce credentials.")

    with _APP_LOCK:
        if name not in _apps:
            app = _apps[name] = Application(
                name,
                private_token,
                public_token,
                proxy,
            )
            return app

    if name == _DEFAULT_APP_NAME:
        raise ValueError(
            "The default Pagopar app already initialized. If you want to initialize "
            "multiple applications, give a unique value to the `name` parameter."
        )
    raise ValueError(f"Pagopar app named {name!r} already initialized.")


def get_app(name: str = _DEFAULT_APP_NAME) -> Application:
    with _APP_LOCK:
        if name in _apps:
            return _apps[name]
    raise ValueError(f"Pagopar named {name!r} not exists.")


def close_app(name: str = _DEFAULT_APP_NAME) -> None:
    app = get_app(name)
    with _APP_LOCK:
        del _apps[name]
    app.session.closed


def check_initialized_app(app: Application | None) -> Application:
    if app is None:
        return get_app()
    if app is not get_app(app.name):
        raise ValueError("Application instance not initialized via the pagopar module.")
    return app
