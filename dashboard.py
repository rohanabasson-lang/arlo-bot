import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
import base64

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="ARLO Pricing Engine",
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
st.markdown(
    """
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
    .arlo-card {
        background: #0b1220;
        border: 1px solid #1f2a44;
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
def save_quote(data: tuple) -> None:
    c.execute("""
    INSERT INTO quotes (
        user_phone, client_name, project,
        total_direct_cost, labour_portion, material_portion,
        overhead_pct, overhead_amount, total_cost,
        price, suggested, profit, margin, walk_away, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()

def get_user_quotes(phone: str) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT * FROM quotes WHERE user_phone=? ORDER BY id DESC",
        conn,
        params=(phone,)
    )

def get_all_quotes() -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT * FROM quotes ORDER BY id DESC",
        conn
    )

def make_pdf_bytes(
    user_name: str,
    project_name: str,
    total_direct_cost: float,
    labour_portion: float,
    material_portion: float,
    overhead_pct: float,
    overhead_amount: float,
    total_cost: float,
    price: float,
    suggested: float,
    profit: float,
    margin: float,
    walk_away: float,
    boq_items: list[dict],
) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "ARLO PROJECT QUOTATION", ln=True, align="C")

    pdf.ln(4)
    pdf.set_font("Arial", size=11)
    pdf.cell(190, 8, f"Client: {user_name}", ln=True)
    pdf.cell(190, 8, f"Project: {project_name}", ln=True)
    pdf.cell(190, 8, f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
    valid_until = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    pdf.cell(190, 8, f"Quote valid until: {valid_until}", ln=True)

    pdf.ln(8)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 8, "Project Price Summary", ln=True)

    pdf.set_font("Arial", size=11)
    summary_text = (
        f"Total Project Price (excl. VAT): R{price:,.0f}\n"
        f"VAT @ 15% will be added where applicable.\n"
        f"Final amount due: R{price * 1.15:,.0f} (incl. VAT)"
    )
    safe_summary = summary_text.encode("latin-1", errors="ignore").decode("latin-1")
    pdf.multi_cell(180, 7, safe_summary)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 8, "BOQ Breakdown", ln=True)

    pdf.set_font("Arial", size=10)

    for idx, item in enumerate(boq_items, start=1):
        name = item['name'] if item['name'] else f"Item {idx}"
        line = (
            f"{idx}. {name} - "   # plain ASCII hyphen → no Unicode crash
            f"Qty: {item['qty']:,.2f} | "
            f"Rate: R{item['rate']:,.0f} | "
            f"Subtotal: R{item['cost']:,.0f}"
        )
        pdf.multi_cell(170, 6, line)
        pdf.ln(1)

    pdf.ln(10)
    footer = (
        "Prepared by ARLO - The Profit Prophet\n\n"
        "Payment Terms: 50% deposit on acceptance, balance on practical completion.\n"
        "Inclusions: As per BOQ above.\n"
        "Exclusions: Variations, provisional sums, unforeseen site conditions.\n"
        "All prices exclude VAT unless stated otherwise."
    )
    safe_footer = footer.encode("latin-1", errors="ignore").decode("latin-1")
    pdf.multi_cell(180, 7, safe_footer)

    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str):
        pdf_bytes = pdf_output.encode('latin-1', errors='ignore')
    else:
        pdf_bytes = bytes(pdf_output)

    return pdf_bytes

# =========================================================
# SESSION STATE
# =========================================================
if "boq" not in st.session_state:
    st.session_state.boq = []

if "last_saved_key" not in st.session_state:
    st.session_state.last_saved_key = None

# =========================================================
# HEADER
# =========================================================
st.title("🏗️ ARLO Pricing Engine")
st.caption("BOQ-Based Pricing. Margin Protected.")

# =========================================================
# ACCESS
# =========================================================
user_phone = st.text_input("Enter your WhatsApp number", placeholder="e.g. 0659994443")

if not user_phone:
    st.info("Enter your number to access your workspace.")
    st.stop()

user_phone = user_phone.strip()

if user_phone not in AUTHORIZED_USERS:
    st.warning("Access restricted")
    st.stop()

user_name = AUTHORIZED_USERS[user_phone]
is_admin = user_phone in ADMIN_NUMBERS

st.success(f"Welcome {user_name}")
if is_admin:
    st.info("🧠 Admin Mode Enabled")

# =========================================================
# PROJECT
# =========================================================
project_name = st.text_input("Project Name", value="General Works")

# =========================================================
# BOQ INPUT
# =========================================================
st.subheader("📦 Job Breakdown (BOQ)")

top_a, top_b = st.columns([1, 1])
with top_a:
    if st.button("➕ Add Item", use_container_width=True):
        st.session_state.boq.append({
            "name": "",
            "qty": 1.0,
            "rate": 0.0,
            "labour_pct": 50
        })
        st.rerun()

with top_b:
    if st.button("🧹 New Quote", use_container_width=True):
        st.session_state.boq = []
        st.session_state.last_saved_key = None
        st.rerun()

total_direct_cost = 0.0
labour_portion = 0.0
material_portion = 0.0
boq_snapshot = []

for i, item in enumerate(st.session_state.boq):
    with st.expander(f"Item {i+1}", expanded=True):
        col1, col2, col3 = st.columns(3)

        item["name"] = col1.text_input("Item", value=item["name"], key=f"name_{i}")
        item["qty"] = col2.number_input("Qty", min_value=0.0, value=float(item["qty"]), step=1.0, key=f"qty_{i}")
        item["rate"] = col3.number_input("Rate", min_value=0.0, value=float(item["rate"]), step=100.0, key=f"rate_{i}")

        item["labour_pct"] = st.slider("Labour %", 0, 100, int(item["labour_pct"]), key=f"lab_{i}")

        cost = float(item["qty"]) * float(item["rate"])
        labour_cost = cost * (float(item["labour_pct"]) / 100)
        material_cost = cost - labour_cost

        total_direct_cost += cost
        labour_portion += labour_cost
        material_portion += material_cost

        boq_snapshot.append({
            "name": item["name"] if item["name"] else f"Item {i+1}",
            "qty": float(item["qty"]),
            "rate": float(item["rate"]),
            "cost": cost,
            "labour_cost": labour_cost,
            "material_cost": material_cost
        })

        m1, m2, m3 = st.columns(3)
        m1.metric("Cost", f"R{cost:,.0f}")
        m2.metric("Labour", f"R{labour_cost:,.0f}")
        m3.metric("Material", f"R{material_cost:,.0f}")

        if st.button("🗑 Delete", key=f"del_{i}"):
            st.session_state.boq.pop(i)
            st.rerun()

st.markdown("---")

# =========================================================
# PRICING CONTROLS
# =========================================================
st.subheader("⚙️ Pricing Controls")
ctrl1, ctrl2 = st.columns(2)
with ctrl1:
    overhead_pct = st.slider("Overhead %", 0, 100, 20)
with ctrl2:
    margin_pct = st.slider("Target Margin %", 1, 99, 30)

if total_direct_cost <= 0:
    st.warning("Enter at least one cost item to generate pricing.")
    st.stop()

# =========================================================
# CALCULATIONS
# =========================================================
try:
    overhead_amount = total_direct_cost * (overhead_pct / 100)
    total_cost = total_direct_cost + overhead_amount
    price = total_cost / (1 - margin_pct / 100)
    suggested = price * 0.95
    profit = price - total_cost
    margin = (profit / price) * 100 if price > 0 else 0
    walk_away = total_cost * 1.25
except Exception as e:
    st.error(f"Calculation error: {e}")
    st.stop()

# =========================================================
# RESULTS
# =========================================================
st.subheader("📊 Results")

r1, r2, r3 = st.columns(3)
r1.metric("Total Direct Cost", f"R{total_direct_cost:,.0f}")
r2.metric("Labour Portion", f"R{labour_portion:,.0f}")
r3.metric("Material Portion", f"R{material_portion:,.0f}")

r4, r5, r6 = st.columns(3)
r4.metric("Overhead", f"R{overhead_amount:,.0f}")
r5.metric("Total Cost", f"R{total_cost:,.0f}")
r6.metric("Profit", f"R{profit:,.0f}")

r7, r8, r9 = st.columns(3)
r7.metric("Target Price", f"R{price:,.0f}")
r8.metric("Suggested", f"R{suggested:,.0f}")
r9.metric("Walk-Away", f"R{walk_away:,.0f}")

st.metric("Margin", f"{margin:.1f}%")

if margin < 15:
    st.error("Margin is very low. This is high risk.")
elif margin < 25:
    st.warning("Margin is thin. Proceed carefully.")
else:
    st.success("Margin looks healthy.")

# =========================================================
# ACTIONS
# =========================================================
action1, action2 = st.columns(2)

quote_key = (
    user_phone,
    project_name,
    round(total_cost, 2),
    round(price, 2),
    round(margin, 2),
    len(boq_snapshot)
)

with action1:
    if st.button("💾 Save Quote", use_container_width=True):
        if st.session_state.last_saved_key == quote_key:
            st.info("This quote is already saved.")
        else:
            save_quote((
                user_phone,
                user_name,
                project_name,
                total_direct_cost,
                labour_portion,
                material_portion,
                float(overhead_pct),
                overhead_amount,
                total_cost,
                price,
                suggested,
                profit,
                margin,
                walk_away,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            st.session_state.last_saved_key = quote_key
            st.success("Quote saved")

with action2:
    pdf_bytes = make_pdf_bytes(
        user_name=user_name,
        project_name=project_name,
        total_direct_cost=total_direct_cost,
        labour_portion=labour_portion,
        material_portion=material_portion,
        overhead_pct=float(overhead_pct),
        overhead_amount=overhead_amount,
        total_cost=total_cost,
        price=price,
        suggested=suggested,
        profit=profit,
        margin=margin,
        walk_away=walk_away,
        boq_items=boq_snapshot
    )
    st.download_button(
        label="📄 Download PDF",
        data=pdf_bytes,
        file_name=f"arlo_quote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# =========================================================
# DISCOUNT SIMULATION
# =========================================================
st.subheader("🔻 Discount Simulation")
discount = st.slider("Discount %", 0, 25, 0)

if discount > 0:
    new_price = price * (1 - discount / 100)
    new_profit = new_price - total_cost
    new_margin = (new_profit / new_price) * 100 if new_price > 0 else 0

    st.warning(
        f"After {discount}% discount:\n\n"
        f"Price: R{new_price:,.0f}\n\n"
        f"Profit: R{new_profit:,.0f}\n\n"
        f"Margin: {new_margin:.1f}%"
    )

# =========================================================
# HISTORY
# =========================================================
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
            st.write(f"**Client:** {row['client_name']}")
            st.write(f"**Project:** {row['project']}")
            st.write(f"**Total Cost:** R{row['total_cost']:,.0f}")
            st.write(f"**Profit:** R{row['profit']:,.0f}")
            st.write(f"**Margin:** {row['margin']:.1f}%")
            st.write(f"**Walk-Away:** R{row['walk_away']:,.0f}")
            st.write(f"**Suggested:** R{row['suggested']:,.0f}")

# =========================================================
# FOOTER
# =========================================================
st.markdown("---")
st.caption("📱 Tip: Add to Home Screen → Use like an app")
st.caption("ARLO v1.0 MVP")