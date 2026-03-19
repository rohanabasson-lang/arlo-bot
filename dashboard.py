import streamlit as st
from datetime import datetime
from fpdf import FPDF
import base64
import secrets

from database import init_db, save_quote, get_recent_quotes

init_db()

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="ARLO Pricing Engine", layout="centered")

# ─────────────────────────────────────────────
# SAFE SESSION STATE INIT (CRITICAL FIX)
# ─────────────────────────────────────────────
if "items" not in st.session_state or not isinstance(st.session_state.get("items"), list):
    st.session_state["items"] = []

# ─────────────────────────────────────────────
# UI STYLE
# ─────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.block-container {
    padding-top: 1.5rem;
    max-width: 480px;
    margin: auto;
}

div.stButton > button {
    border-radius: 10px;
    height: 50px;
    font-size: 16px;
    font-weight: bold;
}

.result-card {
    padding:15px;
    border-radius:12px;
    background:#111827;
    border:1px solid #333;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<h2 style='text-align:center;'>🏗️ ARLO Pricing Engine</h2>
<p style='text-align:center; color:#888;'>Protect your margin. Win the job.</p>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BASIC INPUTS
# ─────────────────────────────────────────────
st.subheader("Job Costs")

col1, col2 = st.columns(2)

labour = col1.number_input("Labour (R)", min_value=0.0, step=1.0)
materials = col1.number_input("Materials (R)", min_value=0.0, step=1.0)
equipment = col2.number_input("Equipment / Hire (R)", min_value=0.0, step=1.0)
other = col2.number_input("Transport / Other (R)", min_value=0.0, step=1.0)

project_name = st.text_input("Project Name (optional)", "")

# ─────────────────────────────────────────────
# LINE ITEM ENGINE (SAFE)
# ─────────────────────────────────────────────
st.markdown("## 📦 Detailed Job Breakdown (Optional)")

colA, colB = st.columns(2)

if colA.button("➕ Add Line Item"):
    st.session_state["items"].append({
        "name": "",
        "type": "Labour",
        "cost": 0.0
    })

if colB.button("🗑 Clear Items"):
    st.session_state["items"] = []

line_total = 0

for i, item in enumerate(st.session_state["items"]):

    st.markdown(f"### Item {i+1}")

    c1, c2 = st.columns(2)

    name = c1.text_input(f"Name {i}", value=item["name"])
    item_type = c2.selectbox(
        f"Type {i}",
        ["Labour", "Material", "Subcontract"],
        index=["Labour", "Material", "Subcontract"].index(item["type"])
    )

    cost = st.number_input(f"Cost {i}", value=item["cost"], min_value=0.0)

    st.session_state["items"][i] = {
        "name": name,
        "type": item_type,
        "cost": cost
    }

    line_total += cost

st.markdown(f"### 💰 Line Item Total: R{line_total:,.0f}")

st.markdown("---")

# ─────────────────────────────────────────────
# PRICING CONTROLS
# ─────────────────────────────────────────────
overhead_pct = st.slider("Overhead %", 10, 30, 18)
margin_pct = st.slider("Target Margin %", 20, 45, 30)

# ─────────────────────────────────────────────
# CALCULATE
# ─────────────────────────────────────────────
if st.button("💰 Generate Client-Ready Quote", use_container_width=True):

    try:
        if margin_pct >= 100:
            st.error("Margin must be below 100%")
            st.stop()

        if all(v == 0 for v in [labour, materials, equipment, other, line_total]):
            st.warning("Enter at least one cost value")
            st.stop()

        direct_cost = labour + materials + equipment + other + line_total
        overhead = direct_cost * (overhead_pct / 100)
        total_cost = direct_cost + overhead

        price = total_cost / (1 - margin_pct / 100)
        profit = price - total_cost
        margin_actual = (profit / price) * 100
        walkaway = total_cost / (1 - 0.20)
        suggested_price = (price + walkaway) / 2

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        ref = f"ARLO-{secrets.token_hex(3).upper()}"

        save_quote({
            "timestamp": timestamp,
            "project_name": project_name,
            "total_cost": total_cost,
            "price": price,
            "profit": profit,
            "margin": margin_actual,
            "walkaway": walkaway
        })

        # RESULTS
        st.markdown("## 📊 Results")

        st.markdown(f"""
        <div class="result-card">
        <b>Total Cost:</b> R{total_cost:,.0f}<br><br>
        <b>Target Price:</b> R{price:,.0f}<br><br>
        <b style='color:#4ade80;'>Suggested:</b> R{suggested_price:,.0f}<br><br>
        <b>Profit:</b> R{profit:,.0f}<br><br>
        <b>Margin:</b> {margin_actual:.1f}%<br><br>
        <b style='color:#ff4b4b;'>Walk-Away:</b> R{walkaway:,.0f}
        </div>
        """, unsafe_allow_html=True)

        # LINE ITEMS DISPLAY
        if line_total > 0:
            st.markdown("### 📋 Breakdown")
            for item in st.session_state["items"]:
                st.caption(f"{item['name']} — R{item['cost']:,.0f}")

        # DISCOUNT SIM
        st.markdown("### 🔻 Discount Simulation")

        discount_pct = st.slider("Discount %", 0, 25, 0)

        if discount_pct > 0:
            new_price = price * (1 - discount_pct / 100)
            new_profit = new_price - total_cost
            new_margin = (new_profit / new_price) * 100

            st.warning(f"""
After {discount_pct}% discount:
Price: R{new_price:,.0f}
Profit: R{new_profit:,.0f}
Margin: {new_margin:.1f}%
""")

        # PDF
        pdf = FPDF()
        pdf.add_page()

        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, "ARLO PROJECT QUOTATION", ln=1, align="C")

        pdf.set_font("Arial", size=12)
        pdf.cell(200, 8, f"Date: {timestamp}", ln=1)
        pdf.cell(200, 8, f"Reference: {ref}", ln=1)
        pdf.cell(200, 8, f"Project: {project_name or 'General Works'}", ln=1)

        pdf.ln(10)

        pdf.cell(200, 8, f"Total Price: R{price:,.0f}", ln=1)

        pdf.ln(5)

        pdf.multi_cell(0, 8, f"""
Total Cost: R{total_cost:,.0f}
Overhead: {overhead_pct}%
Margin: {margin_pct}%

Prepared by ARLO – The Profit Prophet
""")

        pdf_output = pdf.output(dest="S")
        pdf_bytes = pdf_output.encode("latin-1") if isinstance(pdf_output, str) else pdf_output

        b64 = base64.b64encode(pdf_bytes).decode()

        st.markdown(
            f'<a href="data:application/pdf;base64,{b64}" download="ARLO_Quote_{ref}.pdf">📄 Download PDF</a>',
            unsafe_allow_html=True
        )

    except Exception as e:
        st.error(f"Error: {str(e)}")

# ─────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 Recent Quotes")

rows = get_recent_quotes()

if not rows:
    st.info("No quotes yet.")
else:
    for r in rows:
        with st.expander(f"{r['timestamp'][:16]} | R{r['price']:,.0f}"):
            st.caption(r.get("project_name", ""))

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.caption("📱 Add to Home Screen → Use like an app")