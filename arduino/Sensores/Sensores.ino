#define TRIG1 2
#define ECHO1 3
#define TRIG2 4
#define ECHO2 5

#define LED_VERDE 8
#define LED_ROJO 9

int aforo = 0;
const int AFORO_MAXIMO = 50;

// Rango de detección
const int DIST_MIN = 2;   // cm
const int DIST_MAX = 15;  // cm

// Filtrado y tiempos
const int LECTURAS = 3;            // lecturas por muestreo
const unsigned long ENTRY_TIMEOUT = 3000;   // ms para completar secuencia 1->2
const unsigned long EXIT_TIMEOUT  = 3000;   // ms para completar secuencia 2->1
const unsigned long COOLDOWN_AFTER_EVENT = 800; // ms para evitar COLA justo después de evento
const unsigned long COLA_PRINT_INTERVAL = 800;  // ms entre impresiones de COLA

// Estados / tiempos
bool lastS1 = false;
bool lastS2 = false;

int state = 0; // 0 = idle, 1 = saw S1 (posible entrada), 2 = saw S2 (posible salida)
unsigned long stateStartTime = 0;
unsigned long lastEventTime = 0;
unsigned long lastColaPrint = 0;

// -------- LECTURA CON RANGO Y FILTRO --------
bool sensorActivo(int trig, int echo) {
  int lecturasBuenas = 0;
  for (int i = 0; i < LECTURAS; i++) {
    digitalWrite(trig, LOW);
    delayMicroseconds(3);
    digitalWrite(trig, HIGH);
    delayMicroseconds(10);
    digitalWrite(trig, LOW);

    long duracion = pulseIn(echo, HIGH, 30000); // timeout 30 ms
    long d = (duracion == 0) ? 999 : duracion * 0.034 / 2;

    if (d >= DIST_MIN && d <= DIST_MAX) lecturasBuenas++;

    delay(6);
  }
  return lecturasBuenas >= 2; // al menos 2/3 lecturas dentro del rango
}

void setup() {
  pinMode(TRIG1, OUTPUT);
  pinMode(ECHO1, INPUT);
  pinMode(TRIG2, OUTPUT);
  pinMode(ECHO2, INPUT);

  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_ROJO, OUTPUT);

  Serial.begin(9600);
}

void loop() {
  bool s1 = sensorActivo(TRIG1, ECHO1);
  bool s2 = sensorActivo(TRIG2, ECHO2);

  unsigned long now = millis();

  // Detectar flancos rising (falso -> verdadero)
  bool s1Rising = (s1 && !lastS1);
  bool s2Rising = (s2 && !lastS2);

  // Actualizar last
  lastS1 = s1;
  lastS2 = s2;

  // Si estamos en cooldown por evento reciente, ignoramos nuevas iniciaciones
  bool inCooldown = (now - lastEventTime) < COOLDOWN_AFTER_EVENT;

  // --------- Manejo de flancos S1 (inicio posible entrada o confirmación de salida) ----------
  if (s1Rising) {
    // Si venimos de S2 (state == 2), esto confirma SALIDA (2 -> 1)
    if (state == 2) {
      // Confirmar salida
      if (aforo > 0) aforo--;
      Serial.print("SALIDA AFORO: ");
      Serial.println(aforo);
      lastEventTime = now;
      state = 0;
      stateStartTime = 0;
    } else {
      // Posible inicio de entrada, salvo si estamos en cooldown
      if (!inCooldown && state == 0) {
        state = 1; // esperando S2
        stateStartTime = now;
        lastColaPrint = 0; // permitir imprimir COLA de inmediato
        // imprimimos COLA en loop (no aquí) para evitar spam
      }
      // si state == 1 ya, no hacemos nada extra (ya estamos en cola)
    }
  }

  // --------- Manejo de flancos S2 (inicio posible salida o confirmación de entrada) ----------
  if (s2Rising) {
    // Si venimos de S1 (state == 1), esto confirma ENTRADA (1 -> 2)
    if (state == 1) {
      // Confirmar entrada
      aforo = min(aforo + 1, AFORO_MAXIMO);
      Serial.print("ENTRADA AFORO: ");
      Serial.println(aforo);
      lastEventTime = now;
      state = 0;
      stateStartTime = 0;
    } else {
      // Posible inicio de salida (siempre permitido)
      if (!inCooldown && state == 0) {
        state = 2; // esperando S1 para confirmar salida
        stateStartTime = now;
      }
      // si state == 2 ya, no hacemos nada extra
    }
  }

  // --------- Mientras estamos en estado 1 (persona en S1 esperando S2) -> imprimir COLA periódicamente ----------
  if (state == 1) {
    // Si se excedió el timeout sin pasar al sensor 2, volver a idle
    if (now - stateStartTime > ENTRY_TIMEOUT) {
      state = 0;
      stateStartTime = 0;
    } else {
      // imprimir COLA cada COLA_PRINT_INTERVAL ms (pero evitar imprimir justo después de un evento)
      if ((now - lastColaPrint) >= COLA_PRINT_INTERVAL && (now - lastEventTime) > COOLDOWN_AFTER_EVENT) {
        Serial.println("COLA");
        lastColaPrint = now;
      }
    }
  }

  // --------- Mientras estamos en estado 2 (persona en S2 esperando S1) -> timeout para volver a idle ----------
  if (state == 2) {
    if (now - stateStartTime > EXIT_TIMEOUT) {
      state = 0;
      stateStartTime = 0;
    }
    // NO imprimimos COLA en salida; solo esperamos flanco S1 para confirmar salida
  }

  // --------- Control de LEDs ----------
  if (aforo >= AFORO_MAXIMO) {
    digitalWrite(LED_ROJO, HIGH);
    digitalWrite(LED_VERDE, LOW);
  } else {
    digitalWrite(LED_ROJO, LOW);
    digitalWrite(LED_VERDE, HIGH);
  }

  // pequeña espera para evitar saturar el loop
  delay(25);
}
