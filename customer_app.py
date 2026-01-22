import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="RideBoss Customer Portal",
    page_icon="🏎️",
    layout="centered"
)

# --- DATABASE CONNECTION ---
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Connection Error. Please try again later.")
    st.stop()

# --- CUSTOM STYLING (Matching the Main System) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700;900&display=swap');
    
    .stApp { 
        background-color: #05070a;
        background-image: radial-gradient(at 0% 50%, rgba(0, 255, 255, 0.05) 0px, transparent 40%);
        color: #e2e8f0; 
        font-family: 'Outfit', sans-serif;
    }
    .status-card {
        background: rgba(15, 18, 25, 0.8);
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 15px;
        padding: 25px;
        text-align: center;
        margin-bottom: 20px;
    }
    .plate-header {
        font-size: 2.5rem;
        font-weight: 900;
        color: #00d4ff;
        letter-spacing: 2px;
    }
    .status-badge {
        font-size: 1.2rem;
        font-weight: 700;
        padding: 5px 15px;
        border-radius: 50px;
        background: rgba(0, 212, 255, 0.1);
        border: 1px solid #00d4ff;
    }
    </style>
    """, unsafe_allow_html=True)

# --- APP LOGO ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    try:
        st.image("logo.png", use_container_width=True)
    except:
        st.header("RIDEBOSS AUTOS")

st.markdown("<h3 style='text-align:center;'>CLIENT SERVICE PORTAL</h3>", unsafe_allow_html=True)

# --- NAVIGATION ---
menu = st.tabs(["🚀 LIVE STATUS", "💳 MY MEMBERSHIP", "🍹 LOUNGE MENU"])

# ==========================================
# TAB 1: LIVE STATUS
# ==========================================
with menu[0]:
    st.write("Track your vehicle's progress in real-time.")
    search_plate = st.text_input("ENTER PLATE NUMBER", placeholder="e.g. ABC-123DE").upper().strip()

    if search_plate:
        # Query Live Bays
        query = "SELECT * FROM live_bays WHERE plate = :p"
        res = conn.query(query, params={"p": search_plate}, ttl=0)

        if not res.empty:
            row = res.iloc[0]
            status = row['status']
            
            # Progress Logic
            progress_val = 0
            if status == "WAITING": progress_val = 10
            elif status == "WET BAY": progress_val = 40
            elif status == "DRY BAY": progress_val = 85
            elif status == "READY": progress_val = 100

            st.markdown(f"""
                <div class="status-card">
                    <div class="plate-header">{row['plate']}</div>
                    <div style="margin: 15px 0;">
                        <span class="status-badge">{status}</span>
                    </div>
                    <p>Vehicle: {row['vehicle_type']}</p>
                    <small>Service: {row['service_detail']}</small>
                </div>
            """, unsafe_allow_html=True)
            
            st.progress(progress_val / 100)
            
            if status == "READY":
                st.balloons()
                st.success("✨ Your vehicle is ready for pickup!")
            else:
                st.info("🕒 Our team is working on your vehicle. Refresh to see updates.")
        else:
            st.warning("No active session found for this plate. If you just checked in, please wait a moment.")

# ==========================================
# TAB 2: MEMBERSHIP
# ==========================================
with menu[1]:
    st.write("Check your Gold Card balance.")
    m_plate = st.text_input("VEHICLE PLATE (MEMBERSHIP)", key="mem_input").upper().strip()

    if m_plate:
        m_query = "SELECT * FROM memberships WHERE plate = :p"
        m_res = conn.query(m_query, params={"p": m_plate}, ttl=0)

        if not m_res.empty:
            m_row = m_res.iloc[0]
            bal = m_row['balance_washes']
            
            st.markdown(f"""
                <div class="status-card" style="border-color: #FFD700;">
                    <h2 style="color:#FFD700;">{m_row['card_type']}</h2>
                    <div style="font-size: 4rem; font-weight: 900;">{bal}</div>
                    <p>WASHES REMAINING</p>
                </div>
            """, unsafe_allow_html=True)
            
            if bal <= 1:
                st.warning("⚠️ Your balance is low. Visit the reception to top up!")
        else:
            st.error("No membership found for this plate.")

# ==========================================
# TAB 3: LOUNGE MENU
# ==========================================
with menu[2]:
    st.write("Browse our available refreshments while you wait.")
    
    inv_data = conn.query("SELECT item, price, stock FROM inventory WHERE price > 0", ttl=0)
    
    if not inv_data.empty:
        for idx, row in inv_data.iterrows():
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{row['item']}**")
                if row['stock'] <= 0:
                    st.caption("Out of Stock")
            with c2:
                st.markdown(f"₦{row['price']:,}")
            st.divider()
    else:
        st.info("Lounge menu is currently being updated.")

# --- FOOTER ---
st.markdown("---")
st.caption("© 2026 RideBoss Autos | Victoria Island, Lagos")
