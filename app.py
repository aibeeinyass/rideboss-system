import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3

# --- DATABASE SETUP ---
conn = sqlite3.connect('rideboss_final.db', check_same_thread=False)
c = conn.cursor()

# Create tables for everything
c.execute('''CREATE TABLE IF NOT EXISTS customers 
             (plate TEXT PRIMARY KEY, name TEXT, phone TEXT, visits INTEGER, last_visit TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS sales 
             (id INTEGER PRIMARY KEY, plate TEXT, services TEXT, total REAL, method TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS expenses 
             (id INTEGER PRIMARY KEY, item TEXT, amount REAL, category TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS live_bays 
             (plate TEXT PRIMARY KEY, status TEXT)''')
conn.commit()

# --- CONFIGURATION ---
SERVICES = {
    "Standard Wash": 5000,
    "Executive Detail": 15000,
    "Engine Steam": 10000,
    "Ceramic Wax": 25000,
    "Interior Deep Clean": 12000
}

# --- APP STYLE ---
st.set_page_config(page_title="RideBoss HQ", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: white; }
    .status-card { background: #111; padding: 20px; border-radius: 10px; border-left: 5px solid #00d4ff; margin-bottom: 10px; }
    .metric-box { background: #1a1c23; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🏎️ RideBoss Autos")
menu = ["🛎️ Reception & POS", "🌊 Live U-Flow Tracker", "📊 Finance & Expenses", "💎 CRM & Loyalty"]
choice = st.sidebar.radio("Main Menu", menu)

# --- 1. RECEPTION & POS ---
if choice == "🛎️ Reception & POS":
    st.title("Check-In & Payment")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Customer Details")
        plate = st.text_input("Number Plate").upper()
        name = st.text_input("Owner Name")
        phone = st.text_input("WhatsApp Number (e.g., 234...)")

    with col2:
        st.subheader("Order Summary")
        selected = st.multiselect("Select Services", list(SERVICES.keys()))
        total_price = sum([SERVICES[s] for s in selected])
        st.markdown(f"## Total: ₦{total_price:,}")
        pay_method = st.selectbox("Payment Method", ["Moniepoint POS", "Bank Transfer", "Cash"])

    if st.button("🚀 Process & Start Wash", use_container_width=True):
        if plate and selected:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            # Log Sale
            c.execute("INSERT INTO sales (plate, services, total, method, timestamp) VALUES (?,?,?,?,?)",
                      (plate, ", ".join(selected), total_price, pay_method, now))
            # Update Customer Loyalty
            c.execute("INSERT OR REPLACE INTO customers (plate, name, phone, visits, last_visit) VALUES (?, ?, ?, COALESCE((SELECT visits FROM customers WHERE plate=?), 0) + 1, ?)",
                      (plate, name, phone, plate, now.split()[0]))
            # Put in Live Bay Tracker
            c.execute("INSERT OR REPLACE INTO live_bays (plate, status) VALUES (?, ?)", (plate, "Wet Bay (Washing)"))
            conn.commit()
            st.success(f"Payment Confirmed! {plate} is now in Wet Bay.")
        else:
            st.error("Missing plate or services!")

# --- 2. LIVE U-FLOW TRACKER ---
elif choice == "🌊 Live U-Flow Tracker":
    st.title("Active Bay Management")
    live_cars = pd.read_sql_query("SELECT * FROM live_bays", conn)
    
    if live_cars.empty:
        st.info("No cars currently in the U-Flow system.")
    else:
        for index, row in live_cars.iterrows():
            with st.container():
                st.markdown(f'<div class="status-card">', unsafe_allow_html=True)
                c1, c2, c3 = st.columns([2, 2, 1])
                
                c1.markdown(f"### 🚗 {row['plate']}")
                c1.write(f"Current Zone: **{row['status']}**")
                
                with c2:
                    if row['status'] == "Wet Bay (Washing)":
                        if st.button(f"Move {row['plate']} to Dry Bay"):
                            c.execute("UPDATE live_bays SET status='Dry Bay (Detailing)' WHERE plate=?", (row['plate'],))
                            conn.commit()
                            st.rerun()
                
                with c3:
                    if st.button(f"✅ READY: {row['plate']}"):
                        # Get phone and name for notification
                        c.execute("SELECT name, phone FROM customers WHERE plate=?", (row['plate'],))
                        cust = c.fetchone()
                        # Remove from live tracker
                        c.execute("DELETE FROM live_bays WHERE plate=?", (row['plate'],))
                        conn.commit()
                        # Notification Link
                        msg = f"https://wa.me/{cust[1]}?text=Hi%20{cust[0]},%20your%20car%20({row['plate']})%20is%20ready%20at%20RideBoss%20Autos!%20🚀"
                        st.markdown(f"[**CLICK TO NOTIFY CUSTOMER**]({msg})")
                st.markdown('</div>', unsafe_allow_html=True)

# --- 3. FINANCE & EXPENSES ---
elif choice == "📊 Finance & Expenses":
    st.title("Financial Intelligence")
    
    # Expense Input
    with st.expander("➕ Log New Expense"):
        item = st.text_input("Expense Item (e.g., Car Soap)")
        amt = st.number_input("Amount (₦)", min_value=0)
        cat = st.selectbox("Category", ["Chemicals/Supplies", "Electricity", "Staff Pay", "Maintenance"])
        if st.button("Save Expense"):
            c.execute("INSERT INTO expenses (item, amount, category, timestamp) VALUES (?,?,?,?)",
                      (item, amt, cat, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()

    # Reporting
    sales_df = pd.read_sql_query("SELECT * FROM sales", conn)
    exp_df = pd.read_sql_query("SELECT * FROM expenses", conn)
    
    rev = sales_df['total'].sum() if not sales_df.empty else 0
    costs = exp_df['amount'].sum() if not exp_df.empty else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Gross Revenue", f"₦{rev:,}")
    m2.metric("Total Expenses", f"₦{costs:,}")
    m3.metric("Net Profit", f"₦{rev - costs:,}")
    
    st.subheader("Sales History")
    st.dataframe(sales_df, use_container_width=True)

# --- 4. CRM & LOYALTY ---
elif choice == "💎 CRM & Loyalty":
    st.title("Customer VIP Portal")
    cust_df = pd.read_sql_query("SELECT * FROM customers", conn)
    
    for index, row in cust_df.iterrows():
        last_date = datetime.strptime(row['last_visit'], "%Y-%m-%d")
        days_away = (datetime.now() - last_date).days
        
        col_x, col_y = st.columns([3, 1])
        with col_x:
            status = "🔥 ACTIVE" if days_away < 7 else "⚠️ MIA"
            st.write(f"**{row['name']}** ({row['plate']}) | Visits: {row['visits']} | Last: {days_away} days ago [{status}]")
        
        with col_y:
            if days_away >= 7:
                remind = f"https://wa.me/{row['phone']}?text=Hi%20{row['name']},%20your%20car%20is%20due%20for%20a%20shine!%20See%20you%20this%20week?"
                st.markdown(f"[Send Reminder]({remind})")