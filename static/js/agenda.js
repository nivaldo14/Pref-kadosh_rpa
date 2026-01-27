document.addEventListener('DOMContentLoaded', function() {


    // Elementos do Modal Fertipar
    const fertiparModal = document.getElementById('fertiparModal');
    const btnLerDadosFertipar = document.getElementById('btnLerDadosFertipar');
    const lastReadStatus = document.getElementById('lastReadStatus');
    const fertiparDataTableBody = document.getElementById('fertiparDataTableBody');
    const selectedFertiparItemsDiv = document.getElementById('selected-fertipar-items');
    const btnSaveFertipar = fertiparModal ? fertiparModal.querySelector('.modal-footer .btn-primary') : null;

    // Elementos do Formulário de Agendamento
    const formGerarAgenda = document.getElementById('form-gerar-agenda');
    const motoristaSelect = document.getElementById('agenda-motorista-select');
    const caminhaoSelect = document.getElementById('agenda-caminhao-select');
    const hiddenMotoristaId = document.getElementById('hidden-motorista-id');
    const hiddenCaminhaoId = document.getElementById('hidden-caminhao-id');
    const hiddenFertiparItemJson = document.getElementById('hidden-fertipar-item-json');
    const motoristaInfoDiv = document.getElementById('agenda-motorista-info');
    const caminhaoInfoDiv = document.getElementById('agenda-caminhao-info');

    // Tabela de Agendas Executadas
    const agendasExecutadasBody = document.getElementById('agendas-executadas-body');
    const agendasEmEsperaBody = document.getElementById('agendas-em-espera-body');

    // Filtros de Ano e M├¬s
    const selectAnoFiltro = document.getElementById('select-ano-filtro');
    const selectMesFiltro = document.getElementById('select-mes-filtro');

    // --- Constantes ---
    const LAST_READ_KEY = 'lastFertiparRead';
    const FIVE_MINUTES_MS = 5 * 60 * 1000;
    const POLLING_INTERVAL_MS = 5000; // 5 segundos para o auto-refresh

    // --- Fun├º├Áes Auxiliares ---
    function getAuthHeaders() {
        const token = localStorage.getItem('jwt_token'); // Assumindo que o token ├® salvo aqui no login
        const headers = {
            'Content-Type': 'application/json'
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    }

    function formatDateTime(date) {
        const options = { year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' };
        return date.toLocaleDateString('pt-BR', options);
    }
    
    function showAlert(message, type = 'info', isFixed = false) {
        toastr.options = {
            "closeButton": true,
            "debug": false,
            "newestOnTop": false,
            "progressBar": true,
            "positionClass": "toast-top-right",
            "preventDuplicates": false,
            "onclick": null,
            "showDuration": "300",
            "hideDuration": "1000",
            "extendedTimeOut": "1000",
            "showEasing": "swing",
            "hideEasing": "linear",
            "showMethod": "fadeIn",
            "hideMethod": "fadeOut"
        };

        // Caso especial para a mensagem de site bloqueado
        if (message === "Dados N├úo coletados, site j├í bloqueado!") {
            toastr.options.timeOut = 0; // Fica vis├¡vel at├® ser fechado
            type = 'warning'; // Usa o tipo 'aviso' (amarelo)
        } else if (type === 'danger') {
            toastr.options.timeOut = 0; // Erros reais tamb├®m ficam vis├¡veis
        } else if (isFixed) {
            toastr.options.timeOut = 0; // Fixed toast
            toastr.options.extendedTimeOut = 0;
        }
        else {
            toastr.options.timeOut = 10000; // 10 segundos para outros tipos (success, info)
        }

        const toastrType = type === 'danger' ? 'error' : type;
        toastr[toastrType](message);
    }

    // Fun├º├Áes auxiliares para encontrar e atualizar o status visual da linha
    function updateTableRowStatus(protocolo, pedido, newStatus) {
        // Encontra a linha principal usando o protocolo (e opcionalmente o pedido para maior especificidade)
        // Usamos um atributo de dados 'data-protocolo-pedido' para uma identifica├º├úo ├║nica
        const rowIdentifier = `${protocolo}-${pedido}`;
        const mainRow = $(`#fertiparDataTableBody tr.fertipar-main-row[data-protocolo="${protocolo}"][data-pedido="${pedido}"]`);
        
        if (mainRow.length === 0) {
            console.warn(`Linha para protocolo ${protocolo} e pedido ${pedido} n├úo encontrada.`);
            return;
        }

        const subgridRow = mainRow.next('.fertipar-subgrid-row');
        const statusInput = subgridRow.find('.subgrid-status');

        // Atualiza o texto do status no subgrid
        statusInput.val(newStatus);

        // Remove classes de status antigas
        mainRow.removeClass('agendado-row status-changed-row erro-row recusado-row'); // Added erro-row and recusado-row
        subgridRow.removeClass('agendado-row status-changed-row erro-row recusado-row'); // Added erro-row and recusado-row

        // Adiciona a classe apropriada com base no novo status
        if (newStatus === 'espera') {
            mainRow.addClass('agendado-row'); // Agendado (verde)
            subgridRow.addClass('agendado-row');
        } else if (newStatus === 'erro' || newStatus === 'erro (Dev)') { // Added condition for error
            mainRow.addClass('erro-row');
            subgridRow.addClass('erro-row');
        } else if (newStatus === 'recusado') { // Adicionada condição para 'recusado'
            mainRow.addClass('recusado-row'); // Amarelo
            subgridRow.addClass('recusado-row');
        } else {
            mainRow.addClass('status-changed-row'); // Status diferente de espera (azul)
            subgridRow.addClass('status-changed-row');
        }
    }

    // Fun├º├Áes auxiliares para limpar e atualizar UI
    function clearAgendaForm() {
        motoristaSelect.value = '';
        caminhaoSelect.value = '';
        motoristaInfoDiv.innerHTML = '';
        caminhaoInfoDiv.innerHTML = '';
        hiddenMotoristaId.value = '';
        hiddenCaminhaoId.value = '';
        hiddenFertiparItemJson.value = '';
        
        // Limpar sele├º├úo de Fertipar
        $('.fertipar-radio').prop('checked', false);
        $('.fertipar-item-card').removeClass('selected');
    }

    function disableFertiparCard(protocolo) {
        const card = selectedFertiparItemsDiv.querySelector(`.fertipar-item-card[data-protocolo="${protocolo}"]`);
        if (card) {
            card.classList.add('agendado'); // Adiciona classe para estilo de bloqueio/riscado
            const radio = card.querySelector('.fertipar-radio');
            if (radio) {
                radio.disabled = true; // Desabilita o radio button
            }
            // Opcional: Adicionar texto riscado. Pode ser feito via CSS na classe 'agendado'
            const label = card.querySelector('.form-check-label');
            if (label) {
                label.style.textDecoration = 'line-through';
            }
        }
    }

    // fetchAgendasProcessarData n├úo ├® mais usado da mesma forma, mas mantido por enquanto
    function fetchAgendasProcessarData() { 
        return fetch('/api/agendas_processar', { headers: getAuthHeaders() })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Erro HTTP: ${response.status}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error('Erro ao buscar agendas para processar:', error); 
                showAlert('Falha ao carregar agendas para processar. Verifique sua conex├úo ou autentica├º├úo.', 'danger'); 
                return []; 
            });
    }

    // Nova fun├º├úo para buscar agendas, agora com filtros de ano e m├¬s
    async function fetchAgendasData(year, month) {
        let url = `/api/agendas_agendadas?year=${year}&month=${month}`;
        try {
            const response = await fetch(url, { headers: getAuthHeaders() });
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Erro ao buscar agendas:', error);
            showAlert('Falha ao carregar agendas. Verifique sua conex├úo ou autentica├º├úo.', 'danger');
            return [];
        }
    }

    // Nova fun├º├úo para renderizar as agendas no DOM
    async function renderAgendas(agendas) { 
        if (!agendasEmEsperaBody) return; // Se o elemento n├úo existe na p├ígina, n├úo faz nada
        agendasEmEsperaBody.innerHTML = ''; // Limpa o conte├║do atual da tabela

        if (agendas.length === 0) {
            agendasEmEsperaBody.innerHTML = '<tr><td colspan="9" class="text-center">Nenhuma agenda encontrada para o per├¡odo selecionado.</td></tr>';
            return;
        }

        for (const agenda of agendas) { 
            const row = agendasEmEsperaBody.insertRow();
            
            // L├│gica de Status e Cor
            let statusBadgeClass = 'badge-secondary'; // Cor padr├úo
            let rowClass = ''; // Classe da linha
            const status = agenda.status ? agenda.status.toLowerCase() : '';

            if (status === 'agendado') {
                statusBadgeClass = 'badge-success';
            } else if (status.includes('erro')) { 
                statusBadgeClass = 'badge-danger';
                rowClass = 'table-danger'; // Vermelho para a linha toda
            } else if (['processando', 'monitorando', 'aprovado_e_agendando'].some(s => status.includes(s))) {
                statusBadgeClass = 'badge-info';
            } else if (status === 'cancelado' || status === 'recusado') { 
                statusBadgeClass = 'badge-warning';
                if (status === 'recusado') {
                    rowClass = 'table-warning'; // Amarelo para a linha toda
                }
            } else if (status === 'espera') {
                statusBadgeClass = 'badge-primary';
            }

            // Formata as informa├º├Áes do caminh├úo
            let caminhaoDisplay = agenda.caminhao.placa || 'N/A';
            if (agenda.caminhao.tipo_carroceria) {
                caminhaoDisplay += ` - ${agenda.caminhao.tipo_carroceria}`;
            }
            if (agenda.caminhao.reboques && agenda.caminhao.reboques.length > 0) {
                caminhaoDisplay += ` | ${agenda.caminhao.reboques.join(', ')}`;
            }

            row.className = rowClass; // Aplica a classe de cor na linha
            row.innerHTML = `
                <td>${agenda.data_agendamento}</td>
                <td>${agenda.motorista}</td>
                <td>${caminhaoDisplay}</td>
                <td>${agenda.protocolo}</td>
                <td>${agenda.pedido}</td>
                <td>${agenda.destino}</td>
                <td>${agenda.carga_solicitada !== null ? agenda.carga_solicitada : 'N/A'}</td>
                <td><span class="badge ${statusBadgeClass}">${(agenda.status || '').toUpperCase()}</span></td>
                <td>
                    <button class="btn btn-sm btn-info btn-executar-agenda" title="Executar" data-id="${agenda.id}" ${status !== 'espera' ? 'disabled' : ''}><i class="fas fa-play"></i></button>
                    <button class="btn btn-sm btn-danger btn-cancelar-agenda" title="Cancelar" data-id="${agenda.id}" ${status !== 'espera' ? 'disabled' : ''}><i class="fas fa-times"></i></button>
                </td>
            `;

            const executeButton = row.querySelector('.btn-executar-agenda');
            if (executeButton) {
                executeButton.addEventListener('click', async () => {
                    await executeAgenda(agenda.id);
                });
            }
        }
    }

    async function executeAgendaDevMode(agendaId) {
        console.log(`[Dev Mode] Tentando executar agenda ID: ${agendaId}`);
        showAlert(`Enviando agenda ID ${agendaId} para processamento em modo DEV (apenas log no console do Flask)...`, 'info', true);
        try {
            const response = await fetch(`/api/agendas/execute_dev_mode/${agendaId}`, {
                method: 'POST',
                headers: getAuthHeaders(),
            });

            if (response.status === 401) {
                showAlert('Sess├úo expirada ou inv├ílida. Por favor, fa├ºa login novamente.', 'danger');
                return;
            }

            const result = await response.json();

            if (result.success) {
                showAlert(result.message || 'Comando RPA (DEV) executado com sucesso!', 'success');
                console.log(`[Dev Mode] Resposta do Flask: ${result.message}`);
            } else {
                showAlert(result.message || 'Ocorreu um erro durante a execu├º├úo do RPA (DEV).', 'danger', true);
                console.error(`[Dev Mode] Erro do Flask: ${result.message}`);
            }
        } catch (error) {
            console.error('[Dev Mode] Erro ao chamar executeAgendaDevMode:', error);
            showAlert('Erro de conex├úo com o servidor ao tentar executar o RPA (DEV). Verifique sua rede e o status do servidor.', 'danger', true);
        }
        // N├úo ├® necess├írio loadAndRenderAgendas aqui, pois ├® apenas um log no modo dev
    }


    // --- L├│gica Principal ---

    function showInfoToast(title, data) {
        let content = '';
        for (const [key, value] of Object.entries(data)) {
            if (value) {
                content += `<strong>${key}:</strong> ${value}<br>`;
            }
        }
        if (content) {
            toastr.success(content, title);
        }
    }

    async function executeRpaTask(agenda) {
        try {
            const response = await fetch(`/api/agendas/execute/${agenda.id}`, {
                method: 'POST',
                headers: getAuthHeaders(),
            });

            const result = await response.json();
            return result; // Retorna o resultado JSON bruto do backend
        } catch (error) {
            console.error('Erro de conex├úo ao chamar executeRpaTask:', error);
            // Retorna um objeto de erro para que o chamador possa lidar com ele
            return { success: false, message: 'Erro de conex├úo com o servidor ao tentar executar o RPA. Verifique sua rede e o status do servidor.', user_facing_message: 'Erro de conex├úo com o servidor.' };
        }
    }

    const btnLigarRoboDev = document.getElementById('btnLigarRoboDev');
    if (btnLigarRoboDev) {
        btnLigarRoboDev.addEventListener('click', async function() {
            const agendaId = prompt("Por favor, insira o ID da agenda para executar em modo DEV:");
            if (agendaId) {
                await executeAgendaDevMode(parseInt(agendaId));
            } else {
                showAlert("ID da agenda n├úo fornecido. Opera├º├úo cancelada.", 'warning');
            }
        });
    }


    // 1. Atualizar informa├º├Áes e campos ocultos na sele├º├úo
    if (motoristaSelect) {
        motoristaSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const motoristaId = selectedOption.value;
            hiddenMotoristaId.value = motoristaId;
            
            if (motoristaId) {
                const nome = selectedOption.text;
                const cpf = selectedOption.getAttribute('data-cpf');
                const telefone = selectedOption.getAttribute('data-telefone');
                
                motoristaInfoDiv.innerHTML = `
                    <div class="toast-like-info">
                        <strong>Motorista:</strong> ${nome}<br>
                        <strong>CPF:</strong> ${cpf || 'N/A'}<br>
                        <strong>Telefone:</strong> ${telefone || 'N/A'}
                    </div>
                `;
            } else {
                motoristaInfoDiv.innerHTML = '';
            }
        });
    }

    if (caminhaoSelect) {
        caminhaoSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const caminhaoId = selectedOption.value;
            hiddenCaminhaoId.value = caminhaoId;

            if (caminhaoId) {
                const placa = selectedOption.getAttribute('data-placa');
                const uf = selectedOption.getAttribute('data-uf');
                const tipoCarroceria = selectedOption.getAttribute('data-tipo-carroceria');
                const reboque1 = selectedOption.getAttribute('data-reboque1');
                const uf1 = selectedOption.getAttribute('data-uf1');
                const reboque2 = selectedOption.getAttribute('data-reboque2');
                const uf2 = selectedOption.getAttribute('data-uf2');
                const reboque3 = selectedOption.getAttribute('data-reboque3');
                const uf3 = selectedOption.getAttribute('data-uf3');

                let reboquesInfo = [];
                if (reboque1) reboquesInfo.push(`${reboque1} (${uf1 || ''})`);
                if (reboque2) reboquesInfo.push(`${reboque2} (${uf2 || ''})`);
                if (reboque3) reboquesInfo.push(`${reboque3} (${uf3 || ''})`);

                caminhaoInfoDiv.innerHTML = `
                    <div class="toast-like-info">
                        <strong>Placa:</strong> ${placa} (${uf || 'N/A'})<br>
                        <strong>Carroceria:</strong> ${tipoCarroceria || 'N/A'}<br>
                        ${reboquesInfo.length > 0 ? `<strong>Reboques:</strong> ${reboquesInfo.join(', ')}` : ''}
                    </div>
                `;
            } else {
                caminhaoInfoDiv.innerHTML = '';
            }
        });
    }

    $(selectedFertiparItemsDiv).on('change', '.fertipar-radio', function() {
        if (this.checked) {
            hiddenFertiparItemJson.value = this.getAttribute('data-item');
            $('.fertipar-item-card').removeClass('selected');
            $(this).closest('.fertipar-item-card').addClass('selected');
        }
    });

    // 2. L├│gica do Modal Fertipar
    function updateLastReadStatus() {
        const lastRead = localStorage.getItem(LAST_READ_KEY);
        let needsUpdate = false;

        if (lastRead) {
            const lastReadDate = new Date(lastRead);
            const now = new Date();
            const diff = now.getTime() - lastReadDate.getTime();
            let statusText = `├Ültima leitura: ${formatDateTime(lastReadDate)}`;
            if (diff > FIVE_MINUTES_MS) {
                statusText += ' <span class="text-danger font-weight-bold">(Precisa atualizar!)</span>';
                needsUpdate = true;
            }
            lastReadStatus.innerHTML = statusText;
        } else {
            lastReadStatus.textContent = 'Nenhuma leitura anterior.';
            needsUpdate = true;
        }

        $('#fertiparDataTableBody input[type="checkbox"]').prop('disabled', needsUpdate);
        $('#fertiparModal .filter-input').prop('disabled', needsUpdate);
        if (btnSaveFertipar) $(btnSaveFertipar).prop('disabled', needsUpdate);
    }

    function populateFertiparTable(data, agendasEmEspera = []) {
        fertiparDataTableBody.innerHTML = '';
        const existingAgendas = new Set(agendasEmEspera.map(a => `${a.protocolo}-${a.pedido}`));

        if (data && data.length > 0) {
            data.forEach((item, index) => {
                const isItemAgendado = existingAgendas.has(`${item.Protocolo}-${item.Pedido}`);
                const isItemRecusado = item['Situação'] === 'RECUSADO'; // Nova verificação para 'RECUSADO'
                const row = fertiparDataTableBody.insertRow();
                row.setAttribute('data-item', JSON.stringify(item));
                row.classList.add('fertipar-main-row');

                if (isItemAgendado) {
                    row.classList.add('agendado-row');
                } else if (isItemRecusado) {
                    row.classList.add('recusado-row'); // Adiciona a classe para a linha recusada
                }

                row.setAttribute('data-protocolo', item.Protocolo);
                row.setAttribute('data-pedido', item.Pedido);
                row.innerHTML = `
                    <td><button class="btn btn-sm btn-outline-secondary btn-toggle-subgrid"><i class="fas fa-plus"></i></button></td>
                    <td><input type="checkbox" name="selecionar_item_modal" value="${index}" ${isItemAgendado || isItemRecusado ? 'disabled' : ''}></td>
                    <td><strong>${item.Protocolo || ''}</strong></td>
                    <td><strong>${item.Pedido || ''}</strong></td>
                    <td>${item.Data || ''}</td>
                    <td>${item['Situação'] || ''}</td>
                    <td>${item.Destino || ''}</td>
                    <td><strong>${item['Qtde.'] || ''}</strong></td>
                    <td>${item.Embalagem || ''}</td>
                    <td>${item['Cota├º├úo'] || ''}</td>
                    <td>${item['Observa├º├úo Cota├º├úo'] || ''}</td>
                `;

                const subgridRow = fertiparDataTableBody.insertRow();
                subgridRow.classList.add('fertipar-subgrid-row');
                if (isItemAgendado) {
                    subgridRow.classList.add('agendado-row');
                } else if (isItemRecusado) {
                    subgridRow.classList.add('recusado-row'); // Adiciona a classe para o subgrid recusado
                }
                subgridRow.style.display = 'none';
                subgridRow.innerHTML = `
                    <td colspan="11">
                        <div class="subgrid-content p-2 shadow-sm" style="width: 100%; display: flex; padding: 10px; background-color: #f8f9fa; border: 1px solid #e9ecef;">
                            <div class="form-group col-md-3 custom-select-container">
                                <label for="motorista-subgrid-input-${index}">Motorista</label>
                                <input type="text" class="form-control form-control-sm custom-select-input motorista-subgrid-input" id="motorista-subgrid-input-${index}" placeholder="Selecione ou digite" data-id="" ${(isItemAgendado || isItemRecusado) ? 'disabled' : ''}>
                                <div class="custom-select-dropdown" id="motorista-subgrid-dropdown-${index}"><ul class="list-group list-group-flush custom-select-list"></ul></div>
                                <div class="selected-item-details mt-1"></div>
                            </div>
                            <div class="form-group col-md-3 custom-select-container">
                                <label for="caminhao-subgrid-input-${index}">Caminh├úo</label>
                                <input type="text" class="form-control form-control-sm custom-select-input caminhao-subgrid-input" id="caminhao-subgrid-input-${index}" placeholder="Selecione ou digite" data-id="" ${(isItemAgendado || isItemRecusado) ? 'disabled' : ''}>
                                <div class="custom-select-dropdown" id="caminhao-subgrid-dropdown-${index}"><ul class="list-group list-group-flush custom-select-list"></ul></div>
                                <div class="selected-item-details mt-1"></div>
                            </div>
                            <div class="form-group col-md-2">
                                <label for="carga-solicitada-input-${index}">Carga Sol.</label>
                                <input type="number" step="0.01" class="form-control form-control-sm carga-solicitada-input" id="carga-solicitada-input-${index}" placeholder="Ton" ${(isItemAgendado || isItemRecusado) ? 'disabled' : ''}>
                            </div>
                            <div class="form-group col-md-2">
                                <label>Status</label>
                                <input type="text" class="form-control form-control-sm subgrid-status" value="${isItemAgendado ? 'Agendado!' : (isItemRecusado ? 'Recusado' : '')}" readonly>
                            </div>
                            <div class="form-group col-md-1">
                                <label>&nbsp;</label>
                                <button type="button" class="btn btn-success btn-sm btn-block btn-agendar-subgrid" ${(isItemAgendado || isItemRecusado) ? 'disabled' : ''}>
                                    Agendar
                                </button>
                            </div>
                        </div>
                    </td>
                `;
            });
        } else {
            fertiparDataTableBody.innerHTML = '<tr><td colspan="11" class="text-center">Nenhum dado encontrado.</td></tr>';
        }
        updateLastReadStatus();
    }

    function displaySelectedFertiparItems(items) {
        selectedFertiparItemsDiv.innerHTML = '';
        if (items.length === 0) return;

        const heading = '<h5>Itens Fertipar Selecionados</h5>';
        const cardContainer = $('<div class="d-flex flex-wrap"></div>');

        fetchAgendasProcessarData().then(agendasEmEspera => {
            const existingAgendas = new Set(agendasEmEspera.map(a => `${a.protocolo}-${a.pedido}`));

            items.forEach((item, index) => {
                const itemIdentifier = `${item.Protocolo}-${item.Pedido}`;
                const isItemAgendado = existingAgendas.has(itemIdentifier);
                
                const cardHtml = `
                    <div class="card fertipar-item-card ${isItemAgendado ? 'agendado' : ''}" data-protocolo="${item.Protocolo}">
                        <div class="card-body p-2">
                            <div class="form-check">
                                <input class="form-check-input fertipar-radio" type="radio" name="selectedFertipar" id="fertiparRadio${index}" value="${item.Protocolo}" data-item='${JSON.stringify(item)}' ${isItemAgendado ? 'disabled' : ''}>
                                <label class="form-check-label" for="fertiparRadio${index}">
                                    <strong>Protocolo:</strong> ${item.Protocolo || ''}<br>
                                    <strong>Pedido:</strong> ${item.Pedido || ''}<br>
                                    <strong>Destino:</strong> ${item.Destino || ''}
                                </label>
                            </div>
                        </div>
                    </div>`;
                cardContainer.append(cardHtml);
            });
            $(selectedFertiparItemsDiv).append(heading).append(cardContainer);
        });
    }

    if (btnLerDadosFertipar) {
        btnLerDadosFertipar.addEventListener('click', async function() {
            btnLerDadosFertipar.disabled = true;
            lastReadStatus.innerHTML = '<span class="text-info">Lendo dados...</span>';
            fertiparDataTableBody.innerHTML = '<tr><td colspan="11" class="text-center"><div class="spinner-border text-primary" role="status"><span class="sr-only">Carregando...</span></div></td></tr>';

            try {
                const [fertiparResponse, agendasEmEspera] = await Promise.all([
                    fetch('/api/scrape_fertipar_data', { headers: getAuthHeaders() }),
                    fetchAgendasProcessarData()
                ]);

                if (fertiparResponse.status === 401) {
                    showAlert('Sess├úo expirada ou inv├ílida. Por favor, fa├ºa login novamente.', 'danger');
                    lastReadStatus.innerHTML = '<span class="text-danger">N├úo autorizado.</span>';
                    populateFertiparTable([], agendasEmEspera); // Pass empty data, but still pass agendasEmEspera
                    return;
                }

                const result = await fertiparResponse.json();

                if (result.success) {
                    if (result.data.length > 0) {
                        populateFertiparTable(result.data, agendasEmEspera);
                        showAlert('Dados Fertipar lidos com sucesso!', 'success');
                    } else {
                        populateFertiparTable([], agendasEmEspera);
                        showAlert(result.message || 'N├úo h├í dados de cota├º├úo dispon├¡veis no momento.', 'info');
                    }
                    localStorage.setItem(LAST_READ_KEY, new Date().toISOString());
                    updateLastReadStatus();
                } else {
                    populateFertiparTable([], agendasEmEspera);
                    showAlert(result.message || 'Ocorreu um erro desconhecido ao buscar os dados.', 'danger');
                    lastReadStatus.innerHTML = '<span class="text-danger">Erro na leitura.</span>';
                }
            } catch (error) {
                console.error('Erro ao ler dados Fertipar:', error);
                populateFertiparTable([], []); // Pass empty arrays in case of connection error
                showAlert('Erro de conex├úo ao tentar buscar os dados da Fertipar.', 'danger');
                lastReadStatus.innerHTML = '<span class="text-danger">Falha na conex├úo.</span>';
            } finally {
                btnLerDadosFertipar.disabled = false;
            }
        });
    }

    if (fertiparModal) {
        $(fertiparModal).on('show.bs.modal', () => updateLastReadStatus());
        
        // Listener para o novo bot├úo de dados fict├¡cios
        $('#btnDadosFicticios').on('click', async function() {
            const fictitiousData = [
                { "Protocolo": "346562", "Pedido": "928580", "Data": "13/01/2026 10:21", "Situa├º├úo": "APROVADO", "Destino": "BELA VISTA -MS", "Qtde.": "46.0", "Embalagem": "BIG-BAG", "Cota├º├úo": "290.0", "Observa├º├úo Cota├º├úo": "" },
                { "Protocolo": "346512", "Pedido": "939686", "Data": "09/01/2026 16:32", "Situa├º├úo": "APROVADO", "Destino": "COSTA RICA - MS", "Qtde.": "97.5", "Embalagem": "BIG-BAG", "Cota├º├úo": "290.0", "Observa├º├úo Cota├º├úo": "MINIMO MOTO RODO 247,64" },
                { "Protocolo": "346445", "Pedido": "928580", "Data": "07/01/2026 13:27", "Situa├º├úo": "APROVADO", "Destino": "BONITO-MS", "Qtde.": "48.0", "Embalagem": "BIG-BAG", "Cota├º├úo": "280.0", "Observa├º├úo Cota├º├úo": "MINIMO MOTO RODO 256,47" },
                { "Protocolo": "346443", "Pedido": "928580", "Data": "07/01/2026 14:08", "Situa├º├úo": "APROVADO", "Destino": "BONITO-MS", "Qtde.": "70.0", "Embalagem": "BIG-BAG", "Cota├º├úo": "335.0", "Observa├º├úo Cota├º├úo": "MINIMO MOTO BITREM 301,49" },
                { "Protocolo": "346442", "Pedido": "928580", "Data": "07/01/2026 14:10", "Situa├º├úo": "APROVADO", "Destino": "BONITO-MS", "Qtde.": "2.0", "Embalagem": "BIG-BAG", "Cota├º├úo": "335.0", "Observa├º├úo Cota├º├úo": "MINIMO MOTO BITREM 301,49" },
                { "Protocolo": "346419", "Pedido": "938069", "Data": "05/01/2026 11:52", "Situa├º├úo": "APROVADO", "Destino": "PARAISO DAS AGUAS - MS", "Qtde.": "48.0", "Embalagem": "BIG-BAG", "Cota├º├úo": "320.0", "Observa├º├úo Cota├º├úo": "MINIMO MOTO RODO 228,45" },
                { "Protocolo": "346405", "Pedido": "928580", "Data": "13/01/2026 13:05", "Situa├º├úo": "APROVADO", "Destino": "ANASTACIO - MS", "Qtde.": "35.0", "Embalagem": "BIG-BAG", "Cota├º├úo": "335.0", "Observa├º├úo Cota├º├úo": "MINIMO MOTO 300,0" },
                { "Protocolo": "346387", "Pedido": "926074", "Data": "04/12/2025 16:10", "Situa├º├úo": "APROVADO", "Destino": "ALCINOPOLIS - MS", "Qtde.": "49.0", "Embalagem": "BIG-BAG", "Cota├º├úo": "300.0", "Observa├º├úo Cota├º├úo": "MINIMO MOTO RODO 279,88" },
                { "Protocolo": "346215", "Pedido": "939421", "Data": "07/01/2026 10:21", "Situa├º├úo": "APROVADO", "Destino": "ROSANA-SP", "Qtde.": "72.0", "Embalagem": "BIG-BAG", "Cota├º├úo": "240.0", "Observa├º├úo Cota├º├úo": "MINIMO MOTO BITREM 185,30" },
                { "Protocolo": "346203", "Pedido": "940277", "Data": "12/01/2026 18:30", "Situa├º├úo": "APROVADO", "Destino": "ESPIGAO DO OESTE - RO", "Qtde.": "16.0", "Embalagem": "BIG-BAG", "Cota├º├úo": "620.0", "Observa├º├úo Cota├º├úo": "" }
            ];
            
            const agendasEmEspera = await fetchAgendasProcessarData(); // Fetch agendas here
            populateFertiparTable(fictitiousData, agendasEmEspera);
            toastr.info('Dados fict├¡cios carregados na tabela.');

            if(lastReadStatus) {
                lastReadStatus.innerHTML = '<span class="text-warning font-weight-bold">Exibindo dados fict├¡cios.</span>';
            }
            
            $('#fertiparDataTableBody input[type="checkbox"]').prop('disabled', false);
            $('#fertiparModal .filter-input').prop('disabled', false);
            if (btnSaveFertipar) $(btnSaveFertipar).prop('disabled', false);
        });

        // L├│gica de filtragem
        $(fertiparModal).on('keyup', '.filter-input', function() {
            const columnIndex = $(this).parent().index(); 
            const filterValue = $(this).val().toLowerCase();

            $('#fertiparDataTableBody tr.fertipar-main-row').each(function() {
                const row = $(this);
                const cell = row.find('td').eq(columnIndex);
                const cellText = cell.text().toLowerCase();
                const subgridRow = row.next('.fertipar-subgrid-row');

                if (cellText.includes(filterValue)) {
                    row.show();
                    // N├úo mexer no status do subgrid aqui para manter o estado (aberto/fechado)
                } else {
                    row.hide();
                    if(subgridRow.length > 0) {
                        subgridRow.hide(); // Esconder subgrid associado se a linha principal for escondida
                    }
                }
            });
        });



        // Listener para o bot├úo Limpar Agendas
        $('#btnLimparAgendas').on('click', async function() {
            if (!confirm('Tem certeza que deseja limpar TODOS os agendamentos em espera? Esta a├º├úo ├® irrevers├¡vel.')) {
                return;
            }

            toastr.info('Limpando agendamentos...');
            try {
                const response = await fetch('/api/agendas/clear', {
                    method: 'POST',
                    headers: getAuthHeaders(),
                });

                const result = await response.json();

                if (result.success) {
                    showAlert(result.message || 'Agendamentos limpos com sucesso!', 'success');
                    loadAndRenderAgendas();
                } else {
                    showAlert(result.message || 'Ocorreu um erro ao limpar os agendamentos.', 'danger');
                }
            } catch (error) {
                console.error('Erro ao limpar agendamentos:', error);
                showAlert('Erro de conex├úo ao tentar limpar os agendamentos.', 'danger');
            }
        });
    }

    if (formGerarAgenda) {
        formGerarAgenda.addEventListener('submit', async function(event) {
            event.preventDefault(); // Previne o refresh da p├ígina

            const pesoCarregarInput = document.getElementById('peso-carregar');
            const pesoCarregar = parseFloat(pesoCarregarInput.value);

            if (!pesoCarregar || pesoCarregar <= 0) {
                // showAlert('O campo "Peso a Carregar" ├® obrigat├│rio e deve ser maior que zero.', 'warning'); // Removido toast
                pesoCarregarInput.focus();
                return;
            }

            // Coleta os dados do formul├írio
            const motoristaId = hiddenMotoristaId.value;
            const caminhaoId = hiddenCaminhaoId.value;
            const fertiparItemJson = hiddenFertiparItemJson.value;
            
            if (!motoristaId || !caminhaoId || !fertiparItemJson) {
                // showAlert('Por favor, selecione um motorista, um caminh├úo e um item Fertipar.', 'warning'); // Removido toast
                return;
            }

            const formData = {
                motorista_id: motoristaId,
                caminhao_id: caminhaoId,
                fertipar_item: JSON.parse(fertiparItemJson), // Parsear a string JSON para um objeto
                peso_carregar: parseFloat(pesoCarregar) || 0 // Adiciona o peso a carregar, convertendo para float
            };

            try {
                const response = await fetch('/agendar', {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify(formData),
                });

                if (response.status === 401) {
                    // showAlert('Sess├úo expirada ou inv├ílida. Por favor, fa├ºa login novamente.', 'danger'); // Removido toast
                    return;
                }

                const result = await response.json();

                if (result.success) {
                    showAlert('Agenda criada com sucesso!', 'success', true);
                    
                    const fertiparItem = JSON.parse(fertiparItemJson);
                    if (fertiparItem && fertiparItem.Protocolo) {
                        disableFertiparCard(fertiparItem.Protocolo);
                    }
                    
                    showAlert(`Executando RPA para Protocolo ${fertiparItem.Protocolo}...`, 'info', true);
                    const rpaResult = await executeRpaTask(result.agenda); // Chama a fun├º├úo refatorada

                    if (rpaResult.success) {
                        showAlert(rpaResult.message || 'Comando RPA executado com sucesso!', 'success');
                    } else {
                        const displayMessage = rpaResult.user_facing_message || rpaResult.message || 'Ocorreu um erro durante a execu├º├úo do RPA.';
                        showAlert(displayMessage, 'danger', true);
                    }
                    
                    clearAgendaForm(); // Limpa os campos

                    // Ativa a aba "Gerar Agenda" e recarrega a lista
                    $('[href="#gerar-agenda"]').tab('show'); 
                    loadAndRenderAgendas();
                } else {
                    showAlert(result.message || 'Erro ao criar agenda: Erro desconhecido', 'danger');
                }
            } catch (error) {
                console.error('Erro ao agendar:', error);
                // Removido toast de erro de conex├úo para simplificar a UI
                // showAlert('Erro de conex├úo ao agendar.', 'danger');
            }
        });
    }

    // --- L├│gica de Agendamento (Subgrid) ---
    async function startStatusMonitoring(protocolo, pedido) {
        showAlert(`Iniciando monitoramento de status para Protocolo ${protocolo}...`, 'info', true);
    
        try {
            const response = await fetch('/api/agendas/monitor_status', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ protocolo: protocolo, pedido: pedido }),
            });
    
            const result = await response.json();
    
            if (result.success) {
                showAlert(`Protocolo ${protocolo}: APROVADO! Iniciando agendamento...`, 'success', true);
                updateTableRowStatus(protocolo, pedido, 'aprovado_e_agendando'); // A new temporary status
                return true; // Indicate success to proceed with scheduling
            } else {
                const finalStatus = result.status || 'erro'; // 'RECUSADO' or 'ERRO'
                const message = result.message || `O monitoramento falhou ou o item foi recusado.`;
                showAlert(`Protocolo ${protocolo}: ${finalStatus}. ${message}`, 'danger', true);
                updateTableRowStatus(protocolo, pedido, finalStatus.toLowerCase());
                return false; // Indicate failure
            }
        } catch (error) {
            console.error('Erro de conex├úo durante o monitoramento de status:', error);
            showAlert('Erro de conex├úo com o servidor durante o monitoramento. Verifique o console.', 'danger', true);
            updateTableRowStatus(protocolo, pedido, 'erro');
            return false; // Indicate failure
        }
    }

    async function agendarViaSubgrid(button) {
        const subgridContent = $(button).closest('.subgrid-content');
        const mainRow = subgridContent.closest('.fertipar-subgrid-row').prev('.fertipar-main-row');
        const statusInput = subgridContent.find('.subgrid-status');
        
        const motoristaId = subgridContent.find('.motorista-subgrid-input').attr('data-id');
        const caminhaoId = subgridContent.find('.caminhao-subgrid-input').attr('data-id');
        const cargaSolicitada = subgridContent.find('.carga-solicitada-input').val();
        const fertiparItem = JSON.parse(mainRow.attr('data-item'));
        const protocolo = fertiparItem.Protocolo;
        const pedido = fertiparItem.Pedido;

        if (!motoristaId || !caminhaoId || !fertiparItem) {
            // showAlert('Por favor, selecione um motorista e um caminh├úo para agendar.', 'warning'); // Removido toast
            return;
        }
        
        const cargaSolicitadaFloat = parseFloat(cargaSolicitada);
        if (isNaN(cargaSolicitadaFloat) || cargaSolicitadaFloat <= 0) {
            // showAlert('O campo "Carga Solicitada" ├® obrigat├│rio e deve ser maior que zero.', 'warning'); // Removido toast
            subgridContent.find('.carga-solicitada-input').focus();
            return;
        }

        statusInput.val('Agendando...');
        button.disabled = true;

        const formData = {
            motorista_id: motoristaId,
            caminhao_id: caminhaoId,
            fertipar_item: fertiparItem,
            carga_solicitada: parseFloat(cargaSolicitada) || null
        };

        try {
            const createAgendaResponse = await fetch('/agendar', {
                method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(formData)
            });
            const createResult = await createAgendaResponse.json();

            if (createResult.success) {
                showAlert('Agenda criada no sistema, iniciando monitoramento no site externo...', 'info', true);
                updateTableRowStatus(protocolo, pedido, 'monitorando'); // New visual status
    
                // **NEW LOGIC: Start the monitoring process**
                const isApproved = await startStatusMonitoring(protocolo, pedido);
    
                if (isApproved) {
                    // If approved, THEN execute the original RPA to schedule
                    showAlert(`Status APROVADO. Executando agendamento final para Protocolo ${protocolo}...`, 'info', true);
                    const rpaResult = await executeRpaTask(createResult.agenda); // executeRpaTask already exists
    
                    if (rpaResult.success) {
                        showAlert(rpaResult.message || 'Comando RPA executado com sucesso!', 'success');
                        updateTableRowStatus(protocolo, pedido, 'agendado');
                    } else {
                        const displayMessage = rpaResult.user_facing_message || rpaResult.message || 'Ocorreu um erro durante a execu├º├úo do RPA.';
                        showAlert(displayMessage, 'danger', true);
                        updateTableRowStatus(protocolo, pedido, 'erro');
                    }
                    loadAndRenderAgendas();
                    subgridContent.find('input, button').prop('disabled', true);
    
                } else {
                    // If not approved (rejected or error during monitoring), stop here.
                    // The status has already been updated by startStatusMonitoring.
                    button.disabled = false; // Maybe re-enable the button? Or keep it disabled.
                }
    
            } else {
                showAlert(createResult.message || 'Erro ao criar agenda no sistema.', 'danger');
                statusInput.val('Erro local!');
                updateTableRowStatus(protocolo, pedido, 'erro');
                button.disabled = false;
            }
        } catch (error) {
            console.error('Erro ao agendar via subgrid:', error);
            showAlert('Erro de conex├úo ao agendar. Verifique sua rede e o status do servidor.', 'danger');
            statusInput.val('Falha na conex├úo');
            updateTableRowStatus(protocolo, pedido, 'erro'); // Atualiza visualmente para erro
            button.disabled = false;
        }
    }


    if (fertiparDataTableBody) {
        // Listener para o bot├úo de agendamento do subgrid
        fertiparDataTableBody.addEventListener('click', function(event) {
            const agendarButton = event.target.closest('.btn-agendar-subgrid');
            if (agendarButton) {
                agendarViaSubgrid(agendarButton);
            }
        });

        // Listener para valida├º├úo do campo de carga solicitada
        fertiparDataTableBody.addEventListener('input', function(event) {
            const cargaInput = event.target.closest('.carga-solicitada-input');
            if (cargaInput) {
                const mainRow = $(cargaInput).closest('.fertipar-subgrid-row').prev('.fertipar-main-row');
                const itemData = JSON.parse(mainRow.attr('data-item'));
                const qtdeDisponivel = parseFloat(itemData['Qtde.']);
                const cargaDigitada = parseFloat(cargaInput.value);

                if (!isNaN(cargaDigitada) && !isNaN(qtdeDisponivel) && cargaDigitada > qtdeDisponivel) {
                    toastr.warning(`A carga solicitada (${cargaDigitada} ton) n├úo pode ser maior que a quantidade dispon├¡vel (${qtdeDisponivel} ton).`, 'Valor Inv├ílido');
                    cargaInput.value = qtdeDisponivel;
                }
            }
        });
    }

    const btnAgendarTodos = document.getElementById('btnAgendarTodos');
    if (btnAgendarTodos) {
        btnAgendarTodos.addEventListener('click', async function() {
            try {
                showAlert('Iniciando o processamento de "Agendar Todos". Verifique o console do navegador para os detalhes.', 'info'); // Alerta moderno
                
                const agendas = await fetchAgendasProcessarData();
                if (agendas.length === 0) {
                    showAlert('Nenhuma agenda em espera para agendar.', 'info');
                    return;
                }

                // Imprime os dados formatados em JSON no console do navegador
                console.log('Dados das Agendas em Espera (JSON):');
                console.log(JSON.stringify(agendas, null, 2));
                
                showAlert(`Foram encontrados ${agendas.length} agendas em espera. Dados impressos no console.`, 'success');

            } catch (error) {
                console.error('Erro ao agendar todos:', error);
                showAlert('Erro ao processar as agendas em espera. Verifique o console para mais detalhes.', 'danger');
            }
        });
    }

    // --- Nova fun├º├úo para exclus├úo de agenda ---
    async function deleteAgenda(agendaId) {
        if (!confirm('Tem certeza que deseja cancelar esta agenda?')) {
            return;
        }

        try {
            const response = await fetch(`/api/agenda/${agendaId}`, {
                method: 'DELETE',
                headers: getAuthHeaders(),
            });

            if (response.status === 401) {
                showAlert('Sess├úo expirada ou inv├ílida. Por favor, fa├ºa login novamente.', 'danger');
                return;
            }

            const result = await response.json();

            if (result.success) {
                showAlert('Agenda cancelada com sucesso!', 'success');
                loadAndRenderAgendas(); // Recarregar a lista
            } else {
                showAlert('Erro ao cancelar agenda: ' + (result.message || 'Erro desconhecido'), 'danger');
            }
        } catch (error) {
            console.error('Erro de conex├úo ao cancelar agenda:', error);
            showAlert('Erro de conex├úo ao cancelar agenda.', 'danger');
        }
    }

    // --- Event listener para os bot├Áes de cancelar ---
    if (agendasEmEsperaBody) {
        agendasEmEsperaBody.addEventListener('click', function(event) {
            const target = event.target.closest('.btn-cancelar-agenda');
            if (target) {
                const agendaId = target.getAttribute('data-id');
                if (agendaId) {
                    deleteAgenda(agendaId);
                }
            }
        });
    }

    // --- L├│gica para expandir/recolher subgrid no Modal Fertipar ---
    $(document).on('click', '.btn-toggle-subgrid', function() {
        const mainRow = $(this).closest('.fertipar-main-row');
        const subgridRow = mainRow.next('.fertipar-subgrid-row');

        if (subgridRow.length) {
            subgridRow.toggle(); // Alterna a visibilidade do subgrid
            const icon = $(this).find('i');
            icon.toggleClass('fa-plus fa-minus'); // Alterna o ├¡cone
        }
    });
    
    // --- L├│gica de busca e renderiza├º├úo dos selects customizados ---
    let cachedMotoristas = [];
    let cachedCaminhoes = [];

    async function fetchMotoristas() {
        if (cachedMotoristas.length > 0) {
            return cachedMotoristas;
        }
        try {
            const response = await fetch('/api/motoristas'); // N├úo requer autentica├º├úo
            const data = await response.json();
            cachedMotoristas = data;
            return data;
        } catch (error) {
            console.error('Erro ao buscar motoristas:', error);
            return [];
        }
    }

    async function fetchCaminhoes() {
        if (cachedCaminhoes.length > 0) {
            return cachedCaminhoes;
        }
        try {
            const response = await fetch('/api/caminhoes'); // N├úo requer autentica├º├úo
            const data = await response.json();
            cachedCaminhoes = data;
            return data;
        } catch (error) {
            console.error('Erro ao buscar caminh├Áes:', error);
            return [];
        }
    }

    function renderSelectOptions(inputElement, dropdownElement, items, displayKey, idKey) {
        const ul = dropdownElement.querySelector('.custom-select-list');
        ul.innerHTML = '';
        const filterValue = inputElement.value.toLowerCase();
        const filteredItems = items.filter(item => 
            item[displayKey].toLowerCase().includes(filterValue)
        );

        if (filteredItems.length === 0) {
            const li = document.createElement('li');
            li.className = 'list-group-item disabled';
            li.textContent = 'Nenhum resultado';
            ul.appendChild(li);
        } else {
            filteredItems.forEach(item => {
                const li = document.createElement('li');
                li.className = 'list-group-item list-group-item-action';
                li.setAttribute('data-id', item[idKey]);
                li.setAttribute('data-value', item[displayKey]);
                li.textContent = item[displayKey];
                ul.appendChild(li);
            });
        }
        dropdownElement.style.display = 'block';
    }

    function hideSelectDropdown(dropdownElement) {
        if (dropdownElement) dropdownElement.style.display = 'none';
    }

    $(fertiparDataTableBody).on('focus', '.motorista-subgrid-input', async function() {
        const dropdown = $(this).closest('.custom-select-container').find('.custom-select-dropdown')[0];
        const motoristas = await fetchMotoristas();
        renderSelectOptions(this, dropdown, motoristas, 'nome', 'id');
    });

    $(fertiparDataTableBody).on('keyup', '.motorista-subgrid-input', async function() {
        const dropdown = $(this).closest('.custom-select-container').find('.custom-select-dropdown')[0];
        const motoristas = await fetchMotoristas();
        renderSelectOptions(this, dropdown, motoristas, 'nome', 'id');
    });
    
    $(fertiparDataTableBody).on('focus', '.caminhao-subgrid-input', async function() {
        const dropdown = $(this).closest('.custom-select-container').find('.custom-select-dropdown')[0];
        const caminhoes = await fetchCaminhoes();
        renderSelectOptions(this, dropdown, caminhoes, 'placa', 'id');
    });

    $(fertiparDataTableBody).on('keyup', '.caminhao-subgrid-input', async function() {
        const dropdown = $(this).closest('.custom-select-container').find('.custom-select-dropdown')[0];
        const caminhoes = await fetchCaminhoes();
        renderSelectOptions(this, dropdown, caminhoes, 'placa', 'id');
    });

    $(fertiparDataTableBody).on('click', '.custom-select-list li', function() {
        const selectedId = this.getAttribute('data-id');
        const selectedValue = this.getAttribute('data-value');
        const customSelectContainer = $(this).closest('.custom-select-container');
        const input = customSelectContainer.find('.custom-select-input');
        const detailsDiv = customSelectContainer.find('.selected-item-details');

        input.val(selectedValue);
        input.attr('data-id', selectedId);
        hideSelectDropdown(customSelectContainer.find('.custom-select-dropdown')[0]);
        
        if (input.hasClass('motorista-subgrid-input')) {
            const selectedMotorista = cachedMotoristas.find(m => m.id == selectedId);
            if (selectedMotorista) {
                detailsDiv.html(`
                    <div class="subgrid-details-card">
                        <div><strong>CPF:</strong>${selectedMotorista.cpf || 'N/A'}</div>
                        <div><strong>Telefone:</strong>${selectedMotorista.telefone || 'N/A'}</div>
                    </div>
                `);
            }
        } else if (input.hasClass('caminhao-subgrid-input')) {
            const selectedCaminhao = cachedCaminhoes.find(c => c.id == selectedId);
            if (selectedCaminhao) {
                const reboques = ['1', '2', '3'].map(i => {
                    const placa = selectedCaminhao[`placa_reboque${i}`];
                    const uf = selectedCaminhao[`uf${i}`];
                    return placa ? `<div><strong>Reb${i}:</strong> ${placa} (${uf || ''})</div>` : null;
                }).filter(Boolean).join('');
                detailsDiv.html(`
                    <div class="subgrid-details-card">
                        <div><strong>Carroceria:</strong> ${selectedCaminhao.tipo_carroceria || 'N/A'}</div>
                        ${reboques}
                    </div>
                `);
            }
        }
    });

    $(document).on('click', function(event) {
        $('.custom-select-container').each(function() {
            if (!this.contains(event.target)) {
                hideSelectDropdown($(this).find('.custom-select-dropdown')[0]);
            }
        });
    });
    
    async function executeAgenda(agendaId) {
        if (!confirm('Tem certeza que deseja executar esta agenda?')) {
            return;
        }
        showAlert(`Executando agenda ID ${agendaId}...`, 'info', true);
        try {
            const response = await fetch(`/api/agendas/execute/${agendaId}`, {
                method: 'POST',
                headers: getAuthHeaders(),
            });

            if (response.status === 401) {
                showAlert('Sess├úo expirada ou inv├ílida. Por favor, fa├ºa login novamente.', 'danger');
                return;
            }

            const result = await response.json();

            if (result.success) {
                showAlert(result.message || 'Agenda executada com sucesso!', 'success');
                // Re-render the table to reflect status change (e.g., from 'espera'/'erro' to 'processando' then 'agendado')
                await loadAndRenderAgendas(); 
            } else {
                showAlert(result.message || 'Ocorreu um erro ao executar a agenda.', 'danger');
                await loadAndRenderAgendas(); // Re-render to show error status
            }
        } catch (error) {
            console.error('Erro de conex├úo ao executar agenda:', error);
            showAlert('Erro de conex├úo ao executar agenda.', 'danger');
        }
    }

    // --- L├│gica de Polling para Atualiza├º├úo de Status ---
    // A fun├º├úo 'pollForAgendaUpdates' ser├í integrada diretamente na 'loadAndRenderAgendas'
    // A fun├º├úo 'loadAndRenderAgendas' agora carrega as agendas com base nos filtros
    async function loadAndRenderAgendas() {
        const selectedYear = selectAnoFiltro.value;
        const selectedMonth = selectMesFiltro.value;
        const agendas = await fetchAgendasData(selectedYear, selectedMonth); 
        await renderAgendas(agendas);
        // lastKnownStatuses n├úo ├® mais necess├írio com o refresh completo a cada poll.
    }

    // 1. Configurar valores padr├úo para ano e m├¬s
    const today = new Date();
    selectAnoFiltro.value = today.getFullYear();
    selectMesFiltro.value = today.getMonth() + 1; // getMonth() ├® 0-indexado

    // 2. Adicionar event listeners para os filtros
    if (selectAnoFiltro && selectMesFiltro) {
        selectAnoFiltro.addEventListener('change', loadAndRenderAgendas);
        selectMesFiltro.addEventListener('change', loadAndRenderAgendas);

        // 3. Inicializar a carga e configurar o polling de 5 segundos
        async function pollForAgendaUpdates() {
            const selectedYear = selectAnoFiltro.value;
            const selectedMonth = selectMesFiltro.value;
            const agendas = await fetchAgendasData(selectedYear, selectedMonth);
            await renderAgendas(agendas);
        }

        loadAndRenderAgendas(); // Executa uma vez imediatamente
        setInterval(pollForAgendaUpdates, 10000); // Executa a cada 10 segundos
    }

    // L├│gica de Filtragem da Tabela de Agendas
    function applyGridFilters() {
        const filters = {};
        $('#filter-row input').each(function() {
            const colIndex = $(this).data('column');
            const value = $(this).val().toLowerCase();
            if (value) {
                filters[colIndex] = value;
            }
        });

        $('#agendas-em-espera-body tr').each(function() {
            let rowVisible = true;
            const row = $(this);
            
            for (const colIndex in filters) {
                const cellText = row.find('td').eq(colIndex).text().toLowerCase();
                if (!cellText.includes(filters[colIndex])) {
                    rowVisible = false;
                    break;
                }
            }
            row.toggle(rowVisible);
        });
    }

    // Adiciona o event listener para os campos de filtro
    $(document).on('keyup', '#filter-row input', applyGridFilters);
});
