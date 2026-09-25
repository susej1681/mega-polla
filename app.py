import streamlit as st
import pandas as pd
import re
from collections import Counter

st.set_page_config(page_title="Mega Polla Fríos", page_icon="🎰", layout="centered")

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


def fmt_num(n):
    if n == 100: return "00"
    if n == 0: return "0"
    return f"{n:02d}"


def extraer_hora(hora_str):
    m = re.match(r'^(\d+):(\d+)\s*(AM|PM)$', str(hora_str).strip().upper())
    if not m: return 0
    h = int(m.group(1))
    suf = m.group(3)
    if suf == "AM":
        if h == 12: h = 0
    else:
        if h != 12: h += 12
    return h


def hora_legible(hora_num):
    if hora_num == 0: return "12:00 AM"
    if hora_num < 12: return f"{hora_num}:00 AM"
    if hora_num == 12: return "12:00 PM"
    return f"{hora_num-12}:00 PM"


@st.cache_data(ttl=120)
def cargar_hoja(sheet_id):
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
                        registros.append({
                            "fecha_dt": fd,
                            "fecha": fd.strftime("%d/%m/%Y"),
                            "hora_num": extraer_hora(hv),
                            "numero": n
                        })
        df = pd.DataFrame(registros)
        if not df.empty:
            df = df.sort_values(["fecha_dt", "hora_num"], kind="stable").reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error: {e}")
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


def get_frios_combinados(df_turno_combinado, df_g_completo):
    if df_turno_combinado.empty:
        return [], {}

    fechas = sorted(df_turno_combinado["fecha_dt"].dropna().unique())
    if len(fechas) < VENTANA_FRIOS:
        ventana = fechas
    else:
        ventana = fechas[-VENTANA_FRIOS:]

    df_vent = df_turno_combinado[df_turno_combinado["fecha_dt"].isin(ventana)]
    conteo = Counter(df_vent["numero"].tolist())

    dias_sin = dias_sin_salir(df_g_completo)

    candidatos = [n for n in ANIMALITOS_DICT.keys() if dias_sin[n] < EXCLUIR_DESDE]
    candidatos.sort(key=lambda n: (conteo.get(n, 0), n))

    return candidatos, conteo


def armar_2_pollas(frios):
    if len(frios) < 12:
        return [], []
    return frios[0:6], frios[6:12]


def mostrar_pollas(frios, p1, p2, titulo, loterias, conteo):
    st.markdown(f"### 🎯 {titulo}")
    st.caption(f"Juega en: {' + '.join(loterias)} · Pool combinado")

    if not frios:
        st.warning("Sin fríos disponibles.")
        return

    st.markdown("**❄️ TOP 10 FRÍOS DEL POOL (últimos 5 días):**")
    for i, n in enumerate(frios[:10], 1):
        veces = conteo.get(n, 0)
        st.write(f"{i}. **{fmt_num(n)} {ANIMALITOS_DICT[n]}** — {veces} veces en últimos 5 días")

    st.markdown("---")

    if p1 and p2:
        st.markdown("**🎯 POLLA 1 (FRÍOS TOP 6):**")
        linea_1 = " - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in p1])
        st.success(linea_1)

        st.markdown("**⚡ POLLA 2 (FRÍOS 7-12):**")
        linea_2 = " - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in p2])
        st.info(linea_2)

    st.markdown("")


def mostrar_ultimo(df, nombre):
    if df.empty:
        st.write(f"**{nombre}:** Sin datos")
        return
    u = df.iloc[-1]
    st.write(f"**{nombre}:** {u['fecha']} - {hora_legible(int(u['hora_num']))} → {fmt_num(u['numero'])} {ANIMALITOS_DICT[u['numero']]}")


def verificar_polla(polla, nums_bloque):
    return all(n in nums_bloque for n in polla)


def backtest(df_g, df_l, df_r, dias_test=55):
    fechas_g = set(df_g["fecha_dt"].dropna().unique())
    fechas_l = set(df_l["fecha_dt"].dropna().unique())
    fechas_r = set(df_r["fecha_dt"].dropna().unique())
    fechas_comunes = sorted(fechas_g & fechas_l & fechas_r)

    if len(fechas_comunes) < dias_test + 6:
        dias_test = len(fechas_comunes) - 6

    if dias_test < 1:
        return {}, 0

    fechas_test = fechas_comunes[-dias_test:]

    resultados = {
        "mañana": {"polla_1": 0, "polla_2": 0},
        "tarde": {"polla_1": 0, "polla_2": 0},
        "animaniacs": {"polla_1": 0, "polla_2": 0}
    }
    total_dias = 0

    for fecha in fechas_test:
        df_g_hasta = df_g[df_g["fecha_dt"] < fecha]
        df_l_hasta = df_l[df_l["fecha_dt"] < fecha]
        df_r_hasta = df_r[df_r["fecha_dt"] < fecha]

        if len(df_g_hasta) < 60:
            continue

        total_dias += 1

        for turno in ["mañana", "tarde", "animaniacs"]:
            g_turno = filtrar_turno(df_g_hasta, turno)
            l_turno = filtrar_turno(df_l_hasta, turno)
            r_turno = filtrar_turno(df_r_hasta, turno) if turno != "animaniacs" else pd.DataFrame()

            if turno == "animaniacs":
                df_comb = pd.concat([g_turno, l_turno], ignore_index=True)
            else:
                df_comb = pd.concat([g_turno, l_turno, r_turno], ignore_index=True)

            frios, _ = get_frios_combinados(df_comb, df_g_hasta)
            p1, p2 = armar_2_pollas(frios)

            if not p1:
                continue

            df_g_dia = df_g[df_g["fecha_dt"] == fecha]
            df_l_dia = df_l[df_l["fecha_dt"] == fecha]
            df_r_dia = df_r[df_r["fecha_dt"] == fecha] if turno != "animaniacs" else pd.DataFrame()

            g_bloque = filtrar_turno(df_g_dia, turno)
            l_bloque = filtrar_turno(df_l_dia, turno)
            r_bloque = filtrar_turno(df_r_dia, turno) if not df_r_dia.empty else pd.DataFrame()

            nums_bloque = set()
            nums_bloque.update(g_bloque["numero"].tolist())
            nums_bloque.update(l_bloque["numero"].tolist())
            if not r_bloque.empty:
                nums_bloque.update(r_bloque["numero"].tolist())

            if verificar_polla(p1, nums_bloque):
                resultados[turno]["polla_1"] += 1
            if verificar_polla(p2, nums_bloque):
                resultados[turno]["polla_2"] += 1

    return resultados, total_dias


def main():
    st.title("🎰 Mega Polla Fríos")
    st.caption("6 Pollas al día · Pool combinado · Con backtest")

    if st.button("🔄 Recargar"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Cargando las 3 loterías..."):
        df_g = cargar_hoja(GRANJITA_ID)
        df_l = cargar_hoja(LOTTO_ID)
        df_r = cargar_hoja(RULETA_ID)

    if df_g.empty or df_l.empty or df_r.empty:
        st.error("No se pudieron cargar las loterías.")
        return

    st.markdown("### 📅 Últimos datos")
    mostrar_ultimo(df_g, "GRANJITA")
    mostrar_ultimo(df_l, "LOTTO")
    mostrar_ultimo(df_r, "RULETA")
    st.markdown("---")

    # MAÑANA
    st.markdown("## 🌅 SUPER POLLA MAÑANA (9AM-1PM)")
    g_m = filtrar_turno(df_g, "mañana")
    l_m = filtrar_turno(df_l, "mañana")
    r_m = filtrar_turno(df_r, "mañana")
    df_m_comb = pd.concat([g_m, l_m, r_m], ignore_index=True)
    frios_m, conteo_m = get_frios_combinados(df_m_comb, df_g)
    p1_m, p2_m = armar_2_pollas(frios_m)
    mostrar_pollas(frios_m, p1_m, p2_m, "SUPER POLLA MAÑANA", ["Granjita", "Lotto", "Ruleta"], conteo_m)
    st.markdown("---")

    # TARDE
    st.markdown("## 🌇 SUPER POLLA TARDE (3PM-7PM)")
    g_t = filtrar_turno(df_g, "tarde")
    l_t = filtrar_turno(df_l, "tarde")
    r_t = filtrar_turno(df_r, "tarde")
    df_t_comb = pd.concat([g_t, l_t, r_t], ignore_index=True)
    frios_t, conteo_t = get_frios_combinados(df_t_comb, df_g)
    p1_t, p2_t = armar_2_pollas(frios_t)
    mostrar_pollas(frios_t, p1_t, p2_t, "SUPER POLLA TARDE", ["Granjita", "Lotto", "Ruleta"], conteo_t)
    st.markdown("---")

    # ANIMANIACS
    st.markdown("## 🐾 ANIMANIACS (8AM-7PM)")
    g_a = filtrar_turno(df_g, "todo")
    l_a = filtrar_turno(df_l, "todo")
    df_a_comb = pd.concat([g_a, l_a], ignore_index=True)
    frios_a, conteo_a = get_frios_combinados(df_a_comb, df_g)
    p1_a, p2_a = armar_2_pollas(frios_a)
    mostrar_pollas(frios_a, p1_a, p2_a, "ANIMANIACS", ["Granjita", "Lotto"], conteo_a)
    st.markdown("---")

    # BACKTEST
    st.markdown("## 📊 BACKTEST — ÚLTIMOS 55 DÍAS")
    st.caption("Verificamos si los 6 animalitos de cada polla salieron en el bloque")

    with st.spinner("Analizando histórico..."):
        resultados, total_dias = backtest(df_g, df_l, df_r, dias_test=55)

    if total_dias > 0:
        st.markdown(f"**Días analizados:** {total_dias}")
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🌅 MAÑANA")
            st.metric("Polla 1 pegó", resultados["mañana"]["polla_1"])
            st.metric("Polla 2 pegó", resultados["mañana"]["polla_2"])
        with col2:
            st.markdown("### 🌇 TARDE")
            st.metric("Polla 1 pegó", resultados["tarde"]["polla_1"])
            st.metric("Polla 2 pegó", resultados["tarde"]["polla_2"])

        st.markdown("### 🐾 ANIMANIACS")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Polla 1 pegó", resultados["animaniacs"]["polla_1"])
        with col2:
            st.metric("Polla 2 pegó", resultados["animaniacs"]["polla_2"])

        total_pegadas = (resultados["mañana"]["polla_1"] + resultados["mañana"]["polla_2"] +
                         resultados["tarde"]["polla_1"] + resultados["tarde"]["polla_2"] +
                         resultados["animaniacs"]["polla_1"] + resultados["animaniacs"]["polla_2"])

        st.markdown("---")
        st.metric("🎯 TOTAL POLLAS PEGADAS", total_pegadas)

        if total_pegadas > 0:
            st.success(f"✅ El sistema habría pegado {total_pegadas} pollas en {total_dias} días")
        else:
            st.warning(f"⚠️ En {total_dias} días, el sistema NO habría pegado ninguna polla")

    st.markdown("---")
    st.caption(f"Filtros: fríos puros (últimos {VENTANA_FRIOS} días) · Excluye enjaulados {EXCLUIR_DESDE}+ días")


if __name__ == "__main__":
    main()
