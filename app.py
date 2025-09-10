import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image
import geocoder
import random, string
import numpy as np
import cv2
import sqlite3

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    sos_email TEXT)''')
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


# --- Init Database ---
init_db()

# --- UI ---
st.title("🧬 DNA Encoder/Decoder + QR Generator + Login System")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.email = None

menu = st.sidebar.radio("Menu", ["Login", "Register", "App"])

# --- LOGIN ---
if menu == "Login":
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

# --- REGISTER ---
elif menu == "Register":
    st.subheader("Register")
    email = st.text_input("Email Baru")
    password = st.text_input("Password Baru", type="password")
    if st.button("Register"):
        if register_user(email, password):
            st.success("Registrasi berhasil! Silakan login.")
        else:
            st.error("Email sudah terdaftar!")

# --- APP ---
elif menu == "App":
    if not st.session_state.logged_in:
        st.warning("Silakan login dulu untuk mengakses aplikasi!")
    else:
        st.sidebar.success(f"Logged in sebagai {st.session_state.email}")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.email = None
            st.experimental_rerun()

        # Submenu dalam aplikasi
        sub_menu = st.radio("Pilih Menu", ["Encode/Decode DNA", "QR Maker", "SOS Settings"])

        if sub_menu == "Encode/Decode DNA":
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

        elif sub_menu == "QR Maker":
            teks = st.text_input("Masukkan teks/password:")
            if st.button("Generate QR dari DNA + Lokasi"):
                if teks:
                    g = geocoder.ip('me')
                    lokasi = f"LAT:{g.latlng[0]},LON:{g.latlng[1]}" if g.ok else "LAT:0,LON:0"
                    full_text = f"{teks} | {lokasi}"
                    dna = text_to_dna(full_text)
                    qr = qrcode.make(dna)
                    buf = BytesIO()
                    qr.save(buf, format="PNG")
                    st.image(buf.getvalue(), caption="QR Code", width=200)
                    st.download_button("Download QR", buf.getvalue(), file_name="dna_qr.png")

        elif sub_menu == "SOS Settings":
            st.subheader("Email Darurat")
            current = get_sos_email(st.session_state.email)
            st.info(f"Email SOS sekarang: {current if current else 'Belum diset'}")
            sos_email = st.text_input("Masukkan email penerima SOS")
            if st.button("Update Email SOS"):
                update_sos_email(st.session_state.email, sos_email)
                st.success("Email SOS berhasil diperbarui!")
