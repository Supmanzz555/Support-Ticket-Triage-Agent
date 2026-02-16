"""Customer profile lookup tool."""
from typing import Optional


def get_customer_profile(
    customer_plan: str,
    tenure_months: int,
    region: Optional[str] = None,
) -> dict:
    """
    Get customer profile info (form mock data )
    """
    # Mocked logic based on plan and tenure
    is_vip = (
        customer_plan == "enterprise" or
        tenure_months >= 12 or
        (customer_plan == "pro" and tenure_months >= 6)
    )
    
    # Approximate MRR based on plan
    mrr_map = {
        "free": 0,
        "pro": 29.99,
        "enterprise": 299.99,
    }
    mrr = mrr_map.get(customer_plan.lower(), 0)
    
    # Risk indicators
    at_risk = (
        customer_plan == "free" and tenure_months >= 6 and tenure_months <= 8
    )
    
    return {
        "plan": customer_plan,
        "tenure_months": tenure_months,
        "region": region,
        "is_vip": is_vip,
        "mrr_dollars": mrr,
        "at_risk": at_risk,
    }
