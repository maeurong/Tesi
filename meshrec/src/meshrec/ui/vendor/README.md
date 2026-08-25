# three.js vendorizzato

Versione **r180** (`three@0.180.0`), build minificate ufficiali.

| file | sha256 |
|---|---|
| `three.core.min.js` | `61ba0df005b05991361d040d8ff670e1aadfd0ce7aeebd1fdb0725957a8957de` |
| `three.module.min.js` | `e2b5ee6bccd38fd6d8a2428546b83c5f2426d84b152ef82be8055556e3b40eb6` |

Le stesse due impronte stanno in `tests/test_server.py` (`IMPRONTE_VENDOR`) e il
test le verifica sul contenuto che il server serve davvero. Sono state
confrontate con il tarball del registry npm, la cui `dist.integrity` è firmata
ECDSA dal registry stesso.

Per aggiornare la versione:

```
npm pack three@<versione>
tar -xzf three-<versione>.tgz
shasum -a 256 package/build/three.core.min.js package/build/three.module.min.js
```

Copia i due file da `package/build/`, riporta le impronte qui e in
`IMPRONTE_VENDOR`. Non serve né SRI (non si applica agli `import` ES) né un
`package.json`: la dipendenza è vendorizzata e non installata.
