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
             (id INTEGER PRIMARY KEY, plate TEXT, services TEXT, total REAL, method TEXT, staff TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notifications 
             (id INTEGER PRIMARY KEY, message TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS live_bays 
             (plate TEXT PRIMARY KEY, status TEXT, entry_time TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS inventory 
             (item TEXT PRIMARY KEY, stock REAL, unit TEXT)''')
conn.commit()

# --- PRE-SEED INVENTORY ---
c.execute("INSERT OR IGNORE INTO inventory VALUES ('Car Shampoo', 10.0, 'Gallons'), ('Ceramic Wax', 5.0, 'Tubs'), ('Tire Shine', 8.0, 'Liters')")
conn.commit()

# --- SECURITY CONFIG ---
MANAGER_PIN = "0000"  # <--- CHANGE YOUR PIN HERE

# --- CONFIGURATION ---
SERVICES = {
    "Standard Wash": 5000,
    "Executive Detail": 15000,
    "Engine Steam": 10000,
    "Ceramic Wax": 25000,
    "Interior Deep Clean": 12000
}
STAFF_MEMBERS = ["Sunday", "Musa", "Chidi", "Ibrahim", "Tunde"]
COUNTRY_CODES = {"Nigeria": "+234", "Ghana": "+233", "UK": "+44", "USA": "+1", "UAE": "+971"}

# --- CLASSIC UI STYLING ---
st.set_page_config(page_title="RideBoss Autos HQ", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #E0E0E0; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #0A0A0A; border-right: 1px solid #222; }
    .status-card { background: #0F0F0F; padding: 25px; border-radius: 2px; border-left: 4px solid #00d4ff; margin-bottom: 15px; border-top: 1px solid #1A1A1A; }
    .notification-bar { background: #00d4ff22; padding: 12px; border-radius: 0px; border-bottom: 1px solid #00d4ff; color: #00d4ff; font-size: 0.85em; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 30px; }
    .stButton>button { border-radius: 0px; letter-spacing: 2px; font-size: 0.8em; text-transform: uppercase; background-color: transparent; border: 1px solid #333; color: white; height: 3em; transition: 0.4s; width: 100%; }
    .stButton>button:hover { border-color: #00d4ff; color: #00d4ff; background-color: #00d4ff11; }
    .metric-val { color: #00d4ff; font-size: 24px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- UTILITIES ---
def add_event(msg):
    now = datetime.now().strftime("%H:%M:%S")
    c.execute("INSERT INTO notifications (message, timestamp) VALUES (?,?)", (f"{now} | {msg}", now))
    conn.commit()

def format_whatsapp(phone, message):
    encoded_msg = urllib.parse.quote(message)
    return f"https://wa.me/{phone}?text={encoded_msg}"

# --- SIDEBAR & AUTHENTICATION ---
st.sidebar.markdown("<h2 style='letter-spacing:4px;'>RIDEBOSS</h2>", unsafe_allow_html=True)

access_level = st.sidebar.selectbox("ACCESS LEVEL", ["STAFF", "MANAGER"])
authenticated = False

if access_level == "MANAGER":
    pin = st.sidebar.text_input("MANAGER PIN", type="password")
    if pin == MANAGER_PIN:
        authenticated = True
        st.sidebar.success("SECURE ACCESS GRANTED")
    elif pin:
        st.sidebar.error("INVALID PIN")

# Define menu based on access
if authenticated:
    menu = ["COMMAND CENTER", "LIVE U-FLOW", "INVENTORY & STAFF", "FINANCIALS", "CRM & RETENTION"]
else:
    menu = ["COMMAND CENTER", "LIVE U-FLOW"]

choice = st.sidebar.radio("NAVIGATE", menu)

# --- TOP NOTIFICATION FEED ---
latest_note = pd.read_sql_query("SELECT message FROM notifications ORDER BY id DESC LIMIT 1", conn)
st.markdown(f'<div class="notification-bar">SYSTEM LOG: {latest_note["message"].iloc[0] if not latest_note.empty else "READY FOR AUTHORIZATION"}</div>', unsafe_allow_html=True)

# --- 1. COMMAND CENTER (RECEPTION) ---
if choice == "COMMAND CENTER":
    st.subheader("GATEWAY AUTHORIZATION")
    col1, col2 = st.columns(2)
    
    with col1:
        plate = st.text_input("PLATE NUMBER").upper()
        name = st.text_input("CLIENT NAME")
        c_code = st.selectbox("COUNTRY CODE", list(COUNTRY_CODES.keys()), index=0)
        phone_raw = st.text_input("PHONE NUMBER (Without leading zero)")
        full_phone = f"{COUNTRY_CODES[c_code].replace('+', '')}{phone_raw}"

    with col2:
        selected = st.multiselect("SERVICES", list(SERVICES.keys()))
        total_price = sum([SERVICES[s] for s in selected])
        staff_assigned = st.selectbox("ASSIGN DETAILER", STAFF_MEMBERS)
        st.markdown(f"### VALUATION: ₦{total_price:,}")
        pay_method = st.selectbox("PAYMENT METHOD", ["Moniepoint POS", "Bank Transfer", "Cash"])

    if st.button("AUTHORIZE TRANSACTION", use_container_width=True):
        if plate and selected and phone_raw:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute("INSERT INTO sales (plate, services, total, method, staff, timestamp) VALUES (?,?,?,?,?,?)", (plate, ", ".join(selected), total_price, pay_method, staff_assigned, now))
            c.execute("INSERT OR REPLACE INTO customers (plate, name, phone, visits, last_visit) VALUES (?, ?, ?, COALESCE((SELECT visits FROM customers WHERE plate=?), 0) + 1, ?)", (plate, name, full_phone, plate, now.split()[0]))
            c.execute("INSERT OR REPLACE INTO live_bays (plate, status, entry_time) VALUES (?, ?, ?)", (plate, "WET BAY", now))
            add_event(f"TRANSACTION AUTHORIZED: {plate} MOVED TO WET BAY. HANDLED BY {staff_assigned.upper()}.")
            conn.commit()
            st.success("ACCESS GRANTED.")
            st.rerun()

# --- 2. LIVE U-FLOW TRACKER ---
elif choice == "LIVE U-FLOW":
    st.subheader("U-FLOW STATUS")
    live_cars = pd.read_sql_query("SELECT * FROM live_bays", conn)
    
    if live_cars.empty:
        st.info("NO ACTIVE VEHICLES IN U-FLOW.")
    else:
        for index, row in live_cars.iterrows():
            st.markdown(f'<div class="status-card">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.markdown(f"**VEHICLE:** {row['plate']}")
            c1.caption(f"ZONE: {row['status']}")
            
            with c2:
                if row['status'] == "WET BAY":
                    if st.button(f"TRANSIT {row['plate']} TO DRY"):
                        c.execute("UPDATE live_bays SET status='DRY BAY' WHERE plate=?", (row['plate'],))
                        add_event(f"VEHICLE {row['plate']} TRANSITIONED TO DETAILING ZONE.")
                        conn.commit()
                        st.rerun()
            with c3:
                if st.button(f"RELEASE {row['plate']}"):
                    c.execute("SELECT name, phone FROM customers WHERE plate=?", (row['plate'],))
                    cust = c.fetchone()
                    c.execute("DELETE FROM live_bays WHERE plate=?", (row['plate'],))
                    add_event(f"SERVICE FINALIZED: {row['plate']} READY FOR RELEASE.")
                    conn.commit()
                    
                    ready_msg = f"Dear {cust[0]}, your vehicle ({row['plate']}) is ready at RideBoss Autos. Thank you."
                    st.markdown(f"[NOTIFY CLIENT VIA WHATSAPP]({format_whatsapp(cust[1], ready_msg)})")
            st.markdown('</div>', unsafe_allow_html=True)

# --- 3. INVENTORY & STAFF (MANAGER ONLY) ---
elif choice == "INVENTORY & STAFF" and authenticated:
    st.subheader("RESOURCE ALLOCATION")
    col1, col2 = st.columns(2)
    with col1:
        st.write("INVENTORY LEVELS")
        inv_df = pd.read_sql_query("SELECT * FROM inventory", conn)
        st.table(inv_df)
        item_to_update = st.selectbox("UPDATE ITEM", inv_df['item'].tolist())
        new_qty = st.number_input("NEW STOCK LEVEL", min_value=0.0)
        if st.button("CALIBRATE STOCK"):
            c.execute("UPDATE inventory SET stock=? WHERE item=?", (new_qty, item_to_update))
            conn.commit()
            add_event(f"INVENTORY CALIBRATED: {item_to_update.upper()}")
            st.rerun()
    with col2:
        st.write("STAFF PERFORMANCE")
        staff_data = pd.read_sql_query("SELECT staff, COUNT(*) as washes FROM sales GROUP BY staff", conn)
        if not staff_data.empty:
            st.bar_chart(staff_data.set_index('staff'))

# --- 4. FINANCIALS (MANAGER ONLY) ---
elif choice == "FINANCIALS" and authenticated:
    st.subheader("FINANCIAL INTELLIGENCE")
    sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
    if not sales_df.empty:
        total_rev = sales_df['total'].sum()
        st.metric("TOTAL GROSS REVENUE", f"₦{total_rev:,.2f}")
        st.write("TRANSACTION LOG")
        st.dataframe(sales_df, use_container_width=True)
    else:
        st.info("NO SALES DATA RECORDED.")

# --- 5. CRM & RETENTION (MANAGER ONLY) ---
elif choice == "CRM & RETENTION" and authenticated:
    st.subheader("RETENTION INTELLIGENCE")
    cust_df = pd.read_sql_query("SELECT * FROM customers", conn)
    
    for index, row in cust_df.iterrows():
        last_date = datetime.strptime(row['last_visit'], "%Y-%m-%d")
        days_away = (datetime.now() - last_date).days
        
        col_x, col_y = st.columns([3, 1])
        with col_x:
            color = "#00d4ff" if days_away < 14 else "#FF3B30"
            st.markdown(f"<span style='color:{color}; letter-spacing:1px;'>**{row['name']}** ({row['plate']}) | LAST SEEN: {days_away} DAYS AGO</span>", unsafe_allow_html=True)
        
        with col_y:
            if days_away >= 14:
                recall_msg = f"Dear {row['name']}, we missed you at RideBoss Autos! It has been {days_away} days since your last visit. We've reserved a VIP slot for you."
                st.markdown(f"[SEND RECALL]({format_whatsapp(row['phone'], recall_msg)})")