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
             (username TEXT PRIMARY KEY, password TEXT, role TEXT, status TEXT DEFAULT 'ACTIVE')''')
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
# UPDATED: Added sale_price to track card revenue
c.execute('''CREATE TABLE IF NOT EXISTS memberships 
             (plate TEXT PRIMARY KEY, balance_washes INTEGER, card_type TEXT, sale_price REAL DEFAULT 0.0)''')

# Seed Admin and Initial Data
c.execute("INSERT OR IGNORE INTO users VALUES ('admin', '0000', 'MANAGER', 'ACTIVE')")
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

# --- LOAD CONFIG & DYNAMIC STAFF AVAILABILITY ---
staff_query = pd.read_sql_query("SELECT username FROM users WHERE status='ACTIVE'", conn)
ALL_STAFF = staff_query['username'].tolist()

# Logic to find Busy Staff (those currently in a live bay)
busy_query = pd.read_sql_query("SELECT staff FROM live_bays", conn)
busy_list = busy_query['staff'].tolist()
# Logic to find Free Staff
AVAILABLE_STAFF = [s for s in ALL_STAFF if s not in busy_list]

wash_prices_df = pd.read_sql_query("SELECT * FROM wash_prices", conn)
SERVICES = dict(zip(wash_prices_df['service'], wash_prices_df['price']))
COUNTRY_CODES = {"Nigeria": "+234", "Ghana": "+233", "UK": "+44", "USA": "+1", "UAE": "+971"}

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown(f"USER: **{st.session_state.user_name}**")
menu = ["COMMAND CENTER", "LIVE U-FLOW", "NOTIFICATIONS"]
if st.session_state.user_role == "MANAGER":
    menu += ["ONBOARD STAFF", "INVENTORY & STAFF", "FINANCIALS", "CRM & RETENTION"]

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
                # SMARTER FEATURE: Upsell Prompt
                if selected and "Standard Wash" in selected and "Ceramic Wax" not in selected:
                    st.warning("💡 PROMPT: Ask client if they want Ceramic Wax for long-lasting shine!")
                
                total_price = sum([SERVICES[s] for s in selected])
                
                # SMARTER FEATURE: Staff Availability UI
                staff_assigned = st.selectbox("ASSIGN DETAILER (Available listed first)", AVAILABLE_STAFF + ["--- BUSY ---"] + busy_list)
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
                staff_assigned = st.selectbox("SERVER", ALL_STAFF)
                item_summary = ", ".join([f"{i} (x{q})" for i, q in lounge_items_sold])

            st.markdown(f"### TOTAL: ₦{total_price:,}")
            pay_method = st.selectbox("PAYMENT METHOD", ["Moniepoint POS", "Bank Transfer", "Cash", "Gold Card Credit"])

        if st.button(f"AUTHORIZE {mode} TRANSACTION", use_container_width=True):
            if (plate or mode == "LOUNGE") and (selected if mode=="CAR WASH" else lounge_items_sold):
                
                can_proceed = True
                low_bal = False
                
                if pay_method == "Gold Card Credit":
                    c.execute("SELECT balance_washes FROM memberships WHERE plate=?", (plate,))
                    m_res = c.fetchone()
                    if m_res and m_res[0] > 0:
                        new_bal = m_res[0] - 1
                        c.execute("UPDATE memberships SET balance_washes=? WHERE plate=?", (new_bal, plate))
                        if new_bal <= 1: low_bal = True
                    else:
                        st.error("No active card or zero balance for this plate.")
                        can_proceed = False

                if can_proceed:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    c.execute("INSERT INTO sales (plate, services, total, method, staff, timestamp, type) VALUES (?,?,?,?,?,?,?)", 
                              (plate, item_summary, total_price, pay_method, staff_assigned, now, mode))
                    c.execute("INSERT OR REPLACE INTO customers (plate, name, phone, visits, last_visit) VALUES (?, ?, ?, COALESCE((SELECT visits FROM customers WHERE plate=?), 0) + 1, ?)", (plate, name, full_phone, plate, now.split()[0]))
                    
                    if mode == "CAR WASH":
                        # Updated to include staff name in live_bays for monitor tracking
                        c.execute("INSERT OR REPLACE INTO live_bays (plate, status, entry_time, staff) VALUES (?, ?, ?, ?)", (plate, "WET BAY", now, staff_assigned))
                    else:
                        for item, qty in lounge_items_sold:
                            c.execute("UPDATE inventory SET stock = stock - ? WHERE item = ?", (qty, item))
                    
                    conn.commit()
                    st.session_state['last_receipt'] = {
                        "id": c.lastrowid, "mode": mode, "name": name, "plate": plate, "phone": full_phone,
                        "items": item_summary, "total": total_price if pay_method != "Gold Card Credit" else 0, 
                        "staff": staff_assigned, "date": now, "low_bal": low_bal
                    }
                    add_event(f"{mode} AUTH: {plate if plate else 'Lounge'} via {pay_method}")
                    st.rerun()

    with tab_mem:
        st.subheader("ACTIVATE MEMBERSHIP CARD")
        m_plate = st.text_input("SCAN/ENTER PLATE FOR CARD").upper()
        tier = st.selectbox("CARD TIER", ["Silver (5 Washes)", "Gold (10 Washes)", "Platinum (25 Washes)"])
        # SMARTER FEATURE: Track Revenue from Card Sales
        card_sale_price = st.number_input("CARD SALE PRICE (₦)", min_value=0.0)
        qty = 5 if "Silver" in tier else 10 if "Gold" in tier else 25
        
        if st.button("ISSUE CARD"):
            if m_plate:
                c.execute("INSERT OR REPLACE INTO memberships (plate, balance_washes, card_type, sale_price) VALUES (?, ?, ?, ?)", (m_plate, qty, tier, card_sale_price))
                conn.commit()
                add_event(f"CARD ISSUED: {tier} to {m_plate}")
                st.success(f"Activated {tier} for {m_plate}!")
            else:
                st.error("Plate number required.")

    # --- RECEIPT VIEW ---
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
                <div class="receipt-row"><span>Detailer/Server:</span> <span>{r['staff']}</span></div>
            </div>
            <div style="text-align:center;"><div class="receipt-stamp">RIDEBOSS OFFICIAL STAMP</div></div>
        </div>
        """, unsafe_allow_html=True)
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("🖨️ PRINT RECEIPT"):
                st.markdown('<script>window.print();</script>', unsafe_allow_html=True)
        with col_r2:
            if r.get('low_bal'):
                msg = f"Hi {r['name']}, your Gold Card has only 1 wash left. Visit us soon to top up!"
                st.markdown(f'[:warning: SEND LOW BALANCE ALERT]({format_whatsapp(r["phone"], msg)})')

        if st.button("DONE"):
            del st.session_state['last_receipt']
            st.rerun()

# --- 2. LIVE U-FLOW (For Outside Monitor) ---
elif choice == "LIVE U-FLOW":
    st.subheader("ACTIVE WASH BAYS (EXTERNAL DISPLAY MODE)")
    live_cars = pd.read_sql_query("SELECT * FROM live_bays", conn)
    
    if live_cars.empty: 
        st.info("ALL BAYS CLEAR. READY FOR NEXT VEHICLE.")
    else:
        for idx, row in live_cars.iterrows():
            # SMARTER FEATURE: Bay Timer Logic
            entry_dt = datetime.strptime(row['entry_time'], "%Y-%m-%d %H:%M")
            time_spent = (datetime.now() - entry_dt).seconds // 60
            
            # Color logic for monitor
            border_color = "#00d4ff" if time_spent < 40 else "#FF3B30"
            
            st.markdown(f'<div class="status-card" style="border-left: 10px solid {border_color};">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"### {row['plate']}")
                st.write(f"**ZONE:** {row['status']}")
            with c2:
                st.write(f"**DETAILER:** {row['staff']}")
                st.write(f"**ELAPSED:** {time_spent} mins")
            with c3:
                if row['status'] == "WET BAY":
                    if st.button(f"TO DRY {row['plate']}"):
                        c.execute("UPDATE live_bays SET status='DRY BAY' WHERE plate=?", (row['plate'],))
                        add_event(f"{row['plate']} MOVED TO DRY."); conn.commit(); st.rerun()
                if st.button(f"RELEASE {row['plate']}"):
                    c.execute("SELECT name, phone FROM customers WHERE plate=?", (row['plate'],))
                    cust = c.fetchone()
                    c.execute("DELETE FROM live_bays WHERE plate=?", (row['plate'],))
                    add_event(f"{row['plate']} READY."); conn.commit()
                    msg = f"Hi {cust[0]}, your vehicle {row['plate']} is ready at RideBoss!"
                    st.markdown(f"[:speech_balloon: WHATSAPP]({format_whatsapp(cust[1], msg)})")
            st.markdown('</div>', unsafe_allow_html=True)

# --- 3. ONBOARD STAFF (MANAGER) ---
elif choice == "ONBOARD STAFF" and st.session_state.user_role == "MANAGER":
    st.subheader("STAFF ONBOARDING")
    with st.form("new_staff"):
        s_name = st.text_input("Full Name (This shows in Detailer list)")
        s_pass = st.text_input("Login Password", type="password")
        s_role = st.selectbox("System Role", ["STAFF", "MANAGER"])
        if st.form_submit_button("ONBOARD STAFF"):
            if s_name and s_pass:
                c.execute("INSERT OR REPLACE INTO users (username, password, role, status) VALUES (?,?,?,?)", (s_name, s_pass, s_role, 'ACTIVE'))
                conn.commit()
                st.success(f"{s_name} added to system.")
                st.rerun()
    
    st.write("---")
    st.subheader("CURRENT STAFF LIST")
    current_staff_df = pd.read_sql_query("SELECT username, role, status FROM users", conn)
    st.dataframe(current_staff_df, use_container_width=True)
    
    # Feature to deactivate staff
    target_staff = st.selectbox("Deactivate Staff Member", ["None"] + current_staff_df['username'].tolist())
    if st.button("SET AS INACTIVE") and target_staff != "None":
        c.execute("UPDATE users SET status='INACTIVE' WHERE username=?", (target_staff,))
        conn.commit(); st.rerun()

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
        
        # SMARTER FEATURE: Low Stock Alert
        inv_data = pd.read_sql_query("SELECT * FROM inventory", conn)
        for _, item in inv_data.iterrows():
            if item['stock'] < 5:
                st.error(f"🚨 LOW STOCK: {item['item']} ({item['stock']} left)")
        st.dataframe(inv_data, use_container_width=True)

    with t2:
        edit_svc = st.selectbox("Select Service", list(SERVICES.keys()))
        new_svc_price = st.number_input("New Price", value=SERVICES[edit_svc])
        if st.button("UPDATE PRICE"):
            c.execute("UPDATE wash_prices SET price=? WHERE service=?", (new_svc_price, edit_svc))
            conn.commit(); st.rerun()
    with t3:
        # SMARTER FEATURE: Detailed Performance
        perf_query = "SELECT staff, COUNT(*) as washes, SUM(total) as revenue FROM sales WHERE type='CAR WASH' GROUP BY staff"
        perf_df = pd.read_sql_query(perf_query, conn)
        st.bar_chart(perf_df.set_index('staff')['washes'])
        st.dataframe(perf_df, use_container_width=True)

# --- 5. FINANCIALS (MANAGER) ---
elif choice == "FINANCIALS" and st.session_state.user_role == "MANAGER":
    st.subheader("REVENUE BREAKDOWN")
    
    tab_fin, tab_cards_hub = st.tabs(["REVENUE & EXPENSES", "MANAGE MEMBERSHIP CARDS"])
    
    with tab_fin:
        sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
        exp_df = pd.read_sql_query("SELECT * FROM expenses", conn)
        
        # SMARTER FEATURE: Separate Card Revenue
        rev_wash = sales_df[sales_df['type'] == 'CAR WASH']['total'].sum() if not sales_df.empty else 0
        rev_lounge = sales_df[sales_df['type'] == 'LOUNGE']['total'].sum() if not sales_df.empty else 0
        card_sales_rev = pd.read_sql_query("SELECT SUM(sale_price) FROM memberships", conn).iloc[0,0] or 0
        exps = exp_df['amount'].sum() if not exp_df.empty else 0
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("WASH REV", f"₦{rev_wash:,}")
        col2.metric("LOUNGE REV", f"₦{rev_lounge:,}")
        col3.metric("CARD SALES", f"₦{card_sales_rev:,}")
        col4.metric("EXPENSES", f"₦{exps:,}", delta_color="inverse")
        col5.metric("NET PROFIT", f"₦{(rev_wash + rev_lounge + card_sales_rev) - exps:,}")
        
        st.markdown("---")
        with st.expander("LOG EXPENSE"):
            e_desc = st.text_input("Description")
            e_amt = st.number_input("Amount", min_value=0.0)
            if st.button("LOG"):
                c.execute("INSERT INTO expenses (description, amount, timestamp) VALUES (?,?,?)", (e_desc, e_amt, datetime.now().strftime("%Y-%m-%d")))
                conn.commit(); st.rerun()
        st.write("### FULL TRANSACTION LOG")
        st.dataframe(sales_df)

    with tab_cards_hub:
        st.write("### 💳 MEMBERSHIP CONTROL CENTER")
        m_df = pd.read_sql_query("SELECT * FROM memberships", conn)
        
        for idx, row in m_df.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.write(f"**{row['plate']}** ({row['card_type']})")
                c2.write(f"Bal: {row['balance_washes']} left")
                
                # REFRESH BALANCE BUTTON
                if c3.button(f"TOP UP {row['plate']}", key=f"up_{row['plate']}"):
                    c.execute("UPDATE memberships SET balance_washes = 10 WHERE plate=?", (row['plate'],))
                    conn.commit(); st.rerun()
                
                # DELETE CARD BUTTON
                if c4.button(f"DELETE {row['plate']}", key=f"del_{row['plate']}"):
                    c.execute("DELETE FROM memberships WHERE plate=?", (row['plate'],))
                    conn.commit(); st.rerun()
                st.markdown("---")

# --- 6. CRM & RETENTION (MANAGER) ---
elif choice == "CRM & RETENTION" and st.session_state.user_role == "MANAGER":
    st.subheader("RETENTION INTELLIGENCE")
    cust_df = pd.read_sql_query("SELECT * FROM customers", conn)
    for idx, row in cust_df.iterrows():
        last_v = datetime.strptime(row['last_visit'], "%Y-%m-%d")
        days = (datetime.now() - last_v).days
        color = "#00d4ff" if days < 14 else "#FF3B30"
        st.markdown(f"<p style='color:{color};'><b>{row['name']}</b> ({row['plate']}) - {days} days since last visit</p>", unsafe_allow_html=True)
        if days > 14:
            st.markdown(f"[:warning: REACH OUT]({format_whatsapp(row['phone'], f'Hi {row['name']}, we miss you at RideBoss!')})")

# --- 7. NOTIFICATIONS ---
elif choice == "NOTIFICATIONS":
    st.subheader("SYSTEM NOTIFICATION HISTORY")
    notes = pd.read_sql_query("SELECT timestamp as 'TIME', message as 'EVENT' FROM notifications ORDER BY id DESC", conn)
    st.table(notes)
