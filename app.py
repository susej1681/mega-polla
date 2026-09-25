import streamlit as st
import pandas as pd
import re
from collections import Counter
from datetime import datetime, timedelta

st.set_page_config(page_title="Mega Polla Fríos V2", page_icon="🎰", layout="centered")

GRANJITA_ID = "1JpJgdyqu3HP4TlNyDocQ7WQjnsDfkUMP4Aj3q97TmHY"
LOTTO_ID = "1Wm31ULE_YckLHEaek8Kre42UMdglkli-QeLpHxzFf-I"
RULETA_ID = "1MG9Ycjikd2LunDtjFy7LHjM7arC5_P0Xymn8H7ABhVo"

VENTANA_FRIOS = 5
EXCLUIR_DESDE = 10

ANIMALITOS_DICT = {
    0: "Delfín", 1: "Carnero", 2: "Toro", 3: "Ciempiés", 4: "Alacrán",
    5: "León", 6: "Rana", 7: "Perico", 8: "Ratón", 9: "Águila",
    10: "Tigre", 11: "Gato", 12: "Caballo", 13: "Mono", 14: "Paloma",
    15: "Zorro", 16: "Oso", 17: "Pavo", 18: "Burro", 19: "Chivo",
    20: "Cochino", 21: "Gallo", 22: "Camello", 23: "Cebra", 24: "Iguana",
    25: "Gallina", 26: "Vaca", 27: "Perro", 28: "Zamuro", 29: "Elefante",
    30: "Caimán", 31: "Lapa", 32: "Ardilla", 33: "Pescado", 34: "Venado",
    35: "Jirafa", 36: "Culebra", 100: "Ballena"
}

DIAS = {0: "LUNES", 1: "MARTES", 2: "MIÉRCOLES", 3: "JUEVES", 4: "VIERNES", 5: "SÁBADO", 6: "DOMINGO"}


def fmt_num(n):
    if n == 100: return "00"
    if n == 0: return "0"
    return f"{n:02d}"


def extraer_hora(hora_str):
    m = re.match(r'^(\d+):(\d+)\s*(AM|PM)$', str(hora_str).strip().upper())
    if not m: return 99
    h = int(m.group(1))
    suf = m.group(3)
    if suf == "AM":
        if h == 12: h = 0
    else:
        if h != 12: h += 12
    return h


def formatear_hora(hora_num):
    if hora_num == 0: return "12:00 AM"
    if hora_num < 12: return f"{hora_num:02d}:00 AM"
    if hora_num == 12: return "12:00 PM"
    return f"{hora_num-12:02d}:00 PM"


@st.cache_data(ttl=120)
def cargar_hoja(sheet_id, nombre_loteria):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        df_raw = pd.read_csv(url, header=None)
        filas_enc = []
        for f in range(len(df_raw)):
            v = str(df_raw.iloc[f, 0]).strip().lower()
            if v == "hora":
                filas_enc.append(f)
        registros = []
        for idx, fe in enumerate(filas_enc):
            ff = filas_enc[idx + 1] if idx + 1 < len(filas_enc) else len(df_raw)
            fechas_col = {}
            for col in range(1, len(df_raw.columns)):
                v = str(df_raw.iloc[fe, col]).strip()
                if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', v):
                    try:
                        fd = pd.to_datetime(v, format="%d/%m/%Y", errors="coerce")
                        if pd.notna(fd): fechas_col[col] = fd
                    except: pass
            ffd = min(ff, fe + 13)
            for col, fd in fechas_col.items():
                for fila in range(fe + 1, ffd):
                    hv = str(df_raw.iloc[fila, 0]).strip()
                    v = str(df_raw.iloc[fila, col]).strip()
                    if not v or v.lower() == "nan" or v.lower() == "hora":
                        continue
                    m = re.search(r'\((\d+)\)', v)
                    if m:
                        ns = m.group(1)
                        n = 100 if ns == "00" else int(ns)
                        hora_n = extraer_hora(hv)
                        if hora_n == 99:
                            continue
                        registros.append({
                            "fecha_dt": fd,
                            "fecha": fd.strftime("%d/%m/%Y"),
                            "hora_num": hora_n,
                            "hora_str": formatear_hora(hora_n),
                            "numero": n,
                            "loteria": nombre_loteria
                        })
        df = pd.DataFrame(registros)
        if not df.empty:
            df = df.sort_values(["fecha_dt", "hora_num"], kind="stable").reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error {nombre_loteria}: {e}")
        return pd.DataFrame()


def filtrar_turno(df, turno):
    if df.empty: return df
    if turno == "mañana": return df[(df["hora_num"] >= 9) & (df["hora_num"] <= 13)]
    if turno == "tarde": return df[(df["hora_num"] >= 15) & (df["hora_num"] <= 19)]
    if turno == "todo": return df[(df["hora_num"] >= 8) & (df["hora_num"] <= 19)]
    return df


def dias_sin_salir(df_completo):
    fechas = sorted(df_completo["fecha_dt"].dropna().unique())
    if not fechas: return {n: 999 for n in ANIMALITOS_DICT.keys()}
    ultima = fechas[-1]
    resultado = {}
    for num in ANIMALITOS_DICT.keys():
        df_num = df_completo[df_completo["numero"] == num]
        if df_num.empty:
            resultado[num] = 999
        else:
            ult = df_num["fecha_dt"].max()
            resultado[num] = (ultima - ult).days
    return resultado


def get_frios_pool(df_combinado, df_g_completo, fecha_hoy_str):
    if df_combinado.empty:
        return [], {}, set()

    df_hoy = df_combinado[df_combinado["fecha"] == fecha_hoy_str]
    salieron_hoy = set(df_hoy["numero"].tolist())

    fechas = sorted(df_combinado["fecha_dt"].dropna().unique())
    if len(fechas) < VENTANA_FRIOS:
        ventana = fechas
    else:
        ventana = fechas[-VENTANA_FRIOS:]

    df_vent = df_combinado[df_combinado["fecha_dt"].isin(ventana)]
    conteo = Counter(df_vent["numero"].tolist())

    dias_sin = dias_sin_salir(df_g_completo)

    candidatos = [n for n in ANIMALITOS_DICT.keys() 
                  if dias_sin[n] < EXCLUIR_DESDE and n not in salieron_hoy]
    candidatos.sort(key=lambda n: (conteo.get(n, 0), n))

    return candidatos, conteo, salieron_hoy


def armar_2_pollas(frios):
    if len(frios) < 12:
        return [], []
    return frios[0:6], frios[6:12]


def mostrar_dia_completo(df_g, df_l, df_r, fecha_str, nombre_dia):
    """Muestra un día combinado con las 3 loterías por hora."""
    g_dia = df_g[df_g["fecha"] == fecha_str]
    l_dia = df_l[df_l["fecha"] == fecha_str]
    r_dia = df_r[df_r["fecha"] == fecha_str]

    if g_dia.empty and l_dia.empty and r_dia.empty:
        return False

    st.markdown(f"### 📅 {nombre_dia} {fecha_str}")

    horas = set()
    for df_dia in [g_dia, l_dia, r_dia]:
        if not df_dia.empty:
            horas.update(df_dia["hora_num"].unique())

    for hora_num in sorted(horas):
        lineas = []
        for df_dia, letra in [(g_dia, "G"), (l_dia, "L"), (r_dia, "R")]:
            if not df_dia.empty:
                fila = df_dia[df_dia["hora_num"] == hora_num]
                if not fila.empty:
                    num = int(fila.iloc[0]["numero"])
                    lineas.append(f"{fmt_num(num)} {ANIMALITOS_DICT[num]} ({letra})")
        if lineas:
            st.write(f"**{formatear_hora(hora_num)}** → {' · '.join(lineas)}")

    st.markdown("")
    return True


def main():
    st.title("🎰 Mega Polla Fríos V2")
    st.caption("Vista día por día · Pool combinado · 6 pollas al día")

    if st.button("🔄 Recargar"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Cargando las 3 loterías..."):
        df_g = cargar_hoja(GRANJITA_ID, "G")
        df_l = cargar_hoja(LOTTO_ID, "L")
        df_r = cargar_hoja(RULETA_ID, "R")

    if df_g.empty or df_l.empty or df_r.empty:
        st.error("No se pudieron cargar las loterías.")
        return

    hoy = datetime.now().date()
    hoy_str = hoy.strftime("%d/%m/%Y")
    nombre_dia = DIAS[hoy.weekday()]

    st.markdown(f"## 📅 Hoy es **{nombre_dia}**")
    st.caption(f"Fecha: {hoy_str}")

    # Días de la ventana
    dia_semana = hoy.weekday()
    if dia_semana == 0:
        dias_ventana = [hoy - timedelta(days=2), hoy - timedelta(days=1)]
        desc = "Referencia: Sábado + Domingo anterior"
    elif dia_semana == 1:
        dias_ventana = [hoy - timedelta(days=2), hoy - timedelta(days=1)]
        desc = "Referencia: Domingo + Lunes"
    else:
        inicio = hoy - timedelta(days=dia_semana)
        dias_ventana = []
        d = inicio
        while d < hoy:
            dias_ventana.append(d)
            d += timedelta(days=1)
        desc = f"Semana en curso: {len(dias_ventana)} días"

    st.info(f"📊 **{desc}**")
    st.markdown("---")

    # Vista día por día
    st.markdown("## 📅 ANÁLISIS DÍA POR DÍA")
    st.caption("(G) Granjita · (L) Lotto · (R) Ruleta")

    for dia in dias_ventana:
        fecha_str = dia.strftime("%d/%m/%Y")
        nombre = DIAS[dia.weekday()]
        mostrar_dia_completo(df_g, df_l, df_r, fecha_str, nombre)

    # HOY (siempre)
    mostrar_dia_completo(df_g, df_l, df_r, hoy_str, nombre_dia)

    st.markdown("---")

    # POLLAS
    st.markdown("## 🎯 POLLAS PARA HOY")

    # MAÑANA
    st.markdown("### 🌅 SUPER POLLA MAÑANA (9AM-1PM)")
    g_m = filtrar_turno(df_g, "mañana")
    l_m = filtrar_turno(df_l, "mañana")
    r_m = filtrar_turno(df_r, "mañana")
    df_m = pd.concat([g_m, l_m, r_m], ignore_index=True)
    frios_m, _, _ = get_frios_pool(df_m, df_g, hoy_str)
    p1_m, p2_m = armar_2_pollas(frios_m)

    if p1_m and p2_m:
        st.markdown("**🎯 POLLA 1:**")
        st.success(" - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in p1_m]))
        st.markdown("**⚡ POLLA 2:**")
        st.info(" - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in p2_m]))
    else:
        st.warning("Sin suficientes fríos.")
    st.markdown("---")

    # TARDE
    st.markdown("### 🌇 SUPER POLLA TARDE (3PM-7PM)")
    g_t = filtrar_turno(df_g, "tarde")
    l_t = filtrar_turno(df_l, "tarde")
    r_t = filtrar_turno(df_r, "tarde")
    df_t = pd.concat([g_t, l_t, r_t], ignore_index=True)
    frios_t, _, _ = get_frios_pool(df_t, df_g, hoy_str)
    p1_t, p2_t = armar_2_pollas(frios_t)

    if p1_t and p2_t:
        st.markdown("**🎯 POLLA 1:**")
        st.success(" - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in p1_t]))
        st.markdown("**⚡ POLLA 2:**")
        st.info(" - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in p2_t]))
    else:
        st.warning("Sin suficientes fríos.")
    st.markdown("---")

    # ANIMANIACS
    st.markdown("### 🐾 ANIMANIACS (8AM-7PM)")
    g_a = filtrar_turno(df_g, "todo")
    l_a = filtrar_turno(df_l, "todo")
    df_a = pd.concat([g_a, l_a], ignore_index=True)
    frios_a, _, _ = get_frios_pool(df_a, df_g, hoy_str)
    p1_a, p2_a = armar_2_pollas(frios_a)

    if p1_a and p2_a:
        st.markdown("**🎯 POLLA 1:**")
        st.success(" - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in p1_a]))
        st.markdown("**⚡ POLLA 2:**")
        st.info(" - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in p2_a]))
    else:
        st.warning("Sin suficientes fríos.")

    st.markdown("---")
    st.caption(f"Filtros: fríos puros · Excluye enjaulados {EXCLUIR_DESDE}+ días · Excluye los que ya salieron hoy")


if __name__ == "__main__":
    main()
