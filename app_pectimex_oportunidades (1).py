
import io
import re
import json
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Pectimex · Oportunidades", layout="wide")

st.title("Pectimex · Clasificador de Oportunidades")
st.caption("Matrices: **Ansoff** y **Impacto × Esfuerzo × Alineación al propósito** con parámetros ajustables.")

# -----------------------
# Sidebar · Parámetros
# -----------------------
st.sidebar.header("Parámetros de cálculo")

# Archivo
st.sidebar.subheader("Archivo fuente")
header_row_1idx = st.sidebar.number_input("Fila de encabezados (1-index)", min_value=1, max_value=50, value=6, step=1,
                                          help="Fila donde están los nombres de columnas. En tu archivo actual es la 6.")
sheet_name = st.sidebar.text_input("Nombre de hoja", value="Mapa de Oportunidades")

# Pesos de alineación (0–100) — se normalizan internamente
st.sidebar.subheader("Alineación con propósito (pesos)")
w_sabor    = st.sidebar.slider("Sabor", 0, 100, 30)
w_salud    = st.sidebar.slider("Salud", 0, 100, 30)
w_variedad = st.sidebar.slider("Variedad", 0, 100, 20)
w_origen   = st.sidebar.slider("Origen regional", 0, 100, 20)
sum_w = w_sabor + w_salud + w_variedad + w_origen
if sum_w == 0:
    w_sabor = w_salud = w_variedad = w_origen = 25
    sum_w = 100
weights = { "sabor": w_sabor/sum_w, "salud": w_salud/sum_w, "variedad": w_variedad/sum_w, "origen": w_origen/sum_w }
st.sidebar.write(f"**Suma:** {sum_w} (se normaliza a 100)")

# Composición del Impacto y Score final
st.sidebar.subheader("Composición de métricas")
w_margen_vs_aline = st.sidebar.slider("Impacto: peso de Margen vs Alineación (Margen ←→ Alineación)", 0, 100, 40)
w_margen = w_margen_vs_aline/100.0
w_aline  = 1.0 - w_margen

alpha_impact = st.sidebar.slider("Score final: peso de Impacto vs (1-Esfuerzo)", 0, 100, 50)
alpha = alpha_impact / 100.0

st.sidebar.divider()
st.sidebar.subheader("Ajustes específicos")
override_ecommerce = st.sidebar.checkbox("Potenciar e‑commerce B2B (percepción de marca)", True)
ecom_alignment = st.sidebar.slider("Alineación e‑commerce (si está activo)", 0, 5, 4)

# -----------------------
# Carga de datos
# -----------------------
st.markdown("### 1) Cargar tabla de oportunidades")
up = st.file_uploader("Sube el Excel de oportunidades (usa tu documento con hoja 'Mapa de Oportunidades')", type=["xlsx"])

def load_df(file) -> pd.DataFrame:
    xls = pd.ExcelFile(file)
    if sheet_name not in xls.sheet_names:
        st.error(f"La hoja '{sheet_name}' no existe. Hojas encontradas: {xls.sheet_names}")
        st.stop()
    df = pd.read_excel(file, sheet_name=sheet_name, header=None)
    hdr_idx0 = max(0, header_row_1idx - 1)
    headers = df.iloc[hdr_idx0].tolist()
    data = df.iloc[hdr_idx0+1:].reset_index(drop=True)
    data.columns = headers
    # Limpiar y filtrar
    if "Oportunidad" not in data.columns:
        st.error("No encuentro la columna 'Oportunidad'. Revisa la fila de encabezados y el nombre de la hoja.")
        st.stop()
    data = data[data["Oportunidad"].notna()].copy()
    for col in data.columns:
        if data[col].dtype == object:
            data[col] = data[col].astype(str).str.strip()
    return data

# Si el usuario no sube archivo, intentar demo con el archivo del entorno (cuando exista)
default_path = "/mnt/data/Sesión Estrategia 1 Pectimex.xlsx"
if up is not None:
    df = load_df(up)
elif default_path:
    try:
        df = load_df(default_path)
        st.info("Usando el archivo de ejemplo del entorno.")
    except Exception as e:
        st.warning("Sube tu archivo para continuar.")
        st.stop()
else:
    st.stop()

st.dataframe(df, use_container_width=True, height=260)

# -----------------------
# Helpers de mapeo
# -----------------------
map_margen = {"Baja":1, "Media":2, "Medio":2, "Alta":3, "Bajo":1, "Alto":3}
map_inversion_bin = {"Sí":1, "Si":1, "No":0, "NO":0}
map_tiempo_norm = {"Corto":0.0, "Medio":0.5, "Media":0.5, "Largo":1.0}
map_facilidad_norm = {"Alta":0.0, "Media":0.5, "Baja":1.0}
map_riesgo_norm = {"Bajo":0.0, "Medio":0.5, "Media":0.5, "Alto":1.0, "Alta":1.0}

def is_ecommerce(name: str) -> bool:
    name = (name or "").lower()
    return ("ecommerce" in name) or ("mercadolibre" in name) or ("amazon" in name)

def classify_ansoff(op_name: str) -> str:
    name = str(op_name).lower()
    if "exportar producto empacado" in name or ("exportar" in name and "empacado" in name):
        return "Diversificación"
    if "exportar" in name:
        return "Desarrollo de mercado"
    if "desarrollo de nuevos productos" in name or ("nuevo" in name and "producto" in name):
        return "Desarrollo de producto"
    if "marca propia" in name and "retail" in name:
        return "Diversificación"
    if "personalización" in name:
        return "Desarrollo de producto"
    if "ecommerce" in name or "mercadolibre" in name or "amazon" in name:
        return "Penetración de mercado"
    if "horeca" in name and "directo" in name:
        return "Penetración de mercado"
    if "expos" in name or "antad" in name or "foodtech" in name:
        return "Penetración de mercado"
    if "nuevos distribuidores" in name:
        return "Penetración de mercado"
    return "Penetración de mercado"

def score_alineacion(op: str, desc: str, weights: dict, override_ecom: bool, ecom_align_value: int) -> float:
    name = (op or "").lower()
    # Base neutra
    sabor = salud = variedad = origen = 3

    if "desarrollo de nuevos productos" in name or ("nuevo" in name and "producto" in name):
        sabor, salud, variedad, origen = 5, 4, 5, 3
    elif "marca propia" in name and "retail" in name:
        sabor, salud, variedad, origen = 4, 5, 4, 4
    elif "personalización" in name:
        sabor, salud, variedad, origen = 4, 3, 5, 3
    elif "horeca" in name and "directo" in name:
        sabor, salud, variedad, origen = 4, 3, 3, 4
    elif "nuevos distribuidores" in name:
        sabor, salud, variedad, origen = 3, 3, 3, 3
    elif "expos" in name or "antad" in name or "foodtech" in name:
        sabor, salud, variedad, origen = 2, 2, 2, 2
    elif "exportar producto empacado" in name or ("exportar" in name and "empacado" in name):
        sabor, salud, variedad, origen = 4, 5, 4, 5
    elif "exportar" in name:
        sabor, salud, variedad, origen = 4, 4, 3, 5

    if override_ecom and is_ecommerce(name):
        sabor = salud = variedad = origen = ecom_align_value

    score = (weights["sabor"]*sabor + weights["salud"]*salud +
             weights["variedad"]*variedad + weights["origen"]*origen)
    return round(float(score), 2)

# -----------------------
# Cálculos
# -----------------------
df_work = df.copy()
df_work["Clasificación Ansoff"] = df_work["Oportunidad"].apply(classify_ansoff)

# Alineación (0–5)
df_work["Alineación_propósito"] = [
    score_alineacion(op, df_work.get("Descripción", [""]*len(df_work))[i], weights, override_ecommerce, ecom_alignment)
    for i, op in enumerate(df_work["Oportunidad"])
]

# Impacto_norm (0–1) = w_margen * margen_norm + w_aline * alineacion_norm
margen_raw = df_work["Margen potencial"].map(map_margen).fillna(2)
margen_norm = (margen_raw - 1) / 2.0
aline_norm = df_work["Alineación_propósito"] / 5.0
df_work["Impacto_norm"] = w_margen * margen_norm + w_aline * aline_norm

# Esfuerzo_norm (0–1) = promedio de inversión, tiempo, facilidad, riesgo
inv_norm = df_work["Requiere inversión inicial alta"].map(map_inversion_bin).fillna(0.5)
time_norm = df_work["Tiempo a implementación"].map(map_tiempo_norm).fillna(0.5)
fac_norm  = df_work["Facilidad de ejecución"].map(map_facilidad_norm).fillna(0.5)
risk_norm = df_work["Riesgo asociado"].map(map_riesgo_norm).fillna(0.5)
df_work["Esfuerzo_norm"] = (inv_norm + time_norm + fac_norm + risk_norm) / 4.0

# Score final (0–100) = 100 * (alpha*Impacto + (1-alpha)*(1-Esfuerzo))
df_work["Score (0-100)"] = (100.0 * (alpha * df_work["Impacto_norm"] + (1-alpha) * (1 - df_work["Esfuerzo_norm"]))).round(1)

# -----------------------
# 2) Matriz de Ansoff
# -----------------------
st.markdown("### 2) Matriz de Ansoff")
def ansoff_coords(cat: str):
    # (x=Mercado, y=Producto): 0=existente, 1=nuevo
    if cat == "Penetración de mercado":
        return (0,0)
    if cat == "Desarrollo de mercado":
        return (1,0)
    if cat == "Desarrollo de producto":
        return (0,1)
    if cat == "Diversificación":
        return (1,1)
    return (0,0)

coords = df_work["Clasificación Ansoff"].apply(ansoff_coords)
df_work["x_ansoff"] = [c[0] for c in coords]
df_work["y_ansoff"] = [c[1] for c in coords]

fig_ansoff = px.scatter(
    df_work,
    x="x_ansoff", y="y_ansoff",
    size="Score (0-100)",
    color="Clasificación Ansoff",
    hover_name="Oportunidad",
    hover_data={
        "Score (0-100)": True,
        "Alineación_propósito": True,
        "Impacto_norm": True,
        "Esfuerzo_norm": True
    },
)
fig_ansoff.update_traces(marker=dict(line=dict(width=1, color="white")))
fig_ansoff.update_layout(
    xaxis=dict(title="Mercado (0=existente, 1=nuevo)", tickmode="array", tickvals=[0,1]),
    yaxis=dict(title="Producto (0=existente, 1=nuevo)", tickmode="array", tickvals=[0,1]),
    title="Matriz de Ansoff (tamaño = Score)"
)
st.plotly_chart(fig_ansoff, use_container_width=True)

# -----------------------
# 3) Matriz Impacto × Esfuerzo con color por Alineación
# -----------------------
st.markdown("### 3) Matriz de toma de decisiones · Impacto × Esfuerzo × Alineación")
fig_ie = px.scatter(
    df_work,
    x="Esfuerzo_norm", y="Impacto_norm",
    size="Score (0-100)",
    color="Alineación_propósito",
    hover_name="Oportunidad",
    hover_data={
        "Clasificación Ansoff": True,
        "Requiere inversión inicial alta": True,
        "Tiempo a implementación": True,
        "Facilidad de ejecución": True,
        "Riesgo asociado": True,
        "Score (0-100)": True
    }
)
fig_ie.update_layout(
    xaxis_title="Esfuerzo (0–1, ↓ mejor)",
    yaxis_title="Impacto (0–1, ↑ mejor)",
    title="Impacto × Esfuerzo con mapa de color por Alineación al propósito"
)
st.plotly_chart(fig_ie, use_container_width=True)

# -----------------------
# 4) Tabla priorizada y descarga
# -----------------------
st.markdown("### 4) Tabla priorizada por Score (0–100)")
cols_show = ["Oportunidad","Clasificación Ansoff","Score (0-100)","Impacto_norm","Esfuerzo_norm","Alineación_propósito",
             "Margen potencial","Requiere inversión inicial alta","Tiempo a implementación","Facilidad de ejecución","Riesgo asociado"]
tabla = df_work[cols_show].sort_values("Score (0-100)", ascending=False).reset_index(drop=True)
st.dataframe(tabla, use_container_width=True, height=350)

# Botones de descarga
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    import xlsxwriter  # streamlit cloud usually has it; if not, user must install
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Prioridad")
        df_work.to_excel(writer, index=False, sheet_name="Cálculo_full")
    return buffer.getvalue()

st.download_button("Descargar Excel (prioridad + cálculo)", data=to_excel_bytes(tabla), file_name="Pectimex_oportunidades_score.xlsx")
st.download_button("Descargar CSV (prioridad)", data=tabla.to_csv(index=False).encode("utf-8"), file_name="Pectimex_oportunidades_score.csv")

st.success("Listo. Ajusta los parámetros en la barra lateral para recalcular todo al vuelo.")
