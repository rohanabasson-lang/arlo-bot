import streamlit as st
from datetime import datetime
from fpdf import FPDF
import base64
import secrets

from database import init_db, save_quote, get_recent_quotes

init_db()

st.set_page_config(page_title="ARLO Pricing Engine", layout="centered")

# HEADER
st.markdown("""
<h2 style='text-align:center;'>🏗️ ARLO Pricing Engine</h2>
<p style='text-align:center; color:#888;'>Stop underpricing. Protect your profit on every job.</p>
""", unsafe_allow_html=True)

# INPUTS
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

# CALCULATE
if st.button("💰 Generate Client-Ready Quote", use_container_width=True):

    try:
        if margin_pct >= 100:
            st.error("Margin must be below 100%")
            st.stop()

        if all(v == 0 for v in [labour, materials, equipment, other]):
            st.error("Enter at least one cost value")
            st.stop()

        direct_cost = labour + materials + equipment + other
        overhead = direct_cost * (overhead_pct / 100)
        total_cost = direct_cost + overhead

        price = total_cost / (1 - margin_pct / 100)
        profit = price - total_cost
        margin_actual = (profit / price) * 100 if price > 0 else 0
        walkaway = total_cost / (1 - 0.20)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

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

        # RESULTS
        st.markdown("## 📊 Results")

        c1, c2, c3 = st.columns(3)
        c1.metric("Cost", f"R{total_cost:,.0f}")
        c2.metric("Quote", f"R{price:,.0f}")
        c3.metric("Profit", f"R{profit:,.0f}")

        st.metric("📈 Margin", f"{margin_actual:.1f}%")
        st.metric("🚫 Walk-Away Price", f"R{walkaway:,.0f}")

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

        # PDF
        pdf = FPDF()
        pdf.add_page()

        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, "ARLO PROJECT QUOTATION", ln=1, align="C")

        pdf.set_font("Arial", size=12)
        ref = f"ARLO-{secrets.token_hex(3).upper()}"

        pdf.cell(200, 8, f"Date: {timestamp}", ln=1)
        pdf.cell(200, 8, f"Reference: {ref}", ln=1)
        pdf.cell(200, 8, f"Project: {project_name or 'General Works'}", ln=1)

        pdf.ln(10)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 8, f"Total Price: R{price:,.0f}", ln=1)

        pdf.ln(5)

        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 8, f"""
Cost Breakdown:

Labour: R{labour:,.0f}
Materials: R{materials:,.0f}
Equipment: R{equipment:,.0f}
Other: R{other:,.0f}

Includes labour, materials, equipment and overheads.

Valid for 14 days.

Prepared by ARLO - The Profit Prophet
Contact: 065 999 4443
""")

        # 🔥 FIXED PDF OUTPUT
        pdf_output = pdf.output(dest="S")

        if isinstance(pdf_output, str):
            pdf_bytes = pdf_output.encode("latin-1")
        else:
            pdf_bytes = pdf_output

        b64 = base64.b64encode(pdf_bytes).decode()

        filename = f"ARLO_Quote_{timestamp.replace(' ', '_')}.pdf"

        href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}">📄 Download PDF Quote</a>'
        st.markdown(href, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Something went wrong: {str(e)}")

# HISTORY
st.markdown("---")
st.subheader("📊 Recent Quotes")

rows = get_recent_quotes()

if not rows:
    st.info("No quotes yet. Calculate your first one.")
else:
    for r in rows:
        st.markdown(
            f"**{r['timestamp'][:16]} | R{r['price']:,.0f} | {r['margin']:.1f}% margin**"
        )
        st.caption(f"{r.get('project_name') or 'General Works'}")

# FOOTER
st.markdown("---")
st.caption("📱 Tip: Add to Home Screen for app-like experience")