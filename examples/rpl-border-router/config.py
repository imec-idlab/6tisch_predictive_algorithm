import nodes
import numpy as np

z1 = nodes.platform("z1",18.8,17.4,10,0.023,3)
cc2538 = nodes.platform("cc2538",24,24,13,0.0013,3)
nrf = nodes.platform("nRF52840",6.53,6.4,6.3,0.00316,0.0004,3)

cap_xx_200mf = nodes.capacitor(0.2, 1.8, 5, 2.5, 3.5, 1.2, 0.8, 0.00002*5)
cap_xx_100mf = nodes.capacitor(0.1, 1.8, 5, 2.5, 3, 1.2, 0.8, 0.00002*5)
cap_xx_10mf = nodes.capacitor(0.01, 1.8, 5, 2, 3, 1.2, 0.8, 0.00001*5)
cap_xx_100uf = nodes.capacitor(0.001, 1.8, 5, 2, 3, 1.2, 0.8, 0.000005*5)

### Network configurations ###
# TSCH #
EB_PERIOD       = 16.0                  # Beacon period [s]
SF_PERIOD       = 3.97                  # EB slotframe length [s]
B_PERIOD        = 0.62                  # Broadcast slotframe length [s]
U_PERIOD        = 0.21                  # Unicast slotframe length [s]
L_EB            = 37                    # Beacon length [B]
L_MAC_HDR       = 23                    # MAC header [B]
L_EACK          = 19                    # EACK length [B]
GUARD_DATA      = 0.0022                # RX data guard time [ms]
GUARD_ACK       = 0.0004                # RX ACK guard time [ms]
TS              = 0.01                  # Timeslot size [ms]

# RPL #
IMAX            = 1048.0                # Maximum Trickle interval [s]
L_DIO           = 96                    # DIO length [B]
DAO_PERIOD      = 15.0*60               # DAO period [B] (DAG lifetime, between 15 min and 22.5 min (RPL classic))
L_DAO_NS        = 85                    # DAO length non-storing mode [B]
L_DAO_S         = 76                    # DAO length storing mode [B]
L_DAO_ACK       = 0                     # DAO ACK length [B]

# CoAP
COAP_PERIOD     = 1*60                  # CoAP period [s]
L_COAP_RQ       = 16                    # CoAP request payload [B]
L_COAP_RP       = 0                     # CoAP response payload [B]
L_TOT_HDR       = 49                    # IP, UDP and CoAP header length

# NETWORK
N               = 21                     # Number of nodes
ROOT            = 1                     # Root ID
SERVER          = 1                     # Server ID
COOJA_OFFSET    = 384                   # Offset between ASN and Cooja time [ms]

# PREDICTION
INT_PERIOD      = 15*60                 # INT period [s]
P_INTERVAL      = 900                   # Prediction interval [s]
PROTOCOL        = "Total"               # Choose protocol (Total, CoAP, DAO, DAO ACK, DIO, EB, EACK)
RT              = True                  # Predict in real-time (True) or evaluate after simulation with actual values from cooja (False)
SIM_DIR         = "Simulations/Test"    # Simulation directory for non-real-time predictions
EB_INT          = True                  # Enable optional EB telemetry
DIO_INT         = False                 # Enable optional DIO telemetry
DAO_INT         = True                  # Enable optional DAO telemetry

# PLATFORM
PLATFORM        = nrf                   # Platform for energy calculations
CAPACITOR       = cap_xx_200mf          # Capacitor for energy harvesting predictions

# HARVESTING
HARV_PERIOD     = 20*60                 # Period of harvested power change
MAX_T           = 13200                 # Simulation duration

# Define simulated battery-less nodes  
np.random.seed(5)

bl_nodes = []
for i in range(1,N):
    base = np.random.uniform(0.0003,0.0007)
    # base = 0.0005
    bl_nodes.append(nodes.bl_node(id = i+1,
                harv_seq = np.random.uniform(base-0.0001, base+0.0001, 100),
                # harv_seq = np.random.uniform(base, base, 100),
                harv_period = HARV_PERIOD,
                platform = nrf,
                capacitor=cap_xx_200mf
                ))