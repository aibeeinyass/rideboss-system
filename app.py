import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import urllib.parse

# --- DATABASE SETUP ---
conn = sqlite3.connect('rideboss_ultra.db', check_same_thread=False)
c = conn.cursor()

# Tables setup
c.execute('''CREATE TABLE IF NOT EXISTS customers 
             (plate TEXT PRIMARY KEY, name TEXT, phone TEXT, visits INTEGER, last_visit TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS sales 
             (id INTEGER PRIMARY KEY, plate TEXT, services TEXT, total REAL, method TEXT, staff TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notifications 
             (id INTEGER PRIMARY KEY, message TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS live_bays 
             (plate TEXT PRIMARY KEY, status TEXT, entry_time TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS inventory 
             (item TEXT PRIMARY KEY, stock REAL, unit TEXT)''')
conn.commit()

# --- CONFIGURATION ---
MANAGER_PIN = "0000"
SERVICES = {"Standard Wash": 5000, "Executive Detail": 15000, "Engine Steam": 10000, "Ceramic Wax": 25000, "Interior Deep Clean": 12000}
STAFF_MEMBERS = ["Sunday", "Musa", "Chidi", "Ibrahim", "Tunde"]
COUNTRY_CODES = {"Nigeria": "+234", "Ghana": "+233", "UK": "+44", "USA": "+1", "UAE": "+971"}

# --- UI STYLING ---
st.set_page_config(page_title="RideBoss HQ", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #E0E0E0; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #0A0A0A; border-right: 1px solid #222; }
    .status-card { background: #0F0F0F; padding: 25px; border-radius: 2px; border-left: 4px solid #00d4ff; margin-bottom: 15px; border-top: 1px solid #1A1A1A; }
    .notification-bar { background: #00d4ff22; padding: 12px; border-bottom: 1px solid #00d4ff; color: #00d4ff; font-size: 0.85em; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 30px; }
    </style>
    """, unsafe_allow_html=True)

# --- UTILITIES ---
def add_event(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO notifications (message, timestamp) VALUES (?,?)", (msg, now))
    conn.commit()

def format_whatsapp(phone, message):
    return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"

# --- SIDEBAR & AUTH ---
st.sidebar.markdown("<h2 style='letter-spacing:4px;'>RIDEBOSS</h2>", unsafe_allow_html=True)
access_level = st.sidebar.selectbox("ACCESS LEVEL", ["STAFF", "MANAGER"])
authenticated = (access_level == "MANAGER" and st.sidebar.text_input("MANAGER PIN", type="password") == MANAGER_PIN)

menu = ["COMMAND CENTER", "LIVE U-FLOW", "LOGS"]
if authenticated:
    menu += ["INVENTORY & STAFF", "FINANCIALS", "CRM & RETENTION"]
choice = st.sidebar.radio("NAVIGATE", menu)

# --- NOTIFICATION BAR ---
latest_note = pd.read_sql_query("SELECT message FROM notifications ORDER BY id DESC LIMIT 1", conn)
st.markdown(f'<div class="notification-bar">LATEST: {latest_note["message"].iloc[0] if not latest_note.empty else "SYSTEM READY"}</div>', unsafe_allow_html=True)

# --- 1. COMMAND CENTER (INTELLIGENT RECEPTION) ---
if choice == "COMMAND CENTER":
    st.subheader("GATEWAY AUTHORIZATION")
    
    # Smart Search Logic
    all_custs = pd.read_sql_query("SELECT plate, name, phone FROM customers", conn)
    plate_list = ["NEW VEHICLE"] + all_custs['plate'].tolist()
    
    search_plate = st.selectbox("SEARCH EXISTING PLATE (Or select NEW)", plate_list)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pre-fill if existing customer
        if search_plate != "NEW VEHICLE":
            row = all_custs[all_custs['plate'] == search_plate].iloc[0]
            plate = st.text_input("PLATE NUMBER", value=row['plate']).upper()
            name = st.text_input("CLIENT NAME", value=row['name'])
            # Extract phone details for display
            phone_display = row['phone']
            st.info(f"Existing Client: {name} ({phone_display})")
            full_phone = phone_display # Keep original
        else:
            plate = st.text_input("PLATE NUMBER").upper()
            name = st.text_input("CLIENT NAME")
            c_code = st.selectbox("COUNTRY CODE", list(COUNTRY_CODES.keys()))
            phone_raw = st.text_input("PHONE (No leading zero)")
            full_phone = f"{COUNTRY_CODES[c_code].replace('+', '')}{phone_raw}"

    with col2:
        selected = st.multiselect("SERVICES", list(SERVICES.keys()))
        total_price = sum([SERVICES[s] for s in selected])
        staff_assigned = st.selectbox("ASSIGN DETAILER", STAFF_MEMBERS)
        st.markdown(f"### TOTAL: ₦{total_price:,}")
        pay_method = st.selectbox("PAYMENT METHOD", ["Moniepoint POS", "Bank Transfer", "Cash"])
        
        # Duplication Prevention Check
        confirm_gate = st.checkbox("I CONFIRM PAYMENT IS RECEIVED")

    if st.button("AUTHORIZE & LOG TRANSACTION", use_container_width=True, disabled=not confirm_gate):
        if plate and selected and name:
            now_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            # 1. Log Sale
            c.execute("INSERT INTO sales (plate, services, total, method, staff, timestamp) VALUES (?,?,?,?,?,?)", 
                      (plate, ", ".join(selected), total_price, pay_method, staff_assigned, now_ts))
            # 2. Update Customer (Ensures phone is stored/updated)
            c.execute("INSERT OR REPLACE INTO customers (plate, name, phone, visits, last_visit) VALUES (?, ?, ?, COALESCE((SELECT visits FROM customers WHERE plate=?), 0) + 1, ?)", 
                      (plate, name, full_phone, plate, now_ts.split()[0]))
            # 3. Add to Flow
            c.execute("INSERT OR REPLACE INTO live_bays (plate, status, entry_time) VALUES (?, ?, ?)", (plate, "WET BAY", now_ts))
            
            add_event(f"AUTHORIZED: {plate} by {staff_assigned}. Payment via {pay_method}.")
            conn.commit()
            st.toast(f"Success! {plate} registered.", icon="✅")
            st.success(f"TRANSACTION LOGGED. Car {plate} is now in Wet Bay.")
            st.rerun()

# --- 2. LIVE U-FLOW ---
elif choice == "LIVE U-FLOW":
    st.subheader("U-FLOW TRACKER")
    live_cars = pd.read_sql_query("SELECT * FROM live_bays", conn)
    if live_cars.empty:
        st.info("NO ACTIVE VEHICLES.")
    else:
        for idx, row in live_cars.iterrows():
            st.markdown(f'<div class="status-card">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2,2,1])
            c1.write(f"**{row['plate']}** | Entered: {row['entry_time']}")
            with c2:
                if row['status'] == "WET BAY":
                    if st.button(f"MOVE {row['plate']} TO DRY"):
                        c.execute("UPDATE live_bays SET status='DRY BAY' WHERE plate=?", (row['plate'],))
                        add_event(f"{row['plate']} moved to DRY BAY.")
                        conn.commit()
                        st.rerun()
            with c3:
                if st.button(f"FINISH {row['plate']}"):
                    c.execute("SELECT name, phone FROM customers WHERE plate=?", (row['plate'],))
                    cust = c.fetchone()
                    c.execute("DELETE FROM live_bays WHERE plate=?", (row['plate'],))
                    add_event(f"{row['plate']} wash completed.")
                    conn.commit()
                    msg = f"Hi {cust[0]}, your vehicle {row['plate']} is sparkling clean and ready for pickup at RideBoss! 🚀"
                    st.markdown(f"[NOTIFY CLIENT]({format_whatsapp(cust[1], msg)})")
            st.markdown("</div>", unsafe_allow_html=True)

# --- 3. LOGS (NOTIFICATION HISTORY) ---
elif choice == "LOGS":
    st.subheader("SYSTEM ACTIVITY LOG")
    logs = pd.read_sql_query("SELECT timestamp, message FROM notifications ORDER BY id DESC", conn)
    st.dataframe(logs, use_container_width=True)

# --- MANAGER TABS (FINANCIALS, ETC.) ---
elif choice == "FINANCIALS" and authenticated:
    st.subheader("FINANCIAL INTELLIGENCE")
    sales = pd.read_sql_query("SELECT * FROM sales", conn)
    st.metric("TOTAL REVENUE", f"₦{sales['total'].sum():,}")
    st.dataframe(sales)

elif choice == "INVENTORY & STAFF" and authenticated:
    st.subheader("STAFF & STOCK")
    staff_eff = pd.read_sql_query("SELECT staff, COUNT(*) as washes FROM sales GROUP BY staff", conn)
    st.bar_chart(staff_eff.set_index('staff'))
    
elif choice == "CRM & RETENTION" and authenticated:
    st.subheader("LOYALTY PORTAL")
    # CRM Logic stays same
