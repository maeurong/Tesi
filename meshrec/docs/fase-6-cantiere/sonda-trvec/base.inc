** Deck di sonda sintetico. Un solo C3D4, geometria unitaria, nessun numero
** del provino di laboratorio.
** Nodi: 1=(0,0,0) 2=(1,0,0) 3=(0,1,0) 4=(0,0,1)
** Faccia 2 = nodi 1-4-2, piano y=0, area esatta 0.5, normale uscente -y
** Faccia 4 = nodi 3-4-1, piano x=0, area esatta 0.5, normale uscente -x
*NODE, NSET=NALL
1, 0.0, 0.0, 0.0
2, 1.0, 0.0, 0.0
3, 0.0, 1.0, 0.0
4, 0.0, 0.0, 1.0
*ELEMENT, TYPE=C3D4, ELSET=EALL
1, 1, 2, 3, 4
*NSET, NSET=FISSI
1, 2, 3
*SURFACE, NAME=SFACCIA2, TYPE=ELEMENT
1, S2
*SURFACE, NAME=SFACCIA4, TYPE=ELEMENT
1, S4
*MATERIAL, NAME=ACCIAIO
*ELASTIC
210000.0, 0.3
*SOLID SECTION, ELSET=EALL, MATERIAL=ACCIAIO
