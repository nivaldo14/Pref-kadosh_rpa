# FUNCIONALIDADE: Grid "Agendas Executadas" - Auto-atualização e Filtro

**Localização:** Formulário Principal → Aba "Gerar Agenda" → Card "Agendas Executadas"

## 1. AUTO-ATUALIZAÇÃO (POLLING)
✅ Aplicar POLL de 5 segundos para atualizar automaticamente o grid
✅ Refresh automático dos dados a cada 5s (sem ação do usuário)

## 2. FONTE DE DADOS
✅ Grid carrega da tabela: AGENDA
✅ Filtro automático: registros do ANO e MÊS selecionados
✅ Exibe TODOS registros que atendem ANO+MÊS

## 3. FILTRO ANO/MÊS
✅ Local: Ao lado do botão "Dados Fertipar"
✅ Criar 2 SELECTs: [ANO] [MÊS]
✅ VALORES DEFAULT:

ANO = Ano corrente (2026)

MÊS = Mês corrente (Janeiro)
✅ Ao alterar → Filtra grid INSTANTANEAMENTE

## COMPORTAMENTO ESPERADO:

Fluxo Completo:
Carrega com ANO=2026, MÊS=01 (default)
Grid mostra agendas de Jan/2026 da tabela AGENDA
Poll 5s → Atualiza grid automaticamente
Usuário altera ANO/MÊS → Grid refiltra imediatamente
Poll 5s continua funcionando com filtro ativo

## IMPLEMENTAÇÃO:

```javascript
// Auto-refresh 5s
setInterval(atualizarGridAgendas, 5000);

// Filtro onChange
selectAno.onchange = filtrarGrid;
selectMes.onchange = filtrarGrid;

// Query base
SELECT * FROM agenda WHERE YEAR(data) = ? AND MONTH(data) = ?
Resultado: Grid sempre atualizado + filtro dinâmico por período! 🚀

✅ **Prompt claro, objetivo e pronto para desenvolvimento!**