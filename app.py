import os 
import subprocess
import requests
import streamlit as st

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

def parse_time(time_str):
    parts = str(time_str).strip().split(':')
    try:
        if len(parts) == 1:
            return float(parts[0])
        elif len(parts) ==2:
            return float(parts[0])*60 + float(parts[1])
        elif len(parts) ==3:
            return float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
    except ValueError:
        return 0
    return 0
def process_and_publish(video_file, start_time, end_time, bg_image, title, library_name, wp_status):
    if not video_file:
        return "Eroare: Nu ai incarcat niciun videoclip!"

        library_id = BUNNY_LIBRARIES.get(library_name)
        if not library_id:
            return f"Eroare: Biblioteca '{library_name}' nu a fost gasita!"

    start_sec = parse_time(start_time)
    end_sec = parse_time(end_time)
    duration = end_sec-start_sec

    if duration <= 0:
        return "Eroare: Timpul de sfarsit trebuie sa fie mai mare decat timpul de inceput!"

        output_path = "output_processed.mp4"

        try:
            if bg_imgae:
                cmd = [
                    'ffmpeg', '-y',
                    '-ss', str(start_sec),
                    '-i', video_file,
                    '-i', bg_image,
                    '-t', str(duration),
                    '-filter_complex', '[1:v][0:v]overlay=(W-w)/2:(H-h)/2[out]',
                    '-map', '[out]', '-map', '0:a?',
                    '-c:v', 'libx264', '-crf', '23', '-preset', 'fast', '-c:a', 'aac', 
                    output_path
                    ]
            else:
                cmd =[
                    'ffmpeg', '-y',
                    '-ss', str(start_sec),
                     '-i', video_file,
                    '-t', str(duration),
                     '-c:v', 'libx264', '-crf', '23', '-preset', 'fast', '-c:a', 'aac', 
                    output_path
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVINULL, stderr=subprocess.PIPE)
        except Exception as e:
            return f"Eroare la procesarea video: {str(e)}"

            try:
                create_url = f"https://video.bunny.net/library/{library_id}/videos"
                headers = {"AccessKey": BUNNY_API_KEY, "Content-Type": "application/json"}
                res = request.post(create_url, json = {"title": title}, headers = headers)

                if res.status_code not in [200, 201]:
                    return f"Eroare creare video Bunny ({res.status_code}):{res.text}"

                video_id = res.json().get("guid")

                upload_url = f"https://video.bunny.net/library/{library_id}/videos/{video_id}"

                with open(output_path, 'rb') as f:
                    upload_res = requests.put(upload_url, data=f, headers={"AccesKey": BUNNY_API_KEY})

                    if upload_res.status_code != 200:
                        retuirn f"Eroare upload Bunny ({upload_res.status_code}):{upload_res.text}"
            except Exception as e:
                return f"Eroare conexiune Bunny: {str(e)}"

                try:
                    iframe_code = (
                        f'<div style="position:relative;padding-top:56.25%;">'
                        f'<iframe src="https://iframe.mediadelivery.net/embed/{library_id}/{video_id}?autoplay=false"'
                        f'loading="lazy" style ="border:0; position:absolute;top:0;left:0;height:100%;width:100%;"'
                        f'allowfullscreen="true"></iframe></div>'
                        )

                    wp_endpoint = f"{WORDPRESS_URL.rstrip('/')}/wp-json/wp/v2/posts"
                    wp_res = requests.post(
                        wp_endpoint,
                        json={"title":title, "content":iframe_code}, "status":wp_status},
                        auth=(WP_USERNAME, WP_APP_PASSWORD)
                    )

                    if os.path.exists(output_path):
                        os.remove(output_path)

                    if wp_res.status_code in [200, 201]:
                        post_link = wp_res.json().get("link")
                        return f"SUCCES! Uploadat in '{library_name' si publicat pe WordPres..\n Link articol: {post_link}"
                    else:
                        return f"Videoclipul este pe Bunny, dar postarea pe Wordpress a esuat ({wp_res.status_code}): {wp_res.text}"
                except Exception as e:
                    return f"Eroare conexiune WordPress: {str(e)}"
                    with gr.Blocks(title="Auto Video Publisher") as demo:
                        gr.Markdown("# Editor & Publicator Video Automat ")
                        with gr.Row():
                            with gr.Column():
                                video_input = st.file_uploader(label="1.Incarca Video")
                                bg_input - st.file_uploader(type="filepath", label="2.Imagine Fundal")
                            with gr.Column():
                                title_input = st.text_input(label="Titlu Video", value = "Videoclip Nou")
                                library_input = st.selectbox(
                                    choices = list(BUNNY_LIBRARIES.keys()),
                                    value = list(BUNNY_LIBRARIES.keys())[0],
                                    label = "3.Selecteaza Bbiblioteca Bunny"
                                )
                            with gr.Row():
                                start_input =st.text_input(label="Timp Inceput, ex. 01:15", value="00:00")
                                end_input = st.text_input(label = "Timp Sfarsit", value="01:00")
                                status_input = st.radio(["publish", "draft"], label="Status WordPress", value="publish")
                                btn=st.Button("Proceseaza si Publica", variant="primary")
                                output_text = st.text_input(label="Rezultat/Status Procesare", lines=4)
                                btn.click(
                                    fn=process_and_publish,
                                    inputs=[video_input, start_input, end_input, bg_input, title_input, library_input, status_input],
                                    outputs=output_text
                                )
                                    demo.lunch()
                    
