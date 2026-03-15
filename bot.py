from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import re
import uuid
from datetime import datetime, timedelta

from database import init_db, get_or_create_user, save_quote, get_recent_quotes

app = Flask(__name__)

init_db()

sessions = {}
SESSION_TIMEOUT = 86400

def clean_sessions():

```
now = datetime.now()

for num in list(sessions.keys()):
    if (now - sessions[num]["last_active"]).total_seconds() > SESSION_TIMEOUT:
        del sessions[num]
```

def make_quote_ref():

```
return "ARLO-" + uuid.uuid4().hex[:6].upper()
```

def parse_money_value(text):

```
match = re.search(r'(\d+(?:[.,]\d+)?)', text)

if not match:
    return None

try:
    return float(match.group(1).replace(",", ""))
except:
    return None
```

def classify_cost_line(line):

```
line = line.lower()

if any(k in line for k in ["labour", "labor", "manhour", "crew"]):
    return "labour"

if any(k in line for k in ["material", "mat", "supply", "mats"]):
    return "materials"

if any(k in line for k in ["equip", "machine", "plant", "hire"]):
    return "equipment"

if any(k in line for k in ["transport", "delivery", "logistic", "cartage"]):
    return "transport"

return None
```

@app.route("/")
def home():
return "ARLO is alive"

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

```
clean_sessions()

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
        "profit": None,
        "quote_ref": None,
        "last_active": datetime.now()
    }

session = sessions[from_number]
session["last_active"] = datetime.now()

if txt in ["hi", "hello", "start", "menu", "help"]:

    msg.body(
        "ARLO AI Pricing Assistant\n\n"
        "Commands:\n"
        "industry → choose trade\n"
        "reduce by 15%\n"
        "generate quote\n"
        "history → see recent quotes"
    )

elif txt == "industry":

    msg.body(
        "Select your industry:\n\n"
        "1 Construction\n"
        "2 Plumbing\n"
        "3 Electrical\n\n"
        "Reply with 1,2,3"
    )

elif txt in ["1", "2", "3"]:

    industries = {
        "1": "Construction",
        "2": "Plumbing",
        "3": "Electrical"
    }

    session["industry"] = industries[txt]

    msg.body(
        f"{industries[txt]} selected.\n\n"
        "Send job costs like:\n\n"
        "Labour 60000\n"
        "Materials 90000\n"
        "Equipment 12000\n"
        "Transport 3000"
    )

elif any(k in txt for k in ["labour", "material", "equip", "transport", "delivery"]):

    lines = txt.split("\n")

    labour = 0
    materials = 0
    equipment = 0
    transport = 0

    for line in lines:

        value = parse_money_value(line)

        if value is None:
            continue

        category = classify_cost_line(line)

        if category == "labour":
            labour = value

        elif category == "materials":
            materials = value

        elif category == "equipment":
            equipment = value

        elif category == "transport":
            transport = value

    total_cost = labour + materials + equipment + transport

    if total_cost == 0:

        msg.body(
            "Couldn't read numbers.\n\n"
            "Try:\n"
            "Labour 60000\n"
            "Materials 90000"
        )

        return str(resp)

    margin = 0.30

    recommended_price = total_cost / (1 - margin)

    profit = recommended_price - total_cost

    quote_ref = make_quote_ref()

    session["cost"] = total_cost
    session["price"] = recommended_price
    session["profit"] = profit
    session["quote_ref"] = quote_ref

    get_or_create_user(from_number)

    save_quote(
        from_number,
        quote_ref,
        total_cost,
        recommended_price,
        profit
    )

    msg.body(
        f"ARLO Quote Analysis\n\n"
        f"Industry: {session['industry'] or 'Not selected'}\n\n"
        f"Total Cost: R{total_cost:,.2f}\n"
        f"Recommended Price: R{recommended_price:,.2f}\n"
        f"Expected Profit: R{profit:,.2f}\n"
        f"Margin: 30%\n\n"
        f"Next:\n"
        f"reduce by 15%\n"
        f"generate quote"
    )

elif "reduce by" in txt or "discount" in txt:

    if session["price"] is None:

        msg.body("Run pricing analysis first.")

        return str(resp)

    match = re.search(r'(\d+(?:\.\d+)?)', txt)

    if not match:

        msg.body("Specify discount like: reduce by 10%")

        return str(resp)

    discount_pct = float(match.group(1)) / 100

    new_price = session["price"] * (1 - discount_pct)

    new_margin = ((new_price - session["cost"]) / new_price) * 100

    msg.body(
        f"Discount Simulation\n\n"
        f"Original Price: R{session['price']:,.2f}\n"
        f"Discount: {int(discount_pct*100)}%\n"
        f"New Price: R{new_price:,.2f}\n"
        f"New Margin: {new_margin:.1f}%\n\n"
        f"{'⚠️ Margin too low' if new_margin < 25 else 'Still profitable'}"
    )

elif "generate quote" in txt:

    if session["price"] is None:

        msg.body("Run pricing analysis first.")

        return str(resp)

    today = datetime.now().strftime("%Y-%m-%d")

    msg.body(
        f"CLIENT QUOTATION\n\n"
        f"Quote Ref: {session['quote_ref']}\n"
        f"Date: {today}\n\n"
        f"Project: {session['industry']} Works\n"
        f"Total Price: R{session['price']:,.2f}\n\n"
        f"Inclusions:\n"
        f"Labour\n"
        f"Materials\n"
        f"Equipment\n"
        f"Transport\n\n"
        f"Valid for 14 days.\n\n"
        f"Prepared by ARLO\n"
        f"The Profit Prophet"
    )

elif txt in ["history", "my quotes"]:

    quotes = get_recent_quotes(from_number)

    if not quotes:

        msg.body("No quotes yet.")

        return str(resp)

    lines = ["Your recent ARLO quotes:\n"]

    for ref, price, ts in quotes:

        date = ts[:10]

        lines.append(f"{date} | {ref} | R{price:,.2f}")

    msg.body("\n".join(lines))

else:

    msg.body(
        "ARLO AI Pricing Assistant\n\n"
        "Commands:\n"
        "industry\n"
        "reduce by 15%\n"
        "generate quote\n"
        "history"
    )

return str(resp)
```

if **name** == "**main**":
app.run(host="0.0.0.0", port=5000, debug=False)
