# Prova della finestra su Windows 11

Da fare sul PC Windows dell'autore, prima di fondere `feat/finestra`.

## Comandi

    cd meshrec
    uv sync
    uv run meshrec serve

## Da guardare, uno alla volta

- [x] Si apre una finestra con titolo «MeshRec» (non una scheda di Edge). — provato da Mario
- [ ] Il viewport 3D di uno step con geometria si vede e ruota. — non ancora provato
- [x] «Sfoglia…» porta il selettore file in primo piano, sopra la finestra. — provato da Mario
- [ ] «Sfoglia» apre un dialogo spostabile e intero (su macOS era uno sheet
      tagliato sul bordo: corretto in `2e4c721`). — non ancora provato
- [x] «Salva immagine» scrive in `runs\<corsa>\immagini\` e la riga di esito dice il percorso. — provato da Mario
- [ ] «come citare» nel piè di pagina: si apre nel browser di sistema? (sì/no) — non ancora provato
- [ ] Chiudere la finestra: il prompt torna, `netstat -ano | findstr :8765` è vuoto. — non ancora provato
- [ ] `uv run meshrec serve --browser`: scheda nel browser, Ctrl-C ferma. — non ancora provato
- [ ] Se possibile, senza WebView2 (o rinominando temporaneamente la chiave di registro
      `HKCU\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`):
      stderr dice «il runtime WebView2 manca» e si apre Edge in modalità app. — non ancora provato
- [ ] `crea-collegamento.ps1` (tasto destro › Esegui con PowerShell): «MeshRec» nel menu Start con l'icona. — non ancora provato

## Esito

Data: 11/09/2026  Windows: 11  WebView2: __________

Note: finestra, «Sfoglia» e «Salva immagine» provati da Mario su questo branch,
tutti e tre ok. Le altre voci restano da provare prima di fondere.
