#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name


switch_table = {}
vlan_config_cp = {}

def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    # pe 12 b
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    # 2 octeti definesc eu valoarea
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def send_bdpu_every_sec():
    while True:
        # TODO Send BDPU every second if necessary
        time.sleep(1)


def read_vlan_config(switch_id):
    global vlan_config_cp
    try:
        filename = f"configs/switch{switch_id}.cfg"
        with open(filename, 'r') as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) == 2:
                    interface, mode = parts
                    if mode == 'T':
                        # daca interfata e tip trunk
                        vlan_config_cp[interface] = 'trunk'
                    else:
                        # daca interfata e tip access
                        vlan_config_cp[interface] = int(mode)  
    except IOError:
        print(f"Can't read the file {filename}")
    except ValueError:
        print(f"Invalid format: {filename}")

def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    # referinta la var globale
    global switch_table, vlan_config_cp

    # introduc datele din cfg in hashmapul vlan_config_cp 
    read_vlan_config(switch_id)
    
    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    print("# Starting switch with id {}".format(switch_id), flush=True)
    
    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec)
    t.start()

    # Printing interface names
    for i in interfaces:
        print(get_interface_name(i))
    
    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()
        
        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)

        # Print the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]

        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')

        print("Received frame of size {} on interface {}".format(length, interface), flush=True)
        
        # actualizare tabela de comutare cu adresa MAC sursa
        switch_table[src_mac] = (interface, vlan_id)
        
        # verifica daca adresa MAC este unicast (bitul cel mai putin semnificativ al primului octet este 0)
        def is_unicast(mac_address):
            if isinstance(mac_address, str):
            # mac in hexa : 'xx:xx:xx:xx:xx:xx'
                mac_address = bytes.fromhex(mac_address.replace(':', ''))
            return (mac_address[0] & 1) == 0

        # determin modul interfetei de pe care trimit (trunk/access)
        sending_interface = vlan_config_cp.get(get_interface_name(interface), 'access') 
        
        if sending_interface == 'trunk':
                # trunk
                pass
        else:
                # acces - elimina tagul vlan
            if vlan_id != -1 and ethertype == 0x8200:
                data = data[0:12] + data[16:]
                length -= 4  

        # verific tipul destinatiei si fac forwarding la pachet
        if is_unicast(dest_mac):
            if dest_mac in switch_table:
                current_interface, current_vlan_id = switch_table[dest_mac]
                current_mode = vlan_config_cp.get(get_interface_name(current_interface), 'access')
                # daca e trunk sau vlanul este acelasi 
                if current_mode == 'trunk' or current_vlan_id == vlan_id:
                    # adaug sau elimin tag-ul de vlan
                    if current_mode == 'trunk':
                        if vlan_id != -1 and ethertype != 0x8200:
                            data = data[0:12] + create_vlan_tag(vlan_id) + data[12:]
                    else:
                        if ethertype == 0x8200:
                            data = data[0:12] + data [16:]
                    send_to_link(current_interface, data, length)          
            else:
                # trimite cadru pe toate interfetele fara sursa
                for intf in interfaces:
                    if intf != interface:
                        next_interface = vlan_config_cp.get(get_interface_name(intf), 'access')
                        # verific daca e buna ruta
                        # daca se transmite pe trunk sau au acelasi vland_id
                        if next_interface == 'trunk' or vlan_id == next_interface:
                            # adaug tag vlan 
                            # verific daca vine de pe access si se duce in trunk
                            if next_interface == 'trunk' and str(sending_interface).isdigit():
                                modified_data = data[0:12] + create_vlan_tag(sending_interface) + data[12:]
                                send_to_link(intf, modified_data, length + 4)

                            elif sending_interface == 'trunk' and str(next_interface).isdigit():
                                # trimite fara tag VLANs
                                modified_data = data[0:12] + data[16:]
                                send_to_link(intf, modified_data, length - 4)

                            else:
                                send_to_link(intf, data, length)
        # pentru multicast/broadcast
        # logica similara
        else:
                for intf in interfaces:
                    if intf != interface:
                        next_interface = vlan_config_cp.get(get_interface_name(intf), 'access')
                        # verific daca e buna ruta
                        # daca se duce pe trunk sau au acelasi vlan_id
                        if next_interface == 'trunk' or vlan_id == next_interface:
                            # adaug tag vlan 
                            # verific daca vine de pe access si se duce in trunk
                            if next_interface == 'trunk' and str(sending_interface).isdigit():
                                modified_data = data[0:12] + create_vlan_tag(sending_interface) + data[12:]
                                send_to_link(intf, modified_data, length + 4)
                            elif sending_interface == 'trunk' and str(next_interface).isdigit():
                                # trimite fara tag vlan
                                modified_data = data[0:12] + data[16:]
                                send_to_link(intf, modified_data, length - 4)
                            else:
                                send_to_link(intf, data, length)
        
        # TODO: Implement STP support
if __name__ == "__main__":
    main()

