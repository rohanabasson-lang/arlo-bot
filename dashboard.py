import streamlit as st
from datetime import datetime
from fpdf import FPDF
import base64
import secrets

from database import init_db, save_quote, get_recent_quotes

init_db()

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="ARLO Pricing Engine", layout="centered")

# ─────────────────────────────────────────────
# SAFE SESSION STATE (CRITICAL)
# ─────────────────────────────────────────────
if "items" not in st.session_state or not isinstance(st.session_state.get("items"), list):
    st.session_state["items"] = []

# ─────────────────────────────────────────────
# UI STYLE
# ─────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}

.block-container {
    max-width: 480px;
    margin: auto;
    padding-top: 1.5rem;
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
<p style='text-align:center; color:#888;'>BOQ-Based Pricing. Margin Protected.</p>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PROJECT INPUT
# ─────────────────────────────────────────────
project_name = st.text_input("Project Name")

# ─────────────────────────────────────────────
# LINE ITEM ENGINE (LEVEL 3)
# ─────────────────────────────────────────────
st.markdown("## 📦 Job Breakdown (BOQ)")

colA, colB = st.columns(2)

if colA.button("➕ Add Line Item"):
    st.session_state["items"].append({
        "name": "",
        "type": "Mixed",
        "qty": 1.0,
        "rate": 0.0,
        "labour_pct": 50,
        "material_pct": 50,
        "subcontract": 0.0,
        "cost": 0.0
    })

if colB.button("🗑 Clear"):
    st.session_state["items"] = []

line_total = 0

for i, item in enumerate(st.session_state["items"]):

    st.markdown(f"### 🔹 Item {i+1}")

    c1, c2 = st.columns(2)
    name = c1.text_input(f"Item Name {i}", value=item.get("name", ""))
    item_type = c2.selectbox(
        f"Type {i}",
        ["Labour", "Material", "Mixed", "Subcontract"],
        index=["Labour", "Material", "Mixed", "Subcontract"].index(item.get("type", "Mixed"))
    )

    c3, c4 = st.columns(2)
    qty = c3.number_input(f"Qty {i}", value=item.get("qty", 1.0), min_value=0.0)
    rate = c4.number_input(f"Rate (R) {i}", value=item.get("rate", 0.0), min_value=0.0)

    base_cost = qty * rate

    labour_pct = 0
    material_pct = 0
    subcontract_cost = 0

    if item_type == "Mixed":
        c5, c6 = st.columns(2)
        labour_pct = c5.slider(f"Labour % {i}", 0, 100, int(item.get("labour_pct", 50)))
        material_pct = 100 - labour_pct

    elif item_type == "Subcontract":
        subcontract_cost = st.number_input(f"Subcontract Cost {i}", value=item.get("subcontract", 0.0))

    labour_cost = base_cost * (labour_pct / 100)
    material_cost = base_cost * (material_pct / 100)

    total_item_cost = labour_cost + material_cost + subcontract_cost

    st.caption(f"💰 Cost: R{total_item_cost:,.0f}")

    # ⚠️ LOSS / LOW RATE WARNING
    if rate < 50 and rate != 0:
        st.warning("⚠️ This rate looks very low")

    st.session_state["items"][i] = {
        "name": name,
        "type": item_type,
        "qty": qty,
        "rate": rate,
        "labour_pct": labour_pct,
        "material_pct": material_pct,
        "subcontract": subcontract_cost,
        "cost": total_item_cost
    }

    line_total += total_item_cost

st.markdown(f"### 💰 Total Direct Cost: R{line_total:,.0f}")

st.markdown("---")

# ─────────────────────────────────────────────
# PRICING CONTROLS
# ─────────────────────────────────────────────
overhead_pct = st.slider("Overhead %", 10, 30, 18)
margin_pct = st.slider("Target Margin %", 20, 45, 30)

# ─────────────────────────────────────────────
# CALC ENGINE
# ─────────────────────────────────────────────
if st.button("💰 Generate Quote", use_container_width=True):

    try:
        if line_total == 0:
            st.warning("Add at least one line item")
            st.stop()

        direct_cost = line_total
        overhead = direct_cost * (overhead_pct / 100)
        total_cost = direct_cost + overhead

        price = total_cost / (1 - margin_pct / 100)
        profit = price - total_cost
        margin_actual = (profit / price) * 100
        walkaway = total_cost / (1 - 0.20)
        suggested = (price + walkaway) / 2

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
        <b style='color:#4ade80;'>Suggested:</b> R{suggested:,.0f}<br><br>
        <b>Profit:</b> R{profit:,.0f}<br><br>
        <b>Margin:</b> {margin_actual:.1f}%<br><br>
        <b style='color:#ff4b4b;'>Walk-Away:</b> R{walkaway:,.0f}
        </div>
        """, unsafe_allow_html=True)

        # BOQ DISPLAY
        st.markdown("### 📋 BOQ Breakdown")

        for item in st.session_state["items"]:
            st.write(
                f"{item['name']} — R{item['cost']:,.0f} "
                f"({item['qty']} × {item['rate']})"
            )

        # DISCOUNT SIM
        st.markdown("### 🔻 Discount Simulation")

        discount = st.slider("Discount %", 0, 25, 0)

        if discount > 0:
            new_price = price * (1 - discount / 100)
            new_profit = new_price - total_cost
            new_margin = (new_profit / new_price) * 100

            st.warning(f"""
New Price: R{new_price:,.0f}
Profit: R{new_profit:,.0f}
Margin: {new_margin:.1f}%
""")

        # PDF
        pdf = FPDF()
        pdf.add_page()

        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, "ARLO QUOTATION", ln=1, align="C")

        pdf.set_font("Arial", size=12)
        pdf.cell(200, 8, f"Date: {timestamp}", ln=1)
        pdf.cell(200, 8, f"Ref: {ref}", ln=1)
        pdf.cell(200, 8, f"Project: {project_name}", ln=1)

        pdf.ln(10)

        for item in st.session_state["items"]:
            pdf.cell(200, 8, f"{item['name']} - R{item['cost']:,.0f}", ln=1)

        pdf.ln(5)
        pdf.cell(200, 8, f"Total Price: R{price:,.0f}", ln=1)

        pdf_output = pdf.output(dest="S")
        pdf_bytes = pdf_output.encode("latin-1") if isinstance(pdf_output, str) else pdf_output

        b64 = base64.b64encode(pdf_bytes).decode()

        st.markdown(
            f'<a href="data:application/pdf;base64,{b64}" download="ARLO_Quote_{ref}.pdf">📄 Download PDF</a>',
            unsafe_allow_html=True
        )

    except Exception as e:
        st.error(str(e))

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