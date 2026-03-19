import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import base64
import secrets

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="ARLO Pricing Engine", layout="centered")

# -----------------------------
# DATABASE
# -----------------------------
conn = sqlite3.connect("arlo.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    project TEXT,
    total_cost REAL,
    price REAL,
    profit REAL,
    margin REAL
)
""")
conn.commit()

# -----------------------------
# SESSION STATE (SAFE NAMES)
# -----------------------------
if "boq_items" not in st.session_state:
    st.session_state.boq_items = []

if "results" not in st.session_state:
    st.session_state.results = None

# -----------------------------
# HEADER
# -----------------------------
st.markdown("## 🏗️ ARLO Pricing Engine")
st.caption("BOQ-Based Pricing. Margin Protected.")

project_name = st.text_input("Project Name")

# -----------------------------
# BOQ SECTION
# -----------------------------
st.markdown("## 📦 Job Breakdown (BOQ)")

col1, col2 = st.columns(2)

if col1.button("➕ Add Line Item"):
    st.session_state.boq_items.append({
        "name": "",
        "type": "Mixed",
        "qty": 1.0,
        "rate": 0.0,
        "labour_pct": 50
    })

if col2.button("🗑️ Clear"):
    st.session_state.boq_items = []
    st.session_state.results = None

total_direct_cost = 0

for i, item in enumerate(st.session_state.boq_items):

    st.markdown(f"### 🔹 Item {i+1}")

    item["name"] = st.text_input(f"Item Name {i}", item["name"])
    item["type"] = st.selectbox(f"Type {i}", ["Labour", "Material", "Mixed"], index=2)
    item["qty"] = st.number_input(f"Qty {i}", value=item["qty"], step=1.0)
    item["rate"] = st.number_input(f"Rate (R) {i}", value=item["rate"], step=100.0)
    item["labour_pct"] = st.slider(f"Labour % {i}", 0, 100, item["labour_pct"])

    cost = item["qty"] * item["rate"]
    total_direct_cost += cost

    st.caption(f"💰 Cost: R{cost:,.0f}")

# -----------------------------
# TOTAL
# -----------------------------
st.markdown(f"## 💰 Total Direct Cost: R{total_direct_cost:,.0f}")

# -----------------------------
# PRICING INPUTS
# -----------------------------
overhead_pct = st.slider("Overhead %", 0, 100, 20)
margin_pct = st.slider("Target Margin %", 0, 100, 30)

# -----------------------------
# CALCULATE
# -----------------------------
if st.button("💰 Generate Quote"):

    if margin_pct >= 100:
        st.error("Margin must be below 100%")
        st.stop()

    if total_direct_cost == 0:
        st.warning("Add at least one item")
        st.stop()

    overhead = total_direct_cost * (overhead_pct / 100)
    total_cost = total_direct_cost + overhead

    price = total_cost / (1 - margin_pct / 100)
    profit = price - total_cost
    margin = (profit / price) * 100 if price > 0 else 0

    walk_away = total_cost * 1.25
    suggested = (price + walk_away) / 2

    st.session_state.results = {
        "total_cost": total_cost,
        "price": price,
        "profit": profit,
        "margin": margin,
        "walk_away": walk_away,
        "suggested": suggested
    }

    # SAVE TO DB
    c.execute("""
    INSERT INTO quotes (ts, project, total_cost, price, profit, margin)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        project_name,
        total_cost,
        price,
        profit,
        margin
    ))
    conn.commit()

# -----------------------------
# RESULTS
# -----------------------------
if st.session_state.results:

    r = st.session_state.results

    st.markdown("## 📊 Results")

    st.success(f"""
Total Cost: R{r['total_cost']:,.0f}

Target Price: R{r['price']:,.0f}

Suggested Price: R{r['suggested']:,.0f}

Profit: R{r['profit']:,.0f}

Margin: {r['margin']:.1f}%

🚫 Walk-Away Price: R{r['walk_away']:,.0f}
""")

    # -------------------------
    # DISCOUNT SIM
    # -------------------------
    st.markdown("## 🔻 Discount Simulation")

    discount_pct = st.slider("Discount %", 0, 25, 0)

    if discount_pct > 0:
        new_price = r["price"] * (1 - discount_pct / 100)
        new_profit = new_price - r["total_cost"]
        new_margin = (new_profit / new_price) * 100 if new_price > 0 else 0

        st.warning(f"""
After {discount_pct}% discount:

New Price: R{new_price:,.0f}
New Profit: R{new_profit:,.0f}
New Margin: {new_margin:.1f}%
""")

    # -------------------------
    # PDF EXPORT (FINAL SAFE)
    # -------------------------
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "ARLO PROJECT QUOTATION", ln=1, align="C")

    pdf.set_font("Arial", size=12)

    ref = f"ARLO-{secrets.token_hex(3).upper()}"

    pdf.cell(200, 8, f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=1)
    pdf.cell(200, 8, f"Reference: {ref}", ln=1)
    pdf.cell(200, 8, f"Project: {project_name or 'General Works'}", ln=1)

    pdf.ln(10)

    pdf.cell(200, 8, f"Total Price: R{r['price']:,.0f}", ln=1)

    pdf.ln(5)

    pdf_text = f"""
Total Cost: R{r['total_cost']:,.0f}
Suggested: R{r['suggested']:,.0f}
Walk-Away: R{r['walk_away']:,.0f}

Prepared by ARLO - The Profit Prophet
"""

    safe_text = pdf_text.encode("latin-1", "ignore").decode("latin-1")
    pdf.multi_cell(0, 8, safe_text)

    # 🔥 FINAL FIX (NO BYTEARRAY ERROR)
    pdf_raw = pdf.output(dest="S")

    if isinstance(pdf_raw, str):
        pdf_bytes = pdf_raw.encode("latin-1", "ignore")
    else:
        pdf_bytes = bytes(pdf_raw)

    b64 = base64.b64encode(pdf_bytes).decode()

    filename = f"ARLO_{ref}.pdf"

    href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}">📄 Download PDF Quote</a>'
    st.markdown(href, unsafe_allow_html=True)

# -----------------------------
# HISTORY
# -----------------------------
st.markdown("## 📊 Recent Quotes")

df = pd.read_sql_query("SELECT * FROM quotes ORDER BY id DESC LIMIT 5", conn)

if df.empty:
    st.info("No quotes yet.")
else:
    for _, row in df.iterrows():
        with st.expander(f"{row['ts']} | R{row['price']:,.0f}"):
            st.write(f"Project: {row['project']}")
            st.write(f"Profit: R{row['profit']:,.0f}")
            st.write(f"Margin: {row['margin']:.1f}%")

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
st.caption("📱 Add to Home Screen → Use like an app")
st.caption("ARLO by The Profit Prophet")