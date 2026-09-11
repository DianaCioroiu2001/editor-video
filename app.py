import streamlit as st
import os
import subprocess
import requests

BUNNY_API_KEY="f2ad32f2-ba5b-4e31-ae46-51782e8536d59644de27-9601-4147-b209-1c53c7259464"

BUNNY_LIBRARIES = {
    "Grupa 5A": "742487",
    "Grupa 6A": "742488",
    "Grupa 6B": "742489",
    "Grupa 7A": "742490",
    "Grupa 7B": "742491",
    "Grupa 7C": "742492",
    "Grupa 8A": "742494",
    "Grupa 8B": "742495",
    "Grupa 8C": "742497",
    "Grupa 8D": "742498",
    "Grupa 8E": "742498"
}

WORDPRESS_URL = "https://www.levelup-dela0la10.ro/"
WP_USERNAME = "levelup"
WP_APP_PASSWORD = "Inginer@@01"

# ==========================================
# 2. FUNCȚIE PENTRU CALCULUL TIMPULUI
# ==========================================
def parse_time(time_str):
    parts = str(time_str).strip().split(':')
    try:
        if len(parts) == 1:
            return float(parts[0])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except ValueError:
        return 0
    return 0

# ==========================================
# 3. INTERFAȚA WEB (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Auto Video Publisher", page_icon="🎬")
st.title("🎬 Editor & Publicator Video Automat")
st.write("Încarcă videoclipul, selectează minutele, alege biblioteca Bunny și publică-l pe site!")

# Elemente de încărcare fișiere (Uploader)
video_file = st.file_uploader("1. Încarcă Videoclipul (MP4, MOV)", type=["mp4", "mov", "avi"])
bg_image = st.file_uploader("2. Imagine de Fundal - Opțional (JPG, PNG)", type=["jpg", "png", "jpeg"])

# Câmpuri text și opțiuni
title = st.text_input("Titlu Video / Postare WordPress", value="Videoclip Nou")
library_name = st.selectbox("3. Selectează Biblioteca Bunny", list(BUNNY_LIBRARIES.keys()))

col1, col2 = st.columns(2)

start_time = st.text_input("Timp Început (ex: 01:15 sau 75)", value="00:00")

end_time = st.text_input("Timp Sfârșit (ex: 02:30 sau 150)", value="01:00")

wp_status = st.radio("Status Postare WordPress", ["publish", "draft"], horizontal=True)

# ==========================================
# 4. EXECUTARE LA APĂSAREA BUTONULUI
# ==========================================
if st.button("🚀 Procesează și Publică", type="primary"):
if not video_file:
st.error("❌ Te rugăm să încarci un fișier video înainte de a procesa!")
else:
with st.spinner("⏳ Se procesează videoclipul în cloud... Te rugăm să aștepți."):

# Pasul A: Salvare fișiere încărcate local pe serverul temporar
temp_video_path = "temp_input.mp4"
with open(temp_video_path, "wb") as f:
f.write(video_file.getbuffer())

bg_path = None
if bg_image:
bg_path = "temp_bg.png"
with open(bg_path, "wb") as f:
f.write(bg_image.getbuffer())

# Calculare durată
start_sec = parse_time(start_time)
end_sec = parse_time(end_time)
duration = end_sec - start_sec

if duration <= 0:
st.error("❌ Timpul de sfârșit trebuie să fie mai mare decât timpul de început!")
else:
output_path = "output_processed.mp4"

# Pasul B: Procesare FFmpeg (Tăiere + Overlay Imagine Fundal)
try:
if bg_path:
cmd = [
'ffmpeg', '-y',
'-ss', str(start_sec),
'-i', temp_video_path,
'-i', bg_path,
'-t', str(duration),
'-filter_complex', '[1:v][0:v]overlay=(W-w)/2:(H-h)/2[out]',
'-map', '[out]', '-map', '0:a?',
'-c:v', 'libx264', '-crf', '23', '-preset', 'fast', '-c:a', 'aac',
output_path
]
else:
cmd = [
'ffmpeg', '-y',
'-ss', str(start_sec),
'-i', temp_video_path,
'-t', str(duration),
'-c:v', 'libx264', '-crf', '23', '-preset', 'fast', '-c:a', 'aac',
output_path
]
subprocess.run(cmd, check=True)
except Exception as e:
st.error(f"❌ Eroare la procesarea FFmpeg: {str(e)}")
st.stop()

# Pasul C: Încărcare pe Bunny.net
try:
library_id = BUNNY_LIBRARIES[library_name]

# 1. Creează obiectul video
create_url = f"https://video.bunny.net/library/{library_id}/videos"
headers = {"AccessKey": BUNNY_API_KEY, "Content-Type": "application/json"}
res = requests.post(create_url, json={"title": title}, headers=headers)

if res.status_code not in [200, 201]:
st.error(f"❌ Eroare creare video Bunny ({res.status_code}): {res.text}")
st.stop()

video_id = res.json().get("guid")

# 2. Urcă fișierul procesat
upload_url = f"https://video.bunny.net/library/{library_id}/videos/{video_id}"
with open(output_path, 'rb') as f:
upload_res = requests.put(upload_url, data=f, headers={"AccessKey": BUNNY_API_KEY})

if upload_res.status_code != 200:
st.error(f"❌ Eroare upload Bunny ({upload_res.status_code}): {upload_res.text}")
st.stop()
except Exception as e:
st.error(f"❌ Eroare conexiune Bunny.net: {str(e)}")
st.stop()

# Pasul D: Publicare pe WordPress
try:
iframe_code = (
f'<div style="position:relative;padding-top:56.25%;">'
f'<iframe src="https://iframe.mediadelivery.net/embed/{library_id}/{video_id}?autoplay=false" '
f'loading="lazy" style="border:0;position:absolute;top:0;left:0;height:100%;width:100%;" '
f'allowfullscreen="true"></iframe></div>'
)

wp_endpoint = f"{WORDPRESS_URL.rstrip('/')}/wp-json/wp/v2/posts"
wp_res = requests.post(
wp_endpoint,
json={"title": title, "content": iframe_code, "status": wp_status},
auth=(WP_USERNAME, WP_APP_PASSWORD)
)

# Ștergere fișiere temporare de pe disc
for p in [temp_video_path, output_path, bg_path]:
if p and os.path.exists(p):
os.remove(p)

if wp_res.status_code in [200, 201]:
post_link = wp_res.json().get("link")
st.success(f"✅ SUCCES! Videoclipul a fost urcat pe Bunny în '{library_name}' și publicat pe WordPress!")
st.markdown(f"🔗 **Link Articol:** [{post_link}]({post_link})")
else:
st.warning(f"⚠️ Video încărcat pe Bunny, dar postarea pe WordPress a eșuat ({wp_res.status_code}): {wp_res.text}")

except Exception as e:
st.error(f"❌ Eroare conexiune WordPress: {str(e)}")
