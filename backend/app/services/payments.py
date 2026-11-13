import uuid
from decimal import Decimal


class PaymentGatewayInterface:
    async def payout(self, customer_id: uuid.UUID, order_id: uuid.UUID, amount: Decimal) -> dict:
        raise NotImplementedError


class MockPaymentGateway(PaymentGatewayInterface):
    """Mock payment gateway that simulates an instant refund payout."""

    async def payout(self, customer_id: uuid.UUID, order_id: uuid.UUID, amount: Decimal) -> dict:
        return {
            "status": "success",
            "transaction_id": f"txn_mock_{uuid.uuid4().hex[:12]}",
            "amount": str(amount),
            "gateway": "mock_payout_gateway",
        }
