import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import urllib.parse

# --- DATABASE SETUP ---
conn = sqlite3.connect('rideboss_ultra.db', check_same_thread=False)
c = conn.cursor()

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
conn.commit()

# --- PRE-SEED DATA ---
c.execute("INSERT OR IGNORE INTO inventory VALUES ('Car Shampoo', 10.0, 'Gallons', 0), ('Coke', 50.0, 'Cans', 500), ('Water', 100.0, 'Bottles', 200)")
# Seed Wash Prices if table is empty
c.execute("SELECT COUNT(*) FROM wash_prices")
if c.fetchone()[0] == 0:
    initial_services = [("Standard Wash", 5000), ("Executive Detail", 15000), ("Engine Steam", 10000), ("Ceramic Wax", 25000), ("Interior Deep Clean", 12000)]
    c.executemany("INSERT INTO wash_prices VALUES (?,?)", initial_services)
conn.commit()

# --- SECURITY CONFIG ---
MANAGER_PIN = "0000"

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
    </style>
    """, unsafe_allow_html=True)

# --- UTILITIES ---
def add_event(msg):
    now = datetime.now().strftime("%H:%M:%S")
    c.execute("INSERT INTO notifications (message, timestamp) VALUES (?,?)", (f"{now} | {msg}", now))
    conn.commit()

def format_whatsapp(phone, message):
    return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"

# --- LOAD DYNAMIC CONFIG ---
wash_prices_df = pd.read_sql_query("SELECT * FROM wash_prices", conn)
SERVICES = dict(zip(wash_prices_df['service'], wash_prices_df['price']))
STAFF_MEMBERS = ["Sunday", "Musa", "Chidi", "Ibrahim", "Tunde"]
COUNTRY_CODES = {"Nigeria": "+234", "Ghana": "+233", "UK": "+44", "USA": "+1", "UAE": "+971"}

# --- SIDEBAR & AUTHENTICATION ---
st.sidebar.markdown("<h2 style='letter-spacing:4px;'>RIDEBOSS</h2>", unsafe_allow_html=True)
access_level = st.sidebar.selectbox("ACCESS LEVEL", ["STAFF", "MANAGER"])
authenticated = False
if access_level == "MANAGER":
    pin = st.sidebar.text_input("MANAGER PIN", type="password")
    if pin == MANAGER_PIN:
        authenticated = True
        st.sidebar.success("SECURE ACCESS GRANTED")

menu = ["COMMAND CENTER", "LIVE U-FLOW", "NOTIFICATIONS"]
if authenticated: menu += ["INVENTORY & STAFF", "FINANCIALS", "CRM & RETENTION"]
choice = st.sidebar.radio("NAVIGATE", menu)

# --- TOP NOTIFICATION FEED ---
latest_note = pd.read_sql_query("SELECT message FROM notifications ORDER BY id DESC LIMIT 1", conn)
st.markdown(f'<div class="notification-bar">SYSTEM LOG: {latest_note["message"].iloc[0] if not latest_note.empty else "READY"}</div>', unsafe_allow_html=True)

# --- 1. COMMAND CENTER ---
if choice == "COMMAND CENTER":
    mode = st.radio("SELECT MODE", ["CAR WASH", "LOUNGE"], horizontal=True)
    st.markdown("---")
    cust_data = pd.read_sql_query("SELECT * FROM customers", conn)
    search_options = ["NEW CUSTOMER"] + [f"{r['plate']} - {r['name']} ({r['phone']})" for _, r in cust_data.iterrows()]
    search_selection = st.selectbox("SEARCH EXISTING CLIENT (Plate/Name/Phone)", search_options)
    
    default_plate, default_name, default_phone = "", "", ""
    if search_selection != "NEW CUSTOMER":
        p_key = search_selection.split(" - ")[0]
        match = cust_data[cust_data['plate'] == p_key].iloc[0]
        default_plate, default_name, default_phone = match['plate'], match['name'], match['phone']

    col1, col2 = st.columns(2)
    with col1:
        plate = st.text_input("PLATE NUMBER", value=default_plate).upper()
        name = st.text_input("CLIENT NAME", value=default_name)
        c_code = st.selectbox("COUNTRY CODE", list(COUNTRY_CODES.keys()))
        phone_raw = st.text_input("PHONE (No leading zero)", value=default_phone[3:] if default_phone else "")
        full_phone = f"{COUNTRY_CODES[c_code].replace('+', '')}{phone_raw}" if not default_phone else default_phone

    with col2:
        if mode == "CAR WASH":
            selected = st.multiselect("SERVICES", list(SERVICES.keys()))
            total_price = sum([SERVICES[s] for s in selected])
            staff_assigned = st.selectbox("ASSIGN DETAILER", STAFF_MEMBERS)
        else:
            inv_items = pd.read_sql_query("SELECT item, price FROM inventory WHERE price > 0", conn)
            items_list = st.multiselect("SELECT ITEMS", inv_items['item'].tolist())
            total_price = inv_items[inv_items['item'].isin(items_list)]['price'].sum()
            staff_assigned = st.selectbox("SERVER", STAFF_MEMBERS)
            selected = items_list

        st.markdown(f"### TOTAL: ₦{total_price:,}")
        pay_method = st.selectbox("PAYMENT METHOD", ["Moniepoint POS", "Bank Transfer", "Cash"])

    if st.button(f"AUTHORIZE {mode} TRANSACTION", use_container_width=True):
        if (plate or mode == "LOUNGE") and selected:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute("INSERT INTO sales (plate, services, total, method, staff, timestamp, type) VALUES (?,?,?,?,?,?,?)", 
                      (plate, ", ".join(selected), total_price, pay_method, staff_assigned, now, mode))
            c.execute("INSERT OR REPLACE INTO customers (plate, name, phone, visits, last_visit) VALUES (?, ?, ?, COALESCE((SELECT visits FROM customers WHERE plate=?), 0) + 1, ?)", (plate, name, full_phone, plate, now.split()[0]))
            if mode == "CAR WASH":
                c.execute("INSERT OR REPLACE INTO live_bays (plate, status, entry_time) VALUES (?, ?, ?)", (plate, "WET BAY", now))
                add_event(f"WASH AUTH: {plate} via {pay_method}")
            else:
                for item in selected: c.execute("UPDATE inventory SET stock = stock - 1 WHERE item = ?", (item,))
                add_event(f"LOUNGE SALE: {', '.join(selected)}")
            conn.commit(); st.success("✅ Transaction Logged."); st.balloons(); st.rerun()

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
                    msg = f"Dear {cust[0]}, your vehicle {row['plate']} is ready at RideBoss Autos."
                    st.markdown(f"[:speech_balloon: WHATSAPP]({format_whatsapp(cust[1], msg)})")
            st.markdown('</div>', unsafe_allow_html=True)

# --- 3. NOTIFICATIONS TAB ---
elif choice == "NOTIFICATIONS":
    st.subheader("SYSTEM NOTIFICATION HISTORY")
    notes = pd.read_sql_query("SELECT timestamp as 'TIME', message as 'EVENT' FROM notifications ORDER BY id DESC", conn)
    st.table(notes)

# --- 4. INVENTORY & STAFF (MANAGER) ---
elif choice == "INVENTORY & STAFF" and authenticated:
    t1, t2, t3 = st.tabs(["Lounge Inventory", "Wash Price List", "Staff Performance"])
    with t1:
        st.write("ADD OR UPDATE LOUNGE PRODUCTS")
        with st.form("new_item"):
            ni_name = st.text_input("Item Name")
            ni_stock = st.number_input("Stock", min_value=0.0)
            ni_unit = st.text_input("Unit (e.g. Cans)")
            ni_price = st.number_input("Sales Price (₦)", min_value=0.0)
            if st.form_submit_button("ADD/UPDATE PRODUCT"):
                c.execute("INSERT OR REPLACE INTO inventory VALUES (?,?,?,?)", (ni_name, ni_stock, ni_unit, ni_price))
                conn.commit(); add_event(f"INV UPDATE: {ni_name}"); st.rerun()
        inv_df = pd.read_sql_query("SELECT * FROM inventory", conn)
        st.dataframe(inv_df, use_container_width=True)

    with t2:
        st.write("UPDATE CAR WASH SERVICE PRICES")
        edit_svc = st.selectbox("Select Service to Update", list(SERVICES.keys()))
        new_svc_price = st.number_input("New Price (₦)", min_value=0.0, value=SERVICES[edit_svc])
        if st.button("UPDATE WASH PRICE"):
            c.execute("UPDATE wash_prices SET price=? WHERE service=?", (new_svc_price, edit_svc))
            conn.commit(); add_event(f"PRICE UPDATE: {edit_svc}"); st.rerun()
    
    with t3:
        staff_data = pd.read_sql_query("SELECT staff, COUNT(*) as washes FROM sales GROUP BY staff", conn)
        st.bar_chart(staff_data.set_index('staff'))

# --- 5. FINANCIALS (MANAGER) ---
elif choice == "FINANCIALS" and authenticated:
    st.subheader("PROFIT & LOSS TRACKER")
    sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
    exp_df = pd.read_sql_query("SELECT * FROM expenses", conn)
    
    rev = sales_df['total'].sum() if not sales_df.empty else 0
    exps = exp_df['amount'].sum() if not exp_df.empty else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("GROSS REVENUE", f"₦{rev:,}")
    col2.metric("TOTAL EXPENSES", f"₦{exps:,}", delta_color="inverse")
    col3.metric("NET PROFIT", f"₦{rev-exps:,}")
    
    st.markdown("---")
    with st.expander("LOG NEW EXPENSE"):
        e_desc = st.text_input("Description (e.g. Diesel, Staff Lunch)")
        e_amt = st.number_input("Amount (₦)", min_value=0.0)
        if st.button("LOG EXPENSE"):
            c.execute("INSERT INTO expenses (description, amount, timestamp) VALUES (?,?,?)", (e_desc, e_amt, datetime.now().strftime("%Y-%m-%d")))
            conn.commit(); add_event(f"EXPENSE: {e_desc}"); st.rerun()
    
    st.write("TRANSACTION LOG")
    st.dataframe(sales_df, use_container_width=True)

# --- 6. CRM & RETENTION (MANAGER) ---
elif choice == "CRM & RETENTION" and authenticated:
    st.subheader("RETENTION INTELLIGENCE")
    cust_df = pd.read_sql_query("SELECT * FROM customers", conn)
    if not cust_df.empty:
        for idx, row in cust_df.iterrows():
            last_v = datetime.strptime(row['last_visit'], "%Y-%m-%d")
            days_away = (datetime.now() - last_v).days
            color = "#00d4ff" if days_away < 14 else "#FF3B30"
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"<span style='color:{color};'>**{row['name']}** ({row['plate']}) — {days_away} days away</span>", unsafe_allow_html=True)
            if days_away >= 14:
                msg = f"Hi {row['name']}, we missed you at RideBoss! Your car {row['plate']} is due for a wash."
                c2.markdown(f"[RECALL]({format_whatsapp(row['phone'], msg)})")
