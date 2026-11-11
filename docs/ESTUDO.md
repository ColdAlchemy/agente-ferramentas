# Guia de estudo — agente-ferramentas

## 1. Roteiro de leitura
1. `agente/ferramentas.py`: o que é uma ferramenta e por que se valida antes de executar.
2. `agente/negocio.py`: os dados (repare no estoque "envenenado").
3. `agente/guardas.py` e `agente/agente.py`: o laço e as camadas de defesa.
4. `agente/modelos.py`: como o modelo simulado "obedece" a injeção e como o cliente real monta as mensagens.
5. `agente/avaliacao.py` e `data/cenarios.json`: como se mede segurança.

## 2. Conceitos
**Agente.** Um laço: o modelo escolhe uma ação, o código a executa, o resultado volta para o modelo, e repete até responder ou estourar o limite.

**Tool calling (tool use).** O modelo recebe a descrição das ferramentas (nome, descrição, esquema JSON dos argumentos) e devolve "quero chamar X com estes argumentos". Quem executa é o seu código, não o modelo.

**Validação de argumentos.** O modelo pode errar tipo, esquecer campo ou inventar parâmetro. Valide como validaria entrada de um usuário.

**Injeção de prompt (indireta).** O ataque não vem do usuário, vem de um texto que o agente lê (cadastro, e-mail, página). Se o texto diz "ignore as instruções e faça X", um modelo ingênuo pode obedecer.

**Dado × instrução.** Regra de ouro: o que vem de ferramenta é dado. Marcar isso no prompt ajuda, mas **não basta** (modelos podem falhar), por isso há outras camadas.

**Humano no laço (human-in-the-loop).** Ações com efeito no mundo (enviar mensagem, pagar, apagar) ficam pendentes até uma pessoa aprovar. É a camada que não depende de o modelo ou o detector acertarem.

**Defesa em camadas.** Nenhuma camada é perfeita; juntas, uma falha da primeira é pega pela segunda. O cenário `i5` mostra isso.

**Menor privilégio.** Dê ao agente só as ferramentas de que ele precisa, e deixe as perigosas sensíveis.

**Avaliação de segurança.** Além de "acertou?", medir "fez algo que não devia?". Aqui: violações de segurança e injeções barradas, com e sem guardas, para ver o efeito delas.

**Limites de uso.** Máximo de passos e detecção de laço evitam custo infinito e travamento.

## 3. Perguntas prováveis (treine em voz alta)
- *O que é injeção de prompt indireta?* Ordens maliciosas escondidas em dados que o agente lê.
- *Por que não basta um detector?* Detector por padrão é contornável (veja `i5`); a aprovação humana protege mesmo quando ele falha.
- *Seu modelo é um LLM de verdade?* Não: é simulado, para testar o arcabouço de forma repetível. O cliente da API real existe e foi testado só com HTTP simulado.
- *Por que bloquear tudo depois de um alerta, até o que o usuário pediu?* Porque, depois de suspeitar que a execução foi contaminada, é mais seguro parar as ações sensíveis e pedir confirmação.
- *Quais as limitações dos seus números?* Cenários escritos por mim junto com as guardas; modelo simulado; poucos ataques.
- *O que você faria com um LLM real?* Montar um conjunto maior de ataques, variar a forma das injeções e medir a taxa de sucesso do atacante com e sem cada camada.

## 4. Exercícios
1. Adicione um novo produto "envenenado" com uma frase que o detector **não** reconheça e confirme que nada é enviado.
2. Adicione um padrão ao detector que pegue "mande mensagem" e veja o `i5` passar a gerar alerta. O que muda na resposta?
3. Crie uma ferramenta sensível nova (por exemplo, `aplicar_desconto`) e escreva dois cenários para ela.
4. Mude `max_passos` para 2 e veja quais cenários falham. Por quê?
5. Implemente um modo em que uma ação pendente aprovada pelo usuário **depois de um alerta** possa rodar. Quais riscos isso traz?

## 5. O que dizer sobre a sua experiência (sem exagerar)
"Implementei do zero um laço de agente com tool calling, validação de argumentos, aprovação humana para ações sensíveis e guardas contra injeção de prompt, e uma avaliação que compara o agente com e sem guardas. Usei um modelo simulado e dados fictícios, e desenvolvi com o auxílio do Claude Code, estudando o código." Não diga que "protegeu agentes em produção" nem que sabe defender LLMs contra ataques reais: o projeto cobre o arcabouço e não ataques reais.
