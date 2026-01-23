import datetime
import enum
from collections.abc import Sequence as _Sequence

import aiohttp
import msgspec

from pagopar import _app, _enums, _http, checkout as _checkout

__all__ = ()


class ShippingMethod(enum.Enum):
    """Supported shipping method identifiers used during selection."""
    AEX = "aex"
    MOBI = "mobi"
    OWN_DELIVERY = "propio"
    PICKUP = "retiro"


class Category(msgspec.Struct):
    """
    Represents a Pagopar shipping category used for freight calculation.

    Categories are intended for merchants who do not have exact product
    weight and dimensions. Each category represents an average size and
    weight profile.
    """

    category_id: str = msgspec.field(name="categoria")
    """Category identifier used during freight calculation."""
    name: str = msgspec.field(name="descripcion")
    """Category name."""
    description: str = msgspec.field(name="descripcion_completa")
    """
    Full category description including its hierarchical breadcrumb
    (parent categories).
    """
    needs_dimensions: bool = msgspec.field(name="medidas")
    """
    Indicates whether product dimensions must be provided in addition
    to the category ID. If False, the category ID alone is sufficient.
    """
    is_physic_product: bool = msgspec.field(name="producto_fisico")
    """
    Indicates whether this category represents a physical product.
    Non-physical categories may include services or digital products.
    """
    supports_aex_shipping: bool = msgspec.field(name="envio_aex")
    """
    Indicates whether the category supports Pagopar courier services
    such as AEX or MOBI.
    """


class PickupMethod(msgspec.Struct):
    """
    Configuration for in-store pickup (no delivery).
    """

    notes: str = msgspec.field(name="observacion")
    """Instructions for the customer, such as the store address or pickup hours."""
    cost: int = msgspec.field(default=0, name="costo")
    """Shipping cost in Guaraníes (PYG)."""
    delivery_time: int = msgspec.field(default=0, name="tiempo_entrega")
    """Estimated delivery time, usually expressed in hours."""


class DeliveryRule(msgspec.Struct):
    """
    Represents a merchant-defined delivery rule for a specific destination.
    """

    destination_id: str = msgspec.field(name="destino")
    """The unique identifier for the destination city (from Pagopar city list)."""
    price: int = msgspec.field(name="precio")
    """The shipping cost to be charged to the customer."""
    delivery_time: int = msgspec.field(name="tiempo_entrega")
    """Estimated delivery time, usually expressed in hours."""


class DeliveryMethod(msgspec.Struct):
    """A collection of custom delivery rules managed by the merchant's own logistics."""
    delivery_rules: list[DeliveryRule] = msgspec.field(name="listado")
    """A list of destination-specific shipping rates."""


class CourierOption(msgspec.Struct):
    """Represents a specific shipping service option offered by an external courier."""
    option_id: str = msgspec.field(name="id")
    """Unique identifier for the shipping option (e.g., '10-0'). Used to select this specific service in subsequent steps."""
    description: str = msgspec.field(name="descripcion")
    """Detailed description of the service (e.g., 'BUMER', 'Standard', 'E-Lockers')."""
    cost: int = msgspec.field(name="costo")
    """Shipping cost in Guaraníes (PYG) calculated based on product dimensions and weight."""
    delivery_time: str = msgspec.field(name="tiempo_entrega")
    """Estimated time for delivery in hours, as committed by the courier."""


class AEXMethod(msgspec.Struct):
    """Configuration and available options for AEX courier services."""
    option_id: str | None = msgspec.field(name="id")
    """Initially null in the calculation response. Must be populated with a specific Option ID when confirming the selection."""
    options: list[CourierOption] = msgspec.field(name="opciones")
    """List of available delivery services (Express, Standard, Lockers, etc.)."""
    delivery_time: str | None = msgspec.field(name="tiempo_entrega")
    """Global delivery time estimate, usually null in the initial response."""
    cost: int = msgspec.field(name="costo")
    """Base cost or total cost for the selected method, defaults to 0."""


class MOBIMethod(msgspec.Struct):
    """Configuration and available options for MOBI courier services."""
    option_id: str | None = msgspec.field(name="id")
    """Initially null. Must be populated with a specific Option ID when confirming the selection."""
    options: list[CourierOption] = msgspec.field(name="opciones")
    """List of available delivery services provided by MOBI."""
    delivery_time: str | None = msgspec.field(name="tiempo_entrega")
    """Global delivery time estimate."""
    cost: int = msgspec.field(name="costo")
    """Calculated cost for the MOBI service."""


class ShippingOptions(msgspec.Struct):
    """
    The main container for all shipping and pickup configurations in a request.

    If a method is None, that specific shipping option will not be shown to the user 
    unless calculated automatically by the provider (e.g., Mobi/AEX).
    """
    pickup_method: PickupMethod | None = msgspec.field(name="metodo_retiro")
    """Local pickup settings."""
    delivery_method: DeliveryMethod | None = msgspec.field(name="metodo_propio")
    """Merchant's private delivery fleet settings."""
    mobi_method: MOBIMethod | None = msgspec.field(default=None, name="metodo_mobi")
    """Settings for MOBI courier integration (Generated by pagopar)."""
    aex_method: AEXMethod | None = msgspec.field(default=None, name="metodo_aex")
    """Settings for AEX courier integration (Generated by pagopar)."""


class ShippingOptionsSelection(ShippingOptions, kw_only=True):
    commerce_commission: int = msgspec.field(default=0, name="comercio_comision")
    """Commission charged to the merchant, if applicable."""
    shipping_cost: int = msgspec.field(name="costo_envio")
    """
    Total shipping cost for the selected method.
    If multiple items exist, all selected shipping costs must be summed.
    """
    selected_method: ShippingMethod = msgspec.field(name="envio_seleccionado")
    """Selected shipping method."""


class PhysicalItem(_checkout.Item, kw_only=True):
    """Order item that requires shipping calculation."""

    weight: str = msgspec.field(default="", name="peso")
    length: str = msgspec.field(default="", name="largo")
    width: str = msgspec.field(default="", name="ancho")
    height: str = msgspec.field(default="", name="alto")
    shipping_options: ShippingOptions = msgspec.field(name="opciones_envio")


class Neighborhood(msgspec.Struct):
    """Represents a city neighborhood."""

    neighborhood_id: str = msgspec.field(name="barrio")
    name: str = msgspec.field(name="descripcion")


class City(msgspec.Struct):
    """Represents a city available for pickup and delivery services."""

    city_id: str = msgspec.field(name="ciudad")
    name: str = msgspec.field(name="descripcion")
    neighborhoods: list[Neighborhood] = msgspec.field(
        default_factory=list[Neighborhood], name="barrios"
    )


async def get_cities(app: _app.Application | None = None) -> list[City]:
    """
    Retrieve the list of cities available for pickup and delivery services
    offered by delivery providers associated with Pagopar.

    Currently, the supported providers are AEX and Mobi.

    Parameters
    ----------
    app : Application, optional
        Pagopar commerce/application configuration.
        If not provided, the default application configuration is used.

    Returns
    -------
    list[City]
        A list of available cities.

    Raises
    ------
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network-level error occurs.
    msgspec.DecodeError
        If the response payload cannot be decoded.
    """
    return await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="ciudades/1.1/traer",
        token_data="CIUDADES",
        response_type=list[City],
        payload={},
        key_public_token="token_publico",
        app=app,
    )


async def get_neighborhoods(
    app: _app.Application | None = None,
) -> list[City]:
    """
    Retrieve the list of cities along with their available neighborhoods
    for pickup and delivery services offered by delivery providers
    associated with Pagopar.

    This endpoint behaves similarly to :func:`get_cities`, but additionally
    includes neighborhood-level information. It is useful when the integration
    requires specifying or validating neighborhoods as part of the delivery
    or pickup flow.

    Currently, the supported providers are AEX and Mobi.

    Parameters
    ----------
    app : Application, optional
        Pagopar application configuration.
        If not provided, the default application configuration is used.

    Returns
    -------
    list[City]
        A list of cities, each including its available neighborhoods.

    Raises
    ------
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network-level error occurs.
    msgspec.DecodeError
        If the response payload cannot be decoded.
    """
    response = await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="ciudades/1.1/traer-barrios",
        token_data="CIUDADES",
        response_type=list[list[msgspec.Raw]],
        payload={},
        key_public_token="token_publico",
        app=app,
    )
    return [msgspec.json.decode(city, type=City) for array in response for city in array]


async def get_categories(app: _app.Application | None = None) -> list[Category]:
    """
    Retrieve the list of Pagopar product categories used for freight calculation.

    Categories are recommended when the merchant does not have precise
    product dimensions. When exact dimensions are available, providing
    them is preferred, as categories are based on average sizes and may
    result in higher shipping costs for multiple items.

    Parameters
    ----------
    app : Application, optional
        Pagopar application configuration.

    Returns
    -------
    list[Category]

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
        path="categorias/2.0/traer",
        token_data="CATEGORIAS",
        response_type=list[Category],
        payload={},
        key_public_token="token_publico",
        app=app,
    )


async def calculate_freight(
    commerce_order_id: str,
    items: _Sequence[PhysicalItem],
    amount: int,
    max_payment_date: datetime.datetime,
    buyer_name: str,
    buyer_email: str,
    buyer_phone: str,
    buyer_document: str,
    buyer_document_type: _enums.DocumentType,
    buyer_ruc: str | None = None,
    buyer_legal_name: str | None = None,
    buyer_city_id: str | None = None,
    buyer_address: str | None = None,
    buyer_address_ref: str | None = None,
    buyer_address_coordinates: str | None = None,
    payment_type: _enums.PaymentType | None = None,
    description: str | None = None,
    app: _app.Application | None = None,
) -> list[PhysicalItem]:
    """
    Request available freight options and delivery services for an order.

    This endpoint calculates shipping costs and delivery times for
    all enabled shipping methods (pickup, own delivery, AEX, MOBI)
    based on the provided order and buyer data.

    Parameters
    ----------
    commerce_order_id : str
        Unique merchant order identifier.
    items : Sequence[Item]
        Items included in the order.
    amount : int
        Total order amount (PYG).
    max_payment_date : datetime.datetime
        Payment expiration date.
    buyer_name : str
        Buyer's full name.
    buyer_email : str
        Buyer's email address.
    buyer_phone : str
        Buyer's phone number.
    buyer_document : str
        Buyer identification number.
    buyer_document_type : DocumentType
        Type of identification document.
    buyer_city_id : str, optional
        Buyer city ID (required for courier services).
    payment_type : PaymentType, optional
        Payment method.
    description : str, optional
        Order summary description.
    app : Application, optional
        Pagopar application configuration.

    Returns
    -------
    list[PhysicalItem]
        Items enriched with available shipping options.

    Raises
    ------
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network-level error occurs.
    msgspec.DecodeError
        If the response cannot be decoded.
    """
    response = await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="calcular-flete/2.0/traer",
        token_data="CALCULAR-FLETE",
        response_type=dict[str, msgspec.Raw],
        payload={
            "monto_total": amount,
            "tipo_pedido": "VENTA-COMERCIO",
            "fecha_maxima_pago": max_payment_date.isoformat(" "),
            "id_pedido_comercio": commerce_order_id,
            "descripcion_resumen": description or "",
            "forma_pago": payment_type,
            "comprador": {
                "nombre": buyer_name,
                "ciudad": buyer_city_id or "1",
                "email": buyer_email,
                "telefono": buyer_phone,
                "tipo_documento": buyer_document_type,
                "documento": buyer_document,
                "direccion": buyer_address or "",
                "direccion_referencia": buyer_address_ref or "",
                "coordenadas": buyer_address_coordinates or "",
                "ruc": buyer_ruc or "",
                "razon_social": buyer_legal_name or "",
            },
            "compras_items": items,
        },
        app=app,
    )
    # same payload but adds mobi and aex methods
    return msgspec.json.decode(response["compras_items"], type=list[PhysicalItem])


def select_shipping_method(
    item: PhysicalItem,
    method: ShippingMethod,
    option_id: str | None = None
):
    """
    Select a shipping method and option for a given item.

    For courier-based methods (AEX, MOBI), a valid option_id must be provided.
    This function updates the item's shipping options with the selected method
    and calculated cost.

    Parameters
    ----------
    item : PhysicalItem
        Item for which the shipping method will be selected.
    method : ShippingMethod
        Selected shipping method.
    option_id : str, optional
        Courier option identifier (required for AEX and MOBI).

    Raises
    ------
    ValueError
        If the selected method is not available or the option_id is invalid.
    """
    shipping_options = item.shipping_options
    shipping_cost = 0

    method_map = {
        ShippingMethod.AEX: shipping_options.aex_method,
        ShippingMethod.MOBI: shipping_options.mobi_method,
    }

    if method in method_map:
        if (obj := method_map[method]) is None:
            raise ValueError(f"Missing {method.name.lower()} method config")
        try:
            option = next(o for o in obj.options if o.option_id == option_id)
        except StopIteration:
            raise ValueError("Option id is not in method options list") from None
        shipping_cost = option.cost
        obj.option_id = option_id

    item.shipping_options = ShippingOptionsSelection(
        pickup_method=shipping_options.pickup_method,
        delivery_method=shipping_options.delivery_method,
        mobi_method=shipping_options.mobi_method,
        aex_method=shipping_options.aex_method,
        shipping_cost=shipping_cost,
        selected_method=method,
    )
