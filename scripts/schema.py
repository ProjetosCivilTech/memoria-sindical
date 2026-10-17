"""
Schema Pydantic v2 para os documentos da memória das negociações coletivas ECT.

Aceita a variedade real dos dados extraídos (ACTs, DCs, DCGs, cartilhas),
tolerando variações de tipo.

Decisões de design:
- `memoria_negociacao`: string OU dict (ACTs antigos vs DCs recentes).
- `valor_atual` / `valor_anterior`: float OU string (9.75, "9,75%", "5º dia útil").
- `greve`: bool OU dict (uns JSONs usam flag simples, outros metadados completos).
- Listas com `Field(default_factory=list)` para evitar mutação compartilhada.
- `extra="allow"` em todos os modelos preserva campos não previstos.
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any, Union


# ================================================================
# MODELOS AUXILIARES
# ================================================================

class MetadadosDocumento(BaseModel):
    """Cabeçalho do documento: tipo, período, órgão, entidades."""

    model_config = ConfigDict(extra="allow")

    tipo: str                                   # ACT, DC, DCG, Cartilha
    ano_inicio: int
    ano_fim: Optional[int] = None

    processo: Optional[str] = None
    tribunal: Optional[str] = None
    orgao: Optional[str] = None
    relator: Optional[str] = None

    data_julgamento: Optional[str] = None
    data_publicacao: Optional[str] = None
    data_assinatura: Optional[str] = None

    entidade_patronal: str = "ECT"
    entidades_profissionais: List[str] = Field(default_factory=list)

    arquivo_origem: str

    # Campos opcionais usados em alguns documentos
    grupo: Optional[str] = None                 # ex.: "2013-2014" (FENTECT × FINDECT)
    papel: Optional[str] = None                 # ex.: "FENTECT", "FINDECT"

    # Aceita True/False (flag simples) OU objeto estruturado
    greve: Optional[Union[bool, Dict[str, Any]]] = None

    observacao: Optional[str] = None


class Clausula(BaseModel):
    """Uma cláusula dentro de um documento normativo."""

    model_config = ConfigDict(extra="allow")

    id_canonico: str
    numero_clausula_original: Optional[Union[int, str]] = None
    titulo_original: str
    status: str

    # Aceita número (9.75) ou texto ("9,75%", "5º dia útil", "Novo modelo...")
    valor_atual: Optional[Union[float, str]] = None
    valor_anterior: Optional[Union[float, str]] = None
    unidade: Optional[str] = None

    detalhes: Optional[Dict[str, Any]] = None

    # Aceita string simples OU objeto estruturado
    memoria_negociacao: Optional[Union[str, Dict[str, Any]]] = None

    observacao: Optional[str] = None
    pagina_referencia: Optional[Union[int, str]] = None


# ================================================================
# MODELO PRINCIPAL
# ================================================================

class Documento(BaseModel):
    """Um documento normativo completo (ACT, DC, DCG ou Cartilha)."""

    model_config = ConfigDict(extra="allow")

    metadados_documento: MetadadosDocumento
    clausulas: List[Clausula] = Field(default_factory=list)

    temas_nao_mapeados: List[Any] = Field(default_factory=list)
    retorno_ao_trabalho: Optional[Dict[str, Any]] = None
    dispositivo_final: Optional[Dict[str, Any]] = None
    notas_metodologicas: List[Dict[str, Any]] = Field(default_factory=list)
    memoria_negociacao_geral: List[Dict[str, Any]] = Field(default_factory=list)

    # Campos especiais que aparecem em alguns JSONs
    clausulas_indeferidas: Optional[List[Dict[str, Any]]] = None
    materiais_complementares: Optional[List[Dict[str, Any]]] = None