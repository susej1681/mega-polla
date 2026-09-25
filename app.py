import streamlit as st
import pandas as pd
import re
from collections import Counter
from datetime import datetime, timedelta

st.set_page_config(page_title="Mega Polla Fríos V3", page_icon="🎰", layout="centered")

GRANJITA_ID = "1JpJgdyqu3HP4TlNyDocQ7WQjnsDfkUMP4Aj3q97TmHY"
LOTTO_ID = "1Wm31ULE_YckLHEaek8Kre42UMdglkli-QeLpHxzFf-I"
RULETA_ID = "1MG9Ycjikd2LunDtjFy7LHjM7arC5_P0Xymn8H7ABhVo"

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
    if turno == "animaniacs": return df[(df["hora_num"] >= 8) & (df["hora_num"] <= 19)]
    return df


def analizar_pool(df_combinado, dias_ventana):
    """Analiza el pool: cuenta veces por animalito en toda la ventana."""
    if df_combinado.empty:
        return [], {}

    fechas_str = [d.strftime("%d/%m/%Y") for d in dias_ventana]
    df_vent = df_combinado[df_combinado["fecha"].isin(fechas_str)]

    if df_vent.empty:
        return [], {}

    conteo = Counter(df_vent["numero"].tolist())
    ordenados = sorted(conteo.items(), key=lambda x: x[1], reverse=True)
    return ordenados, conteo


def armar_pollas(ordenados):
    """Arma 2 pollas de 6 animalitos distintos cada una. Puede repetir entre pollas."""
    if len(ordenados) < 6:
        return [], []

    # Pool de animalitos ordenados por actividad
    nums = [n for n, _ in ordenados]

    # Completar con los que no salieron (para tener al menos 12)
    if len(nums) < 12:
        todos = [n for n in ANIMALITOS_DICT.keys() if n not in nums]
        nums.extend(todos)

    # Polla 1: los 6 más activos
    polla_1 = []
    for n in nums:
        if n not in polla_1:
            polla_1.append(n)
        if len(polla_1) >= 6:
            break

    # Polla 2: los siguientes 6 (pero puede repetir hasta 2 de la polla 1 si son muy fuertes)
    polla_2 = []
    # Primero los siguientes
    for n in nums:
        if n not in polla_1:
            polla_2.append(n)
        if len(polla_2) >= 4:
            break
    # Completar con 2 de los top de polla_1 (los más fuertes)
    for n in polla_1[:3]:
        if len(polla_2) >= 6:
            break
        if n not in polla_2:
            polla_2.append(n)

    # Si aún falta, completar
    if len(polla_2) < 6:
        for n in nums:
            if n not in polla_2:
                polla_2.append(n)
            if len(polla_2) >= 6:
                break

    return polla_1[:6], polla_2[:6]


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


def mostrar_pollas(nombre, ordenados, conteo, loterias):
    """Muestra las 2 pollas para un bloque."""
    st.markdown(f"### {nombre}")
    st.caption(f"Juega en: {' + '.join(loterias)}")

    p1, p2 = armar_pollas(ordenados)

    if p1 and p2:
        st.markdown("**🎯 POLLA 1:**")
        st.success(" - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in p1]))
        st.markdown("**⚡ POLLA 2:**")
        st.info(" - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in p2]))
    else:
        st.warning("Sin suficientes datos.")


def main():
    st.title("🎰 Mega Polla Fríos V3")
    st.caption("Vista día por día · Sin excluir los de hoy · 6 pollas al día")

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

    # Agregar HOY a la ventana (para el análisis)
    dias_analisis = dias_ventana + [hoy]

    st.info(f"📊 **{desc}** + HOY")
    st.markdown("---")

    # Vista día por día
    st.markdown("## 📅 ANÁLISIS DÍA POR DÍA")
    st.caption("(G) Granjita · (L) Lotto · (R) Ruleta")

    for dia in dias_ventana:
        fecha_str = dia.strftime("%d/%m/%Y")
        nombre = DIAS[dia.weekday()]
        mostrar_dia_completo(df_g, df_l, df_r, fecha_str, nombre)

    mostrar_dia_completo(df_g, df_l, df_r, hoy_str, nombre_dia)

    st.markdown("---")

    # POLLAS
    st.markdown("## 🎯 POLLAS PARA HOY")

    # MAÑANA (9AM-1PM) - 3 loterías
    st.markdown("### 🌅 SUPER POLLA MAÑANA (9AM-1PM)")
    g_m = filtrar_turno(df_g, "mañana")
    l_m = filtrar_turno(df_l, "mañana")
    r_m = filtrar_turno(df_r, "mañana")
    df_m = pd.concat([g_m, l_m, r_m], ignore_index=True)
    ordenados_m, conteo_m = analizar_pool(df_m, dias_analisis)
    mostrar_pollas("", ordenados_m, conteo_m, ["Granjita", "Lotto", "Ruleta"])
    st.markdown("---")

    # TARDE (3PM-7PM) - 3 loterías
    st.markdown("### 🌇 SUPER POLLA TARDE (3PM-7PM)")
    g_t = filtrar_turno(df_g, "tarde")
    l_t = filtrar_turno(df_l, "tarde")
    r_t = filtrar_turno(df_r, "tarde")
    df_t = pd.concat([g_t, l_t, r_t], ignore_index=True)
    ordenados_t, conteo_t = analizar_pool(df_t, dias_analisis)
    mostrar_pollas("", ordenados_t, conteo_t, ["Granjita", "Lotto", "Ruleta"])
    st.markdown("---")

    # ANIMANIACS (8AM-7PM) - 2 loterías (Granjita + Lotto)
    st.markdown("### 🐾 ANIMANIACS (8AM-7PM)")
    g_a = filtrar_turno(df_g, "animaniacs")
    l_a = filtrar_turno(df_l, "animaniacs")
    df_a = pd.concat([g_a, l_a], ignore_index=True)
    ordenados_a, conteo_a = analizar_pool(df_a, dias_analisis)
    mostrar_pollas("", ordenados_a, conteo_a, ["Granjita", "Lotto"])

    st.markdown("---")
    st.caption("Sin excluir los que ya salieron hoy · Puede repetir animalitos entre pollas si el sistema lo ve fuerte")


if __name__ == "__main__":
    main()
