import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image
import geocoder
import random, string
import numpy as np
import cv2
import sqlite3
import smtplib
from email.message import EmailMessage

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    sos_email TEXT,
                    smtp_server TEXT,
                    smtp_port INTEGER,
                    smtp_user TEXT,
                    smtp_pass TEXT)''')
    conn.commit()
    conn.close()

def register_user(email, password):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(email, password):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
    user = c.fetchone()
    conn.close()
    return user

def update_sos_email(email, sos_email):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE users SET sos_email=? WHERE email=?", (sos_email, email))
    conn.commit()
    conn.close()

def get_sos_email(email):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT sos_email FROM users WHERE email=?", (email,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def update_smtp_config(email, server, port, user, password):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE users SET smtp_server=?, smtp_port=?, smtp_user=?, smtp_pass=? WHERE email=?",
              (server, port, user, password, email))
    conn.commit()
    conn.close()

def get_smtp_config(email):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT smtp_server, smtp_port, smtp_user, smtp_pass FROM users WHERE email=?", (email,))
    result = c.fetchone()
    conn.close()
    return result if result else (None, None, None, None)

def send_sos(sender_email):
    sos_email = get_sos_email(sender_email)
    smtp_server, smtp_port, smtp_user, smtp_pass = get_smtp_config(sender_email)

    if not sos_email or not smtp_server or not smtp_port or not smtp_user or not smtp_pass:
        return False, "Konfigurasi SOS atau SMTP belum lengkap!"

    try:
        msg = EmailMessage()
        msg["Subject"] = "🚨 SOS Alert!"
        msg["From"] = smtp_user
        msg["To"] = sos_email
        msg.set_content("Pesan darurat: Saya membutuhkan bantuan segera!")

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        return True, f"SOS berhasil dikirim ke {sos_email}"
    except Exception as e:
        return False, str(e)

# --- DNA Mapping ---
binary_to_dna = {"00":"A","01":"T","10":"G","11":"C"}
dna_to_binary = {v:k for k,v in binary_to_dna.items()}
complement_map = {"A":"T","T":"A","G":"C","C":"G"}

def text_to_dna(text):
    binary = ''.join(format(ord(c), '08b') for c in text)
    return ''.join(binary_to_dna[binary[i:i+2]] for i in range(0, len(binary), 2))

def dna_to_text(dna_seq):
    binary = ''.join(dna_to_binary[b] for b in dna_seq)
    chars = [binary[i:i+8] for i in range(0, len(binary), 8)]
    return ''.join(chr(int(c,2)) for c in chars)

def generate_password(length=12):
    dna_seq = ''.join(random.choice("ATGC") for _ in range(length * 2))
    while True:
        password = ''.join(
            random.choice(string.ascii_lowercase) if ch=="A" else
            random.choice(string.ascii_uppercase) if ch=="T" else
            random.choice(string.digits) if ch=="G" else
            random.choice("!@#$%^&*") for ch in dna_seq[:length]
        )
        if (any(c.islower() for c in password) and
            any(c.isupper() for c in password) and
            any(c.isdigit() for c in password) and
            any(c in "!@#$%^&*" for c in password)):
            break
    return password, dna_seq

# --- Init DB ---
init_db()

# --- CSS Styling ---
st.markdown("""
<style>
.stApp {
    background-color: #1a1a2e;
    color: #ffffff;
}
.card {
    background-color: #212145;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
}
.neon-text {
    color: #7DF9FF;
    font-weight: bold;
}
.sos-button {
    position: fixed;
    bottom: 30px;
    right: 30px;
    background-color: #FF3C3C;
    color: white;
    padding: 15px 25px;
    border-radius: 10px;
    font-weight: bold;
    z-index: 999;
}
.sos-button:hover {
    background-color: #FF1C1C;
}
</style>
""", unsafe_allow_html=True)

# --- Session State ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.email = None

# --- Sidebar Menu ---
st.sidebar.title("🧬 CamouGene Menu")
menu = st.sidebar.radio("Menu", ["Login", "Register", "Encode/Decode DNA", "QR Maker", "SOS Settings", "Configure"])

# --- LOGIN ---
if menu == "Login":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(email, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.email = email
            st.success(f"Login berhasil sebagai {email}")
        else:
            st.error("Email atau password salah!")
    st.markdown('</div>', unsafe_allow_html=True)

# --- REGISTER ---
elif menu == "Register":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Register")
    email = st.text_input("Email Baru")
    password = st.text_input("Password Baru", type="password")
    if st.button("Register"):
        if register_user(email, password):
            st.success("Registrasi berhasil! Silakan login.")
        else:
            st.error("Email sudah terdaftar!")
    st.markdown('</div>', unsafe_allow_html=True)

# --- Protected Pages ---
else:
    if not st.session_state.logged_in:
        st.warning("Silakan login dulu untuk mengakses halaman ini!")
    else:
        st.sidebar.success(f"Logged in sebagai {st.session_state.email}")

        # --- Encode/Decode DNA ---
        if menu == "Encode/Decode DNA":
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🧬 Encode/Decode DNA")
            teks = st.text_input("Masukkan teks atau DNA sequence:")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Encode (Teks → DNA)"):
                    dna = text_to_dna(teks)
                    st.success(f"DNA: {dna}")
            with col2:
                if st.button("Decode (DNA → Teks)"):
                    try:
                        decoded = dna_to_text(teks)
                        st.success(f"Teks: {decoded}")
                    except:
                        st.error("DNA tidak valid!")
            st.markdown('</div>', unsafe_allow_html=True)

        # --- QR Maker ---
        elif menu == "QR Maker":
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("📷 QR Maker")
            teks_qr = st.text_input("Masukkan teks/password untuk QR:")
            if st.button("Generate QR dari DNA + Lokasi"):
                if teks_qr:
                    g = geocoder.ip('me')
                    lokasi = f"LAT:{g.latlng[0]},LON:{g.latlng[1]}" if g.ok else "LAT:0,LON:0"
                    full_text = f"{teks_qr} | {lokasi}"
                    dna = text_to_dna(full_text)
                    qr = qrcode.make(dna)
                    buf = BytesIO()
                    qr.save(buf, format="PNG")
                    st.image(buf.getvalue(), caption="QR Code", width=200)
                    st.download_button("Download QR", buf.getvalue(), file_name="dna_qr.png")
            st.markdown('</div>', unsafe_allow_html=True)

        # --- SOS Settings ---
        elif menu == "SOS Settings":
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🚨 SOS Settings")
            current = get_sos_email(st.session_state.email)
            st.info(f"Email SOS sekarang: {current if current else 'Belum diset'}")
            sos_email = st.text_input("Masukkan email penerima SOS")
            if st.button("Update Email SOS"):
                update_sos_email(st.session_state.email, sos_email)
                st.success("Email SOS berhasil diperbarui!")
            st.markdown('</div>', unsafe_allow_html=True)

        # --- Configure SMTP ---
        elif menu == "Configure":
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("⚙️ Configure SMTP")
            smtp_server = st.text_input("SMTP Server (contoh: smtp.gmail.com)")
            smtp_port = st.number_input("SMTP Port (contoh: 465)", value=465)
            smtp_user = st.text_input("SMTP User (email pengirim)")
            smtp_pass = st.text_input("SMTP App Password", type="password")
            if st.button("Simpan Konfigurasi"):
                update_smtp_config(st.session_state.email, smtp_server, smtp_port, smtp_user, smtp_pass)
                st.success("Konfigurasi SMTP berhasil disimpan!")
            st.markdown('</div>', unsafe_allow_html=True)

# --- Floating SOS Button ---
if st.session_state.logged_in:
    st.markdown("""
    <a href="#send" class="sos-button">🚨 SOS</a>
    """, unsafe_allow_html=True)
