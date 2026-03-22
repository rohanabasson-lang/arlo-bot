import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="ARLO Pricing Assistant",
    page_icon="🏗️",
    layout="wide"
)

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
    "0659994443": "The Profit Prophet (Admin)",
    "0736826931": "Rohan Basson (Admin)",
    "0699307681": "Apex Electro Dynamics",
    "0686807333": "Boneh Projects",
    "0722396885": "Power Water Solutions",
    "0620136344": "Loyal Construction",
    "0660417821": "Handyman Andries",
    "0718357947": "Champion Renovations"
}

# =========================================================
# STYLING
# =========================================================
st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1100px;
}
.stMetric {
    background: #0f172a;
    border: 1px solid #1e293b;
    padding: 14px;
    border-radius: 14px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DB SETUP
# =========================================================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL;")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_phone TEXT,
    client_name TEXT,
    project TEXT,
    total_direct_cost REAL,
    labour_portion REAL,
    material_portion REAL,
    overhead_pct REAL,
    overhead_amount REAL,
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

# =========================================================
# HELPERS
# =========================================================
def save_quote(data):
    c.execute("""
    INSERT INTO quotes (
        user_phone, client_name, project,
        total_direct_cost, labour_portion, material_portion,
        overhead_pct, overhead_amount, total_cost,
        price, suggested, profit, margin, walk_away, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

# =========================================================
# SESSION STATE
# =========================================================
if "items" not in st.session_state:
    st.session_state.items = []

if "last_saved_key" not in st.session_state:
    st.session_state.last_saved_key = None

# =========================================================
# HEADER
# =========================================================
st.title("🏗️ ARLO PRICING ASSISTANT")
st.caption("Clear. Profitable. Multi-industry quoting.")

# =========================================================
# AUTHENTICATION (UPDATED 🔥)
# =========================================================
user_phone = st.text_input(
    "WhatsApp number",
    placeholder="Enter your registered WhatsApp number (e.g. 0712345678)"
)

if not user_phone:
    st.info("Enter your number to continue.")
    st.stop()

user_phone = user_phone.strip()

# 🔥 Validation (clean UX)
if not user_phone.isdigit():
    st.error("Phone number must contain digits only.")
    st.stop()

if user_phone not in AUTHORIZED_USERS:
    st.error("Number not authorized.")
    st.stop()

user_name = AUTHORIZED_USERS[user_phone]
is_admin = user_phone in ADMIN_NUMBERS

# 🔥 Clean greeting
st.success(f"Welcome back, {user_name}")

if is_admin:
    st.info("Admin mode active")

# =========================================================
# PROJECT INPUT
# =========================================================
project_name = st.text_input("Project / Service Name", value="General Scope")

# =========================================================
# LINE ITEMS
# =========================================================
st.subheader("📋 Project Items")

if st.button("➕ Add Line"):
    st.session_state.items.append({
        "name": "",
        "qty": 1.0,
        "rate": 0.0,
        "labour_pct": 50
    })

total_direct_cost = 0.0

for i, line in enumerate(st.session_state.items):
    line["name"] = st.text_input(f"Item {i+1} Name", value=line["name"], key=f"name_{i}")
    line["qty"] = st.number_input(f"Qty {i+1}", value=line["qty"], key=f"qty_{i}")
    line["rate"] = st.number_input(f"Rate {i+1}", value=line["rate"], key=f"rate_{i}")

    cost = line["qty"] * line["rate"]
    total_direct_cost += cost

    st.write(f"Subtotal: R{cost:,.0f}")

# =========================================================
# PRICING
# =========================================================
overhead_pct = st.number_input("Overhead %", value=20.0)
margin_pct = st.number_input("Margin %", value=30.0)

if total_direct_cost > 0:
    overhead = total_direct_cost * (overhead_pct / 100)
    total_cost = total_direct_cost + overhead
    price = total_cost / (1 - margin_pct / 100)

    st.subheader("📊 Results")
    st.metric("Total Cost", f"R{total_cost:,.0f}")
    st.metric("Price", f"R{price:,.0f}")

# =========================================================
# HISTORY
# =========================================================
st.subheader("📜 History")

df = get_all_quotes() if is_admin else get_user_quotes(user_phone)

if not df.empty:
    st.dataframe(df)
else:
    st.info("No quotes yet")

st.markdown("---")
st.caption("ARLO • The Profit Prophet")