# Sistema de Control de Aforo (Arduino + Python)

Sistema de monitoreo de aforo en tiempo real optimizado para **Windows**. Este proyecto combina hardware (Arduino con sensores ultrasónicos) y software (Python Dash) para controlar el flujo de personas, detectar colas y visualizar estadísticas.

🔗 **Repositorio:** [https://github.com/JhoeLenin/Control-Aforo.git](https://github.com/JhoeLenin/Control-Aforo.git)

## Características Principales

* **Detección Bidireccional:** Algoritmo secuencial para diferenciar entradas de salidas.
* **Interfaz Visual:** Dashboard con medidor de aguja, gráficas en tiempo real y alertas pop-up.
* **Alerta de Colas:** Detecta si una persona obstruye la entrada por más de 1.5 segundos.
* **Plug & Play:** El software detecta automáticamente en qué puerto COM está el Arduino.
* **Feedback LED:** Indicadores visuales físicos (Verde/Rojo).

## Requisitos

* **Sistema Operativo:** Windows 10 u 11.
* **Hardware:** Arduino Uno/Nano, 2 Sensores HC-SR04, LEDs.
* **Software:**
  * [Python 3.10+](https://www.python.org/downloads/) (Importante: Marcar "Add Python to PATH" al instalar).
  * [Arduino IDE](https://www.arduino.cc/en/software) (Para cargar el código a la placa).
* **Git**
---

## 1. Conexiones de Hardware

Realiza el cableado siguiendo estrictamente esta tabla para que coincida con el código:

| Componente | Pin Arduino | Función | Definición en Código |
| :--- | :--- | :--- | :--- |
| **Sensor Entrada (HC-SR04)** | | *Ubicado hacia la calle* | |
| Trig | **Pin 2** | Emisor pulso | `#define TRIG1 2` |
| Echo | **Pin 3** | Receptor | `#define ECHO1 3` |
| **Sensor Confirmación (HC-SR04)** | | *Ubicado hacia el interior* | |
| Trig | **Pin 4** | Emisor pulso | `#define TRIG2 4` |
| Echo | **Pin 5** | Receptor | `#define ECHO2 5` |
| **Indicadores** | | | |
| LED Verde | **Pin 8** | Acceso Libre | `#define LED_VERDE 8` |
| LED Rojo | **Pin 9** | Aforo Lleno | `#define LED_ROJO 9` |
| Alimentación | 5V | VCC | - |
| Tierra | GND | GND | - |

> **Nota de Instalación:** Coloca el "Sensor Entrada" unos centímetros antes que el "Sensor Confirmación" en la dirección de ingreso.

---

## Guía de Instalación Paso a Paso (Windows)

Sigue estos pasos para poner el sistema en marcha en una computadora nueva:

### PASO 1: Descargar el Proyecto
Abre tu terminal (PowerShell o CMD) y ejecuta:

```bash
git clone https://github.com/JhoeLenin/Control-Aforo.git
```
### PASO 2: Cargar el Código al Arduino
1. Conecta tu placa Arduino a la computadora por USB.
2. Abre la carpeta `arduino/` que está dentro de este proyecto.
3. Haz doble clic en el archivo `.ino` para abrirlo con el **Arduino IDE**.
4. En el menú superior, ve a **Herramientas > Placa** y selecciona tu modelo (ej. Arduino Uno).
5. Ve a **Herramientas > Puerto** y selecciona el puerto COM disponible.
6. Haz clic en el botón ➡️ **Subir** (Upload) para cargar el código a la placa.

### PASO 3: Configurar Python (Entorno Virtual)
Para evitar errores con librerías, crearemos un entorno aislado. Ejecuta estos comandos en tu terminal dentro de la carpeta del proyecto:

**A. Crear el entorno virtual:**
```bash
python -m venv venv
```
**B. Activar el entorno:**
```bash
./venv/Scripts/activate
```
(Deberías ver `(venv)` al principio de la línea de comandos. Si recibes un error de permisos en PowerShell, ejecuta primero: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`).

**C. Instalar las dependencias:**
```bash
pip install requirements.txt
```
### PASO 4: Ejecutar el sistema
Una vez instalado todo y con el Arduino conectado por USB:
1. Asegúrate de tener el entorno activado (venv).
2. Ejecuta el comando:
```bash
python app.py
```
3. Verás mensajes en la consola indicando que se encontró el Arduino (ej. "¡Éxito! Conectado al COM3").
4. Abre tu navegador web e ingresa a: http://127.0.0.1:8050/
