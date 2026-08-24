@echo off
rem Avvio col doppio clic da Esplora risorse (Windows).
rem
rem Come il gemello MeshRec.command: nessun argomento, si sposta nella propria
rem cartella (i percorsi relativi del programma -- run.out_dir, runs\,
rem experiments\, .cache\viewport -- sono risolti da li') e tiene aperta la
rem finestra sugli errori. `meshrec serve` senza configurazione apre la
rem schermata d'ingresso, che e' la strada del doppio clic: chi riceve una
rem scansione non ha uno yaml da scegliere.
cd /d "%~dp0"

rem >nul e non >/dev/null: quest'ultima e' sintassi Unix, e cmd.exe la legge
rem come il percorso .\dev\null. La cartella non esiste, la redirezione
rem fallisce e imposta errorlevel 1, quindi il controllo qui sotto scattava
rem sempre e il launcher dichiarava uv assente anche quando c'era.
where uv >nul 2>nul
if errorlevel 1 goto senza_uv

rem %* resta: da riga di comando `MeshRec.bat casi\lab_telaio.yaml` apre quel
rem caso direttamente. E' il doppio clic a non passare nulla.
uv run meshrec serve %*
if errorlevel 1 pause
exit /b

:senza_uv
echo uv non trovato.
echo Installalo da https://docs.astral.sh/uv/ e riprova.
pause
exit /b 1
