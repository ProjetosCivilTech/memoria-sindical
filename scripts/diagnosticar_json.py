"""
Diagnostica e tenta corrigir JSONs com erro de sintaxe.

Uso:
    python -m scripts.diagnosticar_json --pasta data/
"""
import json
import re
import argparse
from pathlib import Path


def mostrar_erro(arq: Path):
    """Mostra a linha exata onde o JSON quebra."""
    texto = arq.read_text(encoding="utf-8")
    try:
        json.loads(texto)
        return None
    except json.JSONDecodeError as e:
        linhas = texto.splitlines()
        print(f"\n{'=' * 70}")
        print(f"❌ {arq.name}")
        print(f"   {e.msg} — linha {e.lineno}, coluna {e.colno}")
        print(f"{'=' * 70}")
        ini = max(0, e.lineno - 3)
        fim = min(len(linhas), e.lineno + 2)
        for i in range(ini, fim):
            marker = ">>>" if i == e.lineno - 1 else "   "
            linha = linhas[i]
            # Mostra a linha truncada em 100 chars
            display = linha if len(linha) <= 100 else linha[:97] + "..."
            print(f"{marker} {i + 1:4} | {display}")
        # Caret na coluna
        linha = linhas[e.lineno - 1] if e.lineno - 1 < len(linhas) else ""
        col = min(e.colno - 1, len(linha))
        print(f"       | {' ' * col}^")
        # Caracteres ao redor
        if col < len(linha):
            contexto = linha[max(0, col - 15):col + 15]
            print(f"       | contexto: ...{contexto}...")
        return e


def tentar_corrigir(texto: str) -> tuple[str, list[str]]:
    """Tenta corrigir problemas comuns de JSON."""
    correcoes = []
    original = texto

    # 1. Trailing commas (vírgula antes de } ou ])
    novo = re.sub(r',\s*([}\]])', r'\1', texto)
    if novo != texto:
        correcoes.append("removidas vírgulas finais")
        texto = novo

    # 2. Smart quotes → straight quotes
    novo = texto.replace('"', '"').replace('"', '"')
    if novo != texto:
        correcoes.append("normalizadas aspas curvas")
        texto = novo

    # 3. Aspas simples em chaves → aspas duplas
    # Heurística: 'palavra': → "palavra":
    novo = re.sub(r"'([^']+)'(\s*:)", r'"\1"\2', texto)
    if novo != texto:
        correcoes.append("convertidas chaves com aspas simples")
        texto = novo

    # 4. Literal newlines dentro de strings (comum em LLM output)
    # Detecta string aberta com " e quebra antes de fechar
    # Estratégia: substitui '\n' literal por '\n' escapado dentro de valores
    # (isso é perigoso; só tenta se ainda não funcionou)
    try:
        json.loads(texto)
    except json.JSONDecodeError:
        # Tenta substituir newlines dentro de strings
        def fix_newlines(s):
            # Regex: captura string JSON e substitui newlines por espaços
            return re.sub(
                r'"([^"\\]*(?:\\.[^"\\]*)*)"',
                lambda m: '"' + m.group(1).replace('\n', '\\n').replace('\r', '') + '"',
                s,
            )
        novo = fix_newlines(texto)
        if novo != texto:
            try:
                json.loads(novo)
                correcoes.append("escapados newlines em strings")
                texto = novo
            except json.JSONDecodeError:
                pass

    return texto, correcoes


def processar(arq: Path, dry_run: bool):
    texto = arq.read_text(encoding="utf-8")

    try:
        json.loads(texto)
        return "ok"
    except json.JSONDecodeError:
        pass

    corrigido, correcoes = tentar_corrigir(texto)

    try:
        json.loads(corrigido)
        if dry_run:
            return f"corrigível ({', '.join(correcoes)})"
        # Backup e regrava
        backup = arq.with_suffix(arq.suffix + ".bak")
        backup.write_text(texto, encoding="utf-8")
        arq.write_text(corrigido, encoding="utf-8")
        return f"corrigido ({', '.join(correcoes)})"
    except json.JSONDecodeError:
        return "não corrigível automaticamente"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", default="data/")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mostrar-linhas", action="store_true",
                    help="Mostra a linha exata de cada erro")
    args = ap.parse_args()

    pasta = Path(args.pasta)
    arquivos = sorted(pasta.glob("*.json"))

    print(f"📂 {pasta}")
    print(f"📄 {len(arquivos)} arquivos\n")

    stats = {"ok": 0, "corrigido": 0, "corrigível": 0, "falhou": 0}

    for arq in arquivos:
        if args.mostrar_linhas:
            mostrar_erro(arq)

        status = processar(arq, args.dry_run)
        if status == "ok":
            stats["ok"] += 1
        elif status.startswith("corrigível"):
            stats["corrigível"] += 1
            print(f"🔧 {arq.name}: {status}")
        elif status.startswith("corrigido"):
            stats["corrigido"] += 1
            print(f"✅ {arq.name}: {status}")
        else:
            stats["falhou"] += 1
            print(f"❌ {arq.name}: {status}")

    print()
    print(f"✅ Já OK:              {stats['ok']}")
    print(f"🔧 Corrigíveis:        {stats['corrigível']}")
    print(f"✅ Corrigidos:         {stats['corrigido']}")
    print(f"❌ Não corrigíveis:    {stats['falhou']}")


if __name__ == "__main__":
    main()