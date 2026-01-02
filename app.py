import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import urllib.parse

# --- DATABASE SETUP ---
conn = sqlite3.connect('rideboss_ultra.db', check_same_thread=False)
c = conn.cursor()

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
    .receipt-container { background: white; color: #1a1a1a; padding: 40px; border: 1px solid #ddd; font-family: 'Garamond', serif; max-width: 500px; margin: auto; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .receipt-header { text-align: center; border-bottom: 2px solid #1a1a1a; margin-bottom: 20px; }
    .receipt-header h1 { letter-spacing: 8px; font-weight: 900; margin-bottom: 5px; }
    .receipt-row { display: flex; justify-content: space-between; margin: 10px 0; font-size: 1.1em; }
    .receipt-footer { text-align: center; border-top: 1px solid #eee; margin-top: 30px; padding-top: 20px; font-style: italic; }
    .stamp-official { color: #8b0000; border: 2px solid #8b0000; padding: 5px 15px; display: inline-block; font-weight: bold; text-transform: uppercase; transform: rotate(-5deg); margin-top: 15px; }
    
    @media print { .no-print { display: none !important; } .receipt-container { border: none; box-shadow: none; } }
    </style>
    """, unsafe_allow_html=True)

# --- UTILITIES ---
def add_event(msg):
    now = datetime.now().strftime("%H:%M:%S")
    c.execute("INSERT INTO notifications (message, timestamp) VALUES (?,?)", (f"{now} | {msg}", now))
    conn.commit()

# --- LOGIN LOGIC ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['user_role'] = None
    st.session_state['user_name'] = None

if not st.session_state['authenticated']:
    st.markdown("<h1 style='text-align:center; letter-spacing:10px;'>RIDEBOSS LOGIN</h1>", unsafe_allow_html=True)
    with st.container():
        _, log_col, _ = st.columns([1,1,1])
        with log_col:
            user_in = st.text_input("Username")
            pass_in = st.text_input("Password", type="password")
            if st.button("ENTER SYSTEM"):
                c.execute("SELECT role FROM users WHERE username=? AND password=?", (user_in, pass_in))
                res = c.fetchone()
                if res:
                    st.session_state['authenticated'] = True
                    st.session_state['user_role'] = res[0]
                    st.session_state['user_name'] = user_in
                    st.rerun()
                else: st.error("Invalid Credentials")
    st.stop()

# --- LOAD DYNAMIC STAFF & PRICES ---
wash_prices_df = pd.read_sql_query("SELECT * FROM wash_prices", conn)
SERVICES = dict(zip(wash_prices_df['service'], wash_prices_df['price']))
staff_query = pd.read_sql_query("SELECT username FROM users", conn)
STAFF_MEMBERS = staff_query['username'].tolist()
COUNTRY_CODES = {"Nigeria": "+234", "Ghana": "+233", "UK": "+44", "USA": "+1"}

# --- NAVIGATION ---
st.sidebar.markdown(f"User: **{st.session_state['user_name']}**")
menu = ["COMMAND CENTER", "LIVE U-FLOW", "NOTIFICATIONS"]
if st.session_state['user_role'] == "MANAGER":
    menu += ["ONBOARD STAFF", "INVENTORY & STAFF", "FINANCIALS", "CRM & RETENTION"]

choice = st.sidebar.radio("NAVIGATE", menu)
if st.sidebar.button("LOGOUT"):
    st.session_state['authenticated'] = False
    st.rerun()

# --- 1. COMMAND CENTER ---
if choice == "COMMAND CENTER":
    mode = st.radio("SELECT MODE", ["CAR WASH", "LOUNGE"], horizontal=True)
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
        phone_raw = st.text_input("PHONE", value=d_phone[3:] if d_phone else "")
        full_phone = f"234{phone_raw}" # Nigeria default

    with col2:
        lounge_items = []
        if mode == "CAR WASH":
            selected = st.multiselect("SERVICES", list(SERVICES.keys()))
            total_price = sum([SERVICES[s] for s in selected])
            staff_assigned = st.selectbox("DETAILER", STAFF_MEMBERS)
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
            staff_assigned = st.selectbox("SERVER", STAFF_MEMBERS)
            item_summary = ", ".join([f"{i} (x{q})" for i, q in lounge_items])

        st.markdown(f"### TOTAL: ₦{total_price:,}")

    if st.button("AUTHORIZE TRANSACTION"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        c.execute("INSERT INTO sales (plate, services, total, method, staff, timestamp, type) VALUES (?,?,?,?,?,?,?)", 
                  (plate, item_summary, total_price, "Logged", staff_assigned, now, mode))
        c.execute("INSERT OR REPLACE INTO customers (plate, name, phone, visits, last_visit) VALUES (?,?,?,COALESCE((SELECT visits FROM customers WHERE plate=?),0)+1,?)", (plate, name, full_phone, plate, now.split()[0]))
        if mode == "CAR WASH": c.execute("INSERT OR REPLACE INTO live_bays VALUES (?,?,?)", (plate, "WET BAY", now))
        else:
            for itm, q in lounge_items: c.execute("UPDATE inventory SET stock=stock-? WHERE item=?", (q, itm))
        conn.commit()
        st.session_state['last_receipt'] = {"id": c.lastrowid, "mode": mode, "name": name, "plate": plate, "items": item_summary, "total": total_price, "staff": staff_assigned, "date": now}
        st.success("Log Success")
        st.rerun()

    if 'last_receipt' in st.session_state:
        r = st.session_state['last_receipt']
        st.markdown(f"""
        <div class="receipt-container" id="receipt">
            <div class="receipt-header">
                <h1>RIDEBOSS</h1>
                <p>AUTOS & LOUNGE HQ</p>
                <p>Abuja-Kaduna Expressway, Nigeria</p>
                <p>Support: 09029557912</p>
            </div>
            <div class="receipt-row"><span>Receipt ID:</span> <span>#RB-{r['id']}</span></div>
            <div class="receipt-row"><span>Date:</span> <span>{r['date']}</span></div>
            <div class="receipt-row"><span>Client:</span> <span>{r['name']}</span></div>
            <div class="receipt-row"><span>Vehicle:</span> <span>{r['plate']}</span></div>
            <hr>
            <div style="min-height: 80px;"><b>Services:</b><br>{r['items']}</div>
            <hr>
            <div class="receipt-row" style="font-size:1.5em; font-weight:bold;"><span>TOTAL:</span> <span>₦{r['total']:,}</span></div>
            <div class="receipt-row"><span>Staff:</span> <span>{r['staff']}</span></div>
            <div class="receipt-footer">
                <div class="stamp-official">RIDEBOSS OFFICIAL</div>
                <p>Thank you for your patronage</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("PRINT RECEIPT"):
            st.markdown('<script>window.print();</script>', unsafe_allow_html=True)

# --- 2. ONBOARD STAFF (MANAGER ONLY) ---
elif choice == "ONBOARD STAFF":
    st.subheader("STAFF & SECURITY MANAGEMENT")
    with st.form("onboard"):
        u = st.text_input("New Staff Username")
        p = st.text_input("Temporary Password")
        r = st.selectbox("Role", ["STAFF", "MANAGER"])
        if st.form_submit_button("CREATE ACCOUNT"):
            c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)", (u, p, r))
            conn.commit(); st.success(f"Staff {u} Onboarded!")
    st.write("CURRENT TEAM")
    st.dataframe(pd.read_sql_query("SELECT username, role FROM users", conn))

# --- FINANCIALS (FIXED SPLIT) ---
elif choice == "FINANCIALS":
    sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
    wash_rev = sales_df[sales_df['type']=='CAR WASH']['total'].sum()
    lounge_rev = sales_df[sales_df['type']=='LOUNGE']['total'].sum()
    st.metric("WASH SALES", f"₦{wash_rev:,}")
    st.metric("LOUNGE SALES", f"₦{lounge_rev:,}")
    st.dataframe(sales_df)

# Note: LIVE U-FLOW, NOTIFICATIONS, INVENTORY, CRM modules follow the same logic as previous versions 
# but are now restricted by the user_role logic established at the top.
