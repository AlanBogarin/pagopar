import datetime
import decimal
import enum
from collections.abc import Collection as _Collection, Sequence as _Sequence
from typing import Any as _Any

import aiohttp
import msgspec

from pagopar import _app, _enums, _http

__all__ = (
    "check_pagopar_payment",
    "get_order",
    "get_payment_methods",
    "pagopar_checkout_url",
    "start_transaction",
    "start_transaction_in_usd",
)


class PaymentMethod(msgspec.Struct, omit_defaults=True):
    """Represents a Pagopar payment method."""

    id: str = msgspec.field(name="forma_pago")
    """Payment method identifier."""
    min_amount: int = msgspec.field(name="monto_minimo")
    """Minimum allowed payment amount."""
    commission_percent: decimal.Decimal = msgspec.field(name="porcentaje_comision")
    """Commission percentage applied."""
    title: str | None = msgspec.field(default=None, name="titulo")
    """Payment method title."""
    description: str | None = msgspec.field(default=None, name="descripcion")
    """Payment method description."""


class BasicItem(msgspec.Struct, kw_only=True):
    """Base structure for an order item."""

    quantity: int = msgspec.field(name="cantidad")
    """Quantity of the product or service."""
    description: str = msgspec.field(name="descripcion")
    """Description of the product or service."""
    image_url: str = msgspec.field(default="", name="url_imagen")
    """Product image URL (optional)."""
    name: str = msgspec.field(name="nombre")
    """Name of the product or service."""
    product_id: int = msgspec.field(name="id_producto")
    """Product or service identifier."""
    total_price: int = msgspec.field(name="precio_total")
    """Total price for this item (quantity included)."""


class Item(BasicItem, kw_only=True):
    """Order item with courier and seller information."""

    category_id: str = msgspec.field(default="909", name="categoria")
    """Courier service category ID (optional)."""
    city_id: str = msgspec.field(default="1", name="ciudad")
    """Buyer city identifier (optional)."""
    seller_address: str = msgspec.field(default="", name="vendedor_direccion")
    """Seller address (optional)."""
    seller_address_ref: str = msgspec.field(default="", name="vendedor_direccion_referencia")
    """Seller address reference."""
    seller_address_coordinates: str = msgspec.field(
        default="", name="vendedor_direccion_coordenadas"
    )
    """Seller address coordinates."""
    seller_phone: str = msgspec.field(default="", name="vendedor_telefono")
    """Seller phone number (optional)."""
    seller_public_key: str = msgspec.field(name="public_key")
    """Seller public key."""


class OrderMessage(msgspec.Struct):
    """Represents a payment result message."""

    description: str = msgspec.field(name="descripcion")
    """HTML content of the message."""
    title: str = msgspec.field(name="titulo")
    """Message title."""


class Order(msgspec.Struct):
    """Represents a Pagopar order."""

    amount: str = msgspec.field(name="monto")
    """Transaction amount."""
    cancelled: bool = msgspec.field(name="cancelado")
    """Indicates whether the order was cancelled."""
    max_payment_date: str = msgspec.field(name="fecha_maxima_pago")
    """Payment deadline (ISO 8601)."""
    order_id: str = msgspec.field(name="hash_pedido")
    """Unique order hash."""
    order_number: str = msgspec.field(name="numero_pedido")
    """Commerce order number."""
    paid: bool = msgspec.field(name="pagado")
    """Indicates whether the order was paid."""
    payment_date: str | None = msgspec.field(name="fecha_pago")
    """Payment date (ISO 8601), if paid."""
    payment_message: OrderMessage = msgspec.field(name="mensaje_resultado_pago")
    """Payment result message."""
    payment_method_id: str = msgspec.field(name="forma_pago_identificador")
    """Payment method identifier."""
    payment_method_name: str = msgspec.field(name="forma_pago")
    """Payment method name."""
    token: str
    """Order security token."""
    extra_data: dict[str, _Any] | None = msgspec.field(default=None, name="datos_adicionales")


class Transaction(msgspec.Struct):
    """Transaction initialization response."""

    order_id: str = msgspec.field(name="data")
    """Pagopar order identifier."""
    order_num: str = msgspec.field(name="pedido")
    """Commerce order number."""


async def start_transaction(
    commerce_order_id: str,
    items: _Collection[Item],
    amount: int,
    payment_type: _enums.PaymentType,
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
    description: str | None = None,
    app: _app.Application | None = None,
) -> Transaction:
    """
    Create and initialize a Pagopar transaction in local currency (PYG).

    Parameters
    ----------
    commerce_order_id : str
        Commerce order identifier. Must be unique across environments.
    items : Collection[Item]
        List of products or services included in the order.
    amount : int
        Total transaction amount in Paraguayan Guaraníes (PYG).
    payment_type : PaymentType
        Payment method to be used.
    max_payment_date : datetime.datetime
        Deadline for completing the payment.
    buyer_name : str
        Buyer's full name.
    buyer_email : str
        Buyer's email address.
    buyer_phone : str
        Buyer's phone number in international format.
    buyer_document : str
        Buyer identification number (CI, CPF, or CNPJ depending on payment method).
    buyer_document_type : DocumentType
        Buyer document type.
    buyer_ruc : str, optional
        Buyer tax identification number.
    buyer_legal_name : str, optional
        Buyer legal name or business name.
    buyer_city_id : str, optional
        Buyer city ID (required for courier services).
    buyer_address : str, optional
        Buyer address.
    buyer_address_ref : str, optional
        Additional address reference.
    buyer_address_coordinates : str, optional
        Geographical coordinates of the buyer address.
    description : str, optional
        Short order description.
    app : Application, optional
        Pagopar application configuration.

    Returns
    -------
    Transaction
        Initialized transaction information.

    Raises
    ------
    ValueError
        If the item list is empty.
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network error occurs.
    msgspec.DecodeError
        If the response cannot be decoded.
    """
    if not items:
        raise ValueError("Empty item list")

    order_type = _enums.OrderType.SIMPLE
    if len({item.seller_public_key for item in items}) > 1:
        order_type = _enums.OrderType.SPLIT_BILLING

    response = await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="comercios/2.0/iniciar-transaccion",
        token_data=str(amount),
        response_type=list[Transaction],
        payload={
            "monto_total": amount,
            "tipo_pedido": order_type,
            "fecha_maxima_pago": max_payment_date.isoformat(" "),
            "id_pedido_comercio": commerce_order_id,
            "descripcion_resumen": description or "",
            "forma_pago": payment_type,
            "comprador": {
                "nombre": buyer_name,
                "email": buyer_email,
                "telefono": buyer_phone,
                "documento": buyer_document,
                "tipo_documento": buyer_document_type,
                "ruc": buyer_ruc or "",
                "razon_social": buyer_legal_name or "",
                "ciudad": buyer_city_id or "1",
                "direccion": buyer_address or "",
                "direccion_referencia": buyer_address_ref or "",
                "coordenadas": buyer_address_coordinates or "",
            },
            "compras_items": items,
        },
        app=app,
    )

    return response[0]


async def start_transaction_in_usd(
    order_id: str,
    items: _Sequence[BasicItem],
    amount: int,
    payment_type: _enums.PaymentType,
    buyer_name: str,
    buyer_email: str,
    buyer_phone: str,
    buyer_document: str,
    buyer_ruc: str = "",
    buyer_legal_name: str = "",
    buyer_pays_commission: bool = True,
    description: str | None = None,
    app: _app.Application | None = None,
) -> Transaction:
    """
    Create and initialize a Pagopar transaction in foreign currency (USD).

    Parameters
    ----------
    order_id : str
        Commerce order identifier. Must be unique across environments.
    items : Sequence[BasicItem]
        List of products or services included in the order.
    amount : int
        Total transaction amount in United States Dollars (USD).
    payment_type : PaymentType
        Payment method to be used.
    buyer_name : str
        Buyer's full name.
    buyer_email : str
        Buyer's email address.
    buyer_phone : str
        Buyer's phone number in international format.
    buyer_document : str
        Buyer identification number (CI, CPF, or CNPJ depending on payment method).
    buyer_ruc : str, optional
        Buyer tax identification number.
    buyer_legal_name : str, optional
        Buyer legal or business name.
    buyer_pays_commission : bool, optional
        Indicates whether the payment commission is transferred to the buyer.
    description : str, optional
        Short order description.
    app : Application, optional
        Pagopar application configuration.

    Returns
    -------
    Transaction
        Initialized transaction information.

    Raises
    ------
    ValueError
        If the item list is empty.
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network error occurs.
    msgspec.DecodeError
        If the response cannot be decoded.
    """
    if not items:
        raise ValueError("Empty item list")

    response = await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="comercios/2.0/iniciar-transaccion-divisa",
        token_data=str(amount),
        response_type=list[Transaction],
        payload={
            "comprador": {
                "ruc": buyer_ruc,
                "email": buyer_email,
                "nombre": buyer_name,
                "telefono": buyer_phone,
                "documento": buyer_document,
                "razon_social": buyer_legal_name,
            },
            "monto_total": amount,
            "moneda": "USD",
            "comision_transladada_comprador": buyer_pays_commission,
            "compras_items": items,
            "id_pedido_comercio": order_id,
            "descripcion_resumen": description or "",
            "forma_pago": payment_type,
        },
        app=app,
    )

    return response[0]


def pagopar_checkout_url(
    order_id: str,
    payment_type: _enums.PaymentType | None = None,
) -> str:
    """
    Generate the Pagopar checkout redirection URL.

    Parameters
    ----------
    order_id : str
        Pagopar order identifier returned after initializing a transaction.
    payment_type : PaymentType, optional
        Preselected payment method. Available only for approved merchants and
        allows skipping the Pagopar payment method selection screen.

    Returns
    -------
    str
        Checkout redirection URL.
    """
    url = f"https://www.pagopar.com/pagos/{order_id}"
    if payment_type:
        url += f"?forma_pago={payment_type.value}"
    return url


async def get_payment_methods(
    app: _app.Application | None = None,
) -> list[PaymentMethod]:
    """
    Retrieve the list of available payment methods.

    Parameters
    ----------
    app : Application, optional
        Pagopar application configuration.

    Returns
    -------
    list[PaymentMethod]
        Available payment methods for the merchant.

    Raises
    ------
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network error occurs.
    msgspec.DecodeError
        If the response cannot be decoded.
    """
    return await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="forma-pago/1.1/traer/",
        token_data="FORMA-PAGO",
        response_type=list[PaymentMethod],
        payload={},
        key_public_token="token_publico",
        app=app,
    )


def check_pagopar_payment(token: str, order_id: str) -> bool:
    """
    Validate a Pagopar payment notification token.

    Parameters
    ----------
    token : str
        Token received from Pagopar payment notification.
    order_id : str
        Merchant order identifier associated with the token.

    Returns
    -------
    bool
        True if the token is valid, otherwise False.
    """
    return token == _http.create_token(order_id)


async def get_order(order_id: str, app: _app.Application | None = None) -> Order:
    """
    Retrieve the current status and details of an order.

    Parameters
    ----------
    order_id : str
        Pagopar order identifier.
    app : Application, optional
        Pagopar application configuration.

    Returns
    -------
    Order
        Updated order information.

    Raises
    ------
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network error occurs.
    msgspec.DecodeError
        If the response cannot be decoded.
    """
    response = await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="pedidos/1.1/traer",
        token_data="CONSULTA",
        response_type=list[Order],
        payload={"hash_pedido": order_id, "datos_adicionales": True},
        key_public_token="token_publico",
        app=app,
    )
    return response[0]


class ReverseType(enum.Enum):
    """Defines when the reversal will be executed."""

    INMEDIATLY = "Inmediata"
    PROGRAMED = "Agendada"


class ReversedOrder(msgspec.Struct):
    """
    Represents the result of a paid order reversal request.
    """

    payment_method_id: str = msgspec.field(name="forma_pago")  # int
    """Payment method identifier used in the original transaction."""
    order_id: str = msgspec.field(name="hash")
    """Unique Pagopar order hash."""
    order_number: str = msgspec.field(name="pedido")  # int
    """Commerce order number."""
    transaction_id: str = msgspec.field(name="transaccion")
    """Transaction identifier, primarily for internal use."""
    transaction_status: str = msgspec.field(name="estado_transaccion")
    """Transaction status identifier, mainly for internal tracking."""
    reverse_type: ReverseType = msgspec.field(name="tiempo_reversion")
    """Indicates whether the reversal was processed immediately or scheduled for a later execution."""
    extra_data: dict[str, _Any] | None = msgspec.field(default=None, name="otros_datos")
    """Additional data returned by Pagopar, if any."""


async def reverse_paid_order(
    order_id: str,
    app: _app.Application | None = None,
) -> list[ReversedOrder]:
    """
    Request the reversal of a paid order.

    Order reversal is available only for payments made using:
    - Credit/debit cards processed through Bancard
    - Zimple
    - Tigo Money
    - Giros Claro
    - Wally
    - Billetera Personal

    If the reversal request is submitted on the same day the payment was made,
    the reversal may be processed immediately. Requests made on subsequent days
    will be scheduled for later execution.

    Even if the request is made late on the same day, Pagopar may still
    schedule the reversal instead of processing it immediately.

    Parameters
    ----------
    order_id : str
        Pagopar order identifier.
    app : Application, optional
        Pagopar application configuration.

    Returns
    -------
    list[Order]
        Reversal result information for the requested order.

    Raises
    ------
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network error occurs.
    msgspec.DecodeError
        If the response cannot be decoded.
    """
    return await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="pedidos/1.1/reversar",
        token_data="PEDIDO-REVERSAR",
        response_type=list[ReversedOrder],
        payload={
            "hash_pedido": order_id,
        },
        key_public_token="token_publico",
        app=app,
    )
