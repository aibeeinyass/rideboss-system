import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import urllib.parse
import time
import json
import io 
from PIL import Image

# --- DATABASE SETUP ---
conn = sqlite3.connect('rideboss_ultra.db', check_same_thread=False)
c = conn.cursor()

# --- EXISTING TABLES (UNTOUCHED LOGIC) ---
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (username TEXT PRIMARY KEY, password TEXT, role TEXT, dept TEXT, status TEXT DEFAULT 'ACTIVE', verified INTEGER DEFAULT 0)''')
c.execute('''CREATE TABLE IF NOT EXISTS customers 
             (plate TEXT PRIMARY KEY, name TEXT, phone TEXT, visits INTEGER, last_visit TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS sales 
             (id INTEGER PRIMARY KEY, plate TEXT, services TEXT, total REAL, method TEXT, staff TEXT, timestamp TEXT, type TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notifications 
             (id INTEGER PRIMARY KEY, message TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS live_bays 
             (plate TEXT PRIMARY KEY, status TEXT, entry_time TEXT, staff TEXT, vehicle_type TEXT, service_detail TEXT, wet_staff_history TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS inventory (item TEXT PRIMARY KEY, stock REAL, unit TEXT, price REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS wash_prices (service TEXT PRIMARY KEY, price REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, description TEXT, amount REAL, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS memberships 
             (plate TEXT PRIMARY KEY, balance_washes INTEGER, card_type TEXT, sale_price REAL DEFAULT 0.0)''')

# --- NEW FEATURES TABLES ---
c.execute('''CREATE TABLE IF NOT EXISTS staff_profiles 
             (username TEXT PRIMARY KEY, full_name TEXT, phone TEXT, address TEXT, nin TEXT, bank_name TEXT, account_no TEXT, id_type TEXT, id_image BLOB)''')
c.execute('''CREATE TABLE IF NOT EXISTS staff_payroll_config 
             (username TEXT PRIMARY KEY, base_salary REAL DEFAULT 0.0, bonus_pc REAL DEFAULT 0.0)''')
c.execute('''CREATE TABLE IF NOT EXISTS earnings_log 
             (id INTEGER PRIMARY KEY, username TEXT, amount REAL, ref_plate TEXT, timestamp TEXT)''')

# --- DB MIGRATION FOR OLD VERSIONS (Ensures wet_staff_history exists) ---
try:
    c.execute("ALTER TABLE live_bays ADD COLUMN wet_staff_history TEXT")
except:
    pass # Column likely exists

# Seed Admin and Initial Data
c.execute("INSERT OR IGNORE INTO users VALUES ('admin', '0000', 'MANAGER', 'MANAGEMENT', 'ACTIVE', 1)")
c.execute("INSERT OR IGNORE INTO inventory VALUES ('Car Shampoo', 10.0, 'Gallons', 0), ('Coke', 50.0, 'Cans', 500), ('Water', 100.0, 'Bottles', 200)")
c.execute("SELECT COUNT(*) FROM wash_prices")
if c.fetchone()[0] == 0:
    initial_services = [("Standard Wash", 5000), ("Executive Detail", 15000), ("Engine Steam", 10000), ("Ceramic Wax", 25000), ("Interior Deep Clean", 12000)]
    c.executemany("INSERT INTO wash_prices VALUES (?,?)", initial_services)
conn.commit()

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
    
    /* MONITOR SCROLLING */
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
    c.execute("INSERT INTO notifications (message, timestamp) VALUES (?,?)", (f"{now} | {msg}", now))
    conn.commit()

def format_whatsapp(phone, message):
    return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"

def get_free_staff_by_dept(dept_name):
    busy_list = pd.read_sql_query("SELECT staff FROM live_bays", conn)['staff'].tolist()
    # NEW FEATURE: Only Verified Staff
    all_dept = pd.read_sql_query(f"SELECT username FROM users WHERE dept='{dept_name}' AND status='ACTIVE' AND verified=1", conn)['username'].tolist()
    return [s for s in all_dept if s not in busy_list]

def calculate_payouts(username):
    # Fetch base salary
    c.execute("SELECT base_salary FROM staff_payroll_config WHERE username=?", (username,))
    res = c.fetchone()
    base = res[0] if res else 0.0
    
    # Fetch commissions
    df_comm = pd.read_sql_query(f"SELECT * FROM earnings_log WHERE username='{username}'", conn)
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
            c.execute("SELECT role, dept FROM users WHERE username=? AND password=?", (u, p))
            result = c.fetchone()
            if result:
                st.session_state.logged_in = True
                st.session_state.user_role = result[0]
                st.session_state.user_dept = result[1]
                st.session_state.user_name = u
                st.rerun()
            else:
                st.error("Invalid Username or Password")
    st.stop()

# --- NEW FEATURE 1: STAFF INDUCTION GATE ---
c.execute("SELECT verified FROM users WHERE username=?", (st.session_state.user_name,))
is_verified = c.fetchone()[0]

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
                # Process Image
                img_bytes = id_file.getvalue()
                c.execute("INSERT OR REPLACE INTO staff_profiles VALUES (?,?,?,?,?,?,?,?,?)", 
                          (st.session_state.user_name, fn, ph, addr, nin, bn, acc, id_type, img_bytes))
                conn.commit()
                st.success("Details submitted! Awaiting Manager Approval.")
                st.info("Log out and wait for your manager to verify your account.")
            else:
                st.error("Please fill all fields and upload ID.")
    
    if st.button("LOGOUT"):
        st.session_state.logged_in = False
        st.rerun()
    st.stop()

# --- LOAD CONFIG ---
wash_prices_df = pd.read_sql_query("SELECT * FROM wash_prices", conn)
SERVICES = dict(zip(wash_prices_df['service'], wash_prices_df['price']))
COUNTRY_CODES = {"Nigeria": "+234", "Ghana": "+233", "UK": "+44", "USA": "+1", "UAE": "+971"}

# --- SIDEBAR NAVIGATION (RESTORED ONBOARD STAFF) ---
st.sidebar.markdown(f"USER: **{st.session_state.user_name}**")
st.sidebar.caption(f"DEPT: {st.session_state.user_dept}")

# Define Menus based on Role/Dept
if st.session_state.user_role == "MANAGER":
    # Added "ONBOARD STAFF" back to the Manager's list
    menu = ["COMMAND CENTER", "LIVE U-FLOW", "ONBOARD STAFF", "BOSS HR", "FINANCIALS", "INVENTORY & STAFF", "CRM & RETENTION", "NOTIFICATIONS"]
elif st.session_state.user_dept == "RECEPTIONIST":
    menu = ["COMMAND CENTER", "LIVE U-FLOW", "MY EARNINGS", "NOTIFICATIONS"]
else:
    # Wet/Dry Bay Staff only see this
    menu = ["LIVE U-FLOW", "MY EARNINGS", "NOTIFICATIONS"]

choice = st.sidebar.radio("NAVIGATE", menu)
if st.sidebar.button("LOGOUT"):
    st.session_state.logged_in = False
    st.rerun()

# --- TOP NOTIFICATION FEED ---
latest_note = pd.read_sql_query("SELECT message FROM notifications ORDER BY id DESC LIMIT 1", conn)
st.markdown(f'<div class="notification-bar">SYSTEM LOG: {latest_note["message"].iloc[0] if not latest_note.empty else "READY"}</div>', unsafe_allow_html=True)

# --- 1. COMMAND CENTER (RESTRICTED) ---
if choice == "COMMAND CENTER":
    tab_trans, tab_mem = st.tabs(["NEW TRANSACTION", "REGISTER MEMBERSHIP"])
    
    with tab_trans:
        mode = st.radio("SELECT MODE", ["CAR WASH", "LOUNGE"], horizontal=True)
        st.markdown("---")
        
        cust_data = pd.read_sql_query("SELECT * FROM customers", conn)
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
                
                # Smart Filtering (Verified only)
                wet_staff = get_free_staff_by_dept("WET BAY")
                staff_assigned = st.selectbox("ASSIGN WET BAY DETAILER", wet_staff if wet_staff else ["NO FREE STAFF"])
                item_summary = ", ".join(selected)
            else:
                inv_items = pd.read_sql_query("SELECT item, price FROM inventory WHERE price > 0", conn)
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
                
                if pay_method == "Gold Card Credit":
                    c.execute("SELECT balance_washes FROM memberships WHERE plate=?", (plate,))
                    m_res = c.fetchone()
                    if m_res and m_res[0] > 0:
                        new_bal = m_res[0] - 1
                        c.execute("UPDATE memberships SET balance_washes=? WHERE plate=?", (new_bal, plate))
                        final_sales_total = 0.0
                        if new_bal <= 1: low_bal = True
                    else:
                        st.error("No active card or zero balance for this plate.")
                        can_proceed = False

                if can_proceed:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    c.execute("INSERT INTO sales (plate, services, total, method, staff, timestamp, type) VALUES (?,?,?,?,?,?,?)", 
                              (plate, item_summary, final_sales_total, pay_method, staff_assigned, now, mode))
                    c.execute("INSERT OR REPLACE INTO customers (plate, name, phone, visits, last_visit) VALUES (?, ?, ?, COALESCE((SELECT visits FROM customers WHERE plate=?), 0) + 1, ?)", (plate, name, full_phone, plate, now.split()[0]))
                    
                    if mode == "CAR WASH":
                        # NEW: Init wet_staff_history as None
                        c.execute("INSERT OR REPLACE INTO live_bays (plate, status, entry_time, staff, vehicle_type, service_detail, wet_staff_history) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                                  (plate, "WET BAY", now, staff_assigned, v_type, item_summary, None))
                    else:
                        for item, qty in lounge_items_sold:
                            c.execute("UPDATE inventory SET stock = stock - ? WHERE item = ?", (qty, item))
                    
                    conn.commit()
                    st.session_state['last_receipt'] = {
                        "id": c.lastrowid, "mode": mode, "name": name, "plate": plate, "phone": full_phone,
                        "items": item_summary, "total": final_sales_total, 
                        "staff": staff_assigned, "date": now, "low_bal": low_bal
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
                c.execute("INSERT OR REPLACE INTO memberships (plate, balance_washes, card_type, sale_price) VALUES (?, ?, ?, ?)", (m_plate, qty, tier, card_sale_price))
                
                # --- COMMISSION LOGIC FOR RECEPTIONIST ---
                receptionist = st.session_state.user_name
                c.execute("SELECT bonus_pc FROM staff_payroll_config WHERE username=?", (receptionist,))
                p_res = c.fetchone()
                if p_res and p_res[0] > 0:
                    comm_amt = card_sale_price * (p_res[0] / 100)
                    c.execute("INSERT INTO earnings_log (username, amount, ref_plate, timestamp) VALUES (?,?,?,?)",
                              (receptionist, comm_amt, f"NEW_CARD:{m_plate}", datetime.now().strftime("%Y-%m-%d %H:%M")))
                
                conn.commit()
                add_event(f"CARD ISSUED: {tier} to {m_plate}")
                st.success(f"Activated {tier} for {m_plate}!")
            else:
                st.error("Plate number required.")

    if 'last_receipt' in st.session_state:
        r = st.session_state['last_receipt']
        st.markdown(f"""
        <div style="background: white; color: black; padding: 40px; max-width: 500px; margin: 20px auto; border: 1px solid #ddd; border-top: 10px solid black;">
            <div style="text-align: center; border-bottom: 2px solid black; padding-bottom: 20px; margin-bottom: 20px;">
                <h2 style="color: black !important; margin: 0; letter-spacing: 5px;">RIDEBOSS</h2>
                <p style="color: #666 !important; font-size: 12px; margin: 0;">OFFICIAL TRANSACTION SUMMARY</p>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="font-weight: bold;">REFERENCE:</span> <span>#RB-{r['id']}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="font-weight: bold;">DATE:</span> <span>{r['date']}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 30px;">
                <span style="font-weight: bold;">VEHICLE:</span> <span style="background: black; color: white; padding: 2px 8px;">{r['plate']}</span>
            </div>
            
            <div style="border: 1px solid black; padding: 15px; margin-bottom: 30px;">
                <small style="color: #888; font-weight: bold;">DESCRIPTION</small><br>
                <div style="font-size: 18px; margin-top: 5px;">{r['items']}</div>
            </div>

            <div style="display: flex; justify-content: space-between; border-top: 2px solid black; padding-top: 15px;">
                <span style="font-size: 18px; font-weight: bold;">AMOUNT PAID</span>
                <span style="font-size: 22px; font-weight: 900;">₦{r['total']:,}</span>
            </div>
            <p style="text-align: center; margin-top: 40px; font-size: 10px; color: #999; letter-spacing: 2px;">AUTHENTIC RIDEBOSS DOCUMENT</p>
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

# --- 2. LIVE U-FLOW (ENHANCED FOR COMMISSION) ---
elif choice == "LIVE U-FLOW":
    view_mode = st.radio("VIEW MODE", ["Management controls", "External Flight Board"], horizontal=True)
    live_cars = pd.read_sql_query("SELECT * FROM live_bays", conn)
    
    if view_mode == "External Flight Board":
        st.markdown("<h1 style='text-align:center; color:#00d4ff;'>WORKFLOW MONITOR</h1>", unsafe_allow_html=True)
        if live_cars.empty:
            st.info("ALL BAYS CLEAR.")
        else:
            monitor_html = """
            <style>
                body { background-color: #050505; margin: 0; padding: 0; font-family: sans-serif; overflow: hidden; }
                .monitor-container { background: #000; height: 100vh; width: 100%; position: relative; overflow: hidden; }
                .scroll-content { position: absolute; width: 100%; animation: scrollUp 30s linear infinite; }
                @keyframes scrollUp { 0% { transform: translateY(100%); } 100% { transform: translateY(-100%); } }
                .monitor-row { display: flex; justify-content: space-between; align-items: center; padding: 30px; border-bottom: 2px solid #222; background: #050505; color: white; }
                .monitor-plate { font-size: 50px; font-weight: 900; color: #00d4ff; font-family: 'Courier New', monospace; line-height: 1; }
                .monitor-status { font-size: 18px; color: #FFD700; font-weight: bold; text-transform: uppercase; }
                .monitor-meta { text-align: right; }
                .monitor-staff { font-size: 20px; color: #888; text-transform: uppercase; }
                .monitor-svc { color: #00d4ff; font-style: italic; font-size: 22px; }
            </style>
            <div class="monitor-container"><div class="scroll-content">"""
            
            scroll_data = pd.concat([live_cars, live_cars])
            
            for _, row in scroll_data.iterrows():
                monitor_html += f"""
                <div class="monitor-row">
                    <div class="monitor-plate">{row['plate']}<br><span style="font-size:18px; color:#555;">{row['vehicle_type']}</span></div>
                    <div style="flex:1; padding-left:40px;"><div class="monitor-svc">SERVICE: {row['service_detail']}</div></div>
                    <div class="monitor-meta">
                        <div class="monitor-status">{row['status']}</div>
                        <div class="monitor-staff">ASSIGNED: {row['staff']}</div>
                    </div>
                </div>"""
            
            monitor_html += "</div></div>"
            import streamlit.components.v1 as components
            components.html(monitor_html, height=800)

    else:
        for idx, row in live_cars.iterrows():
            entry_dt = datetime.strptime(row['entry_time'], "%Y-%m-%d %H:%M")
            time_spent = (datetime.now() - entry_dt).seconds // 60
            border_color = "#00d4ff" if time_spent < 40 else "#FF3B30"
            st.markdown(f'<div class="status-card" style="border-left: 10px solid {border_color};">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"### {row['plate']} ({row['vehicle_type']})")
                st.write(f"**SERVICES:** {row['service_detail']}")
                st.write(f"**ZONE:** {row['status']}")
            with c2:
                st.write(f"**DETAILER:** {row['staff']}")
                st.write(f"**ELAPSED:** {time_spent} mins")
            with c3:
                # --- WET TO DRY LOGIC ---
                if row['status'] == "WET BAY":
                    with st.popover("TO DRY BAY"):
                        dry_staff = get_free_staff_by_dept("DRY BAY")
                        new_dry_detailer = st.selectbox("Assign Dry Bay", dry_staff if dry_staff else ["NO FREE STAFF"], key=f"dry_{idx}")
                        if st.button("Confirm Handover", key=f"hnd_{idx}"):
                            if new_dry_detailer != "NO FREE STAFF":
                                # NEW: Store the current staff (Wet) into wet_staff_history before changing status
                                c.execute("UPDATE live_bays SET status='DRY BAY', staff=?, wet_staff_history=? WHERE plate=?", 
                                          (new_dry_detailer, row['staff'], row['plate']))
                                conn.commit(); add_event(f"{row['plate']} moved to Dry Bay"); st.rerun()
                
                # --- AUTOMATED COMMISSION RELEASE LOGIC ---
                if st.button(f"RELEASE {row['plate']}", key=f"rel_{idx}"):
                    # 1. Get Transaction Total
                    c.execute("SELECT total FROM sales WHERE plate=? ORDER BY id DESC LIMIT 1", (row['plate'],))
                    sale_data = c.fetchone()
                    
                    if sale_data:
                        sale_total = sale_data[0]
                        # 2. Identify Staff Involved (Current + Previous)
                        current_staff = row['staff'] # Likely Dry Bay
                        prev_staff = row['wet_staff_history'] # Wet Bay
                        
                        staff_to_pay = [s for s in [current_staff, prev_staff] if s is not None]
                        
                        for s_member in staff_to_pay:
                            # Get their commission %
                            c.execute("SELECT bonus_pc FROM staff_payroll_config WHERE username=?", (s_member,))
                            p_res = c.fetchone()
                            if p_res and p_res[0] > 0:
                                comm_amt = sale_total * (p_res[0] / 100)
                                c.execute("INSERT INTO earnings_log (username, amount, ref_plate, timestamp) VALUES (?,?,?,?)",
                                          (s_member, comm_amt, row['plate'], datetime.now().strftime("%Y-%m-%d %H:%M")))

                    c.execute("SELECT name, phone FROM customers WHERE plate=?", (row['plate'],))
                    cust_info = c.fetchone()
                    c.execute("DELETE FROM live_bays WHERE plate=?", (row['plate'],))
                    conn.commit()
                    add_event(f"{row['plate']} Released.")
                    if cust_info:
                        wa_msg = f"Hi {cust_info[0]}, your vehicle ({row['plate']}) is ready! Thank you."
                        st.markdown(f'<a href="{format_whatsapp(cust_info[1], wa_msg)}" target="_blank">SEND WA</a>', unsafe_allow_html=True)
                    st.success("Released & Commissions Logged.")
                    time.sleep(1); st.rerun()
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
                # Default Verified=0 for staff
                c.execute("INSERT OR REPLACE INTO users (username, password, role, dept, status, verified) VALUES (?,?,?,?,?,?)", (s_name, s_pass, s_role, s_dept, 'ACTIVE', 0))
                conn.commit(); st.success(f"{s_name} added to {s_dept}."); st.rerun()
    st.write("---")
    st.subheader("CURRENT STAFF DIRECTORY")
    current_staff_df = pd.read_sql_query("SELECT username, dept, role, status, verified FROM users", conn)
    st.dataframe(current_staff_df, use_container_width=True)
    target_staff = st.selectbox("Select Staff Member", ["None"] + current_staff_df['username'].tolist())
    if st.button("DEACTIVATE STAFF") and target_staff != "None":
        c.execute("UPDATE users SET status='INACTIVE' WHERE username=?", (target_staff,))
        conn.commit(); st.rerun()

# --- NEW FEATURE 2: BOSS HR PORTAL ---
elif choice == "BOSS HR" and st.session_state.user_role == "MANAGER":
    st.subheader("BOSS HUMAN RESOURCES")
    
    hr_t1, hr_t2, hr_t3 = st.tabs(["PENDING APPROVALS", "ACTIVE STAFF DOSSIERS", "SALARY CONFIG"])
    
    with hr_t1:
        # PENDING VERIFICATIONS
        pending_staff = pd.read_sql_query("SELECT * FROM staff_profiles WHERE username IN (SELECT username FROM users WHERE verified=0)", conn)
        if pending_staff.empty:
            st.info("No pending verifications.")
        else:
            for idx, row in pending_staff.iterrows():
                with st.expander(f"REVIEW: {row['username']} ({row['full_name']})"):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if row['id_image']:
                            try:
                                image = Image.open(io.BytesIO(row['id_image']))
                                st.image(image, caption=row['id_type'])
                            except:
                                st.error("Image Error")
                    with c2:
                        st.write(f"**NIN:** {row['nin']}")
                        st.write(f"**Address:** {row['address']}")
                        st.write(f"**Bank:** {row['bank_name']} - {row['account_no']}")
                        
                        if st.button("APPROVE & VERIFY", key=f"app_{idx}"):
                            c.execute("UPDATE users SET verified=1 WHERE username=?", (row['username'],))
                            # Set default salary config 0
                            c.execute("INSERT OR IGNORE INTO staff_payroll_config VALUES (?, 0, 0)", (row['username'],))
                            conn.commit(); st.success("Approved!"); st.rerun()

    with hr_t2:
        # ACTIVE STAFF TABLE & DETAILS
        active_staff = pd.read_sql_query("SELECT username FROM users WHERE verified=1 AND role='STAFF'", conn)
        st.dataframe(active_staff, use_container_width=True)
        
        selected_staff = st.selectbox("SELECT STAFF TO VIEW FULL DETAILS", active_staff['username'].tolist())
        if selected_staff:
            s_prof = pd.read_sql_query(f"SELECT * FROM staff_profiles WHERE username='{selected_staff}'", conn)
            if not s_prof.empty:
                row = s_prof.iloc[0]
                base, d_com, m_com, y_com, total_m = calculate_payouts(selected_staff)
                
                st.markdown("---")
                col_d1, col_d2 = st.columns([1, 2])
                with col_d1:
                     if row['id_image']:
                        image = Image.open(io.BytesIO(row['id_image']))
                        st.image(image, caption=f"{selected_staff}'s ID")
                with col_d2:
                    st.markdown(f"### {row['full_name']}")
                    st.write(f"**Phone:** {row['phone']}")
                    st.write(f"**NIN:** {row['nin']}")
                    st.write(f"**Bank:** {row['bank_name']} | {row['account_no']}")
                    st.info(f"💰 BASE SALARY: ₦{base:,} | BONUS %: SET IN CONFIG")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Daily Bonus", f"₦{d_com:,}")
                    m2.metric("Monthly Bonus", f"₦{m_com:,}")
                    m3.metric("Yearly Bonus", f"₦{y_com:,}")
                    st.success(f"**TOTAL ESTIMATED PAYOUT THIS MONTH:** ₦{total_m:,}")

    with hr_t3:
        # SALARY CONFIG
        st.write("Configure Payroll Parameters")
        all_staff_list = pd.read_sql_query("SELECT username FROM users WHERE role='STAFF'", conn)['username'].tolist()
        
        config_staff = st.selectbox("Select Staff to Config", all_staff_list)
        if config_staff:
            c.execute("SELECT base_salary, bonus_pc FROM staff_payroll_config WHERE username=?", (config_staff,))
            curr = c.fetchone()
            curr_base = curr[0] if curr else 0.0
            curr_bon = curr[1] if curr else 0.0
            
            with st.form("sal_conf"):
                new_base = st.number_input("Monthly Base Salary (₦)", value=curr_base)
                new_bon = st.number_input("Commission Percentage per Car (%)", value=curr_bon)
                if st.form_submit_button("UPDATE PAYROLL CONFIG"):
                    c.execute("INSERT OR REPLACE INTO staff_payroll_config VALUES (?,?,?)", (config_staff, new_base, new_bon))
                    conn.commit(); st.success("Updated!"); st.rerun()

# --- 4. INVENTORY & STAFF (MANAGER) ---
elif choice == "INVENTORY & STAFF" and st.session_state.user_role == "MANAGER":
    t1, t2, t3 = st.tabs(["Lounge Inventory", "Wash Price List", "Staff Performance"])
    with t1:
        with st.form("new_item"):
            ni_name = st.text_input("Item Name")
            ni_stock = st.number_input("Stock", min_value=0.0)
            ni_unit = st.text_input("Unit")
            ni_price = st.number_input("Price (₦)", min_value=0.0)
            if st.form_submit_button("ADD/UPDATE"):
                c.execute("INSERT OR REPLACE INTO inventory VALUES (?,?,?,?)", (ni_name, ni_stock, ni_unit, ni_price))
                conn.commit(); st.rerun()
        inv_data = pd.read_sql_query("SELECT * FROM inventory", conn)
        st.dataframe(inv_data, use_container_width=True)
    with t2:
        st.subheader("EDIT SERVICES & PRICES")
        edit_svc_list = list(SERVICES.keys())
        svc_to_edit = st.selectbox("Select Service to Modify", ["-- ADD NEW --"] + edit_svc_list)
        with st.form("svc_form"):
            new_name = st.text_input("Service Name", value="" if svc_to_edit == "-- ADD NEW --" else svc_to_edit)
            new_price = st.number_input("Service Price (₦)", value=0.0 if svc_to_edit == "-- ADD NEW --" else SERVICES[svc_to_edit])
            sub_col1, sub_col2 = st.columns(2)
            if sub_col1.form_submit_button("SAVE SERVICE"):
                if svc_to_edit != "-- ADD NEW --" and new_name != svc_to_edit:
                    c.execute("DELETE FROM wash_prices WHERE service=?", (svc_to_edit,))
                c.execute("INSERT OR REPLACE INTO wash_prices VALUES (?,?)", (new_name, new_price))
                conn.commit(); st.rerun()
            if svc_to_edit != "-- ADD NEW --":
                if sub_col2.form_submit_button("DELETE SERVICE"):
                    c.execute("DELETE FROM wash_prices WHERE service=?", (svc_to_edit,))
                    conn.commit(); st.rerun()
    with t3:
        perf_query = "SELECT staff, COUNT(*) as washes, SUM(total) as revenue FROM sales WHERE type='CAR WASH' GROUP BY staff"
        perf_df = pd.read_sql_query(perf_query, conn)
        st.bar_chart(perf_df.set_index('staff')['washes'])
        st.dataframe(perf_df, use_container_width=True)

# --- 5. FINANCIALS (SMART YEARLY LOGIC) ---
elif choice == "FINANCIALS" and st.session_state.user_role == "MANAGER":
    st.subheader("FINANCIAL INTELLIGENCE CENTER")
    tab_fin, tab_cards_hub = st.tabs(["TRANSPARENT REVENUE", "MEMBERSHIP HUB"])
    
    with tab_fin:
        col_f1, col_f2 = st.columns([1, 2])
        view_scope = col_f1.radio("REPORTING SCOPE", ["DAILY", "MONTHLY", "YEARLY"], horizontal=True)
        sales_raw = pd.read_sql_query("SELECT * FROM sales", conn)
        exp_raw = pd.read_sql_query("SELECT * FROM expenses", conn)
        m_sales_raw = pd.read_sql_query("SELECT plate, card_type, sale_price, '2026-01-01' as timestamp FROM memberships", conn)
        sales_raw['timestamp'] = pd.to_datetime(sales_raw['timestamp'])
        exp_raw['timestamp'] = pd.to_datetime(exp_raw['timestamp'])
        now = datetime.now()
        
        if view_scope == "DAILY":
            selected_date = col_f2.date_input("SELECT DAY", now.date())
            f_sales = sales_raw[sales_raw['timestamp'].dt.date == selected_date]
            f_exps = exp_raw[exp_raw['timestamp'].dt.date == selected_date]
            label = f"REPORT FOR {selected_date}"
        elif view_scope == "MONTHLY":
            months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            selected_month_name = col_f2.selectbox("SELECT MONTH", months, index=now.month-1)
            selected_month = months.index(selected_month_name) + 1
            f_sales = sales_raw[(sales_raw['timestamp'].dt.month == selected_month) & (sales_raw['timestamp'].dt.year == now.year)]
            f_exps = exp_raw[(exp_raw['timestamp'].dt.month == selected_month) & (exp_raw['timestamp'].dt.year == now.year)]
            label = f"REPORT FOR {selected_month_name} {now.year}"
        else:
            current_year = now.year
            year_options = list(range(2024, current_year + 1))
            selected_year = col_f2.selectbox("SELECT YEAR", year_options, index=len(year_options)-1)
            f_sales = sales_raw[sales_raw['timestamp'].dt.year == selected_year]
            f_exps = exp_raw[exp_raw['timestamp'].dt.year == selected_year]
            label = f"ANNUAL REPORT {selected_year}"

        rev_wash = f_sales[f_sales['type'] == 'CAR WASH']['total'].sum()
        rev_lounge = f_sales[f_sales['type'] == 'LOUNGE']['total'].sum()
        card_total = m_sales_raw['sale_price'].sum() if view_scope != "DAILY" else 0 
        total_exp = f_exps['amount'].sum()
        net_profit = (rev_wash + rev_lounge + card_total) - total_exp

        st.markdown(f"### {label}")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("WASH REVENUE", f"₦{rev_wash:,}")
        m2.metric("LOUNGE REVENUE", f"₦{rev_lounge:,}")
        m3.metric("CARD SALES", f"₦{card_total:,}")
        m4.metric("EXPENSES", f"₦{total_exp:,}")
        m5.metric("NET PROFIT/LOSS", f"₦{net_profit:,}", delta=net_profit, delta_color="normal")
        st.markdown("---")
        chart_data = pd.DataFrame({'Category': ['Wash', 'Lounge', 'Cards', 'Expenses'], 'Amount': [rev_wash, rev_lounge, card_total, total_exp]})
        st.bar_chart(chart_data.set_index('Category'))
        st.subheader("Detailed Transaction Log")
        st.dataframe(f_sales, use_container_width=True)
        csv = f_sales.to_csv(index=False).encode('utf-8')
        st.download_button("📥 DOWNLOAD FILTERED REPORT (CSV)", csv, f"RideBoss_{view_scope}_{label}.csv", "text/csv")
        with st.expander("LOG NEW EXPENSE"):
            e_desc = st.text_input("Description")
            e_amt = st.number_input("Amount", min_value=0.0)
            if st.button("LOG"):
                c.execute("INSERT INTO expenses (description, amount, timestamp) VALUES (?,?,?)", (e_desc, e_amt, datetime.now().strftime("%Y-%m-%d")))
                conn.commit(); st.rerun()

        with tab_cards_hub:
        m_df = pd.read_sql_query("SELECT * FROM memberships", conn)
        for idx, row in m_df.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.write(f"**{row['plate']}** ({row['card_type']})")
                c2.write(f"Bal: {row['balance_washes']} left")
                
                # Correctly indented under st.container
                if c3.button(f"TOP UP {row['plate']}", key=f"up_{idx}"):
                    # 1. Update the balance
                    c.execute("UPDATE memberships SET balance_washes = 10 WHERE plate=?", (row['plate'],))
                    
                    # 2. Log Commission for the person who clicked 'Top Up'
                    receptionist = st.session_state.user_name
                    c.execute("SELECT bonus_pc FROM staff_payroll_config WHERE username=?", (receptionist,))
                    p_res = c.fetchone()
                    if p_res and p_res[0] > 0:
                        comm_amt = row['sale_price'] * (p_res[0] / 100)
                        c.execute("INSERT INTO earnings_log (username, amount, ref_plate, timestamp) VALUES (?,?,?,?)",
                                  (receptionist, comm_amt, f"REFILL:{row['plate']}", datetime.now().strftime("%Y-%m-%d %H:%M")))
                    
                    conn.commit()
                    st.success(f"Card Refilled & Commission Logged!")
                    st.rerun()

                # Correctly indented under st.container
                if c4.button(f"DELETE {row['plate']}", key=f"del_{idx}"):
                    c.execute("DELETE FROM memberships WHERE plate=?", (row['plate'],))
                    conn.commit()
                    st.rerun()
                
                st.markdown("---")     

# --- 6. CRM & NOTIFICATIONS ---
elif choice == "CRM & RETENTION" and st.session_state.user_role == "MANAGER":
    st.subheader("RETENTION PANEL")
    cust_df = pd.read_sql_query("SELECT * FROM customers", conn)
    for idx, row in cust_df.iterrows():
        last_v = datetime.strptime(row['last_visit'], "%Y-%m-%d")
        days = (datetime.now() - last_v).days
        color = "#00d4ff" if days < 14 else "#FF3B30"
        st.markdown(f"<p style='color:{color};'><b>{row['name']}</b> ({row['plate']}) - {days} days since last visit</p>", unsafe_allow_html=True)

elif choice == "NOTIFICATIONS":
    st.subheader("SYSTEM HISTORY")
    notes = pd.read_sql_query("SELECT timestamp as 'TIME', message as 'EVENT' FROM notifications ORDER BY id DESC", conn)
    st.table(notes)

# --- NEW FEATURE: MY EARNINGS (FOR STAFF) ---
elif choice == "MY EARNINGS":
    st.subheader(f"EARNINGS DASHBOARD: {st.session_state.user_name}")
    base, d_com, m_com, y_com, total_m = calculate_payouts(st.session_state.user_name)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("COMMISSION (TODAY)", f"₦{d_com:,}")
    col2.metric("COMMISSION (THIS MONTH)", f"₦{m_com:,}")
    col3.metric("TOTAL PAYOUT (BASE + BONUS)", f"₦{total_m:,}")
    
    st.write("### RECENT EARNINGS LOG")
    e_log = pd.read_sql_query(f"SELECT timestamp, ref_plate, amount FROM earnings_log WHERE username='{st.session_state.user_name}' ORDER BY id DESC LIMIT 20", conn)
    st.table(e_log)
