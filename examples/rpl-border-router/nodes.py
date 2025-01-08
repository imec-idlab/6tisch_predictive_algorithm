import numpy as np
import math

def init(MOP):
    global nodes                # Array of nodes
    global read                 # Interrupt reading logfile and perform prediction
    global count                # How many nodes did we encounter?
    global mop                  # RPL MOP (1 = storing mode, 0 = non-storing mode)
    global logfile              # Logfile name
    global logsize              # Logfile size
    global logcount             # Current line in logfile
    global cont                 # Continue reading logfile
    global intstream            # Required to change INT update interval

    nodes = []
    count = 0
    read = True
    logcount = 0
    cont = True
    intstream = False
    mop = MOP

class node:
    def __init__(self, id):
        self.id = id            # Node ID
        self.ipaddr = "fd00::20"+str(id)+":"+ str(id)+":"+ str(id)+":"+ str(id)
        self.n = 0              # Number of neighbours
        self.ns = []            # Neighbours
        self.ts = None          # Time source
        self.pn = None          # Preferred parent
        self.etx = 1            # ETX preferred parent
        self.coaptx = 0         # Amount of TX bytes due to CoAP traffic
        self.coaptxslots = []   # variabelen toevoegen om info op te slaan over slots en aantal bytes vb: [[Tx,10b], ...]
        self.coaprx = 0         # Amount of RX bytes due to CoAP traffic
        self.coaprxslots = []
        self.idleunicastrxslots = 0
        self.plannedunicastrxslots = 0
        self.ebtx = 0           # Amount of TX bytes due to EB traffic
        self.ebtxslots = []
        self.ebrx = 0           # Amoount of RX bytes due to EB traffic
        self.ebrxslots = []
        self.plannedebrxslots = 0 # Amount of planned EB RX slots
        self.idleebrxslots = 0  # Amount of idle EB RX slots
        self.diotx = 0          # Amount of TX bytes due to DIO traffic
        self.diotxslots = []
        self.diorx = 0          # Amount of RX bytes due to DIO traffic
        self.diorxslots = []
        self.planneddiorxslots = 0
        self.planneddiotxslots = 0
        self.idlediorxslots = 0
        
        self.daotx = 0          # Amount of TX bytes due to DAO traffic
        self.daotxslots = []
        self.daorx = 0          # Amount of RX bytes due to DAO traffic
        self.daorxslots = []
        self.dao_acktx = 0      # Amount of TX bytes due to DAO ACK traffic
        self.dao_acktxslots = []
        self.dao_ackrx = 0      # Amount of RX bytes due to DAO ACK traffic
        self.dao_ackrxslots = []
        self.eacktx = 0         # Amount of TX bytes due to EACK traffic
        self.eackrx = 0         # Amount of RX bytes due to EACK traffic
        self.lastdao = None     # Node time of last DAO transmission
        self.lastdio = None     # Node time of last DIO transmission
        self.lastebgen = None   # Node time of last EB generation
        self.lastebtx = None    # Node time of last EB transmission
        self.updtime = None     # Node time of last INT update
        self.predtime = None    # Time of prediction
        self.energest = []      # Energest state times (t, RX, TX) [ms]
        self.energest_pred = [] # Energest state times predictions (RX, TX) [ms]
        self.intbytes = [[],[]] # Number of INT bytes with timestamp
        self.rt = []            # Routing table
        self.coapsumtx = 0
        self.coapsumrx = 0
        self.TxDataEnergy = 0
        self.RxDataEnergy = 0 
        self.TxDataRxAckEnergy = 0
        self.RxDataTxAckEnergy = 0
        self.RxIdleEnergy = 0
        self.totalEnergy = 0
        self.energies = []
        # Energy harvesting parameters
        self.last_voltage = 0
        self.last_p_harv = 0
        self.last_harvester_update = 0
        self.predicted_voltage = 0
        self.predicted_time = 0
        self.sent_voltage = 0
        self.sf_divisor = 1

    def add_neighbour(self, neighbour):
        if(np.any(np.isin(self.ns,neighbour)) == 0):
            self.ns = np.append(self.ns,neighbour)
            self.n = len(self.ns)

    def search_eb_receivers(self):
        receivers = []
        if(len(nodes) != 0):
            for tsn in nodes:
                if((tsn.ts != None) and (tsn.ts.id == self.id)):
                    receivers.append(tsn)
        return receivers
    
    def get_next_hop_sm(self, destination):
        if(len(self.rt) != 0):
            for route in self.rt:
                if(route[0].id == destination.id):
                    return route[1]
        return -1
    
    def is_node_in_path(self,path):
        if(len(path) != 0):
            for p in path:
                if(p.id == self.id):
                    return True
        return False

    def reset_bytecount(self):
        self.coaptx = 0
        self.ebtx = 0
        self.diotx = 0     
        self.daotx = 0  
        self.dao_acktx = 0 
        self.eacktx = 0
        self.coaprx = 0
        self.ebrx = 0
        self.diorx = 0     
        self.daorx = 0  
        self.dao_ackrx = 0 
        self.eackrx = 0
        self.diorxslots = []
        self.diotxslots = []
        self.ebtxslots = []
        self.ebrxslots = []
        self.daotxslots = []
        self.daorxslots = []
        self.dao_acktxslots = []
        self.dao_ackrxslots = []
        self.coaptxslots = []
        self.coaprxslots = []
        self.coapsumtx = 0
        self.coapsumrx = 0
        self.TxDataEnergy = 0
        self.RxDataEnergy = 0 
        self.TxDataRxAckEnergy = 0
        self.RxDataTxAckEnergy = 0
        self.totalEnergy = 0
        self.plannedebrxslots = 0 
        self.idleebrxslots = 0 
        self.planneddiorxslots = 0
        self.planneddiotxslots = 0
        self.idlediorxslots = 0
        self.plannedunicastrxslots = 0
        self.idleunicastrxslots = 0
        self.TxDataEnergy = 0
        self.RxDataEnergy = 0
        self.TxDataEnergy = 0
        self.RxDataEnergy = 0
        self.TxDataRxAckEnergy = 0
        self.RxDataTxAckEnergy = 0
        self.TxDataRxAckEnergy = 0
        self.RxDataTxAckEnergy = 0
        self.RxIdleEnergy = 0
        self.totalEnergy = 0

    def print_n(self, telemetry, traffic, energest, energy, interval):
        print("================")
        print("Node " + str(self.id))
        # if(telemetry):
            # print("----------")
            # print("Telemetry:")
            # print("#Neighbours:\t\t" + str(self.n))
            # string = ""
            # for n in self.ns:
            #     string = string + str(n.id) + " "
            # print("Neighbours:\t\t" + string)
            # if(self.rt != []):
            #     print("Routing table:\t\t")
            #     for r in self.rt:
            #         print(str(r[0].id) + " v " + str(r[1].id))
            # if(self.ts != None):
            #     print("Time source:\t\t" + str(self.ts.id))
            # if(self.pn != None):
            #     print("Preferred parent:\t" + str(self.pn.id))
            # if(self.lastdao != None):
            #     print("Last DAO at:\t\t" + str(self.lastdao) + " ms")
            # if(self.lastdio != None):
            #     print("Last DIO at:\t\t" + str(self.lastdio) + " ms")
            # if(self.lastebgen != None):
            #     print("Last EB gen at:\t\t" + str(self.lastebgen) + " ms")
            # if(self.lastebtx != None):
            #     print("Last EB TX at:\t\t" + str(self.lastebtx) + " ms")
            # if(self.updtime != None):
            #     print("Last update at:\t\t" + str(self.updtime) + " ms")
        # if(self.predtime != None):
        #     print("Prediction at:\t\t" + str(self.predtime) + " ms")
        # print(str(interval) + " s prediction")
        if(traffic):
            print("----------")
            print("Traffic prediction:")
            print("EB bytes: \t\t" + str(self.ebtx) + " TX / " + str(self.ebrx) + " RX")
            print("EB slots: \t\t" + str(len(self.ebtxslots))+ " TX / " + str(len(self.ebrxslots))+ " RX")
            print("Idle EB RX slots: \t"+ str(self.idleebrxslots))
            print("EACK bytes: \t\t" + str(self.eacktx) + " TX / " + str(self.eackrx) + " RX")
            print("DIO bytes: \t\t" + str(round(self.diotx,2)) + " TX / " + str(round(self.diorx,2)) + " RX")
            print("DIO slots: \t\t" + str(len(self.diotxslots))+ " TX / " + str(len(self.diorxslots)) + " Rx")
            print("Idle BC RX slots: \t"+ str(self.idlediorxslots))
            print("DAO bytes: \t\t" + str(round(self.daotx,2)) + " TX / " + str(round(self.daorx,2)) + " RX")
            print("DAO slots: \t\t" + str(len(self.daotxslots))+ " TX / " + str(len(self.daorxslots))+ " RX")
            print("DAO ACK bytes: \t\t" + str(self.dao_acktx) + " TX / " + str(self.dao_ackrx) + " RX")
            print("DAO ACK slots: \t\t" + str(len(self.dao_acktxslots))+ " TX / " + str(len(self.dao_ackrxslots))+ " RX")
            print("CoAP bytes: \t\t" + str(round(self.coaptx,2)) + " TX / " + str(round(self.coaprx,2)) + " RX")
            print("CoAP slots: \t\t" + str(len(self.coaptxslots)) + " TX / "+ str(len(self.coaprxslots)) + " RX")
            print("Idle UC RX slots: \t"+ str(self.idleunicastrxslots))
            print("Total TX bytes:\t\t" + str(round(self.diotx+self.ebtx+self.eacktx+self.coaptx+self.daotx+self.dao_acktx+self.diotx,2)))
            print("Total RX bytes:\t\t" + str(round(self.diorx+self.ebrx+self.eackrx+self.coaprx+self.daorx+self.dao_ackrx+self.diorx,2)))
            print("Total bytes:\t\t" + str(round(self.diotx+self.ebtx+self.eacktx+self.coaptx+self.daotx+self.dao_acktx+self.diotx+self.diorx+self.ebrx+self.eackrx+self.coaprx+self.daorx+self.dao_ackrx+self.diorx,2)))
        if(energest):
            print("----------")            
            print("Energest prediction:")
            if((len(self.energest_pred) > 90) and (len(self.energest) > 90)):
                predicted = [self.energest_pred[-90][0], self.energest_pred[-90][1]]
                energest = [(self.energest[-1][1]-self.energest[-90][1]), (self.energest[-1][2]-self.energest[-90][2])]
                print("RX " + str(predicted[0]) + " TX " + str(predicted[1]))
                print("RX " + str(energest[0]) + " TX " + str(energest[1]))
                print("RX " + str(round(100*(predicted[0]-energest[0])/predicted[0],2)) + "% TX " + str(round(100*(predicted[1]-energest[1])/predicted[1],2)) + "%")       
        if(energy):
            # print("----------")
            # print("Energy prediction:")  
            print(self.totalEnergy,"J\tDivisor:", self.sf_divisor)
            # print("----------")            
            # print("Harvester update:")
            print(self.last_voltage,"mV",self.last_p_harv*10,"uW",self.last_harvester_update,"ms")
            print("Predicted voltage:",self.predicted_voltage,"at",self.predicted_time,"ms")

def search_node(n):
    if(len(nodes) != 0):
        for i in nodes:
            if(n == i.id):
                return i
    return -1

def get_etx(node1, node2):
    if((node1.pn != None) and (node1.pn.id == node2.id)):
        etx = max(node1.etx,1)
    elif((node2.pn != None) and (node2.pn.id == node1.id)):
        etx = max(node2.etx,1)
    else:
        etx = 1
    return etx

class platform:
    def __init__(self, name, rx, tx, cpu, lpm, off, v):
        self.name = name
        self.rx = rx
        self.tx = tx
        self.cpu = cpu
        self.lpm = lpm
        self.off = off
        self.v = v
        
        self.t_ts = 0.01 
        self.tx_time = 0
        self.rx_time = 0
        self.e_ts = 0  
        self.energy_update = 0
        self.join = 1
        
    def calculate_ts_energy(self, tx_time, rx_time, idle):
        tx = tx_time - self.tx_time
        rx = rx_time - self.rx_time
        e_missed = 0
        # Missed updates during harvester update
        if(self.energy_update and rx > self.t_ts*1000):
            cpu_time = rx/2.2*(self.t_ts*1000-2.2)/2
            e_missed = ((tx*self.tx + rx*self.rx + cpu_time*self.cpu)/1000000)
            # self.energy_update = 0
        # Joining energy
        elif(self.join == 1 and rx > 1000*self.t_ts*1000):
            cpu_time = 0
            e_missed = ((tx*self.tx + rx*self.rx + cpu_time*self.cpu)/1000000)
            self.join = 0
        # if(rx > 10*self.t_ts*1000):
        #     cpu_time = 0
        #     e_missed = ((tx*self.tx + rx*self.rx + cpu_time*self.cpu)/1000000)
        else:
            cpu_time = self.t_ts*1000 - tx - rx
            cpu = self.cpu if not idle else self.lpm
            self.e_ts = ((tx*self.tx + rx*self.rx + cpu_time*self.cpu)/1000000)
        self.tx_time = tx_time
        self.rx_time = rx_time
        return e_missed
        
class capacitor:
    def __init__(self, c, v_min, v_max, v_cutoff, v_turnon, pmu_l, pmu_h, p_leak):
        self.C = c
        self.v_min = v_min
        self.v_max = v_max
        self.p_leak = p_leak
        self.pmu_l = pmu_l
        self.pmu_h = pmu_h
        self.v_cutoff = v_cutoff
        self.v_turnon = v_turnon
        
        self.t_previous = 0
        self.t_ts = 0.01    
        
    def fully_charge(self):
        # self.V = self.v_max
        self.V = self.v_turnon
    
    # def charge_turnon(self, platform, harv_seq, harv_i, harv_period):
    def charge_turnon(self, dev):    
        # p_in = p_harv*self.pmu_h
        p_in = dev.harv_seq[dev.harv_i]*self.pmu_h
        p_out = dev.platform.off*dev.platform.v*self.pmu_l/1000.0
        t_charge_total = 0
        t_charge = -((dev.platform.v*self.C)/p_out)*np.log((self.v_turnon-(dev.platform.v*p_in/p_out))/(self.V-(dev.platform.v*p_in/p_out)))
        while(t_charge > dev.harv_period):
            t_charge_total += dev.harv_period
            print(t_charge_total)
            # calculate voltage after harv_period
            self.V = min((dev.platform.v*p_in/p_out)*(1-math.exp(-(dev.harv_period*p_out)/(pow(dev.platform.v,2)*self.C)))+self.V*math.exp(-(dev.harv_period*p_out)/(pow(dev.platform.v,2)*self.C)),self.v_max)
            print(self.V)
            dev.harv_i = (dev.harv_i + 1) % len(dev.harv_seq)
            p_in = dev.harv_seq[dev.harv_i]*self.pmu_h
            # calculate t_charge again
            t_charge = -((dev.platform.v*self.C)/p_out)*np.log((self.v_turnon-(dev.platform.v*p_in/p_out))/(self.V-(dev.platform.v*p_in/p_out)))
            print(t_charge)
        t_charge_total += t_charge
        self.V = self.v_turnon
        self.t_previous += t_charge_total
        return t_charge_total    
        
    def update_voltage(self, t, platform, e_missed, p_harv):
        p_lpm = platform.lpm*platform.v/1000.0
        time = t-self.t_previous
        # First, calculate the voltage after charging
        p_in = p_harv*self.pmu_h
        if(e_missed != 0):
            p_out = (e_missed/time + p_lpm)*self.pmu_l + self.p_leak
            # platform.energy_update = 0
        else:    
            p_out = (p_lpm)*self.pmu_l + self.p_leak
        v_charge = min((platform.v*p_in/p_out)*(1-math.exp(-(time*p_out)/(pow(platform.v,2)*self.C)))+self.V*math.exp(-(time*p_out)/(pow(platform.v,2)*self.C)),self.v_max)
        # Then, calculate the voltage after timeslot
        p_out = (platform.e_ts/self.t_ts)*self.pmu_l + self.p_leak
        v_timeslot = max(min((platform.v*p_in/p_out)*(1-math.exp(-(self.t_ts*p_out)/(pow(platform.v,2)*self.C)))+v_charge*math.exp(-(self.t_ts*p_out)/(pow(platform.v,2)*self.C)),self.v_max),0)
        # Update capacitor voltage and time
        self.V = v_timeslot
        self.t_previous = t+self.t_ts
        return v_charge, v_timeslot
        
class bl_node:
    def __init__(self, id, harv_seq, harv_period, platform, capacitor):
        self.id = id
        self.harv_seq = harv_seq
        self.harv_period = harv_period
        self.platform = platform
        self.capacitor = capacitor
        
        self.harv_i =  0
        self.t_change_pharv = 0
        self.int_times = []