# 🚦 Orquestador RUNT API

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/AWS-%23FF9900.svg?style=for-the-badge&logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)

API robusta diseñada para la **orquestación de consultas y trámites** ante el sistema RUNT (Registro Único Nacional de Tránsito) y SIMIT. Este sistema permite consolidar información de múltiples fuentes en una interfaz unificada, escalable y optimizada para despliegues en la nube.

---

## 🚀 Funcionalidades Principales

### 🔍 Consulta Integral
Unifica la información de múltiples fuentes en una sola respuesta JSON enriquecida:
- **RUNT Ciudadano**: Datos básicos y licencias de conducción.
- **RUNT Vehículo**: Información técnica, gravámenes y antecedentes.
- **SIMIT**: Infracciones y acuerdos de pago (incluye resolución de qxCaptcha/PoW).

### 📊 Procesamiento Masivo
Módulo especializado para el procesamiento de grandes volúmenes de datos:
- Carga de datos vía archivos **Excel (.xlsx)**.
- Aplicación de filtros de negocio avanzados (Conductor Laboral, Rodamiento).
- Notificaciones en tiempo real del progreso mediante **WebSockets**.
- Generación de reportes consolidados en formato Excel.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
| :--- | :--- |
| **Framework** | FastAPI + Uvicorn |
| **Bases de Datos** | Oracle (thick mode), PostgreSQL |
| **Data Processing** | Polars (Análisis de datos de alto rendimiento) |
| **Web Scraping** | Playwright / Requests |
| **Concurrency** | ThreadPoolExecutor (Especial para queries bloqueantes de Oracle) |
| **Deployment** | Docker, AWS Lambda (via Mangum), AWS EKS |

---

## 📁 Estructura del Proyecto

El proyecto sigue una arquitectura modular y escalable dividida por dominios:

```text
app/
├── core/           # Configuración global, logging y metadatos
├── db/             # Gestión de conexiones, pools y túneles SSH
├── procesos/       # Lógica de negocio (un dominio por carpeta)
│   ├── r_integral/ # Orquestador individual
│   ├── r_masiva/   # Procesamiento masivo por Excel
│   └── shared/     # Utilidades compartidas
└── main.py         # Punto de entrada de la aplicación
```

---

## ⚙️ Configuración e Instalación

### 1. Requisitos Previos
- Python 3.10+
- [Oracle Instant Client](https://www.oracle.com/database/technologies/instant-client.html) (Requerido para modo `thick`)
- Docker (Opcional para despliegue en contenedores)

### 2. Instalación Local
```bash
# Clonar el repositorio
git clone http://.../OrquestadorRUNT.git
cd API-RUNT

# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Variables de Entorno
Crea un archivo `.env` basado en `.env.example`:
```env
APP_NAME="Orquestador RUNT API"
APP_ENV=dev
DB_THREAD_WORKERS=10
RUNT_VEHICULO_API_BASE=https://...
SIMIT_API_BASE=https://...
```

### 4. Ejecución
```bash
# Desarrollo con recarga automática
uvicorn app.main:app --reload --port 8000
```

---

## 📖 Documentación de la API

Una vez que la API esté corriendo, puedes acceder a la documentación interactiva en:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

La documentación incluye ejemplos de respuesta, esquemas de validación y descripciones detalladas de cada endpoint.

---

## 🛠️ Guía de Desarrollo

Para agregar nuevas funcionalidades o modificar la lógica existente, consulta los siguientes documentos detallados:
- 📑 [Arquitectura Detallada](ARQUITECTURA.md): Patrones de diseño, caché y manejo de concurrencia.
- 💾 [Integración de Base de Datos](DOCUMENTACION_DB_INTEGRATION.md): Guía para configurar nuevas fuentes de datos.

---

## 👤 Autor
Desarrollado con ❤️ por **Camilo Calderon** (@Milo443).