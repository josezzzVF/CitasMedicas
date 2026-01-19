import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, date, time
import time as time_mod
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

st.set_page_config(
    page_title="Sistema de Citas Médicas",
    page_icon="🏥",
    layout="wide"
)

N8N_WEBHOOK_URL = "https://quincee.app.n8n.cloud/webhook/citas_medicas"

def construir_pdf_citas_bytes_pdfreport(citas) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Reporte de Citas Médicas</b>", styles["Title"]))
    story.append(Paragraph(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    df = pd.DataFrame(citas) if citas else pd.DataFrame(columns=[
        "paciente_nombre", "fecha_cita", "hora_cita", "medico", "especialidad", "estado"
    ])

    total = len(df)
    completadas = int((df["estado"].fillna("").str.lower() == "completado").sum()) if "estado" in df else 0
    por_estado = df["estado"].value_counts().to_dict() if "estado" in df else {}

    story.append(Paragraph("<b>Estadísticas</b>", styles["Heading3"]))
    story.append(Paragraph(f"Total de Citas: {total}", styles["Normal"]))
    story.append(Paragraph(f"Citas Completadas: {completadas}", styles["Normal"]))
    if por_estado:
        story.append(Paragraph("Distribución por estado:", styles["Normal"]))
        for k, v in por_estado.items():
            story.append(Paragraph(f"- {k}: {v}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Citas Agendadas</b>", styles["Heading3"]))

    headers = ["Paciente", "Fecha", "Hora", "Médico", "Especialidad", "Estado"]
    table_data = [headers]

    for c in citas:
        table_data.append([
            str(c.get("paciente_nombre") or c.get("paciente") or ""),
            str(c.get("fecha_cita") or ""),
            str(c.get("hora_cita") or ""),
            str(c.get("medico") or c.get("medico_nombre") or ""),
            str(c.get("especialidad") or c.get("medico_especialidad") or ""),
            str(c.get("estado") or "")
        ])

    tbl = Table(table_data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("FONTSIZE", (0,1), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.transparent]),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(tbl)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def n8n_api(action: str, payload: dict, timeout: int = 20):
    try:
        resp = requests.post(N8N_WEBHOOK_URL, json={"accion": action, **payload}, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}

@st.cache_data(ttl=30)
def n8n_cached(action: str, payload: dict):
    """Caché corta para listados/lecturas frecuentes."""
    return n8n_api(action, payload)

ESTADOS_VALIDOS = ["Agendado", "Confirmado", "Cancelado", "Completado"]

def to_date(s):
    try:
        return pd.to_datetime(s).date()
    except Exception:
        return None

def to_time(s):
    try:
        return pd.to_datetime(s).time()
    except Exception:
        return None

def pagina_gestion_pacientes():
    st.header("👥 Gestión de Pacientes")
    tabs = st.tabs(["➕ Crear", "📋 Listar", "✏️ Editar", "🗑️ Eliminar"])

    with tabs[0]:
        st.subheader("Crear Paciente")
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre*", key="pac_crear_nombre")
            email = st.text_input("Email*", key="pac_crear_email")
            telefono = st.text_input("Teléfono", key="pac_crear_tel")
            edad = st.number_input("Edad", min_value=0, max_value=120, step=1, key="pac_crear_edad")
        with col2:
            genero = st.selectbox("Género", ["", "Masculino", "Femenino"], key="pac_crear_genero")
            direccion = st.text_area("Dirección", key="pac_crear_dir")
            activo = st.checkbox("Activo", value=True, key="pac_crear_activo")

        if st.button("Crear Paciente", type="primary"):
            if not nombre or not email:
                st.error("Nombre y Email son obligatorios.")
            else:
                res = n8n_api("crear_paciente", {
                    "nombre": nombre,
                    "email": email,
                    "telefono": telefono,
                    "edad": int(edad) if edad else None,
                    "genero": genero or None,
                    "direccion": direccion or None,
                    "activo": bool(activo)
                })
                if res.get("success"):
                    st.success("✅ Paciente creado")
                    st.cache_data.clear()
                else:
                    st.error("❌ No se pudo crear el paciente")
            st.rerun()

    with tabs[1]:
        st.subheader("Lista de Pacientes")
        colf1, colf2 = st.columns([2,1])
        with colf1:
            busq = st.text_input("Buscar por nombre", key="pac_list_busq")
        with colf2:
            do_search = st.button("🔍 Buscar", use_container_width=True)

        if do_search or busq == "":
            pacientes = n8n_cached("listar_pacientes", {"busqueda": busq})
        else:
            pacientes = []

        if not pacientes:
            st.info("No se encontraron pacientes.")
        else:
            df = pd.DataFrame(pacientes)
            cols = ["id", "nombre", "email", "telefono", "edad", "genero", "direccion", "fecha_registro", "activo"]
            cols = [c for c in cols if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)

    with tabs[2]:
        st.subheader("Editar Paciente")
        pacientes = n8n_cached("listar_pacientes", {"busqueda": ""}) or []
        if not pacientes:
            st.info("No hay pacientes.")
        else:
            opciones = {f"{p['nombre']} ({p['email']})": p for p in pacientes}
            key_sel = st.selectbox("Seleccionar paciente", list(opciones.keys()))
            sel = opciones[key_sel]

            col1, col2 = st.columns(2)
            with col1:
                nuevo_nombre = st.text_input("Nombre", value=sel.get("nombre",""))
                nuevo_email = st.text_input("Email", value=sel.get("email",""))
                nuevo_tel = st.text_input("Teléfono", value=sel.get("telefono","") or "")
                nueva_edad = st.number_input("Edad", value=int(sel.get("edad") or 0), min_value=0, max_value=120)
            with col2:
                nuevo_genero = st.selectbox("Género",
                                            ["", "Masculino", "Femenino"],
                                            index=["","Masculino","Femenino"].index(sel.get("genero","") or ""))
                nueva_dir = st.text_area("Dirección", value=sel.get("direccion","") or "")
                nuevo_activo = st.checkbox("Activo", value=bool(sel.get("activo", True)))

            if st.button("Guardar cambios", type="primary"):
                res = n8n_api("editar_paciente", {
                    "paciente_id": sel["id"],
                    "nombre": nuevo_nombre,
                    "email": nuevo_email,
                    "telefono": nuevo_tel,
                    "edad": int(nueva_edad) if nueva_edad else None,
                    "genero": nuevo_genero or None,
                    "direccion": nueva_dir or None,
                    "activo": bool(nuevo_activo)
                })
                if res.get("success"):
                    st.success("✅ Paciente actualizado")
                    st.cache_data.clear()
                else:
                    st.error("❌ No se pudo actualizar el paciente")

    with tabs[3]:
        st.subheader("Eliminar Paciente")
        pacientes = n8n_cached("listar_pacientes", {"busqueda": ""}) or []
        if not pacientes:
            st.info("No hay pacientes.")
        else:
            opciones = {f"{p['nombre']} ({p['email']})": p for p in pacientes}
            key_sel = st.selectbox("Seleccionar paciente a eliminar", list(opciones.keys()), key="pac_del_sel")
            sel = opciones[key_sel]
            st.warning("Esta acción no se puede deshacer.")
            if st.button("Eliminar Paciente", type="secondary"):
                res = n8n_api("eliminar_paciente", {"paciente_id": sel["id"]})
                if res.get("success"):
                    st.success("🗑️ Paciente eliminado")
                    st.cache_data.clear()
                else:
                    st.error("❌ No se pudo eliminar el paciente")

def pagina_gestion_medicos():
    st.header("👨‍⚕️ Gestión de Médicos")
    tabs = st.tabs(["➕ Crear", "📋 Listar", "✏️ Editar", "🗑️ Eliminar"])

    with tabs[0]:
        st.subheader("Crear Médico")
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre*", key="med_crear_nombre")
            especialidad = st.text_input("Especialidad*", key="med_crear_espec")
            email = st.text_input("Email", key="med_crear_email")
        with col2:
            telefono = st.text_input("Teléfono", key="med_crear_tel")
            activo = st.checkbox("Activo", value=True, key="med_crear_activo")

        if st.button("Crear Médico", type="primary"):
            if not nombre or not especialidad:
                st.error("Nombre y Especialidad son obligatorios.")
            else:
                res = n8n_api("crear_medico", {
                    "nombre": nombre, "especialidad": especialidad,
                    "email": email or None, "telefono": telefono or None,
                    "activo": bool(activo)
                })
                if res.get("success"):
                    st.success("✅ Médico creado")
                    st.cache_data.clear()
                else:
                    st.error("❌ No se pudo crear el médico")

    with tabs[1]:
        st.subheader("Lista de Médicos")
        col1, col2 = st.columns([3,1])
        with col1:
            busq = st.text_input("Buscar por nombre/especialidad", key="med_list_busq")
        with col2:
            do_search = st.button("🔍 Buscar", use_container_width=True)

        if do_search or busq == "":
            medicos = n8n_cached("listar_medicos", {"busqueda": busq})
        else:
            medicos = []

        if not medicos:
            st.info("No se encontraron médicos.")
        else:
            df = pd.DataFrame(medicos)
            cols = ["id","nombre","especialidad","email","telefono","activo"]
            cols = [c for c in cols if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)

    with tabs[2]:
        st.subheader("Editar Médico")
        medicos = n8n_cached("listar_medicos", {"busqueda": ""}) or []
        if not medicos:
            st.info("No hay médicos.")
        else:
            opciones = {f"{m['nombre']} ({m.get('especialidad','')})": m for m in medicos}
            key_sel = st.selectbox("Seleccionar médico", list(opciones.keys()), key="med_edit_sel")
            sel = opciones[key_sel]

            col1, col2 = st.columns(2)
            with col1:
                nuevo_nombre = st.text_input("Nombre", value=sel.get("nombre",""))
                nueva_especialidad = st.text_input("Especialidad", value=sel.get("especialidad",""))
                nuevo_email = st.text_input("Email", value=sel.get("email","") or "")
            with col2:
                nuevo_tel = st.text_input("Teléfono", value=sel.get("telefono","") or "")
                nuevo_activo = st.checkbox("Activo", value=bool(sel.get("activo", True)))

            if st.button("Guardar cambios", type="primary"):
                res = n8n_api("editar_medico", {
                    "medico_id": sel["id"],
                    "nombre": nuevo_nombre,
                    "especialidad": nueva_especialidad,
                    "email": nuevo_email or None,
                    "telefono": nuevo_tel or None,
                    "activo": bool(nuevo_activo)
                })
                if res.get("success"):
                    st.success("✅ Médico actualizado")
                    st.cache_data.clear()
                else:
                    st.error("❌ No se pudo actualizar el médico")

    with tabs[3]:
        st.subheader("Eliminar Médico")
        medicos = n8n_cached("listar_medicos", {"busqueda": ""}) or []
        if not medicos:
            st.info("No hay médicos.")
        else:
            opciones = {f"{m['nombre']} ({m.get('especialidad','')})": m for m in medicos}
            key_sel = st.selectbox("Seleccionar médico a eliminar", list(opciones.keys()), key="med_del_sel")
            sel = opciones[key_sel]
            st.warning("Esta acción no se puede deshacer.")
            if st.button("Eliminar Médico", type="secondary"):
                res = n8n_api("eliminar_medico", {"medico_id": sel["id"]})
                if res.get("success"):
                    st.success("🗑️ Médico eliminado")
                    st.cache_data.clear()
                else:
                    st.error("❌ No se pudo eliminar el médico")


def pagina_gestion_citas():
    st.header("📅 Gestión de Citas")
    tabs = st.tabs(["➕ Crear", "📋 Listar", "✏️ Editar", "🗑️ Eliminar"])

    medicos = n8n_cached("listar_medicos", {"busqueda": ""}) or []
    pacientes = n8n_cached("listar_pacientes", {"busqueda": ""}) or []
    map_medico = {f"{m['nombre']} ({m.get('especialidad','')})": m for m in medicos}
    map_paciente = {f"{p['nombre']} ({p['email']})": p for p in pacientes}

    def _reset_verificacion():
        st.session_state.pop("cita_verificada", None)
        st.session_state.pop("cita_firma", None)

    with tabs[0]:
        st.subheader("Crear Cita")

        st.session_state.setdefault("cita_verificada", False)
        st.session_state.setdefault("cita_firma", None)
        st.session_state.setdefault("cita_timer_start", None)

        if st.session_state.get("cita_timer_start") is None:
            st.session_state["cita_timer_start"] = time_mod.time()

        col1, col2 = st.columns(2)
        with col1:
            sel_med = st.selectbox(
                "Médico*", list(map_medico.keys()) or ["-- No hay médicos --"],
                key="cita_crear_med", on_change=_reset_verificacion
            )
            sel_pac = st.selectbox(
                "Paciente*", list(map_paciente.keys()) or ["-- No hay pacientes --"],
                key="cita_crear_pac"
            )
            fecha_cita = st.date_input(
                "Fecha*", min_value=date.today(),
                key="cita_crear_fecha", on_change=_reset_verificacion
            )
        with col2:
            hora_cita = st.time_input(
                "Hora*", value=time(9,0),
                key="cita_crear_hora", on_change=_reset_verificacion
            )
            estado = st.selectbox("Estado", ESTADOS_VALIDOS, index=0, key="cita_crear_estado")

        es_domingo = fecha_cita.weekday() == 6 if fecha_cita else False
        if es_domingo:
            st.error("🚫 No se pueden agendar citas los domingos.")

        med_id = map_medico[sel_med]["id"] if "-- No hay" not in sel_med else None
        firma_actual = (
            med_id,
            fecha_cita.strftime("%Y-%m-%d") if fecha_cita else None,
            hora_cita.strftime("%H:%M")
        )

        colb1, colb2 = st.columns(2)
        with colb1:
            verificar = st.button("🔍 Verificar Disponibilidad", use_container_width=True)
        with colb2:
            crear = st.button(
                "🩺 Crear Cita",
                type="primary",
                use_container_width=True,
                disabled=(
                    es_domingo or
                    med_id is None or
                    "-- No hay" in sel_pac or
                    not st.session_state.get("cita_verificada", False) or
                    st.session_state.get("cita_firma") != firma_actual
                )
            )

        if verificar:
            if med_id is None or "-- No hay" in sel_pac:
                st.error("Debes registrar al menos un médico y un paciente.")
            elif es_domingo:
                st.error("🚫 No se pueden agendar citas los domingos.")
            else:
                disp = n8n_api("verificar_disponibilidad", {
                    "fecha_cita": fecha_cita.strftime("%Y-%m-%d"),
                    "hora_cita": hora_cita.strftime("%H:%M:%S"),
                    "medico_id": med_id
                })
                if disp.get("disponible") == "true":
                    st.success("✅ Horario disponible. Ahora puedes crear la cita.")
                    st.session_state["cita_verificada"] = True
                    st.session_state["cita_firma"] = firma_actual
                else:
                    st.session_state["cita_verificada"] = False
                    st.session_state["cita_firma"] = None
                    st.session_state.pop("cita_timer_start", None)
                    st.error("❌ No disponible. Elige otra hora.")
                
                st.rerun()

        if crear:
            if es_domingo:
                st.error("🚫 No se pueden agendar citas los domingos.")
            elif not st.session_state.get("cita_verificada", False) or st.session_state.get("cita_firma") != firma_actual:
                st.warning("Primero verifica la disponibilidad del horario seleccionado.")
            elif med_id is None or "-- No hay" in sel_pac:
                st.error("Debes registrar al menos un médico y un paciente.")
            else:
                pac_id = map_paciente[sel_pac]["id"]
                timer_start = st.session_state.get("cita_timer_start")
                tiempo_segundos = None
                if timer_start:
                    tiempo_segundos = round(time_mod.time() - timer_start, 2)

                payload_crear = {
                    "medico_id": med_id,
                    "paciente_id": pac_id,
                    "fecha_cita": fecha_cita.strftime("%Y-%m-%d"),
                    "hora_cita": hora_cita.strftime("%H:%M:%S"),
                    "estado": estado,
                    "tiempo_segundos_creacion": tiempo_segundos
                }

                res = n8n_api("crear_cita", payload_crear)
                if res.get("success"):
                    st.success("✅ Cita creada")
                    st.cache_data.clear()
                    if tiempo_segundos is not None:
                        st.info(f"⏱️ Tiempo desde la verificación hasta la creación: {tiempo_segundos} segundos")
                    else:
                        st.info("⏱️ Tiempo de creación: no disponible")
                    _reset_verificacion()
                else:
                    st.error("❌ No se pudo crear la cita")

        if st.session_state.get("cita_firma") and st.session_state.get("cita_firma") != firma_actual:
            st.info("ℹ️ Cambiaste médico/fecha/hora. Vuelve a verificar disponibilidad.")

        with tabs[1]:
            st.subheader("Lista de Citas")
            colf1, colf2, colf3, colf4 = st.columns(4)
            with colf1:
                filtro_estado = st.selectbox("Estado", ["Todos"] + ESTADOS_VALIDOS, index=0, key="citas_list_filtro_estado")
            with colf2:
                filtro_medico = st.text_input("Doctor contiene...")
            with colf3:
                filtro_paciente = st.text_input("Paciente contiene...")
            with colf4:
                filtro_fecha = st.date_input("Fecha (opcional)", value=None)

            citas = n8n_cached("listar_citas", {}) or []
            df = pd.DataFrame(citas)
            if not df.empty:
                if "medico_nombre" not in df.columns and "medico" in df.columns:
                    df["medico_nombre"] = df["medico"]
                if "paciente_nombre" not in df.columns and "paciente" in df.columns:
                    df["paciente_nombre"] = df["paciente"]
                if "especialidad" not in df.columns and "medico_especialidad" in df.columns:
                    df["especialidad"] = df["medico_especialidad"]

                if filtro_estado != "Todos" and "estado" in df:
                    df = df[df["estado"] == filtro_estado]
                if filtro_medico and "medico_nombre" in df:
                    df = df[df["medico_nombre"].fillna("").str.contains(filtro_medico, case=False)]
                if filtro_paciente and "paciente_nombre" in df:
                    df = df[df["paciente_nombre"].fillna("").str.contains(filtro_paciente, case=False)]
                if filtro_fecha is not None and "fecha_cita" in df:
                    df = df[pd.to_datetime(df["fecha_cita"]).dt.date == filtro_fecha]

                cols = ["id","fecha_cita","hora_cita","estado","medico_nombre","especialidad","paciente_nombre"]
                cols = [c for c in cols if c in df.columns]
                st.dataframe(df[cols].sort_values(by=["fecha_cita","hora_cita"], ascending=True),
                            use_container_width=True, hide_index=True)
            else:
                st.info("No hay citas.")

    with tabs[2]:
        st.subheader("Editar Cita")
        citas = n8n_cached("listar_citas", {}) or []
        if not citas:
            st.info("No hay citas para editar.")
        else:
            labels = []
            for c in citas:
                med = c.get("medico_nombre") or c.get("medico") or ""
                pac = c.get("paciente_nombre") or c.get("paciente") or ""
                labels.append(f"[{c['id']}] {c.get('fecha_cita','')} {c.get('hora_cita','')} - {med} / {pac} ({c.get('estado','')})")
            idx = st.selectbox("Selecciona la cita", list(range(len(citas))), format_func=lambda i: labels[i])
            cita = citas[idx]

            fecha_new = st.date_input("Nueva fecha", value=to_date(cita.get("fecha_cita")))
            hora_new = st.time_input("Nueva hora", value=to_time(cita.get("hora_cita")) or time(9,0))
            estado_new = st.selectbox("Estado", ESTADOS_VALIDOS,
                                      index=ESTADOS_VALIDOS.index(cita.get("estado","Agendado")) if cita.get("estado") in ESTADOS_VALIDOS else 0)

            colr1, colr2 = st.columns(2)
            with colr1:
                med_label = st.selectbox("Reasignar Médico (opcional)", ["(Mantener)"] + list(map_medico.keys()))
            with colr2:
                pac_label = st.selectbox("Reasignar Paciente (opcional)", ["(Mantener)"] + list(map_paciente.keys()))

            payload = {
                "cita_id": cita["id"],
                "fecha_cita": fecha_new.strftime("%Y-%m-%d"),
                "hora_cita": hora_new.strftime("%H:%M:%S"),
                "estado": estado_new
            }
            if med_label != "(Mantener)":
                payload["medico_id"] = map_medico[med_label]["id"]
            if pac_label != "(Mantener)":
                payload["paciente_id"] = map_paciente[pac_label]["id"]

            if st.button("Guardar cambios", type="primary"):
                res = n8n_api("editar_cita", payload)
                if res.get("success"):
                    st.success("✅ Cita actualizada")
                    st.cache_data.clear()
                else:
                    st.error("❌ No se pudo actualizar la cita")

    with tabs[3]:
        st.subheader("Eliminar Cita")
        citas = n8n_cached("listar_citas", {}) or []
        if not citas:
            st.info("No hay citas para eliminar.")
        else:
            labels = []
            for c in citas:
                med = c.get("medico_nombre") or c.get("medico") or ""
                pac = c.get("paciente_nombre") or c.get("paciente") or ""
                labels.append(f"[{c['id']}] {c.get('fecha_cita','')} {c.get('hora_cita','')} - {med} / {pac} ({c.get('estado','')})")
            idx = st.selectbox("Selecciona la cita a eliminar", list(range(len(citas))), format_func=lambda i: labels[i], key="cita_del_sel")
            cita = citas[idx]
            st.warning("Esta acción no se puede deshacer.")
            if st.button("Eliminar Cita", type="secondary"):
                res = n8n_api("eliminar_cita", {"cita_id": cita["id"]})
                if res.get("success"):
                    st.success("🗑️ Cita eliminada")
                    st.cache_data.clear()
                else:
                    st.error("❌ No se pudo eliminar la cita")

def mostrar_reportes():
    st.header("📊 Reportes y Análisis")
    
    with st.spinner("Cargando reportes..."):
        reportes = n8n_api("datos_reportes", {})

    if not reportes:
        st.info("No hay datos disponibles para generar reportes.")
        return
    
    df_medico = pd.DataFrame(
        list(reportes["citas_por_medico"].items()), columns=["Médico", "Citas"]
    )
    df_especialidad = pd.DataFrame(
        list(reportes["citas_por_especialidad"].items()), columns=["Especialidad", "Citas"]
    )
    df_dia = pd.DataFrame(
        list(reportes["citas_por_dia"].items()), columns=["Día", "Citas"]
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Citas por Médico")
        fig_medico = px.bar(df_medico, x='Médico', y='Citas', color='Citas')
        st.plotly_chart(fig_medico, use_container_width=True)
        
        st.subheader("Distribución por Especialidad")
        fig_especialidad = px.pie(df_especialidad, values='Citas', names='Especialidad')
        st.plotly_chart(fig_especialidad, use_container_width=True)
    
    with col2:
        st.subheader("Citas por Día de la Semana")
        fig_dia = px.line(df_dia, x='Día', y='Citas', markers=True)
        st.plotly_chart(fig_dia, use_container_width=True)
        
        st.subheader("Métricas Principales")
        total_citas = df_medico['Citas'].sum()
        avg_citas = df_medico['Citas'].mean()
        
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        with metric_col1:
            st.metric("Total Citas", total_citas)
        with metric_col2:
            st.metric("Promedio por Médico", f"{avg_citas:.1f}")
        with metric_col3:
            st.metric("Día Más Ocupado", "Viernes")

def generar_pdf_report():
    st.header("📄 Generar Reporte PDF")
    if st.button("Generar Reporte PDF"):
        with st.spinner("Obteniendo datos desde n8n..."):
            try:
                citas = n8n_api("listar_citas", {})
                if not citas:
                    st.warning("⚠️ No se encontraron citas para generar el reporte.")
                    return
            except Exception as e:
                st.error(f"Error al obtener datos: {e}")
                return

        with st.spinner("Generando reporte PDF..."):
            try:
                pdf_bytes = construir_pdf_citas_bytes_pdfreport(citas)
                st.download_button(
                    label="📥 Descargar Reporte PDF",
                    data=pdf_bytes,
                    file_name=f"reporte_citas_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf"
                )
                st.success("Reporte PDF generado exitosamente ✅")
            except Exception as e:
                st.error(f"Error al generar el PDF: {e}")

def main():
    st.title("🏥 Sistema de Gestión de Citas Médicas")

    menu = st.sidebar.selectbox(
        "Menú Principal",
        [
            "Gestión de Pacientes",
            "Gestión de Médicos",
            "Gestión de Citas",
            "Reportes y Análisis",
            "Generar PDF"
        ]
    )
    if menu == "Gestión de Pacientes":
        pagina_gestion_pacientes()
    elif menu == "Gestión de Médicos":
        pagina_gestion_medicos()
    elif menu == "Gestión de Citas":
        pagina_gestion_citas()
    elif menu == "Reportes y Análisis":
        mostrar_reportes()
    elif menu == "Generar PDF":
        generar_pdf_report()

if __name__ == "__main__":
    main()