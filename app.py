import streamlit as st
import pandas as pd
import re
from collections import Counter

st.set_page_config(page_title="Mega Polla IA V2", page_icon="🎰", layout="centered")

GRANJITA_ID = "1JpJgdyqu3HP4TlNyDocQ7WQjnsDfkUMP4Aj3q97TmHY"
LOTTO_ID = "1Wm31ULE_YckLHEaek8Kre42UMdglkli-QeLpHxzFf-I"
RULETA_ID = "1MG9Ycjikd2LunDtjFy7LHjM7arC5_P0Xymn8H7ABhVo"

SORTEOS_POR_DIA = 12
DESCARTE_ATRASO = 60

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

ECOSISTEMAS = {
    "PLUMAS": [6, 7, 9, 11, 14, 18, 28, 36],
    "DEPREDADORES": [5, 10, 15, 16, 24, 30],
    "CUADRÚPEDOS": [1, 2, 12, 13, 20, 21, 22, 23, 25, 26, 29, 32, 34, 35],
    "RASTREROS": [3, 4, 31],
    "ACUÁTICOS": [0, 17, 19, 27, 33],
}


def ecosistema_de(num):
    for eco, lista in ECOSISTEMAS.items():
        if num in lista:
            return eco
    return "?"


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


def calcular_ritmo(df):
    nums = df["numero"].tolist()
    ritmos = {}
    for num in ANIMALITOS_DICT.keys():
        pos = [i for i, n in enumerate(nums) if n == num]
        if len(pos) >= 2:
            diffs = [pos[k+1] - pos[k] for k in range(len(pos)-1)]
            ritmos[num] = {"promedio": round(sum(diffs)/len(diffs), 1), "pos": pos}
        else:
            ritmos[num] = {"promedio": 999, "pos": pos}
    return ritmos


def calcular_congelados(df, ritmos):
    total = len(df)
    congelados = set()
    for num in ANIMALITOS_DICT.keys():
        r = ritmos.get(num, {}).get("promedio", 999)
        if r <= 0 or r >= 500: continue
        pos = ritmos[num]["pos"]
        if not pos: continue
        atraso = total - 1 - pos[-1]
        if atraso >= r * 2:
            congelados.add(num)
    return congelados


def calcular_penal_ayer(df):
    if df.empty: return set()
    fechas = sorted(df["fecha_dt"].unique())
    if len(fechas) < 2: return set()
    fecha_ayer = fechas[-2]
    df_ayer = df[df["fecha_dt"] == fecha_ayer]
    c = Counter(df_ayer["numero"].tolist())
    return set([n for n, cnt in c.items() if cnt >= 3])


def calcular_ecosistema_top(df):
    if df.empty or len(df) < 20: return None
    df_rec = df.tail(60)
    conteo = Counter([ecosistema_de(n) for n in df_rec["numero"].tolist()])
    if not conteo: return None
    return conteo.most_common(1)[0][0]


def calcular_prob_dia_semana(df, fecha_actual):
    if df.empty or fecha_actual is None: return {}
    ds = fecha_actual.weekday()
    df_dia = df[df["fecha_dt"].apply(lambda x: x.weekday() == ds)]
    if df_dia.empty: return {}
    total = len(df_dia)
    conteo = Counter(df_dia["numero"].tolist())
    return {num: round(c / total * 100, 2) for num, c in conteo.items()}


def aprender_jales(df, max_atraso=3):
    jales = {n: Counter() for n in ANIMALITOS_DICT.keys()}
    nums = df["numero"].tolist()
    for i in range(len(nums)-1):
        for j in range(i+1, min(i+1+max_atraso, len(nums))):
            jales[nums[i]][nums[j]] += 1
    return jales


def calcular_carga_banca(df, scores, detalles, salieron_hoy):
    if df.empty: return []
    fecha_hoy_str = df["fecha"].iloc[-1]
    total_hoy = len(df[df["fecha"] == fecha_hoy_str])
    if total_hoy < 3: return []
    top = [(n, s) for n, s in sorted(scores.items(), key=lambda x: x[1], reverse=True) if n not in salieron_hoy][:10]
    cargados = []
    for num, sc in top[:3]:
        if detalles[num]["freq_20"] >= 2 or detalles[num]["jales_in"] >= 2:
            cargados.append({"num": num, "score_original": sc})
    return cargados


def analizar(df, turno, df_completo):
    if df.empty or len(df) < 5: return []

    fecha_actual = df["fecha_dt"].iloc[-1]
    fecha_hoy_str = df["fecha"].iloc[-1]

    nums = df["numero"].tolist()
    total = len(nums)
    freq = Counter(nums)
    freq_20 = Counter(nums[-20:]) if total >= 20 else Counter(nums)
    freq_30 = Counter(nums[-30:]) if total >= 30 else Counter(nums)

    atrasos = {}
    for num in ANIMALITOS_DICT.keys():
        pos = [i for i, n in enumerate(nums) if n == num]
        atrasos[num] = total - 1 - pos[-1] if pos else total

    jales_aprendidos = aprender_jales(df)
    jales_in = Counter()
    for nr in nums[-10:]:
        for sig, c in jales_aprendidos.get(nr, Counter()).most_common(3):
            jales_in[sig] += c

    ritmos = calcular_ritmo(df)
    congelados = calcular_congelados(df, ritmos)
    penal_ayer = calcular_penal_ayer(df_completo)

    salieron_hoy = set(df_completo[df_completo["fecha"] == fecha_hoy_str]["numero"].tolist()) if not df_completo.empty else set()
    atraso_hoy_dict = {}
    df_hoy = df_completo[df_completo["fecha"] == fecha_hoy_str] if not df_completo.empty else pd.DataFrame()
    total_hoy = len(df_hoy)
    for num in ANIMALITOS_DICT.keys():
        pos_hoy = df_hoy[df_hoy["numero"] == num].index.tolist() if not df_hoy.empty else []
        if pos_hoy:
            atraso_hoy_dict[num] = total_hoy - 1 - df_hoy.index.get_loc(pos_hoy[-1])
        else:
            atraso_hoy_dict[num] = 999

    eco_top = calcular_ecosistema_top(df)
    prob_dia = calcular_prob_dia_semana(df, fecha_actual)

    max_f = max(freq.values()) if freq else 1
    max_f20 = max(freq_20.values()) if freq_20 else 1
    max_atr = max(atrasos.values()) if atrasos else 1
    max_jal = max(jales_in.values()) if jales_in else 1

    scores = {}
    detalles = {}
    for num in ANIMALITOS_DICT.keys():
        f = freq.get(num, 0)
        f20 = freq_20.get(num, 0)
        f30 = freq_30.get(num, 0)
        atr = atrasos.get(num, 0)
        atr_hoy = atraso_hoy_dict.get(num, 999)
        jal = jales_in.get(num, 0)

        n_f = f / max_f if max_f else 0
        n_f20 = f20 / max_f20 if max_f20 else 0
        n_atr = atr / max_atr if max_atr else 0
        n_jal = jal / max_jal if max_jal else 0

        bonus_caliente = 0.08 if f30 >= 3 else (0.04 if f30 == 2 else 0)

        penal_frio = 0
        if atr > 60: penal_frio = -0.35
        elif atr > 45: penal_frio = -0.20
        elif atr > 30: penal_frio = -0.10

        penal_reciente = 0
        if atr_hoy == 0: penal_reciente = -0.60
        elif atr_hoy == 1: penal_reciente = -0.45
        elif atr_hoy == 2: penal_reciente = -0.30
        elif atr_hoy == 3: penal_reciente = -0.20
        elif atr_hoy == 4: penal_reciente = -0.10

        score = n_f*0.20 + n_f20*0.20 + n_atr*0.20 + n_jal*0.25 + bonus_caliente + penal_frio + penal_reciente

        if eco_top and ecosistema_de(num) == eco_top:
            score += 0.10

        if prob_dia.get(num, 0) >= 3:
            score += 0.05

        if f == 0: score *= 0.4
        if atr >= DESCARTE_ATRASO: score = 0
        if num in congelados: score *= 0.10
        if num in penal_ayer: score *= 0.80

        scores[num] = round(max(score, 0) * 100, 2)
        detalles[num] = {
            "freq": f, "freq_20": f20, "atraso": atr, "jales_in": jal,
            "caliente": bonus_caliente > 0,
            "congelado": num in congelados,
            "penal_ayer": num in penal_ayer,
            "eco_top": eco_top and ecosistema_de(num) == eco_top,
            "prob_dia": prob_dia.get(num, 0)
        }

    carga_banca = calcular_carga_banca(df, scores, detalles, salieron_hoy)
    for c in carga_banca:
        scores[c["num"]] = round(scores[c["num"]] * 0.5, 2)
        detalles[c["num"]]["cargado_banca"] = True

    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    resultado = []
    for num, sc in top[:10]:
        resultado.append({
            "num": num,
            "score": sc,
            "detalle": detalles[num]
        })
    return resultado


def armar_pollas(graf, llot, rrul):
    pollas = {"polla_1": [], "polla_2": [], "polla_3": []}

    if len(graf) >= 4 and len(llot) >= 4 and len(rrul) >= 4:
        polla_1 = []
        for i in range(2):
            polla_1.append({"loteria": "GRANJITA", "item": graf[i]})
            polla_1.append({"loteria": "LOTTO", "item": llot[i]})
            polla_1.append({"loteria": "RULETA", "item": rrul[i]})
        pollas["polla_1"] = polla_1

        polla_2 = []
        for i in range(2, 4):
            polla_2.append({"loteria": "GRANJITA", "item": graf[i]})
            polla_2.append({"loteria": "LOTTO", "item": llot[i]})
            polla_2.append({"loteria": "RULETA", "item": rrul[i]})
        pollas["polla_2"] = polla_2

        polla_3 = [
            {"loteria": "GRANJITA", "item": graf[0]},
            {"loteria": "GRANJITA", "item": graf[2]},
            {"loteria": "LOTTO", "item": llot[0]},
            {"loteria": "LOTTO", "item": llot[2]},
            {"loteria": "RULETA", "item": rrul[0]},
            {"loteria": "RULETA", "item": rrul[2]},
        ]
        pollas["polla_3"] = polla_3

    return pollas


def armar_pollas_animaniacs(graf, llot):
    """2 pollas para Animaniacs: Especial y Todo el Día."""
    pollas = {"polla_1": [], "polla_2": []}

    if len(graf) < 3 or len(llot) < 3:
        return pollas

    # POLLA 1 (ESPECIAL): 3 mejores Granjita + 3 mejores Lotto
    p1 = []
    for i in range(3):
        p1.append({"loteria": "GRANJITA", "item": graf[i]})
    for i in range(3):
        p1.append({"loteria": "LOTTO", "item": llot[i]})

    vistos = set()
    final_p1 = []
    for x in p1:
        n = x["item"]["num"]
        if n not in vistos:
            final_p1.append(x)
            vistos.add(n)

    # Completar si hay duplicados
    if len(final_p1) < 6:
        for i in range(3, 10):
            if len(graf) > i:
                n = graf[i]["num"]
                if n not in vistos:
                    final_p1.append({"loteria": "GRANJITA", "item": graf[i]})
                    vistos.add(n)
            if len(final_p1) >= 6: break
        for i in range(3, 10):
            if len(llot) > i:
                n = llot[i]["num"]
                if n not in vistos:
                    final_p1.append({"loteria": "LOTTO", "item": llot[i]})
                    vistos.add(n)
            if len(final_p1) >= 6: break

    pollas["polla_1"] = final_p1[:6]

    # POLLA 2: los siguientes (diferentes a los de la Polla 1)
    p2 = []
    vistos_p2 = set(vistos)
    for i in range(3, 10):
        if len(graf) > i:
            n = graf[i]["num"]
            if n not in vistos_p2:
                p2.append({"loteria": "GRANJITA", "item": graf[i]})
                vistos_p2.add(n)
        if len(p2) >= 3: break
    for i in range(3, 10):
        if len(llot) > i:
            n = llot[i]["num"]
            if n not in vistos_p2:
                p2.append({"loteria": "LOTTO", "item": llot[i]})
                vistos_p2.add(n)
        if len(p2) >= 6: break

    pollas["polla_2"] = p2[:6]

    return pollas


def mostrar_polla(pollas, titulo):
    st.markdown(f"### 🎯 Pollas {titulo}")

    for idx, key in enumerate(["polla_1", "polla_2", "polla_3"], 1):
        p = pollas[key]
        if not p: continue

        nombres_unicos = []
        vistos = set()
        for x in p:
            n = x["item"]["num"]
            if n not in vistos:
                nombres_unicos.append(x)
                vistos.add(n)

        if len(nombres_unicos) < 6: continue

        emoji = "🎯" if idx == 1 else ("⚡" if idx == 2 else "🔀")
        label = "FUERTE" if idx == 1 else ("VARIACIÓN" if idx == 2 else "MEZCLA")

        st.markdown(f"**{emoji} Polla {idx} ({label}):**")
        linea = " - ".join([f"{fmt_num(x['item']['num'])} {ANIMALITOS_DICT[x['item']['num']]}" for x in nombres_unicos[:6]])
        if idx == 1: st.success(linea)
        elif idx == 2: st.info(linea)
        else: st.warning(linea)
        st.markdown("")


def mostrar_pollas_animaniacs(pollas):
    """Muestra las 2 pollas de Animaniacs."""
    if len(pollas["polla_1"]) < 6:
        st.warning("Sin candidatos suficientes.")
        return

    # POLLA 1 (ESPECIAL)
    st.markdown("### 🎯 POLLA 1 — ESPECIAL (8 AM a 12 PM)")
    st.caption("Si los 6 salen antes de las 12 PM → Premio acumulado · Si no, sigue hasta las 7 PM")
    linea_1 = " - ".join([f"{fmt_num(x['item']['num'])} {ANIMALITOS_DICT[x['item']['num']]}" for x in pollas["polla_1"]])
    st.success(linea_1)
    st.markdown("**Detalle:**")
    for x in pollas["polla_1"]:
        d = x["item"]["detalle"]
        marcas = []
        if d["caliente"]: marcas.append("🔥")
        if d["eco_top"]: marcas.append("🌍")
        if d["penal_ayer"]: marcas.append("⚠️")
        if d.get("cargado_banca"): marcas.append("🚫")
        st.write(f"- [{x['loteria']}] **{fmt_num(x['item']['num'])} {ANIMALITOS_DICT[x['item']['num']]}** — {x['item']['score']}% {' '.join(marcas)}")

    st.markdown("")

    # POLLA 2 (DÍA COMPLETO)
    if len(pollas["polla_2"]) >= 6:
        st.markdown("### ⚡ POLLA 2 — DÍA COMPLETO (8 AM a 7 PM)")
        st.caption("Animalitos distintos a la Polla 1")
        linea_2 = " - ".join([f"{fmt_num(x['item']['num'])} {ANIMALITOS_DICT[x['item']['num']]}" for x in pollas["polla_2"]])
        st.info(linea_2)
        st.markdown("**Detalle:**")
        for x in pollas["polla_2"]:
            d = x["item"]["detalle"]
            marcas = []
            if d["caliente"]: marcas.append("🔥")
            if d["eco_top"]: marcas.append("🌍")
            if d["penal_ayer"]: marcas.append("⚠️")
            if d.get("cargado_banca"): marcas.append("🚫")
            st.write(f"- [{x['loteria']}] **{fmt_num(x['item']['num'])} {ANIMALITOS_DICT[x['item']['num']]}** — {x['item']['score']}% {' '.join(marcas)}")


def mostrar_ultimo(df, nombre):
    if df.empty:
        st.write(f"**{nombre}:** Sin datos")
        return
    u = df.iloc[-1]
    st.write(f"**{nombre}:** {u['fecha']} - {hora_legible(int(u['hora_num']))} → {fmt_num(u['numero'])} {ANIMALITOS_DICT[u['numero']]}")


def mostrar_top(lista, loteria):
    st.markdown(f"**{loteria}**")
    for i, item in enumerate(lista[:10], 1):
        d = item["detalle"]
        marcas = []
        if d["caliente"]: marcas.append("🔥")
        if d["eco_top"]: marcas.append("🌍")
        if d["penal_ayer"]: marcas.append("⚠️")
        if d.get("cargado_banca"): marcas.append("🚫")
        st.write(f"{i}. **{fmt_num(item['num'])} {ANIMALITOS_DICT[item['num']]}** — {item['score']}% {' '.join(marcas)}")


def main():
    st.title("🎰 Mega Polla IA V2")
    st.caption("3 Pollas Polla · 2 Pollas Animaniacs · Filtros · Ecosistemas")

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

    # SUPER POLLA MAÑANA
    st.markdown("## 🌅 SUPER POLLA MAÑANA (9AM-1PM)")

    g_m = analizar(filtrar_turno(df_g, "mañana"), "mañana", df_g)
    l_m = analizar(filtrar_turno(df_l, "mañana"), "mañana", df_l)
    r_m = analizar(filtrar_turno(df_r, "mañana"), "mañana", df_r)

    c1, c2, c3 = st.columns(3)
    with c1: mostrar_top(g_m, "GRANJITA")
    with c2: mostrar_top(l_m, "LOTTO")
    with c3: mostrar_top(r_m, "RULETA")

    st.markdown("")
    pollas_m = armar_pollas(g_m, l_m, r_m)
    mostrar_polla(pollas_m, "Mañana")
    st.markdown("---")

    # SUPER POLLA TARDE
    st.markdown("## 🌇 SUPER POLLA TARDE (3PM-7PM)")

    g_t = analizar(filtrar_turno(df_g, "tarde"), "tarde", df_g)
    l_t = analizar(filtrar_turno(df_l, "tarde"), "tarde", df_l)
    r_t = analizar(filtrar_turno(df_r, "tarde"), "tarde", df_r)

    c1, c2, c3 = st.columns(3)
    with c1: mostrar_top(g_t, "GRANJITA")
    with c2: mostrar_top(l_t, "LOTTO")
    with c3: mostrar_top(r_t, "RULETA")

    st.markdown("")
    pollas_t = armar_pollas(g_t, l_t, r_t)
    mostrar_polla(pollas_t, "Tarde")
    st.markdown("---")

    # ANIMANIACS (2 POLLAS)
    st.markdown("## 🐾 ANIMANIACS (8AM-7PM)")

    g_a = analizar(filtrar_turno(df_g, "todo"), "todo", df_g)
    l_a = analizar(filtrar_turno(df_l, "todo"), "todo", df_l)

    c1, c2 = st.columns(2)
    with c1: mostrar_top(g_a, "GRANJITA")
    with c2: mostrar_top(l_a, "LOTTO")

    st.markdown("")
    pollas_anim = armar_pollas_animaniacs(g_a, l_a)
    mostrar_pollas_animaniacs(pollas_anim)

    st.markdown("---")
    st.caption("🌍 = Ecosistema top · 🔥 = Caliente · ⚠️ = 3+ veces ayer · 🚫 = Cargado por banca")


if __name__ == "__main__":
    main()
