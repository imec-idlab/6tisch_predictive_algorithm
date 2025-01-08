echo "Starting battery-less simulator"

coap_log="coap.log"
> "coap.log"

topology_log="topology.log"
> "topology.log"

# for I in {2..21}
for I in {2..3}
do
    gnome-terminal -- python3 serial_server.py $I
done

gnome-terminal -- python3 6tisch_predictor.py

make TARGET=cooja connect-router-cooja > topology.log