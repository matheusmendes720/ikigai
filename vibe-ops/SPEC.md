# Vibe-Ops (Central de Comando)

## Propósito do Submódulo
A `life/vibe-ops` atua como a infraestrutura de Planejamento de Nível Sub-Atômico e Operações Arquiteturais ("Vibe Operations"). É daqui que orquestramos as integrações, os contratos de dados lógicos entre ferramentas (ex: Taskwarrior, Timewarrior, GnuCash, Obsidian, etc.) e abstraímos todo "como fazer" técnico das rotinas de rastreio de produtividade.

## Regras Críticas e Restritivas do Repositório (Agent Behavior)
Devido ao altíssimo nível de riqueza de detalhes concentrados nestas documentações lógicas (design de sistemas, diagramações e abstrações conceituais), adotamos a política de **Acúmulo Constante de Contextos**.

### 1. Diretriz: Append-Only e Engrandecimento
Os Agentes de IA trabalhando neste diretório devem:
1. **NUNCA DELETAR NADA**: É expressamente proibido remover sessões, tópicos, sub-tópicos ou re-escrever parágrafos inteiros reduzindo a quantidade de informação. A janela de contexto não pode sofrer fadiga de poda.
2. **Priorizar Append-Only**: Novas discussões, descobertas e arquitetamentos devem ser injetados entre as lógicas ou anexados ao final das sessões relevantes, aprofundando o nível de detalhe.
3. **Escultura e Organização**: Você pode re-organizar as estruturas (transformando em subtópicos ou listas), mas a string inteira pre-existente deve sobreviver ilesa ao processo de re-organização.

### 2. Protocolo de Refatoração (Apenas Sob Forte Demanda)
Se o usuário solicitar correções estruturais ou re-escrita ("refatoração de master guideline"):
1. O Agente deve estagnar a edição imediata.
2. O Agente deve propor um **Plano de Ação** descrevendo os blocos e vetores a serem movidos ou alterados.
3. O Agente deve requisitar a aprovação do usuário ("Approval Gate").
4. Somente após a liberação da aprovação os documentos podem ser mutados destrutivamente.

Este SPEC.md é imutável em seu propósito. Qualquer desvio destruirá o histórico de engenharia do usuário.
