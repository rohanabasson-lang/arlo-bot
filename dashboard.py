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
USAGE_LIMIT = 15

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

BUSINESS_MAP = AUTHORIZED_USERS

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
    div[data-testid="stMetric"] {
        background: #0f172a;
        border: 1px solid #1e293b;
        padding: 14px;
        border-radius: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# DATABASE SETUP
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

c.execute("""
CREATE TABLE IF NOT EXISTS usage_tracking (
    user_phone TEXT PRIMARY KEY,
    quote_count INTEGER DEFAULT 0
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


def safe_text(text) -> str:
    replacements = {
        "—": "-",
        "–": "-",
        "•": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "…": "...",
        "\u00a0": " ",
        "⚡": "",
        "👋": "",
        "✅": "",
        "🚫": "",
        "📄": "",
        "📋": "",
        "⚙️": "",
        "🔻": "",
        "📜": "",
        "🏗️": ""
    }

    text = str(text)
    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.encode("latin-1", "replace").decode("latin-1")


def get_usage(phone: str) -> int:
    result = c.execute(
        "SELECT quote_count FROM usage_tracking WHERE user_phone=?",
        (phone,)
    ).fetchone()

    if result:
        return int(result[0])

    c.execute(
        "INSERT INTO usage_tracking (user_phone, quote_count) VALUES (?, 0)",
        (phone,)
    )
    conn.commit()
    return 0


def increment_usage(phone: str) -> None:
    c.execute("""
        INSERT INTO usage_tracking (user_phone, quote_count)
        VALUES (?, 1)
        ON CONFLICT(user_phone)
        DO UPDATE SET quote_count = quote_count + 1
    """, (phone,))
    conn.commit()


def make_pdf_bytes(
    user_name: str,
    project_name: str,
    price: float,
    boq_items: list[dict],
    is_admin: bool = False
) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, safe_text("ARLO QUOTATION"), ln=True, align="C")

    pdf.ln(6)
    pdf.set_font("Arial", size=11)
    pdf.cell(190, 8, safe_text(f"Prepared for: {user_name}"), ln=True)
    pdf.cell(190, 8, safe_text(f"Project / Service: {project_name}"), ln=True)
    pdf.cell(190, 8, safe_text(f"Date: {datetime.now().strftime('%Y-%m-%d')}"), ln=True)
    valid_until = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    pdf.cell(190, 8, safe_text(f"Valid until: {valid_until}"), ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 8, safe_text("Price Summary"), ln=True)

    pdf.set_font("Arial", size=11)
    summary_text = (
        f"Total Price (excluding VAT): R{price:,.0f}\n"
        f"VAT @ 15%: R{price * 0.15:,.0f}\n\n"
        f"Total Amount Due (including VAT): R{price * 1.15:,.0f}"
    )
    pdf.multi_cell(180, 8, safe_text(summary_text))

    pdf.ln(12)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 8, safe_text("Project Breakdown"), ln=True)

    pdf.set_font("Arial", size=10)
    for idx, item in enumerate(boq_items, start=1):
        name = item["name"] if item["name"] else f"Line {idx}"
        line = (
            f"{idx}. {name} - Qty: {item['qty']:,.2f} | "
            f"Rate: R{item['rate']:,.0f} | "
            f"Subtotal: R{item['cost']:,.0f}"
        )
        pdf.multi_cell(0, 7, safe_text(line))
        pdf.ln(2)

    if is_admin:
        pdf.ln(12)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(190, 8, safe_text("Internal Pricing Details (Admin Only)"), ln=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 7, safe_text("(This section is hidden from clients)"))

    pdf.ln(12)
    footer = (
        "Prepared by ARLO - The Profit Prophet\n\n"
        "Payment Terms: 50% deposit on acceptance, balance on completion.\n"
        "Inclusions: As detailed in the breakdown above.\n"
        "Exclusions: Variations, additional work, unforeseen conditions.\n"
        "All prices exclude VAT unless stated otherwise.\n"
        "Quote valid for 30 days from date of issue."
    )
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 6, safe_text(footer))

    return pdf.output(dest="S").encode("latin-1", errors="ignore")

# =========================================================
# SESSION STATE
# =========================================================
if "boq" not in st.session_state:
    st.session_state.boq = []

if "last_saved_key" not in st.session_state:
    st.session_state.last_saved_key = None

if "user" not in st.session_state:
    st.session_state.user = None

# =========================================================
# UI – HEADER
# =========================================================
st.title("🏗️ ARLO Pricing Assistant")
st.caption("Professional quoting. Margin protected.")

# =========================================================
# AUTH / SESSION LOGIN
# =========================================================
if st.session_state.user is None:
    login_phone = st.text_input(
        "WhatsApp number",
        placeholder="e.g. 0712345678"
    )

    if not login_phone:
        st.info("Enter your number to continue.")
        st.stop()

    login_phone = login_phone.strip()

    if login_phone not in AUTHORIZED_USERS:
        st.error("Number not authorized.")
        st.stop()

    st.session_state.user = login_phone
    st.rerun()

user_phone = st.session_state.user
user_name = BUSINESS_MAP.get(user_phone, user_phone)
is_admin = user_phone in ADMIN_NUMBERS

# =========================================================
# WELCOME BANNER
# =========================================================
st.markdown(
    f"""
    <div style="background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: white; padding: 24px; border-radius: 12px; margin-bottom: 28px; text-align: center;">
        <h2 style="margin: 0; font-size: 2.1rem;">👋 Welcome back, {user_name}!</h2>
        <p style="margin: 12px 0 0; font-size: 1.1rem; opacity: 0.95;">Ready to create another sharp quote? ⚡</p>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.markdown(f"**Logged in as**  \n{user_name}")
st.sidebar.markdown(f"Phone: `{user_phone}`")

if is_admin:
    st.sidebar.success("Admin Mode Active")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.session_state.boq = []
    st.session_state.last_saved_key = None
    st.rerun()

# =========================================================
# USAGE DISPLAY
# =========================================================
usage = get_usage(user_phone)

if not is_admin:
    remaining = max(0, USAGE_LIMIT - usage)

    uc1, uc2 = st.columns(2)
    uc1.metric("Quotes Used", f"{usage}/{USAGE_LIMIT}")
    uc2.metric("Remaining", remaining)

    if usage >= USAGE_LIMIT:
        st.error("🚫 Quote limit reached (15). Upgrade required.")
        st.stop()
    elif remaining <= 3:
        st.warning("⚠️ You're almost out of quotes. Upgrade soon to avoid disruption.")

# =========================================================
# PROJECT NAME
# =========================================================
project_name = st.text_input("Project / Service Name", value="General Scope")

# =========================================================
# LINE ITEMS
# =========================================================
st.subheader("📋 Project Items")

col_a, col_b = st.columns(2)
with col_a:
    if st.button("➕ Add Line", use_container_width=True):
        st.session_state.boq.append({
            "name": "",
            "qty": 1.0,
            "rate": 0.0,
            "labour_pct": 50
        })
        st.rerun()

with col_b:
    if st.button("🧹 Clear / New", use_container_width=True):
        st.session_state.boq = []
        st.session_state.last_saved_key = None
        st.rerun()

total_direct_cost = 0.0
labour_portion = 0.0
material_portion = 0.0
boq_snapshot = []

for i, item in enumerate(st.session_state.boq):
    with st.expander(f"Line {i+1}", expanded=True):
        c1, c2, c3 = st.columns(3)

        item["name"] = c1.text_input(
            "Description",
            value=item["name"],
            key=f"name_{i}"
        )

        item["qty"] = c2.number_input(
            "Quantity",
            min_value=0.0,
            value=float(item["qty"]),
            step=0.1,
            key=f"qty_{i}"
        )

        item["rate"] = c3.number_input(
            "Unit Rate",
            min_value=0.0,
            value=float(item["rate"]),
            step=10.0,
            key=f"rate_{i}"
        )

        item["labour_pct"] = st.slider(
            "Labour portion %",
            0,
            100,
            int(item["labour_pct"]),
            key=f"lab_{i}"
        )

        cost = float(item["qty"]) * float(item["rate"])
        labour = cost * (item["labour_pct"] / 100)
        material = cost - labour

        total_direct_cost += cost
        labour_portion += labour
        material_portion += material

        boq_snapshot.append({
            "name": item["name"] or f"Line {i+1}",
            "qty": float(item["qty"]),
            "rate": float(item["rate"]),
            "cost": cost
        })

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Line Total", f"R{cost:,.0f}")
        mc2.metric("Labour", f"R{labour:,.0f}")
        mc3.metric("Material/Other", f"R{material:,.0f}")

        if st.button("🗑 Remove", key=f"del_{i}"):
            st.session_state.boq.pop(i)
            st.rerun()

st.divider()

# =========================================================
# PRICING
# =========================================================
st.subheader("⚙️ Markup & Margin")

pc1, pc2 = st.columns(2)
with pc1:
    overhead_pct = st.number_input(
        "Overhead / Business %",
        min_value=0.0,
        max_value=100.0,
        value=20.0,
        step=0.5,
        format="%.1f"
    )

with pc2:
    margin_pct = st.number_input(
        "Desired Margin %",
        min_value=1.0,
        max_value=99.0,
        value=30.0,
        step=0.5,
        format="%.1f"
    )

if total_direct_cost <= 0:
    st.info("Add at least one line item to see pricing.")
    st.stop()

overhead_amount = total_direct_cost * (overhead_pct / 100)
total_cost = total_direct_cost + overhead_amount
price = total_cost / (1 - margin_pct / 100)
suggested = price * 0.95
profit = price - total_cost
margin = (profit / price) * 100 if price > 0 else 0
walk_away = total_cost * 1.25

# =========================================================
# RESULTS (INTERNAL VIEW)
# =========================================================
with st.expander("Pricing Summary (internal)", expanded=is_admin):
    cols = st.columns(3)
    cols[0].metric("Direct Costs", f"R{total_direct_cost:,.0f}")
    cols[1].metric("Labour Portion", f"R{labour_portion:,.0f}")
    cols[2].metric("Material / Other", f"R{material_portion:,.0f}")

    cols = st.columns(3)
    cols[0].metric("Overhead", f"R{overhead_amount:,.0f}")
    cols[1].metric("Total Cost", f"R{total_cost:,.0f}")
    cols[2].metric("Expected Profit", f"R{profit:,.0f}")

    cols = st.columns(3)
    cols[0].metric("Target Price", f"R{price:,.0f}")
    cols[1].metric("Suggested Price", f"R{suggested:,.0f}")
    cols[2].metric("Walk-away", f"R{walk_away:,.0f}")

    st.metric("Achieved Margin", f"{margin:.1f}%")

    if margin < 15:
        st.error("Margin very low - high risk")
    elif margin < 25:
        st.warning("Margin quite thin - be cautious")
    else:
        st.success("Healthy margin range")

# =========================================================
# ACTIONS
# =========================================================
act1, act2 = st.columns(2)

quote_key = (
    user_phone,
    project_name,
    round(total_cost, 2),
    round(price, 2),
    round(margin, 2),
    len(boq_snapshot)
)

save_disabled = (not is_admin and usage >= USAGE_LIMIT)
pdf_disabled = (not is_admin and usage >= USAGE_LIMIT)

with act1:
    if st.button("💾 Save Quote", use_container_width=True, disabled=save_disabled):
        if st.session_state.last_saved_key == quote_key:
            st.info("Already saved (no changes)")
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

            if not is_admin:
                increment_usage(user_phone)
                usage = get_usage(user_phone)

            st.session_state.last_saved_key = quote_key
            st.success("Quote saved")
            st.rerun()

with act2:
    if pdf_disabled:
        st.button(
            "📄 Download Client Quotation",
            disabled=True,
            use_container_width=True
        )
    else:
        pdf_data = make_pdf_bytes(
            user_name=user_name,
            project_name=project_name,
            price=price,
            boq_items=boq_snapshot,
            is_admin=is_admin
        )

        st.download_button(
            "📄 Download Client Quotation",
            data=pdf_data,
            file_name=f"ARLO_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# =========================================================
# DISCOUNT SIMULATOR
# =========================================================
st.subheader("🔻 Quick Discount Check")

disc = st.slider("Discount %", 0, 25, 0)

if disc > 0:
    new_price = price * (1 - disc / 100)
    new_profit = new_price - total_cost
    new_margin = (new_profit / new_price) * 100 if new_price > 0 else 0

    st.warning(
        f"After {disc}% discount:\n\n"
        f"**Price:** R{new_price:,.0f}\n"
        f"**Profit:** R{new_profit:,.0f}\n"
        f"**Margin:** {new_margin:.1f}%"
    )

# =========================================================
# HISTORY
# =========================================================
st.subheader("📜 Quote History")

if is_admin:
    quotes_df = get_all_quotes()
else:
    quotes_df = get_user_quotes(user_phone)

if quotes_df.empty:
    st.info("No saved quotes yet")
else:
    for _, r in quotes_df.iterrows():
        with st.expander(f"{r['timestamp']} - R{r['price']:,.0f}"):
            st.write(f"**Client** {r['client_name']}")
            st.write(f"**Project/Service** {r['project']}")
            st.write(f"Total Cost: R{r['total_cost']:,.0f}")
            st.write(f"Profit: R{r['profit']:,.0f}")
            st.write(f"Margin: {r['margin']:.1f}%")
            st.write(f"Suggested: R{r['suggested']:,.0f}")

# =========================================================
# FOOTER
# =========================================================
st.markdown("---")
st.caption("ARLO • Multi-industry Pricing • v1.5 - Full client list + usage tracking + PDF safe")