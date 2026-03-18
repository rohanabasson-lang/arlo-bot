import streamlit as st
from datetime import datetime
from fpdf import FPDF
import base64
import secrets

from database import init_db, save_quote, get_recent_quotes

init_db()

st.set_page_config(page_title="ARLO Pricing Engine", layout="centered")

# ── GLOBAL STYLE (PWC CLEAN LOOK) ─────────────────────────
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
h2 {
    text-align: center;
}
.metric-label {
    font-size: 14px;
    color: #888;
}
</style>
""", unsafe_allow_html=True)

# ── HEADER ───────────────────────────────────────────────
st.markdown("""
<h2>ARLO Pricing Engine</h2>
<p style='text-align:center; color:#666;'>AI-assisted pricing for margin protection</p>
""", unsafe_allow_html=True)

st.markdown("---")

# ── INPUTS (STACKED FOR MOBILE) ─────────────────────────
st.subheader("Job Cost Inputs")

labour     = st.number_input("Labour (R)", min_value=0.0, step=1.0)
materials  = st.number_input("Materials (R)", min_value=0.0, step=1.0)
equipment  = st.number_input("Equipment / Hire (R)", min_value=0.0, step=1.0)
other      = st.number_input("Transport / Other (R)", min_value=0.0, step=1.0)

project_name = st.text_input("Project Name", "")

st.markdown("---")

overhead_pct = st.slider("Overhead (%)", 10, 30, 18)
margin_pct   = st.slider("Target Margin (%)", 20, 45, 30)

st.markdown("---")

# ── BUTTON ──────────────────────────────────────────────
calculate = st.button("Generate Pricing Output", use_container_width=True)

if calculate:

    try:
        if margin_pct >= 100:
            st.error("Margin must be below 100%")
            st.stop()

        if all(v == 0 for v in [labour, materials, equipment, other]):
            st.error("Enter at least one cost input")
            st.stop()

        # CALC
        direct_cost = labour + materials + equipment + other
        overhead    = direct_cost * (overhead_pct / 100)
        total_cost  = direct_cost + overhead

        price   = total_cost / (1 - margin_pct / 100)
        profit  = price - total_cost
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

        # ── RESULTS (EXEC STYLE) ───────────────────────
        st.markdown("## Pricing Output")

        st.metric("Recommended Quote", f"R{price:,.0f}")
        st.metric("Total Cost", f"R{total_cost:,.0f}")
        st.metric("Expected Profit", f"R{profit:,.0f}")

        st.metric("Margin (%)", f"{margin_actual:.1f}%")
        st.metric("Walk-Away Price", f"R{walkaway:,.0f}")

        st.markdown("---")

        # INSIGHT
        if margin_actual < 25:
            st.error("Margin below acceptable threshold")
        elif margin_actual < 30:
            st.warning("Margin acceptable, but can be improved")
        else:
            st.success("Strong margin position")

        st.info(
            f"Industry benchmark net margin ~3–5%. "
            f"This pricing aligns to ~{margin_actual*0.4:.1f}%–{margin_actual*0.6:.1f}% net."
        )

        # ── PDF (CLEAN EXEC VERSION) ───────────────────
        pdf = FPDF()
        pdf.add_page()

        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, "PROJECT QUOTATION", ln=1, align="C")

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

Valid for 14 days.
Prepared by ARLO Pricing Engine
""")

        pdf_bytes = pdf.output(dest="S").encode("latin-1", "ignore")
        b64 = base64.b64encode(pdf_bytes).decode()

        st.markdown(
            f'<a href="data:application/pdf;base64,{b64}" download="Quote.pdf">Download PDF</a>',
            unsafe_allow_html=True
        )

    except Exception as e:
        st.error(f"Error: {str(e)}")

# ── HISTORY ────────────────────────────────────────────
st.markdown("---")
st.subheader("Recent Pricing Activity")

rows = get_recent_quotes()

if not rows:
    st.caption("No pricing history available.")
else:
    for r in rows:
        st.markdown(
            f"**{r['timestamp'][:16]}** — R{r['price']:,.0f} ({r['margin']:.1f}%)"
        )
        st.caption(f"{r.get('project_name') or 'General'}")

# ── FOOTER ─────────────────────────────────────────────
st.markdown("---")
st.caption("Mobile Tip: Add to Home Screen for app-like experience")