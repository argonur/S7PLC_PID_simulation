"""
planta_opcua.py
First-order plant simulation with OPC UA communication to a PLC.
Reads MV from PLC and writes PV back. Designed for PLCSIM Advanced
exposing OPC UA variables (e.g., DB1.MV, DB1.PV).
"""

import time
from opcua import Client, ua
import sys
import random

# === CONFIGURATION ===
OPC_ENDPOINT = "opc.tcp://192.168.0.1:4840"  # OPC UA endpoint
NODE_MV = 'ns=3;s="PID_SIM_3_DB"."ManipulatedValue"'  # NodeId for MV
NODE_PV = 'ns=3;s="PID_SIM_3_DB"."ProcessValue"'      # NodeId for PV
TS = 0.1          # sampling time [s] (must match OB in PLC)
Kproc = 1.0       # plant gain
Tau = 2.0         # plant time constant [s]
NOISE_PCT = 0.0025  # ±0.25% multiplicative noise

# === DELAY SETTINGS ===
DELAY_SEC = 10.0
DELAY_SAMPLES = int(DELAY_SEC / TS + 0.5)

# Initialize plant state and FIFO for delayed MV
pv = 20.0
t = 0.0
initial_mv = 0.0
fifo = [initial_mv] * DELAY_SAMPLES

# --- HELPER FUNCTIONS ---

def connect_client():
    """Connect to OPC UA server with retry loop."""
    while True:
        try:
            client = Client(OPC_ENDPOINT)
            client.connect()
            print(f"[OK] Connected to {OPC_ENDPOINT}")
            return client, client.get_node(NODE_MV), client.get_node(NODE_PV)
        except Exception as e:
            print(f"[WARN] Connection failed: {e}. Retrying in 3s...")
            time.sleep(3)

def write_value(node, value):
    """Write float value to OPC UA node."""
    try:
        node.set_attribute(ua.AttributeIds.Value, ua.DataValue(ua.Variant(value, ua.VariantType.Float)))
        return True
    except Exception as e:
        print(f"Error writing PV: {e}")
        return False

def read_value(node):
    """Read float value from OPC UA node."""
    try:
        return float(node.get_value())
    except Exception as e:
        print(f"Error reading MV: {e}")
        return None

# --- MAIN LOOP ---

client, node_mv, node_pv = connect_client()

try:
    while True:
        start = time.time()

        # Read MV from PLC
        mv = read_value(node_mv)
        if mv is None:
            client.disconnect()
            print("[INFO] Reconnecting...")
            client, node_mv, node_pv = connect_client()
            continue

        # Apply FIFO delay
        fifo.append(mv)
        mv_delayed = fifo.pop(0)

        # First-order plant model (explicit Euler)
        new_pv = pv + TS * ((Kproc * mv_delayed - pv) / Tau)

        # Apply multiplicative noise
        noise = (random.random() - 0.5) * 2.0 * NOISE_PCT
        new_pv *= (1.0 + noise)

        # Saturate PV to 0..100
        new_pv = max(0.0, min(100.0, new_pv))
        pv = new_pv

        # Write PV back to PLC
        if not write_value(node_pv, pv):
            client.disconnect()
            print("[INFO] Reconnecting...")
            client, node_mv, node_pv = connect_client()
            continue

        # Simple logging
        print(f"t={t:.2f}s  MV={mv:.2f}  MV_delayed={mv_delayed:.2f}  PV={pv:.3f}")

        # Synchronize loop with TS
        elapsed = time.time() - start
        sleep_for = TS - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)
        else:
            print(f"Warning: loop took {elapsed:.3f}s > TS={TS}s")
        t += TS

except KeyboardInterrupt:
    print("\n[SIGINT] Cancelled by user.")
finally:
    try:
        client.disconnect()
        print("[OK] Disconnected correctly.")
    except:
        pass

    sys.exit(0)
