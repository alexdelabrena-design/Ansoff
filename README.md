Pectimex · Matrices de Oportunidades (Ansoff + Impacto×Esfuerzo)

App en Streamlit para:

Clasificar oportunidades en Matriz de Ansoff.

Evaluar Impacto × Esfuerzo con color por Alineación al propósito.

Generar un Score automático (0–100) y ajustarlo con sliders (pesos y supuestos).

Exportar Excel/CSV con la priorización y el cálculo completo.

🗂 Archivos del repo

app_pectimex_oportunidades.py → código de la app

requirements.txt → dependencias

(opcional) Sesión Estrategia 1 Pectimex.xlsx → tu Excel de oportunidades (o súbelo desde la app)

📥 Datos de entrada

La app espera una hoja llamada “Mapa de Oportunidades” con (mínimo) estas columnas:

Oportunidad

Descripción (opcional)

Requiere inversión inicial alta → Sí/No

Tiempo a implementación → Corto/Medio/Largo

Margen potencial → Baja/Media/Alta

Riesgo asociado → Bajo/Medio/Alto

Facilidad de ejecución → Alta/Media/Baja

Comentarios clave (opcional)

La fila de encabezados por defecto es la 6 (puedes cambiarla en la barra lateral).

⚙️ Cómo correr localmente
# 1) Crear y activar entorno (macOS/Linux)
python3 -m venv .venv
source .venv/bin/activate
# En Windows (PowerShell):
# python -m venv .venv
# .\.venv\Scripts\Activate.ps1

# 2) Instalar dependencias
pip install -r requirements.txt

# 3) Ejecutar la app
streamlit run app_pectimex_oportunidades.py


Abre: http://localhost:8501

☁️ Despliegue en Streamlit Community Cloud

Sube app_pectimex_oportunidades.py y requirements.txt a este repo (pestaña Add file → Upload files).

Ve a https://share.streamlit.io/
, conecta tu GitHub y selecciona este repo.

Archivo principal: app_pectimex_oportunidades.py.

Despliega y comparte la URL (puedes embeberla en Notion con un bloque Embed).

🧮 Cómo se calcula el Score (0–100)

Alineación al propósito (0–5) ponderada por:
Sabor 30%, Salud 30%, Variedad 20%, Origen 20% (ajustables en la barra lateral).

Impacto (0–1) = (peso Margen vs. Alineación) · Margen_normalizado + (resto) · Alineación_normalizada.

Esfuerzo (0–1) = promedio de Inversión (Sí/No), Tiempo (C/M/L), Facilidad (A/M/B), Riesgo (B/M/A).

Score = 100 × [ α·Impacto + (1−α)·(1−Esfuerzo) ] (α ajustable).

E-commerce B2B puede recibir un override de alineación (activar en la barra lateral).

🎛 Parámetros ajustables (barra lateral)

Pesos de Sabor/Salud/Variedad/Origen en la Alineación.

Margen vs. Alineación dentro de Impacto.

Impacto vs. (1−Esfuerzo) en el Score final.

Potenciar e-commerce B2B (alineación configurable).

📤 Exportables

Excel: priorización + hoja de cálculo completa.

CSV: priorización.

🐳 Docker (opcional)
docker build -t pectimex-app .
docker run -p 8501:8501 pectimex-app

🧩 Notas

Si cambias nombres de columnas u hoja, ajusta los campos en la barra lateral.

Python 3.9+ recomendado.
