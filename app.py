import streamlit as st
import pandas as pd
from datetime import datetime
import sqlalchemy
from sqlalchemy import text
import urllib.parse
import time
import json
import io 
from PIL import Image

# --- DATABASE SETUP (POSTGRESQL / SUPABASE) ---
# Ensure your .streamlit/secrets.toml has [connections.postgresql]
conn = st.connection("postgresql", type="sql")

def init_db():
    # 1. CREATE ALL TABLES
    with conn.session as s:
        s.execute(text('''CREATE TABLE IF NOT EXISTS users 
                     (username TEXT PRIMARY KEY, password TEXT, role TEXT, dept TEXT, status TEXT DEFAULT 'ACTIVE', verified INTEGER DEFAULT 0)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS customers 
                     (plate TEXT PRIMARY KEY, name TEXT, phone TEXT, visits INTEGER, last_visit TEXT)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS sales 
                     (id SERIAL PRIMARY KEY, plate TEXT, services TEXT, total REAL, method TEXT, staff TEXT, timestamp TEXT, type TEXT)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS notifications 
                     (id SERIAL PRIMARY KEY, message TEXT, timestamp TEXT)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS live_bays 
                     (plate TEXT PRIMARY KEY, status TEXT, entry_time TEXT, staff TEXT, vehicle_type TEXT, service_detail TEXT, wet_staff_history TEXT)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS inventory (item TEXT PRIMARY KEY, stock REAL, unit TEXT, price REAL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS wash_prices (service TEXT PRIMARY KEY, price REAL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS expenses (id SERIAL PRIMARY KEY, description TEXT, amount REAL, timestamp TEXT)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS memberships 
                     (plate TEXT PRIMARY KEY, balance_washes INTEGER, card_type TEXT, sale_price REAL DEFAULT 0.0)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS staff_profiles 
                     (username TEXT PRIMARY KEY, full_name TEXT, phone TEXT, address TEXT, nin TEXT, bank_name TEXT, account_no TEXT, id_type TEXT, id_image BYTEA)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS staff_payroll_config 
                     (username TEXT PRIMARY KEY, base_salary REAL DEFAULT 0.0, bonus_pc REAL DEFAULT 0.0)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS earnings_log 
                     (id SERIAL PRIMARY KEY, username TEXT, amount REAL, ref_plate TEXT, timestamp TEXT)'''))
        
        # Migration
        try:
            s.execute(text("ALTER TABLE live_bays ADD COLUMN wet_staff_history TEXT"))
        except:
            pass
        s.commit()

    # 2. SEED DATA (Independent Transaction)
    with conn.session as s:
        # Seed Admin
        s.execute(text("INSERT INTO users (username, password, role, dept, status, verified) VALUES ('admin', '0000', 'MANAGER', 'MANAGEMENT', 'ACTIVE', 1) ON CONFLICT (username) DO NOTHING"))
        
        # Seed Inventory
        items = [('Car Shampoo', 10.0, 'Gallons', 0), ('Coke', 50.0, 'Cans', 500), ('Water', 100.0, 'Bottles', 200)]
        for item, stock, unit, price in items:
            s.execute(text("INSERT INTO inventory (item, stock, unit, price) VALUES (:i, :s, :u, :p) ON CONFLICT (item) DO NOTHING"), 
                      {"i": item, "s": stock, "u": unit, "p": price})
        
        # Seed Wash Prices
        initial_services = [
            ("Standard Wash", 5000), 
            ("Executive Detail", 15000), 
            ("Engine Steam", 10000), 
            ("Ceramic Wax", 25000), 
            ("Interior Deep Clean", 12000)
        ]
        for name, price in initial_services:
            s.execute(text("INSERT INTO wash_prices (service, price) VALUES (:s, :p) ON CONFLICT (service) DO NOTHING"), 
                      {"s": name, "p": price})
        
        s.commit()

init_db()

# --- CLASSIC UI STYLING ---
st.set_page_config(page_title="RideBoss Autos HQ", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #E0E0E0; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #0A0A0A; border-right: 1px solid #222; }
    .status-card { background: #0F0F0F; padding: 25px; border-radius: 2px; border-left: 4px solid #00d4ff; margin-bottom: 15px; border-top: 1px solid #1A1A1A; }
    .notification-bar { background: #00d4ff22; padding: 12px; border-bottom: 1px solid #00d4ff; color: #00d4ff; font-size: 0.85em; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 30px; }
    .stButton>button { border-radius: 0px; letter-spacing: 2px; font-size: 0.8em; text-transform: uppercase; background-color: transparent; border: 1px solid #333; color: white; height: 3em; transition: 0.4s; width: 100%; }
    .stButton>button:hover { border-color: #00d4ff; color: #00d4ff; background-color: #00d4ff11; }
    .monitor-container { background: #000; border: 2px solid #222; border-radius: 10px; height: 700px; overflow: hidden; position: relative; }
    .scroll-content { position: absolute; width: 100%; animation: scrollUp 40s linear infinite; will-change: transform; }
    @keyframes scrollUp { 0% { transform: translateY(100%); } 100% { transform: translateY(-100%); } }
    .scroll-content:hover { animation-play-state: paused; }
    .monitor-row { display: flex; justify-content: space-between; align-items: center; padding: 30px; border-bottom: 2px solid #222; background: #050505; }
    .monitor-plate { font-size: 55px; font-weight: 900; color: #00d4ff; font-family: 'Courier New', monospace; }
    .monitor-status { font-size: 18px; color: #FFD700; font-weight: bold; }
    .monitor-meta { text-align: right; }
    .monitor-staff { font-size: 20px; color: #888; text-transform: uppercase; }
    .monitor-svc { color: #00d4ff; font-style: italic; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

# --- SPECIAL PRINT RENDERER ---
query_params = st.query_params
if "print_receipt" in query_params:
    receipt_data = json.loads(query_params["print_receipt"])
    st.markdown(f"""
        <style>
            @media print {{
                body {{ background: white !important; }}
                .stApp {{ background: white !important; }}
                [data-testid="stSidebar"], header, .stButton {{ display: none !important; }}
            }}
            .print-wrap {{ background: white; color: black; padding: 30px; font-family: 'Courier New', Courier, monospace; max-width: 400px; margin: auto; border: 2px solid black; }}
            .print-header {{ text-align: center; border-bottom: 2px solid black; padding-bottom: 10px; margin-bottom: 15px; }}
            .print-row {{ display: flex; justify-content: space-between; margin: 5px 0; font-size: 14px; }}
            .print-divider {{ border-top: 1px dashed black; margin: 15px 0; }}
            .print-total {{ border-top: 2px solid black; margin-top: 10px; padding-top: 10px; font-weight: bold; font-size: 22px; display: flex; justify-content: space-between; }}
            .footer {{ text-align: center; font-size: 12px; margin-top: 30px; border-top: 1px solid black; padding-top: 10px; }}
        </style>
        <div class="print-wrap">
            <div class="print-header">
                <h1 style="margin:0; font-size:24px; color: black !important;">RIDEBOSS AUTOS</h1>
                <p style="margin:0; font-size:12px; letter-spacing:2px; color: black !important;">PREMIUM DETAILING & LOUNGE</p>
            </div>
            <div class="print-row"><span>REF NO:</span> <span>#RB{receipt_data['id']}</span></div>
            <div class="print-row"><span>DATE:</span> <span>{receipt_data['date']}</span></div>
            <div class="print-row"><span>PLATE:</span> <b>{receipt_data['plate']}</b></div>
            <div class="print-divider"></div>
            <div style="min-height: 100px;">
                <p style="font-size:12px; margin-bottom:5px;">SERVICES RENDERED:</p>
                <p style="font-size:16px; font-weight:bold;">{receipt_data['items']}</p>
            </div>
            <div class="print-total"><span>TOTAL</span><span>₦{receipt_data['total']:,}</span></div>
            <div class="footer">THANK YOU FOR YOUR PATRONAGE<br>www.ridebossautos.com</div>
        </div>
        <script>window.print();</script>
    """, unsafe_allow_html=True)
    st.stop()

# --- UTILITIES ---
def add_event(msg):
    now = datetime.now().strftime("%H:%M:%S")
    with conn.session as s:
        s.execute(text("INSERT INTO notifications (message, timestamp) VALUES (:m, :t)"), {"m": f"{now} | {msg}", "t": now})
        s.commit()

def format_whatsapp(phone, message):
    return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"

def get_free_staff_by_dept(dept_name):
    busy_list = conn.query("SELECT staff FROM live_bays", ttl=0)['staff'].tolist()
    all_dept = conn.query("SELECT username FROM users WHERE dept=:d AND status='ACTIVE' AND verified=1", 
                          params={"d": dept_name}, ttl=0)['username'].tolist()
    return [s for s in all_dept if s not in busy_list]

def calculate_payouts(username):
    with conn.session as s:
        res = s.execute(text("SELECT base_salary FROM staff_payroll_config WHERE username=:u"), {"u": username}).fetchone()
        base = res[0] if res else 0.0
    
    df_comm = conn.query("SELECT * FROM earnings_log WHERE username=:u", params={"u": username}, ttl=0)
    if df_comm.empty:
        return base, 0.0, 0.0, 0.0, base

    df_comm['timestamp'] = pd.to_datetime(df_comm['timestamp'])
    now = datetime.now()
    
    daily_comm = df_comm[df_comm['timestamp'].dt.date == now.date()]['amount'].sum()
    monthly_comm = df_comm[(df_comm['timestamp'].dt.month == now.month) & (df_comm['timestamp'].dt.year == now.year)]['amount'].sum()
    yearly_comm = df_comm[df_comm['timestamp'].dt.year == now.year]['amount'].sum()
    
    return base, daily_comm, monthly_comm, yearly_comm, (base + monthly_comm)

# --- LOGIN SYSTEM ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = None
if 'user_name' not in st.session_state: st.session_state.user_name = None
if 'user_dept' not in st.session_state: st.session_state.user_dept = None

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align:center; letter-spacing:10px; margin-top:100px;'>RIDEBOSS LOGIN</h1>", unsafe_allow_html=True)
    _, log_col, _ = st.columns([1,1,1])
    with log_col:
        u = st.text_input("Username").strip()
        p = st.text_input("Password", type="password")
        if st.button("ACCESS SYSTEM"):
            with conn.session as s:
                result = s.execute(text("SELECT role, dept FROM users WHERE username=:u AND password=:p"), {"u": u, "p": p}).fetchone()
                if result:
                    st.session_state.logged_in = True
                    st.session_state.user_role = result[0]
                    st.session_state.user_dept = result[1]
                    st.session_state.user_name = u
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
    st.stop()

# --- STAFF INDUCTION GATE ---
with conn.session as s:
    res_v = s.execute(text("SELECT verified FROM users WHERE username=:u"), {"u": st.session_state.user_name}).fetchone()
    is_verified = res_v[0] if res_v else 0

if st.session_state.user_role == "STAFF" and is_verified == 0:
    st.markdown("<h2 style='text-align:center; color:#00d4ff;'>RIDEBOSS INDUCTION</h2>", unsafe_allow_html=True)
    st.info("Please complete your verification details to unlock the system.")
    
    with st.form("staff_verification_form"):
        col1, col2 = st.columns(2)
        with col1:
            fn = st.text_input("Full Legal Name")
            ph = st.text_input("Phone Number")
            addr = st.text_area("Residential Address")
        with col2:
            nin = st.text_input("NIN (11 Digits)", max_chars=11)
            bn = st.text_input("Bank Name")
            acc = st.text_input("Account Number")
        
        st.markdown("---")
        st.write("IDENTITY VERIFICATION")
        id_type = st.selectbox("Document Type", ["National ID Card", "Drivers License", "International Passport"])
        id_file = st.file_uploader("Upload Clear Photo of ID", type=['jpg', 'png', 'jpeg'])

        if st.form_submit_button("SUBMIT FOR VERIFICATION"):
            if len(nin) != 11 or not nin.isdigit():
                st.error("Invalid NIN. Please provide exactly 11 digits.")
            elif fn and ph and addr and nin and bn and acc and id_file:
                img_bytes = id_file.getvalue()
                with conn.session as s:
                    s.execute(text("""INSERT INTO staff_profiles (username, full_name, phone, address, nin, bank_name, account_no, id_type, id_image) 
                                   VALUES (:u, :fn, :ph, :addr, :nin, :bn, :acc, :idt, :img) 
                                   ON CONFLICT (username) DO UPDATE SET full_name=EXCLUDED.full_name, id_image=EXCLUDED.id_image"""),
                              {"u": st.session_state.user_name, "fn": fn, "ph": ph, "addr": addr, "nin": nin, "bn": bn, "acc": acc, "idt": id_type, "img": img_bytes})
                    s.commit()
                st.success("Details submitted! Awaiting Manager Approval.")
                st.info("Log out and wait for your manager to verify your account.")
            else:
                st.error("Please fill all fields and upload ID.")
    
    if st.button("LOGOUT"):
        st.session_state.logged_in = False
        st.rerun()
    st.stop()

# --- LOAD CONFIG ---
wash_prices_df = conn.query("SELECT * FROM wash_prices", ttl=0)
SERVICES = dict(zip(wash_prices_df['service'], wash_prices_df['price']))
COUNTRY_CODES = {"Nigeria": "+234", "Ghana": "+233", "UK": "+44", "USA": "+1", "UAE": "+971"}

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown(f"USER: **{st.session_state.user_name}**")
st.sidebar.caption(f"DEPT: {st.session_state.user_dept}")

if st.session_state.user_role == "MANAGER":
    menu = ["COMMAND CENTER", "LIVE U-FLOW", "ONBOARD STAFF", "BOSS HR", "FINANCIALS", "INVENTORY & STAFF", "CRM & RETENTION", "NOTIFICATIONS"]
elif st.session_state.user_dept == "RECEPTIONIST":
    menu = ["COMMAND CENTER", "LIVE U-FLOW", "MY EARNINGS", "NOTIFICATIONS"]
else:
    menu = ["LIVE U-FLOW", "MY EARNINGS", "NOTIFICATIONS"]

choice = st.sidebar.radio("NAVIGATE", menu)
if st.sidebar.button("LOGOUT"):
    st.session_state.logged_in = False
    st.rerun()

# --- TOP NOTIFICATION FEED ---
latest_note = conn.query("SELECT message FROM notifications ORDER BY id DESC LIMIT 1", ttl=0)
st.markdown(f'<div class="notification-bar">SYSTEM LOG: {latest_note["message"].iloc[0] if not latest_note.empty else "READY"}</div>', unsafe_allow_html=True)

# --- 1. COMMAND CENTER ---
if choice == "COMMAND CENTER":
    tab_trans, tab_mem = st.tabs(["NEW TRANSACTION", "REGISTER MEMBERSHIP"])
    
    with tab_trans:
        mode = st.radio("SELECT MODE", ["CAR WASH", "LOUNGE"], horizontal=True)
        st.markdown("---")
        
        cust_data = conn.query("SELECT * FROM customers", ttl=0)
        search_options = ["NEW CUSTOMER"] + [f"{r['plate']} - {r['name']} ({r['phone']})" for _, r in cust_data.iterrows()]
        search_selection = st.selectbox("SEARCH EXISTING CLIENT", search_options)
        
        d_plate, d_name, d_phone = "", "", ""
        if search_selection != "NEW CUSTOMER":
            p_key = search_selection.split(" - ")[0]
            match = cust_data[cust_data['plate'] == p_key].iloc[0]
            d_plate, d_name, d_phone = match['plate'], match['name'], match['phone']

        col1, col2 = st.columns(2)
        with col1:
            plate = st.text_input("PLATE NUMBER", value=d_plate).upper()
            v_type = st.selectbox("VEHICLE TYPE", ["Sedan", "SUV", "Truck", "Crossover", "Bike", "Other"])
            name = st.text_input("CLIENT NAME", value=d_name)
            c_code = st.selectbox("COUNTRY CODE", list(COUNTRY_CODES.keys()))
            phone_raw = st.text_input("PHONE (No leading zero)", value=d_phone[3:] if d_phone else "")
            full_phone = f"{COUNTRY_CODES[c_code].replace('+', '')}{phone_raw}" if not d_phone else d_phone

        with col2:
            lounge_items_sold = []
            if mode == "CAR WASH":
                selected = st.multiselect("SERVICES", list(SERVICES.keys()))
                if selected and "Standard Wash" in selected and "Ceramic Wax" not in selected:
                    st.warning("💡 PROMPT: Ask client if they want Ceramic Wax for long-lasting shine!")
                total_price = sum([SERVICES[s] for s in selected])
                wet_staff = get_free_staff_by_dept("WET BAY")
                staff_assigned = st.selectbox("ASSIGN WET BAY DETAILER", wet_staff if wet_staff else ["NO FREE STAFF"])
                item_summary = ", ".join(selected)
            else:
                inv_items = conn.query("SELECT item, price FROM inventory WHERE price > 0", ttl=0)
                items_list = st.multiselect("SELECT ITEMS", inv_items['item'].tolist())
                total_price = 0
                for item in items_list:
                    u_price = inv_items[inv_items['item'] == item]['price'].values[0]
                    qty = st.number_input(f"Quantity for {item}", min_value=1, value=1)
                    total_price += (u_price * qty)
                    lounge_items_sold.append((item, qty))
                staff_assigned = st.session_state.user_name
                item_summary = ", ".join([f"{i} (x{q})" for i, q in lounge_items_sold])

            st.markdown(f"### TOTAL: ₦{total_price:,}")
            pay_method = st.selectbox("PAYMENT METHOD", ["Moniepoint POS", "Bank Transfer", "Cash", "Gold Card Credit"])

        if st.button(f"AUTHORIZE {mode} TRANSACTION", use_container_width=True):
            if staff_assigned == "NO FREE STAFF" and mode == "CAR WASH":
                st.error("Cannot authorize. No available staff in the Wet Bay.")
            elif (plate or mode == "LOUNGE") and (selected if mode=="CAR WASH" else lounge_items_sold):
                can_proceed = True
                low_bal = False
                final_sales_total = total_price
                
                with conn.session as s:
                    if pay_method == "Gold Card Credit":
                        m_res = s.execute(text("SELECT balance_washes FROM memberships WHERE plate=:p"), {"p": plate}).fetchone()
                        if m_res and m_res[0] > 0:
                            new_bal = m_res[0] - 1
                            s.execute(text("UPDATE memberships SET balance_washes=:b WHERE plate=:p"), {"b": new_bal, "p": plate})
                            final_sales_total = 0.0
                            if new_bal <= 1: low_bal = True
                        else:
                            st.error("No active card or zero balance for this plate."); can_proceed = False

                    if can_proceed:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M")
                        ins_sale = s.execute(text("""INSERT INTO sales (plate, services, total, method, staff, timestamp, type) 
                                                VALUES (:p, :s, :t, :m, :st, :ts, :tp) RETURNING id"""), 
                                            {"p": plate, "s": item_summary, "t": final_sales_total, "m": pay_method, "st": staff_assigned, "ts": now, "tp": mode})
                        last_id = ins_sale.fetchone()[0]
                        
                        s.execute(text("""INSERT INTO customers (plate, name, phone, visits, last_visit) 
                                       VALUES (:p, :n, :ph, 1, :lv) 
                                       ON CONFLICT (plate) DO UPDATE SET visits = customers.visits + 1, last_visit = EXCLUDED.last_visit"""),
                                  {"p": plate, "n": name, "ph": full_phone, "lv": now.split()[0]})
                        
                        if mode == "CAR WASH":
                            s.execute(text("""INSERT INTO live_bays (plate, status, entry_time, staff, vehicle_type, service_detail, wet_staff_history) 
                                           VALUES (:p, 'WET BAY', :ts, :st, :vt, :sd, NULL) ON CONFLICT (plate) DO NOTHING"""),
                                      {"p": plate, "ts": now, "st": staff_assigned, "vt": v_type, "sd": item_summary})
                        else:
                            for item, qty in lounge_items_sold:
                                s.execute(text("UPDATE inventory SET stock = stock - :q WHERE item = :i"), {"q": qty, "i": item})
                        
                        s.commit()
                        st.session_state['last_receipt'] = {
                            "id": last_id, "mode": mode, "name": name, "plate": plate, "phone": full_phone,
                            "items": item_summary, "total": final_sales_total, "staff": staff_assigned, "date": now, "low_bal": low_bal
                        }
                        add_event(f"{mode} AUTH: {plate if plate else 'Lounge'} via {pay_method}")
                        st.rerun()

    with tab_mem:
        st.subheader("ACTIVATE MEMBERSHIP CARD")
        m_plate = st.text_input("SCAN/ENTER PLATE FOR CARD").upper()
        tier = st.selectbox("CARD TIER", ["Silver (5 Washes)", "Gold (10 Washes)", "Platinum (25 Washes)"])
        card_sale_price = st.number_input("CARD SALE PRICE (₦)", min_value=0.0)
        qty = 5 if "Silver" in tier else 10 if "Gold" in tier else 25
        
        if st.button("ISSUE CARD"):
            if m_plate:
                with conn.session as s:
                    s.execute(text("INSERT INTO memberships (plate, balance_washes, card_type, sale_price) VALUES (:p, :b, :t, :s) ON CONFLICT (plate) DO UPDATE SET balance_washes=EXCLUDED.balance_washes"),
                              {"p": m_plate, "b": qty, "t": tier, "s": card_sale_price})
                    
                    receptionist = st.session_state.user_name
                    p_res = s.execute(text("SELECT bonus_pc FROM staff_payroll_config WHERE username=:u"), {"u": receptionist}).fetchone()
                    if p_res and p_res[0] > 0:
                        comm_amt = card_sale_price * (p_res[0] / 100)
                        s.execute(text("INSERT INTO earnings_log (username, amount, ref_plate, timestamp) VALUES (:u, :a, :r, :t)"),
                                  {"u": receptionist, "a": comm_amt, "r": f"NEW_CARD:{m_plate}", "t": datetime.now().strftime("%Y-%m-%d %H:%M")})
                    s.commit()
                add_event(f"CARD ISSUED: {tier} to {m_plate}")
                st.success(f"Activated {tier} for {m_plate}!")

    if 'last_receipt' in st.session_state:
        r = st.session_state['last_receipt']
        st.markdown(f"""
        <div style="background: white; color: black; padding: 40px; max-width: 500px; margin: 20px auto; border: 1px solid #ddd; border-top: 10px solid black;">
            <div style="text-align: center; border-bottom: 2px solid black; padding-bottom: 20px; margin-bottom: 20px;">
                <h2 style="color: black !important; margin: 0; letter-spacing: 5px;">RIDEBOSS</h2>
                <p style="color: #666 !important; font-size: 12px; margin: 0;">OFFICIAL TRANSACTION SUMMARY</p>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;"><b>REF:</b> <span>#RB-{r['id']}</span></div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 30px;"><b>VEHICLE:</b> <span style="background: black; color: white; padding: 2px 8px;">{r['plate']}</span></div>
            <div style="border: 1px solid black; padding: 15px; margin-bottom: 30px;"><div style="font-size: 18px;">{r['items']}</div></div>
            <div style="display: flex; justify-content: space-between; border-top: 2px solid black; padding-top: 15px;"><b>AMOUNT PAID</b><span style="font-size: 22px; font-weight: 900;">₦{r['total']:,}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            receipt_payload = { "id": r["id"], "date": r["date"], "plate": r["plate"], "items": r["items"], "total": r["total"] }
            receipt_url = f"?print_receipt={urllib.parse.quote(json.dumps(receipt_payload))}"
            st.markdown(f'<a href="{receipt_url}" target="_blank" style="text-decoration:none;"><button style="width:100%; height:3.5em; border:2px solid black; background:black; color:white; font-weight:bold; cursor:pointer; text-transform:uppercase; letter-spacing:2px;">🖨️ PRINT RECEIPT</button></a>', unsafe_allow_html=True)
        with c_p2:
            if st.button("CLOSE & DISMISS"):
                del st.session_state['last_receipt']
                st.rerun()

# --- 2. LIVE U-FLOW (STICKY WHATSAPP & COMMISSION) ---
elif choice == "LIVE U-FLOW":
    if 'wa_pending' not in st.session_state: st.session_state.wa_pending = None

    view_mode = st.radio("VIEW MODE", ["Management controls", "External Flight Board"], horizontal=True)
    live_cars = conn.query("SELECT * FROM live_bays", ttl=0)
    
    if view_mode == "External Flight Board":
        st.markdown("<h1 style='text-align:center; color:#00d4ff;'>WORKFLOW MONITOR</h1>", unsafe_allow_html=True)
        if live_cars.empty:
            st.info("ALL BAYS CLEAR.")
        else:
            monitor_html = """<style>
                body { background-color: #050505; margin: 0; padding: 0; font-family: sans-serif; overflow: hidden; }
                .monitor-container { background: #000; height: 100vh; width: 100%; position: relative; overflow: hidden; }
                .scroll-content { position: absolute; width: 100%; animation: scrollUp 30s linear infinite; }
                @keyframes scrollUp { 0% { transform: translateY(100%); } 100% { transform: translateY(-100%); } }
                .monitor-row { display: flex; justify-content: space-between; align-items: center; padding: 30px; border-bottom: 2px solid #222; background: #050505; color: white; }
                .monitor-plate { font-size: 50px; font-weight: 900; color: #00d4ff; font-family: 'Courier New', monospace; line-height: 1; }
                .monitor-svc { color: #00d4ff; font-style: italic; font-size: 22px; }
            </style><div class="monitor-container"><div class="scroll-content">"""
            scroll_data = pd.concat([live_cars, live_cars])
            for _, row in scroll_data.iterrows():
                monitor_html += f"""<div class="monitor-row">
                    <div class="monitor-plate">{row['plate']}<br><span style="font-size:18px; color:#555;">{row['vehicle_type']}</span></div>
                    <div style="flex:1; padding-left:40px;"><div class="monitor-svc">SERVICE: {row['service_detail']}</div></div>
                    <div style="text-align: right;"><div style="color:#FFD700; font-weight:bold;">{row['status']}</div><div style="color:#888;">{row['staff']}</div></div>
                </div>"""
            monitor_html += "</div></div>"
            import streamlit.components.v1 as components
            components.html(monitor_html, height=800)
    else:
        if st.session_state.wa_pending:
            st.markdown(f"""<div style="background-color:#050505; border:2px solid #25D366; padding:20px; border-radius:10px; margin-bottom:20px; text-align:center;">
                    <h3 style="color:#25D366; margin:0;">Vehicle Released: {st.session_state.wa_pending['plate']}</h3>
                    <a href="{st.session_state.wa_pending['url']}" target="_blank" style="text-decoration:none;"><button style="background-color:#25D366; color:white; padding:15px 40px; border:none; border-radius:8px; font-weight:bold; cursor:pointer; width:100%; font-size:16px;">📲 SEND WHATSAPP MESSAGE</button></a>
                </div>""", unsafe_allow_html=True)
            if st.button("❌ DISMISS NOTIFICATION", use_container_width=True):
                st.session_state.wa_pending = None; st.rerun()
            st.divider()

        for idx, row in live_cars.iterrows():
            entry_dt = datetime.strptime(row['entry_time'], "%Y-%m-%d %H:%M")
            time_spent = (datetime.now() - entry_dt).seconds // 60
            border_color = "#00d4ff" if time_spent < 40 else "#FF3B30"
            st.markdown(f'<div class="status-card" style="border-left: 10px solid {border_color};">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"### {row['plate']} ({row['vehicle_type']})")
                st.write(f"**ZONE:** {row['status']}")
            with c2:
                st.write(f"**DETAILER:** {row['staff']}")
                st.write(f"**ELAPSED:** {time_spent} mins")
            with c3:
                if row['status'] == "WET BAY":
                    with st.popover("TO DRY BAY"):
                        dry_staff = get_free_staff_by_dept("DRY BAY")
                        new_dry = st.selectbox("Assign Dry Bay", dry_staff if dry_staff else ["NO FREE STAFF"], key=f"dry_{idx}")
                        if st.button("Confirm Handover", key=f"hnd_{idx}"):
                            if new_dry != "NO FREE STAFF":
                                with conn.session as s:
                                    s.execute(text("UPDATE live_bays SET status='DRY BAY', staff=:st, wet_staff_history=:wh WHERE plate=:p"), 
                                              {"st": new_dry, "wh": row['staff'], "p": row['plate']}); s.commit()
                                add_event(f"{row['plate']} moved to Dry Bay"); st.rerun()
                
                if st.button(f"RELEASE {row['plate']}", key=f"rel_{idx}"):
                    with conn.session as s:
                        sale_res = s.execute(text("SELECT total FROM sales WHERE plate=:p ORDER BY id DESC LIMIT 1"), {"p": row['plate']}).fetchone()
                        if sale_res:
                            sale_total = sale_res[0]
                            staff_to_pay = [s_m for s_m in [row['staff'], row['wet_staff_history']] if s_m]
                            for s_member in staff_to_pay:
                                p_res = s.execute(text("SELECT bonus_pc FROM staff_payroll_config WHERE username=:u"), {"u": s_member}).fetchone()
                                if p_res and p_res[0] > 0:
                                    comm_amt = sale_total * (p_res[0] / 100)
                                    s.execute(text("INSERT INTO earnings_log (username, amount, ref_plate, timestamp) VALUES (:u, :a, :r, :t)"),
                                              {"u": s_member, "a": comm_amt, "r": row['plate'], "t": datetime.now().strftime("%Y-%m-%d %H:%M")})
                        
                        cust_info = s.execute(text("SELECT name, phone FROM customers WHERE plate=:p"), {"p": row['plate']}).fetchone()
                        if cust_info:
                            wa_msg = f"Hi {cust_info[0]}, your vehicle ({row['plate']}) is ready for pickup! Thank you for choosing RideBoss Autos."
                            st.session_state.wa_pending = {"url": format_whatsapp(cust_info[1], wa_msg), "plate": row['plate']}
                        
                        s.execute(text("DELETE FROM live_bays WHERE plate=:p"), {"p": row['plate']}); s.commit()
                    add_event(f"{row['plate']} Released."); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- 3. ONBOARD STAFF (MANAGER) ---
elif choice == "ONBOARD STAFF" and st.session_state.user_role == "MANAGER":
    st.subheader("STAFF ONBOARDING")
    with st.form("new_staff"):
        s_name = st.text_input("Full Name")
        s_pass = st.text_input("Login Password", type="password")
        s_role = st.selectbox("System Role", ["STAFF", "MANAGER"])
        s_dept = st.selectbox("Department", ["WET BAY", "DRY BAY", "RECEPTIONIST", "MANAGEMENT"])
        if st.form_submit_button("ONBOARD STAFF"):
            if s_name and s_pass:
                with conn.session as s:
                    s.execute(text("INSERT INTO users (username, password, role, dept, status, verified) VALUES (:u,:p,:r,:d,'ACTIVE',0) ON CONFLICT (username) DO NOTHING"),
                              {"u": s_name, "p": s_pass, "r": s_role, "d": s_dept}); s.commit()
                st.success(f"{s_name} added."); st.rerun()
    st.write("---")
    current_staff_df = conn.query("SELECT username, dept, role, status, verified FROM users", ttl=0)
    st.dataframe(current_staff_df, use_container_width=True)
    target_staff = st.selectbox("Select Staff Member", ["None"] + current_staff_df['username'].tolist())
    if st.button("DEACTIVATE STAFF") and target_staff != "None":
        with conn.session as s:
            s.execute(text("UPDATE users SET status='INACTIVE' WHERE username=:u"), {"u": target_staff}); s.commit()
        st.rerun()

# --- 4. BOSS HR PORTAL ---
elif choice == "BOSS HR" and st.session_state.user_role == "MANAGER":
    hr_t1, hr_t2, hr_t3 = st.tabs(["PENDING APPROVALS", "ACTIVE STAFF DOSSIERS", "SALARY CONFIG"])
    with hr_t1:
        pending_staff = conn.query("SELECT * FROM staff_profiles WHERE username IN (SELECT username FROM users WHERE verified=0)", ttl=0)
        if pending_staff.empty:
            st.info("No pending verifications.")
        else:
            for idx, row in pending_staff.iterrows():
                with st.expander(f"REVIEW: {row['username']}"):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if row['id_image']:
                            st.image(Image.open(io.BytesIO(row['id_image'])))
                    with c2:
                        st.write(f"**NIN:** {row['nin']}"); st.write(f"**Bank:** {row['bank_name']} - {row['account_no']}")
                        if st.button("APPROVE", key=f"app_{idx}"):
                            with conn.session as s:
                                s.execute(text("UPDATE users SET verified=1 WHERE username=:u"), {"u": row['username']})
                                s.execute(text("INSERT INTO staff_payroll_config (username, base_salary, bonus_pc) VALUES (:u, 0, 0) ON CONFLICT DO NOTHING"), {"u": row['username']}); s.commit()
                            st.success("Approved!"); st.rerun()

    with hr_t2:
        active_staff = conn.query("SELECT username FROM users WHERE verified=1 AND role='STAFF'", ttl=0)
        selected_staff = st.selectbox("SELECT STAFF", active_staff['username'].tolist() if not active_staff.empty else [])
        if selected_staff:
            s_prof = conn.query("SELECT * FROM staff_profiles WHERE username=:u", params={"u": selected_staff}, ttl=0)
            if not s_prof.empty:
                r = s_prof.iloc[0]
                base, d_com, m_com, y_com, total_m = calculate_payouts(selected_staff)
                st.markdown(f"### {r['full_name']}")
                st.info(f"💰 BASE SALARY: ₦{base:,}")
                m1, m2, m3 = st.columns(3)
                m1.metric("Daily Bonus", f"₦{d_com:,}"); m2.metric("Monthly Bonus", f"₦{m_com:,}"); m3.metric("Yearly Bonus", f"₦{y_com:,}")

    with hr_t3:
        all_staff_list = conn.query("SELECT username FROM users WHERE role='STAFF'", ttl=0)['username'].tolist()
        config_staff = st.selectbox("Staff to Config", all_staff_list)
        if config_staff:
            curr = conn.query("SELECT base_salary, bonus_pc FROM staff_payroll_config WHERE username=:u", params={"u": config_staff}, ttl=0)
            with st.form("sal_conf"):
                new_base = st.number_input("Base Salary", value=float(curr.iloc[0]['base_salary']) if not curr.empty else 0.0)
                new_bon = st.number_input("Commission %", value=float(curr.iloc[0]['bonus_pc']) if not curr.empty else 0.0)
                if st.form_submit_button("UPDATE"):
                    with conn.session as s:
                        s.execute(text("INSERT INTO staff_payroll_config (username, base_salary, bonus_pc) VALUES (:u, :b, :p) ON CONFLICT (username) DO UPDATE SET base_salary=EXCLUDED.base_salary, bonus_pc=EXCLUDED.bonus_pc"),
                                  {"u": config_staff, "b": new_base, "p": new_bon}); s.commit()
                    st.success("Updated!"); st.rerun()

# --- 5. INVENTORY & STAFF (MANAGER) ---
elif choice == "INVENTORY & STAFF" and st.session_state.user_role == "MANAGER":
    t1, t2, t3 = st.tabs(["Lounge Inventory", "Wash Price List", "Staff Performance"])
    with t1:
        with st.form("new_item"):
            ni_name = st.text_input("Item Name"); ni_stock = st.number_input("Stock"); ni_unit = st.text_input("Unit"); ni_price = st.number_input("Price")
            if st.form_submit_button("ADD/UPDATE"):
                with conn.session as s:
                    s.execute(text("INSERT INTO inventory (item, stock, unit, price) VALUES (:i,:s,:u,:p) ON CONFLICT (item) DO UPDATE SET stock=EXCLUDED.stock, price=EXCLUDED.price"),
                              {"i": ni_name, "s": ni_stock, "u": ni_unit, "p": ni_price}); s.commit(); st.rerun()
        st.dataframe(conn.query("SELECT * FROM inventory", ttl=0), use_container_width=True)
    with t2:
        svc_to_edit = st.selectbox("Select Service", ["-- ADD NEW --"] + list(SERVICES.keys()))
        with st.form("svc_form"):
            new_name = st.text_input("Name", value="" if svc_to_edit == "-- ADD NEW --" else svc_to_edit)
            new_price = st.number_input("Price", value=0.0 if svc_to_edit == "-- ADD NEW --" else SERVICES[svc_to_edit])
            if st.form_submit_button("SAVE"):
                with conn.session as s:
                    if svc_to_edit != "-- ADD NEW --" and new_name != svc_to_edit:
                        s.execute(text("DELETE FROM wash_prices WHERE service=:o"), {"o": svc_to_edit})
                    s.execute(text("INSERT INTO wash_prices (service, price) VALUES (:n,:p) ON CONFLICT (service) DO UPDATE SET price=EXCLUDED.price"), {"n": new_name, "p": new_price}); s.commit(); st.rerun()
    with t3:
        perf_df = conn.query("SELECT staff, COUNT(*) as washes, SUM(total) as revenue FROM sales WHERE type='CAR WASH' GROUP BY staff", ttl=0)
        st.bar_chart(perf_df.set_index('staff')['washes'])

# --- 6. FINANCIALS (REPORTING) ---
elif choice == "FINANCIALS" and st.session_state.user_role == "MANAGER":
    tab_fin, tab_cards_hub = st.tabs(["REVENUE", "MEMBERSHIP HUB"])
    with tab_fin:
        view_scope = st.radio("SCOPE", ["DAILY", "MONTHLY", "YEARLY"], horizontal=True)
        sales_raw = conn.query("SELECT * FROM sales", ttl=0)
        exp_raw = conn.query("SELECT * FROM expenses", ttl=0)
        m_sales_raw = conn.query("SELECT plate, card_type, sale_price FROM memberships", ttl=0)
        sales_raw['timestamp'] = pd.to_datetime(sales_raw['timestamp'])
        exp_raw['timestamp'] = pd.to_datetime(exp_raw['timestamp'])
        now = datetime.now()
        
        if view_scope == "DAILY":
            f_sales = sales_raw[sales_raw['timestamp'].dt.date == now.date()]; f_exps = exp_raw[exp_raw['timestamp'].dt.date == now.date()]
        elif view_scope == "MONTHLY":
            f_sales = sales_raw[(sales_raw['timestamp'].dt.month == now.month)]; f_exps = exp_raw[(exp_raw['timestamp'].dt.month == now.month)]
        else:
            f_sales = sales_raw[sales_raw['timestamp'].dt.year == now.year]; f_exps = exp_raw[exp_raw['timestamp'].dt.year == now.year]

        rev_wash = f_sales[f_sales['type'] == 'CAR WASH']['total'].sum()
        rev_lounge = f_sales[f_sales['type'] == 'LOUNGE']['total'].sum()
        card_total = m_sales_raw['sale_price'].sum() if view_scope != "DAILY" else 0 
        total_exp = f_exps['amount'].sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("WASH", f"₦{rev_wash:,}"); m2.metric("LOUNGE", f"₦{rev_lounge:,}"); m3.metric("CARDS", f"₦{card_total:,}"); m4.metric("EXPENSES", f"₦{total_exp:,}")
        with st.expander("LOG EXPENSE"):
            e_desc = st.text_input("Desc"); e_amt = st.number_input("Amt")
            if st.button("LOG"):
                with conn.session as s:
                    s.execute(text("INSERT INTO expenses (description, amount, timestamp) VALUES (:d,:a,:t)"), {"d": e_desc, "a": e_amt, "t": datetime.now().strftime("%Y-%m-%d")}); s.commit(); st.rerun()

    with tab_cards_hub:
        m_df = conn.query("SELECT * FROM memberships", ttl=0)
        for idx, row in m_df.iterrows():
            c1, c2, c3, c4 = st.columns([2,1,1,1])
            c1.write(f"**{row['plate']}**"); c2.write(f"Bal: {row['balance_washes']}")
            if c3.button("TOP UP", key=f"up_{idx}"):
                with conn.session as s:
                    s.execute(text("UPDATE memberships SET balance_washes=10 WHERE plate=:p"), {"p": row['plate']})
                    receptionist = st.session_state.user_name
                    p_res = s.execute(text("SELECT bonus_pc FROM staff_payroll_config WHERE username=:u"), {"u": receptionist}).fetchone()
                    if p_res and p_res[0] > 0:
                        s.execute(text("INSERT INTO earnings_log (username, amount, ref_plate, timestamp) VALUES (:u, :a, :r, :t)"),
                                  {"u": receptionist, "a": row['sale_price'] * (p_res[0] / 100), "r": f"REFILL:{row['plate']}", "t": datetime.now().strftime("%Y-%m-%d %H:%M")})
                    s.commit(); st.rerun()
            if c4.button("DELETE", key=f"del_{idx}"):
                with conn.session as s: s.execute(text("DELETE FROM memberships WHERE plate=:p"), {"p": row['plate']}); s.commit(); st.rerun()

# --- CRM & NOTIFICATIONS ---
elif choice == "CRM & RETENTION" and st.session_state.user_role == "MANAGER":
    cust_df = conn.query("SELECT * FROM customers", ttl=0)
    for _, row in cust_df.iterrows():
        days = (datetime.now() - datetime.strptime(row['last_visit'], "%Y-%m-%d")).days
        st.markdown(f"<p style='color:{'#00d4ff' if days < 14 else '#FF3B30'};'><b>{row['name']}</b> ({row['plate']}) - {days} days</p>", unsafe_allow_html=True)

elif choice == "NOTIFICATIONS":
    notes = conn.query("SELECT timestamp as 'TIME', message as 'EVENT' FROM notifications ORDER BY id DESC", ttl=0)
    st.table(notes)

elif choice == "MY EARNINGS":
    st.subheader(f"EARNINGS: {st.session_state.user_name}")
    base, d_com, m_com, y_com, total_m = calculate_payouts(st.session_state.user_name)
    c1, c2, c3 = st.columns(3)
    c1.metric("TODAY", f"₦{d_com:,}"); c2.metric("MONTH", f"₦{m_com:,}"); c3.metric("EST. PAYOUT", f"₦{total_m:,}")
    e_log = conn.query("SELECT timestamp, ref_plate, amount FROM earnings_log WHERE username=:u ORDER BY id DESC LIMIT 20", params={"u": st.session_state.user_name}, ttl=0)
    st.table(e_log)
