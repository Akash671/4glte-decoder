# Streamlit GUI image — this is the one Hugging Face Spaces (Docker SDK) runs.
FROM python:3.11-slim

WORKDIR /code

# System deps for pycrate / cryptography extras (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Hugging Face Spaces expects the app to listen on 7860
ENV PORT=7860
EXPOSE 7860

# Streamlit needs these to run headless and bind to 0.0.0.0 inside a container
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    DECODER_MODE=local

CMD ["sh", "-c", "streamlit run app/streamlit_app.py --server.port=${PORT} --server.address=0.0.0.0"]
