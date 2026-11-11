"""Ferramentas que um agente pode chamar: esquema, validação de argumentos e execução.

Toda chamada passa por validação ANTES de executar: o modelo pode inventar argumentos, e quem executa não
deve confiar neles. Ferramentas marcadas como sensíveis nunca rodam sozinhas: ficam pendentes de aprovação humana.
"""
from dataclasses import dataclass
from typing import Any, Callable

TIPOS = {"string": str, "integer": int, "number": (int, float), "boolean": bool}


@dataclass(frozen=True)
class Ferramenta:
    nome: str
    descricao: str
    parametros: dict[str, dict]  # nome -> {"tipo": ..., "obrigatorio": True, "enum": [...], "minimo": 0}
    funcao: Callable[..., Any]
    sensivel: bool = False

    def esquema(self) -> dict:
        """Descrição no formato de 'tool use' (JSON Schema) para enviar a um modelo de linguagem."""
        props = {}
        for nome, regra in self.parametros.items():
            p = {"type": regra["tipo"]}
            if "enum" in regra:
                p["enum"] = regra["enum"]
            if "minimo" in regra:
                p["minimum"] = regra["minimo"]
            props[nome] = p
        obrig = [n for n, r in self.parametros.items() if r.get("obrigatorio", True)]
        return {
            "name": self.nome,
            "description": self.descricao,
            "input_schema": {"type": "object", "properties": props, "required": obrig, "additionalProperties": False},
        }


@dataclass
class Resultado:
    ok: bool
    conteudo: Any = None
    erro: str | None = None
    pendente: bool = False  # sensível: aguardando aprovação humana


def validar_argumentos(parametros: dict[str, dict], args: dict) -> list[str]:
    erros: list[str] = []
    if not isinstance(args, dict):
        return ["os argumentos devem ser um objeto"]
    for nome, regra in parametros.items():
        if nome not in args:
            if regra.get("obrigatorio", True):
                erros.append(f"falta o argumento '{nome}'")
            continue
        valor, tipo = args[nome], regra["tipo"]
        if isinstance(valor, bool) and tipo in ("integer", "number"):
            erros.append(f"'{nome}' deve ser {tipo}")
        elif not isinstance(valor, TIPOS[tipo]):
            erros.append(f"'{nome}' deve ser {tipo}")
        elif "enum" in regra and valor not in regra["enum"]:
            erros.append(f"'{nome}' deve ser um de {regra['enum']}")
        elif "minimo" in regra and valor < regra["minimo"]:
            erros.append(f"'{nome}' deve ser no mínimo {regra['minimo']}")
    for extra in sorted(set(args) - set(parametros)):
        erros.append(f"argumento desconhecido '{extra}'")
    return erros


class Registro:
    def __init__(self, ferramentas: list[Ferramenta]):
        self.por_nome = {f.nome: f for f in ferramentas}

    def esquemas(self) -> list[dict]:
        return [f.esquema() for f in self.por_nome.values()]

    def sensivel(self, nome: str) -> bool:
        return nome in self.por_nome and self.por_nome[nome].sensivel

    def executar(self, nome: str, args: dict, aprovado: bool = False) -> Resultado:
        ferramenta = self.por_nome.get(nome)
        if ferramenta is None:
            return Resultado(False, erro=f"ferramenta desconhecida '{nome}'")
        erros = validar_argumentos(ferramenta.parametros, args)
        if erros:
            return Resultado(False, erro="; ".join(erros))
        if ferramenta.sensivel and not aprovado:
            return Resultado(True, conteudo={"proposta": args}, pendente=True)
        try:
            return Resultado(True, conteudo=ferramenta.funcao(**args))
        except ValueError as e:  # erro esperado da própria ferramenta (ex.: data inválida)
            return Resultado(False, erro=str(e))
