```instructions
---
applyTo: "**/*.py"
---

# Coding Conventions — Comments

## RULE: Every Function Must Have a Docstring

Every function — public or private — MUST have a Google-style docstring.

```python
def download_invoice(order_id: str, session: requests.Session) -> Path:
    """Download the invoice PDF for a single order.

    Args:
        order_id: The AliExpress order ID.
        session: Authenticated requests session.

    Returns:
        Path to the saved PDF file.

    Raises:
        InvoiceNotFoundError: If no invoice is available for the order.
    """
```

### Docstring Checklist

1. One-line summary — imperative mood ("Download …", not "Downloads …").
2. `Args:` — one per parameter with type implied by annotation.
3. `Returns:` — describe what the return value means (omit for `None`).
4. `Raises:` — list exceptions the caller should expect.

## RULE: Module-Level Docstring

Every `.py` file MUST start with a module docstring describing its purpose.
```
