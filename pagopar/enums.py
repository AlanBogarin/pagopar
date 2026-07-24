import enum

__all__ = ("DocumentType", "OrderType", "PaymentType")


class PaymentType(enum.Enum):
    """
    Enumeration of supported payment methods.

    Includes credit cards, wallets, and cash payment networks.
    """
    PROCARD = 1
    """(Accepts Visa, Mastercard, Credicard and Unica)"""
    AQUI_PAGO = 2
    PAGO_EXPRESS = 3
    PRACTIPAGO = 4
    BANCARD = 9
    """(Accepts Visa, Mastercard, American Express, Discover, Diners Club and Credifielco.)"""
    TIGO_MONEY = 10
    TRANSFERENCIA_BANCARIA = 11
    BILLETERA_PERSONAL = 12
    PAGO_MOVIL = 13
    INFONET = 15
    ZIMPLE = 18
    WALLY = 20
    WEPA = 22
    GIROS_CLARO = 23
    PAGO_QR = 24
    PIX = 25


class DocumentType(enum.Enum):
    """Supported identity document types."""
    CI = "CI"


class OrderType(enum.Enum):
    """
    Enumeration of order types.

    Distinguishes between simple direct sales and split billing scenarios.
    """
    SIMPLE = "VENTA-COMERCIO"
    SPLIT_BILLING = "COMERCIO-HEREDADO"
