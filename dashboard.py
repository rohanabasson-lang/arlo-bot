import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import base64
import secrets

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(page_title="ARLO Pricing Engine", layout="centered")

# ---------------------------------------------------
# AUTHORIZED TRIAL USERS
# ---------------------------------------------------
AUTHORIZED_USERS = {
    "0795659007": "Ahluma Construction and Trading",
    "0815555088": "Ben Lutumba Construction",
    "0626011810": "Imabacon Projects",
    "0829980714": "Orion Shades and Steel Worx",
    "0730434326": "TAAL Projects and Civil Contractors",
    "0693794420": "Tripoli Private Investigators Security Systems Pty.Ltd",
    "0631172296": "Volts and Amps Engineering(Solar/Electrical)",
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
}

# ---------------------------------------------------
# DATABASE
# ---------------------------------------------------
conn = sqlite3.connect("arlo.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    project TEXT,
    total_direct_cost REAL,
    total_labour REAL,
    total_material REAL,
    overhead REAL,
    total_cost REAL,
    price REAL,
    profit REAL,
    margin REAL,
    walk_away REAL,
    suggested REAL,
    user_id TEXT
)
""")
conn.commit()

# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------
if "boq_items" not in st.session_state:
    st.session_state.boq_items = []

if "results" not in st.session_state:
    st.session_state.results = None

# ---------------------------------------------------
# ACCESS CONTROL
# ---------------------------------------------------
st.markdown("## 🔐 ARLO Access")
phone = st.text_input("Enter your WhatsApp number to continue")

if not phone:
    st.stop()

phone = phone.strip()

if phone not in AUTHORIZED_USERS:
    st.error("Access not authorised. Please contact ARLO.")
    st.stop()

client_name = AUTHORIZED_USERS[phone]
st.success(f"Welcome, {client_name} 👋")
st.caption(f"Workspace: {client_name} | {phone}")

st.markdown("---")

# ---------------------------------------------------
# HEADER
# ---------------------------------------------------
st.markdown("## 🏗️ ARLO Pricing Engine")
st.caption("BOQ-Based Pricing. Margin Protected.")

project_name = st.text_input("Project Name")

# ---------------------------------------------------
# BOQ SECTION
# ---------------------------------------------------
st.markdown("## 📦 Job Breakdown (BOQ)")

top_col1, top_col2 = st.columns(2)

if top_col1.button("➕ Add Line Item"):
    st.session_state.boq_items.append({
        "name": "",
        "type": "Mixed",
        "qty": 1.0,
        "rate": 0.0,
        "labour_pct": 50
    })
    st.rerun()

if top_col2.button("🗑️ Clear All"):
    st.session_state.boq_items = []
    st.session_state.results = None
    st.rerun()

total_direct_cost = 0.0
total_labour = 0.0
total_material = 0.0
boq_lines = []

for i, item in enumerate(st.session_state.boq_items):
    st.markdown(f"### 🔹 Item {i+1}")

    item["name"] = st.text_input(f"Item Name {i}", value=item["name"])
    item["type"] = st.selectbox(
        f"Type {i}",
        ["Labour", "Material", "Mixed"],
        index=["Labour", "Material", "Mixed"].index(item["type"]) if item["type"] in ["Labour", "Material", "Mixed"] else 2,
        key=f"type_{i}"
    )
    item["qty"] = st.number_input(f"Qty {i}", min_value=0.0, value=float(item["qty"]), step=1.0)
    item["rate"] = st.number_input(f"Rate (R) {i}", min_value=0.0, value=float(item["rate"]), step=100.0)
    item["labour_pct"] = st.slider(f"Labour % {i}", 0, 100, int(item["labour_pct"]))

    cost = item["qty"] * item["rate"]

    if item["type"] == "Labour":
        labour_cost = cost
        material_cost = 0.0
    elif item["type"] == "Material":
        labour_cost = 0.0
        material_cost = cost
    else:
        labour_cost = cost * (item["labour_pct"] / 100)
        material_cost = cost - labour_cost

    total_direct_cost += cost
    total_labour += labour_cost
    total_material += material_cost

    boq_lines.append({
        "name": item["name"] or f"Item {i+1}",
        "qty": item["qty"],
        "rate": item["rate"],
        "cost": cost,
        "labour_cost": labour_cost,
        "material_cost": material_cost,
        "type": item["type"]
    })

    st.caption(f"💰 Cost: R{cost:,.0f} | Labour: R{labour_cost:,.0f} | Material: R{material_cost:,.0f}")

    if st.button("🗑 Delete Item", key=f"del_{i}"):
        del st.session_state.boq_items[i]
        st.session_state.results = None
        st.rerun()

# ---------------------------------------------------
# TOTALS
# ---------------------------------------------------
st.markdown(f"## 💰 Total Direct Cost: R{total_direct_cost:,.0f}")
sum_col1, sum_col2 = st.columns(2)
sum_col1.metric("Total Labour", f"R{total_labour:,.0f}")
sum_col2.metric("Total Material", f"R{total_material:,.0f}")

# ---------------------------------------------------
# PRICING INPUTS
# ---------------------------------------------------
overhead_pct = st.slider("Overhead %", 0, 100, 20)
margin_pct = st.slider("Target Margin %", 0, 100, 30)

action_col1, action_col2 = st.columns(2)

# ---------------------------------------------------
# CALCULATE
# ---------------------------------------------------
if action_col1.button("💰 Generate Quote"):
    if margin_pct >= 100:
        st.error("Margin must be below 100%")
        st.stop()

    if total_direct_cost == 0:
        st.warning("Add at least one item")
        st.stop()

    if margin_pct < 10:
        st.warning("Very low margin — risky pricing")

    overhead = total_direct_cost * (overhead_pct / 100)
    total_cost = total_direct_cost + overhead

    price = total_cost / (1 - margin_pct / 100)
    profit = price - total_cost
    margin = (profit / price) * 100 if price > 0 else 0

    walk_away = total_cost * 1.25
    suggested = (price + walk_away) / 2

    st.session_state.results = {
        "total_direct_cost": total_direct_cost,
        "total_labour": total_labour,
        "total_material": total_material,
        "overhead": overhead,
        "total_cost": total_cost,
        "price": price,
        "profit": profit,
        "margin": margin,
        "walk_away": walk_away,
        "suggested": suggested,
        "project_name": project_name,
        "boq_lines": boq_lines,
        "overhead_pct": overhead_pct
    }

    c.execute("""
    INSERT INTO quotes (
        ts, project, total_direct_cost, total_labour, total_material,
        overhead, total_cost, price, profit, margin, walk_away, suggested, user_id
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        project_name,
        total_direct_cost,
        total_labour,
        total_material,
        overhead,
        total_cost,
        price,
        profit,
        margin,
        walk_away,
        suggested,
        phone
    ))
    conn.commit()

if action_col2.button("➕ New Quote"):
    st.session_state.boq_items = []
    st.session_state.results = None
    st.rerun()

# ---------------------------------------------------
# RESULTS
# ---------------------------------------------------
if st.session_state.results:
    r = st.session_state.results

    st.markdown("## 📊 Results")

    st.success(f"""
Total Direct Cost: R{r['total_direct_cost']:,.0f}

Total Labour: R{r['total_labour']:,.0f}

Total Material: R{r['total_material']:,.0f}

Overhead: R{r['overhead']:,.0f}

Total Cost: R{r['total_cost']:,.0f}

Target Price: R{r['price']:,.0f}

Suggested: R{r['suggested']:,.0f}

Profit: R{r['profit']:,.0f}

Margin: {r['margin']:.1f}%

Walk-Away: R{r['walk_away']:,.0f}
""")

    st.markdown("### 📋 BOQ Breakdown")
    for line in r["boq_lines"]:
        st.write(
            f"{line['name']} — Cost: R{line['cost']:,.0f} | "
            f"Labour: R{line['labour_cost']:,.0f} | "
            f"Material: R{line['material_cost']:,.0f}"
        )

    # ---------------------------------------------------
    # DISCOUNT SIMULATION
    # ---------------------------------------------------
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

    # ---------------------------------------------------
    # PDF EXPORT
    # ---------------------------------------------------
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "ARLO PROJECT QUOTATION", ln=1, align="C")

    pdf.set_font("Arial", size=12)
    ref = f"ARLO-{secrets.token_hex(3).upper()}"
    today = datetime.now().strftime("%Y-%m-%d")

    pdf.cell(200, 8, f"Date: {today}", ln=1)
    pdf.cell(200, 8, f"Reference: {ref}", ln=1)
    pdf.cell(200, 8, f"Client: {client_name}", ln=1)
    pdf.cell(200, 8, f"Project: {project_name or 'General Works'}", ln=1)

    pdf.ln(8)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 8, f"Total Price: R{r['price']:,.0f}", ln=1)

    pdf.ln(5)
    pdf.set_font("Arial", size=12)

    body = [
        "BOQ Breakdown:",
        ""
    ]

    for line in r["boq_lines"]:
        body.append(
            f"{line['name']}: Cost R{line['cost']:,.0f} | "
            f"Labour R{line['labour_cost']:,.0f} | "
            f"Material R{line['material_cost']:,.0f}"
        )

    body.extend([
        "",
        f"Total Direct Cost: R{r['total_direct_cost']:,.0f}",
        f"Total Labour: R{r['total_labour']:,.0f}",
        f"Total Material: R{r['total_material']:,.0f}",
        f"Overhead ({r['overhead_pct']}%): R{r['overhead']:,.0f}",
        f"Total Cost: R{r['total_cost']:,.0f}",
        f"Suggested: R{r['suggested']:,.0f}",
        f"Walk-Away: R{r['walk_away']:,.0f}",
        "",
        "Prepared by ARLO - The Profit Prophet"
    ])

    pdf_text = "\n".join(body)
    safe_text = pdf_text.encode("latin-1", "ignore").decode("latin-1")
    pdf.multi_cell(0, 8, safe_text)

    pdf_raw = pdf.output(dest="S")
    if isinstance(pdf_raw, str):
        pdf_bytes = pdf_raw.encode("latin-1", "ignore")
    else:
        pdf_bytes = bytes(pdf_raw)

    b64 = base64.b64encode(pdf_bytes).decode()
    filename = f"ARLO_{ref}.pdf"

    href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}">📄 Download PDF Quote</a>'
    st.markdown(href, unsafe_allow_html=True)

# ---------------------------------------------------
# PRIVATE HISTORY
# ---------------------------------------------------
st.markdown("## 📊 Recent Quotes")

df = pd.read_sql_query(
    "SELECT * FROM quotes WHERE user_id = ? ORDER BY id DESC LIMIT 5",
    conn,
    params=(phone,)
)

if df.empty:
    st.info("No quotes yet.")
else:
    for _, row in df.iterrows():
        with st.expander(f"{row['ts']} | R{row['price']:,.0f}"):
            st.write(f"Project: {row['project'] or 'General Works'}")
            st.write(f"Total Direct Cost: **R{row['total_direct_cost']:,.0f}**")
            st.write(f"Total Labour: **R{row['total_labour']:,.0f}**")
            st.write(f"Total Material: **R{row['total_material']:,.0f}**")
            st.write(f"Profit: **R{row['profit']:,.0f}**")
            st.write(f"Margin: **{row['margin']:.1f}%**")
            st.write(f"Walk-Away: **R{row['walk_away']:,.0f}**")
            st.write(f"Suggested: **R{row['suggested']:,.0f}**")

# ---------------------------------------------------
# FOOTER
# ---------------------------------------------------
st.markdown("---")
st.caption("📱 Add to Home Screen → Use like an app")
st.caption("ARLO by The Profit Prophet")