def detect_leak(user_price,recommended_price):

    if user_price >= recommended_price:
        return None

    leak = recommended_price - user_price

    if leak > 10000:
        severity = "HIGH"
    else:
        severity = "MEDIUM"

    return {

        "severity":severity,
        "lost_profit":round(leak,2)

    }