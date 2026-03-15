from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timedelta
import secrets
import re

from database import (
    init_db,
    get_or_create_user,
    update_user_industry,
    save_quote,
    get_recent_quotes,
)

app = Flask(__name__)
init_db()

# -----------------------------
# SESSION MEMORY + TTL
# -----------------------------
sessions = {}
SESSION_TTL_HOURS = 24

INDUSTRIES = {
    "1": "Construction",
    "2": "Electrical",
    "3": "Painting",
}


def cleanup_sessions():
    cutoff = datetime.now() - timedelta(hours=SESSION_TTL_HOURS)
    expired = [
        k for k, v in sessions.items()
        if v.get("last_active", datetime.now()) < cutoff
    ]
    for k in expired:
        del sessions[k]


def get_session(phone):
    cleanup_sessions()

    if phone not in sessions:
        sessions[phone] = {
            "industry": None,
            "state": "idle",
            "last_active": datetime.now(),
        }

    sessions[phone]["last_active"] = datetime.now()
    return sessions[phone]


# -----------------------------
# HELPERS
# -----------------------------
def make_quote_ref():
    return f"ARLO-{secrets.token_hex(3).upper()}"


def safe_float(value_str):
    if not value_str:
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", value_str)
    try:
        return float(cleaned)
    except Exception:
        return 0.0


def extract_costs(text: str):
    values = {
        "labour": 0.0,
        "materials": 0.0,
        "equipment": 0.0,
        "transport": 0.0,
    }

    lines = text.split("\n")
    for line in lines:
        clean = line.strip().lower()
        if not clean:
            continue

        match = re.search(r"(\d[\d,]*\.?\d*)", clean)
        if not match:
            continue

        value = safe_float(match.group(1))

        if any(k in clean for k in ["labour", "labor", "manhour", "crew"]):
            values["labour"] = value
        elif any(k in clean for k in ["material", "mat", "mats", "supply"]):
            values["materials"] = value
        elif any(k in clean for k in ["equip", "machine", "hire", "plant"]):
            values["equipment"] = value
        elif any(k in clean for k in ["trans", "delivery", "logistic", "cartage", "ancillary"]):
            values["transport"] = value

    return values


def calculate_quote(costs: dict):
    direct_cost = sum(costs.values())
    overhead = direct_cost * 0.19
    protected_cost = direct_cost + overhead
    margin = 0.30
    recommended_quote = protected_cost / (1 - margin)
    profit = recommended_quote - protected_cost

    return {
        "direct_cost": direct_cost,
        "protected_cost": protected_cost,
        "recommended_quote": recommended_quote,
        "profit": profit,
        "margin": margin,
    }


def twiml(text: str):
    resp = MessagingResponse()
    resp.message(text)
    return str(resp)


# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def home():
    return "ARLO is alive"


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip()
    phone = request.values.get("From", "unknown")
    txt = incoming_msg.lower()

    # DB user
    user = get_or_create_user(phone)

    # Session
    session = get_session(phone)
    if session["industry"] is None and user.get("industry"):
        session["industry"] = user["industry"]

    # -----------------------------
    # HELP / MENU
    # -----------------------------
    if txt in ["hi", "hello", "start", "menu", "help", "arlo"]:
        return twiml(
            "ARLO AI Pricing Assistant\n\n"
            "Commands:\n"
            "• industry → choose trade\n"
            "• reduce by XX% → test discount\n"
            "• generate quote → client version\n"
            "• history → last quotes\n"
            "• help → this menu"
        )

    # -----------------------------
    # INDUSTRY MENU
    # -----------------------------
    if "industry" in txt:
        session["state"] = "awaiting_industry"
        return twiml(
            "ARLO Industry Presets\n\n"
            "1 Construction\n"
            "2 Electrical\n"
            "3 Painting\n\n"
            "Reply with the number of your industry."
        )

    # -----------------------------
    # INDUSTRY SELECTION
    # -----------------------------
    if session["state"] == "awaiting_industry":
        choice = txt.strip()
        if choice in INDUSTRIES:
            industry = INDUSTRIES[choice]
            session["industry"] = industry
            session["state"] = "awaiting_costs"
            update_user_industry(phone, industry)

            return twiml(
                f"{industry} pricing drivers\n\n"
                "Labour hours\n"
                "Material cost\n"
                "Equipment hire\n"
                "Transport / logistics\n\n"
                "Example input:\n\n"
                "Labour 45000\n"
                "Materials 80000\n"
                "Equipment 12000\n"
                "Transport 5000"
            )
        return twiml("Please reply with 1, 2 or 3.")

    # -----------------------------
    # COST INPUT
    # -----------------------------
    costs = extract_costs(incoming_msg)
    total = sum(costs.values())

    if total > 0:
        quote_data = calculate_quote(costs)
        quote_ref = make_quote_ref()

        save_quote(
            phone=phone,
            ref=quote_ref,
            direct_cost=quote_data["direct_cost"],
            protected_cost=quote_data["protected_cost"],
            price=quote_data["recommended_quote"],
            profit=quote_data["profit"],
            margin=quote_data["margin"],
            raw_input=incoming_msg,
        )

        session["state"] = "quote_ready"

        return twiml(
            "ARLO Pricing Analysis\n\n"
            f"Reference: {quote_ref}\n"
            f"Industry: {session['industry'] or user.get('industry') or 'Not set'}\n\n"
            f"Direct Cost\nR{quote_data['direct_cost']:,.0f}\n\n"
            f"Protected Cost\nR{quote_data['protected_cost']:,.0f}\n\n"
            f"Recommended Quote\nR{quote_data['recommended_quote']:,.0f}\n\n"
            f"Margin Protected\n{quote_data['margin']*100:.1f}%\n\n"
            "South African Construction Benchmark\n\n"
            "Typical contractor net margin\n≈ 3% – 5%\n\n"
            "With ARLO guardrails\n≈ 8% – 12%\n\n"
            "Commands\n\n"
            "reduce by 10%\n"
            "generate quote\n"
            "history\n"
            "industry"
        )

    # -----------------------------
    # DISCOUNT SIMULATION
    # -----------------------------
    discount_match = re.search(r"(reduce|discount|lower).*?(\d+(?:\.\d+)?)", txt, re.I)
    if discount_match:
        recent = get_recent_quotes(phone, limit=1)
        if not recent:
            return twiml("No recent quote found. Run a new pricing analysis first.")

        last = recent[0]
        discount_pct = float(discount_match.group(2)) / 100
        new_price = last["price"] * (1 - discount_pct)
        new_margin = ((new_price - last["protected_cost"]) / new_price) * 100 if new_price > 0 else 0
        lost = last["price"] - new_price

        return twiml(
            "⚠️ Profit Leak Detected\n\n"
            f"Previous Quote:     R{last['price']:,.0f}\n"
            f"Discount Applied:   {int(discount_pct*100)}%\n\n"
            f"New Quote:          R{new_price:,.0f}\n"
            f"Protected Cost:     R{last['protected_cost']:,.0f}\n\n"
            f"New Margin:         {new_margin:.1f}%\n"
            f"Profit Lost:        R{lost:,.0f}\n\n"
            f"Tip: Stay near R{last['price']:,.0f} to protect profit."
        )

    # -----------------------------
    # CLIENT QUOTE
    # -----------------------------
    if "generate quote" in txt or "client quote" in txt:
        recent = get_recent_quotes(phone, limit=1)
        if not recent:
            return twiml("No recent quote found. Run a new pricing analysis first.")

        last = recent[0]

        return twiml(
            "📄 CLIENT QUOTATION\n\n"
            f"Reference: {last['ref']}\n"
            f"Project: {(session['industry'] or user.get('industry') or 'General')} Works\n"
            f"Date: {last['timestamp'][:10]}\n\n"
            f"Total Project Price\nR{last['price']:,.2f}\n\n"
            "Includes labour, materials, equipment & transport.\n"
            "Valid 14 days.\n\n"
            "Prepared by ARLO – The Profit Prophet\n"
            "065 999 4443"
        )

    # -----------------------------
    # HISTORY
    # -----------------------------
    if txt in ["history", "my quotes", "last quotes"]:
        quotes = get_recent_quotes(phone, limit=3)
        if not quotes:
            return twiml("No quotes yet. Send job costs first.")

        lines = ["Your recent quotes:"]
        for q in quotes:
            lines.append(f"{q['timestamp'][:10]} | {q['ref']} | R{q['price']:,.2f}")

        return twiml("\n".join(lines))

    # -----------------------------
    # DEFAULT
    # -----------------------------
    return twiml(
        "ARLO AI Pricing Assistant\n\n"
        "Type 'industry' to begin."
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)