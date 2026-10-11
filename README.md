# Refactor Arch

## Análise Manual
### Projeto code-smells-project

***Severidade Critical***
- key exposta sem nenhum tipo de mitigador em um arquivo versionado do projeto (deveria no mínimo ser um .env não commitado ou um keyvault ou similar). Pior ainda, ela é exposta no endpoint de healthcheck
- Rota "/admin/query" não está protegida de SQL Injection.
- SQL Injection possível em praticamente todo o models.py
- Senha em texto puro (sem hash ou algum mecânismo de segurança)

***Severidade MEDIUM***
- Não há arquivo de configuração. Mudar o modo debug por exemplo exige uma alteração no arquivo app.py, que tem outras responsabilidades
- Sistema não está preparado para rodar em produção (app.run(host="0.0.0.0", port=5000, debug=True))
- Controllers tem muita responsabilidade. Deviam cuidar só da parte de interface (qual código HTTP, autenticação, etc.). Regras de negócio deveriam estar em services.

***Severidade LOW***
- Um arquivo controllers para todas as entidades. Extremamente confuso.
- Em get_pedidos_usuario (arquivo models.py). Os nomes das variáveis cursor1, cursor2 e cursor3 são genéticos e não dizem o que foi buscado.

### Projeto ecommerce-api-legacy

***Severidade Critical***
- Senha do admin_master commitada em arquivo versionado. Deveria estar em um keyvault ou no mínimo em um env não commitado (ainda altamente arriscado)
- Senhas armazenadas sem grande segurança com bad_crypto. Ataque ao sistema é muito fácil.
- Múltiplas ações no banco de dados sem uma transação. Possibilidade de inconsistência na base de dados (exemplo /api/checkout')
- PaymentgatewayKey exposta como log no console.
- Número do cartão exposto como log!
- Deletes mantém entidades com referência a entidade deletada.
- Rotas de admin sem quaisquer autenticação, entregando dados sensíveis a qulaquer um.

***Severidade MEDIUM***
- Arquivo AppManager faz tudo. Não há qualquer organização no projeto (exemplo, controller, services, repositories, infra, etc).
- Não existe rate limiting, limite de tamanho de body, CORS, middleware de validação, etc.

***Severidade LOW***
- Rotas confusas e difíceis de entender com alta complexidade idiomática.
- Diversos select *. As boas práticas ditam que devemos apenas buscar colunas que de fato vamos usar (para ficarmos future proof com relação a estrutura que pode mudar e também para economizar recursos).
- Péssima nomenclatura. O contrato da API usa usr, eml, pwd, c_id, card (:29-33) mapeados para u, e, p, cid, cc — e e ocupa o nome convencional da variável de erro. Junta com o self = this 

### Projeto task-manager-api

***Severidade Critical***
- NotificationService com usuário e senha hardcoded, exposto em arquivo versionado e commitado no repositório.
-SECRET_KEY hardcoded em app.py:13 ('super-secret-key-123').

***Severidade MEDIUM***
- validate_email em helpers.py deixa passar emaiils inválido (só valida ter dois blocos de texto separados por @)
- Lógica de "task atrasada" reimplementada 6 vezes, com o método do model existindo e nunca sendo chamado.

***Severidade LOW***
- created_at em diversos arquivos do projeto usa um método deprecated (datetime.utcnow). 
- no arquivo task.py a lib json é importada e nunca usada
- No arquivo helpers.py há diversos exemplos de libs importadas e não usadas
## Construção da Skill
Fase 1: Escrita manual da skill baseada nas instruções do projeto.
Contendo assim o que cada etapa do fluxo deveria fazer e o que era esperado.
Foram usadas técnicas de prompts engeneering como few shot e chain of thought para organizer o trabalho.
Fase 2: Formulação de um plano para chegar a versão final da skill.
- Como adicionar os arquivos de referência e quais estratégias usar para que não fiquem grandes demais e sejam ignoradas pelos agented de IA? -> Nesse caso a estratégia foi dividir certos pontos que precisam de mais detalhamento em arquivos de referência + deep analysis (feito para anti patterns e refactoring playbook). O agente identifica o problema e então toma a ação carregando só o necessário. -> Nenhum arquivo de referência deveria ter mais de 200 linhas.
- Refatorar a skill para um linguagem mais clara, sem ambiguidade e já referenciando os reference files. Foi usado a IA para pontuar quais são as falhas da skill frente as instruções para que as mudanças pudessem ser feitas com clareza e intencionalidade.

## Resultados

## Como Executar
