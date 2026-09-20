import streamlit as st
import pandas as pd
import re
from collections import Counter

st.set_page_config(page_title="Mega Polla IA", page_icon="🎰", layout="centered")

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

def fmt_num(n):
    if n == 100: return "00"
    if n == 0: return "0"
    return f"{n:02d}"

def extraer_hora(hora_str):
    m = re.match(r'^(\d+):(\d+)\s*(AM|PM)$', hora_str.strip().upper())
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

def analizar(df):
    if df.empty or len(df) < 10: return []
    total = len(df)
    nums = df["numero"].tolist()
    freq = Counter(nums)
    atrasos = {}
    for num in ANIMALITOS_DICT.keys():
        pos = [i for i, n in enumerate(nums) if n == num]
        atrasos[num] = total - 1 - pos[-1] if pos else total
    jales_in = Counter()
    ultimos_10 = set(nums[-10:])
    for i in range(1, len(nums)):
        if nums[i-1] in ultimos_10:
            jales_in[nums[i]] += 1
    mx_f = max(freq.values()) if freq else 1
    mx_a = max(atrasos.values()) if atrasos else 1
    mx_j = max(jales_in.values()) if jales_in else 1
    scores = {}
    for num in ANIMALITOS_DICT.keys():
        f = freq.get(num, 0)
        a = atrasos.get(num, 0)
        j = jales_in.get(num, 0)
        s = (f/mx_f)*0.4 + (a/mx_a)*0.3 + (j/mx_j)*0.3
        if a > 60: s *= 0.5
        scores[num] = round(s*100, 2)
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
    return [{"num": n, "score": s, "freq": freq.get(n, 0), "atr": atrasos.get(n, 0), "jal": jales_in.get(n, 0)} for n, s in top]

def mostrar_top(top, cantidad=10):
    for i, x in enumerate(top[:cantidad], 1):
        st.write(f"{i}. **{fmt_num(x['num'])} {ANIMALITOS_DICT[x['num']]}** ({x['score']}%)")

def mostrar_ultimo(df, nombre):
    if df.empty:
        st.write(f"**{nombre}:** Sin datos")
        return
    ultimo = df.iloc[-1]
    fecha_txt = ultimo["fecha_dt"].strftime("%d/%m/%Y")
    hora_txt = hora_legible(int(ultimo["hora_num"]))
    st.write(f"**{nombre}:** {fecha_txt} - {hora_txt} → {fmt_num(ultimo['numero'])} {ANIMALITOS_DICT[ultimo['numero']]}")

def armar_3_pollas(lista_g, lista_l, lista_r=None, tipo="2+2+2"):
    """Arma 3 pollas: Fuerte, Variación, Mezcla."""
    resultado = {"polla_1": [], "polla_2": [], "polla_3": []}

    if tipo == "2+2+2" and lista_r is not None:
        # Polla 1: #1 y #2 de cada
        if len(lista_g) >= 2 and len(lista_l) >= 2 and len(lista_r) >= 2:
            resultado["polla_1"] = lista_g[:2] + lista_l[:2] + lista_r[:2]
        # Polla 2: #3 y #4 de cada
        if len(lista_g) >= 4 and len(lista_l) >= 4 and len(lista_r) >= 4:
            resultado["polla_2"] = lista_g[2:4] + lista_l[2:4] + lista_r[2:4]
        # Polla 3: #1, #3 de cada
        if len(lista_g) >= 3 and len(lista_l) >= 3 and len(lista_r) >= 3:
            resultado["polla_3"] = [lista_g[0], lista_g[2], lista_l[0], lista_l[2], lista_r[0], lista_r[2]]
    elif tipo == "3+3":
        # Polla 1: #1, #2, #3
        if len(lista_g) >= 3 and len(lista_l) >= 3:
            resultado["polla_1"] = lista_g[:3] + lista_l[:3]
        # Polla 2: #4, #5, #6
        if len(lista_g) >= 6 and len(lista_l) >= 6:
            resultado["polla_2"] = lista_g[3:6] + lista_l[3:6]
        # Polla 3: #1, #4, #7 de cada
        if len(lista_g) >= 7 and len(lista_l) >= 7:
            resultado["polla_3"] = [lista_g[0], lista_g[3], lista_g[6], lista_l[0], lista_l[3], lista_l[6]]

    return resultado

def mostrar_pollas(pollas):
    def fmt_polla(lista):
        return " - ".join([f"{fmt_num(x['num'])} {ANIMALITOS_DICT[x['num']]}" for x in lista])

    if len(pollas["polla_1"]) == 6:
        st.markdown("**🎯 POLLA 1 (FUERTE - los más potentes)**")
        st.success(fmt_polla(pollas["polla_1"]))
    if len(pollas["polla_2"]) == 6:
        st.markdown("**⚡ POLLA 2 (VARIACIÓN - los segundos)**")
        st.info(fmt_polla(pollas["polla_2"]))
    if len(pollas["polla_3"]) == 6:
        st.markdown("**🔀 POLLA 3 (MEZCLA - #1 y #3)**")
        st.warning(fmt_polla(pollas["polla_3"]))

def main():
    st.title("🎰 Mega Polla IA")
    st.caption("Super Polla · Animaniacs · 3 Pollas (Fuerte, Variación, Mezcla)")

    if st.button("🔄 Recargar"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Cargando loterías..."):
        df_g = cargar_hoja(GRANJITA_ID)
        df_l = cargar_hoja(LOTTO_ID)
        df_r = cargar_hoja(RULETA_ID)

    st.markdown("### 📅 Últimos datos cargados")
    mostrar_ultimo(df_g, "GRANJITA")
    mostrar_ultimo(df_l, "LOTTO")
    mostrar_ultimo(df_r, "RULETA")
    st.markdown("---")

    # ============ SUPER POLLA MAÑANA ============
    st.markdown("## 🌅 SUPER POLLA MAÑANA (9AM-1PM)")
    g_m = analizar(filtrar_turno(df_g, "mañana"))
    l_m = analizar(filtrar_turno(df_l, "mañana"))
    r_m = analizar(filtrar_turno(df_r, "mañana"))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**GRANJITA**")
        mostrar_top(g_m)
    with c2:
        st.markdown("**LOTTO**")
        mostrar_top(l_m)
    with c3:
        st.markdown("**RULETA**")
        mostrar_top(r_m)
    pollas_m = armar_3_pollas(g_m, l_m, r_m, tipo="2+2+2")
    st.markdown("### 🎯 Pollas Mañana")
    mostrar_pollas(pollas_m)
    st.markdown("---")

    # ============ SUPER POLLA TARDE ============
    st.markdown("## 🌇 SUPER POLLA TARDE (3PM-7PM)")
    g_t = analizar(filtrar_turno(df_g, "tarde"))
    l_t = analizar(filtrar_turno(df_l, "tarde"))
    r_t = analizar(filtrar_turno(df_r, "tarde"))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**GRANJITA**")
        mostrar_top(g_t)
    with c2:
        st.markdown("**LOTTO**")
        mostrar_top(l_t)
    with c3:
        st.markdown("**RULETA**")
        mostrar_top(r_t)
    pollas_t = armar_3_pollas(g_t, l_t, r_t, tipo="2+2+2")
    st.markdown("### 🎯 Pollas Tarde")
    mostrar_pollas(pollas_t)
    st.markdown("---")

    # ============ ANIMANIACS ============
    st.markdown("## 🐾 ANIMANIACS (8AM-7PM)")
    g_f = analizar(filtrar_turno(df_g, "todo"))
    l_f = analizar(filtrar_turno(df_l, "todo"))
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**GRANJITA**")
        mostrar_top(g_f)
    with c2:
        st.markdown("**LOTTO**")
        mostrar_top(l_f)
    pollas_a = armar_3_pollas(g_f, l_f, tipo="3+3")
    st.markdown("### 🎯 Pollas Animaniacs")
    mostrar_pollas(pollas_a)

if __name__ == "__main__":
    main()
