 <!-- FUNCIONALIDADE: Botão "Agendar" - Monitoramento Automático de Status

**Localização:** Modal → Após Grid Pai (tabela principal) + Grid Filho (tabela detalhe)

**Objetivo:** Iniciar RPA que monitora status de aprovação até resolução final.

**Critérios de Busca (fixos):**
- Protocolo: [valor do grid pai]
- Pedido: [valor do grid pai]  
- Situação: "APROVADO"

**Lógica Completa do RPA (loop infinito):**

INÍCIO LOOP:
├── 1. Executa busca com Protocolo + Pedido + Situação="APROVADO"

RESULTADO DA BUSCA:
├── [APROVADO encontrado]
│ └── ✅ EXECUTA PRÓXIMOS PASSOS DO SISTEMA → SAI LOOP
├── [RECUSADO encontrado]
│ └── ❌ ATUALIZA LABEL STATUS="RECUSADO" → SAI LOOP
├── [PENDENTE encontrado]
│ └── ⏳ Aguarda 1s → Refresh URL → VOLTA INÍCIO LOOP
└── [Nada encontrado]
└── ⏳ Aguarda 1s → Refresh URL → VOLTA INÍCIO LOOP


**Comportamento Técnico:**
- Persistência infinita: nunca timeout
- Cada iteração PENDENTE/Nada: delay 1 segundo + refresh completo da página
- Estados finais AUTOMÁTICOS: APROVADO(sucesso) | RECUSADO(falha)
- Monitora transição natural: PENDENTE → APROVADO/RECUSADO

**Saídas Específicas:**
- ✅ APROVADO: Continua fluxo normal do sistema (agendamento)
- ❌ RECUSADO: Label Status = "RECUSADO" (feedback visual usuário)

**Implementação RPA: codigo exemplo para voce ter como referencia**
```python
while True:
    if busca_aprovado(protocolo, pedido):
        prosseguir_proximos_passos()
        break
    elif busca_recusado(protocolo, pedido): 
        atualizar_label_status("RECUSADO")
        break
    else:  # PENDENTE ou vazio
        sleep(1)
        refresh_page()
Contexto: RPA acompanha aprovação em tempo real no sistema externo.
 -->
