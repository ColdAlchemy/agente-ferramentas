"""O laço do agente: o modelo decide, o código valida, executa, aplica as guardas e devolve o resultado."""
from dataclasses import dataclass, field
from typing import Protocol

from .ferramentas import Registro, Resultado
from .guardas import como_texto, parece_injecao


@dataclass(frozen=True)
class Chamar:
    nome: str
    argumentos: dict


@dataclass(frozen=True)
class Responder:
    texto: str


class Modelo(Protocol):
    def decidir(self, pedido: str, historico: list["Passo"]) -> "Chamar | Responder": ...


@dataclass
class Passo:
    nome: str
    argumentos: dict
    status: str  # executada | pendente | bloqueada | erro | repetida
    resultado: Resultado | None = None


@dataclass
class Execucao:
    pedido: str
    resposta: str = ""
    passos: list[Passo] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)
    motivo_parada: str = "resposta"  # resposta | limite_de_passos | repeticao

    def chamadas(self) -> list[str]:
        """Nomes das ferramentas pedidas, na ordem (inclui pendentes, bloqueadas e com erro)."""
        return [p.nome for p in self.passos]

    def executadas(self) -> list[str]:
        return [p.nome for p in self.passos if p.status == "executada"]

    def pendentes(self) -> list[Passo]:
        return [p for p in self.passos if p.status == "pendente"]


class Agente:
    def __init__(self, modelo: Modelo, registro: Registro, guardas: bool = True, max_passos: int = 6):
        self.modelo, self.registro, self.guardas, self.max_passos = modelo, registro, guardas, max_passos

    def executar(self, pedido: str) -> Execucao:
        ex = Execucao(pedido)
        modo_seguro = False  # liga quando um dado de ferramenta traz instruções suspeitas
        vistas: set[tuple] = set()
        for _ in range(self.max_passos):
            acao = self.modelo.decidir(pedido, ex.passos)
            if isinstance(acao, Responder):
                ex.resposta = acao.texto
                return ex
            chave = (acao.nome, repr(sorted(acao.argumentos.items())) if isinstance(acao.argumentos, dict) else repr(acao.argumentos))
            if chave in vistas:  # mesma chamada de novo: o agente está em laço
                ex.passos.append(Passo(acao.nome, acao.argumentos, "repetida"))
                ex.motivo_parada = "repeticao"
                ex.resposta = "Parei porque a mesma chamada se repetiu."
                return ex
            vistas.add(chave)

            if self.guardas and modo_seguro and self.registro.sensivel(acao.nome):
                ex.alertas.append(f"bloqueada '{acao.nome}': a ordem veio de dados de ferramenta, não do usuário")
                ex.passos.append(Passo(acao.nome, acao.argumentos, "bloqueada"))
                continue

            # sem guardas, o baseline executa até as ferramentas sensíveis (para mostrar o risco)
            res = self.registro.executar(acao.nome, acao.argumentos, aprovado=not self.guardas)
            status = "pendente" if res.pendente else ("executada" if res.ok else "erro")
            ex.passos.append(Passo(acao.nome, acao.argumentos, status, res))

            if self.guardas and res.ok and not res.pendente and parece_injecao(como_texto(res.conteudo)):
                modo_seguro = True
                ex.alertas.append(f"possível injeção de prompt na saída de '{acao.nome}'")
        ex.motivo_parada = "limite_de_passos"
        ex.resposta = "Parei porque atingi o limite de passos."
        return ex

    def aprovar(self, passo: Passo) -> Resultado:
        """A pessoa aprovou uma ação pendente: só agora a ferramenta sensível roda."""
        if passo.status != "pendente":
            raise ValueError("só ações pendentes podem ser aprovadas")
        res = self.registro.executar(passo.nome, passo.argumentos, aprovado=True)
        passo.resultado, passo.status = res, "executada" if res.ok else "erro"
        return res
