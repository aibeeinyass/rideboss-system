import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import urllib.parse

# --- DATABASE SETUP ---
conn = sqlite3.connect('rideboss_ultra.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS customers (plate TEXT PRIMARY KEY, name TEXT, phone TEXT, visits INTEGER, last_visit TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, plate TEXT, services TEXT, total REAL, method TEXT, staff TEXT, timestamp TEXT, type TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY, message TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS live_bays (plate TEXT PRIMARY KEY, status TEXT, entry_time TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS inventory (item TEXT PRIMARY KEY, stock REAL, unit TEXT, price REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS wash_prices (service TEXT PRIMARY KEY, price REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, description TEXT, amount REAL, timestamp TEXT)''')
conn.commit()

# --- PRE-SEED ADMIN ---
c.execute("INSERT OR IGNORE INTO users VALUES ('admin', '0000', 'MANAGER')")
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
    
    /* CLASSIC RECEIPT DESIGN */
    .receipt-container { background: white; color: #1a1a1a; padding: 40px; border: 1px solid #ddd; font-family: 'Courier New', monospace; max-width: 450px; margin: auto; }
    .receipt-header { text-align: center; border-bottom: 2px solid #1a1a1a; margin-bottom: 20px; }
    .receipt-row { display: flex; justify-content: space-between; margin: 8px 0; }
    .stamp-official { color: #8b0000; border: 2px solid #8b0000; padding: 5px; display: inline-block; font-weight: bold; transform: rotate(-5deg); margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- UTILITIES ---
def add_event(msg):
    now = datetime.now().strftime("%H:%M:%S")
    c.execute("INSERT INTO notifications (message, timestamp) VALUES (?,?)", (f"{now} | {msg}", now))
    conn.commit()

def format_whatsapp(phone, message):
    return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"

# --- LOGIN SESSION ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'role' not in st.session_state: st.session_state.role = None
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.auth:
    st.markdown("<h1 style='text-align:center;'>RIDEBOSS SECURE ACCESS</h1>", unsafe_allow_html=True)
    with st.container():
        _, log_col, _ = st.columns([1,1,1])
        with log_col:
            u_in = st.text_input("Username")
            p_in = st.text_input("Password", type="password")
            if st.button("LOGIN"):
                c.execute("SELECT role FROM users WHERE username=? AND password=?", (u_in, p_in))
                res = c.fetchone()
                if res:
                    st.session_state.auth = True
                    st.session_state.role = res[0]
                    st.session_state.user = u_in
                    st.rerun()
                else: st.error("Access Denied")
    st.stop()

# --- LOAD APP DATA ---
wash_prices_df = pd.read_sql_query("SELECT * FROM wash_prices", conn)
SERVICES = dict(zip(wash_prices_df['service'], wash_prices_df['price']))
staff_query = pd.read_sql_query("SELECT username FROM users", conn)
STAFF_LIST = staff_query['username'].tolist()

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown(f"**ACTIVE SESSION:** {st.session_state.user}")
menu = ["COMMAND CENTER", "LIVE U-FLOW", "NOTIFICATIONS"]
if st.session_state.role == "MANAGER":
    menu += ["ONBOARD STAFF", "INVENTORY & STAFF", "FINANCIALS", "CRM & RETENTION"]

choice = st.sidebar.radio("NAVIGATE", menu)
if st.sidebar.button("LOGOUT"):
    st.session_state.auth = False
    st.rerun()

# --- 1. COMMAND CENTER ---
if choice == "COMMAND CENTER":
    mode = st.radio("MODE", ["CAR WASH", "LOUNGE"], horizontal=True)
    cust_data = pd.read_sql_query("SELECT * FROM customers", conn)
    search_options = ["NEW CUSTOMER"] + [f"{r['plate']} - {r['name']}" for _, r in cust_data.iterrows()]
    search_selection = st.selectbox("SEARCH CLIENT", search_options)
    
    d_plate, d_name, d_phone = "", "", ""
    if search_selection != "NEW CUSTOMER":
        p_key = search_selection.split(" - ")[0]
        match = cust_data[cust_data['plate'] == p_key].iloc[0]
        d_plate, d_name, d_phone = match['plate'], match['name'], match['phone']

    col1, col2 = st.columns(2)
    with col1:
        plate = st.text_input("PLATE", value=d_plate).upper()
        name = st.text_input("NAME", value=d_name)
        phone = st.text_input("PHONE (234...)", value=d_phone if d_phone else "234")

    with col2:
        lounge_items = []
        if mode == "CAR WASH":
            selected = st.multiselect("SERVICES", list(SERVICES.keys()))
            total_price = sum([SERVICES[s] for s in selected])
            staff_assigned = st.selectbox("ASSIGN DETAILER", STAFF_LIST)
            item_summary = ", ".join(selected)
        else:
            inv_items = pd.read_sql_query("SELECT item, price FROM inventory WHERE price > 0", conn)
            items_list = st.multiselect("ITEMS", inv_items['item'].tolist())
            total_price = 0
            for item in items_list:
                u_price = inv_items[inv_items['item'] == item]['price'].values[0]
                qty = st.number_input(f"Qty: {item}", min_value=1)
                total_price += (u_price * qty)
                lounge_items.append((item, qty))
            staff_assigned = st.selectbox("SERVER", STAFF_LIST)
            item_summary = ", ".join([f"{i} (x{q})" for i, q in lounge_items])

        st.markdown(f"### TOTAL: ₦{total_price:,}")
        pay_method = st.selectbox("PAYMENT", ["POS", "Transfer", "Cash"])

    if st.button("AUTHORIZE & LOG"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        c.execute("INSERT INTO sales (plate, services, total, method, staff, timestamp, type) VALUES (?,?,?,?,?,?,?)", 
                  (plate, item_summary, total_price, pay_method, staff_assigned, now, mode))
        c.execute("INSERT OR REPLACE INTO customers (plate, name, phone, visits, last_visit) VALUES (?,?,?,COALESCE((SELECT visits FROM customers WHERE plate=?),0)+1,?)", (plate, name, phone, plate, now.split()[0]))
        if mode == "CAR WASH": c.execute("INSERT OR REPLACE INTO live_bays VALUES (?,?,?)", (plate, "WET BAY", now))
        else:
            for itm, q in lounge_items: c.execute("UPDATE inventory SET stock=stock-? WHERE item=?", (q, itm))
        conn.commit()
        st.session_state['last_receipt'] = {"id": c.lastrowid, "name": name, "plate": plate, "items": item_summary, "total": total_price, "staff": staff_assigned, "date": now}
        st.rerun()

    if 'last_receipt' in st.session_state:
        r = st.session_state['last_receipt']
        st.markdown(f"""
        <div class="receipt-container">
            <div class="receipt-header">
                <h1 style="letter-spacing:5px;">RIDEBOSS</h1>
                <p>Premium Autos & Lounge<br>Tel: 09029557912</p>
            </div>
            <div class="receipt-row"><span>ID: #RB{r['id']}</span> <span>{r['date']}</span></div>
            <hr>
            <p><b>Client:</b> {r['name']} ({r['plate']})</p>
            <p><b>Service:</b> {r['items']}</p>
            <div class="receipt-row" style="font-size:1.4em; font-weight:bold;"><span>TOTAL:</span> <span>₦{r['total']:,}</span></div>
            <p><b>Staff:</b> {r['staff']}</p>
            <div class="receipt-footer"><div class="stamp-official">RIDEBOSS VERIFIED</div></div>
        </div>""", unsafe_allow_html=True)
        if st.button("PRINT RECEIPT"): st.markdown('<script>window.print();</script>', unsafe_allow_html=True)

# --- 2. LIVE U-FLOW ---
elif choice == "LIVE U-FLOW":
    st.subheader("WASH BAYS")
    live = pd.read_sql_query("SELECT * FROM live_bays", conn)
    for idx, row in live.iterrows():
        st.markdown(f'<div class="status-card">{row["plate"]} | {row["status"]}</div>', unsafe_allow_html=True)
        if st.button(f"Release {row['plate']}"):
            c.execute("DELETE FROM live_bays WHERE plate=?", (row['plate'],))
            conn.commit(); st.rerun()

# --- 3. ONBOARD STAFF ---
elif choice == "ONBOARD STAFF":
    with st.form("ob"):
        u = st.text_input("Username")
        p = st.text_input("Password")
        r = st.selectbox("Role", ["STAFF", "MANAGER"])
        if st.form_submit_button("ADD TEAM MEMBER"):
            c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)", (u, p, r))
            conn.commit(); st.success("Onboarded"); st.rerun()

# --- 4. FINANCIALS ---
elif choice == "FINANCIALS":
    df = pd.read_sql_query("SELECT * FROM sales", conn)
    st.metric("TOTAL REVENUE", f"₦{df['total'].sum():,}")
    st.dataframe(df)

# --- 5. CRM & RETENTION ---
elif choice == "CRM & RETENTION":
    cust = pd.read_sql_query("SELECT * FROM customers", conn)
    st.write("Customer Database")
    st.table(cust)

# --- 6. NOTIFICATIONS ---
elif choice == "NOTIFICATIONS":
    notes = pd.read_sql_query("SELECT * FROM notifications ORDER BY id DESC", conn)
    st.table(notes)
