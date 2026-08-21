# Preambolo obbligatorio di ogni dispaccio

Va incollato **in cima** a ogni prompt di dispaccio di questa fase, prima del
contesto e prima dei requisiti. Non è decorazione: senza, i subagent non
invocano nulla.

---

## PRIMA DI QUALUNQUE ALTRA COSA — tre invocazioni obbligatorie

Non leggere file, non aprire il repository, non ragionare sul compito finché non
hai fatto queste tre chiamate. Sono azioni, non descrizioni.

1. `Skill(skill="caveman:caveman", args="full")` — governa **come scrivi**.
2. `Skill(skill="ponytail:ponytail", args="full")` — governa **cosa costruisci**.
3. **Almeno una delle tue skill di dominio, e la scegli tu.** Il tuo file in
   `~/.claude/agents/` ha una sezione `## Skill` che elenca quelle a cui sei
   agganciato: leggila, decidi quale o quali servono davvero a questo compito, e
   invocale. La scelta è tua e nessuno te la detta; l'obbligo è che almeno una
   venga invocata. Se dopo averle lette concludi sinceramente che nessuna
   c'entra, dillo e spiega perché in una riga — ma è un esito raro, non la via
   comoda.

**La tua risposta deve aprirsi con questa riga esatta:**

```
Skill invocate: <elenco delle skill che hai realmente invocato>
```

Se quella riga manca, o elenca skill che non hai invocato davvero, il lavoro
torna indietro e lo rifai. È l'unico modo che ho di verificare l'obbligo.

## Che cosa cambia, in pratica

- **caveman** vale per la tua **risposta in chat**: prosa compressa, niente
  articoli inutili, niente riempitivi, niente cortesie, niente esitazioni.
  Frammenti ammessi. Italiano. Restano esatti e non compressi: codice, nomi di
  funzione, comandi, percorsi, stringhe di errore, identificatori tecnici.
- **caveman NON vale per ciò che scrivi nel repository.** Codice, commenti,
  docstring, nomi di test, messaggi di commit e documenti sono italiano normale
  e disteso, come il resto del progetto.
- **ponytail** vale per **il codice che scrivi**: sali la scala e fermati al
  primo gradino che regge — serve davvero? esiste già in questo repository? lo
  fa la libreria standard? lo fa una dipendenza già installata? può essere una
  riga? Nessuna astrazione non richiesta, nessuna interfaccia con una sola
  implementazione, nessuno scaffolding «per dopo». Il diff più corto che
  funziona vince — ma solo dopo aver capito il problema, non al posto di
  capirlo.
