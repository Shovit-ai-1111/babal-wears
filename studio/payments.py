from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass(frozen=True)
class GatewaySession:
    reference: str
    redirect_url: str


class PaymentGateway(ABC):
    """Boundary for a future provider adapter; amounts must come from the saved order."""
    @abstractmethod
    def initiate(self, *, order_number: str, amount_paisa: int, return_url: str) -> GatewaySession:
        raise NotImplementedError("Implement the provider's authenticated initiation API.")

    @abstractmethod
    def verify(self, *, reference: str, amount_paisa: int) -> bool:
        raise NotImplementedError("Implement server-to-server amount, currency and reference verification.")


class GatewayNotConfigured(RuntimeError):
    pass


class DisabledGateway(PaymentGateway):
    """Intentionally disabled, never returns a fake payment success."""
    def initiate(self, *, order_number, amount_paisa, return_url):
        raise GatewayNotConfigured("Automatic payment gateways are not configured. Use QR proof or COD.")

    def verify(self, *, reference, amount_paisa):
        raise GatewayNotConfigured("Only an authenticated server-to-server adapter may verify a payment.")


gateway = DisabledGateway()
