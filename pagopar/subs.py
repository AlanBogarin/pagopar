import enum

import msgspec


class NotifType(enum.Enum):
    """
    Enumeration of notification action types sent by Pagopar.

    This value indicates which subscription-related event triggered
    the notification.
    """

    SUB = "suscripcion"
    """Subscription creation event."""
    UNSUB = "desuscripcion"
    """Subscription cancellation event."""
    PAID = "pagado"
    """Successful subscription payment event."""


class User(msgspec.Struct):
    """
    Represents the user associated with a subscription notification.
    """

    token_id: str = msgspec.field(name="token_identificador")
    """Unique identifier token of the user."""
    name: str = msgspec.field(name="nombre")
    """User first name."""
    lastname: str = msgspec.field(name="apellido")
    """User last name."""
    email: str
    """User email address."""
    phone: str = msgspec.field(name="celular")
    """User mobile phone number."""
    document: str = msgspec.field(name="documento")
    """User identification document number."""
    legal_name: str = msgspec.field(name="razon_social")
    """Registered legal name of the user or business."""
    ruc: str
    """Tax identification number (RUC)."""


class Subscription(msgspec.Struct):
    """
    Represents subscription details included in a notification.
    """

    sub_id: str = msgspec.field(name="id")
    """Pagopar subscription link identifier."""
    sub_date: str = msgspec.field(name="fecha_suscripcion")
    """Date when the user subscribed."""
    sub_link: str = msgspec.field(name="link_suscripcion")
    """Subscription payment link identifier."""
    commerce_sub_id: str = msgspec.field(name="identificador_comercio")
    """Subscription identifier defined by the commerce."""
    amount: str = msgspec.field(name="monto")
    """Subscription amount charged to the user."""
    title: str = msgspec.field(name="titulo")
    """Current subscription title."""
    historical_title: str = msgspec.field(name="titulo_suscripcion")
    """Historical subscription title at the time of subscription."""
    status: str = msgspec.field(name="estado")
    """
    Current subscription status.

    Common values include ``Pendiente de Pago``, ``Cancelada``, and ``Pagada``.
    """
    debit_amount: str | None = msgspec.field(name="cantidad_debito")
    """Number of billing cycles already charged to the user."""
    visit_amount: str = msgspec.field(name="visitas")
    """Number of visits included or consumed by the subscription."""
    periodicity: str = msgspec.field(name="periodicidad")
    """
    Billing periodicity of the subscription.

    Example values include ``Mensual``.
    """
    payment_method_id: str = msgspec.field(name="identificador_forma_pago")
    """Identifier of the payment method selected at subscription time."""
    payment_method_title: str = msgspec.field(name="titulo_forma_pago")
    """Description of the payment method selected at subscription time."""
    validity: str = msgspec.field(name="vigencia")
    """Validity period of the subscription."""
    unsub_date: str | None = msgspec.field(default=None, name="fecha_desuscripcion")
    """Date when the user unsubscribed, if applicable."""


class Payment(msgspec.Struct):
    """
    Represents payment information associated with a subscription notification.

    This structure is only present for payment-related notifications.
    """

    order_id: str = msgspec.field(name="hash_pedido")
    """Pagopar order hash identifier."""
    receipt: str = msgspec.field(name="comprobante_interno")
    """Internal payment receipt number."""
    payment_date: str = msgspec.field(name="fecha_pago")
    """Date when the payment was completed."""
    payment_method_id: str = msgspec.field(name="identificador_forma_pago_transaccion")
    """Identifier of the payment method used in the transaction."""
    payment_method_title: str = msgspec.field(name="titulo_forma_pago_transaccion")
    """Description of the payment method used in the transaction."""


class Notification(msgspec.Struct, omit_defaults=True):
    """
    Represents a subscription-related notification sent by Pagopar.
    """

    notif_type: NotifType = msgspec.field(name="tipo_accion")
    """Action type that triggered the notification."""
    hashed_token: str = msgspec.field(name="token")
    """
    Verification hash generated using the commerce private token and
    the notification type.
    """
    user: User = msgspec.field(name="usuario")
    """User associated with the subscription."""
    subcription: Subscription = msgspec.field(name="suscripcion")
    """Subscription details."""
    payment: Payment | None = msgspec.field(default=None, name="pago")
    """Payment information, present only for payment notifications."""


def parse_notification(message: bytes | str) -> Notification:
    """
    Parse a subscription notification payload sent by Pagopar.

    Parameters
    ----------
    message : bytes or str
        Raw JSON payload received from Pagopar.

    Returns
    -------
    Notification
        Parsed notification object.

    Raises
    ------
    msgspec.DecodeError
        If the payload cannot be decoded or does not match the expected schema.
    """
    return msgspec.json.decode(message, type=Notification)
