# app.py
import random
import threading
import time
import os
import sys
import serial # pip install pyserial
import serial.tools.list_ports # Para buscar puertos solitos
from datetime import datetime
from dash import Dash, html, dcc, dash_table, callback_context
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go

# ==========================================
# 1. PREPARANDO EL TERRENO (CONFIG Y CONEXIÓN)
# ==========================================
BAUD_RATE = 9600
ser = None
modo_simulado = True # Asumimos simulado hasta demostrar lo contrario

# Función para jugar al detective y encontrar el Arduino
def buscar_puerto_arduino():
    print("Buscando Arduino conectado...")
    puertos = list(serial.tools.list_ports.comports())
    
    # Palabras clave comunes en los drivers de Arduino/Clones
    identificadores = ["Arduino", "CH340", "USB SERIAL", "USB-SERIAL"]
    
    for p in puertos:
        # Imprimimos qué encontramos para depurar
        print(f"   -> Encontrado: {p.device} - {p.description}")
        
        # Si la descripción suena a Arduino, lo elegimos
        for ident in identificadores:
            if ident.lower() in p.description.lower():
                return p.device
    
    # Si no encontramos nada obvio, pero hay puertos, devolvemos el primero (a suerte o verdad)
    if puertos:
        return puertos[0].device
        
    return None

# Intentamos conectar
puerto_detectado = buscar_puerto_arduino()

if puerto_detectado:
    try:
        ser = serial.Serial(puerto_detectado, BAUD_RATE, timeout=1)
        # Limpiamos buffer por si quedó basura de antes
        ser.reset_input_buffer()
        print(f"¡Éxito! Conectado al {puerto_detectado}")
        modo_simulado = False
    except Exception as e:
        print(f"Se encontró el puerto {puerto_detectado} pero no pude entrar. (Error: {e})")
        print("   -> Pasando a MODO SIMULADO.")
else:
    print("No se encontró ningún Arduino conectado.")
    print("   -> Pasando a MODO SIMULADO.")

# ==========================================
# 2. LAS VARIABLES DE LA APP
# ==========================================
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Buscar el logo automáticamente en la carpeta assets
logo_src = ""
extensiones_validas = ['png', 'jpg', 'jpeg', 'svg', 'webp']
if os.path.exists('assets'):
    for ext in extensiones_validas:
        if os.path.isfile(f'assets/logo.{ext}'):
            logo_src = f'assets/logo.{ext}'
            break

# Variables que controlan el estado del sistema
aforo_maximo = 50
personas_actuales = 0
historial = [] # Aquí guardamos la data para la gráfica
ultimo_tiempo_cola = 0      
COLA_TIMEOUT = 1.5          

# Variables para los avisos emergentes (Pop-ups)
ultimo_cambio_ts = 0        # Para saber cuándo pasó algo
mensaje_notificacion = ""   # ¿Entraron o salieron?
tipo_evento = ""            # Color del aviso (verde/rojo)

# ==========================================
# 3. EL CEREBRO QUE ESCUCHA (HILO DE FONDO)
# ==========================================
# Este hilo corre separado de la web para no congelarla mientras espera datos
def leer_arduino():
    global personas_actuales, modo_simulado, ultimo_tiempo_cola, ultimo_cambio_ts, mensaje_notificacion, tipo_evento
    while True:
        if ser and ser.is_open:
            try:
                # Leemos línea, quitamos espacios y decodificamos
                linea = ser.readline().decode('utf-8', errors='ignore').strip()
                
                # --- CASO A: El Arduino nos dice cuánta gente hay ---
                if "AFORO:" in linea:
                    partes = linea.split(":")
                    if len(partes) > 1:
                        try:
                            nuevo_valor = int(partes[1].strip())
                            
                            # Si el número cambió, preparamos la notificación
                            if nuevo_valor != personas_actuales:
                                if "ENTRADA" in linea or nuevo_valor > personas_actuales:
                                    mensaje_notificacion = "🚶 ENTRADA DETECTADA"
                                    tipo_evento = "entrada"
                                    ultimo_tiempo_cola = 0 # Si avanza la COLA, reseteamos la alerta de cola
                                else:
                                    mensaje_notificacion = "🔙 SALIDA DETECTADA"
                                    tipo_evento = "salida"
                                
                                ultimo_cambio_ts = time.time() # ¡Hora exacta del suceso!
                            
                            personas_actuales = nuevo_valor
                        except ValueError:
                            pass # Basura en el puerto, ignoramos
                
                # --- CASO B: El sensor detecta que alguien se quedó parado (COLA) ---
                if "COLA" in linea:
                    ultimo_tiempo_cola = time.time()
                    
            except Exception as e:
                print(f"Error leyendo serial: {e}")
        
        # Una pausita para no quemar el procesador
        time.sleep(0.02)

# Solo arrancamos el hilo si el Arduino es real
if not modo_simulado:
    hilo = threading.Thread(target=leer_arduino)
    hilo.daemon = True # Esto hace que el hilo muera si cierras la app principal
    hilo.start()

# ==========================================
# 4. MAQUILLAJE (ESTILOS CSS)
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
        /* Reseteo básico */
        * { box-sizing: border-box; }
        html, body {
            margin: 0 !important; padding: 0 !important;
            width: 100%; height: 100%;
            background-color: #0d1117; color: #f0f6fc;
            font-family: 'Segoe UI', Roboto, sans-serif;
            overflow-x: hidden;
        }
        
        /* Menú lateral (Sidebar) */
        .sidebar {
            width: 260px; height: 100vh; position: fixed; top: 0; left: 0;
            background-color: #161b22; transition: left 0.3s ease;
            box-shadow: 2px 0 15px rgba(0,0,0,0.4); z-index: 2000;
        }
        .sidebar.hidden { left: -260px; }
        .menu-item { padding: 15px 25px; cursor: pointer; font-weight: 500; color: #f0f6fc; transition: 0.2s; }
        .menu-item:hover { background-color: #1f2937; }
        
        /* Contenido principal */
        #page-content {
            margin-left: 260px; padding: 30px; transition: margin-left 0.3s ease; min-height: 100vh;
        }
        #page-content.full-width { margin-left: 0 !important; }
        
        /* Tarjetas de datos */
        .card {
            background-color: #1f2937; border-radius: 16px; padding: 20px;
            text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            flex: 1; min-width: 200px;
        }
        
        /* Header y Logo */
        .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px; width: 100%; }
        .logo-container { height: 50px; margin-right: 15px; }
        .logo-img { height: 100%; width: auto; object-fit: contain; }
        
        .menu-toggle {
            background-color: #58a6ff; color: white; border: none; border-radius: 8px;
            padding: 10px 14px; cursor: pointer; font-size: 20px; min-width: 44px;
        }
        
        .graph-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px; }
        
        /* Notificación Flotante (Toast) */
        .notification-toast {
            position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
            padding: 15px 30px; border-radius: 50px;
            font-size: 18px; font-weight: bold;
            box-shadow: 0 5px 25px rgba(0,0,0,0.5);
            z-index: 3000; transition: opacity 0.3s ease;
        }

        /* Ajustes para celular */
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
# 5. ESTRUCTURA VISUAL (LAYOUT)
# ==========================================
estado_texto = "🟢 CONECTADO" if not modo_simulado else "🟠 MODO SIMULACIÓN"

# Componente del Logo (si existe)
logo_component = html.Div()
if logo_src:
    logo_component = html.Div([
        html.Img(src=logo_src, className="logo-img")
    ], className="logo-container")

app.layout = html.Div([
    # Popup de notificación (invisible por defecto)
    html.Div(id="notificacion-popup", className="notification-toast", style={"display": "none"}),

    # Barra Lateral
    html.Div([
        html.H2("CONTROL", style={"color": colors["acento"], "textAlign": "center", "padding": "18px 0", "margin": "0"}),
        html.Hr(style={"borderColor": colors["acento"]}),
        html.Div("🏠 Panel Principal", id="menu-dashboard", className="menu-item", n_clicks=0),
        html.Div("⚙️ Ajustes", id="menu-config", className="menu-item", n_clicks=0),
        html.Div(f"Estado: {estado_texto}", style={"padding": "20px", "fontSize": "12px", "color": "#8b949e", "position": "absolute", "bottom": "0"})
    ], id="sidebar", className="sidebar"),

    # Área de Contenido
    html.Div([
        # Encabezado con Logo y Título
        html.Div([
            html.Div([
                logo_component, # Aquí va el logo a la izquierda
                html.H1("Monitor de Aforo en Tiempo Real", style={"color": colors["acento"], "margin": "0", "display": "inline-block", "verticalAlign": "middle"}) 
            ], style={"display": "flex", "alignItems": "center", "flex": "1"}),
            
            html.Div([ html.Button("☰", id="toggle-btn", className="menu-toggle", n_clicks=0) ])
        ], className="header"),

        # --- VISTA 1: DASHBOARD ---
        html.Div(id="dashboard-div", children=[
            
            # Tarjetas Superiores
            html.Div([
                html.Div([
                    html.H3("Personas", style={"color": colors["verde"]}),
                    html.H1(id="personas-actuales", style={"fontSize": "42px", "margin": "0", "color": colors["texto"]})
                ], className="card"),

                html.Div([
                    html.H3("Capacidad Máx.", style={"color": colors["texto"]}),
                    html.H1(id="aforo-max-display", children=str(aforo_maximo), style={"fontSize": "42px", "margin": "0", "color": colors["texto"]})
                ], className="card"),

                html.Div([
                    html.H3("% Ocupación", style={"color": colors["texto"]}),
                    html.H1(id="porcentaje-ocupacion", style={"fontSize": "42px", "margin": "0"})
                ], className="card"),

                html.Div([
                    html.H3("Estado del Flujo", style={"color": colors["texto"]}),
                    html.H1(id="estado-actual-texto", children="--", style={"fontSize": "26px", "marginTop": "8px", "fontWeight": "bold"})
                ], className="card")
            ], style={"display": "flex", "gap": "15px", "marginBottom": "20px", "flexWrap": "wrap"}),

            # Gráficas
            html.Div([
                dcc.Graph(id="grafico-ocupacion", style={"height": "300px", "borderRadius": "12px", "overflow": "hidden"}),
                dcc.Graph(id="grafico-tiempo", style={"height": "300px", "borderRadius": "12px", "overflow": "hidden"})
            ], className="graph-container"),

            # Tabla de Historial
            html.Div([
                html.H3("📝 Últimos Movimientos", style={"color": colors["texto"], "borderBottom": f"1px solid {colors['acento']}", "paddingBottom": "15px", "marginBottom": "15px"}),
                html.Div([ 
                    dash_table.DataTable(
                        id="tabla-historial",
                        columns=[
                            {"name": "Hora", "id": "hora"},
                            {"name": "Evento", "id": "evento"},
                            {"name": "Total Personas", "id": "personas"},
                            {"name": "% Ocupación", "id": "ocupacion"}
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

        # --- VISTA 2: CONFIGURACIÓN ---
        html.Div(id="config-div", children=[
            html.H2("⚙️ Ajustar Parámetros", style={"color": colors["acento"], "textAlign": "center"}),
            html.Div([
                html.Label("Definir nuevo límite de aforo: ", style={"fontSize": "18px"}),
                dcc.Input(id="input-aforo", type="number", min=1, value=aforo_maximo, style={"fontSize": "16px", "padding": "8px", "borderRadius": "5px"}),
                html.Button("Actualizar", id="guardar-aforo", style={"marginLeft": "10px", "backgroundColor": colors["acento"], "color": "white", "border": "none", "borderRadius": "5px", "padding": "8px 15px", "cursor": "pointer"}),
                html.Div(id="mensaje-guardado", style={"marginTop": "20px", "color": colors["verde"]})
            ], style={"textAlign": "center", "marginTop": "40px"})
        ], style={"display": "none"}),

        # Almacenamiento local y timer
        dcc.Store(id="sidebar-store", data={"visible": True}),
        dcc.Interval(id="intervalo", interval=300, n_intervals=0), # Se actualiza cada 300ms

    ], id="page-content"), 
])

# ==========================================
# 6. LA MAGIA (CALLBACKS)
# ==========================================

# Callback para abrir/cerrar el menú lateral
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
    
    # Clases CSS dinámicas
    sb_class = "sidebar"
    if is_visible: sb_class += " mobile-open"
    else: sb_class += " hidden"
    
    content_class = "" if is_visible else "full-width"
    return sb_class, content_class, {"visible": is_visible}

# Callback para navegar entre Dashboard y Configuración
@app.callback(Output("dashboard-div", "style"), Output("config-div", "style"), Input("menu-dashboard", "n_clicks"), Input("menu-config", "n_clicks"))
def nav(n1, n2):
    ctx = callback_context
    if not ctx.triggered or "dashboard" in ctx.triggered[0]["prop_id"]: return {"display": "block"}, {"display": "none"}
    return {"display": "none"}, {"display": "block"}

# Callback para guardar el nuevo aforo
@app.callback(Output("mensaje-guardado", "children"), Output("aforo-max-display", "children"), Input("guardar-aforo", "n_clicks"), State("input-aforo", "value"))
def save(n, val):
    global aforo_maximo
    if n: 
        aforo_maximo = int(val)
        return "¡Cambios guardados correctamente!", str(aforo_maximo)
    return "", str(aforo_maximo)

# Callback PRINCIPAL: Actualiza toda la interfaz periódicamente
@app.callback(
    Output("personas-actuales", "children"), 
    Output("porcentaje-ocupacion", "children"), 
    Output("porcentaje-ocupacion", "style"),
    Output("grafico-ocupacion", "figure"), 
    Output("grafico-tiempo", "figure"), 
    Output("tabla-historial", "data"),
    Output("estado-actual-texto", "children"), 
    Output("estado-actual-texto", "style"),
    Output("notificacion-popup", "children"),
    Output("notificacion-popup", "style"),
    Input("intervalo", "n_intervals")
)
def update(n):
    global personas_actuales, historial, ultimo_tiempo_cola, ultimo_cambio_ts, mensaje_notificacion, tipo_evento
    
    # --- BLOQUE DE SIMULACIÓN ---
    # Si no hay Arduino, inventamos datos para probar la interfaz
    if modo_simulado:
        prev = personas_actuales
        # Hacemos que sea más probable que NO pase nada (más ceros) para estabilizar
        cambio = random.choice([-1, 0, 0, 0, 0, 0, 0, 0, 1]) 
        personas_actuales = max(0, min(aforo_maximo + 5, personas_actuales + cambio))
        
        # Simulamos eventos de notificación
        if personas_actuales != prev:
            ultimo_cambio_ts = time.time()
            if personas_actuales > prev:
                mensaje_notificacion = "🚶 ENTRADA SIMULADA"
                tipo_evento = "entrada"
                ultimo_tiempo_cola = 0
            else:
                mensaje_notificacion = "🔙 SALIDA SIMULADA"
                tipo_evento = "salida"
        elif personas_actuales == prev and random.random() > 0.98:
            # A veces simulamos que hay cola
            ultimo_tiempo_cola = time.time()

    # --- CÁLCULOS VISUALES ---
    porc = (personas_actuales / aforo_maximo) * 100 if aforo_maximo > 0 else 0
    
    # Determinar estado (Verde, Amarillo, Rojo)
    estado_txt, estado_col = "🟢 NORMAL", colors["verde"]
    if personas_actuales >= aforo_maximo: 
        estado_txt, estado_col = "⛔ LLENO", colors["alerta"]
    elif (time.time() - ultimo_tiempo_cola) < COLA_TIMEOUT: 
        estado_txt, estado_col = "⚠️ COLA DETECTADA", colors["aviso"]

    # Guardar historial cada cierto tiempo (no cada tick del reloj para no saturar)
    if n % 4 == 0:
        historial.append({"hora": datetime.now().strftime("%H:%M:%S"), "evento": estado_txt, "personas": personas_actuales, "ocupacion": f"{porc:.1f}%"})
        # Mantenemos solo los últimos 100 registros
        if len(historial) > 100: historial = historial[-100:]

    # Configurar Gráfica de Medidor (Gauge)
    gauge = go.Figure(go.Indicator(
        mode="gauge+number", 
        value=porc, 
        number={'suffix': "%"}, # <--- AQUÍ ESTÁ EL CAMBIO
        gauge={
            "axis": {"range": [0, 100]}, 
            "bar": {"color": estado_col}, 
            "steps": [{"range": [0, 100], "color": "#1E293B"}]
        }
    ))
    gauge.update_layout(paper_bgcolor=colors["tarjeta"], font={"color": colors["texto"]}, margin=dict(t=30, b=20, l=30, r=30), height=250)

    # Configurar Gráfica de Línea (Tiempo)
    line = go.Figure()
    line.add_trace(go.Scatter(x=[h["hora"] for h in historial], y=[h["personas"] for h in historial], line=dict(color=colors["acento"], width=3)))
    line.update_layout(paper_bgcolor=colors["tarjeta"], plot_bgcolor=colors["tarjeta"], font={"color": colors["texto"]}, margin=dict(t=30, b=40, l=40, r=20), title="Tendencia", height=250)

    # --- CONTROL DE NOTIFICACIÓN POP-UP ---
    delta_tiempo = time.time() - ultimo_cambio_ts
    estilo_notif = {
        "display": "none", 
        "backgroundColor": colors["verde"] if tipo_evento == "entrada" else colors["alerta"],
        "color": "white"
    }
    # Mostrar solo por 2 segundos después del evento
    if delta_tiempo < 2.0:
        estilo_notif["display"] = "block"
        estilo_notif["opacity"] = "1"

    # Retornamos toooodos los valores a la interfaz
    return personas_actuales, f"{porc:.1f}%", {"color": estado_col}, gauge, line, historial[-15:][::-1], estado_txt, {"color": estado_col}, mensaje_notificacion, estilo_notif

if __name__ == "__main__":
    app.run(debug=True, port=8050, use_reloader=False)