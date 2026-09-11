# Crea «MeshRec» nel menu Start dell'utente, con l'icona, verso MeshRec.bat.
# Si lancia una volta, con il tasto destro > Esegui con PowerShell. Rilanciato,
# sovrascrive il collegamento.
$cartella = Split-Path -Parent $MyInvocation.MyCommand.Path
$shell = New-Object -ComObject WScript.Shell
$destinazione = Join-Path ([Environment]::GetFolderPath('Programs')) 'MeshRec.lnk'
$collegamento = $shell.CreateShortcut($destinazione)
$collegamento.TargetPath = Join-Path $cartella 'MeshRec.bat'
$collegamento.WorkingDirectory = $cartella
$collegamento.IconLocation = Join-Path $cartella 'src\meshrec\ui\icona.ico'
$collegamento.Description = 'MeshRec: dal rilievo fotogrammetrico al modello FEM'
$collegamento.Save()
Write-Host "Collegamento creato: $destinazione"
