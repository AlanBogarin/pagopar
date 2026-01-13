import enum

__all__ = ("DocumentType", "OrderType", "PaymentType")


class PaymentType(enum.Enum):
	PROCARD = 1
	"""(Acepta Visa, Mastercard, Credicard y Unica)"""
	AQUI_PAGO = 2
	PAGO_EXPRESS = 3
	PRACTIPAGO = 4
	BANCARD = 9
	"""(Acepta Visa, Mastercard, American Express, Discover, Diners Club y Credifielco.)"""
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
	CI = "CI"


class OrderType(enum.Enum):
	SIMPLE = "VENTA-COMERCIO"
	SPLIT_BILLING = "COMERCIO-HEREDADO"
