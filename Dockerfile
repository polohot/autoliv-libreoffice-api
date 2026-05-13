# Use Miniforge3 as the base image
FROM condaforge/miniforge3:latest

# Install LibreOffice, Python UNO bindings, and CJK fonts for Multilingual support
RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-script-provider-python \
    python3-uno \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy environment file
COPY environment.yml .

# Configure conda to ignore SSL (as requested) and create the environment
RUN conda config --set ssl_verify false && \
    conda env create -f environment.yml

# Copy application code
COPY app.py util.py ./

# Expose the API port
EXPOSE 8000

# Ensure the conda environment is activated when running the app
# We use uvicorn to run the FastAPI app on port 8000
CMD ["conda", "run", "--no-capture-output", "-n", "autoliv-libreoffice-api", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]