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
conn.commit()

# --- PRE-SEED INVENTORY (Updated with Prices) ---
c.execute("INSERT OR IGNORE INTO inventory VALUES ('Car Shampoo', 10.0, 'Gallons', 0), ('Ceramic Wax', 5.0, 'Tubs', 0), ('Coke', 50.0, 'Cans', 500), ('Water', 100.0, 'Bottles', 200), ('Club Sandwich', 20.0, 'Units', 3500)")
conn.commit()

# --- SECURITY CONFIG ---
MANAGER_PIN = "0000"

# --- CONFIGURATION ---
SERVICES = {"Standard Wash": 5000, "Executive Detail": 15000, "Engine Steam": 10000, "Ceramic Wax": 25000, "Interior Deep Clean": 12000}
STAFF_MEMBERS = ["Sunday", "Musa", "Chidi", "Ibrahim", "Tunde"]
COUNTRY_CODES = {"Nigeria": "+234", "Ghana": "+233", "UK": "+44", "USA": "+1", "UAE": "+971"}

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
    
    # SMART SEARCH LOGIC
    cust_data = pd.read_sql_query("SELECT * FROM customers", conn)
    search_options = ["NEW CUSTOMER"] + [f"{r['plate']} - {r['name']} ({r['phone']})" for _, r in cust_data.iterrows()]
    search_selection = st.selectbox("SEARCH EXISTING CLIENT (Plate/Name/Phone)", search_options)
    
    # Auto-fill variables
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
            # Log Sale
            c.execute("INSERT INTO sales (plate, services, total, method, staff, timestamp, type) VALUES (?,?,?,?,?,?,?)", 
                      (plate, ", ".join(selected), total_price, pay_method, staff_assigned, now, mode))
            # Register/Update Customer
            c.execute("INSERT OR REPLACE INTO customers (plate, name, phone, visits, last_visit) VALUES (?, ?, ?, COALESCE((SELECT visits FROM customers WHERE plate=?), 0) + 1, ?)", (plate, name, full_phone, plate, now.split()[0]))
            
            if mode == "CAR WASH":
                c.execute("INSERT OR REPLACE INTO live_bays (plate, status, entry_time) VALUES (?, ?, ?)", (plate, "WET BAY", now))
                add_event(f"WASH AUTH: {plate} MOVED TO WET BAY via {pay_method}")
            else:
                # Update Inventory for lounge
                for item in selected:
                    c.execute("UPDATE inventory SET stock = stock - 1 WHERE item = ?", (item,))
                add_event(f"LOUNGE SALE: {', '.join(selected)} sold by {staff_assigned}")
            
            conn.commit()
            st.success(f"✅ CONFIRMED: {mode} Transaction Logged Successfully.")
            st.balloons()
            st.rerun()

# --- 2. LIVE U-FLOW ---
elif choice == "LIVE U-FLOW":
    st.subheader("ACTIVE WASH BAYS")
    live_cars = pd.read_sql_query("SELECT * FROM live_bays", conn)
    if live_cars.empty: st.info("ALL BAYS CLEAR.")
    else:
        for index, row in live_cars.iterrows():
            st.markdown('<div class="status-card">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.write(f"**{row['plate']}** | ZONE: {row['status']}")
            with c2:
                if row['status'] == "WET BAY":
                    if st.button(f"TRANSIT {row['plate']} TO DRY"):
                        c.execute("UPDATE live_bays SET status='DRY BAY' WHERE plate=?", (row['plate'],))
                        add_event(f"{row['plate']} MOVED TO DRY.")
                        conn.commit(); st.rerun()
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
    st.subheader("RESOURCES")
    inv_df = pd.read_sql_query("SELECT item, stock, unit, price FROM inventory", conn)
    st.dataframe(inv_df, use_container_width=True)
    # Update logic preserved...
    staff_data = pd.read_sql_query("SELECT staff, COUNT(*) as washes FROM sales GROUP BY staff", conn)
    st.bar_chart(staff_data.set_index('staff'))

# --- 5. FINANCIALS (MANAGER) ---
elif choice == "FINANCIALS" and authenticated:
    st.subheader("REVENUE ANALYTICS")
    sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
    if not sales_df.empty:
        col1, col2 = st.columns(2)
        col1.metric("WASH REVENUE", f"₦{sales_df[sales_df['type']=='CAR WASH']['total'].sum():,}")
        col2.metric("LOUNGE REVENUE", f"₦{sales_df[sales_df['type']=='LOUNGE']['total'].sum():,}")
        st.write("DETAILED TRANSACTION LOG")
        st.dataframe(sales_df)
