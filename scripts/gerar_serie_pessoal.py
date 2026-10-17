# -*- coding: utf-8 -*-
"""
gerar_serie_pessoal.py — Série mensal de headcount + admissões + demissões.

Lê _pessoal_limpo.parquet (gerado pelo perfilar_pessoal.py), reconstrói a
evolução mensal do quadro de pessoal desde jan/1989 e salva:

    dados/export/serie_pessoal_mensal.json
    dados/export/analise_pessoal.html   (self-contained, abre no navegador)

Uso no Spyder:
    %cd F:\\AUTOMAÇÕES\\projeto_memoria_sindicato
    %run scripts/gerar_serie_pessoal.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ     = Path(r"F:\AUTOMAÇÕES\projeto_memoria_sindicato")
PARQUET  = RAIZ / "dados" / "export" / "_pessoal_limpo.parquet"
SAIDA_JSON = RAIZ / "dados" / "export" / "serie_pessoal_mensal.json"

MES_INICIO = "1989-01"


# ---------------------------------------------------------------------------
# 1. CARREGAR
# ---------------------------------------------------------------------------

def carregar() -> pd.DataFrame:
    if not PARQUET.exists():
        sys.exit(f"[ERRO] Rode antes: scripts/perfilar_pessoal.py")
    df = pd.read_parquet(PARQUET)
    # Garante datetime
    for c in ("admissao", "desligamento"):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# 2. SANITIZAR
# ---------------------------------------------------------------------------

def sanitizar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    hoje = pd.Timestamp.today().normalize()
    diag = {"total_bruto": len(df)}

    # Remove admissões futuras (66 registros que o perfil detectou)
    mask_fut_adm = df["admissao"] > hoje
    diag["adm_futuras_removidas"] = int(mask_fut_adm.sum())
    df = df.loc[~mask_fut_adm].copy()

    # Remove desligamentos futuros, se houver
    mask_fut_dem = df["desligamento"] > hoje
    diag["dem_futuras_removidas"] = int(mask_fut_dem.sum())
    df.loc[mask_fut_dem, "desligamento"] = pd.NaT

    # Remove desligamento anterior à admissão (inconsistência)
    mask_inv = (df["desligamento"].notna()) & \
               (df["desligamento"] < df["admissao"])
    diag["invertidas_removidas"] = int(mask_inv.sum())
    df.loc[mask_inv, "desligamento"] = pd.NaT

    # Sanidade: batimentos
    diag["total_limpo"] = len(df)
    diag["ativos_hoje"] = int((df["desligamento"].isna()).sum())
    diag["situacao_ativo_declarado"] = int((df["situacao"] == "ATIVO").sum())
    return df, diag


# ---------------------------------------------------------------------------
# 3. RECONSTRUIR SÉRIE
# ---------------------------------------------------------------------------

def serie_mensal(df: pd.DataFrame) -> pd.DataFrame:
    ini = pd.Period(MES_INICIO, freq="M")
    fim = pd.Period(pd.Timestamp.today(), freq="M")
    meses = pd.period_range(ini, fim, freq="M")

    # Headcount no início do período
    inicio = ini.to_timestamp()
    hc_inicial = int(
        ((df["admissao"] < inicio) &
         (df["desligamento"].isna() | (df["desligamento"] >= inicio))).sum()
    )

    # Eventos por mês
    adm = df["admissao"].dropna().dt.to_period("M").value_counts()
    dem = df["desligamento"].dropna().dt.to_period("M").value_counts()

    saida = pd.DataFrame(index=meses)
    saida["admissoes"] = adm.reindex(meses, fill_value=0)
    saida["demissoes"] = dem.reindex(meses, fill_value=0)
    saida["ativos"] = hc_inicial + \
        saida["admissoes"].cumsum() - saida["demissoes"].cumsum()
    saida["saldo"] = saida["admissoes"] - saida["demissoes"]

    # Metadados
    saida.attrs["headcount_inicial"] = hc_inicial
    saida.attrs["mes_inicial"] = str(ini)
    return saida


# ---------------------------------------------------------------------------
# 4. EXPORTAR JSON + HTML
# ---------------------------------------------------------------------------

def exportar_json(s: pd.DataFrame, diag: dict) -> None:
    payload = {
        "metadados": {
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "fonte": "_pessoal_limpo.parquet",
            "mes_inicial": s.attrs["mes_inicial"],
            "headcount_inicial": s.attrs["headcount_inicial"],
            "meses_total": len(s),
            "diagnostico": diag,
        },
        "periodos": [str(p) for p in s.index],
        "ativos":     [int(v) for v in s["ativos"]],
        "admissoes":  [int(v) for v in s["admissoes"]],
        "demissoes":  [int(v) for v in s["demissoes"]],
        "saldo":      [int(v) for v in s["saldo"]],
    }
    SAIDA_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tam = SAIDA_JSON.stat().st_size / 1024
    print(f"[OK] {SAIDA_JSON.name} ({tam:.1f} KB, {len(s)} meses)")


def exportar_html(s: pd.DataFrame, diag: dict) -> None:
    html = _template_html(s, diag)
    destino = SAIDA_JSON.parent / "analise_pessoal.html"
    destino.write_text(html, encoding="utf-8")
    tam = destino.stat().st_size / 1024
    print(f"[OK] {destino.name} ({tam:.1f} KB) — abre no navegador")


def _template_html(s: pd.DataFrame, diag: dict) -> str:
    # Injeta dados inline (evita CORS ao abrir file://)
    dados_js = json.dumps({
        "periodos":  [str(p) for p in s.index],
        "ativos":    [int(v) for v in s["ativos"]],
        "admissoes": [int(v) for v in s["admissoes"]],
        "demissoes": [int(v) for v in s["demissoes"]],
        "saldo":     [int(v) for v in s["saldo"]],
    }, ensure_ascii=False)
    meta_js = json.dumps(diag, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Evolução do quadro de pessoal — Correios (1989–hoje)</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  :root {{
    --preto:#0F0F0F; --vermelho:#C8102E; --amarelo:#FFCC00;
    --cinza:#595959; --cinza-claro:#EDEDED; --verde:#1B9E4B;
  }}
  * {{ box-sizing:border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin:0; padding:1.25rem; background:#FAFAFA; color:var(--preto);
  }}
  h1 {{ font-size:1.35rem; margin:0 0 .25rem; }}
  p.sub {{ color:var(--cinza); margin:0 0 1rem; font-size:.9rem; }}
  .stat-row {{
    display:grid; grid-template-columns:repeat(4, minmax(0,1fr));
    gap:.6rem; margin-bottom:1rem;
  }}
  .stat {{
    background:#fff; border-radius:8px; padding:.7rem .9rem;
    box-shadow:0 1px 3px rgba(0,0,0,.06);
  }}
  .stat .rot {{ font-size:.7rem; color:var(--cinza); text-transform:uppercase; letter-spacing:.04em; }}
  .stat .val {{ font-size:1.1rem; font-weight:700; margin-top:.15rem; }}
  #grafico {{ width:100%; background:#fff; border-radius:8px;
              box-shadow:0 1px 3px rgba(0,0,0,.06); }}
  .nota {{ font-size:.78rem; color:var(--cinza); margin-top:.8rem; line-height:1.5; }}
  @media (max-width:720px) {{
    body {{ padding:.75rem; }}
    .stat-row {{ grid-template-columns:repeat(2, minmax(0,1fr)); }}
    h1 {{ font-size:1.1rem; }}
  }}
</style>
</head>
<body>
  <h1>Evolução do quadro de pessoal — Correios</h1>
  <p class="sub">
    Reconstruído a partir de <strong>285 mil registros</strong> de
    admissão/desligamento. Série mensal desde
    <strong>janeiro de 1989</strong> até hoje.
  </p>

  <div class="stat-row" id="stats">
    <div class="stat"><div class="rot">Pico histórico</div>
      <div class="val" id="st-pico">—</div></div>
    <div class="stat"><div class="rot">Quadro atual</div>
      <div class="val" id="st-atual">—</div></div>
    <div class="stat"><div class="rot">Maior alta mensal</div>
      <div class="val" id="st-alta">—</div></div>
    <div class="stat"><div class="rot">Maior queda mensal</div>
      <div class="val" id="st-queda">—</div></div>
  </div>

  <div id="grafico" style="height:640px"></div>

  <p class="nota">
    <strong>Leitura:</strong> a linha azul é o quadro efetivo em cada mês;
    as barras verdes/vermelhas mostram admissões e demissões no mês.
    O saldo líquido (verde = entrou mais que saiu) aparece na linha inferior.
    Use o slider inferior ou arraste sobre o gráfico para dar zoom.
    Duplo clique reseta.
  </p>
  <p class="nota" id="diag"></p>

<script>
const D = {dados_js};
const DIAG = {meta_js};

// --- Estatísticas de cabeçalho
function fmt(n) {{ return n.toLocaleString('pt-BR'); }}
const ativos = D.ativos;
const pico   = Math.max(...ativos);
const iPico  = ativos.indexOf(pico);
const atual  = ativos[ativos.length - 1];
const saldo  = D.saldo;
const alta   = Math.max(...saldo);
const queda  = Math.min(...saldo);
const iAlta  = saldo.indexOf(alta);
const iQueda = saldo.indexOf(queda);

document.getElementById('st-pico').textContent  = fmt(pico) + ' (' + D.periodos[iPico] + ')';
document.getElementById('st-atual').textContent = fmt(atual) + ' (' + D.periodos[D.periodos.length-1] + ')';
document.getElementById('st-alta').textContent  = '+' + fmt(alta) + ' (' + D.periodos[iAlta] + ')';
document.getElementById('st-queda').textContent = fmt(queda) + ' (' + D.periodos[iQueda] + ')';

// --- Rodapé com diagnóstico
document.getElementById('diag').innerHTML =
  '<strong>Diagnóstico da base:</strong> ' +
  DIAG.total_bruto.toLocaleString('pt-BR') + ' registros brutos · ' +
  DIAG.adm_futuras_removidas + ' admissões futuras removidas · ' +
  DIAG.invertidas_removidas + ' datas invertidas corrigidas · ' +
  'headcount inicial em ' + D.periodos[0] + ': ' +
  DIAG_total_inicial() + ' pessoas.';

function DIAG_total_inicial() {{
  // o headcount inicial está em metadados, mas aqui reconstruímos do primeiro ponto
  return ativos[0].toLocaleString('pt-BR');
}}

// --- Gráfico
const traceAtivos = {{
  x: D.periodos, y: D.ativos,
  type: 'scatter', mode: 'lines',
  name: 'Quadro efetivo',
  line: {{ color: '#1F4E79', width: 2 }},
  fill: 'tozeroy',
  fillcolor: 'rgba(31,78,121,0.10)',
  hovertemplate: '%{{x}}<br><b>%{{y:,.0f}</b> ativos<extra></extra>',
  yaxis: 'y1',
}};

const traceAdm = {{
  x: D.periodos, y: D.admissoes,
  type: 'bar', name: 'Admissões',
  marker: {{ color: '#1B9E4B' }},
  hovertemplate: '%{{x}}<br>Admissões: <b>%{{y:,.0f}</b><extra></extra>',
  yaxis: 'y2',
}};

const traceDem = {{
  x: D.periodos, y: D.demissoes.map(v => -v),
  type: 'bar', name: 'Demissões',
  marker: {{ color: '#C8102E' }},
  customdata: D.demissoes,
  hovertemplate: '%{{x}}<br>Demissões: <b>%{{customdata:,.0f}</b><extra></extra>',
  yaxis: 'y2',
}};

const traceSaldo = {{
  x: D.periodos, y: D.saldo,
  type: 'scatter', mode: 'lines',
  name: 'Saldo líquido',
  line: {{ color: '#FFCC00', width: 1.5 }},
  hovertemplate: '%{{x}}<br>Saldo: <b>%{{y:+,.0f}</b><extra></extra>',
  yaxis: 'y3',
}};

const layout = {{
  margin: {{ l: 70, r: 30, t: 30, b: 60 }},
  grid: {{ rows: 3, columns: 1, subplots: [['xy1'], ['xy2'], ['xy3']],
           roworder: 'top to bottom' }},
  showlegend: true,
  legend: {{ orientation: 'h', x: 0, y: 1.06, font: {{ size: 11 }} }},
  xaxis: {{
    type: 'category',
    showticklabels: false,
    rangeslider: {{ visible: true, thickness: 0.06 }},
    showgrid: false,
  }},
  xaxis2: {{ type: 'category', showticklabels: false, showgrid: false }},
  xaxis3: {{
    type: 'category',
    showticklabels: true,
    tickmode: 'auto',
    nticks: 12,
    showgrid: false,
  }},
  yaxis:  {{ title: 'Ativos', tickformat: ',.0f',
             gridcolor: 'rgba(0,0,0,0.05)', zeroline: false }},
  yaxis2: {{ title: 'Adm/Dem (mês)', tickformat: ',.0f',
             gridcolor: 'rgba(0,0,0,0.05)', zeroline: true,
             zerolinecolor: '#999' }},
  yaxis3: {{ title: 'Saldo', tickformat: '+,.0f',
             gridcolor: 'rgba(0,0,0,0.05)', zeroline: true,
             zerolinecolor: '#999' }},
  height: 640,
  bargap: 0.05,
  hovermode: 'x unified',
}};

Plotly.newPlot('grafico',
  [traceAtivos, traceAdm, traceDem, traceSaldo],
  layout,
  {{ responsive: true, displaylogo: false,
     modeBarButtonsToRemove: ['lasso2d','select2d','autoScale2d'] }}
);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print(f"[1/4] Carregando parquet ...")
    df = carregar()
    print(f"      {len(df):,} linhas")

    print(f"[2/4] Sanitizando ...")
    df, diag = sanitizar(df)
    print(f"      {diag['adm_futuras_removidas']} admissões futuras removidas")
    print(f"      {diag['invertidas_removidas']} datas invertidas corrigidas")
    print(f"      {diag['ativos_hoje']:,} ativos hoje (situacao declara "
          f"{diag['situacao_ativo_declarado']:,})")

    print(f"[3/4] Reconstruindo série mensal ...")
    s = serie_mensal(df)
    print(f"      {len(s)} meses | headcount inicial "
          f"{s.attrs['headcount_inicial']:,} em {s.attrs['mes_inicial']}")

    print(f"[4/4] Exportando ...")
    exportar_json(s, diag)
    exportar_html(s, diag)

    # Amostra rápida no console
    print("\n--- AMOSTRA ---")
    for p in (pd.Period("1989-01", "M"),
              pd.Period("1995-01", "M"),
              pd.Period("2005-01", "M"),
              pd.Period("2015-01", "M"),
              pd.Period("2020-06", "M"),
              s.index[-1]):
        if p in s.index:
            row = s.loc[p]
            print(f"  {p}  ativos={row['ativos']:>7,}  "
                  f"adm={row['admissoes']:>4,}  dem={row['demissoes']:>4,}")


if __name__ == "__main__":
    main()