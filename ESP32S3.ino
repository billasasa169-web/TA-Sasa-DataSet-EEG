#include <Arduino.h>
#include <NimBLEDevice.h>
#include <math.h>

// ===================== CONFIG =====================
#define TIMER_FREQ  1000000UL
#define SAMP_RATE   500.0

#define SYNC_BYTE_1 0xC7
#define SYNC_BYTE_2 0x7C
#define END_BYTE    0x01
#define BAUD_RATE   230400

// Packet: [C7][7C][CTR][HI][LO][01]
#define PACKET_LEN  6

const uint8_t adcPin = 4; // GPIO4

// ===================== NOTCH FILTER =====================
#define NOTCH_ENABLE 1
#define NOTCH_FREQ   50.0    // 50Hz PLN (ubah ke 60.0 kalau perlu)
#define NOTCH_Q      20.0

struct Biquad {
  float b0, b1, b2, a1, a2;
  float x1=0, x2=0, y1=0, y2=0;

  float process(float x) {
    float y = b0*x + b1*x1 + b2*x2 - a1*y1 - a2*y2;
    x2=x1; x1=x;
    y2=y1; y1=y;
    return y;
  }
};

Biquad notch;

void designNotch(Biquad &q, float f0, float Q, float fs) {
  float w0 = 2.0f * (float)M_PI * (f0 / fs);
  float cw = cosf(w0);
  float sw = sinf(w0);
  float alpha = sw / (2.0f * Q);

  float b0 = 1.0f;
  float b1 = -2.0f * cw;
  float b2 = 1.0f;
  float a0 = 1.0f + alpha;
  float a1 = -2.0f * cw;
  float a2 = 1.0f - alpha;

  q.b0 = b0 / a0;
  q.b1 = b1 / a0;
  q.b2 = b2 / a0;
  q.a1 = a1 / a0;
  q.a2 = a2 / a0;

  q.x1=q.x2=q.y1=q.y2=0;
}

// ===================== BLE =====================
static const char* BLE_NAME = "ESP32S3-ADC";

static NimBLEUUID SERVICE_UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E");
static NimBLEUUID RX_UUID     ("6E400002-B5A3-F393-E0A9-E50E24DCCA9E");
static NimBLEUUID TX_UUID     ("6E400003-B5A3-F393-E0A9-E50E24DCCA9E");

NimBLECharacteristic* txChar = nullptr;
volatile bool bleConnected = false;

// ===================== OUTPUT MODE =====================
enum { MODE_SERIAL, MODE_BLE, MODE_BOTH };
volatile uint8_t outMode = MODE_SERIAL;

// ===================== GLOBAL =====================
uint8_t packet[PACKET_LEN];
volatile bool bufferReady = false;
volatile bool running = false;
hw_timer_t* timer1 = nullptr;

// ===================== ACQ =====================
void acqStart() { running = true; timerStart(timer1); }
void acqStop()  { running = false; timerStop(timer1); }

// ===================== COMMAND =====================
void handleCommand(String cmd) {
  cmd.trim(); cmd.toUpperCase();

  auto reply = [&](const char* s){
    if (outMode == MODE_SERIAL || outMode == MODE_BOTH) Serial.println(s);
  };

  if (cmd == "START") { acqStart(); reply("RUNNING"); }
  else if (cmd == "STOP") { acqStop(); reply("STOPPED"); }
  else if (cmd == "STATUS") reply(running ? "RUNNING":"STOPPED");
  else if (cmd == "MODE BLE")   { outMode = MODE_BLE;   reply("OK MODE BLE"); }
  else if (cmd == "MODE SERIAL"){ outMode = MODE_SERIAL;reply("OK MODE SERIAL"); }
  else if (cmd == "MODE BOTH")  { outMode = MODE_BOTH;  reply("OK MODE BOTH"); }
  else if (cmd == "WHORU") reply("ESP32-S3");
  else reply("UNKNOWN COMMAND");
}

// ===================== ISR =====================
void IRAM_ATTR ADC_ISR() {
  uint16_t v = analogRead(adcPin);

#if NOTCH_ENABLE
  float x = (float)v - 2048.0f;
  float y = notch.process(x) + 2048.0f;
  if (y < 0) y = 0;
  if (y > 4095) y = 4095;
  v = (uint16_t)(y + 0.5f);
#endif

  packet[3] = (uint8_t)(v >> 8);
  packet[4] = (uint8_t)(v & 0xFF);
  packet[2]++;                 // counter
  bufferReady = true;
}

// ===================== BLE CALLBACKS (SUPER KOMPATIBEL) =====================
class ServerCB : public NimBLEServerCallbacks {
public:
  void onConnect(NimBLEServer* s) { (void)s; bleConnected = true; }
  void onDisconnect(NimBLEServer* s) { (void)s; bleConnected = false; NimBLEDevice::startAdvertising(); }
};

class RxCB : public NimBLECharacteristicCallbacks {
public:
  void onWrite(NimBLECharacteristic* c) {
    std::string v = c->getValue();
    if (v.empty()) return;
    handleCommand(String(v.c_str()));
  }
};

// ===================== SETUP BLE =====================
void setupBLE() {
  NimBLEDevice::init(BLE_NAME);
  NimBLEDevice::setPower(ESP_PWR_LVL_P9);

  NimBLEServer* srv = NimBLEDevice::createServer();
  srv->setCallbacks(new ServerCB());

  NimBLEService* svc = srv->createService(SERVICE_UUID);

  txChar = svc->createCharacteristic(TX_UUID, NIMBLE_PROPERTY::NOTIFY);

  NimBLECharacteristic* rx = svc->createCharacteristic(
    RX_UUID,
    NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR
  );
  rx->setCallbacks(new RxCB());

  svc->start();

  NimBLEAdvertising* adv = NimBLEDevice::getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->start();
}

// ===================== SETUP =====================
void setup() {
  Serial.begin(BAUD_RATE);
  Serial.setTimeout(100);

  packet[0] = SYNC_BYTE_1;
  packet[1] = SYNC_BYTE_2;
  packet[2] = 0;
  packet[5] = END_BYTE;

  analogReadResolution(12);

#if NOTCH_ENABLE
  designNotch(notch, NOTCH_FREQ, NOTCH_Q, SAMP_RATE);
#endif

  timer1 = timerBegin(TIMER_FREQ);
  timerAttachInterrupt(timer1, &ADC_ISR);
  timerAlarm(timer1, (uint64_t)(TIMER_FREQ / SAMP_RATE), true, 0);
  timerStop(timer1);

  setupBLE();
  outMode = MODE_SERIAL; // default
}

// ===================== LOOP =====================
void loop() {
  if (running && bufferReady) {
    bufferReady = false;

    // SERIAL STREAM
    if (outMode == MODE_SERIAL || outMode == MODE_BOTH) {
      Serial.write(packet, PACKET_LEN);
    }

    // BLE STREAM
    if ((outMode == MODE_BLE || outMode == MODE_BOTH) && bleConnected && txChar) {
      txChar->setValue(packet, PACKET_LEN);
      txChar->notify();
    }
  }

  if (Serial.available()) {
    handleCommand(Serial.readStringUntil('\n'));
  }
}
