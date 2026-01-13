"""
Cliente para interactuar con la API de Pagopar Login.

Esta implementación se basó en el articulo proveido por Pagopar.
https://soporte.pagopar.com/portal/es/kb/articles/pagopar-login-29-8-2020

"""

import decimal
import urllib.parse

import aiohttp
import msgspec

from pagopar import _app, _http

__all__ = (
    "confirm_linking",
    "get_commerce",
    "get_linked_commerce",
    "linking_url",
)


class PaymentMethod(msgspec.Struct):
    id: str = msgspec.field(name="forma_pago")
    """Payment method identifier."""
    min_amount: int = msgspec.field(name="monto_minimo")
    """Minimum allowed amount for this payment method."""
    commission_percent: decimal.Decimal = msgspec.field(name="porcentaje_comision")
    """Commission percentage applied to the transaction."""
    method_type: str | None = msgspec.field(default=None, name="tipo")
    """Optional payment method type or category."""


class Plan(msgspec.Struct):
    plan_id: int = msgspec.field(name="plan")
    """Plan identifier."""
    description: str = msgspec.field(name="descripcion")
    """Human-readable plan description."""
    cost: int = msgspec.field(name="costo")
    """Plan cost."""
    next_billing_date: str = msgspec.field(name="fecha_siguiente_factura")
    """Next billing date in ISO 8601 format (e.g. '2020-08-01T12:36:56.685076')."""


class User(msgspec.Struct):
    email: str
    """User email address."""
    name: str = msgspec.field(name="nombre")
    """User name."""
    lastname: str = msgspec.field(name="apellido")
    """User last name."""
    phone: str = msgspec.field(name="celular")
    """User phone number."""
    balance: int = msgspec.field(name="saldo")
    """Current account balance."""
    document: int = msgspec.field(name="documento")
    """User identification document number."""
    balance_updated_at: str = msgspec.field(name="fecha_saldo_actualizacion")
    """Last balance update timestamp (ISO 8601)."""
    pending_collection_amount: int = msgspec.field(name="monto_pendiente_cobro")
    """Pending amount to be collected (can be negative)."""
    hash: str | None = msgspec.field(name="hash")
    "Optional user hash identifier."
    payment_status: str = msgspec.field(name="estado_pago")
    """Current payment status."""
    has_plan_payment: bool = msgspec.field(name="pago_plan")
    """Indicates if the plan payment is active."""
    has_card_payment: bool = msgspec.field(name="pago_tarjeta")
    """Indicates if card payments are enabled."""


class Order(msgspec.Struct):
    amount: int = msgspec.field(name="monto")
    """Order total amount."""
    description: str = msgspec.field(name="descripcion")
    """Order description."""
    max_payment_date: str = msgspec.field(name="fecha_maxima_pago")
    """Maximum allowed payment date (ISO 8601)."""
    state: str = msgspec.field(name="estado")
    """Current order state."""
    url: str
    """Order payment or detail URL."""


class Commerce(msgspec.Struct):
    description: str = msgspec.field(name="descripcion")
    """Commerce description."""
    commission_percent: decimal.Decimal = msgspec.field(name="porcentaje_comision")
    """Commission percentage applied to the commerce."""
    legal_name: str = msgspec.field(name="razon_social")
    """Registered legal name."""
    ruc: str
    """Registro Único de Contribuyentes or Single Taxpayer Registry (RUC)."""
    payment_mode_label: str = msgspec.field(name="modo_pago_denominacion")
    """Payment mode label."""
    has_services: bool = msgspec.field(name="servicios")
    """Indicates if services are enabled."""
    local_withdrawal: bool = msgspec.field(name="retiro_local")
    """Indicates if local withdrawal is available."""
    own_shipping: bool = msgspec.field(name="envio_propio")
    """Indicates if the commerce uses its own shipping."""
    commerce_id: int = msgspec.field(name="comercio")
    """Commerce identifier."""
    ranking: int
    """Commerce ranking score."""
    payment_mode: int = msgspec.field(name="modo_pago")
    """Payment mode identifier."""
    contract_signed: bool = msgspec.field(name="contrato_firmado")
    """Indicates if the contract is signed."""
    sales_link_permission: bool = msgspec.field(name="permisos_link_venta")
    """Indicates if sales link usage is allowed."""
    environment: str = msgspec.field(name="entorno")
    """Operating environment (e.g. Staging, Production)."""
    sale_type: str = msgspec.field(name="tipo_venta")
    """Type of sale."""

    payment_methods: list[PaymentMethod] = msgspec.field(name="forma_pago")
    """Available payment methods."""
    plan: Plan
    """Associated billing plan."""
    user: User = msgspec.field(name="usuario")
    """Associated user account."""
    pending_orders: list[Order] = msgspec.field(name="pedidos_pendientes")
    """List of pending orders."""


def linking_url(
    hash_comercio: str,
    usuario_id: str,
    url_redirect: str,
    plan: int | None = None,
) -> str:
    """
    Once the client clicks the linking URL, they will see the Pagopar Login page,
    where they can log in or register their Pagopar account.

    1. If the user logs in: their account is automatically linked and they are
        redirected to the previously defined `url_redirect`.

    2. If the user decides to register: they complete their information, log in,
        and may be asked to upload some documents. After that, they are redirected
        to the previously defined `url_redirect`.

    Parameters
    ----------
    hash_comercio : str
        Public key of the parent commerce.
    usuario_id : str
        User/account ID on the parent commerce website.
    url_redirect : str
        URL where the user will be redirected after the linking process.
        The redirection will include an additional parameter `hash_comercio`,
        which is the public key of the child commerce.
    plan : int, optional
        Pagopar plan the user will subscribe to. Available plans can be found at
        https://www.pagopar.com/planes

    Returns
    -------
    str
        The account linking URL.
    """
    data: dict[str, str] = {
        "hash_comercio": hash_comercio,
        "usuario_id": usuario_id,
        "url_redirect": url_redirect,
    }
    if plan is not None:
        data["plan"] = str(plan)
    query = urllib.parse.urlencode(data)
    return f"https://www.pagopar.com/v1.0/pagopar-login/login/?{query}"


async def confirm_linking(
    public_token: str,
    user_id: int,
    app: _app.Application | None = None,
) -> Commerce:
    """
    After returning from the linking URL and landing on the commerce page,
    the linking must be confirmed. This finalizes the linking process.

    Parameters
    ----------
    public_token : str
        Linked commerce public token provided by Pagopar.
    user_id : int
        User/account ID on the parent commerce website.
    app : Application, opcional
        Pagopar commerce config.

    Returns
    -------
    Comercio
        Child commerce data.

    Raises
    ------
    PagoparError
        If Pagopar rejects the linking.
    aiohttp.ClientResponseError
        If a network error occurs.
    msgspec.DecodeError
        If the Pagopar response cannot be processed.
    """
    # TODO: de donde se consigue el token del comericio hijo?
    return await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="pagopar-login/2.0/confirmar-vinculacion/",
        token_data="PAGOPAR-LOGIN",
        response_type=Commerce,
        payload={
            "token_comercio_hijo": public_token,
            "usuario_id": user_id,
        },
        app=app,
    )


async def get_linked_commerce(
    public_token: str,
    user_id: int,
    app: _app.Application | None = None,
) -> Commerce:
    """
    Retrieve linked commerce data in real time.

    Parameters
    ----------
    token_comercio_hijo : str
        Public linked commerce token.
    user_id : int
        User/account ID on the parent commerce website.
    app : Application, opcional
        Pagopar commerce configuration.

    Returns
    -------
    Comercio
        Child commerce data.

    Raises
    ------
    PagoparError
        When Pagopar rejects the request.
    aiohttp.ClientResponseError
        When a network error occurs.
    msgspec.DecodeError
        When the Pagopar response cannot be processed.
    """
    return await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="pagopar-login/2.0/datos-comercio/",
        token_data="PAGOPAR-LOGIN",
        response_type=Commerce,
        payload={
            "token_comercio_hijo": public_token,
            "usuario_id": user_id,
        },
        app=app,
    )


async def get_commerce(app: _app.Application | None = None) -> Commerce:
    """
    Retrieve commerce data in real time.

    Parameters
    ----------
    app : Application, opcional
        Pagopar commerce configuration.

    Returns
    -------
    Comercio
        Commerce data.

    Raises
    ------
    PagoparError
        When Pagopar rejects the request.
    aiohttp.ClientResponseError
        When a network error occurs.
    msgspec.DecodeError
        When the Pagopar response cannot be processed.
    """
    return await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="comercios/2.0/datos-comercio/",
        token_data="DATOS-COMERCIO",
        response_type=Commerce,
        payload={},
        app=app,
    )
