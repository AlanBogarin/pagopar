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
    """
    Represents a Pagopar application configuration.

    This class holds credential information and manages the underlying
    HTTP session used for API requests.

    Parameters
    ----------
    name : str
        Unique identifier for this application instance.
    private_token : str
        Commerce private token provided by Pagopar.
    public_token : str
        Commerce public token provided by Pagopar.
    proxy : str, optional
        Proxy URL to use for network requests.
    """

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
        """Application name."""
        return self._name

    @property
    def private_token(self) -> str:
        """Commerce private token."""
        return self._private_token

    @property
    def public_token(self) -> str:
        """Commerce public token."""
        return self._public_token

    @property
    def session(self) -> aiohttp.ClientSession:
        """
        The aiohttp ClientSession used by this application.

        The session is lazily created when first accessed.
        """
        with self._session_lock:
            if not self._session or self._session.closed:
                self._session = _http.create_session(self.proxy)
            return self._session

def initialize_app(
    private_token: str | None = None,
    public_token: str | None = None,
    *,
    proxy: str | None = None,
    name: str = _DEFAULT_APP_NAME,
) -> Application:
    """
    Initialize the Pagopar application with credentials.

    If tokens are not provided, the function attempts to read them from
    environment variables ``PAGOPAR_PRIVATE_TOKEN`` and ``PAGOPAR_PUBLIC_TOKEN``.

    Parameters
    ----------
    private_token : str, optional
        Commerce private token.
    public_token : str, optional
        Commerce public token.
    proxy : str, optional
        Proxy URL for API requests.
    name : str, optional
        Unique name for this application instance. Defaults to a global default name.

    Returns
    -------
    Application
        The initialized application instance.

    Raises
    ------
    RuntimeError
        If credentials are missing (neither provided nor found in environment).
    ValueError
        If an application with the same name is already initialized.
    """
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
    """
    Retrieve an initialized application instance by name.

    Parameters
    ----------
    name : str, optional
        The name of the application to retrieve.

    Returns
    -------
    Application
        The requested application instance.

    Raises
    ------
    ValueError
        If no application with the specified name exists.
    """
    with _APP_LOCK:
        if name in _apps:
            return _apps[name]
    raise ValueError(f"Pagopar named {name!r} not exists.")


async def close_app(name: str = _DEFAULT_APP_NAME) -> None:
    """
    Close an initialized application and its associated HTTP session.

    Parameters
    ----------
    name : str, optional
        The name of the application to close.

    Raises
    ------
    ValueError
        If no application with the specified name exists.
    """
    app = get_app(name)
    with _APP_LOCK:
        del _apps[name]
    if app._session and not app._session.closed:
        await app.session.close()


def check_initialized_app(app: Application | None) -> Application:
    if app is None:
        return get_app()
    if app is not get_app(app.name):
        raise ValueError("Application instance not initialized via the pagopar module.")
    return app
