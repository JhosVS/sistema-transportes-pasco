# Sistema de Transporte con Predicción de Alta Ocupación y Agentes en la Nube

> **Proyecto de Investigación y Desarrollo Técnico**  
> **Autor:** Valladares Solís, Jhoshua Elí  
> **Institución:** Universidad Nacional Daniel Alcides Carrión (UNDAC)  
> **Escuela:** Ingeniería de Sistemas y Computación  

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
Abra su terminal o consola de comandos y ejecute:
```bash
git clone https://github.com/JhosVS/sistema-transportes-pasco.git
cd sistema-transportes-pasco
```

### Paso 2: Crear y Activar un Entorno Virtual
Se recomienda utilizar un entorno virtual para aislar las dependencias del proyecto:

* **En Windows:**
  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```
* **En Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Paso 3: Instalar Dependencias
Instale todos los paquetes requeridos especificados en `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Paso 4: Configurar las Variables de Entorno
Cree un archivo llamado `.env` en la raíz del proyecto basándose en el archivo `.env.example`:

* **En Linux/macOS o PowerShell:**
  ```bash
  cp .env.example .env
  ```
* **En Windows (CMD):**
  ```cmd
  copy .env.example .env
  ```

Edite el archivo `.env` recién creado con un editor de texto y complete los valores requeridos (consulte la sección de la guía de variables a continuación).

### Paso 5: Inicializar la Base de Datos y Iniciar el Servidor
Una vez configuradas las credenciales de la base de datos en el archivo `.env`, ejecute:

```bash
python run.py
```

El servidor web se iniciará de forma predeterminada y estará accesible desde cualquier navegador en la dirección:  
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Explicación Detallada de Variables de Entorno (`.env`)

Para que el evaluador comprenda la función de cada parámetro de configuración, a continuación se describe el propósito de cada variable definida en el archivo `.env.example`:

| Variable | Tipo | Descripción y Propósito | Ejemplo / Valor por defecto |
| :--- | :---: | :--- | :--- |
| `FLASK_APP` | Texto | Define el punto de entrada de la aplicación para los comandos de Flask. | `run.py` |
| `FLASK_ENV` | Texto | Establece el entorno de ejecución (`development` para depuración o `production` para despliegue). | `development` |
| `SECRET_KEY` | Texto | Clave secreta criptográfica utilizada por Flask para firmar cookies de sesión y proteger formularios contra ataques CSRF. | `clave_secreta_para_sesiones_y_flash` |
| `DB_HOST` | Texto | Dirección de IP o nombre de host del servidor donde está alojada la base de datos MySQL. | `localhost` o servidor de Aiven |
| `DB_USER` | Texto | Nombre del usuario con permisos para consultar y escribir en la base de datos MySQL. | `root` |
| `DB_PASSWORD` | Texto | Contraseña de acceso correspondiente al usuario de la base de datos MySQL. | *(Su contraseña local)* |
| `DB_NAME` | Texto | Nombre exacto del esquema o base de datos relacional del proyecto. | `agencia_transportes` |
| `DB_PORT` | Número | Puerto TCP de red por el cual escucha el servicio MySQL. | `3306` |
| `APISPERU_TOKEN` | Texto | Token de autenticación de la API externa ApisPerú utilizada para consultas rápidas de validación de identidad (DNI/RUC). | `tu_token_de_apis_peru` |
| `GEMINI_API_KEY` | Texto | Llave de API oficial de Google AI Studio requerida para habilitar la comunicación de la red multiagente con el modelo de lenguaje **Google Gemini**. | `tu_token_de_gemini` |

---

## 🛡️ Consideraciones de Seguridad y Buenas Prácticas

1. **Protección de Secretos:** Ninguna clave de API, contraseña de base de datos o credencial privada está incrustada en el código fuente pública. Todo se gestiona a través de las variables de entorno del archivo `.env` (el cual está incluido en `.gitignore`).
2. **Supervisión y Control:** Las predicciones emitidas por el modelo de Machine Learning y las recomendaciones formuladas por la red multiagente actúan exclusivamente como herramientas de apoyo. Ninguna acción destructiva o cambio tarifario se ejecuta de forma automática sin confirmación humana explícita.