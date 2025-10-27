"""
planta_opcua.py
Simula una planta primer orden y comunica con PLC via OPC UA.
Lee MV (manipulated variable) desde el PLC y escribe PV (process value) de vuelta.
Diseñado para usarse con PLCSIM Advanced exponiendo variables OPC UA (p.ej. DB1.MV, DB1.PV).
"""

import time
from opcua import Client, ua
import sys
import random

# === CONFIG (ajusta según tu proyecto TIA/PLCSIM) ===
OPC_ENDPOINT = "opc.tcp://192.168.0.1:4840"   # ajusta si PLCSIM usa otra IP/puerto
NODE_MV = 'ns=3;s="PID_SIM_3_DB"."ManipulatedValue"'    # ejemplo de NodeId; confirma en tu servidor OPC UA
NODE_PV = 'ns=3;s="PID_SIM_3_DB"."ProcessValue"'
TS = 0.1   # tiempo de muestreo [s] -> debe coincidir con tu OB en PLC
Kproc = 1.0
Tau = 2.0  # segundos (constante de tiempo de la planta)
NOISE_PCT = 0.0025  # 0.0 para pruebas sin ruido, 0.0025 = ±0.25%

# === Delay settings ===
delay_seconds = 10.0
delay_samples = int(delay_seconds / TS + 0.5)

# variables internas de la planta
pv = 20.0  # valor inicial (en la misma escala que uses, ej 0..100)
t = 0.0

# Inicializa FIFO con un valor neutro
initial_mv = 0.0
fifo = [initial_mv] * delay_samples

# --- funciones auxiliares ---

def connect_client():
    """Intenta conectar al servidor OPC UA con reintentos."""
    while True:
        try:
            client = Client(OPC_ENDPOINT)
            client.connect()
            print(f"[OK] Conectado a {OPC_ENDPOINT}")
            node_mv = client.get_node(NODE_MV)
            node_pv = client.get_node(NODE_PV)
            return client, node_mv, node_pv
        except Exception as e:
            print(f"[WARN] Falló conexión: {e}")
            print("Reintentando en 3 s...")
            time.sleep(3)

def write_value(node, value):
    """Escribe un float en el nodo dado."""
    try:
        data_value = ua.DataValue(ua.Variant(pv, ua.VariantType.Float))
        node.set_attribute(ua.AttributeIds.Value, data_value)
        return True
    except Exception as e:
        print(f"Error escribiendo PV: {e}")
        return False

def read_value(node):
    """Lee valor de nodo OPC UA (float)."""
    try:
        return float(node.get_value())
    except Exception as e:
        print(f"Error leyendo MV: {e}")
        return None

# --- bucle principal ---

client, node_mv, node_pv = connect_client()

try:
    while True:
        start = time.time()

        # Leer MV desde PLC (suponiendo REAL)
        mv = read_value(node_mv)
        if mv is None:
            # comunicación caída → reconectar
            client.disconnect()
            print("[INFO] Reconectando...")
            client, node_mv, node_pv = connect_client()
            continue

         # --- APLICA RETARDO ---
        fifo.append(mv)
        mv_delayed = fifo.pop(0)

        # Modelo primer orden discretizado (Euler explícito)
        # dPV/dt = (Kproc * MV - PV) / Tau   => PV_next = PV + Ts * ((Kproc*MV - PV) / Tau)
        new_pv = pv + TS * ((Kproc * mv_delayed - pv) / Tau)

        # Ruido multiplicativo (aplicar sobre el nuevo PV)
        noise = (random.random() - 0.5) * 2.0 * NOISE_PCT   # -NOISE_PCT .. +NOISE_PCT
        new_pv = new_pv * (1.0 + noise)

        # Option: saturate PV to 0..100
        if new_pv < 0.0:
            new_pv = 0.0
        elif new_pv > 100.0:
            new_pv = 100.0

        pv = new_pv

        # Escribir PV de vuelta al PLC
        ok = write_value(node_pv, pv)
        if not ok:
            client.disconnect()
            print("[INFO] Reconectando...")
            client, node_mv, node_pv = connect_client()
            continue

        # logging ligero
        print(f"t={t:.2f}s  MV={mv:.2f}  MV_delayed={mv_delayed:.2f}  PV={pv:.3f}")

        # sincronizar con Ts
        elapsed = time.time() - start
        sleep_for = TS - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)
        else:
            # si estamos atrasados, warn y seguir sin sleep
            print(f"Warning: loop tardó {elapsed:.3f}s > TS={TS}s")
        t += TS

except KeyboardInterrupt:
    print("\n[SIGINT] Cancelado por el usuario.")
finally:
    try:
        client.disconnect()
        print("[OK] Desconectado correctamente.")
    except:
        pass

    sys.exit(0)
