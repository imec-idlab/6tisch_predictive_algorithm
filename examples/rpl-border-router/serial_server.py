import csv
import socket
import sys
from socketserver import TCPServer
import signal
import re
from _socket import dup  # type: ignore
from sliplib import SlipRequestHandler
import argparse
import config
import time
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Slider
 
# Update function to modify the plot with a maximum of 100 values
def update_plot(x, y, amplitude_slider, node):  
    # Append new data
    x_data.append(x)
    y_data.append(y)
    
    # Limit to the last 600 values
    if len(x_data) > 1000:
        x_data.pop(0)  # Remove the first element
        y_data.pop(0)  # Remove the first element

    # Update the plot data
    line.set_xdata(x_data)
    line.set_ydata(y_data)

    # Rescale and redraw the plot
    ax.relim()  # Recompute limits
    ax.autoscale_view()  # Rescale axes
    plt.draw()  # Update the plot
    
    # Update the slider value in node object
    node.harv_seq[0] = amplitude_slider.val / 1000000.0  # Get the current slider value
    
    plt.pause(0.005)  # Small pause to allow GUI to update
    
    


def find_node(nodes, id):
    for n in nodes:
        if(n.id == id):
            return n
    return 0

class _ChattySocket(socket.socket):
    """A socket subclass that prints the raw data that is received and sent."""

    def __init__(self, sock):
        fd = dup(sock.fileno())
        super().__init__(sock.family, sock.type, sock.proto, fileno=fd)
        super().settimeout(sock.gettimeout())

    def recv(self, chunksize):
        data = super().recv(chunksize)
        return data

    def sendall(self, data):
        data = data.strip(b'\xc0')       
        super().sendall(data)
    
            
class SlipHandler(SlipRequestHandler):
    """A SlipRequestHandler that echoes the received message with the bytes in reversed order."""

    def setup(self):
        self.request = _ChattySocket(self.request)
        print("Incoming connection from {}".format(self.request.getpeername()))
        super().setup()
        
    def handle_voltage_request(self, message):
        int_match = re.search(rb'(\d+) ms', message)
        if(int_match):
            int_delay = int(int_match.group(1))
            int_time = node.capacitor.t_previous + int_delay/1000.0 - 60
            node.int_times.append(int_time)     # 45 seconds buffer 
            global count
            count = 0
        
    def handle_message(self, message):
        global count
        idle = False
        # Extract RX and TX in milliseconds
        asn_match = re.search(rb'asn ([0-9A-Fa-f]+\.[0-9A-Fa-f]+) link', message)
        rx_match = re.search(rb'RX (\d+) ms', message)
        tx_match = re.search(rb'TX (\d+) ms', message)
        idle_match = re.search(rb'(idle)', message)
        if idle_match:
            idle = True
        if asn_match and rx_match and tx_match:
            rx_time = int(rx_match.group(1))
            tx_time = int(tx_match.group(1))
            asn_hex = asn_match.group(1).replace(b'.', b'').decode('utf-8')  # Remove dot and decode bytes to string
            asn_decimal = int(asn_hex, 16)  # Convert hexadecimal string to integer                    
            e_missed = node.platform.calculate_ts_energy(tx_time, rx_time, idle)
            v_charge, v_timeslot = node.capacitor.update_voltage(asn_decimal/100,node.platform, e_missed, node.harv_seq[node.harv_i])
            # print(args.id,"Time:",asn_decimal/100,"V:",v_timeslot, node.harv_seq[node.harv_i]*1000000,"uW")
            if(node.id == 2 or node.id == 3):
                update_plot(asn_decimal/100, v_timeslot, amplitude_slider, node)
            # with open('router_harvesting_'+str(args.id)+'.csv', mode='a', newline='') as file:
            #     writer = csv.writer(file)
            #     writer.writerow([asn_decimal / 100, v_charge,node.harv_seq[node.harv_i]])
            #     writer.writerow([asn_decimal / 100 + 0.01, v_timeslot,node.harv_seq[node.harv_i]])
            if(v_timeslot < node.capacitor.v_min):
                return 1
            if((asn_decimal/100 - node.t_change_pharv) > node.harv_period):
                node.harv_i = (node.harv_i + 1) % len(node.harv_seq)
                node.t_change_pharv = asn_decimal/100
            if(len(node.int_times) > 0 and count < 5 and asn_decimal/100 > node.int_times[0]):
                node.platform.energy_update = 1
                self.request.send_msg((b"energy-update " + bytes(str(int(node.capacitor.V*1000)), 'utf-8') + b" " + bytes(str(int(node.harv_seq[node.harv_i]*100000)), 'utf-8') + b" " + bytes(str(int(asn_decimal)), 'utf-8') + b"\n"))  # Send voltage and harvested power
                count += 1
                if(count == 5):
                    node.int_times.pop(0)
                return 0
        return 0

    def handle(self):
        buffer = b''
        while True:
            data = self.request.recv_msg()
            if not data:
                break
            buffer += data
            while True:
                # Search INT message
                int_start_index = buffer.find(b'Scheduling INT')
                int_end_index = buffer.find(b'\n', int_start_index + 1)
                
                # Search TSCH log message
                tsch_start_index = buffer.find(b'INFO: TSCH-LOG')
                tsch_end_index = buffer.find(b'\n', tsch_start_index + 1)    
                
                 # Found an INT message
                if int_start_index != -1:
                    int_message = buffer[int_start_index:int_end_index]      
                
                # Found a TSCH LOG message
                if tsch_start_index != -1:
                    tsch_message = buffer[tsch_start_index:tsch_end_index]
                    
                # Handle INT message
                if int_start_index != -1:
                    self.handle_voltage_request(int_message)
                    buffer = buffer[int_end_index + 1:]
                    
                # Handle TSCH LOG message
                if tsch_start_index != -1:
                    if(self.handle_message(tsch_message)):
                        # t_charge = node.capacitor.charge_turnon(node.platform, node.harv_seq, node.harv_i, node.harv_period)
                        t_charge = node.capacitor.charge_turnon(node)
                        self.request.send_msg((b"tsch-shutdown " + bytes(str(int(t_charge)), 'utf-8') + b"\n"))
                        # with open('router_harvesting_'+str(args.id)+'.csv', mode='a', newline='') as file:
                        #     writer = csv.writer(file)
                        #     writer.writerow([0.0, 0.0, t_charge])
                        print("Shutting down, recharged in",t_charge,"s")
                        buffer = b''
                        node.platform.join = 1
                    else:
                        buffer = buffer[tsch_end_index + 1:]

                break  # Exit inner loop if end marker is not found

        print('Closing down')


class TCPServerIPv6(TCPServer):
    """An IPv6 TCPServer"""
    address_family = socket.AF_INET6
    allow_reuse_address = True
    
# Create a handler for the SIGINT signal (Ctrl+C)
def signal_handler(sig, frame):
    print("Ctrl+C pressed. Shutting down server.")
    server.server_close()  # This releases the socket and frees the port
    sys.exit(0)

if __name__ == '__main__':
    # Create ArgumentParser object
    parser = argparse.ArgumentParser(description="Set battery-less router ID")
    parser.add_argument("id", type=int, help="ID of battery-less router")
    args = parser.parse_args()
    node = find_node(config.bl_nodes, args.id)
    if(node == 0):
        print("Invalid ID!")
        sys.exit()
    else:
        PORT = 1200 + node.id
        count = 0
        node.capacitor.fully_charge()
        if(node.id == 2 or node.id == 3):
            # Set up the figure and axis
            plt.ion()  # Turn on interactive mode
            fig, ax = plt.subplots()
            plt.subplots_adjust(left=0.2, bottom=0.2, top=0.8)
            ax.set_title("Node " + str(node.id), color="orange", fontweight="bold")
            fig.canvas.manager.set_window_title("Supercapacitor simulation")
            x_data, y_data = [], []
            line, = ax.plot([], [], linewidth=3, zorder=2)
            # Set axis labels
            ax.set_xlabel("Time [s]")
            ax.set_ylabel("Capacitor voltage [V]")
            ax.set_ylim([1.7,4])
            ax.set_yticks([1.8,2.5,3,3.5,4])
            ax.set_yticklabels(["1.8 (Voff)","2.5 (Vth)",3,"3.5 (Von)",4])
            ax.axhline(y=1.8, color='r', linestyle='--', zorder=1)
            ax.axhline(y=2.5, color='r', linestyle='--', zorder=1)
            ax.axhline(y=3.5, color='r', linestyle='--', zorder=1)
            
            slider_ax = plt.axes([0.3, 0.9, 0.3, 0.05], facecolor='lightgoldenrodyellow')
            amplitude_slider = Slider(slider_ax, 'Pharv [uW]', 0.1, 1000, valinit=500)
            update_plot(0, node.capacitor.v_turnon, amplitude_slider, node)
        # Write the initial capacitor state
        # with open('router_harvesting_'+str(args.id)+'.csv', mode='w', newline='') as file:
        #     writer = csv.writer(file)
        #     writer.writerow([0, node.capacitor.v_max])
        # Set the signal handler for SIGINT
        signal.signal(signal.SIGINT, signal_handler)
        server = TCPServer(('localhost', PORT), SlipHandler)
        print('Slip server listening on localhost, port', PORT)
        server.handle_request()
    
# Keep the plot open
plt.ioff()  # Turn off interactive mode
plt.show()  # Final display

# # Simulate data update
# for i in range(100):
#     update_plot(i, np.sin(i / 10.0))  # Example data: sine wave
#     time.sleep(0.1)  # Simulate a delay between data points