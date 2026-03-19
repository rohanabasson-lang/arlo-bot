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
# UI POLISH
# ─────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 1rem;
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
<p style='text-align:center; color:#888;'>Protect your margin. Win the job. Never underprice again.</p>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# INPUTS
# ─────────────────────────────────────────────
st.subheader("Job Costs")

col1, col2 = st.columns(2)

labour = col1.number_input("Labour (R)", min_value=0.0, step=1.0)
materials = col1.number_input("Materials (R)", min_value=0.0, step=1.0)
equipment = col2.number_input("Equipment / Hire (R)", min_value=0.0, step=1.0)
other = col2.number_input("Transport / Other (R)", min_value=0.0, step=1.0)

project_name = st.text_input("Project Name (optional)", "")

st.markdown("---")

overhead_pct = st.slider("Overhead %", 10, 30, 18)
margin_pct = st.slider("Target Margin %", 20, 45, 30)

# ─────────────────────────────────────────────
# CALC
# ─────────────────────────────────────────────
if st.button("💰 Generate Client-Ready Quote", use_container_width=True):

    try:
        if margin_pct >= 100:
            st.error("Target margin must be below 100%")
            st.stop()

        if margin_pct < 10:
            st.warning("Margin below 10% is very aggressive")

        if all(v == 0 for v in [labour, materials, equipment, other]):
            st.warning("Enter at least one cost value")
            st.stop()

        # CORE CALC
        direct_cost = labour + materials + equipment + other
        overhead = direct_cost * (overhead_pct / 100)
        total_cost = direct_cost + overhead

        price = total_cost / (1 - margin_pct / 100)
        profit = price - total_cost
        margin_actual = (profit / price) * 100
        walkaway = total_cost / (1 - 0.20)

        # 🔥 SUGGESTED PRICE (SMART POSITIONING)
        suggested_price = (price + walkaway) / 2

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        ref = f"ARLO-{secrets.token_hex(3).upper()}"

        # SAVE
        save_quote({
            "timestamp": timestamp,
            "project_name": project_name,
            "labour": labour,
            "materials": materials,
            "equipment": equipment,
            "other": other,
            "overhead_pct": overhead_pct,
            "margin_target": margin_pct,
            "total_cost": total_cost,
            "price": price,
            "profit": profit,
            "margin": margin_actual,
            "walkaway": walkaway
        })

        # ───────── RESULTS ─────────
        st.markdown("## 📊 Results")

        st.markdown(f"""
        <div class="result-card">
        <b>Cost:</b> R{total_cost:,.0f}<br><br>
        <b>Target Price:</b> R{price:,.0f}<br><br>
        <b style='color:#4ade80;'>💡 Suggested Price:</b> R{suggested_price:,.0f}<br><br>
        <b>Profit:</b> R{profit:,.0f}<br><br>
        <b>Margin:</b> {margin_actual:.1f}%<br><br>
        <b style='color:#ff4b4b;'>🚫 Walk-Away:</b> R{walkaway:,.0f}
        </div>
        """, unsafe_allow_html=True)

        st.error(f"🚫 NEVER go below: R{walkaway:,.0f}")

        if margin_actual < 25:
            st.error("⚠️ High risk — margin too low")
        elif margin_actual < 30:
            st.warning("Margin acceptable, but could improve")
        else:
            st.success("Strong margin")

        st.info(
            f"Typical contractors net ~3–5%. "
            f"You are positioned at ~{margin_actual*0.4:.1f}%–{margin_actual*0.6:.1f}% net."
        )

        # ───────── DISCOUNT SIM ─────────
        st.markdown("### 🔻 Discount Simulation")

        discount_pct = st.slider("Simulate discount (%)", 0, 25, 0)

        if discount_pct > 0:
            new_price = price * (1 - discount_pct / 100)
            new_profit = new_price - total_cost
            new_margin = (new_profit / new_price) * 100

            st.warning(f"""
After {discount_pct}% discount:
- New Price:     R{new_price:,.0f}
- New Profit:    R{new_profit:,.0f}
- New Margin:    {new_margin:.1f}%

⚠️ This is how profit leaks during negotiation.
""")

        # ───────── PDF ─────────
        pdf = FPDF()
        pdf.add_page()

        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, "ARLO PROJECT QUOTATION", ln=1, align="C")

        pdf.set_font("Arial", size=12)
        pdf.cell(200, 8, f"Date: {timestamp}", ln=1)
        pdf.cell(200, 8, f"Reference: {ref}", ln=1)
        pdf.cell(200, 8, f"Project: {project_name or 'General Works'}", ln=1)

        pdf.ln(10)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 8, f"Total Price: R{price:,.0f}", ln=1)

        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 8, f"""
Cost Breakdown:

Labour: R{labour:,.0f}
Materials: R{materials:,.0f}
Equipment: R{equipment:,.0f}
Other: R{other:,.0f}
Overhead ({overhead_pct}%): R{overhead:,.0f}

Valid for 14 days.

Prepared by ARLO – The Profit Prophet
""")

        pdf_output = pdf.output(dest="S")
        pdf_bytes = pdf_output.encode("latin-1") if isinstance(pdf_output, str) else pdf_output

        b64 = base64.b64encode(pdf_bytes).decode()

        filename = f"ARLO_Quote_{ref}.pdf"

        st.markdown(
            f'<a href="data:application/pdf;base64,{b64}" download="{filename}">📄 Download PDF Quote</a>',
            unsafe_allow_html=True
        )

    except Exception as e:
        st.error(f"Calculation error: {str(e)}")

# ───────── HISTORY ─────────
st.markdown("---")
st.subheader("📊 Recent Quotes")

rows = get_recent_quotes()

if not rows:
    st.info("No quotes yet.")
else:
    for r in rows:
        with st.expander(f"{r['timestamp'][:16]} | R{r['price']:,.0f} | {r['margin']:.1f}%"):
            st.caption(f"{r.get('project_name') or 'General Works'}")

# ───────── FOOTER ─────────
st.markdown("---")
st.caption("📱 Add to Home Screen → Use like an app")
st.caption("v1.2 – Early Access")