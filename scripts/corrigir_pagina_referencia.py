"""
Corrige o campo 'pagina_referencia' em JSONs malformados.

O erro é sempre o mesmo: o valor veio sem aspas.

    "pagina_referencia": 1-2          →  "pagina_referencia": "1-2"
    "pagina_referencia": 21, 96, 113  →  "pagina_referencia": "21, 96, 113"
    "pagina_referencia": 4-5,         →  "pagina_referencia": "4-5",

Uso:
    python -m scripts.corrigir_pagina_referencia --pasta data/ --dry-run
    python -m scripts.corrigir_pagina_referencia --pasta data/
"""
import json
import re
import argparse
import shutil
from pathlib import Path
from datetime import datetime


# Captura o prefixo + valor. Valor começa com caractere que NÃO é aspas
# nem whitespace (para pular strings já corretas e valores vazios).
PADRAO = re.compile(
    r'("pagina_referencia"\s*:\s*)([^"\s][^\n]*)',
    re.MULTILINE,
)


def corrigir_pagina_referencia(texto: str) -> tuple[str, int]:
    """
    Envolve em aspas o valor de 'pagina_referencia' quando não é string.
    Retorna (texto_corrigido, num_ocorrencias).
    """
    ocorrencias = [0]

    def repl(m):
        prefixo = m.group(1)
        valor_bruto = m.group(2).strip()
        tinha_virgula = valor_bruto.endswith(",")
        valor = valor_bruto.rstrip(",").strip()
        ocorrencias[0] += 1
        # Se já é string entre aspas ou é null, deixa como está
        if valor.startswith('"') or valor == "null":
            return m.group(0)
        sufixo = "," if tinha_virgula else ""
        return f'{prefixo}"{valor}"{sufixo}'

    return PADRAO.sub(repl, texto), ocorrencias[0]


def processar(arq: Path, dry_run: bool):
    texto_original = arq.read_text(encoding="utf-8")

    # Se já é JSON válido, não mexe
    try:
        json.loads(texto_original)
        return "ok", 0
    except json.JSONDecodeError:
        pass

    texto_corrigido, n = corrigir_pagina_referencia(texto_original)

    # Se não houve mudança, não adianta tentar
    if n == 0:
        return "sem_correcao", 0

    # Testa se agora é JSON válido
    try:
        json.loads(texto_corrigido)
    except json.JSONDecodeError as e:
        return f"ainda_quebrado: {e.msg} (linha {e.lineno})", n

    if dry_run:
        return f"corrigivel ({n} ocorrências)", n

    # Backup + gravação
    backup = arq.with_suffix(arq.suffix + ".bak")
    shutil.copy2(arq, backup)
    arq.write_text(texto_corrigido, encoding="utf-8")
    return f"corrigido ({n} ocorrências)", n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", default="data/")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pasta = Path(args.pasta)
    arquivos = sorted(pasta.glob("*.json"))

    print(f"📂 {pasta}")
    print(f"📄 {len(arquivos)} arquivos\n")

    stats = {"ok": 0, "corrigido": 0, "corrigivel": 0, "falhou": 0, "sem_correcao": 0}

    for arq in arquivos:
        status, n = processar(arq, args.dry_run)
        if status == "ok":
            stats["ok"] += 1
        elif status.startswith("corrigivel"):
            stats["corrigivel"] += 1
            print(f"🔧 {arq.name}: {status}")
        elif status.startswith("corrigido"):
            stats["corrigido"] += 1
            print(f"✅ {arq.name}: {status}")
        elif status == "sem_correcao":
            stats["sem_correcao"] += 1
            print(f"⏭️  {arq.name}: campo não encontrado, sem alteração")
        else:
            stats["falhou"] += 1
            print(f"❌ {arq.name}: {status}")

    print()
    print(f"✅ Já OK:              {stats['ok']}")
    print(f"🔧 Corrigíveis:        {stats['corrigivel']}")
    print(f"✅ Corrigidos:         {stats['corrigido']}")
    print(f"⏭️  Sem alteração:      {stats['sem_correcao']}")
    print(f"❌ Falharam:           {stats['falhou']}")


if __name__ == "__main__":
    main()