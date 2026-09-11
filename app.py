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
# UTILITARE
# ==========================================
def parse_sec(t):
    p = str(t).strip().split(':')
    try:
        if len(p) == 1: return float(p[0])
        if len(p) == 2: return float(p[0])*60 + float(p[1])
        if len(p) == 3: return float(p[0])*3600 + float(p[1])*60 + float(p[2])
    except Exception:
        return 0
    return 0

st.set_page_config(page_title="Auto Video Publisher", page_icon="🎬")
st.title("🎬 Editor & Publicator Video Automat")

video_file = st.file_uploader("1. Încarcă Videoclipul", type=["mp4", "mov", "avi"])
bg_image = st.file_uploader("2. Imagine Fundal (Opțional)", type=["jpg", "png", "jpeg"])

title = st.text_input("Titlu Video / Postare", value="Videoclip Nou")
library_name = st.selectbox("3. Selectează Biblioteca Bunny", list(BUNNY_LIBRARIES.keys()))

start_time = st.text_input("Timp Început (ex: 01:15 sau 75)", value="00:00")
end_time = st.text_input("Timp Sfârșit (ex: 02:30 sau 150)", value="01:00")

wp_status = st.radio("Status WordPress", ["publish", "draft"], horizontal=True)

if st.button("🚀 Procesează și Publică", type="primary"):
    if not video_file:
        st.error("❌ Te rugăm să încarci un fișier video!")
    else:
        try:
            with st.spinner("⏳ Se procesează videoclipul în cloud..."):
                temp_video_path = "temp_input.mp4"
                with open(temp_video_path, "wb") as f:
                    f.write(video_file.getbuffer())
                
                bg_path = None
                if bg_image:
                    bg_path = "temp_bg.png"
                    with open(bg_path, "wb") as f:
                        f.write(bg_image.getbuffer())

                start_sec = parse_sec(start_time)
                end_sec = parse_sec(end_time)
                duration = end_sec - start_sec

                if duration <= 0:
                    st.error("❌ Timpul de sfârșit trebuie să fie mai mare decât timpul de început!")
                else:
                    output_path = "output_processed.mp4"
                    
                    # Comandă FFmpeg optimizată pentru memorie redusă
                    if bg_path:
                        cmd = [
                            'ffmpeg', '-y',
                            '-ss', str(start_sec),
                            '-i', temp_video_path,
                            '-i', bg_path,
                            '-t', str(duration),
                            '-filter_complex', '[1:v][0:v]overlay=(W-w)/2:(H-h)/2[out]',
                            '-map', '[out]', '-map', '0:a?',
                            '-c:v', 'libx264', '-crf', '28', '-preset', 'ultrafast',
                            '-threads', '2', '-c:a', 'aac',
                            output_path
                        ]
                    else:
                        cmd = [
                            'ffmpeg', '-y',
                            '-ss', str(start_sec),
                            '-i', temp_video_path,
                            '-t', str(duration),
                            '-c:v', 'libx264', '-crf', '28', '-preset', 'ultrafast',
                            '-threads', '2', '-c:a', 'aac',
                            output_path
                        ]
                    
                    res_cmd = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if res_cmd.returncode != 0:
                        st.error(f"❌ Eroare FFmpeg: {res_cmd.stderr.decode('utf-8')[-500:]}")
                        st.stop()

                    # 2. Upload Bunny.net
                    library_id = BUNNY_LIBRARIES.get(library_name)
                    create_url = f"https://dash.bunny.net/stream/{library_id}/library/overview"
                    headers = {
    "AccessKey": BUNNY_API_KEY,
    "Content-Type": "application/json",
    "accept": "application/json"
}

res = requests.post(create_url, json={"title": title}, headers=headers)
if res.status_code not in [200, 201]:
    st.error(f"❌ Eroare la crearea clipului în Bunny ({res.status_code}): {res.text}")
    st.stop()

video_id = res.json().get("guid")

# 2. Încarcă fișierul fizic (PUT)
upload_url = f"https://video.bunnycdn.com/library/{library_id}/videos/{video_id}"
upload_headers = {
    "AccessKey": BUNNY_API_KEY,
    "Content-Type": "application/octet-stream"
}

with open(output_path, 'rb') as f:
    up_res = requests.put(upload_url, data=f, headers=upload_headers)

                    if up_res.status_code != 200:
                        st.error(f"❌ Eroare la încărcarea fișierului pe Bunny ({up_res.status_code}): {up_res.text}")
                        st.stop()

                    # 3. Publicare WordPress
                    iframe_code = f'<div style="position:relative;padding-top:56.25%;"><iframe src="https://iframe.mediadelivery.net/embed/{library_id}/{video_id}?autoplay=false" loading="lazy" style="border:0;position:absolute;top:0;left:0;height:100%;width:100%;" allowfullscreen="true"></iframe></div>'
                    
                    wp_endpoint = f"{WORDPRESS_URL.rstrip('/')}/wp-json/wp/v2/posts"
                    wp_res = requests.post(
                        wp_endpoint,
                        json={"title": title, "content": iframe_code, "status": wp_status},
                        auth=(WP_USERNAME, WP_APP_PASSWORD)
                    )

                    if wp_res.status_code in [200, 201]:
                        post_link = wp_res.json().get("link")
                        st.success("✅ Succes complet!")
                        st.markdown(f"🔗 **Vezi postarea pe WordPress:** [{post_link}]({post_link})")
                    else:
                        st.warning(f"⚠️ Video încărcat pe Bunny, dar WordPress a dat eroare ({wp_res.status_code}): {wp_res.text}")

                    # Curățare fișiere
                    for p in [temp_video_path, output_path, bg_path]:
                        if p and os.path.exists(p): os.remove(p)

        except Exception as e:
            st.error(f"❌ A apărut o eroare la procesare: {str(e)}")
