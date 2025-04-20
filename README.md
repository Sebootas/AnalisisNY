# 🗽 NYC Business & Demographics Analyzer

Este proyecto permite analizar la relación entre negocios legalmente establecidos (incluyendo individuos con licencia) y el perfil demográfico por ZIP Code en la ciudad de Nueva York. Incluye una interfaz web personalizada para cargar nuevos datos, ejecutar análisis y visualizar resultados.

---

## 📁 Estructura principal del Proyecto

```
project-root/
│
├── .idea/                
│   ├── .gitignore/
│   ├── AnalisisNY
│   ├── modules.xml
│   ├── vcs.xml
│
├── client/                # Interfaz web (React)
│   ├── public/
│   ├── src/
│     ├── App.js
│     ├── App.css
│     ├── index.css
│     ├── index.js
│   ├── .gitignore
│   └── package.json
│
├── server/                # Lógica backend (Flask)
│   ├── app.py
│   └── requirements.txt
│
└── README.md
```

---

## 🚀 Instrucciones para ejecutar el proyecto

### 🔧 1. Clona el repositorio

```bash
git clone https://github.com/tuusuario/nyc-business-analyzer.git
cd nyc-business-analyzer
```

---

### 🖥️ 2. Backend (Flask API)

#### 📍 Ubicación: `server/`

```bash
cd server
pip install -r requirements.txt
python app.py
```

Esto iniciará la API en `http://localhost:5000`.

---

### 🌐 3. Frontend (React)

#### 📍 Ubicación: `client/`

```bash
cd client
npm install
npm install papaparse
npm start
```

Esto abrirá la aplicación en `http://localhost:3000`.

---

## 📊 Funcionalidades

- Carga de archivos CSV para negocios y demografía.
- Visualización de:
  - Distribución de industrias (gráfico de pastel).
  - Negocios por cada 1000 habitantes (barras).
  - Heatmap de correlaciones entre variables demográficas y concentración comercial.
- Análisis diferenciado al incluir individuos con licencia.

---

## 🧠 Requerimientos

### Python / Backend
- Flask
- Flask-CORS
- NumPy
- Pandas
- Matplotlib
- Seaborn
- Gunicorn (para despliegue si es necesario)

### JavaScript / Frontend
- React
- PapaParse (para procesar archivos CSV)

---

## 📬 Contacto

Proyecto realizado por **Sebastian Isaza**  
Para más información, consulta el PDF y presentación adjunta o visita el repositorio.

---
