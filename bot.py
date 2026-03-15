from flask import Flask, request, Response
import re

app = Flask(__name__)

print("ARLO BOT STARTING...")

# ------------------------------------------------
# In-memory quote storage per WhatsApp user
# ------------------------------------------------

last_quotes = {}

# ------------------------------------------------
# Reply helper
# ------------------------------------------------

def reply(text):
    return Response(
        f"<Response><Message>{text}</Message></Response>",
        mimetype="text/xml"
    )

# ------------------------------------------------
# Parse contractor cost input
# ------------------------------------------------

def parse_costs(text):

    data = {
        "labour": 0.0,
        "materials": 0.0,
        "equipment": 0.0,
        "transport": 0.0
    }

    lines = text.lower().split("\n")

    for line in lines:

        line = line.strip()

        if not line:
            continue

        parts = re.split(r'\s+', line)

        if len(parts) < 2:
            continue

        key = parts[0]

        try:
            value = float(parts[-1])
        except:
            continue

        if "labour" in key:
            data["labour"] = value

        elif "material" in key:
            data["materials"] = value

        elif "equip" in key:
            data["equipment"] = value

        elif "trans" in key or "logistic" in key or "ancillary" in key:
            data["transport"] = value

    return data


# ------------------------------------------------
# WhatsApp Webhook
# ------------------------------------------------

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    msg = request.values.get("Body", "").strip()
    txt = msg.lower()

    user = request.values.get("From", "unknown")

    print(f"Incoming from {user}: {msg}")


    # ------------------------------------------------
    # Industry Menu
    # ------------------------------------------------

    if "industry" in txt:

        return reply(
"""ARLO Industry Presets

1 Construction
2 Electrical
3 Painting

Reply with the number."""
        )


    if txt in ["1", "2", "3"]:

        names = {
            "1": "Construction",
            "2": "Electrical",
            "3": "Painting"
        }

        return reply(
f"""{names[txt]} pricing drivers

Labour
Materials
Equipment
Transport / ancillary

Example:

Labour 60000
Materials 90000
Equipment 12000
Transport 3000"""
        )


    # ------------------------------------------------
    # Discount / Profit Leak Simulation
    # ------------------------------------------------

    if any(word in txt for word in ["reduce", "discount", "lower", "cut"]):

        if user not in last_quotes:
            return reply("Run a quote first before testing discounts.")

        match = re.search(r"(\d+)", txt)

        if not match:
            return reply("Specify a % discount. Example: reduce by 10%")

        discount = float(match.group(1)) / 100

        prev = last_quotes[user]

        new_quote = prev["quote"] * (1 - discount)

        new_margin = ((new_quote - prev["cost"]) / new_quote) * 100 if new_quote > 0 else 0

        lost_profit = prev["quote"] - new_quote

        return reply(
f"""⚠️ Profit Leak Detected

Previous Quote:     R{prev['quote']:,.0f}
Discount Applied:   {int(discount*100)}%

New Quote:          R{new_quote:,.0f}
Protected Cost:     R{prev['cost']:,.0f}

New Margin:         {new_margin:.1f}%
Profit Lost:        R{lost_profit:,.0f}

Tip: Stay near R{prev['quote']:,.0f} to protect profit."""
        )


    # ------------------------------------------------
    # Client Quote Generator
    # ------------------------------------------------

    if "generate quote" in txt or "client quote" in txt or "send to client" in txt:

        if user not in last_quotes:
            return reply("Run a job quote first before generating a client version.")

        prev = last_quotes[user]

        return reply(
f"""📄 CLIENT QUOTATION

Project: {prev.get('project_name', 'General Works')}

Scope Included
• Labour
• Materials
• Equipment
• Transport & logistics

Total Price
R{prev['quote']:,.0f}

This quotation includes full project execution.

Validity: 14 days

Prepared by
ARLO – The Profit Prophet
Contact: 065 999 4443"""
        )


    # ------------------------------------------------
    # Normal Pricing Calculation
    # ------------------------------------------------

    scope = parse_costs(msg)

    total = sum(scope.values())

    if total == 0:

        return reply(
"""Couldn't detect costs.

Use format:

Labour 60000
Materials 90000
Equipment 12000
Transport 3000"""
        )


    # ------------------------------------------------
    # Pricing Model
    # ------------------------------------------------

    direct = total

    overhead = direct * 0.12

    risk = direct * 0.07

    protected = direct + overhead + risk

    quote = protected / 0.7      # 30% margin target

    profit = quote - protected

    margin = (profit / quote) * 100


    # ------------------------------------------------
    # Save for future commands
    # ------------------------------------------------

    last_quotes[user] = {
        "quote": quote,
        "cost": protected,
        "project_name": "Your Job"
    }


    benchmarks = """Labour rate within SA range (R300–R450/h)
Materials appear typical
Quote protects healthy margin"""


    response = f"""ARLO Pricing Analysis

Direct Cost          R{direct:,.0f}
Overhead (12%)       R{overhead:,.0f}
Risk Buffer (7%)     R{risk:,.0f}

Protected Cost       R{protected:,.0f}

Recommended Quote    R{quote:,.0f}

Expected Profit      R{profit:,.0f}
Margin Protected     {margin:.1f}%

South African Benchmark

Typical contractor margin ≈ 3–5%
With ARLO guardrails ≈ 8–12%

Cost Review
{benchmarks}

Commands

"reduce by 10%"  → test discount impact
"generate quote" → client version
"industry"       → change sector
"""

    return reply(response)


# ------------------------------------------------
# Run Server
# ------------------------------------------------

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000, debug=True)