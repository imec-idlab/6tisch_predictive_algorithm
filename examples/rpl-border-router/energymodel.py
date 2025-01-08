import numpy as np
import math
import socket
import traffic_model as tm

try:    
    import config
except:
    print("Did you fill the fields in the config.py.example file and rename it to config.py?")
    exit()
    
UDP_SRC_PORT = 31001
UDP_DEST_PORT = 5678

#initialize udp socket
def init_udp_socket():
    global UDP_SRC_PORT
    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    sock.bind(('',UDP_SRC_PORT))
    return sock

#function for sending udp messages
def send_udp_message(sock, address, message):
    global UDP_DEST_PORT
    sock.sendto(message.encode(), (address, UDP_DEST_PORT))
    
udp_socket = init_udp_socket()

# For unicast Tx slots (DAO, DAO_ACK, COAP)
def get_TxDataRxAck_energy(bytes):
    tx_time = 0.000032*bytes
    rx_time = 0.000032*17+config.GUARD_ACK/2
    cpu_time = config.TS-tx_time-rx_time
    energy = (tx_time*config.PLATFORM.tx + rx_time*config.PLATFORM.rx + cpu_time*config.PLATFORM.cpu)*config.PLATFORM.v
    return energy

# Get TxDataRxAck times in ms
def get_TxDataRxAck_times_ms(bytes, radio_times):
    tx_time = 0.032*bytes
    rx_time = 0.032*17+config.GUARD_ACK*2000
    radio_times[0] += rx_time
    radio_times[1] += tx_time

# For unicast Rx slots (DAO, DAO_ACK, COAP)
def get_RxDataTxAck_energy(bytes):
    tx_time = 0.000032*17
    rx_time = 0.000032*bytes+config.GUARD_DATA/2
    cpu_time = config.TS-tx_time-rx_time
    energy = (tx_time*config.PLATFORM.tx + rx_time*config.PLATFORM.rx + cpu_time*config.PLATFORM.cpu)*config.PLATFORM.v
    return energy

# Get RxDataTxAck times in ms    
def get_RxDataTxAck_times_ms(bytes, radio_times):
    tx_time = 0.032*17
    rx_time = 0.032*bytes+config.GUARD_DATA*2000
    radio_times[0] += rx_time
    radio_times[1] += tx_time

# For broadcast Tx slots (DIO) en EB tx slots
def get_TxData_energy(bytes):
    tx_time = 0.000032*bytes
    rx_time = 0 
    cpu_time = config.TS-tx_time-rx_time
    energy = (tx_time*config.PLATFORM.tx + rx_time*config.PLATFORM.rx + cpu_time*config.PLATFORM.cpu)*config.PLATFORM.v
    return energy
    
# Get TxData times in ms    
def get_TxData_times_ms(bytes, radio_times, n):
    tx_time = 0.032*bytes
    rx_time = 0 
    radio_times[0] += rx_time*n
    radio_times[1] += tx_time*n

# For broadcast Rx slots (DIO) en EB rx slots
def get_RxData_energy(bytes):
    tx_time = 0
    rx_time = 0.000032*bytes+config.GUARD_DATA/2
    cpu_time = config.TS-tx_time-rx_time
    energy = (tx_time*config.PLATFORM.tx + rx_time*config.PLATFORM.rx + cpu_time*config.PLATFORM.cpu)*config.PLATFORM.v
    return energy

# Get RxData times in ms    
def get_RxData_times_ms(bytes, radio_times, n):
    tx_time = 0
    rx_time = 0.032*bytes+config.GUARD_DATA*2000
    radio_times[0] += rx_time*n
    radio_times[1] += tx_time*n

# For idle Rx slots (broadcast, unicast & EB)
def get_RxIdle_energy():
    tx_time = 0
    rx_time = config.GUARD_DATA+0.0008
    lpm_time = config.TS-tx_time-rx_time
    energy = (tx_time*config.PLATFORM.tx + rx_time*config.PLATFORM.rx + lpm_time*config.PLATFORM.lpm)*config.PLATFORM.v
    return energy

# Get RxIdle times in ms    
def get_RxIdle_times_ms(radio_times, n):
    tx_time = 0
    rx_time = config.GUARD_DATA*1000+0.8
    radio_times[0] += rx_time*n
    radio_times[1] += tx_time*n
    

###
# Get energy consumption
# Input:    nodes
###
def get_energy(nodes):  
    for n in nodes:
        n.TxDataEnergy += get_TxData_energy(config.L_EB)*len(n.ebtxslots)/1000
        n.RxDataEnergy += get_RxData_energy(config.L_EB)*len(n.ebrxslots)/1000
        n.TxDataEnergy += get_TxData_energy(config.L_DIO)*len(n.diotxslots)/1000
        n.RxDataEnergy += get_RxData_energy(config.L_DIO)*len(n.diorxslots)/1000
        for slot in n.daotxslots:
            n.TxDataRxAckEnergy += get_TxDataRxAck_energy(slot[1])/1000
        for slot in n.daorxslots:
            n.RxDataTxAckEnergy += get_RxDataTxAck_energy(slot[1])/1000
        for slot in n.coaptxslots:
            n.TxDataRxAckEnergy += get_TxDataRxAck_energy(slot[1])/1000
        for slot in n.coaprxslots:
            n.RxDataTxAckEnergy += get_RxDataTxAck_energy(slot[1])/1000
        n.RxIdleEnergy += get_RxIdle_energy()*(n.idlediorxslots+n.idleebrxslots+n.idleunicastrxslots)/1000
        total_slots = len(n.ebtxslots)+len(n.ebrxslots)+len(n.diotxslots)+len(n.diorxslots)+len(n.daotxslots)+len(n.daorxslots)+len(n.coaptxslots)+len(n.coaprxslots)+(n.idlediorxslots+n.idleebrxslots+n.idleunicastrxslots)
        idle_energy = (config.P_INTERVAL-total_slots*config.TS)*config.PLATFORM.lpm*config.PLATFORM.v/1000
        n.totalEnergy = n.TxDataEnergy+n.RxDataEnergy+n.TxDataRxAckEnergy+n.RxDataTxAckEnergy+n.RxIdleEnergy+idle_energy
        n.energies.append([n.predtime,n.totalEnergy])
        
###
# Update energy prediction with new divisor value
# Input: energy prediction, previous divisor, divisor
# Output: energy prediction
###        
def update_energy(E, prev_divisor, divisor):  
    E = E + (math.ceil(config.P_INTERVAL/config.U_PERIOD)*(1.0/divisor - 1.0/prev_divisor))*get_RxIdle_energy()/1000
    E = E + (math.ceil(config.P_INTERVAL/config.U_PERIOD)*(1.0/prev_divisor - 1.0/divisor))*config.TS*config.PLATFORM.lpm*config.PLATFORM.v/1000
    return E
        
###
# Get radio times in ms
# Input:    nodes
###
def get_radio_times(nodes):  
    for n in nodes:
        radio_times = [0,0]
        get_TxData_times_ms(config.L_EB, radio_times, len(n.ebtxslots))
        get_RxData_times_ms(config.L_EB, radio_times, len(n.ebrxslots))
        get_TxData_times_ms(config.L_DIO, radio_times, len(n.diotxslots))
        get_RxData_times_ms(config.L_DIO, radio_times, len(n.diorxslots))
        for slot in n.daotxslots:
            get_TxDataRxAck_times_ms(slot[1], radio_times)
        for slot in n.daorxslots:
            get_RxDataTxAck_times_ms(slot[1], radio_times)
        for slot in n.coaptxslots:
            get_TxDataRxAck_times_ms(slot[1], radio_times)
        for slot in n.coaprxslots:
            get_RxDataTxAck_times_ms(slot[1], radio_times)
        get_RxIdle_times_ms(radio_times,n.idlediorxslots+n.idleebrxslots+n.idleunicastrxslots)
        n.energest_pred.append(radio_times)
        
###
# Search for closest energy prediction
# Input: node
# Output: closest energy prediction
###
def search_closest_prediction(node,t):
    closest_pair = None
    min_difference = float('inf')

    if(len(node.energies)!= 0):
        for pair in node.energies:
            time = pair[0]
            energy = pair[1]
            difference = abs(time - t)

            if difference < min_difference:
                min_difference = difference
                closest_pair = pair
        return closest_pair
    else:
        return -1,-1

###
# Estimate remaining voltage in capacitor
# Input: node, capacitor
# Output:
###
def estimate_voltage(node, e_out):
    # for node in nodes:
    p_in = node.last_p_harv*config.CAPACITOR.pmu_h/100000
    v_0 = node.last_voltage/1000
    t_0 = node.last_harvester_update
    p_out = (e_out/config.P_INTERVAL)*config.CAPACITOR.pmu_l + config.CAPACITOR.p_leak
    v_p = (config.PLATFORM.v*p_in/p_out)*(1-math.exp(-(config.P_INTERVAL*p_out)/(pow(config.PLATFORM.v,2)*config.CAPACITOR.C)))+v_0*math.exp(-(config.P_INTERVAL*p_out)/(pow(config.PLATFORM.v,2)*config.CAPACITOR.C))
    # Get suitable threshold voltage
    if(node.sf_divisor == 1):
        v_th = 1.8/(math.exp(-(config.P_INTERVAL*p_out)/(pow(config.PLATFORM.v,2)*config.CAPACITOR.C)))
        v_on = np.sqrt(2*0.47/config.CAPACITOR.C+pow(v_th,2))
        print("Vth",v_th, "Von", v_on, "Node", node.id)
    node.predicted_voltage = v_p
    node.predicted_time = t_0+config.P_INTERVAL*1000            

###
# Calculate divisor value for each node
# Input: nodes
###
def calculate_divisor(nodes):
    for node in nodes:
        t_p,e_out = search_closest_prediction(node,node.last_harvester_update*10)        
        if(t_p != -1):
            estimate_voltage(node, e_out)
            div_changed = 0
            while(node.predicted_voltage < config.CAPACITOR.v_cutoff and node.sf_divisor < 6 and node.predicted_voltage < node.last_voltage/1000):
                node.sf_divisor =  min(node.sf_divisor+1,6)
                e_out = update_energy(e_out, node.sf_divisor-1, node.sf_divisor)
                estimate_voltage(node, e_out)
                print("V",node.predicted_voltage)
                div_changed = 1
            while(node.predicted_voltage > config.CAPACITOR.v_turnon and node.sf_divisor > 1):
                node.sf_divisor = max(node.sf_divisor-1,1)
                e_out = update_energy(e_out, node.sf_divisor+1, node.sf_divisor)
                estimate_voltage(node, e_out)
                print("V",node.predicted_voltage)
                div_changed = 1
            if(node.predicted_voltage != 0 and (node.predicted_voltage < 2 or node.last_voltage/1000 < 2) and node.sf_divisor < 6):
                node.sf_divisor = 6
                div_changed = 1
            if(div_changed == 1):
                send_udp_message(udp_socket, node.ipaddr, "Increase SF " + str(node.sf_divisor))
                node.sent_voltage = node.predicted_voltage 

###
# Get maximum payload of predicted slots
# Input: predicted slots
# Output: maximum payload of predicted slots
###
def get_max_slot(slots):
    if(len(slots) > 0):
        return np.max([slot[1] for slot in slots])
    else:
        return 0
        
###
# Get unicast peak tasks
# Input: node
# Output peak unicast TX task, peak unicast RX task
###
def get_unicast_peak(node):
    daotx_max = get_max_slot(node.daotxslots)
    coaptx_max = get_max_slot(node.coaptxslots)
    if(max(daotx_max,coaptx_max) != 0):
        peak_uctx = get_TxDataRxAck_energy(max(daotx_max,coaptx_max))
    else:
        peak_uctx = 0
    daorx_max = get_max_slot(node.daorxslots)
    coaprx_max = get_max_slot(node.coaprxslots)
    peak_ucrx = get_RxDataTxAck_energy(max(daorx_max,coaprx_max))
    return peak_uctx,peak_ucrx
        
###
# Get peak sequence
# Input: node, peak unicast TX task, peak unicast RX task
# Output: peak sequence energy, peak sequence duration
###
def get_peak_sequence(node, peak_uctx, peak_ucrx):
    if(len(node.diotxslots) > 0):
        peak_bc = get_TxData_energy(config.L_DIO)
    elif(len(node.diorxslots) > 0):
        peak_bc = get_RxData_energy(config.L_DIO)
    else:
        peak_bc = get_RxIdle_energy()
    if(len(node.ebtxslots) > 0):
        peak_eb = get_TxData_energy(config.L_EB)
    elif(len(node.ebrxslots) > 0):
        peak_eb = get_RxData_energy(config.L_EB)
    else:
        peak_eb = get_RxIdle_energy()
    #TODO: include number of neigbors (UC) and time sources (EB)
    peak_sequence = [peak_uctx,peak_ucrx,peak_bc,peak_eb]
    peak_time = len(peak_sequence)*config.TS
    peak_energy = np.sum(peak_sequence)
    return peak_energy, peak_time

###
# Get frequent task and associated idle period
# Input: node, peak unicast TX task, peak unicast RX task, peak sequence duration
# Output: frequent task, idle period
###        
def get_frequent_task(node, peak_uctx, peak_ucrx, peak_time):
    frequent_task = 0
    idle_period = 0
    # EB SF is smallest
    if(config.SF_PERIOD < min(config.B_PERIOD, config.U_PERIOD)):
        # EB period higher than 2 EB slotframes?
        if(config.EB_PERIOD > 2*config.SF_PERIOD):
            frequent_task = get_RxIdle_energy()
            idle_period = config.SF_PERIOD-config.TS
        else:
            frequent_task = get_TxData_energy(config.L_EB)
            idle_period = config.EB_PERIOD-config.TS
    # UC SF is smallest
    elif(config.U_PERIOD < min(config.SF_PERIOD, config.B_PERIOD)):
        tx_slots = len(node.daotxslots)+len(node.coaptxslots)
        rx_slots = len(node.daorxslots)+len(node.coaprxslots)
        if(tx_slots > node.plannedunicastrxslots/2):
            frequent_task = peak_uctx
            idle_period = (config.P_INTERVAL/tx_slots)-config.TS
        elif(rx_slots > node.plannedunicastrxslots/2):
            frequent_task = peak_ucrx
            idle_period = (config.P_INTERVAL/rx_slots)-config.TS
        else:
            frequent_task = get_RxIdle_energy()
            idle_period = config.U_PERIOD-config.TS
    # BC SF is smallest
    else:
        if(len(node.diotxslots) > node.planneddiotxslots/2):
            frequent_task = get_TxData_energy(config.L_DIO)
            idle_period = (config.P_INTERVAL/node.diotxslots)-config.TS
        elif(len(node.diorxslots) > node.planneddiorxslots/2):
            frequent_task = get_RxData_energy(config.L_DIO)
            idle_period = (config.P_INTERVAL/rx_slots)-config.TS
        else:
            frequent_task = get_RxIdle_energy()
            idle_period = config.B_PERIOD-config.TS
    return frequent_task, idle_period-peak_time
            
                        
###
# Evaluate energy harvesting feasibility
###
def get_eh_feasibility(nodes):
    for n in nodes:
        peak_uctx, peak_ucrx = get_unicast_peak(n)
        peak_energy, peak_time = get_peak_sequence(n,peak_uctx,peak_ucrx)
        frequent_task, idle_period = get_frequent_task(n,peak_uctx,peak_ucrx,peak_time)