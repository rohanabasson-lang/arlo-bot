import os
import re
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from database import init_db, get_or_create_user, save_quote, get_recent_quotes

app = Flask(__name__)

init_db()

# -----------------------------
# Industry presets
# -----------------------------

INDUSTRIES = {
    "1": "Construction",
    "2": "Electrical",
    "3": "Painting"
}

# -----------------------------
# Helper functions
# -----------------------------

def extract_costs(text):
    labour = re.search(r"labour\s*(\d+)", text)
    materials = re.search(r"materials\s*(\d+)", text)
    equipment = re.search(r"equipment\s*(\d+)", text)
    transport = re.search(r"transport\s*(\d+)", text)

    return {
        "labour": float(labour.group(1)) if labour else 0,
        "materials": float(materials.group(1)) if materials else 0,
        "equipment": float(equipment.group(1)) if equipment else 0,
        "transport": float(transport.group(1)) if transport else 0
    }

def calculate_quote(costs):

    direct_cost = sum(costs.values())

    overhead = direct_cost * 0.19
    protected_cost = direct_cost + overhead

    margin = 0.30

    recommended_quote = protected_cost / (1 - margin)

    return {
        "direct_cost": direct_cost,
        "protected_cost": protected_cost,
        "recommended_quote": recommended_quote,
        "margin": margin
    }

# -----------------------------
# Routes
# -----------------------------

@app.route("/")
def home():
    return "ARLO AI Pricing Assistant running."

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "").lower()
    phone = request.values.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    user = get_or_create_user(phone)

    state = user["state"]

    # -----------------------------
    # INDUSTRY COMMAND
    # -----------------------------

    if "industry" in incoming_msg:

        msg.body(
            "ARLO Industry Presets\n\n"
            "1 Construction\n"
            "2 Electrical\n"
            "3 Painting\n\n"
            "Reply with the number of your industry."
        )

        user["state"] = "awaiting_industry"
        return str(resp)

    # -----------------------------
    # INDUSTRY SELECTION
    # -----------------------------

    if state == "awaiting_industry":

        if incoming_msg.strip() in INDUSTRIES:

            industry = INDUSTRIES[incoming_msg.strip()]
            user["industry"] = industry
            user["state"] = "awaiting_costs"

            msg.body(
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

        else:

            msg.body("Please reply with 1, 2 or 3.")

        return str(resp)

    # -----------------------------
    # COST INPUT
    # -----------------------------

    if state == "awaiting_costs":

        costs = extract_costs(incoming_msg)

        if sum(costs.values()) == 0:

            msg.body("Please send costs like:\nLabour 45000\nMaterials 80000\nEquipment 12000\nTransport 5000")

            return str(resp)

        quote = calculate_quote(costs)

        user["last_quote"] = quote["recommended_quote"]
        user["last_cost"] = quote["protected_cost"]
        user["state"] = "quote_ready"

        save_quote(
            phone,
            quote["recommended_quote"],
            quote["protected_cost"],
            quote["margin"]
        )

        msg.body(
            "ARLO Pricing Analysis\n\n"
            f"Direct Cost\nR{quote['direct_cost']:,.0f}\n\n"
            f"Protected Cost\nR{quote['protected_cost']:,.0f}\n\n"
            f"Recommended Quote\nR{quote['recommended_quote']:,.0f}\n\n"
            f"Margin Protected\n{quote['margin']*100:.1f}%\n\n"
            "South African Construction Benchmark\n\n"
            "Typical contractor net margin\n≈ 3% – 5%\n\n"
            "With ARLO guardrails\n≈ 8% – 12%\n\n"
            "Commands\n\n"
            "reduce by 10%\n"
            "generate quote\n"
            "industry"
        )

        return str(resp)

    # -----------------------------
    # DISCOUNT SIMULATION
    # -----------------------------

    if "reduce by" in incoming_msg:

        match = re.search(r"reduce by (\d+)", incoming_msg)

        if match and user["last_quote"]:

            discount = float(match.group(1)) / 100

            new_price = user["last_quote"] * (1 - discount)

            margin = (new_price - user["last_cost"]) / new_price

            profit_lost = user["last_quote"] - new_price

            msg.body(
                "⚠ Profit Leak Detected\n\n"
                f"Previous Quote: R{user['last_quote']:,.0f}\n"
                f"Discount Applied: {discount*100:.0f}%\n\n"
                f"New Quote: R{new_price:,.0f}\n"
                f"Protected Cost: R{user['last_cost']:,.0f}\n\n"
                f"New Margin: {margin*100:.1f}%\n"
                f"Profit Lost: R{profit_lost:,.0f}\n\n"
                f"Tip: Stay near R{user['last_quote']:,.0f} to protect profit."
            )

        return str(resp)

    # -----------------------------
    # GENERATE CLIENT QUOTE
    # -----------------------------

    if "generate quote" in incoming_msg:

        if user["last_quote"]:

            msg.body(
                "Client Quote\n\n"
                f"Total Project Price\nR{user['last_quote']:,.0f}\n\n"
                "Prepared by ARLO AI Pricing Assistant\n"
                "Profit-Protected Pricing"
            )

        return str(resp)

    # -----------------------------
    # DEFAULT RESPONSE
    # -----------------------------

    msg.body(
        "ARLO AI Pricing Assistant\n\n"
        "Type 'industry' to start pricing."
    )

    return str(resp)


if __name__ == "__main__":
    app.run()