import enum
import datetime
import decimal
import hashlib
import uuid
from collections.abc import Collection, Mapping
from typing import Generic, TypeVar, cast

import aiohttp
import msgspec

from pagopar import _app, _errors

T = TypeVar("T")

__all__ = ()


JSONStrOrNum = (
    decimal.Decimal
    | uuid.UUID
    | datetime.datetime
    | datetime.date
    | datetime.time
    | datetime.timedelta
    | enum.Enum
    | float
    | str
    | bytes
)

JSON = (
    Collection["JSON"]
    | Mapping[JSONStrOrNum, "JSON"]
    | msgspec.Struct
    | msgspec.Raw
    | msgspec.msgpack.Ext
    | JSONStrOrNum
    | bytearray
    | None
)

JSONQuery = dict[str, list[float | str] | float | str]


class Response(msgspec.Struct, Generic[T]):
    success: bool = msgspec.field(name="respuesta")
    payload: T | str = msgspec.field(default="", name="resultado")


encoder = msgspec.json.Encoder()


def create_session(proxy: str | None) -> aiohttp.ClientSession:
    return aiohttp.ClientSession(
        "https://api.pagopar.com/api/",
        headers={aiohttp.hdrs.ACCEPT: "application/json"},
        proxy=proxy,
    )


def create_token(token_data: str, app: "_app.Application | None" = None) -> str:
    """Genera un Token para el pedido"""
    app = _app.check_initialized_app(app)
    return hashlib.sha1((app.private_token + token_data).encode('utf-8')).hexdigest()


async def send_request(
    method: str,
    path: str,
    token_data: str,
    response_type: type[T],
    payload: dict[str, JSON],
    key_hashed_token: str = "token",
    key_public_token: str = "public_key",
    app: "_app.Application | None" = None,
) -> T:
    headers = params = data = None

    app = _app.check_initialized_app(app)

    payload[key_hashed_token] = create_token(token_data, app)
    payload[key_public_token] = app.public_token

    if method in aiohttp.ClientRequest.GET_METHODS:
        params = cast(JSONQuery, payload)
    elif method in aiohttp.ClientRequest.POST_METHODS:
        data = encoder.encode(payload)
        headers = {"Content-Type": "application/json; charset=utf-8"}
    else:
        raise ValueError(f"{method=}")

    async with app.session.request(
        method,
        path,
        params=params,
        data=data,
        headers=headers,
    ) as response:
        decoder = msgspec.json.Decoder(Response[response_type], strict=False)
        try:
            model: Response[T] = await response.json(loads=decoder.decode)
        except msgspec.DecodeError:
            response.raise_for_status()
            raise
    if not model.success:
        raise _errors.parse_error(cast(str, model.payload))
    return cast(T, model.payload)
