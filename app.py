import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import urllib.parse
import time

# --- DATABASE SETUP ---
conn = sqlite3.connect('rideboss_ultra.db', check_same_thread=False)
c = conn.cursor()

# Ensure all tables exist including the new Users and Membership tables
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (username TEXT PRIMARY KEY, password TEXT, role TEXT, dept TEXT, status TEXT DEFAULT 'ACTIVE')''')
c.execute('''CREATE TABLE IF NOT EXISTS customers 
             (plate TEXT PRIMARY KEY, name TEXT, phone TEXT, visits INTEGER, last_visit TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS sales 
             (id INTEGER PRIMARY KEY, plate TEXT, services TEXT, total REAL, method TEXT, staff TEXT, timestamp TEXT, type TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notifications 
             (id INTEGER PRIMARY KEY, message TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS live_bays 
             (plate TEXT PRIMARY KEY, status TEXT, entry_time TEXT, staff TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS inventory (item TEXT PRIMARY KEY, stock REAL, unit TEXT, price REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS wash_prices (service TEXT PRIMARY KEY, price REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, description TEXT, amount REAL, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS memberships 
             (plate TEXT PRIMARY KEY, balance_washes INTEGER, card_type TEXT, sale_price REAL DEFAULT 0.0)''')

# Seed Admin and Initial Data
c.execute("INSERT OR IGNORE INTO users VALUES ('admin', '0000', 'MANAGER', 'MANAGEMENT', 'ACTIVE')")
c.execute("INSERT OR IGNORE INTO inventory VALUES ('Car Shampoo', 10.0, 'Gallons', 0), ('Coke', 50.0, 'Cans', 500), ('Water', 100.0, 'Bottles', 200)")
c.execute("SELECT COUNT(*) FROM wash_prices")
if c.fetchone()[0] == 0:
    initial_services = [("Standard Wash", 5000), ("Executive Detail", 15000), ("Engine Steam", 10000), ("Ceramic Wax", 25000), ("Interior Deep Clean", 12000)]
    c.executemany("INSERT INTO wash_prices VALUES (?,?)", initial_services)
conn.commit()

# --- CLASSIC UI STYLING & ANIMATIONS ---
st.set_page_config(page_title="RideBoss Autos HQ", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #E0E0E0; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #0A0A0A; border-right: 1px solid #222; }
    .status-card { background: #0F0F0F; padding: 25px; border-radius: 2px; border-left: 4px solid #00d4ff; margin-bottom: 15px; border-top: 1px solid #1A1A1A; }
    .notification-bar { background: #00d4ff22; padding: 12px; border-bottom: 1px solid #00d4ff; color: #00d4ff; font-size: 0.85em; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 30px; }
    .stButton>button { border-radius: 0px; letter-spacing: 2px; font-size: 0.8em; text-transform: uppercase; background-color: transparent; border: 1px solid #333; color: white; height: 3em; transition: 0.4s; width: 100%; }
    .stButton>button:hover { border-color: #00d4ff; color: #00d4ff; background-color: #00d4ff11; }
    
    /* MONITOR SCROLLING LOGIC */
    @keyframes scroll { 0% { transform: translateY(0); } 100% { transform: translateY(-50%); } }
    .scroll-container { height: 80vh; overflow: hidden; position: relative; border: 2px solid #222; border-radius: 10px; background: #000; }
    .scroll-content { animation: scroll 40s linear infinite; }
    .monitor-row { display: flex; justify-content: space-between; align-items: center; padding: 40px; border-bottom: 2px solid #222; }
    .monitor-plate { font-size: 80px; font-weight: 900; color: #00d4ff; font-family: 'Courier New', monospace; line-height: 1; }
    .monitor-service { font-size: 28px; color: #FFD700; text-transform: uppercase; margin-top: 10px; font-weight: 600; }
    .monitor-meta { text-align: right; }
    .monitor-staff { font-size: 25px; color: #888; text-transform: uppercase; }
    .monitor-status { font-size: 22px; color: #00FF41; font-weight: bold; }

    /* PRINTING OVERRIDE */
    @media print { 
        body * { visibility: hidden; }
        .receipt-wrap, .receipt-wrap * { visibility: visible; }
        .receipt-wrap { position: absolute; left: 0; top: 0; width: 100%; border: none !important; box-shadow: none !important; }
    }
    
    /* RECEIPT STYLING */
    .receipt-wrap { background: white; color: black !important; padding: 40px; font-family: 'Garamond', serif; max-width: 450px; margin: auto; border: 1px solid #ccc; line-height: 1.2; }
    .receipt-header { text-align: center; border-bottom: 3px double black; padding-bottom: 15px; margin-bottom: 20px; }
    .receipt-header h1 { margin: 0; letter-spacing: 5px; font-weight: 900; font-size: 28px; color: black !important;}
    .receipt-body { font-size: 16px; color: black !important;}
    .receipt-row { display: flex; justify-content: space-between; margin: 10px 0; border-bottom: 1px dotted #ccc; color: black !important;}
    .receipt-total { border-top: 2px solid black; margin-top: 20px; padding-top: 10px; display: flex; justify-content: space-between; font-size: 22px; font-weight: bold; color: black !important;}
    .receipt-stamp { border: 2px solid #900; color: #900; padding: 5px 15px; display: inline-block; font-weight: bold; transform: rotate(-5deg); margin-top: 20px; font-size: 14px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- UTILITIES ---
def add_event(msg):
    now = datetime.now().strftime("%H:%M:%S")
    c.execute("INSERT INTO notifications (message, timestamp) VALUES (?,?)", (f"{now} | {msg}", now))
    conn.commit()

def format_whatsapp(phone, message):
    return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"

def get_free_staff_by_dept(dept_name):
    busy_list = pd.read_sql_query("SELECT staff FROM live_bays", conn)['staff'].tolist()
    all_dept = pd.read_sql_query(f"SELECT username FROM users WHERE dept='{dept_name}' AND status='ACTIVE'", conn)['username'].tolist()
    return [s for s in all_dept if s not in busy_list]

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
                st.session_state.logged_in, st.session_state.user_role, st.session_state.user_name = True, result[0], u
                st.rerun()
            else: st.error("Invalid Username or Password")
    st.stop()

# --- LOAD DATA ---
wash_prices_df = pd.read_sql_query("SELECT * FROM wash_prices", conn)
SERVICES = dict(zip(wash_prices_df['service'], wash_prices_df['price']))
COUNTRY_CODES = {"Nigeria": "+234", "Ghana": "+233", "UK": "+44", "USA": "+1"}

# --- SIDEBAR ---
menu = ["COMMAND CENTER", "LIVE U-FLOW", "NOTIFICATIONS"]
if st.session_state.user_role == "MANAGER":
    menu += ["ONBOARD STAFF", "INVENTORY & STAFF", "FINANCIALS", "CRM & RETENTION"]
choice = st.sidebar.radio("NAVIGATE", menu)
if st.sidebar.button("LOGOUT"): st.session_state.logged_in = False; st.rerun()

# --- 1. COMMAND CENTER ---
if choice == "COMMAND CENTER":
    t1, t2 = st.tabs(["NEW TRANSACTION", "REGISTER MEMBERSHIP"])
    with t1:
        mode = st.radio("SELECT MODE", ["CAR WASH", "LOUNGE"], horizontal=True)
        cust_data = pd.read_sql_query("SELECT * FROM customers", conn)
        search_options = ["NEW CUSTOMER"] + [f"{r['plate']} - {r['name']}" for _, r in cust_data.iterrows()]
        search_selection = st.selectbox("SEARCH CLIENT", search_options)
        
        d_plate, d_name, d_phone = "", "", ""
        if search_selection != "NEW CUSTOMER":
            match = cust_data[cust_data['plate'] == search_selection.split(" - ")[0]].iloc[0]
            d_plate, d_name, d_phone = match['plate'], match['name'], match['phone']

        col1, col2 = st.columns(2)
        with col1:
            plate = st.text_input("PLATE NUMBER", value=d_plate).upper()
            name = st.text_input("CLIENT NAME", value=d_name)
            phone = st.text_input("PHONE (WhatsApp)", value=d_phone)
        with col2:
            lounge_items = []
            if mode == "CAR WASH":
                selected = st.multiselect("SERVICES", list(SERVICES.keys()))
                total_price = sum([SERVICES[s] for s in selected])
                staff_assigned = st.selectbox("ASSIGN WET BAY", get_free_staff_by_dept("WET BAY") or ["NO FREE STAFF"])
                item_summary = ", ".join(selected)
            else:
                inv_items = pd.read_sql_query("SELECT item, price FROM inventory WHERE price > 0", conn)
                selected_items = st.multiselect("SELECT ITEMS", inv_items['item'].tolist())
                total_price = 0
                for i in selected_items:
                    u_price = inv_items[inv_items['item'] == i]['price'].values[0]
                    qty = st.number_input(f"Qty for {i}", min_value=1, value=1, key=f"q_{i}")
                    total_price += (u_price * qty); lounge_items.append((i, qty))
                staff_assigned = st.session_state.user_name
                item_summary = ", ".join([f"{i} (x{q})" for i, q in lounge_items])

            st.markdown(f"### TOTAL: ₦{total_price:,}")
            pay_method = st.selectbox("PAYMENT", ["Moniepoint POS", "Bank Transfer", "Cash", "Gold Card Credit"])

        if st.button(f"AUTHORIZE {mode}"):
            can_proceed = True
            if pay_method == "Gold Card Credit":
                c.execute("SELECT balance_washes FROM memberships WHERE plate=?", (plate,))
                res = c.fetchone()
                if res and res[0] > 0:
                    c.execute("UPDATE memberships SET balance_washes = balance_washes - 1 WHERE plate=?", (plate,))
                    final_total = 0.0
                else: st.error("No Balance"); can_proceed = False
            else: final_total = total_price

            if can_proceed:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                c.execute("INSERT INTO sales (plate, services, total, method, staff, timestamp, type) VALUES (?,?,?,?,?,?,?)", 
                          (plate, item_summary, final_total, pay_method, staff_assigned, now, mode))
                c.execute("INSERT OR REPLACE INTO customers (plate, name, phone, visits, last_visit) VALUES (?,?,?,COALESCE((SELECT visits FROM customers WHERE plate=?),0)+1,?)", (plate, name, phone, plate, now.split()[0]))
                if mode == "CAR WASH": c.execute("INSERT OR REPLACE INTO live_bays VALUES (?,?,?,?)", (plate, "WET BAY", now, staff_assigned))
                conn.commit()
                st.session_state['last_receipt'] = {"id": c.lastrowid, "plate": plate, "items": item_summary, "total": total_price, "date": now}
                st.rerun()

    if 'last_receipt' in st.session_state:
        r = st.session_state['last_receipt']
        st.markdown(f'<div class="receipt-wrap"><div class="receipt-header"><h1>RIDEBOSS</h1><p>Premium Detailing</p></div><div class="receipt-body"><p>Plate: {r["plate"]}</p><p>ID: #RB{r["id"]}</p><hr><p>{r["items"]}</p><div class="receipt-total"><span>TOTAL:</span><span>₦{r["total"]:,}</span></div></div><div style="text-align:center;"><div class="receipt-stamp">OFFICIAL</div></div></div>', unsafe_allow_html=True)
        if st.button("🖨️ PRINT"): st.markdown('<script>window.print();</script>', unsafe_allow_html=True)
        if st.button("DONE"): del st.session_state['last_receipt']; st.rerun()

# --- 2. LIVE U-FLOW ---
elif choice == "LIVE U-FLOW":
    view = st.radio("VIEW", ["Controls", "External Flight Board"], horizontal=True)
    if view == "External Flight Board":
        # JOIN Logic to show what was actually paid for
        q = "SELECT lb.plate, lb.status, lb.staff, s.services FROM live_bays lb LEFT JOIN sales s ON lb.plate = s.plate GROUP BY lb.plate HAVING MAX(s.id)"
        df = pd.read_sql_query(q, conn)
        st.markdown("<h1 style='text-align:center; color:#00d4ff;'>FLIGHT BOARD</h1>", unsafe_allow_html=True)
        if df.empty: st.info("ALL BAYS CLEAR")
        else:
            rows = "".join([f'<div class="monitor-row"><div><div class="monitor-plate">{r["plate"]}</div><div class="monitor-service">⚡ {r["services"]}</div></div><div class="monitor-meta"><div class="monitor-status">{r["status"]}</div><div class="monitor-staff">{r["staff"]}</div></div></div>' for _, r in df.iterrows()])
            st.markdown(f'<div class="scroll-container"><div class="scroll-content">{rows + rows}</div></div>', unsafe_allow_html=True)
        time.sleep(20); st.rerun()
    else:
        live = pd.read_sql_query("SELECT * FROM live_bays", conn)
        for idx, row in live.iterrows():
            st.markdown(f'<div class="status-card"><b>{row["plate"]}</b> | {row["status"]} | {row["staff"]}</div>', unsafe_allow_html=True)
            if row['status'] == "WET BAY":
                if st.button(f"MOVE {row['plate']} TO DRY BAY", key=f"m_{idx}"):
                    staff = get_free_staff_by_dept("DRY BAY")
                    if staff:
                        c.execute("UPDATE live_bays SET status='DRY BAY', staff=? WHERE plate=?", (staff[0], row['plate']))
                        conn.commit(); st.rerun()
            if st.button(f"RELEASE {row['plate']}", key=f"r_{idx}"):
                c.execute("DELETE FROM live_bays WHERE plate=?", (row['plate'],)); conn.commit(); st.rerun()

# --- 4. INVENTORY & STAFF (MANAGER) ---
elif choice == "INVENTORY & STAFF" and st.session_state.user_role == "MANAGER":
    t1, t2 = st.tabs(["Lounge Inventory", "Wash Service Editor"])
    with t1:
        st.dataframe(pd.read_sql_query("SELECT * FROM inventory", conn), use_container_width=True)
    with t2:
        # Full CRUD Service Editor
        edit_svc = st.selectbox("Service to Edit", ["NEW SERVICE"] + list(SERVICES.keys()))
        with st.form("svc_form"):
            n_name = st.text_input("Name", value="" if edit_svc == "NEW SERVICE" else edit_svc)
            n_price = st.number_input("Price", value=0.0 if edit_svc == "NEW SERVICE" else SERVICES[edit_svc])
            if st.form_submit_button("SAVE"):
                if edit_svc != "NEW SERVICE" and n_name != edit_svc: c.execute("DELETE FROM wash_prices WHERE service=?", (edit_svc,))
                c.execute("INSERT OR REPLACE INTO wash_prices VALUES (?,?)", (n_name, n_price)); conn.commit(); st.rerun()

# --- 5. FINANCIALS ---
elif choice == "FINANCIALS" and st.session_state.user_role == "MANAGER":
    sales = pd.read_sql_query("SELECT * FROM sales", conn)
    rev = sales['total'].sum()
    card_rev = pd.read_sql_query("SELECT SUM(sale_price) FROM memberships", conn).iloc[0,0] or 0
    st.metric("TOTAL REVENUE (CASH)", f"₦{rev + card_rev:,}")
    st.dataframe(sales)

elif choice == "NOTIFICATIONS":
    st.table(pd.read_sql_query("SELECT timestamp, message FROM notifications ORDER BY id DESC", conn))
