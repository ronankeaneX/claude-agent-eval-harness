"""Stub lookup tools the triage agent can choose to consult."""

FAKE_CUSTOMERS = {
    "cust_001": {"plan": "pro", "prior_tickets": 0, "refunds_last_90d": 0},
    "cust_002": {"plan": "free", "prior_tickets": 7, "refunds_last_90d": 3},
    "cust_003": {"plan": "enterprise", "prior_tickets": 1, "refunds_last_90d": 0},
}

FAKE_OUTAGES = {
    "billing_portal": {"active": True, "since": "2026-07-27T06:00Z", "note": "Payment processor degraded"},
    "email": {"active": False, "since": None, "note": None},
    "api": {"active": False, "since": None, "note": None},
}


def get_customer_history(customer_id: str) -> dict:
    """Return account context for a customer, or a not-found marker."""
    if customer_id in FAKE_CUSTOMERS:
        return FAKE_CUSTOMERS[customer_id]
    return {"error": "customer_not_found", "customer_id": customer_id}

def check_known_outages(service: str) -> dict:
    """Return outage status for a service, or a not-found marker."""
    if service in FAKE_OUTAGES:
        return FAKE_OUTAGES[service]
    return {"error": "service_not_found", "service": service}