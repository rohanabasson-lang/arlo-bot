import streamlit as st
import sqlite3
import pandas as pd
import json
from datetime import datetime, timedelta
from fpdf import FPDF

st.set_page_config(page_title="ARLO Pricing Assistant", page_icon="🏗️", layout="wide")

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

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1100px;}
.stMetric {background: #0f172a; border: 1px solid #1e293b; padding: 14px; border-radius: 14px;}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

conn = get_db_connection()
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_phone TEXT,
    client_name TEXT,
    client_phone TEXT,
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
    boq_json TEXT,
    timestamp TEXT,
    quote_number TEXT,
    selected_price_type TEXT
)
""")
try: c.execute("ALTER TABLE quotes ADD COLUMN selected_price_type TEXT"); conn.commit()
except: pass

c.execute("""
CREATE TABLE IF NOT EXISTS usage_tracking (
    user_phone TEXT PRIMARY KEY,
    quote_count INTEGER DEFAULT 0,
    last_reset TEXT,
    quote_counter INTEGER DEFAULT 0
)
""")
conn.commit()

def safe_text(text):
    if not text: return ""
    text = str(text)
    for k, v in {"—": "-", "–": "-", "•": "-", "“": '"', "”": '"', "’": "'", "‘": "'", "…": "..."}.items():
        text = text.replace(k, v)
    return text

def get_or_init_user(phone):
    c.execute("SELECT quote_count, last_reset, quote_counter FROM usage_tracking WHERE user_phone=?", (phone,))
    row = c.fetchone()
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d")
    if not row:
        c.execute("INSERT INTO usage_tracking (user_phone, quote_count, last_reset, quote_counter) VALUES (?, 0, ?, 0)", (phone, now_str))
        conn.commit()
        return 0, now_str, 0
    count, last_reset_str, qcounter = row
    if not last_reset_str:
        last_reset_str = now_str
        c.execute("UPDATE usage_tracking SET last_reset=? WHERE user_phone=?", (now_str, phone))
        conn.commit()
    try:
        last_reset = datetime.strptime(last_reset_str, "%Y-%m-%d")
    except:
        last_reset = now
    if (now - last_reset).days >= 30:
        count = 0
        last_reset_str = now_str
        c.execute("UPDATE usage_tracking SET quote_count=0, last_reset=? WHERE user_phone=?", (last_reset_str, phone))
        conn.commit()
    return count, last_reset_str, qcounter

def increment_usage(phone):
    c.execute("UPDATE usage_tracking SET quote_count=quote_count+1, quote_counter=quote_counter+1 WHERE user_phone=?", (phone,))
    conn.commit()

def generate_quote_number(phone, counter):
    return f"ARLO-{datetime.now().strftime('%Y')}-{counter:04d}"

def save_quote(data):
    c.execute("""
    INSERT INTO quotes (user_phone, client_name, client_phone, project,
    total_direct_cost, labour_portion, material_portion, overhead_pct, overhead_amount,
    total_cost, price, suggested, profit, margin, walk_away, boq_json, timestamp, quote_number, selected_price_type)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()

def get_user_quotes(phone):
    return pd.read_sql_query("SELECT * FROM quotes WHERE user_phone=? ORDER BY id DESC", conn, params=(phone,))

def get_all_quotes():
    return pd.read_sql_query("SELECT * FROM quotes ORDER BY id DESC", conn)

class QuotePDF(FPDF):
    def header(self):
        self.set_fill_color(30, 58, 138)
        self.rect(0, 0, 210, 24, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 18)
        self.cell(0, 12, "ARLO QUOTATION", ln=True, align="C")
        self.set_font("Arial", size=9)
        self.cell(0, 0, "Professional quoting. Margin protected.", align="C")
        self.ln(10)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-18)
        self.set_draw_color(220, 220, 220)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)
        self.set_font("Arial", size=8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, "Prepared by ARLO - The Profit Prophet", ln=True, align="C")
        self.cell(0, 5, f"Page {self.page_no()}", align="C")

def pdf_section_title(pdf, title):
    pdf.set_fill_color(245, 247, 250)
    pdf.set_draw_color(220, 220, 220)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, title, border=1, ln=True, fill=True)
    pdf.ln(2)

def make_pdf_bytes(user_name, client_name, client_phone, project_name, final_price, boq_items, quote_number="", price_type="", is_admin=False):
    pdf = QuotePDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    quote_date = datetime.now().strftime("%Y-%m-%d")
    valid_until = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    vat = final_price * 0.15
    total_vat = final_price * 1.15

    pdf.ln(4)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(95, 8, "Prepared For", border=1, ln=0)
    pdf.cell(0, 8, "Quotation Details", border=1, ln=1)

    pdf.set_font("Arial", size=10)
    pdf.cell(95, 8, client_name or "Valued Client", border=1, ln=0)
    pdf.cell(0, 8, f"Date: {quote_date}", border=1, ln=1)
    pdf.cell(95, 8, client_phone or "-", border=1, ln=0)
    pdf.cell(0, 8, f"Valid Until: {valid_until}", border=1, ln=1)
    pdf.cell(95, 8, project_name, border=1, ln=0)
    pdf.cell(0, 8, f"From: {user_name}", border=1, ln=1)

    pdf.ln(6)

    pdf_section_title(pdf, "Price Summary")
    pdf.set_font("Arial", size=10)
    pdf.cell(120, 8, "Selected Price excl. VAT", border=1, ln=0)
    pdf.cell(0, 8, f"R{final_price:,.0f}", border=1, ln=1)
    pdf.cell(120, 8, "VAT @ 15%", border=1, ln=0)
    pdf.cell(0, 8, f"R{vat:,.0f}", border=1, ln=1)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(120, 9, "Total Amount Due (incl. VAT)", border=1, ln=0)
    pdf.cell(0, 9, f"R{total_vat:,.0f}", border=1, ln=1)

    pdf.ln(6)

    pdf_section_title(pdf, "Project Breakdown")
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(235, 240, 248)
    pdf.cell(12, 8, "#", border=1, align="C", fill=True)
    pdf.cell(70, 8, "Description", border=1, fill=True)
    pdf.cell(20, 8, "Qty", border=1, align="C", fill=True)
    pdf.cell(25, 8, "Rate", border=1, align="R", fill=True)
    pdf.cell(30, 8, "Labour", border=1, align="R", fill=True)
    pdf.cell(30, 8, "Material/Other", border=1, align="R", fill=True)
    pdf.cell(35, 8, "Subtotal", border=1, align="R", ln=1, fill=True)

    pdf.set_font("Arial", size=9)
    for idx, item in enumerate(boq_items, 1):
        name = safe_text(item.get("name") or f"Line {idx}")
        qty = item.get('qty', 0)
        rate = item.get('rate', 0)
        labour_pct = item.get('labour_pct', 50)
        cost = qty * rate
        labour = cost * (labour_pct / 100)
        material = cost - labour

        row_y = pdf.get_y()
        pdf.cell(12, 8, str(idx), border=1, align="C")
        x = pdf.get_x()
        pdf.multi_cell(70, 8, name, border=1)
        h = max(pdf.get_y() - row_y, 8)
        pdf.set_xy(x + 70, row_y)
        pdf.cell(20, h, f"{qty:,.2f}", border=1, align="C")
        pdf.cell(25, h, f"R{rate:,.0f}", border=1, align="R")
        pdf.cell(30, h, f"R{labour:,.0f}", border=1, align="R")
        pdf.cell(30, h, f"R{material:,.0f}", border=1, align="R")
        pdf.cell(35, h, f"R{cost:,.0f}", border=1, align="R", ln=1)

    pdf.ln(6)
    pdf_section_title(pdf, "Terms & Notes")
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 6, "Payment Terms: 50% deposit, balance on completion.\nInclusions: As per breakdown.\nExclusions: Variations, additional work, unforeseen conditions.\nAll prices exclude VAT unless stated otherwise.\nQuote valid for 30 days from date of issue.")

    pdf_bytes = pdf.output(dest="S")
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("latin-1", errors="ignore")
    elif isinstance(pdf_bytes, bytearray):
        pdf_bytes = bytes(pdf_bytes)
    return pdf_bytes

# Session state initialization
for key, default in [("boq", []), ("last_saved_key", None), ("user", None), ("project_name", "General Scope"), ("client_name", ""), ("client_phone", ""), ("selected_price_type", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# Login
if st.session_state.user is None:
    st.markdown("### Login")
    login_phone = st.text_input("WhatsApp number (your registered business number)", placeholder="e.g. 0712345678")
    if not login_phone:
        st.info("Enter your number to continue.")
        st.stop()
    login_phone = login_phone.strip().replace(" ", "")
    if login_phone not in AUTHORIZED_USERS:
        st.error("Number not authorized.")
        st.stop()
    st.session_state.user = login_phone
    st.success(f"Welcome back, {AUTHORIZED_USERS[login_phone]}!")
    st.rerun()

user_phone = st.session_state.user
user_name = BUSINESS_MAP.get(user_phone, user_phone)
is_admin = user_phone in ADMIN_NUMBERS

# Usage tracking
usage, reset_date, quote_counter = get_or_init_user(user_phone)

if not is_admin:
    remaining = max(0, USAGE_LIMIT - usage)
    c1, c2 = st.columns(2)
    c1.metric("Quotes This Month", f"{usage}/{USAGE_LIMIT}")
    c2.metric("Resets on", reset_date)
    if usage >= USAGE_LIMIT:
        st.error("🚫 Monthly quote limit reached.")
        st.markdown("### Upgrade to continue")
        if st.button("Upgrade (R99 / month)", use_container_width=True):
            st.info("Payment link coming soon – DM Rohan for early unlock.")
        st.stop()
    if remaining <= 3:
        st.warning(f"Only {remaining} quotes left this month.")

st.title("🏗️ ARLO Pricing Assistant")
st.caption("Built for SA contractors")

st.sidebar.markdown(f"**Logged in as**  \n{user_name}")
st.sidebar.markdown(f"Phone: `{user_phone}`")
if is_admin: st.sidebar.success("Admin Mode")
if st.sidebar.button("Logout"):
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

# Client & Project
col1, col2 = st.columns(2)
with col1:
    st.session_state.client_name = st.text_input("Client Name", value=st.session_state.client_name, key="client_name_key")
with col2:
    st.session_state.client_phone = st.text_input("Client Phone (optional)", value=st.session_state.client_phone, key="client_phone_key")
st.session_state.project_name = st.text_input("Project / Service Name", value=st.session_state.project_name, key="project_name_key")

# Line Items
st.subheader("📋 Project Items")
col_a, col_b = st.columns(2)
with col_a:
    if st.button("➕ Add Line", use_container_width=True):
        st.session_state.boq.append({"name": "", "qty": 1.0, "rate": 0.0, "labour_pct": 50})
        st.rerun()
with col_b:
    if st.button("🧹 Clear / New Quote", use_container_width=True):
        st.session_state.boq = []
        st.session_state.last_saved_key = None
        st.session_state.selected_price_type = None
        st.rerun()

total_direct_cost = labour_portion = material_portion = 0.0
boq_snapshot = []

for i, item in enumerate(st.session_state.boq):
    with st.expander(f"Line {i+1}", expanded=True):
        c1, c2, c3 = st.columns(3)
        item["name"] = c1.text_input("Description", value=item.get("name",""), key=f"name_{i}")
        item["qty"] = c2.number_input("Qty", min_value=0.0, value=float(item.get("qty",1)), step=0.1, key=f"qty_{i}")
        item["rate"] = c3.number_input("Unit Rate", min_value=0.0, value=float(item.get("rate",0)), step=10.0, key=f"rate_{i}")
        item["labour_pct"] = st.slider("Labour %", 0, 100, int(item.get("labour_pct",50)), key=f"lab_{i}")

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
            "labour_pct": item["labour_pct"],
            "labour": labour,
            "material": material,
            "cost": cost
        })

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Line Total", f"R{cost:,.0f}")
        mc2.metric("Labour", f"R{labour:,.0f}")
        mc3.metric("Material", f"R{material:,.0f}")

        if st.button("🗑 Remove", key=f"del_{i}"):
            st.session_state.boq.pop(i)
            st.rerun()

st.divider()

if len(st.session_state.boq) == 0:
    st.info("➕ Add at least one line item to continue.")
    st.stop()

st.subheader("⚙️ Markup & Margin")
pc1, pc2 = st.columns(2)
with pc1:
    overhead_pct = st.number_input("Overhead %", 0.0, 100.0, 20.0, step=0.5, format="%.1f")
with pc2:
    margin_pct = st.number_input("Desired Margin %", 1.0, 99.0, 30.0, step=0.5, format="%.1f")

overhead_amount = total_direct_cost * (overhead_pct / 100)
total_cost = total_direct_cost + overhead_amount

target_price    = total_cost / (1 - margin_pct / 100) if margin_pct < 100 else 0
suggested_price = target_price * 0.95
walkaway_price  = total_cost * 1.25

profit_t = target_price - total_cost
margin_t = (profit_t / target_price * 100) if target_price > 0 else 0

profit_s = suggested_price - total_cost
margin_s = (profit_s / suggested_price * 100) if suggested_price > 0 else 0

profit_w = walkaway_price - total_cost
margin_w = (profit_w / walkaway_price * 100) if walkaway_price > 0 else 0

# Price tiles
st.subheader("Final Price Options")
t1, t2, t3 = st.columns(3)

with t1:
    st.metric("Target Price", f"R{target_price:,.0f}", f"{margin_t:.1f}% margin | R{profit_t:,.0f} profit")

with t2:
    st.metric("Suggested Price", f"R{suggested_price:,.0f}", f"{margin_s:.1f}% margin | R{profit_s:,.0f} profit")

with t3:
    st.metric("Walk-away Price", f"R{walkaway_price:,.0f}", f"{margin_w:.1f}% margin | R{profit_w:,.0f} profit")

st.subheader("Select Price to Quote")
selected_type = st.radio(
    "Choose which price to use for this quote:",
    options=["Target Price", "Suggested Price", "Walk-away Price"],
    index=None,
    horizontal=True,
    key="price_radio"
)

if not selected_type:
    st.warning("Please select one of the prices above to save or download the quote.")
    st.stop()

if selected_type == "Target Price":
    final_price, final_profit, final_margin = target_price, profit_t, margin_t
elif selected_type == "Suggested Price":
    final_price, final_profit, final_margin = suggested_price, profit_s, margin_s
else:
    final_price, final_profit, final_margin = walkaway_price, profit_w, margin_w

st.success(f"Selected **{selected_type}**: R{final_price:,.0f} (Profit R{final_profit:,.0f} | {final_margin:.1f}%)")

# Save & Download
act1, act2 = st.columns(2)
save_disabled = (not is_admin and usage >= USAGE_LIMIT)

with act1:
    if st.button("💾 Save Quote", use_container_width=True, disabled=save_disabled):
        c.execute("SELECT quote_counter FROM usage_tracking WHERE user_phone=?", (user_phone,))
        fresh = c.fetchone()
        fresh_counter = fresh[0] if fresh else 0
        new_counter = fresh_counter + 1
        quote_num = generate_quote_number(user_phone, new_counter)

        save_quote((
            user_phone, st.session_state.client_name, st.session_state.client_phone,
            st.session_state.project_name, total_direct_cost, labour_portion, material_portion,
            float(overhead_pct), overhead_amount, total_cost,
            target_price, suggested_price, final_profit, final_margin, walkaway_price,
            json.dumps(boq_snapshot),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), quote_num,
            selected_type
        ))

        if not is_admin:
            increment_usage(user_phone)

        st.success(f"Quote **{quote_num}** saved ({selected_type})!")
        st.balloons()
        st.rerun()

with act2:
    if save_disabled:
        st.button("📄 Download Quotation", disabled=True, use_container_width=True)
    else:
        safe_num = quote_num if 'quote_num' in locals() else "ARLO"
        pdf_data = make_pdf_bytes(
            user_name=user_name,
            client_name=st.session_state.client_name,
            client_phone=st.session_state.client_phone,
            project_name=st.session_state.project_name,
            final_price=final_price,
            boq_items=boq_snapshot,
            quote_number=safe_num,
            price_type=selected_type,
            is_admin=is_admin
        )
        st.download_button(
            "📄 Download Quotation",
            data=pdf_data,
            file_name=f"ARLO_Quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

st.caption("ARLO • SA contractors tool")