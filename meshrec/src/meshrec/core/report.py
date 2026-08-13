"""Report statico generato dal registro: tabella, fronte, istogrammi SVG.

Nessuna libreria di grafici: per pochi istogrammi non si giustifica, ed e'
gia' escluso dalla spec di architettura. Nessuna miniatura e nessun
rendering 3D: il confronto visivo arriva con il viewport della Fase 3, che
rivestira' questo report invece di riscriverlo.
"""

from __future__ import annotations

import html
from pathlib import Path

from meshrec.core.sweep import load_registry

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("fingerprint", "impronta"),
    ("axes", "assi"),
    ("outcome", "esito"),
    ("thickness_error", "errore di spessore [mm]"),
    ("tets", "tetraedri"),
    ("over", "fuori vincolo"),
    ("dihedral", "diedro min., mediana"),
    ("duration_s", "durata [s]"),
)


def histogram_svg(values: list[float], title: str, bins: int) -> str:
    """Istogramma come SVG scritto a mano, senza dipendenze."""
    if not values:
        return f"<svg width='320' height='140'><text x='8' y='20'>{html.escape(title)}: vuoto</text></svg>"

    low, high = min(values), max(values)
    width = (high - low) / bins if high > low else 1.0
    counts = [0] * bins
    for value in values:
        index = min(int((value - low) / width), bins - 1)
        counts[index] += 1
    tallest = max(counts) or 1

    bars = "".join(
        f"<rect x='{8 + index * (300 / bins):.1f}' y='{120 - 100 * count / tallest:.1f}' "
        f"width='{300 / bins - 2:.1f}' height='{100 * count / tallest:.1f}' fill='#456'/>"
        for index, count in enumerate(counts)
    )
    return (
        f"<svg width='320' height='140' role='img'>"
        f"<text x='8' y='14' font-size='11'>{html.escape(title)}</text>{bars}"
        f"<text x='8' y='134' font-size='10'>{low:.3g}</text>"
        f"<text x='260' y='134' font-size='10'>{high:.3g}</text></svg>"
    )


def _cell(row: dict[str, object], key: str) -> str:
    volume = row.get("metrics", {}).get("10_volume_quality", {})
    if key == "tets":
        value = volume.get("tets")
    elif key == "over":
        value = volume.get("radius_edge_over_reference")
    elif key == "dihedral":
        value = volume.get("min_dihedral_deg", {}).get("median")
    else:
        value = row.get(key)

    if isinstance(value, float):
        return f"{value:.4g}"
    if isinstance(value, dict):
        return ", ".join(
            f"{html.escape(str(name))}={html.escape(str(item))}" for name, item in value.items()
        ) or "base"
    return html.escape(str(value)) if value is not None else ""


def write_report(registry_path: Path, out_path: Path) -> Path:
    """Scrive il report HTML a partire dal solo registro.

    Il registro e' l'unica rappresentazione autoritativa: la tabella piatta
    per l'appendice si genera da qui e non si mantiene a mano, che e' il modo
    in cui in Fase 1 numeri di corse diverse sono finiti fianco a fianco.
    """
    rows = load_registry(registry_path)
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in _COLUMNS)
    body = "".join(
        "<tr class='{}'>{}</tr>".format(
            "fronte" if row.get("on_front") else "",
            "".join(f"<td>{_cell(row, key)}</td>" for key, _ in _COLUMNS),
        )
        for row in rows
    )

    errors = [row["thickness_error"] for row in rows if isinstance(row.get("thickness_error"), float)]
    tets = [
        float(row["metrics"]["10_volume_quality"]["tets"])
        for row in rows
        if row.get("metrics", {}).get("10_volume_quality")
    ]

    document = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><title>Sweep — {html.escape(registry_path.parent.name)}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #222; }}
table {{ border-collapse: collapse; font-size: 0.85rem; }}
th, td {{ border: 1px solid #ccc; padding: 0.25rem 0.5rem; text-align: right; }}
th {{ background: #eee; }}
tr.fronte td {{ background: #eaf3ea; font-weight: 600; }}
</style></head><body>
<h1>Sweep — {html.escape(registry_path.parent.name)}</h1>
<p>{len(rows)} candidati. Le righe evidenziate sono il <strong>fronte</strong> di Pareto:
errore di spessore, numero di tetraedri e frazione fuori vincolo, tutti da minimizzare.</p>
<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>
<h2>Distribuzioni</h2>
{histogram_svg(errors, "errore di spessore [mm]", bins=12)}
{histogram_svg(tets, "tetraedri", bins=12)}
</body></html>"""

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document, encoding="utf-8")
    return out_path
