import os
import tempfile
import streamlit as st
import requests
import json
import re
import subprocess
# ==========================================
# CONFIGURARE BUNNY, WORDPRESS & CAPITOLE
# ==========================================

BUNNY_STREAM_API_KEY="f2ad32f2-ba5b-4e31-ae46-51782e8536d59644de27-9601-4147-b209-1c53c7259464"
LIBRARY_ID="742487"
BUNNY_LIBRARIES = {
    "Grupa 5A": {
        "id": "742487",  
        "api_key": "f4bf6266-4c1e-4904-bc517e5bfffd-4cbd-4220"
    },
    # "Grupa 5A": "742487",
    # "Grupa 6A": "742488",
    # "Grupa 6B": "742489",
    # "Grupa 7A": "742490",
    # "Grupa 7B": "742491",
    # "Grupa 7C": "742492",
    # "Grupa 8A": "742494",
    # "Grupa 8B": "742495",
    # "Grupa 8C": "742497",
    # "Grupa 8D": "742498",
    # "Grupa 8E": "742498"
}
# Aici pui Capitolele din Cursuri și ID-ul lor real din Tutor LMS
TOPICS = {
    "Clasa V -> GRUPA 5A": 404,  # Înlocuiește 512 cu ID-ul real al topicului GRUPA 5A
    "Clasa V -> GRUPA 5B": 513
}

COURSE_ID = 404
WORDPRESS_URL = "https://www.levelup-dela0la10.ro/"
WP_USERNAME = "levelup"
WP_APP_PASSWORD = "qHWT At8z apjV 4Rsl AbHc 9fTZ"
st.set_page_config(
    page_title="Procesare Video & Automatizare Tutor LMS",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 Editare Video & Inserare în Curs")
st.write("Încarcă videoclipul, specifică intervalele de tăiat și creează automat lecția în Tutor LMS.")

# ==========================================
# FORMULAR INTRARE
# ==========================================
uploaded_file = st.file_uploader("Alege fișierul video (MP4, MOV, AVI)", type=["mp4", "mov", "avi"])

selected_group = st.selectbox("Alege Grupa / Library-ul Bunny.net", list(BUNNY_LIBRARIES.keys()))

lesson_title = st.text_input("Titlu Lecție", placeholder="Ex: Lecția nr. 2 - Recapitulare și Exerciții")

st.markdown("---")
st.subheader("✂️ Configurare Tăiere & Trimming Video")

# Tăiere Început / Sfârșit
col_trim1, col_trim2 = st.columns(2)
with col_trim1:
    cut_start_sec = st.number_input("Tunde de la ÎNCEPUT (secunde)", min_value=0, value=0, step=1)
with col_trim2:
    cut_end_sec = st.number_input("Tunde de la SFÂRȘIT (secunde)", min_value=0, value=0, step=1)

st.markdown("##### 🔕 Șterge intervale intermediare din interiorul video-ului")
st.caption("Introdu intervale în format `MM:SS - MM:SS` sau `SS - SS` (Ex: `01:15 - 02:00, 10:30 - 11:00`)")

cut_intervals_input = st.text_input(
    "Intervale de șters (separate prin virgulă)",
    placeholder="01:15 - 02:00, 05:30 - 06:10"
)

wp_status = st.selectbox("Status Lecție în WordPress", ["publish", "draft"], index=0)

# ==========================================
# FUNCȚII AUXILIARE PENTRU TIMP ȘI FFmpeg
# ==========================================
def parse_time_to_seconds(time_str):
    time_str = time_str.strip()
    parts = time_str.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 1:
            return float(parts[0])
    except ValueError:
        return None
    return None

def get_video_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(result.stdout.strip())

def parse_intervals(intervals_str, total_duration, start_cut, end_cut):
    cuts = []
    
    if start_cut > 0:
        cuts.append((0, start_cut))
        
    if end_cut > 0 and (total_duration - end_cut) > start_cut:
        cuts.append((total_duration - end_cut, total_duration))

    if intervals_str.strip():
        raw_parts = intervals_str.split(",")
        for part in raw_parts:
            if "-" in part:
                s_str, e_str = part.split("-", 1)
                s_sec = parse_time_to_seconds(s_str)
                e_sec = parse_time_to_seconds(e_str)
                if s_sec is not None and e_sec is not None and s_sec < e_sec:
                    cuts.append((s_sec, e_sec))

    cuts.sort(key=lambda x: x[0])
    merged_cuts = []
    for c in cuts:
        if not merged_cuts:
            merged_cuts.append(c)
        else:
            prev_start, prev_end = merged_cuts[-1]
            if c[0] <= prev_end:
                merged_cuts[-1] = (prev_start, max(prev_end, c[1]))
            else:
                merged_cuts.append(c)

    keep = []
    current_pos = 0.0
    for cut_s, cut_e in merged_cuts:
        if cut_s > current_pos:
            keep.append((current_pos, cut_s))
        current_pos = max(current_pos, cut_e)
    
    if current_pos < total_duration:
        keep.append((current_pos, total_duration))

    return keep

def process_video_ffmpeg(input_path, output_path, keep_intervals):
    if len(keep_intervals) == 1 and keep_intervals[0][0] == 0:
        cmd = ["ffmpeg", "-y", "-i", input_path, "-c", "copy", output_path]
        subprocess.run(cmd, check=True)
        return

    filter_complex = ""
    concat_inputs = ""
    
    for idx, (start, end) in enumerate(keep_intervals):
        filter_complex += f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{idx}]; "
        filter_complex += f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{idx}]; "
        concat_inputs += f"[v{idx}][a{idx}]"
    
    filter_complex += f"{concat_inputs}concat=n={len(keep_intervals)}:v=1:a=1[outv][outa]"
    
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]
    
    subprocess.run(cmd, check=True)

# ==========================================
# EXECUTARE PROCES
# ==========================================
if st.button("🚀 Procesează și Adaugă în Curs", type="primary"):
    if not uploaded_file:
        st.error("Te rugăm să încarci un fișier video!")
    elif not lesson_title.strip():
        st.error("Te rugăm să introduci titlul lecției!")
    else:
        # Preluare credențiale specifice grupei alese
        library_info = BUNNY_LIBRARIES[selected_group]
        library_id = library_info["id"]
        bunny_api_key = library_info["api_key"]

        with st.spinner("1/3 Se procesează și se taie videoclipul conform intervalelor..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                input_video_path = os.path.join(temp_dir, "input_video.mp4")
                output_video_path = os.path.join(temp_dir, "output_processed.mp4")

                with open(input_video_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                total_duration = get_video_duration(input_video_path)
                keep_intervals = parse_intervals(cut_intervals_input, total_duration, cut_start_sec, cut_end_sec)

                try:
                    process_video_ffmpeg(input_video_path, output_video_path, keep_intervals)
                except Exception as e:
                    st.error(f"Eroare la procesarea FFmpeg: {e}")
                    st.stop()

                # 2. Upload Video pe Bunny Stream
                st.spinner(f"2/3 Se încarcă video-ul în librăria Bunny.net ({selected_group})...")
                headers_bunny = {
                    "AccessKey": bunny_api_key,
                    "Content-Type": "application/json"
                }

                # a. Creare ID Video pe Bunny
                create_url = f"https://video.bunnycdn.com/library/{library_id}/videos"
                create_res = requests.post(create_url, json={"title": lesson_title}, headers=headers_bunny)
                
                if create_res.status_code not in [200, 201]:
                    st.error(f"Eroare Bunny CDN la creare video: {create_res.text}")
                    st.stop()

                video_id = create_res.json()["guid"]

                # b. Upload fișier video procesat
                upload_url = f"https://video.bunnycdn.com/library/{library_id}/videos/{video_id}"
                with open(output_video_path, "rb") as video_file:
                    upload_res = requests.put(
                        upload_url,
                        data=video_file,
                        headers={"AccessKey": bunny_api_key, "Content-Type": "application/octet-stream"}
                    )

                if upload_res.status_code not in [200, 201]:
                    st.error(f"Eroare Bunny CDN la upload fișier: {upload_res.text}")
                    st.stop()

                # 3. Creare Lecție în WordPress prin API-ul Custom
                st.spinner("3/3 Se creează lecția în Tutor LMS...")
                iframe_code = f'<div style="position:relative;padding-top:56.25%;"><iframe src="https://iframe.mediadelivery.net/embed/{library_id}/{video_id}?autoplay=false" loading="lazy" style="border:0;position:absolute;top:0;left:0;height:100%;width:100%;" allowfullscreen="true"></iframe></div>'

                lesson_payload = {
                    "title": lesson_title,
                    "content": iframe_code,
                    "course_id": COURSE_ID,
                    "status": wp_status
                }

                custom_endpoint = f"{WORDPRESS_URL.rstrip('/')}/wp-json/custom/v1/create-lesson"
                wp_res = requests.post(
                    custom_endpoint,
                    json=lesson_payload,
                    auth=(WP_USERNAME, WP_APP_PASSWORD)
                )

                if wp_res.status_code in [200, 201] and wp_res.json().get("success"):
                    res_data = wp_res.json()
                    post_link = res_data.get("link")
                    st.success(f"✅ Lecția '{lesson_title}' a fost adăugată cu succes!")
                    st.markdown(f"🔗 **Deschide noua lecție în Curs:** [{post_link}]({post_link})")
                else:
                    st.error(f"⚠️ Eroare la asocierea cu WordPress ({wp_res.status_code}): {wp_res.text}")
