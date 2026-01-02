import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import urllib.parse

# --- DATABASE SETUP ---
conn = sqlite3.connect('rideboss_ultra.db', check_same_thread=False)
c = conn.cursor()

# Ensure all tables exist including the new Users and Membership tables
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS customers 
             (plate TEXT PRIMARY KEY, name TEXT, phone TEXT, visits INTEGER, last_visit TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS sales 
             (id INTEGER PRIMARY KEY, plate TEXT, services TEXT, total REAL, method TEXT, staff TEXT, timestamp TEXT, type TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notifications 
             (id INTEGER PRIMARY KEY, message TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS live_bays 
             (plate TEXT PRIMARY KEY, status TEXT, entry_time TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS inventory 
             (item TEXT PRIMARY KEY, stock REAL, unit TEXT, price REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS wash_prices (service TEXT PRIMARY KEY, price REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, description TEXT, amount REAL, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS memberships 
             (plate TEXT PRIMARY KEY, balance_washes INTEGER, card_type TEXT)''')

# Seed Admin and Initial Data
c.execute("INSERT OR IGNORE INTO users VALUES ('admin', '0000', 'MANAGER')")
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
    
    /* CLASSIC PREMIUM RECEIPT */
    .receipt-wrap { background: white; color: black; padding: 40px; font-family: 'Garamond', serif; max-width: 450px; margin: auto; border: 1px solid #ccc; box-shadow: 0 0 20px rgba(0,0,0,0.2); line-height: 1.2; }
    .receipt-header { text-align: center; border-bottom: 3px double black; padding-bottom: 15px; margin-bottom: 20px; }
    .receipt-header h1 { margin: 0; letter-spacing: 5px; font-weight: 900; font-size: 28px; }
    .receipt-header p { margin: 2px 0; font-size: 14px; text-transform: uppercase; }
    .receipt-body { font-size: 16px; }
    .receipt-row { display: flex; justify-content: space-between; margin: 10px 0; border-bottom: 1px dotted #ccc; }
    .receipt-total { border-top: 2px solid black; margin-top: 20px; padding-top: 10px; display: flex; justify-content: space-between; font-size: 22px; font-weight: bold; }
    .receipt-stamp { border: 2px solid #900; color: #900; padding: 5px 15px; display: inline-block; font-weight: bold; transform: rotate(-5deg); margin-top: 20px; font-size: 14px; text-transform: uppercase; }
    
    @media print { .no-print { display: none !important; } .stApp { background: white !important; } }
    </style>
    """, unsafe_allow_html=True)

# --- UTILITIES ---
def add_event(msg):
    now = datetime.now().strftime("%H:%M:%S")
    c.execute("INSERT INTO notifications (message, timestamp) VALUES (?,?)", (f"{now} | {msg}", now))
    conn.commit()

def format_whatsapp(phone, message):
    return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"

# --- LOGIN SYSTEM ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = None
if 'user_name' not in st.session_state: st.session_state.user_name = None

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align:center; letter-spacing:10px; margin-top:100px;'>RIDEBOSS LOGIN</h1>", unsafe_allow_html=True)
    _, log_col, _ = st.columns([1,1,1])
    with log_col:
        u = st.text_input("Username").strip()
        p = st.text_input("Password", type="password")
        if st.button("ACCESS SYSTEM"):
            c.execute("SELECT role FROM users WHERE username=? AND password=?", (u, p))
            result = c.fetchone()
            if result:
                st.session_state.logged_in = True
                st.session_state.user_role = result[0]
                st.session_state.user_name = u
                st.rerun()
            else:
                st.error("Invalid Username or Password")
    st.stop()

# --- LOAD CONFIG ---
staff_df = pd.read_sql_query("SELECT username FROM users", conn)
STAFF_MEMBERS = staff_df['username'].tolist()
wash_prices_df = pd.read_sql_query("SELECT * FROM wash_prices", conn)
SERVICES = dict(zip(wash_prices_df['service'], wash_prices_df['price']))
COUNTRY_CODES = {"Nigeria": "+234", "Ghana": "+233", "UK": "+44", "USA": "+1", "UAE": "+971"}

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown(f"USER: **{st.session_state.user_name}**")
menu = ["COMMAND CENTER", "LIVE U-FLOW", "NOTIFICATIONS"]
if st.session_state.user_role == "MANAGER":
    menu += ["GOLD CARD MGMT", "ONBOARD STAFF", "INVENTORY & STAFF", "FINANCIALS", "CRM & RETENTION"]

choice = st.sidebar.radio("NAVIGATE", menu)
if st.sidebar.button("LOGOUT"):
    st.session_state.logged_in = False
    st.rerun()

# --- TOP NOTIFICATION FEED ---
latest_note = pd.read_sql_query("SELECT message FROM notifications ORDER BY id DESC LIMIT 1", conn)
st.markdown(f'<div class="notification-bar">SYSTEM LOG: {latest_note["message"].iloc[0] if not latest_note.empty else "READY"}</div>', unsafe_allow_html=True)

# --- 1. COMMAND CENTER ---
if choice == "COMMAND CENTER":
    tab_trans, tab_mem = st.tabs(["NEW TRANSACTION", "REGISTER MEMBERSHIP"])
    
    with tab_trans:
        mode = st.radio("SELECT MODE", ["CAR WASH", "LOUNGE"], horizontal=True)
        st.markdown("---")
        
        cust_data = pd.read_sql_query("SELECT * FROM customers", conn)
        search_options = ["NEW CUSTOMER"] + [f"{r['plate']} - {r['name']} ({r['phone']})" for _, r in cust_data.iterrows()]
        search_selection = st.selectbox("SEARCH EXISTING CLIENT (OR SCAN PLATE)", search_options)
        
        d_plate, d_name, d_phone = "", "", ""
        if search_selection != "NEW CUSTOMER":
            p_key = search_selection.split(" - ")[0]
            match = cust_data[cust_data['plate'] == p_key].iloc[0]
            d_plate, d_name, d_phone = match['plate'], match['name'], match['phone']

        col1, col2 = st.columns(2)
        with col1:
            plate = st.text_input("PLATE NUMBER", value=d_plate).upper()
            name = st.text_input("CLIENT NAME", value=d_name)
            c_code = st.selectbox("COUNTRY CODE", list(COUNTRY_CODES.keys()))
            phone_raw = st.text_input("PHONE (No leading zero)", value=d_phone[3:] if d_phone else "")
            full_phone = f"{COUNTRY_CODES[c_code].replace('+', '')}{phone_raw}" if not d_phone else d_phone

        with col2:
            lounge_items_sold = []
            if mode == "CAR WASH":
                selected = st.multiselect("SERVICES", list(SERVICES.keys()))
                total_price = sum([SERVICES[s] for s in selected])
                staff_assigned = st.selectbox("ASSIGN DETAILER", STAFF_MEMBERS)
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
                staff_assigned = st.selectbox("SERVER", STAFF_MEMBERS)
                item_summary = ", ".join([f"{i} (x{q})" for i, q in lounge_items_sold])

            st.markdown(f"### TOTAL: ₦{total_price:,}")
            pay_method = st.selectbox("PAYMENT METHOD", ["Moniepoint POS", "Bank Transfer", "Cash", "Membership Gold Card"])

        if st.button(f"AUTHORIZE {mode} TRANSACTION", use_container_width=True):
            if (plate or mode == "LOUNGE") and (selected if mode=="CAR WASH" else lounge_items_sold):
                can_proceed = True
                low_balance_alert = False
                
                if pay_method == "Membership Gold Card":
                    c.execute("SELECT balance_washes FROM memberships WHERE plate=?", (plate,))
                    m_res = c.fetchone()
                    if m_res and m_res[0] > 0:
                        new_bal = m_res[0] - 1
                        c.execute("UPDATE memberships SET balance_washes=? WHERE plate=?", (new_bal, plate))
                        add_event(f"GOLD CARD USED: {plate} (Bal: {new_bal})")
                        if new_bal == 1: low_balance_alert = True
                    else:
                        st.error("❌ INSUFFICIENT CARD BALANCE OR PLATE NOT REGISTERED.")
                        can_proceed = False

                if can_proceed:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    c.execute("INSERT INTO sales (plate, services, total, method, staff, timestamp, type) VALUES (?,?,?,?,?,?,?)", 
                              (plate, item_summary, total_price, pay_method, staff_assigned, now, mode))
                    c.execute("INSERT OR REPLACE INTO customers (plate, name, phone, visits, last_visit) VALUES (?, ?, ?, COALESCE((SELECT visits FROM customers WHERE plate=?), 0) + 1, ?)", (plate, name, full_phone, plate, now.split()[0]))
                    if mode == "CAR WASH":
                        c.execute("INSERT OR REPLACE INTO live_bays (plate, status, entry_time) VALUES (?, ?, ?)", (plate, "WET BAY", now))
                    else:
                        for item, qty in lounge_items_sold:
                            c.execute("UPDATE inventory SET stock = stock - ? WHERE item = ?", (qty, item))
                    conn.commit()
                    st.session_state['last_receipt'] = {
                        "id": c.lastrowid, "mode": mode, "name": name, "plate": plate, "phone": full_phone,
                        "items": item_summary, "total": total_price if pay_method != "Membership Gold Card" else 0, 
                        "staff": staff_assigned, "date": now, "method": pay_method, "low_bal": low_balance_alert
                    }
                    st.rerun()

    with tab_mem:
        st.subheader("ISSUE NEW MEMBERSHIP CARD")
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            new_m_plate = st.text_input("VEHICLE PLATE (CARD ID)").upper()
            new_m_tier = st.selectbox("CARD TIER", ["Silver (5 Washes)", "Gold (10 Washes)", "Platinum (25 Washes)"])
        with m_col2:
            st.info("Pricing logic: Staff ensures payment is received via POS/Cash before activation.")
            m_washes = 5 if "Silver" in new_m_tier else 10 if "Gold" in new_m_tier else 25
            if st.button("ACTIVATE & REGISTER CARD"):
                if new_m_plate:
                    c.execute("INSERT OR REPLACE INTO memberships (plate, balance_washes, card_type) VALUES (?, ?, ?)", 
                              (new_m_plate, m_washes, new_m_tier))
                    conn.commit()
                    add_event(f"STAFF ISSUED {new_m_tier} TO {new_m_plate}")
                    st.success(f"Successfully activated {new_m_tier} for {new_m_plate}!")
                else:
                    st.error("Please enter a Plate Number.")

    # Receipt display logic
    if 'last_receipt' in st.session_state:
        r = st.session_state['last_receipt']
        st.markdown(f"""
        <div class="receipt-wrap">
            <div class="receipt-header">
                <h1>RIDEBOSS AUTOS</h1>
                <p>Premium Detailing & Lounge</p>
                <p>Abuja-Kaduna Expressway, Nigeria</p>
                <p>Phone: 09029557912</p>
            </div>
            <div class="receipt-body">
                <div class="receipt-row"><span>Receipt ID:</span> <span>#RB{r['id']}</span></div>
                <div class="receipt-row"><span>Date:</span> <span>{r['date']}</span></div>
                <div class="receipt-row"><span>Client:</span> <span>{r['name']}</span></div>
                <div class="receipt-row"><span>Plate:</span> <span>{r['plate']}</span></div>
                <hr style="border:1px solid black">
                <p><b>DESCRIPTION:</b></p>
                <p>{r['items']}</p>
                <div class="receipt-total"><span>TOTAL:</span><span>₦{r['total']:,}</span></div>
                <div class="receipt-row"><span>Method:</span> <span>{r['method']}</span></div>
            </div>
            <div style="text-align:center;"><div class="receipt-stamp">RIDEBOSS OFFICIAL</div></div>
        </div>
        """, unsafe_allow_html=True)
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            if st.button("🖨️ PRINT"): st.markdown('<script>window.print();</script>', unsafe_allow_html=True)
        with c_p2:
            if r.get('low_bal'):
                alert_msg = f"Hi {r['name']}, your RideBoss Gold Card has only 1 wash left. Visit us to top up!"
                st.markdown(f'<a href="{format_whatsapp(r["phone"], alert_msg)}" target="_blank"><button style="width:100%; height:3em; background:#25D366; color:white; border:none; cursor:pointer;">⚠️ SEND ALERT</button></a>', unsafe_allow_html=True)
        with c_p3:
            if st.button("DONE"):
                del st.session_state['last_receipt']
                st.rerun()

# --- 2. LIVE U-FLOW ---
elif choice == "LIVE U-FLOW":
    st.subheader("ACTIVE WASH BAYS")
    live_cars = pd.read_sql_query("SELECT * FROM live_bays", conn)
    if live_cars.empty: st.info("ALL BAYS CLEAR.")
    else:
        for idx, row in live_cars.iterrows():
            st.markdown('<div class="status-card">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.write(f"**{row['plate']}** | ZONE: {row['status']}")
            with c2:
                if row['status'] == "WET BAY":
                    if st.button(f"TRANSIT {row['plate']} TO DRY"):
                        c.execute("UPDATE live_bays SET status='DRY BAY' WHERE plate=?", (row['plate'],))
                        add_event(f"{row['plate']} MOVED TO DRY."); conn.commit(); st.rerun()
            with c3:
                if st.button(f"RELEASE {row['plate']}"):
                    c.execute("SELECT name, phone FROM customers WHERE plate=?", (row['plate'],))
                    cust = c.fetchone()
                    c.execute("DELETE FROM live_bays WHERE plate=?", (row['plate'],))
                    add_event(f"{row['plate']} READY."); conn.commit()
                    msg = f"Hi {cust[0]}, your vehicle {row['plate']} is ready at RideBoss!"
                    st.markdown(f"[:speech_balloon: WHATSAPP]({format_whatsapp(cust[1], msg)})")
            st.markdown('</div>', unsafe_allow_html=True)

# --- 3. MANAGER TABS ---
elif choice == "GOLD CARD MGMT" and st.session_state.user_role == "MANAGER":
    st.subheader("MEMBERSHIP DATABASE (MANAGER ONLY)")
    m_data = pd.read_sql_query("SELECT * FROM memberships", conn)
    st.dataframe(m_data, use_container_width=True)
    if st.button("RESET PLATE BALANCE"):
        reset_plate = st.text_input("Enter Plate to Reset")
        if st.button("CONFIRM RESET"):
            c.execute("DELETE FROM memberships WHERE plate=?", (reset_plate,))
            conn.commit(); st.rerun()

elif choice == "ONBOARD STAFF" and st.session_state.user_role == "MANAGER":
    st.subheader("STAFF ONBOARDING")
    with st.form("new_staff"):
        s_name = st.text_input("Username")
        s_pass = st.text_input("Password", type="password")
        s_role = st.selectbox("Role", ["STAFF", "MANAGER"])
        if st.form_submit_button("ADD"):
            c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (s_name, s_pass, s_role))
            conn.commit(); st.rerun()

elif choice == "FINANCIALS" and st.session_state.user_role == "MANAGER":
    sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
    st.metric("TOTAL REVENUE", f"₦{sales_df['total'].sum():,}")
    st.dataframe(sales_df)

elif choice == "NOTIFICATIONS":
    notes = pd.read_sql_query("SELECT timestamp, message FROM notifications ORDER BY id DESC", conn)
    st.table(notes)
