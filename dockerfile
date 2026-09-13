FROM python:3.10-slim

# Instalăm FFmpeg pentru procesarea video
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiem dependințele și le instalăm
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiem tot codul aplicației
COPY . .

# Setăm portul oficial 7860 cerut de Hugging Face
EXPOSE 7860

# Pornim Streamlit pe portul 7860
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
