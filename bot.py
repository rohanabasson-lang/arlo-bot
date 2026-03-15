from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import random
import string
import re
from datetime import datetime

from database import init_db, get_or_create_user, save_quote, get_recent_quotes

app = Flask(__name__)

# initialize DB
init_db()

# in-memory session store
sessions = {}


def make_quote_ref():
    return "ARLO-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))


def reply(msg, text):
    msg.body(text)
    return str(msg)


@app.route("/")
def home():
    return "ARLO is alive"


@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From")

    txt = incoming_msg.lower()

    resp = MessagingResponse()
    msg = resp.message()

    if from_number not in sessions:
        sessions[from_number] = {
            "industry": None,
            "cost": None,
            "price": None,
            "profit": None
        }

    session = sessions[from_number]

    # HELP
    if txt in ["hi", "hello", "menu", "help", "start"]:

        return reply(msg,
        "ARLO AI Pricing Assistant\n\n"
        "Commands:\n"
        "industry → choose trade\n"
        "reduce by 10% → test discount\n"
        "generate quote → client quote\n"
        "history → show recent quotes"
        )

    # INDUSTRY MENU
    elif txt == "industry":

        return reply(msg,
        "Select your industry:\n\n"
        "1 Construction\n"
        "2 Plumbing\n"
        "3 Electrical\n\n"
        "Reply with 1, 2 or 3"
        )

    # INDUSTRY CHOICE
    elif txt in ["1", "2", "3"]:

        industries = {
            "1": "Construction",
            "2": "Plumbing",
            "3": "Electrical"
        }

        session["industry"] = industries[txt]

        return reply(msg,
        f"{industries[txt]} selected.\n\n"
        "Send costs like:\n\n"
        "Labour 60000\n"
        "Materials 90000\n"
        "Equipment 12000\n"
        "Transport 3000"
        )

    # COST INPUT
    elif any(k in txt for k in ["labour", "material", "equip", "transport"]):

        labour = materials = equipment = transport = 0

        lines = incoming_msg.split("\n")

        for line in lines:

            value_match = re.search(r'(\d+(?:[.,]\d+)?)', line)

            if not value_match:
                continue

            value = float(value_match.group(1).replace(",", ""))

            l = line.lower()

            if "labour" in l or "labor" in l:
                labour = value

            elif "material" in l or "mat" in l:
                materials = value

            elif "equip" in l:
                equipment = value

            elif "transport" in l or "delivery" in l:
                transport = value

        total_cost = labour + materials + equipment + transport

        if total_cost == 0:
            return reply(msg, "Could not detect numbers. Try:\nLabour 60000\nMaterials 90000")

        margin = 0.30

        recommended_price = total_cost / (1 - margin)
        profit = recommended_price - total_cost

        session["cost"] = total_cost
        session["price"] = recommended_price
        session["profit"] = profit

        quote_ref = make_quote_ref()

        get_or_create_user(from_number)
        save_quote(from_number, quote_ref, total_cost, recommended_price, profit)

        return reply(msg,
        f"ARLO Quote Analysis\n\n"
        f"Industry: {session['industry']}\n\n"
        f"Total Cost: R{total_cost:,.2f}\n"
        f"Recommended Price: R{recommended_price:,.2f}\n"
        f"Profit: R{profit:,.2f}\n\n"
        "Next:\n"
        "reduce by 10%\n"
        "generate quote"
        )

    # DISCOUNT
    elif "reduce" in txt or "discount" in txt:

        if session["price"] is None:
            return reply(msg, "Run pricing analysis first.")

        match = re.search(r'(\d+)', txt)

        if not match:
            return reply(msg, "Specify discount like: reduce by 10%")

        discount = float(match.group(1)) / 100

        new_price = session["price"] * (1 - discount)

        new_margin = ((new_price - session["cost"]) / new_price) * 100

        return reply(msg,
        f"Discount Simulation\n\n"
        f"Original Price: R{session['price']:,.2f}\n"
        f"New Price: R{new_price:,.2f}\n"
        f"New Margin: {new_margin:.1f}%"
        )

    # GENERATE QUOTE
    elif "generate quote" in txt:

        if session["price"] is None:
            return reply(msg, "Run pricing analysis first.")

        ref = make_quote_ref()

        return reply(msg,
        f"CLIENT QUOTATION\n\n"
        f"Quote Ref: {ref}\n"
        f"Date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"Project: {session['industry']} Works\n"
        f"Total Price: R{session['price']:,.2f}\n\n"
        f"Prepared by ARLO"
        )

    # HISTORY
    elif txt in ["history", "my quotes"]:

        quotes = get_recent_quotes(from_number)

        if not quotes:
            return reply(msg, "No previous quotes.")

        lines = ["Recent ARLO quotes:\n"]

        for ref, price, ts in quotes:
            date = ts[:10]
            lines.append(f"{date} | {ref} | R{price:,.2f}")

        return reply(msg, "\n".join(lines))

    else:

        return reply(msg, "Type 'help' to see commands.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)