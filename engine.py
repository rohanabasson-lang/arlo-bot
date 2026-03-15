from policy import Policy

policy = Policy()


def price_job(scope):

    labour = scope.get("labour_hours", 0)
    materials = scope.get("material_cost", 0)
    equipment = scope.get("equipment_cost", 0)
    transport = scope.get("ancillary_cost", 0)

    # -------------------------
    # Direct cost
    # -------------------------

    direct_cost = labour + materials + equipment + transport

    # -------------------------
    # Overhead protection
    # -------------------------

    overhead = direct_cost * policy.overhead_pct

    # -------------------------
    # Risk buffer
    # -------------------------

    risk = direct_cost * policy.risk_pct

    # -------------------------
    # Protected cost
    # -------------------------

    protected_cost = direct_cost + overhead + risk

    # -------------------------
    # Target margin
    # -------------------------

    quote = protected_cost / (1 - policy.margin_pct)

    margin = policy.margin_pct * 100

    return {

        "direct": round(direct_cost, 2),
        "cost": round(protected_cost, 2),
        "quote": round(quote, 2),
        "margin": round(margin, 1)

    }