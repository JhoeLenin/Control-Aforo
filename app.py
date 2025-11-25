# app.py
import random
import threading
import time
import serial  # pip install pyserial
from datetime import datetime
from dash import Dash, html, dcc, dash_table, callback_context
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go

# ==========================================
# 1. CONFIGURACIÓN DE CONEXIÓN
# ==========================================
PUERTO_SERIAL = 'COM5'
BAUD_RATE = 9600

ser = None
modo_simulado = True 

try:
    ser = serial.Serial(PUERTO_SERIAL, BAUD_RATE, timeout=1)
    print(f"Conectado exitosamente al puerto {PUERTO_SERIAL}")
    modo_simulado = False
except Exception as e:
    print(f"MODO SIMULADO ACTIVADO. (Error: {e})")
    modo_simulado = True

# ==========================================
# 2. VARIABLES GLOBALES
# ==========================================
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Variables de Estado
aforo_maximo = 50
personas_actuales = 0
historial = []
ultimo_tiempo_cola = 0      
COLA_TIMEOUT = 1.5          

# Variables para Notificación Temporal
ultimo_cambio_ts = 0        # Marca de tiempo del último cambio
mensaje_notificacion = ""   # Texto a mostrar ("Entrada" o "Salida")
tipo_evento = ""            # Para definir el color (entrada=verde, salida=rojo)

# ==========================================
# 3. HILO DE LECTURA (LOGICA ACTUALIZADA)
# ==========================================
def leer_arduino():
    global personas_actuales, modo_simulado, ultimo_tiempo_cola, ultimo_cambio_ts, mensaje_notificacion, tipo_evento
    while True:
        if ser and ser.is_open:
            try:
                linea = ser.readline().decode('utf-8', errors='ignore').strip()
                
                # --- CASO 1: ACTUALIZACIÓN DE AFORO ---
                if "AFORO:" in linea:
                    partes = linea.split(":")
                    if len(partes) > 1:
                        try:
                            nuevo_valor = int(partes[1].strip())
                            
                            # DETECTAR CAMBIO PARA NOTIFICACIÓN
                            if nuevo_valor != personas_actuales:
                                if "ENTRADA" in linea or nuevo_valor > personas_actuales:
                                    mensaje_notificacion = "ENTRADA DETECTADA"
                                    tipo_evento = "entrada"
                                    ultimo_tiempo_cola = 0 # Reset cola
                                else:
                                    mensaje_notificacion = "SALIDA DETECTADA"
                                    tipo_evento = "salida"
                                
                                ultimo_cambio_ts = time.time() # Guardamos el momento exacto
                            
                            personas_actuales = nuevo_valor
                        except ValueError:
                            pass
                
                # --- CASO 2: DETECCIÓN DE COLA ---
                if "COLA" in linea:
                    ultimo_tiempo_cola = time.time()
                    
            except Exception as e:
                pass
        
        time.sleep(0.02)

if not modo_simulado:
    hilo = threading.Thread(target=leer_arduino)
    hilo.daemon = True
    hilo.start()

# ==========================================
# 4. ESTILOS Y CSS
# ==========================================
colors = {
    "fondo": "#0d1117", "sidebar": "#161b22", "tarjeta": "#1f2937",
    "texto": "#f0f6fc", "acento": "#58a6ff", "alerta": "#f85149",
    "verde": "#3fb950", "aviso": "#e3b341", "borde": "#30363d"
}

app.index_string = """
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Monitor de Aforo</title>
    {%favicon%}
    {%css%}
    <style>
        * { box-sizing: border-box; }
        html, body {
            margin: 0 !important; padding: 0 !important;
            width: 100%; height: 100%;
            background-color: #0d1117; color: #f0f6fc;
            font-family: 'Segoe UI', Roboto, sans-serif;
            overflow-x: hidden;
        }
        .sidebar {
            width: 260px; height: 100vh; position: fixed; top: 0; left: 0;
            background-color: #161b22; transition: left 0.3s ease;
            box-shadow: 2px 0 15px rgba(0,0,0,0.4); z-index: 2000;
        }
        .sidebar.hidden { left: -260px; }
        .menu-item { padding: 15px 25px; cursor: pointer; font-weight: 500; color: #f0f6fc; transition: 0.2s; }
        .menu-item:hover { background-color: #1f2937; }
        
        #page-content {
            margin-left: 260px; padding: 30px; transition: margin-left 0.3s ease; min-height: 100vh;
        }
        #page-content.full-width { margin-left: 0 !important; }
        
        .card {
            background-color: #1f2937; border-radius: 16px; padding: 20px;
            text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            flex: 1; min-width: 200px;
        }
        .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px; width: 100%; }
        .menu-toggle {
            background-color: #58a6ff; color: white; border: none; border-radius: 8px;
            padding: 10px 14px; cursor: pointer; font-size: 20px; min-width: 44px;
        }
        .graph-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px; }
        
        /* ESTILO NOTIFICACIÓN FLOTANTE */
        .notification-toast {
            position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
            padding: 15px 30px; border-radius: 50px;
            font-size: 18px; font-weight: bold;
            box-shadow: 0 5px 25px rgba(0,0,0,0.5);
            z-index: 3000; transition: opacity 0.3s ease;
        }

        @media (max-width: 768px) {
            .sidebar { left: -280px; width: 260px; }
            .sidebar.mobile-open { left: 0; box-shadow: 50px 0 0 100vw rgba(0,0,0,0.5); }
            #page-content { margin-left: 0 !important; padding: 20px; width: 100%; }
            h1 { font-size: 1.5rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .graph-container { grid-template-columns: 1fr; }
            .card { margin-bottom: 15px; width: 100%; }
            .table-responsive { overflow-x: auto; -webkit-overflow-scrolling: touch; }
        }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>
"""

# ==========================================
# 5. LAYOUT
# ==========================================
estado_texto = "🟢 ONLINE" if not modo_simulado else "🟠 SIMULACIÓN"

app.layout = html.Div([
    # --- COMPONENTE DE NOTIFICACIÓN FLOTANTE (Nuevo) ---
    html.Div(id="notificacion-popup", className="notification-toast", style={"display": "none"}),

    # Sidebar
    html.Div([
        html.H2("AFORO", style={"color": colors["acento"], "textAlign": "center", "padding": "18px 0", "margin": "0"}),
        html.Hr(style={"borderColor": colors["acento"]}),
        html.Div("🏠 Dashboard", id="menu-dashboard", className="menu-item", n_clicks=0),
        html.Div("⚙️ Configuración", id="menu-config", className="menu-item", n_clicks=0),
        html.Div(f"Estado: {estado_texto}", style={"padding": "20px", "fontSize": "12px", "color": "#8b949e", "position": "absolute", "bottom": "0"})
    ], id="sidebar", className="sidebar"),

    # Contenido
    html.Div([
        # Header
        html.Div([
            html.Div([ html.H1("Monitor de Aforo", style={"color": colors["acento"], "margin": "0"}) ], style={"flex": "1"}),
            html.Div([ html.Button("☰", id="toggle-btn", className="menu-toggle", n_clicks=0) ])
        ], className="header"),

        # VISTA DASHBOARD
        html.Div(id="dashboard-div", children=[
            
            # WIDGETS
            html.Div([
                html.Div([
                    html.H3("Personas", style={"color": colors["verde"]}),
                    html.H1(id="personas-actuales", style={"fontSize": "42px", "margin": "0", "color": colors["texto"]})
                ], className="card"),

                html.Div([
                    html.H3("Máximo", style={"color": colors["texto"]}),
                    html.H1(id="aforo-max-display", children=str(aforo_maximo), style={"fontSize": "42px", "margin": "0", "color": colors["texto"]})
                ], className="card"),

                html.Div([
                    html.H3("Ocupación", style={"color": colors["texto"]}),
                    html.H1(id="porcentaje-ocupacion", style={"fontSize": "42px", "margin": "0"})
                ], className="card"),

                html.Div([
                    html.H3("Estado", style={"color": colors["texto"]}),
                    html.H1(id="estado-actual-texto", children="--", style={"fontSize": "26px", "marginTop": "8px", "fontWeight": "bold"})
                ], className="card")
            ], style={"display": "flex", "gap": "15px", "marginBottom": "20px", "flexWrap": "wrap"}),

            # GRÁFICAS
            html.Div([
                dcc.Graph(id="grafico-ocupacion", style={"height": "300px", "borderRadius": "12px", "overflow": "hidden"}),
                dcc.Graph(id="grafico-tiempo", style={"height": "300px", "borderRadius": "12px", "overflow": "hidden"})
            ], className="graph-container"),

            # TABLA
            html.Div([
                html.H3("Historial de Eventos", style={"color": colors["texto"], "borderBottom": f"1px solid {colors['acento']}", "paddingBottom": "15px", "marginBottom": "15px"}),
                html.Div([ 
                    dash_table.DataTable(
                        id="tabla-historial",
                        columns=[
                            {"name": "Hora", "id": "hora"},
                            {"name": "Evento", "id": "evento"},
                            {"name": "Personas", "id": "personas"},
                            {"name": "Ocupación (%)", "id": "ocupacion"}
                        ],
                        style_table={"minWidth": "100%"}, 
                        style_cell={
                            "backgroundColor": "#161b22", "color": "#e6edf3", "textAlign": "center",
                            "padding": "10px", "borderBottom": f"1px solid {colors['borde']}", "fontFamily": "Segoe UI"
                        },
                        style_header={
                            "backgroundColor": colors["acento"], "color": "white", "fontWeight": "bold", "border": "none"
                        },
                        style_as_list_view=True,
                    )
                ], className="table-responsive")
            ], style={"backgroundColor": colors["tarjeta"], "padding": "20px", "borderRadius": "16px", "boxShadow": "0 0 15px rgba(0,0,0,0.45)", "marginBottom": "50px"}),

        ], style={"display": "block"}),

        # VISTA CONFIG
        html.Div(id="config-div", children=[
            html.H2("⚙️ Configuración", style={"color": colors["acento"], "textAlign": "center"}),
            html.Div([
                html.Label("Nuevo Aforo: ", style={"fontSize": "18px"}),
                dcc.Input(id="input-aforo", type="number", min=1, value=aforo_maximo, style={"fontSize": "16px", "padding": "8px", "borderRadius": "5px"}),
                html.Button("Guardar", id="guardar-aforo", style={"marginLeft": "10px", "backgroundColor": colors["acento"], "color": "white", "border": "none", "borderRadius": "5px", "padding": "8px 15px", "cursor": "pointer"}),
                html.Div(id="mensaje-guardado", style={"marginTop": "20px", "color": colors["verde"]})
            ], style={"textAlign": "center", "marginTop": "40px"})
        ], style={"display": "none"}),

        dcc.Store(id="sidebar-store", data={"visible": True}),
        dcc.Interval(id="intervalo", interval=300, n_intervals=0),

    ], id="page-content"), 
])

# ==========================================
# 6. CALLBACKS
# ==========================================

@app.callback(
    Output("sidebar", "className"),
    Output("page-content", "className"),
    Output("sidebar-store", "data"),
    Input("toggle-btn", "n_clicks"),
    State("sidebar-store", "data"),
    prevent_initial_call=False
)
def toggle_sidebar(n_clicks, store):
    is_visible = store.get("visible", True)
    if n_clicks and n_clicks > 0: is_visible = not is_visible
    sb_class = "sidebar"
    if is_visible: sb_class += " mobile-open"
    else: sb_class += " hidden"
    content_class = "" if is_visible else "full-width"
    return sb_class, content_class, {"visible": is_visible}

@app.callback(Output("dashboard-div", "style"), Output("config-div", "style"), Input("menu-dashboard", "n_clicks"), Input("menu-config", "n_clicks"))
def nav(n1, n2):
    ctx = callback_context
    if not ctx.triggered or "dashboard" in ctx.triggered[0]["prop_id"]: return {"display": "block"}, {"display": "none"}
    return {"display": "none"}, {"display": "block"}

@app.callback(Output("mensaje-guardado", "children"), Output("aforo-max-display", "children"), Input("guardar-aforo", "n_clicks"), State("input-aforo", "value"))
def save(n, val):
    global aforo_maximo
    if n: aforo_maximo = int(val); return "Guardado", str(aforo_maximo)
    return "", str(aforo_maximo)

@app.callback(
    Output("personas-actuales", "children"), 
    Output("porcentaje-ocupacion", "children"), 
    Output("porcentaje-ocupacion", "style"),
    Output("grafico-ocupacion", "figure"), 
    Output("grafico-tiempo", "figure"), 
    Output("tabla-historial", "data"),
    Output("estado-actual-texto", "children"), 
    Output("estado-actual-texto", "style"),
    # Output Nuevo para la notificación
    Output("notificacion-popup", "children"),
    Output("notificacion-popup", "style"),
    Input("intervalo", "n_intervals")
)
def update(n):
    global personas_actuales, historial, ultimo_tiempo_cola, ultimo_cambio_ts, mensaje_notificacion, tipo_evento
    
    # ---------------------------
    # LÓGICA DE SIMULACIÓN (Actualizada para activar notificación)
    # ---------------------------
    if modo_simulado:
        prev = personas_actuales
        cambio = random.choice([-1, 0, 0, 0, 0, 1]) # Más ceros para que no parpadee tanto
        personas_actuales = max(0, min(aforo_maximo + 2, personas_actuales + cambio))
        
        # Si hubo cambio en simulación, guardamos timestamp
        if personas_actuales != prev:
            ultimo_cambio_ts = time.time()
            if personas_actuales > prev:
                mensaje_notificacion = "🚶 ENTRADA DETECTADA"
                tipo_evento = "entrada"
                ultimo_tiempo_cola = 0
            else:
                mensaje_notificacion = "🔙 SALIDA DETECTADA"
                tipo_evento = "salida"
        elif personas_actuales == prev and random.random() > 0.95:
            ultimo_tiempo_cola = time.time() # Simular cola aleatoria

    # ---------------------------
    # CÁLCULOS GENERALES
    # ---------------------------
    porc = (personas_actuales / aforo_maximo) * 100 if aforo_maximo > 0 else 0
    
    estado_txt, estado_col = "FLUIDO", colors["verde"]
    if personas_actuales >= aforo_maximo: 
        estado_txt, estado_col = "⛔ LLENO", colors["alerta"]
    elif (time.time() - ultimo_tiempo_cola) < COLA_TIMEOUT: 
        estado_txt, estado_col = "⚠️ EN COLA", colors["aviso"]

    if n % 4 == 0:
        historial.append({"hora": datetime.now().strftime("%H:%M:%S"), "evento": estado_txt, "personas": personas_actuales, "ocupacion": f"{porc:.1f}%"})
        if len(historial) > 100: historial = historial[-100:]

    # Gráficas
    gauge = go.Figure(go.Indicator(mode="gauge+number", value=porc, gauge={"axis": {"range": [0, 100]}, "bar": {"color": estado_col}, "steps": [{"range": [0, 100], "color": "#1E293B"}]}))
    gauge.update_layout(paper_bgcolor=colors["tarjeta"], font={"color": colors["texto"]}, margin=dict(t=30, b=20, l=30, r=30), height=250)

    line = go.Figure()
    line.add_trace(go.Scatter(x=[h["hora"] for h in historial], y=[h["personas"] for h in historial], line=dict(color=colors["acento"], width=3)))
    line.update_layout(paper_bgcolor=colors["tarjeta"], plot_bgcolor=colors["tarjeta"], font={"color": colors["texto"]}, margin=dict(t=30, b=40, l=40, r=20), title="Histórico", height=250)

    # ---------------------------
    # LÓGICA DE VISIBILIDAD DE NOTIFICACIÓN
    # ---------------------------
    delta_tiempo = time.time() - ultimo_cambio_ts
    
    # Estilos base de la notificación
    estilo_notif = {
        "display": "none", # Por defecto oculto
        "backgroundColor": colors["verde"] if tipo_evento == "entrada" else colors["alerta"],
        "color": "white"
    }

    # Si pasaron menos de 2 segundos desde el último cambio, mostramos
    if delta_tiempo < 2.0:
        estilo_notif["display"] = "block"
        estilo_notif["opacity"] = "1"
    else:
        estilo_notif["display"] = "none"

    return personas_actuales, f"{porc:.1f}%", {"color": estado_col}, gauge, line, historial[-15:][::-1], estado_txt, {"color": estado_col}, mensaje_notificacion, estilo_notif

if __name__ == "__main__":
    app.run(debug=True, port=8050, use_reloader=False)