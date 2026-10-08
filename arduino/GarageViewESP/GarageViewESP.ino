#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h> // Nécessaire pour envoyer la distance au backend
#include "esp_http_server.h"
#include "secrets.h" // Vos mots de passe et URL secrètes sont ici !

// ===========================
// Identifiants Wi-Fi (lus depuis secrets.h)
// ===========================
const char *ssid = WIFI_SSID;
const char *password = WIFI_PASS;

// ===========================
// Broches pour CAMERA_MODEL_WROVER_KIT
// ===========================
#define PWDN_GPIO_NUM    -1
#define RESET_GPIO_NUM   -1
#define XCLK_GPIO_NUM    21
#define SIOD_GPIO_NUM    26
#define SIOC_GPIO_NUM    27
#define Y9_GPIO_NUM      35
#define Y8_GPIO_NUM      34
#define Y7_GPIO_NUM      39
#define Y6_GPIO_NUM      36
#define Y5_GPIO_NUM      19
#define Y4_GPIO_NUM      18
#define Y3_GPIO_NUM       5
#define Y2_GPIO_NUM       4
#define VSYNC_GPIO_NUM   25
#define HREF_GPIO_NUM    23
#define PCLK_GPIO_NUM    22

// ===========================
// Broches additionnelles
// ===========================
#define RELAY_PIN        14
#define TRIG_PIN         12
#define ECHO_PIN         13

// ===========================
// Configuration du Backend (lue depuis secrets.h)
// ===========================
const char* backendUrl = BACKEND_URL;

// ===========================
// Serveur de flux vidéo
// ===========================
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\nX-Timestamp: %d.%06d\r\n\r\n";

httpd_handle_t stream_httpd = NULL;
httpd_handle_t camera_httpd = NULL; 

// ===========================
// Handlers API
// ===========================
static bool is_servo_moving = false;
static unsigned long last_trigger_time = 0;
const unsigned long COOLDOWN_MS = 3000; // 3 seconds cooldown between triggers


static esp_err_t trigger_handler(httpd_req_t *req) {
  Serial.println("🌐 Ordre reçu via HTTP : Actionner la porte");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  // --- Auth & Security ---
  char token_header[64] = {0};
  if (httpd_req_get_hdr_value_str(req, "X-ESP32-TOKEN", token_header, sizeof(token_header)) != ESP_OK) {
    Serial.println("🔒 Accès refusé : Token manquant");
    httpd_resp_send_err(req, HTTPD_401_UNAUTHORIZED, "Unauthorized");
    return ESP_FAIL;
  }

  const char* expected_token = ESP32_API_KEY;
  size_t len_expected = strlen(expected_token);
  size_t len_actual = strlen(token_header);
  uint8_t result = (len_expected == len_actual) ? 0 : 1;
  for (size_t i = 0; i < len_expected && i < len_actual; i++) {
    result |= (expected_token[i] ^ token_header[i]);
  }
  if (result != 0) {
    Serial.println("🔒 Accès refusé : Token invalide");
    httpd_resp_send_err(req, HTTPD_401_UNAUTHORIZED, "Unauthorized");
    return ESP_FAIL;
  }
  // --- Fin Auth ---

  
  // Sécurité anti-spam : on refuse de lancer le servo s'il est déjà en train de bouger
  // ou si le délai de cooldown n'est pas écoulé.
  if (is_servo_moving || (millis() - last_trigger_time < COOLDOWN_MS)) {
    Serial.println("⏳ Commande ignorée : le servo bouge déjà ou cooldown actif !");
    const char* resp = "BUSY";
    httpd_resp_send(req, resp, strlen(resp));
    return ESP_OK;
  }
  
  is_servo_moving = true; // On verrouille le moteur
  last_trigger_time = millis();

  // --- RÉGLAGES DU SERVOMOTEUR ---
  // Modifie ces deux valeurs pour ajuster l'amplitude du mouvement.
  // Un SG90 accepte des valeurs entre 500 (minimum) et 2400 (maximum).
  int position_repos = 1000; // Position quand le doigt est relevé
  int position_appui = 1200; // Position quand le doigt appuie (Ajusté selon ta demande)
  
  // Mouvement du Servomoteur (Appui)
  for(int i=0; i<25; i++) {
    digitalWrite(RELAY_PIN, HIGH);
    delayMicroseconds(position_appui); 
    digitalWrite(RELAY_PIN, LOW);
    delay(18); // Libère le processeur (évite le plantage de la caméra)
    delayMicroseconds(2000 - position_appui); 
  }
  
  // Mouvement du Servomoteur (Relâche)
  for(int i=0; i<25; i++) {
    digitalWrite(RELAY_PIN, HIGH);
    delayMicroseconds(position_repos); 
    digitalWrite(RELAY_PIN, LOW);
    delay(18); // Libère le processeur
    delayMicroseconds(2000 - position_repos);
  }
  
  is_servo_moving = false; // On déverrouille le moteur
  
  const char* resp = "OK: Servomoteur declenche";
  httpd_resp_send(req, resp, strlen(resp));
  return ESP_OK;
}

static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = NULL;
  struct timeval _timestamp;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t *_jpg_buf = NULL;
  char *part_buf[128]; 

  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;
  
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "X-Framerate", "60");

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      res = ESP_FAIL;
    } else {
      _timestamp.tv_sec = fb->timestamp.tv_sec;
      _timestamp.tv_usec = fb->timestamp.tv_usec;
      if (fb->format != PIXFORMAT_JPEG) {
        res = ESP_FAIL; 
      } else {
        _jpg_buf_len = fb->len;
        _jpg_buf = fb->buf;
      }
    }
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
    if (res == ESP_OK) {
      size_t hlen = snprintf((char *)part_buf, 128, _STREAM_PART, _jpg_buf_len, _timestamp.tv_sec, _timestamp.tv_usec);
      res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
    }
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    
    if (fb) {
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if (_jpg_buf) {
      free(_jpg_buf);
      _jpg_buf = NULL;
    }
    if (res != ESP_OK) break;
  }
  return res;
}

void startCameraServer() {
  // Serveur API (Port 80)
  httpd_config_t config_api = HTTPD_DEFAULT_CONFIG();
  config_api.server_port = 80;
  httpd_uri_t trigger_uri = { .uri = "/trigger", .method = HTTP_POST, .handler = trigger_handler, .user_ctx = NULL };
  if (httpd_start(&camera_httpd, &config_api) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &trigger_uri);
    Serial.println("🌍 Serveur API (port 80) démarré !");
  }

  // Serveur Vidéo (Port 81)
  httpd_config_t config_stream = HTTPD_DEFAULT_CONFIG();
  config_stream.server_port = 81;     
  config_stream.ctrl_port = 32769;    
  httpd_uri_t stream_uri = { .uri = "/stream", .method = HTTP_GET, .handler = stream_handler, .user_ctx = NULL };
  if (httpd_start(&stream_httpd, &config_stream) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
    Serial.println("🎥 Serveur Vidéo démarré sur le port 81 !");
  }
}

void sendDistanceToBackend(int distance_cm) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(backendUrl);
    http.addHeader("Content-Type", "application/json");
    
    String payload = "{\"distance\": " + String(distance_cm) + "}";
    int httpResponseCode = http.POST(payload);
    
    if(httpResponseCode <= 0) {
      Serial.println("❌ Erreur de connexion au backend");
    }
    http.end();
  }
}

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true); 
  Serial.println();

  // Initialisation de la broche du Transistor/Servo (fail-safe)
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); 
  
  // Placement explicite du servo au repos au démarrage (fail-safe)
  for(int i=0; i<10; i++) {
    digitalWrite(RELAY_PIN, HIGH);
    delayMicroseconds(1000); // position_repos
    digitalWrite(RELAY_PIN, LOW);
    delay(19);
  }
  digitalWrite(RELAY_PIN, LOW);

  // Initialisation du Capteur Ultrason
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_UXGA; 
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  if (config.pixel_format == PIXFORMAT_JPEG) {
    if (psramFound()) {
      config.jpeg_quality = 10;
      config.fb_count = 2;
      config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
      config.frame_size = FRAMESIZE_SVGA;
      config.fb_location = CAMERA_FB_IN_DRAM;
    }
  }

  // Initialisation de la caméra
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  sensor_t *s = esp_camera_sensor_get();
  
  // Retournement de l'image (à l'envers)
  s->set_vflip(s, 1);   // Retourne verticalement
  s->set_hmirror(s, 1); // Effet miroir (horizontal) pour que la gauche reste à gauche

  if (config.pixel_format == PIXFORMAT_JPEG) {
    s->set_framesize(s, FRAMESIZE_QVGA); 
  }

  // Connexion Wi-Fi
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("WiFi connected ! IP : ");
  Serial.println(WiFi.localIP());

  startCameraServer();
}

unsigned long dernierMesure = 0;

void loop() {
  // On fait la mesure toutes les 2 secondes pour ne pas inonder le processeur
  if (millis() - dernierMesure > 2000) {
    dernierMesure = millis();

    // Envoi de l'impulsion
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    // On utilise un timeout court (20000 microsecondes = 20 ms) 
    // pour que pulseIn ne bloque JAMAIS la caméra plus longtemps que ça.
    // 20ms = environ 3.4 mètres maximum de lecture, c'est parfait pour un garage.
    long duree = pulseIn(ECHO_PIN, HIGH, 20000); 

    int distance_cm = duree * 0.034 / 2;

    Serial.print("📏 Distance mesurée : ");
    Serial.print(distance_cm);
    Serial.println(" cm");
    
    // Envoi au serveur Python
    sendDistanceToBackend(distance_cm);
  }
}
