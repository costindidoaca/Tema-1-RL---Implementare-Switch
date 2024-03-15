1 2
## Costin Didoaca ##
## 333CA ##

Tema 1 RL
Implementare Switch

    In aceasta tema am abordat doua din cele trei subiecte de rezolvat
anume Procesul de Comutare si functionalitatea cu VLAN-uri impreuna.
Am creat doua hashmap-uri(dictionare): switch_table care reprezinta tabela 
CAM a unui switch avand perechi cheie-valoare formate din interfata curenta 
si vlan id-ul specific acesteia; vland_config_cp format din perechi de 
interfete cu tipul lor specificat, access daca este un integer si trunk,
daca este de tipul T.Popularea dictionarului vlan_config a fost facuta 
folosind functia read_vlan_config care detecteaza tipul fiecarei interfete 
si o stocheaza in dictionar.
    In bucla principala din main am implementat functionalitatea propriu
-zisa urmarind tipurile de interfete de pe care intra pachetul in switch
dar si pe care pleaca. Am creat mai intai o functie is_unicast pentru a 
putea urmari modul de transmitere a pachetelor in functie de adresa MAC,
bitul cel mai putin semnificativ al primului octet fiind 0. Am inceput
sa fac forwarding la pachet urmand mai intai cazul de unicast cu verificari
necesare:
- daca macul destinatie se afla in tabela cam atunci fac forward spre acea
adresa direct
- interfata de tip trunk adaug tagul de vlan, daca nu, il elimin
- daca nu il cunoastem, facem flood si trimitem cadrul pe toate interfetele 
fara sursa
    In functie de tipul interfetei pecare a fost transmis pachetul si cea
pe care putem transmite din switch, adaug sau scot tagul respectiv conform
indicatiilor din cerinta. 
    Pentru logica de multicast/broadcast am aplicat aceeasi functionalitate 
ca la cea de unicast pentru flood.

Feedback: 

    Nu am reusit sa implementez pana la capat STP-ul deoarece aveam erori
cu apelarea functiei ioctl() folosita pentru a extrage switch_mac ul si 
numele interfetei. Am facut mult research pentru a solutiona problema, dar 
in zadar. Un workaround nu am gasit decat prin hardcodare, ceea ce nu ar 
fi permis.
