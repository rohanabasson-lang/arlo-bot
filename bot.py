from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# ----------------------------------
# Health check for Render
# ----------------------------------
@app.route("/")
def home():
    return "ARLO is alive"

# ----------------------------------
# WhatsApp webhook
# ----------------------------------
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "").strip().lower()

    resp = MessagingResponse()
    msg = resp.message()

    # COMMAND: INDUSTRY
    if incoming_msg == "industry":
        msg.body(
            "ARLO AI Pricing Assistant\n\n"
            "Select your industry:\n"
            "1️⃣ Construction\n"
            "2️⃣ Plumbing\n"
            "3️⃣ Electrical\n\n"
            "Reply with 1, 2 or 3."
        )

    elif incoming_msg == "1":
        msg.body(
            "Construction mode activated.\n\n"
            "Send your costs like this:\n"
            "Labour 60000\n"
            "Materials 90000\n"
            "Equipment 12000\n"
            "Transport 3000"
        )

    elif incoming_msg == "2":
        msg.body(
            "Plumbing mode activated.\n\n"
            "Send your job costs to generate pricing."
        )

    elif incoming_msg == "3":
        msg.body(
            "Electrical mode activated.\n\n"
            "Send your job costs to generate pricing."
        )

    # COST INPUT
    elif "labour" in incoming_msg:

        lines = incoming_msg.split("\n")

        labour = 0
        materials = 0
        equipment = 0
        transport = 0

        for line in lines:

            parts = line.split()

            if len(parts) != 2:
                continue

            key = parts[0]
            value = float(parts[1])

            if key == "labour":
                labour = value
            elif key == "materials":
                materials = value
            elif key == "equipment":
                equipment = value
            elif key == "transport":
                transport = value

        cost = labour + materials + equipment + transport
        margin = 0.30
        price = cost / (1 - margin)

        msg.body(
            f"ARLO Quote Analysis\n\n"
            f"Total Cost: R{cost:,.2f}\n"
            f"Recommended Price: R{price:,.2f}\n"
            f"Margin: 30%\n\n"
            f"Commands:\n"
            f"reduce by 10%\n"
            f"generate quote"
        )

    else:

        msg.body(
            "ARLO AI Pricing Assistant\n\n"
            "Commands:\n"
            "industry → select industry\n"
            "reduce by 10% → test discount\n"
            "generate quote → client quote"
        )

    return str(resp)


if __name__ == "__main__":
    app.run()