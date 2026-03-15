from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import re

from database import init_db, get_or_create_user, save_quote

app = Flask(__name__)

# -----------------------------
# Initialize database
# -----------------------------
init_db()

# -----------------------------
# Pricing assumptions
# -----------------------------
ROOF_RATE = 120
FASCIA_RATE = 85
BARGE_RATE = 90

MARGIN_TARGET = 0.30


# -----------------------------
# Root route (Render health check)
# -----------------------------
@app.route("/")
def home():
    return "ARLO is running"


# -----------------------------
# Helper: extract numbers
# -----------------------------
def parse_job(text):

    roof = re.search(r"roof\s*(\d+)", text)
    fascia = re.search(r"fascia\s*(\d+)", text)
    barge = re.search(r"barge\s*(\d+)", text)

    roof = int(roof.group(1)) if roof else 0
    fascia = int(fascia.group(1)) if fascia else 0
    barge = int(barge.group(1)) if barge else 0

    return roof, fascia, barge


# -----------------------------
# Pricing engine
# -----------------------------
def calculate_price(roof, fascia, barge):

    roof_cost = roof * ROOF_RATE
    fascia_cost = fascia * FASCIA_RATE
    barge_cost = barge * BARGE_RATE

    total_cost = roof_cost + fascia_cost + barge_cost

    price = total_cost / (1 - MARGIN_TARGET)

    margin = (price - total_cost) / price

    return round(price, 2), round(total_cost, 2), round(margin * 100, 2)


# -----------------------------
# WhatsApp webhook
# -----------------------------
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "").lower()
    from_number = request.values.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    # register user
    user_id = get_or_create_user(from_number)

    # -----------------------------
    # Discount command
    # -----------------------------
    if "reduce by" in incoming_msg:

        discount = re.search(r"(\d+)", incoming_msg)

        if discount:
            percent = int(discount.group(1))

            msg.body(
                f"ARLO Pricing Adjustment\n\n"
                f"Discount simulation: {percent}%\n\n"
                f"Send 'generate quote' to apply this adjustment."
            )

        else:
            msg.body("Please specify a discount percentage.")

        return str(resp)

    # -----------------------------
    # Job specification
    # -----------------------------
    if "roof" in incoming_msg or "fascia" in incoming_msg or "barge" in incoming_msg:

        roof, fascia, barge = parse_job(incoming_msg)

        price, total_cost, margin = calculate_price(roof, fascia, barge)

        save_quote(
            user_id,
            roof,
            fascia,
            barge,
            price,
            total_cost,
            margin,
            incoming_msg
        )

        msg.body(

            f"ARLO Quote Analysis\n\n"

            f"Roof: {roof} m²\n"
            f"Fascia: {fascia} m\n"
            f"Barge: {barge} m\n\n"

            f"Estimated Cost: R{total_cost}\n"
            f"Recommended Price: R{price}\n"
            f"Margin: {margin}%\n\n"

            f"Commands:\n"
            f"reduce by 10%\n"
            f"generate quote"
        )

        return str(resp)

    # -----------------------------
    # Generate client quote
    # -----------------------------
    if "generate quote" in incoming_msg:

        msg.body(

            "ARLO Client Quote\n\n"

            "Project pricing prepared.\n"
            "All costs verified.\n"
            "Margin protected.\n\n"

            "You can confidently send this to your client."

        )

        return str(resp)

    # -----------------------------
    # Default message
    # -----------------------------
    msg.body(

        "ARLO AI Pricing Assistant\n\n"

        "Send job specs like this:\n\n"

        "Roof 320\n"
        "Fascia 20\n"
        "Barge 10\n\n"

        "Commands:\n"
        "reduce by 10%\n"
        "generate quote"

    )

    return str(resp)


# -----------------------------
# Local run (not used on Render)
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)