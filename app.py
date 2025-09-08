import streamlit as st
import qrcode
from io import BytesIO
from PIL import Image
import geocoder
import random, string
import numpy as np
import cv2

# Mapping
binary_to_dna = {"00":"A","01":"T","10":"G","11":"C"}
dna_to_binary = {v:k for k,v in binary_to_dna.items()}
complement_map = {"A":"T","T":"A","G":"C","C":"G"}

# --- Encode / Decode ---
def text_to_dna(text):
    binary = ''.join(format(ord(c), '08b') for c in text)
    return ''.join(binary_to_dna[binary[i:i+2]] for i in range(0, len(binary), 2))

def dna_to_text(dna_seq):
    binary = ''.join(dna_to_binary[b] for b in dna_seq)
    chars = [binary[i:i+8] for i in range(0, len(binary), 8)]
    return ''.join(chr(int(c,2)) for c in chars)

# --- Password Generator ---
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

# --- Streamlit UI ---
st.title("🧬 DNA Encoder/Decoder + QR Generator")

menu = st.sidebar.radio("Pilih Menu", ["Encode/Decode DNA", "QR Maker"])

if menu == "Encode/Decode DNA":
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

    if st.button("DNA Stats"):
        if teks:
            stats = {base: teks.count(base) for base in "ATGC"}
            st.write(stats)

    if st.button("Complement DNA"):
        if teks:
            comp = ''.join(complement_map.get(b,"") for b in teks)
            st.info(f"Complement: {comp}")

    if st.button("Reverse DNA"):
        if teks:
            st.info(f"Reverse: {teks[::-1]}")

    if st.button("Generate Complex Password"):
        password, dna_seq = generate_password()
        st.success(f"Password: {password}")
        st.text(f"DNA: {dna_seq}")

elif menu == "QR Maker":
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

    uploaded = st.file_uploader("Upload QR untuk decode", type=["png","jpg","jpeg"])
    if uploaded:
        file_bytes = np.asarray(bytearray(uploaded.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(img)

        if data:
            dna = data
            try:
                teks = dna_to_text(dna)
                st.success(f"DNA: {dna}")
                st.info(f"Pesan + Lokasi: {teks}")
            except:
                st.error("DNA tidak valid atau tidak bisa didecode!")
        else:
            st.error("QR tidak bisa dibaca!")
