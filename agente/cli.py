"""Linha de comando: executar, avaliar e ferramentas."""
import argparse
import json
import sys
from pathlib import Path

from .agente import Agente
from .avaliacao import avaliar_tudo, carregar_cenarios
from .modelos import ClienteAnthropic, ModeloScriptado
from .negocio import Loja, ferramentas_da_loja

RAIZ = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="agente", description="Agente com ferramentas, guardas e avaliação.")
    sub = ap.add_subparsers(dest="comando", required=True)
    e = sub.add_parser("executar", help="roda o agente em um pedido")
    e.add_argument("pedido")
    e.add_argument("--ingenuo", action="store_true", help="modelo simulado que obedece a ordens escondidas em dados")
    e.add_argument("--sem-guardas", action="store_true", help="desliga as guardas (mostra o risco)")
    e.add_argument("--real", action="store_true", help="usa a API da Anthropic (exige ANTHROPIC_API_KEY)")
    a = sub.add_parser("avaliar", help="roda os cenários em três configurações")
    a.add_argument("--cenarios", default=str(RAIZ / "data" / "cenarios.json"))
    a.add_argument("--detalhes", action="store_true", help="lista cada cenário")
    sub.add_parser("ferramentas", help="mostra os esquemas das ferramentas")
    args = ap.parse_args(argv)

    if args.comando == "ferramentas":
        print(json.dumps(ferramentas_da_loja(Loja()).esquemas(), ensure_ascii=False, indent=2))
        return 0

    if args.comando == "executar":
        loja = Loja()
        registro = ferramentas_da_loja(loja)
        modelo = ClienteAnthropic(registro) if args.real else ModeloScriptado(args.ingenuo)
        ex = Agente(modelo, registro, guardas=not args.sem_guardas).executar(args.pedido)
        for p in ex.passos:
            print(f"  [{p.status:9}] {p.nome} {json.dumps(p.argumentos, ensure_ascii=False)}")
        for al in ex.alertas:
            print("  ALERTA:", al)
        print("Resposta:", ex.resposta)
        print("Mensagens realmente enviadas:", len(loja.mensagens))
        return 0

    cenarios = carregar_cenarios(args.cenarios)
    resultados = avaliar_tudo(cenarios)
    print(f"{'configuração':30} {'sucesso':>8} {'violações':>10} {'injeções barradas':>18}")
    for r in resultados:
        print(f"{r['configuracao']:30} {r['sucesso']:>3}/{r['total']:<4} {r['violacoes_de_seguranca']:>10} {r['injecoes_bloqueadas']:>9}/{r['injecoes']:<8}")
    if args.detalhes:
        for r in resultados:
            print("\n==", r["configuracao"])
            for x in r["resultados"]:
                marca = "ok " if x["sucesso"] else "FALHA"
                extra = f" violou: {x['violacoes']}" if x["violacoes"] else ""
                print(f"  {marca} {x['id']:3} {x['tipo']:9} {x['chamadas']}{extra}")
    return 0
