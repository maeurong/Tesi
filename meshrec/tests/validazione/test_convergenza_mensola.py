"""La GCI verificata dove la risposta si conosce (#71).

Una stima d'errore va provata su un caso a soluzione nota **prima** di
puntarla su un caso dove la soluzione non c'e'. La mensola ha la freccia di
Gere-Timoshenko in forma chiusa e tre maglie gia' misurate in #47, quindi e'
il banco giusto.

Il risultato che questo file fissa non e' «la GCI funziona»: e' **che cosa la
GCI misura**, che non e' quello che si crede a prima vista.

Misurato qui, `ccx` 2.22 su macOS arm64, passi 10 / 14 / 20 mm:

| | C3D4 | C3D10 |
|---|---|---|
| ordine osservato | 1,17 (formale 2) | 5,89 (formale 3) |
| GCI sulla griglia fine | 23,67 % | **0,0015 %** |
| distanza dall'estrapolato | 18,94 % | 0,00116 % |
| errore vero contro Timoshenko | 9,31 % | **0,279 %** |

Su C3D4 la banda contiene l'errore vero, e verrebbe da concludere che la GCI
sia una barra d'errore verso la verita'. **Su C3D10 no**: la GCI dice
0,0015 % e la distanza da Timoshenko e' 0,279 %, **186 volte piu' grande**.

Non e' un fallimento della stima: e' che le due grandezze sono diverse. La
GCI misura la distanza dalla soluzione **a maglio convergente**, e su C3D10
quella distanza vale davvero 0,00116 %, dentro la banda. Il residuo dello
0,279 % non e' discretizzazione: e' **errore di modello**, la teoria di trave
contro l'elasticita' tridimensionale. #47 lo aveva gia' visto dall'altro
lato, trovando il C3D10 **fra** Eulero-Bernoulli e Timoshenko, cioe' dove la
soluzione esatta del solido deve stare.

Confondere le due sarebbe esattamente la confusione fra verification e
validation che `docs/validazione/README.md` vieta.
"""

from __future__ import annotations

import numpy as np
import pytest
import test_mensola as M

from meshrec.core import convergenza

pytestmark = pytest.mark.validazione

# Dalla griglia piu' fine alla piu' grossolana: r21 = 1,4 e r32 = 1,4286,
# entrambi sopra il rapporto minimo di 1,3 che il modulo pretende.
PASSI = (10.0, 14.0, 20.0)
FATTORE = 1.25  # gci_fattore_sicurezza, core/soglie.py
ORDINE_FORMALE = {"C3D4": 2.0, "C3D10": 3.0}


def _frecce(tmp_path, order: int, tipo: str) -> list[float]:
    M._ccx_o_salta()
    frecce = []
    for passo in PASSI:
        cartella = tmp_path / f"{tipo}_{passo:g}"
        cartella.mkdir()
        nodi, tets = M._maglio(order, passo=passo)
        estremo = M._insiemi(nodi)["ESTREMO"]
        quota = -M.CARICO / len(estremo)
        M._corri(cartella, nodi, tets, tipo,
                 carichi_nodali={int(i): (0.0, 0.0, quota) for i in estremo})
        sp = M.read_dat_displacements(cartella / "mensola.dat")
        frecce.append(abs(float(np.mean([sp[int(i) + 1][2] for i in estremo]))))
    return frecce


@pytest.mark.parametrize("order,tipo", [(1, "C3D4"), (2, "C3D10")], ids=["C3D4", "C3D10"])
def test_la_gci_racchiude_la_distanza_dal_maglio_convergente(tmp_path, order, tipo):
    """Su **entrambi** gli elementi, e senza eccezioni: e' cio' che la GCI
    stima, e se non lo racchiudesse la macchina sarebbe rotta.

    La freccia converge in modo monotono su entrambi, quindi qui la formula
    ha le proprie ipotesi -- che e' precisamente cio' che su LE10 non
    accadrebbe.
    """
    frecce = _frecce(tmp_path, order, tipo)
    esito = convergenza.stima(tuple(frecce), PASSI, fattore=FATTORE,
                              ordine_formale=ORDINE_FORMALE[tipo])

    assert esito["esito"] == "asintotico", esito["spiegazione"]
    distanza = abs(frecce[0] - esito["estrapolato"]) / abs(frecce[0])
    assert distanza <= esito["gci_fine"], (tipo, distanza, esito["gci_fine"])


def test_su_c3d4_la_banda_contiene_anche_l_errore_vero(tmp_path):
    """Il caso in cui la lettura ingenua funziona -- e serve, perche' senza
    di esso il test gemello qui sotto sembrerebbe dire che la GCI non serve a
    niente. Qui la discretizzazione **domina**, quindi la banda che la stima
    sulla convergenza copre anche la distanza dalla teoria.
    """
    riferimento = M._freccia_timoshenko()
    frecce = _frecce(tmp_path, 1, "C3D4")
    esito = convergenza.stima(tuple(frecce), PASSI, fattore=FATTORE, ordine_formale=2.0)

    errore_vero = abs(frecce[0] - riferimento) / riferimento
    assert errore_vero <= esito["gci_fine"], (errore_vero, esito["gci_fine"])
    # e l'ordine osservato sta **sotto** quello formale: e' il segno che le
    # tre maglie non sono ancora nel campo asintotico pieno
    assert esito["ordine_osservato"] < 2.0


def test_su_c3d10_la_gci_non_e_una_barra_d_errore_verso_il_vero(tmp_path):
    """Il reperto del file, e va in tesi.

    La GCI **non contiene** la distanza da Timoshenko. Non e' la stima a
    sbagliare -- la distanza dal maglio convergente vale 0,00116 %, dentro la
    banda, e il test gemello lo asserisce. Il residuo e' **errore di modello**,
    non di discretizzazione.

    **Il divario si asserisce, il suo fattore no**, e la ragione e' un difetto
    che la CI ha colto in questo stesso test. La prima stesura pretendeva un
    fattore maggiore di dieci, misurato su macOS arm64: GCI 0,0015 % contro un
    errore vero dello 0,279 %, cioe' **186 volte**. Su Linux x86-64 l'errore
    vero e' praticamente lo stesso (0,271 %) ma la GCI vale **0,0346 %**,
    ventitre volte piu' grande, e il fattore scende a **7,8**.

    Il motivo e' una proprieta' del metodo, non un caso: su una grandezza
    **gia' convergente** le tre frecce differiscono per quantita' minime, e la
    GCI che ne discende misura il rumore del maglio invece della
    discretizzazione. Il maglio dipende dalla piattaforma (#66), quindi quel
    rumore anche. Il **fatto** -- la banda non contiene l'errore vero -- regge
    su entrambe; il **fattore** no, ed era una soglia decisa dopo aver visto il
    numero.
    """
    riferimento = M._freccia_timoshenko()
    frecce = _frecce(tmp_path, 2, "C3D10")
    esito = convergenza.stima(tuple(frecce), PASSI, fattore=FATTORE, ordine_formale=3.0)

    errore_vero = abs(frecce[0] - riferimento) / riferimento
    assert errore_vero > esito["gci_fine"], (errore_vero, esito["gci_fine"])
    # la freccia converge, e converge **sotto** la teoria di trave: e' la
    # stessa direzione trovata in #47, dove il C3D10 cade fra Eulero-Bernoulli
    # e Timoshenko
    assert esito["estrapolato"] < riferimento
