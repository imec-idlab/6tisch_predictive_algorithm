###############
### IMPORTS ###
###############

import numpy as np
import nodes as ns
import parse_log
import csv
import energymodel as em
import traffic_model as tm

try:    
    import config
except:
    print("Did you fill the fields in the config.py.example file and rename it to config.py?")
    exit()

            
ns.init(1)
if(not config.RT):
    ns.logfile = open(config.SIM_DIR + "/topology.log","r")
    ns.logsize = len(ns.logfile.readlines())
    ns.logfile.seek(0)
    print("Parsing root logfile...")
with open('predictions.csv', 'w', newline='') as csvfile:
    predwriter = csv.writer(csvfile, delimiter=' ')
    predwriter.writerow(['Time','Node_ID','V_pred','T_pred','Divisor','PP','ETX'])
    
    while(ns.cont):
        # Start reading logfile
        ns.read = True
        # Reset estimated bytes
        for n in ns.nodes:
            n.reset_bytecount()
        # Get topology from logfile
        parse_log.update_topology(config.RT)
        # Estimate EB bytes
        tm.get_eb_bytes(ns.nodes)
        # Estimate DIO bytes
        tm.get_dio_bytes(ns.nodes)
        # Estimate DAO bytes         
        tm.get_daos(ns.nodes)
        # Estimate CoAP bytes
        tm.get_p2p_coap_bytes(ns.nodes, config.L_COAP_RQ, config.L_COAP_RP)
        # Estimate unicast slots
        tm.get_unicast_slots(ns.nodes)
        # Estimate energy consumption
        em.get_energy(ns.nodes)
        em.get_radio_times(ns.nodes)
        em.calculate_divisor(ns.nodes)
        # Get feasibility
        em.get_eh_feasibility(ns.nodes)
        if(len(ns.nodes) == config.N):
            totalint = 0
            numberint = 0
            for n in ns.nodes:
                if(config.RT and (n.id != 0)):
                    n.print_n(1, 0, 0, 1, config.P_INTERVAL)
                totalint += sum(n.intbytes[1])
                numberint = len(n.intbytes[1])
