import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import base64

# -----------------------------
# CONFIG
# -----------------------------
DB_PATH = "arlo.db"

ADMIN_NUMBERS = ["0659994443", "0736826931"]

AUTHORIZED_USERS = {
    "0795659007": "Ahluma Construction and Trading",
    "0815555088": "Ben Lutumba Construction",
    "0626011810": "Imabacon Projects",
    "0829980714": "Orion Shades and Steel Worx",
    "0730434326": "TAAL Projects and Civil Contractors",
    "0693794420": "Tripoli Private Investigators Security Systems Pty Ltd",
    "0631172296": "Volts and Amps Engineering (Solar/Electrical)",
    "0828431430": "Marz Construction",
    "0792001200": "Comma Group Pty Ltd",
    "0678201965": "JMF Construction",
    "0768976484": "Kusasa Projects and Maintenance Pty Ltd",
    "0731196550": "Energon Holdings Pty Ltd",
    "0678866227": "Reliable Painters Pty Ltd",
    "0656611289": "Lenyakallo Projects",
    "0730970027": "Myc-services Construction Pty Ltd",
    "0678250880": "NBH Construction Pty Ltd",
    "0795970690": "Bra Joe Steelworks and Construction",
    "0719152903": "Jobfellas",
    "0799722549": "Wiseinn Landscapes",
    "0787247849": "M S Kathide",
    "0660548678": "Ngwenya Property Rehab",
    "0672567151": "Ipotau Projects",

    # ADMIN
    "0659994443": "The Profit Prophet (Admin)",
    "0736826931": "Rohan Basson (Admin)"
}

# -----------------------------
# DB SETUP
# -----------------------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_phone TEXT,
    client_name TEXT,
    project TEXT,
    total_cost REAL,
    price REAL,
    suggested REAL,
    profit REAL,
    margin REAL,
    walk_away REAL,
    timestamp TEXT
)
""")
conn.commit()

# -----------------------------
# FUNCTIONS
# -----------------------------
def save_quote(data):
    c.execute("""
    INSERT INTO quotes (
        user_phone, client_name, project,
        total_cost, price, suggested, profit,
        margin, walk_away, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()

def get_user_quotes(phone):
    return pd.read_sql_query(
        "SELECT * FROM quotes WHERE user_phone=? ORDER BY id DESC",
        conn,
        params=(phone,)
    )

def get_all_quotes():
    return pd.read_sql_query(
        "SELECT * FROM quotes ORDER BY id DESC",
        conn
    )

# -----------------------------
# UI
# -----------------------------
st.set_page_config(layout="wide")
st.title("🏗️ ARLO Pricing Engine")
st.caption("BOQ-Based Pricing. Margin Protected.")

# -----------------------------
# LOGIN
# -----------------------------
user_phone = st.text_input("Enter your WhatsApp number")

if user_phone not in AUTHORIZED_USERS:
    st.warning("Access restricted")
    st.stop()

user_name = AUTHORIZED_USERS[user_phone]
is_admin = user_phone in ADMIN_NUMBERS

st.success(f"Welcome {user_name}")

if is_admin:
    st.info("🧠 Admin Mode Enabled")

# -----------------------------
# PROJECT
# -----------------------------
project_name = st.text_input("Project Name", value="General Works")

# -----------------------------
# BOQ
# -----------------------------
if "boq" not in st.session_state:
    st.session_state.boq = []

st.subheader("📦 Job Breakdown (BOQ)")

if st.button("➕ Add Item"):
    st.session_state.boq.append({
        "name": "",
        "qty": 1.0,
        "rate": 0.0,
        "labour_pct": 50
    })

total_direct_cost = 0

for i, item in enumerate(st.session_state.boq):
    with st.expander(f"Item {i+1}", expanded=True):
        col1, col2, col3 = st.columns(3)

        item["name"] = col1.text_input("Item", item["name"], key=f"name_{i}")
        item["qty"] = col2.number_input("Qty", value=item["qty"], key=f"qty_{i}")
        item["rate"] = col3.number_input("Rate", value=item["rate"], key=f"rate_{i}")

        item["labour_pct"] = st.slider("Labour %", 0, 100, item["labour_pct"], key=f"lab_{i}")

        cost = item["qty"] * item["rate"]
        total_direct_cost += cost

        st.write(f"💰 Cost: R{cost:,.0f}")

        if st.button("🗑 Delete", key=f"del_{i}"):
            st.session_state.boq.pop(i)
            st.rerun()

st.write(f"💰 Total Direct Cost: R{total_direct_cost:,.0f}")

# -----------------------------
# PRICING INPUTS
# -----------------------------
overhead_pct = st.slider("Overhead %", 0, 100, 20)
margin_pct = st.slider("Target Margin %", 0, 100, 30)

# -----------------------------
# CALCULATION
# -----------------------------
try:
    if total_direct_cost == 0:
        st.warning("Enter at least one cost item")
        st.stop()

    if margin_pct >= 100:
        st.error("Margin must be below 100%")
        st.stop()

    overhead = total_direct_cost * (overhead_pct / 100)
    total_cost = total_direct_cost + overhead

    price = total_cost / (1 - margin_pct / 100)
    suggested = price * 0.95
    profit = price - total_cost
    margin = (profit / price) * 100
    walk_away = total_cost * 1.25

    st.subheader("📊 Results")

    st.metric("Total Cost", f"R{total_cost:,.0f}")
    st.metric("Target Price", f"R{price:,.0f}")
    st.metric("Suggested", f"R{suggested:,.0f}")
    st.metric("Profit", f"R{profit:,.0f}")
    st.metric("Margin", f"{margin:.1f}%")
    st.metric("Walk-Away", f"R{walk_away:,.0f}")

except Exception as e:
    st.error(f"Calculation error: {e}")
    st.stop()

# -----------------------------
# SAVE
# -----------------------------
if st.button("💾 Save Quote"):
    save_quote((
        user_phone,
        user_name,
        project_name,
        total_cost,
        price,
        suggested,
        profit,
        margin,
        walk_away,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    st.success("Saved")

# -----------------------------
# PDF
# -----------------------------
if st.button("📄 Download PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, "ARLO QUOTE", ln=True)

    pdf.cell(200, 8, f"Client: {user_name}", ln=True)
    pdf.cell(200, 8, f"Project: {project_name}", ln=True)
    pdf.cell(200, 8, f"Date: {datetime.now()}", ln=True)

    pdf.ln(5)

    pdf.multi_cell(0, 8, f"""
Total Cost: R{total_cost:,.0f}
Price: R{price:,.0f}
Suggested: R{suggested:,.0f}
Profit: R{profit:,.0f}
Margin: {margin:.1f}%
Walk Away: R{walk_away:,.0f}

Prepared by ARLO
""")

    pdf_bytes = pdf.output(dest='S').encode('latin-1', errors='ignore')
    b64 = base64.b64encode(pdf_bytes).decode()

    href = f'<a href="data:application/pdf;base64,{b64}" download="arlo_quote.pdf">Download PDF</a>'
    st.markdown(href, unsafe_allow_html=True)

# -----------------------------
# DISCOUNT SIM
# -----------------------------
st.subheader("🔻 Discount Simulation")

discount = st.slider("Discount %", 0, 25, 0)

if discount > 0:
    new_price = price * (1 - discount / 100)
    new_profit = new_price - total_cost
    new_margin = (new_profit / new_price) * 100

    st.warning(f"""
After {discount}% discount:
Price: R{new_price:,.0f}
Profit: R{new_profit:,.0f}
Margin: {new_margin:.1f}%
""")

# -----------------------------
# HISTORY
# -----------------------------
st.subheader("📊 Quote History")

if is_admin:
    df = get_all_quotes()
else:
    df = get_user_quotes(user_phone)

if df.empty:
    st.info("No quotes yet")
else:
    for _, row in df.iterrows():
        with st.expander(f"{row['timestamp']} | R{row['price']:,.0f}"):
            st.write(f"Project: {row['project']}")
            st.write(f"Margin: {row['margin']:.1f}%")
            st.write(f"Walk-Away: R{row['walk_away']:,.0f}")