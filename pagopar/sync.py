import datetime
import enum
from collections.abc import Sequence as _Sequence
from typing import (
    Any as _Any,
    Literal as _Literal,
    Generic as _Generic,
    TypeVar as _TypeVar,
    overload as _overload,
)

import aiohttp
import msgspec

from pagopar import _app, _http

__all__ = ()

_T = _TypeVar("_T")


class AEXConfig(msgspec.Struct, kw_only=True):
    """
    Configuration for the AEX courier pickup service.

    This structure defines all information required by Pagopar to enable
    AEX shipping for a product, including pickup address, availability window,
    package dimensions, and courier instructions.
    """

    address: str = msgspec.field(name="direccion")
    """Street address where the product will be picked up."""
    address_city_id: str = msgspec.field(name="direccion_ciudad")
    """
    City identifier for the pickup address.

    This value must match a city ID provided by Pagopar.
    """
    address_coordinates: str = msgspec.field(name="direccion_coordenadas")
    """
    Geographic coordinates of the pickup address.

    Used to precisely locate the pickup point.
    """
    address_ref: str = msgspec.field(name="direccion_referencia")
    """
    Additional address reference to help the courier locate the pickup point.
    """
    comment: str = msgspec.field(name="comentarioPickUp")
    """Additional instructions or comments for the courier."""
    enabled: bool = msgspec.field(default=True, name="activo")
    """Indicates whether the AEX courier service is enabled for this product."""
    start_time: datetime.time = msgspec.field(name="hora_inicio")
    """Time from which the product is available for pickup."""
    end_time: datetime.time = msgspec.field(name="hora_fin")
    """Time until which the product is available for pickup."""
    weight: str = msgspec.field(name="peso")
    """Product weight in kilograms (kg)."""
    length: str = msgspec.field(name="largo")
    """Product length in centimeters (cm)."""
    width: str = msgspec.field(name="ancho")
    """Product width in centimeters (cm)."""
    height: str = msgspec.field(name="alto")
    """Product height in centimeters (cm)."""
    pickup_address_pagopar: str | None = msgspec.field(
        default=None,
        name="direccion_retiro",
    )
    """
    Pagopar pickup address identifier.

    If provided, this value overrides the address defined in this configuration.
    """


class MOBISchedule(msgspec.Struct, kw_only=True):
    """
    Pickup schedule definition for the MOBI courier service.
    """

    days: _Sequence[_Literal["1", "2", "3", "4", "5"]] = msgspec.field(name="dias")
    """
    Days of the week when the product is available for pickup.

    Values are represented as numeric strings:
    - "1" = Monday
    - "5" = Friday
    """
    start: datetime.time = msgspec.field(name="pickup_inicio")
    """Time from which the product can be handed over to the courier."""
    end: datetime.time = msgspec.field(name="pickup_fin")
    """Time until which the product can be handed over to the courier."""


class MOBIConfig(msgspec.Struct, kw_only=True):
    """
    Configuration for the MOBI courier service.

    Defines availability, pickup schedules, and courier-specific identifiers.
    """

    enabled: bool = msgspec.field(default=True, name="activo")
    """Indicates whether the MOBI courier service is enabled."""
    title: str = msgspec.field(name="titulo")
    """Human-readable title used to identify the pickup schedule."""
    user_id: str | None = msgspec.field(default=None, name="usuario_mobi")
    """
    MOBI user identifier.

    Must be null when creating a product.
    When editing a product, this value must be set to the identifier
    provided by Pagopar.
    """
    pickup_address_pagopar: str | None = msgspec.field(
        default=None,
        name="direccion_retiro",
    )
    """
    Pagopar pickup address identifier.

    This field may be null if `aex.pickup_address_pagopar` is set.
    When editing an existing product, this value must match the one
    provided by Pagopar.
    """
    schedules: list[MOBISchedule] = msgspec.field(name="horarios")
    """List of pickup schedules available for the MOBI courier service."""


class ProductOperation(msgspec.Struct):
    """
    Result returned by Pagopar after creating a product.
    """
    commerce_product_id: str = msgspec.field(name="id")
    """Internal product identifier of the commerce."""
    product_id: str = msgspec.field(name="link_venta")
    """Pagopar product identifier."""
    url: str
    """Public URL of the generated product."""


async def create_product(
    commerce_product_id: str,
    title: str,
    description: str,
    price: int,
    stock: int,
    images: _Sequence[str],
    category_id: str | None = None,
    aex_config: AEXConfig | None = None,
    mobi_config: MOBIConfig | None = None,
    enabled: bool = True,
    importable: bool = True,
    app: _app.Application | None = None,
) -> ProductOperation:
    """
    Create a new product in Pagopar.

    Parameters
    ----------
    commerce_product_id : str
        Internal product identifier.
    title : str
        Product title.
    description : str
        Product description.
    price : int
        Product price in Guaraníes.
    stock : int
        Available inventory.
    images : Sequence[str]
        List of image URLs.
    category_id : str, optional
        Pagopar product category ID.
    aex_config : AEXConfig, optional
        AEX shipping configuration.
    mobi_config : MOBIConfig, optional
        MOBI shipping configuration.
    enabled : bool, optional
        Whether the product is active.
    importable : bool, optional
        Whether the product is publicly accessible.
    app : Application, optional
        Pagopar commerce configuration.

    Returns
    -------
    ProductOperation
        Information about the created product.

    Raises
    ------
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network-level error occurs.
    msgspec.DecodeError
        If the response cannot be decoded.
    """
    return await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="links-venta/1.1/agregar/",
        token_data="LINKS-VENTA",
        response_type=ProductOperation,
        payload={
            "id_producto": commerce_product_id,
            "categoria": category_id or "979",
            "link_venta": "",
            "link_publico": importable,
            "activo": enabled,
            "monto": price,
            "titulo": title,
            "descripcion": description,
            "cantidad": stock,
            "imagen": images,
            "envio_aex": aex_config,
            "envio_mobi": mobi_config,
        },
        key_public_token="token_publico",
        app=app,
    )


async def edit_product(
    commerce_product_id: str,
    title: str,
    description: str,
    price: int,
    stock: int,
    images: _Sequence[str],
    category_id: str | None,
    aex_config: AEXConfig | None,
    mobi_config: MOBIConfig | None,
    enabled: bool,
    importable: bool,
    app: _app.Application | None = None,
) -> ProductOperation:
    """
    Update an existing product in Pagopar.

    Parameters
    ----------
    commerce_product_id : str
        Internal product identifier of the commerce.
    title : str
        Updated product title.
    description : str
        Updated product description.
    price : int
        Updated product price in Guaraníes.
    stock : int
        Updated available inventory.
    images : Sequence[str]
        List of image URLs to update.
    category_id : str, None
        Pagopar category ID.
    aex_config : AEXConfig, None
        Updated AEX shipping configuration.
    mobi_config : MOBIConfig, None
        Updated MOBI shipping configuration.
    enabled : bool, None
        Whether the product should be active.
    importable : bool, None
        Whether the product should be publicly accessible.
    app : Application, optional
        Pagopar commerce configuration.

    Returns
    -------
    ProductOperation
        Updated product information.

    Raises
    ------
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network-level error occurs.
    msgspec.DecodeError
        If the response cannot be decoded.
    """
    return await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="links-venta/1.1/editar/",
        token_data="LINKS-VENTA",
        response_type=ProductOperation,
        payload={
            "id_producto": commerce_product_id,
            "categoria": category_id or "979",
            "link_venta": "",
            "link_publico": importable,
            "activo": enabled,
            "monto": price,
            "titulo": title,
            "descripcion": description,
            "cantidad": stock,
            "imagen": images,
            "envio_aex": aex_config,
            "envio_mobi": mobi_config,
        },
        key_public_token="token_publico",
        app=app,
    )


class LogType(enum.Enum):
    """
    Type of notification sent by Pagopar.

    The value determines which synchronization action must be executed.
    """

    SOLD_ORDER = 1
    """Indicates that product stock must be decreased."""
    CANCELLED_ORDER = 2
    """Indicates that product stock must be increased."""
    MODIFIED_PRODUCT = 3
    """Indicates that an existing product must be updated."""
    CREATED_PRODUCT = 4
    """Indicates that a new product must be created."""

    @classmethod
    def _missing_(cls, value: _Any) -> "LogType | None":
        try:
            return cls(int(value))
        except (TypeError, ValueError):
            return None


class LogBase(msgspec.Struct):
    """
    Base structure for all synchronization logs.

    Contains only the notification type, which determines how the payload
    must be interpreted.
    """

    log_type: LogType = msgspec.field(name="tipo_aviso")
    """Type of notification sent by Pagopar."""


class User(msgspec.Struct):
    """
    Represents the owner user of a Pagopar commerce.
    """

    name: str = msgspec.field(name="nombre")
    """User first name."""
    lastname: str = msgspec.field(name="apellido")
    """User last name."""
    email: str = msgspec.field(name="email")
    """User email address."""
    phone: str = msgspec.field(name="celular")
    """User phone number."""


class Category(msgspec.Struct):
    """
    Represents a Pagopar product category.
    """

    category_id: int = msgspec.field(name="categoria")
    """Pagopar category identifier."""
    name: str = msgspec.field(name="descripcion")
    """Category description."""
    needs_dimentions: bool = msgspec.field(name="medidas")
    """
    Indicates whether the category requires weight and dimensions
    to be specified.
    """
    physic_product: bool = msgspec.field(name="producto_fisico")
    """Indicates whether the category corresponds to a physical product."""
    commerce_id: int = msgspec.field(name="comercio")
    """Pagopar commerce identifier (informational only)."""


class AddressInfo(msgspec.Struct):
    """
    Pickup address and availability information of a product.
    """

    address: str = msgspec.field(name="direccion")
    """Street address of the pickup location."""
    coordinates: str = msgspec.field(name="latitud_longitud")
    """Geographic coordinates of the pickup location."""
    note: str = msgspec.field(name="observacion")
    """Additional notes to help locate the pickup point."""
    city_id: int = msgspec.field(name="ciudad")
    """Pagopar city identifier."""
    city_name: str = msgspec.field(name="ciudad_descripcion")
    """City name."""
    pickup_address_pagopar: str = msgspec.field(name="direccion_retiro")
    """Pagopar pickup address identifier."""
    pickup_note: str = msgspec.field(name="comentario_pickup")
    """Additional pickup instructions for the courier."""
    pickup_schedule_start: str = msgspec.field(name="hora_inicio")
    """Start time when pickup is available."""
    pickup_schedule_end: str = msgspec.field(name="hora_fin")
    """End time when pickup is available."""


class MOBIShipping(msgspec.Struct):
    """
    MOBI shipping configuration returned by Pagopar for a product.
    """

    enabled: bool = msgspec.field(name="activo")
    """Whether MOBI shipping is enabled."""
    title: str = msgspec.field(name="titulo")
    """Title identifying the MOBI schedule."""
    schedules: list[MOBISchedule] = msgspec.field(name="horarios")
    """Pickup schedules available for MOBI."""
    user_id: int = msgspec.field(name="mobi_usuario")
    """MOBI user identifier assigned by Pagopar."""


class CityShipping(msgspec.Struct):
    """
    Shipping configuration for a specific destination city.
    """

    city_id: int = msgspec.field(name="ciudad")
    """Destination city identifier."""
    name: str = msgspec.field(name="descripcion")
    """Destination city name."""
    cost: int = msgspec.field(name="costo")
    """Delivery cost charged to the customer."""
    delivery_time: int = msgspec.field(name="horas_entrega")
    """Estimated delivery time in hours."""


class OwnShipping(msgspec.Struct):
    """
    Commerce-managed shipping configuration.
    """

    zone_name: str = msgspec.field(name="descripcion")
    """Name of the delivery zone."""
    zone_id: int = msgspec.field(name="zona_envio")
    """Pagopar shipping zone identifier."""
    cities: list[CityShipping] = msgspec.field(name="ciudad")
    """Cities covered by this shipping zone."""


class Product(msgspec.Struct):
    """
    Complete product representation returned by Pagopar.
    """

    weight: int = msgspec.field(name="peso")
    """Product weight in kilograms."""
    length: int = msgspec.field(name="largo")
    """Product length in centimeters."""
    width: int = msgspec.field(name="ancho")
    """Product width in centimeters."""
    height: int = msgspec.field(name="alto")
    """Product height in centimeters."""
    price: int = msgspec.field(name="monto")
    """Product price in Guaraníes."""
    enabled: bool = msgspec.field(name="activo")
    """Whether the product is active for sale."""
    images: _Sequence[str] = msgspec.field(name="imagen")
    """
    List of product image URLs.

    This field is only populated when images must be synchronized.
    """
    name: str = msgspec.field(name="titulo")
    """Product title."""
    description: str = msgspec.field(name="descripcion")
    """Product description."""
    stock: int = msgspec.field(name="cantidad")
    """Available inventory."""
    aex_enabled: bool = msgspec.field(name="envio_aex")
    """Whether AEX shipping is enabled."""
    local_pickup_enabled: bool = msgspec.field(name="retiro_local")
    """Whether local pickup is enabled."""
    local_pickup_note: str | None = msgspec.field(name="observacion_retiro")
    """Optional local pickup notes."""
    linked: bool = msgspec.field(name="vinculado")
    """Indicates whether the commerce is linked (informational)."""
    user: User = msgspec.field(name="usuario")
    """Owner user of the commerce."""
    category: Category = msgspec.field(name="categoria")
    """Product category."""
    address_info: AddressInfo = msgspec.field(name="direccion")
    """Pickup address information."""
    mobi_shipping: MOBIShipping = msgspec.field(name="envio_mobi")
    """MOBI shipping configuration."""
    own_shipping: list[OwnShipping] = msgspec.field(name="envio_propio")
    """Commerce-managed shipping options."""


class ProductLog(LogBase):
    """
    Synchronization log containing full product information.
    """

    commerce_public_token: str = msgspec.field(name="token_publico")
    """Public token of the commerce."""
    log_id: str = msgspec.field(name="logs")
    """Pagopar log identifier."""
    log_date: datetime.datetime = msgspec.field(name="fecha")
    """Timestamp when the log was generated."""
    quantity_sold: int = msgspec.field(name="cantidad_venta")
    """Total quantity sold in this synchronization event."""
    product_id: str = msgspec.field(name="link_venta")
    """Pagopar product identifier."""
    product: Product = msgspec.field(name="datos")
    """Full product data."""


class Inventory(msgspec.Struct):
    """
    Inventory-only product representation.
    """

    stock: int = msgspec.field(name="cantidad")
    """Available inventory."""


class InventoryLog(LogBase):
    """
    Synchronization log containing inventory-only information.
    """

    commerce_public_token: str = msgspec.field(name="token_publico")
    """Public token of the commerce."""
    log_id: str = msgspec.field(name="logs")
    """Pagopar log identifier."""
    log_date: datetime.datetime = msgspec.field(name="fecha")
    """Timestamp when the log was generated."""
    quantity_sold: int = msgspec.field(name="cantidad_venta")
    """Total quantity sold in this synchronization event."""
    product_id: str = msgspec.field(name="link_venta")
    """Pagopar product identifier."""
    product: Inventory = msgspec.field(name="datos")
    """Inventory data."""
    images: str = msgspec.field(name="imagenes")
    """Image synchronization hint."""
    commerce_id: str = msgspec.field(name="comercio")
    """Pagopar commerce identifier."""
    parent_commerce_id: str | None = msgspec.field(name="comercio_padre_heredado")
    """Inherited parent commerce identifier, if any."""


class SyncRequest(msgspec.Struct, _Generic[_T]):
    """
    Generic synchronization request sent by Pagopar.
    """

    public_token: str = msgspec.field(name="token_publico")
    """Public token of the commerce."""
    hashed_token: str = msgspec.field(name="token")
    """Hashed verification token."""
    data: list[_T] = msgspec.field(name="datos")
    """List of synchronization payloads."""


class InventoryResponse(msgspec.Struct):
    """
    Response for inventory synchronization operations.
    """

    log_id: str = msgspec.field(name="logs")
    """Pagopar log identifier."""
    log_type: LogType = msgspec.field(name="tipo_aviso")
    """Notification type being acknowledged."""
    product_id: str = msgspec.field(name="link_venta")
    """Pagopar product identifier."""
    success: bool = msgspec.field(name="respuesta")
    """Whether the operation succeeded."""


class ProductResponse(InventoryResponse):
    """
    Response for product creation or modification synchronization.
    """

    commerce_product_id: str = msgspec.field(name="id_producto")
    """Internal product identifier of the commerce."""


class SyncResponse(msgspec.Struct, _Generic[_T]):
    """
    Generic synchronization response sent back to Pagopar.
    """

    data: list[_T] = msgspec.field(name="resultado")
    """List of individual synchronization responses."""
    success: bool = msgspec.field(name="respuesta")
    """Overall synchronization result."""


def parse_syncronization(message: bytes | str) -> SyncRequest[ProductLog | InventoryLog]:
    """
    Parse a synchronization payload sent by Pagopar.

    The function inspects each log entry to determine whether it contains
    full product data or inventory-only data.

    Parameters
    ----------
    message : bytes, str
        Raw JSON payload received from Pagopar.

    Returns
    -------
    SyncRequest[ProductLog | InventoryLog]
        Parsed synchronization request.

    Raises
    ------
    msgspec.DecodeError
        If the payload cannot be decoded.
    """
    decode = msgspec.json.decode

    request = decode(
        message,
        type=SyncRequest[msgspec.Raw],
        strict=False,
    )

    product_logs = {LogType.CREATED_PRODUCT, LogType.MODIFIED_PRODUCT}
    parsed: list[ProductLog | InventoryLog] = []

    for raw in request.data:
        base = decode(raw, type=LogBase)
        target_type = ProductLog if base.log_type in product_logs else InventoryLog
        parsed.append(decode(raw, type=target_type))

    return SyncRequest(
        public_token=request.public_token,
        hashed_token=request.hashed_token,
        data=parsed,
    )


@_overload
def respond_syncronization(
    *responses: ProductResponse | InventoryResponse,
    json: _Literal[False] = False,
) -> dict[str, _Any]: ...
@_overload
def respond_syncronization(
    *responses: ProductResponse | InventoryResponse,
    json: _Literal[True],
) -> bytes: ...
def respond_syncronization(
    *responses: ProductResponse | InventoryResponse,
    json: bool = False,
) -> dict[str, _Any] | bytes:
    """
    Build a synchronization response to be sent back to Pagopar.

    Parameters
    ----------
    *responses : ProductResponse, InventoryResponse
        Individual synchronization responses.
    json : bool, optional
        If ``True``, returns a JSON-encoded byte string. Otherwise,
        returns a Python dictionary.

    Returns
    -------
    dict | bytes
        Encoded synchronization response.
    """
    encode = msgspec.json.encode if json else msgspec.to_builtins
    return encode(SyncResponse(data=list(responses), success=True))
