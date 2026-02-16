# Pagopar

Client to consume pagopar.com REST API, created based on [official documentation](https://soporte.pagopar.com/portal/es/kb).

Asynchronous Python wrapper for the Pagopar API, designed for efficiency and type safety.

## Installation

```bash
pip install pagopar
```

## Configuration

You can configure the application by passing your credentials directly or by using environment variables.

### Environment Variables

Set the following environment variables:

- `PAGOPAR_PRIVATE_TOKEN`
- `PAGOPAR_PUBLIC_TOKEN`

### Manual Initialization

```python
from pagopar import initialize_app

app = initialize_app(
    private_token="your_private_token",
    public_token="your_public_token"
)
```

## Usage Examples

### Initialize Application

```python
import asyncio
from pagopar import initialize_app, close_app

# Initialize with environment variables or pass tokens here
app = initialize_app()

async def main():
    # Your logic here
    await close_app()

if __name__ == "__main__":
    asyncio.run(main())
```

### Create a Transaction

Generate a payment link for a user.

```python
import datetime
from pagopar import checkout, _enums

async def create_order():
    # Define items
    item = checkout.Item(
        name="Product Name",
        description="Product Description",
        price=150000,
        quantity=1,
        total_price=150000,
        product_id=123,
        image_url="https://example.com/image.png"
    )

    # Start transaction
    transaction = await checkout.start_transaction(
        commerce_order_id="ORDER-001",
        items=[item],
        amount=150000,
        payment_type=_enums.PaymentType.PAGO_EXPRESS,
        max_payment_date=datetime.datetime.now() + datetime.timedelta(days=1),
        buyer_name="John Doe",
        buyer_email="john.doe@example.com",
        buyer_phone="0981123456",
        buyer_document="1234567",
        buyer_document_type=_enums.DocumentType.CI
    )

    # Get checkout URL
    url = checkout.pagopar_checkout_url(transaction.order_id)
    print(f"Checkout URL: {url}")
```

### Check Payment Status

Validate if a payment notification is authentic.

```python
from pagopar import checkout

def validate_pagopar_notification(notification_token: str, order_id: str) -> bool:
    return checkout.check_pagopar_payment(notification_token, order_id)
```

### Get Order Details

Retrieve the current status of an order.

```python
async def check_order_status(order_hash: str):
    order = await checkout.get_order(order_hash)
    print(f"Order Status: {'Paid' if order.paid else 'Pending'}")
```

## Modules

- **checkout**: Transaction initialization, payment link generation, and order status checking.
- **courier**: Integration with shipping providers (AEX, Mobi) and freight calculation.
- **login**: Pagopar Login / Registration linking flow.
- **payment**: Recurring payments and tokenized card management.
- **subs**: Subscription notifications parsing.
- **sync**: Product and inventory synchronization with Pagopar.
