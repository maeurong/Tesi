# Fusione dei prismi fuori piombo: un solido o N (issue #188)

Risposta alla domanda della mappa #187 / ADR `docs/adr/2026-09-07-step-dal-prior-geometrico.md`
(ramo `docs/deck-nudo-adr`): `gmsh.model.occ.fuse` su due membrature che si toccano
su facce quasi complanari con 1-3 gradi di fuori piombo rende **un** solido o due?
Schegge? Con quale tolleranza torna un solido?

**Provenienza di ogni numero qui sotto**: cwd
`/Users/mario/GitHub/Tesi/.claude/worktrees/agent-a7f85cb4db85b5cfb`, ramo
`research/fusione-fuori-piombo` creato da `main` a `cb6ef7e`, comando

```
uv run --project meshrec python research/fusione-fuori-piombo/esperimento.py
```

gmsh 4.15.2 (quello di `meshrec/uv.lock`), OCCT 7.8.1 (da `General.BuildInfo`),
macOS 26.6.2 arm64, 07/09/2026. Lo script e' `esperimento.py` in questa cartella:
stampa la tabella qui sotto, tale e quale.

## Risposta netta

1. **Un solido, senza toccare alcuna tolleranza.** Pilastro con 1, 2 e 3 gradi
   di fuori piombo sotto trave orizzontale (testa centrata sull'intradosso: meta'
   compenetra a cuneo, meta' resta sotto): `fuse` con opzioni predefinite rende
   1 solido, volume contro l'analitico con scarto relativo fra 1.6e-15 e 4.1e-14,
   in 1.8-1.9 ms. Nessuna scheggia: faccia piu' piccola 4.5e4 mm2 (mezza testa,
   150 x 300), spigolo piu' corto 150 mm. STEP scritto e riletto con
   `importShapes`: stesso numero di solidi, stesso `getMass` (rel 1e-9).
2. **La fusione e' geometrica, non "a tolleranza"**: fonde dove i solidi si
   compenetrano o condividono una faccia (contatto perfetto, compenetrazione 3 mm,
   cuneo del fuori piombo). Dove si toccano **solo su uno spigolo** (caso 2t:
   spigolo alto della testa inclinata esattamente sull'intradosso) restano 2
   solidi; con un **gioco** anche di 0.05 mm restano 2 solidi.
3. **L'unico parametro che chiude un gioco e' `Geometry.ToleranceBoolean`**
   (`SetFuzzyValue` di OCCT, `GModelIO_OCC.cpp:3795-3796` a 4.15.2). Con 0.1 mm
   un gioco di 0.05 mm si fonde (1 solido, volume +3.45e-6 rel), con 1.0 mm si
   fonde anche 0.5 mm (+3.45e-5 rel). Sopra il gioco ma sotto lo spessore va
   bene; a **400 mm** (piu' dello spessore 300) il risultato e' rotto: 2 solidi,
   volume -29%, e il STEP riletto ha un volume diverso da quello in memoria
   (6.332e8 contro 6.16e8). Questo e' il tetto del parametro.
4. **Tutto il resto non fa nulla o fa danno**:
   - `Geometry.Tolerance` (0.1, 1.0, perfino 400): identico al default in ogni
     caso. Dal sorgente non entra nei booleani: serve a `addPoint`/facce/
     `healShapes` (`GModelIO_OCC.cpp:176, 1953, 2189, 4887`).
   - `Geometry.OCCFixDegenerated/SmallEdges/SmallFaces`: identico al default.
     Agiscono solo all'**import** (`GModelIO_OCC.cpp:4886-4891`; help
     `DefaultOptions.h:1000-1008` dice "when importing STEP, IGES and BRep").
   - `removeAllDuplicates` e `fragment` prima di `fuse`: stesso risultato del
     `fuse` nudo, stesso conteggio di entita'. `removeAllDuplicates` e' un
     `fragment` di tutte le entita' di dimensione massima
     (`GModelIO_OCC.cpp:4246-4253`); non chiude giochi.
   - `healShapes()` prima di `fuse`: innocuo nei casi normali, **distruttivo**
     sui prismi identici sovrapposti: `sewFaces`+`makeSolids` cuce le due
     scorze in un "solido" a volume 0 (12 facce, 24 spigoli, scarto -1.00).
     Non va messo nel percorso.

## Ingressi degeneri (promesse dell'ADR)

- Prismi disgiunti (10 mm): `fuse` rende **2 solidi, nessuna eccezione**, in
  tutte le varianti. Confermata la promessa dell'ADR ("Prismi che non si
  toccano restano solidi distinti").
- Prismi identici sovrapposti: 1 solido, volume di uno solo (270e6, scarto 0),
  6 facce 12 spigoli. Con `removeAllDuplicates`/`fragment` il `fuse` non serve
  nemmeno (il frammento li ha gia' unificati).
- Tolleranza sopra lo spessore minimo: `ToleranceBoolean=400` rompe il solido
  (sopra). `Tolerance=400` non cambia nulla.

## Raccomandazione (non decisione)

- **Costante, non parametro di `ModelConfig`**: `fuse` con opzioni predefinite.
  Il fuori piombo non e' un problema di tolleranza; i prismi che il prior
  misura o si compenetrano (e si fondono) o non si toccano (e restano N).
- Se si vuole chiudere i giochi sotto la risoluzione dello scanner, l'unica
  leva utile e' `Geometry.ToleranceBoolean`, e va tenuta **sotto lo spessore
  minimo** delle membrature. Un valore sensato per uno scanner da qualche
  decimo di mm e' **1.0 mm**: fonde giochi <= 0.5 mm con scarto di volume
  3.5e-5. Ma e' una scelta di prodotto: il gioco e' un'informazione del
  rilievo (`MembratureNonLegateWarning`, `hexa.py:735`), e la metrica
  `solidi > 1` dell'ADR la dichiara gia'. Consiglio: **partire senza**, e
  aggiungere `ToleranceBoolean` come parametro solo se un caso reale mostra
  giochi sotto il mm che devono fondersi.
- **Cosa correggere nell'ADR**: il ticket cita `Geometry.Tolerance`,
  `removeAllDuplicates` e `fragment` come leve; nessuna delle tre tocca il
  `fuse`. L'unica leva e' `Geometry.ToleranceBoolean`. Da non usare
  `healShapes` sull'intero modello prima del `fuse`.

## Cosa non copre questo esperimento

- Sezioni rettangolari a 4 vertici. Il prior porta contorni misurati a K
  vertici, non testati qui; la geometria resta piana e prismatica, ma con K
  grande le facce laterali sono strette e il cuneo del fuori piombo produce
  facce piu' piccole di 4.5e4 mm2.
- Solo 2 membrature per `fuse`. Un telaio ne ha decine: `fuse(obj, tools)` in
  una chiamata sola e' la forma dello spike (3 box), ma il tempo a N solidi non
  e' misurato.
- Gioco combinato con fuori piombo (testa inclinata che non tocca): stesso
  meccanismo del caso G, non ripetuto.

## Tabella caso x variante

`solidi (attesi)`: `!!` dove il conteggio differisce dall'attesa geometrica
(per i giochi l'attesa e' 2: la fusione a tolleranza e' la deviazione cercata).
`scarto vol. rel.` = (volume fuso - analitico) / analitico. `riletto` `=` se il
STEP riletto con `importShapes` ha stesso numero di solidi e stesso volume
(rel 1e-9). `fuse ms` sul solo `occ.fuse` (la prima riga paga il warm-up).

gmsh 4.15.2, step in /var/folders/2t/qtg_pmb11f33dhg53xjlmx580000gn/T/fuse188-uaiz39vo
| caso | variante | solidi (attesi) | scarto vol. rel. | facce | spigoli | faccia min mm2 | spigolo min mm | fuse ms | riletto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 contatto | default | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 21.0 | = |
| 1 contatto | Tolerance=0.1 | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.3 | = |
| 1 contatto | Tolerance=1.0 | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.2 | = |
| 1 contatto | ToleranceBoolean=0.1 | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.2 | = |
| 1 contatto | ToleranceBoolean=1.0 | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.2 | = |
| 1 contatto | removeAllDuplicates | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.0 | = |
| 1 contatto | fragment poi fuse | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.0 | = |
| 1 contatto | OCCFix*=1 | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.5 | = |
| 1 contatto | healShapes | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.2 | = |
| 2 piombo 1 deg | default | 1 (1) | -4.07e-14 | 11 | 27 | 4.5e+04 | 150 | 1.9 | = |
| 2 piombo 1 deg | Tolerance=0.1 | 1 (1) | -4.07e-14 | 11 | 27 | 4.5e+04 | 150 | 1.9 | = |
| 2 piombo 1 deg | Tolerance=1.0 | 1 (1) | -4.07e-14 | 11 | 27 | 4.5e+04 | 150 | 1.8 | = |
| 2 piombo 1 deg | ToleranceBoolean=0.1 | 1 (1) | -4.07e-14 | 11 | 27 | 4.5e+04 | 150 | 2.2 | = |
| 2 piombo 1 deg | ToleranceBoolean=1.0 | 1 (1) | -4.07e-14 | 11 | 27 | 4.5e+04 | 150 | 1.8 | = |
| 2 piombo 1 deg | removeAllDuplicates | 1 (1) | -4.07e-14 | 11 | 27 | 4.5e+04 | 150 | 1.4 | = |
| 2 piombo 1 deg | fragment poi fuse | 1 (1) | -4.07e-14 | 11 | 27 | 4.5e+04 | 150 | 1.4 | = |
| 2 piombo 1 deg | OCCFix*=1 | 1 (1) | -4.07e-14 | 11 | 27 | 4.5e+04 | 150 | 1.8 | = |
| 2 piombo 1 deg | healShapes | 1 (1) | -4.04e-14 | 11 | 27 | 4.5e+04 | 150 | 1.9 | = |
| 2 piombo 2 deg | default | 1 (1) | +6.58e-15 | 11 | 27 | 4.5e+04 | 150 | 1.9 | = |
| 2 piombo 2 deg | Tolerance=0.1 | 1 (1) | +6.58e-15 | 11 | 27 | 4.5e+04 | 150 | 1.8 | = |
| 2 piombo 2 deg | Tolerance=1.0 | 1 (1) | +6.58e-15 | 11 | 27 | 4.5e+04 | 150 | 1.8 | = |
| 2 piombo 2 deg | ToleranceBoolean=0.1 | 1 (1) | +6.58e-15 | 11 | 27 | 4.5e+04 | 150 | 1.8 | = |
| 2 piombo 2 deg | ToleranceBoolean=1.0 | 1 (1) | +6.58e-15 | 11 | 27 | 4.5e+04 | 150 | 1.8 | = |
| 2 piombo 2 deg | removeAllDuplicates | 1 (1) | +6.58e-15 | 11 | 27 | 4.5e+04 | 150 | 1.4 | = |
| 2 piombo 2 deg | fragment poi fuse | 1 (1) | +6.58e-15 | 11 | 27 | 4.5e+04 | 150 | 1.4 | = |
| 2 piombo 2 deg | OCCFix*=1 | 1 (1) | +6.58e-15 | 11 | 27 | 4.5e+04 | 150 | 1.8 | = |
| 2 piombo 2 deg | healShapes | 1 (1) | +6.58e-15 | 11 | 27 | 4.5e+04 | 150 | 1.9 | = |
| 2 piombo 3 deg | default | 1 (1) | +1.64e-15 | 11 | 27 | 4.5e+04 | 150 | 1.8 | = |
| 2 piombo 3 deg | Tolerance=0.1 | 1 (1) | +1.64e-15 | 11 | 27 | 4.5e+04 | 150 | 1.8 | = |
| 2 piombo 3 deg | Tolerance=1.0 | 1 (1) | +1.64e-15 | 11 | 27 | 4.5e+04 | 150 | 1.9 | = |
| 2 piombo 3 deg | ToleranceBoolean=0.1 | 1 (1) | +1.64e-15 | 11 | 27 | 4.5e+04 | 150 | 1.8 | = |
| 2 piombo 3 deg | ToleranceBoolean=1.0 | 1 (1) | +1.64e-15 | 11 | 27 | 4.5e+04 | 150 | 1.8 | = |
| 2 piombo 3 deg | removeAllDuplicates | 1 (1) | +1.64e-15 | 11 | 27 | 4.5e+04 | 150 | 1.4 | = |
| 2 piombo 3 deg | fragment poi fuse | 1 (1) | +1.64e-15 | 11 | 27 | 4.5e+04 | 150 | 1.4 | = |
| 2 piombo 3 deg | OCCFix*=1 | 1 (1) | +1.64e-15 | 11 | 27 | 4.5e+04 | 150 | 1.8 | = |
| 2 piombo 3 deg | healShapes | 1 (1) | +1.64e-15 | 11 | 27 | 4.5e+04 | 150 | 1.9 | = |
| 2t tangente 2 deg | default | 2 (2) | +0.00e+00 | 13 | 26 | 9e+04 | 300 | 1.0 | = |
| 2t tangente 2 deg | Tolerance=0.1 | 2 (2) | +0.00e+00 | 13 | 26 | 9e+04 | 300 | 1.0 | = |
| 2t tangente 2 deg | Tolerance=1.0 | 2 (2) | +0.00e+00 | 13 | 26 | 9e+04 | 300 | 1.0 | = |
| 2t tangente 2 deg | ToleranceBoolean=0.1 | 2 (2) | +0.00e+00 | 13 | 26 | 9e+04 | 300 | 0.9 | = |
| 2t tangente 2 deg | ToleranceBoolean=1.0 | 2 (2) | +0.00e+00 | 13 | 26 | 9e+04 | 300 | 0.9 | = |
| 2t tangente 2 deg | removeAllDuplicates | 2 (2) | +0.00e+00 | 13 | 26 | 9e+04 | 300 | 0.7 | = |
| 2t tangente 2 deg | fragment poi fuse | 2 (2) | +0.00e+00 | 13 | 26 | 9e+04 | 300 | 0.7 | = |
| 2t tangente 2 deg | OCCFix*=1 | 2 (2) | +0.00e+00 | 13 | 26 | 9e+04 | 300 | 0.9 | = |
| 2t tangente 2 deg | healShapes | 2 (2) | +0.00e+00 | 13 | 26 | 9e+04 | 300 | 0.9 | = |
| 3 compenetra 3 mm | default | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.8 | = |
| 3 compenetra 3 mm | Tolerance=0.1 | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.9 | = |
| 3 compenetra 3 mm | Tolerance=1.0 | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.8 | = |
| 3 compenetra 3 mm | ToleranceBoolean=0.1 | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.8 | = |
| 3 compenetra 3 mm | ToleranceBoolean=1.0 | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.8 | = |
| 3 compenetra 3 mm | removeAllDuplicates | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.4 | = |
| 3 compenetra 3 mm | fragment poi fuse | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.4 | = |
| 3 compenetra 3 mm | OCCFix*=1 | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.8 | = |
| 3 compenetra 3 mm | healShapes | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.9 | = |
| G gioco 0.05 mm | default | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.05 mm | Tolerance=0.1 | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.05 mm | Tolerance=1.0 | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.05 mm | ToleranceBoolean=0.1 | 1 (2) !! | +3.45e-06 | 10 | 24 | 9e+04 | 300 | 1.1 | = |
| G gioco 0.05 mm | ToleranceBoolean=1.0 | 1 (2) !! | +3.45e-06 | 10 | 24 | 9e+04 | 300 | 1.1 | = |
| G gioco 0.05 mm | removeAllDuplicates | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.05 mm | fragment poi fuse | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.05 mm | OCCFix*=1 | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.05 mm | healShapes | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.5 mm | default | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.5 mm | Tolerance=0.1 | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.5 mm | Tolerance=1.0 | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.5 mm | ToleranceBoolean=0.1 | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.5 mm | ToleranceBoolean=1.0 | 1 (2) !! | +3.45e-05 | 10 | 24 | 9e+04 | 300 | 1.2 | = |
| G gioco 0.5 mm | removeAllDuplicates | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.5 mm | fragment poi fuse | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.5 mm | OCCFix*=1 | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| G gioco 0.5 mm | healShapes | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| D disgiunti 10 mm | default | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| D disgiunti 10 mm | Tolerance=0.1 | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| D disgiunti 10 mm | Tolerance=1.0 | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| D disgiunti 10 mm | ToleranceBoolean=0.1 | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| D disgiunti 10 mm | ToleranceBoolean=1.0 | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| D disgiunti 10 mm | removeAllDuplicates | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| D disgiunti 10 mm | fragment poi fuse | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| D disgiunti 10 mm | OCCFix*=1 | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| D disgiunti 10 mm | healShapes | 2 (2) | +0.00e+00 | 12 | 24 | 9e+04 | 300 | 0.6 | = |
| D identici | default | 1 (1) | +0.00e+00 | 6 | 12 | 9e+04 | 300 | 1.0 | = |
| D identici | Tolerance=0.1 | 1 (1) | +0.00e+00 | 6 | 12 | 9e+04 | 300 | 1.0 | = |
| D identici | Tolerance=1.0 | 1 (1) | +0.00e+00 | 6 | 12 | 9e+04 | 300 | 1.0 | = |
| D identici | ToleranceBoolean=0.1 | 1 (1) | +0.00e+00 | 6 | 12 | 9e+04 | 300 | 1.0 | = |
| D identici | ToleranceBoolean=1.0 | 1 (1) | +0.00e+00 | 6 | 12 | 9e+04 | 300 | 1.0 | = |
| D identici | removeAllDuplicates | 1 (1) | +0.00e+00 | 6 | 12 | 9e+04 | 300 | 0.0 | = |
| D identici | fragment poi fuse | 1 (1) | +0.00e+00 | 6 | 12 | 9e+04 | 300 | 0.0 | = |
| D identici | OCCFix*=1 | 1 (1) | +0.00e+00 | 6 | 12 | 9e+04 | 300 | 1.0 | = |
| D identici | healShapes | 1 (1) | -1.00e+00 | 12 | 24 | 9e+04 | 300 | 0.0 | = |
| 1 contatto | ToleranceBoolean=400 | 2 (1) !! | -2.92e-01 | 10 | 16 | 9e+04 | 300 | 3.3 | 2 solidi, 6.332206e+08 |
| 1 contatto | Tolerance=400 | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.1 | = |
| 3 compenetra 3 mm | ToleranceBoolean=400 | 2 (1) !! | -2.92e-01 | 10 | 16 | 9e+04 | 300 | 2.7 | 2 solidi, 6.332708e+08 |
| 3 compenetra 3 mm | Tolerance=400 | 1 (1) | +0.00e+00 | 10 | 24 | 9e+04 | 300 | 1.9 | = |
