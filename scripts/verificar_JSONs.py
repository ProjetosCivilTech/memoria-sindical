import json
import os

pasta_json = r"F:\AUTOMAÇÕES\projeto_memoria_sindicato\site\dados"

arquivos = [
    "efetivo_historico_projecao.json",
    "projecao_2026_2035.json",
    "ondas_aposentadoria.json",
    "raiox_aposentados.json"
]

for arquivo in arquivos:
    caminho = os.path.join(pasta_json, arquivo)
    if os.path.exists(caminho):
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        print(f"\n✅ {arquivo}")
        print(f"   Chaves: {list(dados.keys())}")
        
        # Verificar primeiros valores
        if 'efetivo_real' in dados:
            print(f"   efetivo_real (primeiros 5): {dados['efetivo_real'][:5]}")
            print(f"   efetivo_real (últimos 5): {dados['efetivo_real'][-5:]}")
            print(f"   efetivo_projecao (primeiros 5): {dados['efetivo_projecao'][:5]}")
        elif 'especial' in dados:
            print(f"   especial (primeiros 5): {dados['especial'][:5]}")
            print(f"   efetivo (primeiros 5): {dados['efetivo'][:5]}")
    else:
        print(f"\n❌ {arquivo} NÃO EXISTE")