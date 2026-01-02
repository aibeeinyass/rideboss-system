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
    
    /* Receipt Styling */
    .receipt-box { background: white; color: black; padding: 30px; border-radius: 5px; font-family: 'Courier New', monospace; max-width: 400px; margin: auto; border: 2px dashed #333; }
    .receipt-header { text-align: center; border-bottom: 1px solid #333; padding-bottom: 10px; }
    .receipt-stamp { color: #d00; border: 3px solid #d00; display: inline-block; padding: 5px; transform: rotate(-10deg); font-weight: bold; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- UTILITIES ---
def add_event(msg):
    now = datetime.now().strftime("%H:%M:%S")
    c.execute("INSERT INTO notifications (message, timestamp) VALUES (?,?)", (f"{now} | {msg}", now))
    conn.commit()

def format_whatsapp(phone, message):
    return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"

# --- LOAD CONFIG ---
wash_prices_df = pd.read_sql_query("SELECT * FROM wash_prices", conn)
SERVICES = dict(zip(wash_prices_df['service'], wash_prices_df['price']))
STAFF_MEMBERS = ["Sunday", "Musa", "Chidi", "Ibrahim", "Tunde"]
COUNTRY_CODES = {"Nigeria": "+234", "Ghana": "+233", "UK": "+44", "USA": "+1", "UAE": "+971"}

# --- SIDEBAR ---
st.sidebar.markdown("<h2 style='letter-spacing:4px;'>RIDEBOSS</h2>", unsafe_allow_html=True)
access_level = st.sidebar.selectbox("ACCESS LEVEL", ["STAFF", "MANAGER"])
authenticated = False
if access_level == "MANAGER":
    pin = st.sidebar.text_input("MANAGER PIN", type="password")
    if pin == MANAGER_PIN: authenticated = True; st.sidebar.success("SECURE ACCESS GRANTED")

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
    search_selection = st.selectbox("SEARCH EXISTING CLIENT", search_options)
    
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
        pay_method = st.selectbox("PAYMENT METHOD", ["Moniepoint POS", "Bank Transfer", "Cash"])

    if st.button(f"AUTHORIZE {mode} TRANSACTION", use_container_width=True):
        if (plate or mode == "LOUNGE") and (selected if mode=="CAR WASH" else lounge_items_sold):
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
                "id": c.lastrowid, "mode": mode, "name": name, "plate": plate, 
                "items": item_summary, "total": total_price, "staff": staff_assigned, "date": now
            }
            add_event(f"{mode} AUTH: {plate if plate else 'Lounge'} via {pay_method}")
            st.success("✅ Transaction Logged.")
            st.rerun()

    # --- RECEIPT GENERATION ---
    if 'last_receipt' in st.session_state:
        r = st.session_state['last_receipt']
        st.markdown(f"""
        <div class="receipt-box" id="printableReceipt">
            <div class="receipt-header">
                <h2>RIDEBOSS AUTOS</h2>
                <p>Premium Car Wash & Lounge</p>
                <p>Lagos, Nigeria</p>
                <p>Tel: 09029557912</p>
            </div>
            <p><b>Date:</b> {r['date']}</p>
            <p><b>Receipt No:</b> #00{r['id']}</p>
            <p><b>Client:</b> {r['name']} ({r['plate']})</p>
            <hr>
            <p><b>Items/Services:</b><br>{r['items']}</p>
            <hr>
            <h3>TOTAL: ₦{r['total']:,}</h3>
            <p><b>Handled By:</b> {r['staff']}</p>
            <div class="receipt-stamp">RIDEBOSS VERIFIED</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("PRINT RECEIPT"):
            st.markdown('<script>window.print();</script>', unsafe_allow_html=True)
        if st.button("CLEAR RECEIPT"):
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

# --- 3. NOTIFICATIONS TAB ---
elif choice == "NOTIFICATIONS":
    st.subheader("SYSTEM NOTIFICATION HISTORY")
    notes = pd.read_sql_query("SELECT timestamp as 'TIME', message as 'EVENT' FROM notifications ORDER BY id DESC", conn)
    st.table(notes)

# --- 4. INVENTORY & STAFF (MANAGER) ---
elif choice == "INVENTORY & STAFF" and authenticated:
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
        st.dataframe(pd.read_sql_query("SELECT * FROM inventory", conn), use_container_width=True)
    with t2:
        edit_svc = st.selectbox("Select Service", list(SERVICES.keys()))
        new_svc_price = st.number_input("New Price", value=SERVICES[edit_svc])
        if st.button("UPDATE PRICE"):
            c.execute("UPDATE wash_prices SET price=? WHERE service=?", (new_svc_price, edit_svc))
            conn.commit(); st.rerun()
    with t3:
        st.bar_chart(pd.read_sql_query("SELECT staff, COUNT(*) as washes FROM sales GROUP BY staff", conn).set_index('staff'))

# --- 5. FINANCIALS (MANAGER) ---
elif choice == "FINANCIALS" and authenticated:
    st.subheader("REVENUE BREAKDOWN")
    sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
    exp_df = pd.read_sql_query("SELECT * FROM expenses", conn)
    
    rev_wash = sales_df[sales_df['type'] == 'CAR WASH']['total'].sum() if not sales_df.empty else 0
    rev_lounge = sales_df[sales_df['type'] == 'LOUNGE']['total'].sum() if not sales_df.empty else 0
    exps = exp_df['amount'].sum() if not exp_df.empty else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("WASH REVENUE", f"₦{rev_wash:,}")
    col2.metric("LOUNGE REVENUE", f"₦{rev_lounge:,}")
    col3.metric("EXPENSES", f"₦{exps:,}", delta_color="inverse")
    col4.metric("NET PROFIT", f"₦{(rev_wash + rev_lounge) - exps:,}")
    
    st.markdown("---")
    with st.expander("LOG EXPENSE"):
        e_desc = st.text_input("Description")
        e_amt = st.number_input("Amount", min_value=0.0)
        if st.button("LOG"):
            c.execute("INSERT INTO expenses (description, amount, timestamp) VALUES (?,?,?)", (e_desc, e_amt, datetime.now().strftime("%Y-%m-%d")))
            conn.commit(); st.rerun()
    st.dataframe(sales_df)

# --- 6. CRM & RETENTION (MANAGER) ---
elif choice == "CRM & RETENTION" and authenticated:
    st.subheader("RETENTION")
    cust_df = pd.read_sql_query("SELECT * FROM customers", conn)
    for idx, row in cust_df.iterrows():
        last_v = datetime.strptime(row['last_visit'], "%Y-%m-%d")
        days = (datetime.now() - last_v).days
        color = "#00d4ff" if days < 14 else "#FF3B30"
        st.markdown(f"<p style='color:{color};'><b>{row['name']}</b> ({row['plate']}) - {days} days away</p>", unsafe_allow_html=True)
