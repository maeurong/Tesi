# Risultati Abaqus

MeshRec si ferma al deck `.inp`. L'analisi si esegue in Abaqus, a mano, e i suoi
risultati vanno depositati qui — accanto al deck che li ha prodotti, e non solo
nella tesi stampata.

La ragione è la stessa che regge il resto del progetto. Il registro degli
esperimenti lega già ogni corsa alla propria configurazione, alle impronte dei
suoi artefatti e al commit del codice. Se i risultati vivessero altrove, la
catena della provenienza si spezzerebbe proprio all'ultimo anello: quello che
interessa di più a chi legge.

## Come si deposita un'analisi

Una cartella per analisi, chiamata come la corsa MeshRec che ha prodotto il
deck. Dentro:

- il file `.inp` entrato in Abaqus, copiato dalla corsa;
- l'uscita dell'analisi — i file di risultato, oppure, se superano i 50 MB oltre
  i quali GitHub avvisa e i 100 MB oltre i quali rifiuta, le viste e le tabelle
  estratte da essi;
- un `nota.md` con il modello qui sotto.

## Modello di `nota.md`

```markdown
# <nome della corsa>

**Corsa MeshRec:** `runs/<nome>` — commit `<sha>` del codice che l'ha eseguita.
**Deck:** `<nome>.inp`, prodotto dallo step 11.

## Come è stata impostata l'analisi

- **Abaqus:** versione <...>
- **Tipo di analisi:** <...>
- **Elemento:** <C3D4 / C3D10>, <numero> elementi
- **Materiale:** <nome del materiale della corsa, con i valori usati>
- **Vincoli:** <node set vincolati, e come>
- **Carichi:** <quali, e con quale intensità>

Ogni impostazione che non viene dal deck va scritta qui: è la differenza fra
quello che il programma ha dichiarato e quello che ha effettivamente girato.

## Che cosa è uscito

<Le grandezze lette e i loro valori. Se un risultato ha richiesto di tornare
indietro a cambiare un parametro della pipeline, scrivere quale e perché: è la
parte che non si ricostruisce a distanza di mesi.>
```
