** Cubo unitario sintetico, 6 C3D4. Nessun numero del provino.
** Faccia z=0 vincolata (nodi 1-4), faccia z=1 caricata (nodi 5-8).
** Area esatta di ciascuna delle due superfici: 1.0
*NODE, NSET=NALL
1, 0., 0., 0.
2, 1., 0., 0.
3, 1., 1., 0.
4, 0., 1., 0.
5, 0., 0., 1.
6, 1., 0., 1.
7, 1., 1., 1.
8, 0., 1., 1.
*ELEMENT, TYPE=C3D4, ELSET=EALL
1, 1, 2, 3, 7
2, 1, 3, 4, 7
3, 1, 4, 8, 7
4, 1, 8, 5, 7
5, 1, 5, 6, 7
6, 1, 6, 2, 7
*NSET, NSET=FISSI
1, 2, 3, 4
*NSET, NSET=LIBERI
5, 6, 7, 8
*SURFACE, NAME=SOPRA, TYPE=ELEMENT
4, S3
5, S3
*SURFACE, NAME=LATO, TYPE=ELEMENT
5, S1
6, S1
*MATERIAL, NAME=ACCIAIO
*ELASTIC
210000.0, 0.3
*SOLID SECTION, ELSET=EALL, MATERIAL=ACCIAIO
