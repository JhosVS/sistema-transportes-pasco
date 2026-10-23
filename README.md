# Sistema de Transporte con Predicción de Alta Ocupación y Agentes en la Nube
---

## 📌 Tabla de Contenidos (Índice)

1. [Credenciales de Prueba para Evaluación](#-credenciales-de-prueba-para-evaluación)
2. [Descripción General y Contexto del Proyecto](#-descripción-general-y-contexto-del-proyecto)
3. [Arquitectura y Tecnologías Cloud](#-arquitectura-y-tecnologías-cloud)
4. [Componentes Principales del Sistema](#-componentes-principales-del-sistema)
   * [1. Modelo Predictivo de Aprendizaje Automático](#1-modelo-predictivo-de-aprendizaje-automático)
   * [2. Red Multiagente y Supervisión](#2-red-multiagente-y-supervisión)
5. [Estructura del Proyecto](#-estructura-del-proyecto)
6. [Guía de Instalación y Ejecución Local](#-guía-de-instalación-y-ejecución-local-para-evaluadores)
7. [Explicación Detallada de Variables de Entorno (.env)](#-explicación-detallada-de-variables-de-entorno-env)
8. [Consideraciones de Seguridad y Buenas Prácticas](#-consideraciones-de-seguridad-y-buenas-prácticas)

---

## 🔑 Credenciales de Prueba para Evaluación

Para facilitar la revisión y evaluación del prototipo desplegado o en ejecución local, utilice la siguiente cuenta administrativa preconfigurada:

| Rol | Correo Electrónico | Contraseña |
| :--- | :--- | :--- |
| **Administrador General** | `admin@transportes.com` | `admin123` |

---

## 📑 Descripción General y Contexto del Proyecto

El presente proyecto implementa un prototipo web de apoyo a la toma de decisiones para la planificación de servicios de transporte interprovincial. El sistema toma como escenario de modelado a la empresa ficticia **Transportes Andina Pasqueña**, la cual opera rutas que conectan la ciudad de **Cerro de Pasco con Lima, Huánuco, Huancayo y Tarma**.

En la operación diaria, la demanda de pasajes presenta variaciones críticas influenciadas por el día de la semana, el mes, las tarifas, la proximidad de fines de semana y, de forma muy marcada, los **días feriados y sus vísperas**. La falta de herramientas predictivas suele conducir a dos problemas operativos fundamentales:

1. **Capacidad insuficiente:** Ausencia de unidades de refuerzo en salidas con sobredemanda, generando pérdida de ingresos y pasajeros no atendidos.
2. **Uso ineficiente de flota:** Despliegue de buses de gran capacidad en viajes de baja ocupación, incrementando los costos operativos.

Para solucionar esta problemática, esta solución integra un **modelo predictivo de aprendizaje automático** y una **red de agentes de inteligencia artificial** que analizan datos, estiman ocupación y formulan recomendaciones operativas auditadas antes de su aplicación por el personal administrativo.

---

## 🏗️ Arquitectura y Tecnologías Cloud

El sistema está diseñado bajo una arquitectura web desacoplada, modular y segura:

* **Frontend:** Interfaz web desarrollada con plantillas HTML5, CSS3 y JavaScript interactivo para la visualización de dashboards y calendarios de ocupación.
* **Backend:** Construido en **Python 3.10+** utilizando el framework **Flask**, desplegado en producción sobre el servicio cloud **Render** mediante el servidor WSGI **Gunicorn**.
* **Base de Datos:** Motor relacional **MySQL** alojado en la nube gestionada de **Aiven**, configurado con conexiones seguras mediante cifrado TLS/SSL.
* **Modelo de Machine Learning:** Clasificador supervisado serializado en formato `.joblib` para inferencia rápida en servidor.
* **Red Multiagente:** Integración con la API oficial de **Google Gemini (`google-genai`)** para la generación de explicaciones, recomendaciones y análisis en lenguaje natural.

---

## 🤖 Componentes Principales del Sistema

### 1. Modelo Predictivo de Aprendizaje Automático

El sistema incluye un modelo probabilístico entrenado con **2,577 viajes simulados** ordenados temporalmente. La tarea consiste en predecir la variable binaria `alta_ocupacion` ($\ge 70\%$ de asientos vendidos).

* **Algoritmo Seleccionado:** **Gradient Boosting Classifier** (evaluado y seleccionado frente a Random Forest, Regresión Logística, KNN y Árboles de Decisión por presentar el mayor AUC en validación).
* **Métricas de Desempeño (en conjunto de prueba de 387 viajes):**
  * **AUC (Área bajo la curva ROC):** $0.940$
  * **Exactitud Global:** $86.8\%$ (superando en +20.2% a la línea base de clase mayoritaria).
  * **Medida F1:** $0.800$
  * **Puntuación de Brier:** $0.092$ (excelente calibración probabilística).
* **Variables de Entrada:** Día de la semana, mes, día del mes, bandera de fin de semana, feriado nacional, víspera de feriado, ID de ruta, sedes de origen/destino, distancia en km, hora de salida decimal, precio del pasaje y capacidad del vehículo.

### 2. Red Multiagente y Supervisión

Para transformar los datos brutos y las predicciones en decisiones claras, el sistema despliega una red de agentes con responsabilidades no redundantes:

1. **Orquestador (Motor de Reglas - Sin LLM):** Valida la entrada del usuario, aplica límites de tokens y peticiones, gestiona memoria caché de 10 minutos, direcciona las tareas hacia los agentes especializados y ejecuta rutinas de sincronización.
2. **Agente Analista (LLM + SQL):** Consulta métricas históricas de la base de datos, rutas más transitadas, estado de la flota y rendimiento por periodos.
3. **Agente Predictor (LLM + Modelo ML):** Consume el modelo `.joblib` para calcular la probabilidad de alta ocupación de salidas específicas y alertar sobre la necesidad de reentrenamiento.
4. **Agente Asesor (LLM + Reglas de Negocio):** Examina los hallazgos para proponer decisiones operativas clasificadas por prioridad (Alta, Media, Baja), como habilitar buses extra o ajustar tarifas.
5. **Agente Auditor (Motor de Reglas - Sin LLM):** **Componente crítico de control.** Lee las respuestas en texto generadas por los agentes con LLM y verifica cada cifra contra los datos reales devueltos por las herramientas. Si detecta discrepancias o alucinaciones numéricas, fuerza la reescritura o adjunta un aviso explicativo.
6. **Revisión Humana (Human-in-the-Loop):** Toda sugerencia debe ser aprobada por el administrador del sistema antes de ejecutarse en la operación real.

---

## 📂 Estructura del Proyecto

```text
sistema-transportes-pasco/
├── app/
│   ├── admin/          # Módulos del panel de administración (Dashboards, Informes, Personal)
│   ├── auth/           # Rutas de autenticación, control de acceso y seguridad
│   ├── egresado/       # Módulo para usuarios / perfil egresado o cliente
│   ├── public/         # Vistas públicas, landing page y consultas informativas
│   ├── static/         # Archivos estáticos (CSS, JS, imágenes)
│   ├── templates/      # Plantillas Jinja2 organizadas por secciones y roles
│   ├── utils/          # Conectores de API, utilidades de PDF, email y helpers del sistema
│   ├── extensions.py   # Inicialización de extensiones Flask (SQLAlchemy, Bcrypt, etc.)
│   ├── models.py       # Declaración de modelos ORM y tablas de la base de datos
│   └── __init__.py     # Fábrica de la aplicación (Application Factory)
├── instance/           # Almacenamiento local de logs, certificados SSL y archivos temporales
├── .env.example        # Plantilla con el formato de variables de entorno requeridas
├── config.py           # Clases de configuración de Flask (Desarrollo, Producción, Pruebas)
├── requirements.txt    # Librerías y dependencias exactas de Python
└── run.py              # Punto de entrada para ejecutar la aplicación
```

---

## 💻 Guía de Instalación y Ejecución Local (Para Evaluadores)

Siga estos pasos detallados para desplegar y evaluar el prototipo en su entorno local:

### Prerrequisitos

* **Python 3.10** o superior instalado en el sistema.
* **Git** instalado.
* Acceso a una base de datos **MySQL** (local o remota).

### Paso 1: Clonar el Repositorio

```bash
git clone https://github.com/JhosVS/sistema-transportes-pasco.git
cd sistema-transportes-pasco
```

### Paso 2: Crear y Activar un Entorno Virtual

* **En Windows:**
  ```cmd
  python -m venv venv
  venv\Scripts\activate
  ```
* **En Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Paso 3: Instalar Dependencias

```bash
pip install -r requirements.txt
```

### Paso 4: Configurar las Variables de Entorno

Cree un archivo llamado `.env` en la raíz del proyecto basándose en `.env.example`:

```bash
cp .env.example .env
```

Edite el archivo `.env` recién creado y complete los valores requeridos.

### Paso 5: Inicializar la Base de Datos e Iniciar el Servidor

```bash
python run.py
```

El servidor web estará accesible desde cualquier navegador en:

👉 **`http://127.0.0.1:5000`**

---

## 🔑 Explicación Detallada de Variables de Entorno (`.env`)

| Variable | Tipo | Descripción y Propósito | Ejemplo / Valor por defecto |
| :--- | :--- | :--- | :--- |
| `FLASK_APP` | Texto | Define el punto de entrada de la aplicación para los comandos de Flask. | `run.py` |
| `FLASK_ENV` | Texto | Establece el entorno de ejecución (`development` o `production`). | `development` |
| `SECRET_KEY` | Texto | Clave secreta criptográfica para firmar cookies de sesión y CSRF. | `clave_secreta_para_sesiones_y_flash` |
| `DB_HOST` | Texto | Dirección IP o host del servidor MySQL. | `localhost` o servidor de Aiven |
| `DB_USER` | Texto | Nombre del usuario de la base de datos MySQL. | `root` |
| `DB_PASSWORD` | Texto | Contraseña del usuario de la base de datos MySQL. | *(Su contraseña local)* |
| `DB_NAME` | Texto | Nombre exacto de la base de datos del proyecto. | `agencia_transportes` |
| `DB_PORT` | Número | Puerto TCP de red por el cual escucha MySQL. | `3306` |
| `APISPERU_TOKEN` | Texto | Token de la API externa ApisPerú para consultas de DNI/RUC. | `tu_token_de_apis_peru` |
| `GEMINI_API_KEY` | Texto | Llave de API oficial de Google AI Studio para los agentes (**Google Gemini**). | `tu_token_de_gemini` |

---

## 🛡️ Consideraciones de Seguridad y Buenas Prácticas

1. **Protección de Secretos:** Ninguna clave de API o contraseña se encuentra expuesta en el código fuente pública. Todo se gestiona a través del archivo `.env` (incluido en `.gitignore`).
2. **Supervisión y Control:** Las predicciones emitidas por el modelo ML y las recomendaciones formuladas por la red multiagente actúan exclusivamente como herramientas de apoyo a la decisión, requiriendo confirmación humana antes de cualquier cambio operativo.