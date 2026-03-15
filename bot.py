from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import re
import random
import string
from datetime import datetime

from database import init_db, get_or_create_user, save_quote, get_recent_quotes

app = Flask(__name__)

# Initialize database

init_db()

# In-memory sessions

sessions = {}

def make_quote_ref():
return "ARLO-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))

def parse_money_value(text):
match = re.search(r'(\d+(?:[.,]\d+)?)', text)
if not match:
return None
try:
return float(match.group(1).replace(",", ""))
except:
return None

def classify_cost_line(line, value):
line = line.lower()

```
if any(k in line for k in ["labour", "labor", "crew", "manhour"]):
    return "labour", value

if any(k in line for k in ["material", "mat", "supply"]):
    return "materials", value

if any(k in line for k in ["equip", "machine", "plant", "hire"]):
    return "equipment", value

if any(k in line for k in ["transport", "delivery", "logistic", "cartage"]):
    return "transport", value

return None, None
```

def reply_text(msg, text):
msg.body(text)
return str(msg)

@app.route("/")
def home():
return "ARLO is alive"

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

```
incoming_msg = request.values.get("Body", "").strip()
from_number = request.values.get("From")

txt = incoming_msg.lower()

resp = MessagingResponse()
msg = resp.message()

# Session
if from_number not in sessions:
    sessions[from_number] = {
        "industry": None,
        "cost": None,
        "price": None,
        "profit": None
    }

session = sessions[from_number]

# HELP / MENU
if txt in ["hi", "hello", "start", "menu", "help"]:

    return reply_text(msg,
    "ARLO AI Pricing Assistant\n\n"
    "Commands:\n"
    "industry → choose trade\n"
    "reduce by 10% → simulate discount\n"
    "generate quote → create client quote\n"
    "history → view recent quotes"
    )

# INDUSTRY MENU
elif txt == "industry":

    return reply_text(msg,
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

    return reply_text(msg,
    f"{industries[txt]} selected.\n\n"
    "Send job costs like:\n\n"
    "Labour 60000\n"
    "Materials 90000\n"
    "Equipment 12000\n"
    "Transport 3000"
    )

# COST INPUT
elif any(k in txt for k in ["labour", "material", "equip", "transport", "delivery"]):

    lines = incoming_msg.split("\n")

    labour = materials = equipment = transport = 0

    for line in lines:

        value = parse_money_value(line)

        if value is None:
            continue

        category, amount = classify_cost_line(line, value)

        if category == "labour":
            labour = amount

        elif category == "materials":
            materials = amount

        elif category == "equipment":
            equipment = amount

        elif category == "transport":
            transport = amount

    total_cost = labour + materials + equipment + transport

    if total_cost == 0:
        return reply_text(msg,
        "Could not detect numbers.\n\n"
        "Try format:\n"
        "Labour 60000\n"
        "Materials 90000"
        )

    margin = 0.30
    recommended_price = total_cost / (1 - margin)
    profit = recommended_price - total_cost

    session["cost"] = total_cost
    session["price"] = recommended_price
    session["profit"] = profit

    quote_ref = make_quote_ref()

    # Save to database
    get_or_create_user(from_number)
    save_quote(from_number, quote_ref, total_cost, recommended_price, profit)

    return reply_text(msg,
    f"ARLO Quote Analysis\n\n"
    f"Industry: {session['industry'] or 'Not selected'}\n\n"
    f"Total Cost:     R{total_cost:,.2f}\n"
    f"Recommended:    R{recommended_price:,.2f}\n"
    f"Expected Profit:R{profit:,.2f}\n"
    f"Margin:         30%\n\n"
    f"Next:\n"
    f"reduce by 15%\n"
    f"generate quote"
    )

# DISCOUNT SIMULATION
elif "reduce" in txt or "discount" in txt:

    if session["price"] is None:
        return reply_text(msg,
        "Run pricing analysis first."
        )

    match = re.search(r'(\d+(?:\.\d+)?)', txt)

    if not match:
        return reply_text(msg,
        "Specify discount % like: reduce by 10%"
        )

    discount_pct = float(match.group(1)) / 100

    new_price = session["price"] * (1 - discount_pct)

    new_margin = ((new_price - session["cost"]) / new_price) * 100

    return reply_text(msg,
    f"Discount Simulation\n\n"
    f"Original Price: R{session['price']:,.2f}\n"
    f"Discount:       {int(discount_pct*100)}%\n"
    f"New Price:      R{new_price:,.2f}\n"
    f"New Margin:     {new_margin:.1f}%"
    )

# CLIENT QUOTE
elif "generate quote" in txt:

    if session["price"] is None:
        return reply_text(msg,
        "Run pricing analysis first."
        )

    ref = make_quote_ref()

    return reply_text(msg,
    f"CLIENT QUOTATION\n\n"
    f"Quote Ref: {ref}\n"
    f"Date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
    f"Project: {session['industry']} Works\n"
    f"Total Price: R{session['price']:,.2f}\n\n"
    f"Inclusions:\n"
    f"Labour\nMaterials\nEquipment\nTransport\n\n"
    f"Prepared by ARLO"
    )

# HISTORY
elif txt in ["history", "my quotes"]:

    quotes = get_recent_quotes(from_number)

    if not quotes:
        return reply_text(msg,
        "No previous quotes found."
        )

    lines = ["Recent ARLO Quotes:\n"]

    for ref, price, ts in quotes:
        date = ts[:10]
        lines.append(f"{date} | {ref} | R{price:,.2f}")

    return reply_text(msg, "\n".join(lines))

# DEFAULT
else:

    return reply_text(msg,
    "ARLO AI Pricing Assistant\n\n"
    "Type 'help' to see commands."
    )
```

if **name** == "**main**":
app.run(host="0.0.0.0", port=5000, debug=False)
