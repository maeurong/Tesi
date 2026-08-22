# `ccx` distingue le maiuscole nei nomi di `*NSET`?

**No.** Misurato il 22 agosto 2026 con `ccx` 2.22 su questa macchina arm64.

## Perché la domanda

Il validatore della Fase 6 rifiuta un selettore che porti il nome di uno dei sei
insiemi che `abaqus.build_node_sets` fabbrica da sé (`BASE`, `TOP`,
`FACE_FRONT`, `FACE_BACK`, `SIDE_LEFT`, `SIDE_RIGHT`). Il confronto in pydantic
è fra stringhe esatte. Se il solutore trattasse i nomi senza distinzione di
caso, un selettore chiamato `base` passerebbe il validatore e nel deck
collidere­bbe comunque con `BASE` — cioè esattamente il difetto che il
messaggio d'errore promette di prevenire, ma silenzioso.

## La sonda

`sonda.inp` è un tetraedro C3D4 solo. Dichiara due insiemi:

```
*NSET, NSET=BASSO
1, 2, 3
*NSET, NSET=alto
4
```

`alto` è **minuscolo**. Il carico lo cita **maiuscolo**:

```
*CLOAD
ALTO, 3, -100.0
```

Se i nomi fossero case-sensitive, `ALTO` non esisterebbe e il carico non
troverebbe nulla.

## Come si rifà

```
cd docs/fase-6-cantiere/sonda-caso-nomi
ccx -i sonda
```

## Cosa esce

Uscita 0, `Job finished`, zero occorrenze di `warning` o `error` nel `.dat`.
E soprattutto, in `sonda.dat`, le reazioni sull'insieme vincolato:

```
 forces (fx,fy,fz) for set BASSO and time  0.1000000E+01

         1  4.285714E+01  4.285714E+01  1.000000E+02
         2 -4.285714E+01  0.000000E+00  0.000000E+00
         3  0.000000E+00 -4.285714E+01  0.000000E+00
```

La somma delle `fz` vale **+100,0 N**, che bilancia esattamente i −100 N
dichiarati. Il carico è stato applicato: `ccx` ha risolto `ALTO` contro
l'insieme dichiarato `alto`.

Non basta guardare il codice d'uscita. Un `*CLOAD` su un insieme inesistente in
altre condizioni può passare senza fermare il conto; la reazione che chiude è la
prova che il carico è arrivato ai nodi, non che il file è stato letto.

## Conseguenza

Il confronto anti-collisione normalizza il caso su entrambi i lati, e rifiuta
anche due selettori che differiscano solo per maiuscole: nel deck sono lo stesso
nome.
