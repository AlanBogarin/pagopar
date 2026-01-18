import enum
import urllib.parse
from typing import Literal

import aiohttp
import msgspec

from pagopar import _app, _http

__all__ = ()


class CardType(enum.StrEnum):
    """Supported card types returned by Pagopar."""
    CREDIT = "Crédito"
    DEBIT = "Débito"
    PREPAID = "Prepaga"


class BandcardIFrameStyle(msgspec.Struct):
    """Visual customization options for the Bancard card registration iframe."""
    button_background_color: str = msgspec.field(default="#5CB85C", name="button-background-color")
    """Background color of the submit button."""
    button_border_color: str = msgspec.field(default="#4CAE4C", name="button-border-color")
    """Border color of the submit button."""
    button_text_color: str = msgspec.field(default="#FFFFFF", name="button-text-color")
    """Text color of the submit button."""
    form_background_color: str = msgspec.field(default="#FFFFFF", name="form-background-color")
    """Background color of the iframe form."""
    form_border_color: str = msgspec.field(default="#DDDDDD", name="form-border-color")
    """Border color of the iframe form."""
    header_background_color: str = msgspec.field(default="#F5F5F5", name="header-background-color")
    """Background color of the form header."""
    header_text_color: str = msgspec.field(default="#333333", name="header-text-color")
    """Text color of the form header."""
    hr_border_color: str = msgspec.field(default="#EEEEEE", name="hr-border-color")
    """Color of horizontal separator lines."""
    input_background_color: str = msgspec.field(default="#FFFFFF", name="input-background-color")
    """Background color of input fields."""
    input_border_color: str = msgspec.field(default="#CCCCCC", name="input-border-color")
    """Border color of input fields."""
    input_placeholder_color: str = msgspec.field(default="#999999", name="input-placeholder-color")
    """Placeholder text color of input fields."""
    input_text_color: str = msgspec.field(default="#555555", name="input-text-color")
    """Text color of input fields."""
    label_kyc_text_color: str = msgspec.field(default="#000000", name="label-kyc-text-color")
    """Text color of KYC-related labels."""


class Client(msgspec.Struct):
    """Represents a Pagopar-registered customer."""
    buyer_id: str = msgspec.field(name="id_comprador_comercio")
    fullname: str = msgspec.field(name="nombres_apellidos")
    email: str
    phone: str = msgspec.field(name="celular")


class Card(msgspec.Struct):
    """Represents a stored payment card."""
    alias_token: str
    brand: str = msgspec.field(name="marca")
    card_id: str = msgspec.field(name="tarjeta")
    card_issuer: str = msgspec.field(name="emisor")
    card_number: str = msgspec.field(name="tarjeta_numero")
    card_type: CardType = msgspec.field(name="tipo_tarjeta")
    logo_url: str = msgspec.field(name="url_logo")
    provider: str = msgspec.field(name="proveedor")


class PreAuthorize(msgspec.Struct):
    """Represents a preauthorization response."""
    pagopar_transaction_id: str = msgspec.field(name="transaccion")
    receipt: str = msgspec.field(name="comprobante_interno")


async def add_client(
    commerce_client_id: int,
    fullname: str,
    email: str,
    phone: str,
    app: _app.Application | None = None,
) -> Client:
    """
    Registers a customer in Pagopar for recurring payments.

    This operation must be executed before registering a card for the first
    time. Repeated calls using the same identifier are safe but unnecessary.

    Parameters
    ----------
    commerce_client_id : int
        Unique customer identifier in the commerce system.
    fullname : str
        Customer full name.
    email : str
        Customer email address.
    phone : str
        Customer mobile phone number.
    app : Application, optional
        Pagopar commerce configuration.

    Returns
    -------
    Client
        The registered customer data.

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
        path="pago-recurrente/3.0/agregar-cliente/",
        token_data="PAGO-RECURRENTE",
        response_type=Client,
        payload={
            "identificador": commerce_client_id,
            "nombre_apellido": fullname,
            "email": email,
            "celular": phone,
        },
        key_public_token="token_publico",
        app=app,
    )


async def add_card(
    commerce_client_id: int,
    commerce_checkout_url: str,
    provider: Literal["uPay", "Bancard"],
    app: _app.Application | None = None,
) -> str:
    """
    Initiates the card registration process for a previously registered customer.

    Parameters
    ----------
    commerce_client_id : int
        Unique customer identifier in the commerce system.
    commerce_checkout_url : str
        URL where the customer will be redirected after completing
        the card registration process.
    provider : {"uPay", "Bancard"}
        Card registration provider.
    app : Application, optional
        Pagopar commerce configuration.

    Returns
    -------
    str
        Alias token generated by the selected provider.

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
        path="pago-recurrente/3.0/agregar-tarjeta/",
        token_data="",
        response_type=str,
        payload={
            "url": commerce_checkout_url,
            "proveedor": provider,
            "identificador": commerce_client_id,
        },
        key_public_token="token_publico",
        app=app,
    )


# https://github.com/Bancard/bancard-connectors/blob/master/vpos/checkout/javascript
def add_card_bancard_iframe(
    alias_token: str,
    style: BandcardIFrameStyle | None = None,
    environment: Literal["development", "production", "sandbox"] = "production",
) -> str:
    """
    Builds the Bancard iframe URL for card registration.

    This is functionally equivalent to calling
    ``Bancard.Cards.createForm`` from `bancard-checkout.js` v5.0.1.

    Parameters
    ----------
    alias_token : str
        Token returned by :func:`add_card`.
    style : BandcardIFrameStyle, optional
        Visual customization options for the iframe.
    environment : {"development", "production", "sandbox"}, optional
        Target environment.

    Returns
    -------
    str
        Fully qualified iframe URL.

    Raises
    ------
    ValueError
        If an invalid environment is provided.
    """
    if style is None:
        style = BandcardIFrameStyle()
    query = urllib.parse.urlencode(
        {"process_id": alias_token, "styles": msgspec.json.encode(style)}
    )
    if environment == "production":
        hostname = "vpos.infonet.com.py"
    elif environment == "sandbox":
        hostname = "vpos.infonet.com.py:8888"
    elif environment == "development":
        hostname = "desa.infonet.com.py:8085"
    else:
        raise ValueError("Invalid environment")
    return f"https://{hostname}/checkout/register_card/new?{query}"


def add_card_upay_iframe(alias_token: str) -> str:
    """
    Builds the uPay iframe URL for card registration.

    Parameters
    ----------
    alias_token : str
        Token returned by :func:`add_card`.

    Returns
    -------
    str
        Fully qualified iframe URL.
    """
    return f"https://www.pagopar.com/upay-iframe/?id-form={alias_token}"


async def confirm_card(
    commerce_client_id: int,
    commerce_checkout_url: str,
    app: _app.Application | None = None,
) -> None:
    """
    Confirms a previously registered card after the iframe flow completes.

    This endpoint must be called once the customer finishes the card
    registration process and is redirected back to the commerce site.

    Parameters
    ----------
    commerce_client_id : int
        Unique customer identifier in the commerce system.
    commerce_checkout_url : str
        Redirect URL used during the card registration process.
    app : Application, optional
        Pagopar commerce configuration.

    Raises
    ------
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network-level error occurs.
    msgspec.DecodeError
        If the response cannot be decoded.
    """
    # returns Literal['Ok']
    await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="pago-recurrente/3.0/confirmar-tarjeta/",
        token_data="PAGO-RECURRENTE",
        response_type=str,
        payload={"url": commerce_checkout_url, "identificador": commerce_client_id},
        key_public_token="token_publico",
        app=app,
    )


async def get_cards(
    commerce_client_id: int,
    app: _app.Application | None = None,
) -> list[Card]:
    """
    Retrieves all cards previously registered for a customer.

    This endpoint must be called before performing operations such as
    payment or card deletion, as it returns temporary alias tokens
    required for those actions.

    Parameters
    ----------
    commerce_client_id : int
        Unique customer identifier in the commerce system.
    app : Application, optional
        Pagopar commerce configuration.

    Returns
    -------
    list[Card]
        List of cards registered for the customer.

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
        path="pago-recurrente/3.0/listar-tarjeta/",
        token_data="PAGO-RECURRENTE",
        response_type=list[Card],
        payload={
            "identificador": commerce_client_id,
        },
        key_public_token="token_publico",
        app=app,
    )


async def delete_card(
    commerce_client_id: int,
    card_alias_token: str,
    app: _app.Application | None = None,
) -> None:
    """
    Deletes a previously registered card.

    Since card alias tokens are temporary, the card list must be retrieved
    again before each deletion attempt.

    Parameters
    ----------
    commerce_client_id : int
        Unique customer identifier in the commerce system.
    card_alias_token : str
        Temporary alias token obtained from :func:`get_cards`.
    app : Application, optional
        Pagopar commerce configuration.

    Raises
    ------
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network-level error occurs.
    msgspec.DecodeError
        If the response cannot be decoded.
    """
    # returns Literal["Borrado"]
    await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="pago-recurrente/3.0/eliminar-tarjeta/",
        token_data="PAGO-RECURRENTE",
        response_type=str,
        payload={
            "identificador": commerce_client_id,
            "tarjeta": card_alias_token,
        },
        key_public_token="token_publico",
        app=app,
    )


async def pay(
    commerce_client_id: int,
    card_alias_token: str,
    order_id: str,
    app: _app.Application | None = None,
) -> None:
    """
    Executes a payment using a previously registered card.

    The card alias token must be retrieved from :func:`get_cards`
    immediately before performing the payment.

    Parameters
    ----------
    commerce_client_id : int
        Unique customer identifier in the commerce system.
    card_alias_token : str
        Temporary alias token obtained from :func:`get_cards`.
    order_id : str
        Pagopar order identifier.
    app : Application, optional
        Pagopar commerce configuration.

    Raises
    ------
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network-level error occurs.
    msgspec.DecodeError
        If the response cannot be decoded.
    """
    # returns Literal[""]
    await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="pago-recurrente/3.0/pagar/",
        token_data="PAGO-RECURRENTE",
        response_type=str,
        payload={
            "hash_pedido": order_id,
            "tarjeta": card_alias_token,
            "identificador": commerce_client_id,
        },
        key_public_token="token_publico",
        app=app,
    )


async def pre_authorize(
    card_id: str,
    amount: int,
    commerce_client_id: int,
    commerce_transaction_id: int,
    app: _app.Application | None = None,
) -> PreAuthorize:
    """
    Creates a card preauthorization, temporarily reserving funds.

    If the preauthorization is not confirmed within 30 days,
    it is automatically canceled by Pagopar.

    Parameters
    ----------
    card_id : str
        Numeric card identifier returned by :func:`get_cards`.
    amount : int
        Amount to be reserved.
    commerce_client_id : int
        Unique customer identifier in the commerce system.
    commerce_transaction_id : int
        Commerce-side transaction identifier.
    app : Application, optional
        Pagopar commerce configuration.

    Returns
    -------
    PreAuthorize
        Preauthorization metadata.

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
        path="pago-recurrente/3.0/preautorizar/",
        token_data="PAGO-RECURRENTE",
        response_type=PreAuthorize,
        payload={
            "tarjeta": card_id,
            "monto": amount,
            "id_transaccion": commerce_transaction_id,
            "identificador": commerce_client_id,
        },
        key_public_token="token_publico",
        app=app,
    )


async def confirm_preauthorization(
    order_id: str,
    pagopar_transaction_id: str,
    commerce_transaction_id: int,
    commerce_client_id: int,
    app: _app.Application | None = None,
) -> None:
    """
    Confirms a previously created preauthorization, capturing the funds.

    Parameters
    ----------
    order_id : str
        Pagopar order identifier.
    pagopar_transaction_id : str
        Transaction identifier returned by the preauthorization request.
    commerce_transaction_id : int
        Commerce-side transaction identifier.
    commerce_client_id : int
        Unique customer identifier in the commerce system.
    app : Application, optional
        Pagopar commerce configuration.

    Raises
    ------
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network-level error occurs.
    msgspec.DecodeError
        If the response cannot be decoded.
    """
    await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="pago-recurrente/3.0/confirmar-preautorizacion/",
        token_data="PAGO-RECURRENTE",
        response_type=str,
        payload={
            "hash_pedido": order_id,
            "transaccion": pagopar_transaction_id,
            "id_transaccion": commerce_transaction_id,
            "identificador": commerce_client_id,
        },
        key_public_token="token_publico",
        app=app,
    )


async def cancel_preauthorization(
    order_id: str,
    pagopar_transaction_id: str,
    commerce_transaction_id: int,
    commerce_client_id: int,
    app: _app.Application | None = None,
) -> str:
    """
    Cancels an existing preauthorization and releases reserved funds.

    Once canceled, a preauthorization cannot be confirmed.

    Parameters
    ----------
    order_id : str
        Pagopar order identifier.
    pagopar_transaction_id : str
        Transaction identifier returned by the preauthorization request.
    commerce_transaction_id : int
        Commerce-side transaction identifier.
    commerce_client_id : int
        Unique customer identifier in the commerce system.
    app : Application, optional
        Pagopar commerce configuration.

    Returns
    -------
    str
        Cancellation status returned by Pagopar.

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
        path="pago-recurrente/3.0/cancelar-preautorizacion/",
        token_data="PAGO-RECURRENTE",
        response_type=str,
        payload={
            "hash_pedido": order_id,
            "transaccion": pagopar_transaction_id,
            "id_transaccion": commerce_transaction_id,
            "identificador": commerce_client_id,
        },
        key_public_token="token_publico",
        app=app,
    )


async def personal_pay(
    order_id: str,
    phone: str,
    app: _app.Application | None = None,
) -> None:
    """
    Executes a payment using Personal Pay (Billetera Personal).

    Parameters
    ----------
    order_id : str
        Pagopar order identifier.
    phone : str
        Personal Pay phone number.
    app : Application, optional
        Pagopar commerce configuration.

    Raises
    ------
    PagoparError
        If Pagopar rejects the request.
    aiohttp.ClientResponseError
        If a network-level error occurs.
    msgspec.DecodeError
        If the response cannot be decoded.
    """
    # returns Literal["Transaccion aprobada."]
    await _http.send_request(
        method=aiohttp.hdrs.METH_POST,
        path="billetera-personal/1.0/pagar",
        token_data="pagar",
        response_type=str,
        payload={
            "hash_pedido": order_id,
            "celular": phone,
        },
        key_public_token="token_publico",
        app=app,
    )
