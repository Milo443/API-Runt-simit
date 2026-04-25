# Use an official Python runtime as a parent image
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV TESSERACT_CMD=/usr/bin/tesseract

# Install system dependencies
# tesseract-ocr: motor OCR necesario para la app
# librerias libgl1 y libglib2.0-0: necesarias para opencv-python
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

FROM base AS deps

# Instalacion de uv para gestion rapida de dependencias
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copiar el archivo de requerimientos (sin torch/easyocr ya que se eliminaron)
COPY requirements.txt .

# Instalar dependencias python
# Se eliminan los flags de extra-index-url ya que PyTorch fue removido
RUN uv pip install --no-cache-dir --system -r requirements.txt

FROM deps AS runtime

WORKDIR /app

# Copiar el resto del codigo de la aplicacion
COPY . .

# Crear el directorio de logs y storage
RUN mkdir -p logs storage/mass_results

# Exponer el puerto 8000
EXPOSE 8000

# Comando para ejecutar la aplicacion
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
