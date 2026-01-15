document.addEventListener('DOMContentLoaded', function() {
    // --- Conexão Socket.IO ---
    const socket = io();

    socket.on('connect', function() {
        console.log('Conectado ao servidor Socket.IO!');
    });

    socket.on('status_update', function(data) {
        console.log('Status update received:', data);
        toastr.info(`A agenda para o protocolo ${data.protocolo} foi atualizada para: ${data.status}`);
        
        // Chamar a nova função para atualizar a cor da linha
        updateTableRowStatus(data.protocolo, data.pedido, data.status);
        
        // Recarregar a lista de agendas em espera
        fetchAgendasEmEsperaData().then(renderAgendasEmEspera);
    });

    // Funções auxiliares para encontrar e atualizar o status visual da linha
    function updateTableRowStatus(protocolo, pedido, newStatus) {
        // Encontra a linha principal usando o protocolo (e opcionalmente o pedido para maior especificidade)
        // Usamos um atributo de dados 'data-protocolo-pedido' para uma identificação única
        const rowIdentifier = `${protocolo}-${pedido}`;
        const mainRow = $(`#fertiparDataTableBody tr.fertipar-main-row[data-protocolo="${protocolo}"][data-pedido="${pedido}"]`);
        
        if (mainRow.length === 0) {
            console.warn(`Linha para protocolo ${protocolo} e pedido ${pedido} não encontrada.`);
            return;
        }

        const subgridRow = mainRow.next('.fertipar-subgrid-row');
        const statusInput = subgridRow.find('.subgrid-status');

        // Atualiza o texto do status no subgrid
        statusInput.val(newStatus);

        // Remove classes de status antigas
        mainRow.removeClass('agendado-row status-changed-row');
        subgridRow.removeClass('agendado-row status-changed-row');

        // Adiciona a classe apropriada com base no novo status
        if (newStatus === 'espera') {
            mainRow.addClass('agendado-row'); // Agendado (verde)
            subgridRow.addClass('agendado-row');
        } else {
            mainRow.addClass('status-changed-row'); // Status diferente de espera (azul)
            subgridRow.addClass('status-changed-row');
        }
    }

    // --- Seletores de Elementos ---
    const motoristaSelect = document.getElementById('agenda-motorista-select');
    const motoristaInfoDiv = document.getElementById('agenda-motorista-info');
    const caminhaoSelect = document.getElementById('agenda-caminhao-select');
    const caminhaoInfoDiv = document.getElementById('agenda-caminhao-info');
    const formGerarAgenda = document.getElementById('form-gerar-agenda');

    // Campos ocultos
    const hiddenMotoristaId = document.getElementById('hidden-motorista-id');
    const hiddenCaminhaoId = document.getElementById('hidden-caminhao-id');
    const hiddenFertiparItemJson = document.getElementById('hidden-fertipar-item-json');

    // Elementos do Modal Fertipar
    const fertiparModal = document.getElementById('fertiparModal');
    const btnLerDadosFertipar = document.getElementById('btnLerDadosFertipar');
    const lastReadStatus = document.getElementById('lastReadStatus');
    const fertiparDataTableBody = document.getElementById('fertiparDataTableBody');
    const selectedFertiparItemsDiv = document.getElementById('selected-fertipar-items');
    const btnSaveFertipar = fertiparModal ? fertiparModal.querySelector('.modal-footer .btn-primary') : null;

    // Tabela de Agendas em Espera
    const agendasEmEsperaBody = document.getElementById('agendas-em-espera-body');

    // --- Constantes ---
    const LAST_READ_KEY = 'lastFertiparRead';
    const FIVE_MINUTES_MS = 5 * 60 * 1000;

    // --- Funções Auxiliares ---
    function getAuthHeaders() {
        const token = localStorage.getItem('jwt_token'); // Assumindo que o token é salvo aqui no login
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
        if (message === "Dados Não coletados, site já bloqueado!") {
            toastr.options.timeOut = 0; // Fica visível até ser fechado
            type = 'warning'; // Usa o tipo 'aviso' (amarelo)
        } else if (type === 'danger') {
            toastr.options.timeOut = 0; // Erros reais também ficam visíveis
        } else if (isFixed) {
            toastr.options.timeOut = 0; // Fixed toast
            toastr.options.extendedTimeOut = 0;
        }
        else {
            toastr.options.timeOut = 5000; // 5 segundos para outros tipos (success, info)
        }

        const toastrType = type === 'danger' ? 'error' : type;
        toastr[toastrType](message);
    }

    // Funções auxiliares para limpar e atualizar UI
    function clearAgendaForm() {
        motoristaSelect.value = '';
        caminhaoSelect.value = '';
        motoristaInfoDiv.innerHTML = '';
        caminhaoInfoDiv.innerHTML = '';
        hiddenMotoristaId.value = '';
        hiddenCaminhaoId.value = '';
        hiddenFertiparItemJson.value = '';
        
        // Limpar seleção de Fertipar
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

    function fetchAgendasEmEsperaData() {
        return fetch('/api/agendas_em_espera', { headers: getAuthHeaders() })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Erro HTTP: ${response.status}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error('Erro ao buscar agendas em espera:', error);
                showAlert('Falha ao carregar agendas em espera. Verifique sua conexão ou autenticação.', 'danger');
                return []; // Retorna um array vazio em caso de erro
            });
    }

    // Nova função para renderizar as agendas no DOM
    function renderAgendasEmEspera(agendas) {
        agendasEmEsperaBody.innerHTML = ''; // Limpa o conteúdo atual da tabela

        if (agendas.length === 0) {
            agendasEmEsperaBody.innerHTML = '<tr><td colspan="9" class="text-center">Nenhuma agenda em espera.</td></tr>'; // Colspan ajustado para 9
            return;
        }

        agendas.forEach(agenda => {
            const row = agendasEmEsperaBody.insertRow();
            
            // Formata as informações do caminhão a partir do objeto
            let caminhaoDisplay = agenda.caminhao.placa;
            if (agenda.caminhao.tipo_carroceria) {
                caminhaoDisplay += ` - ${agenda.caminhao.tipo_carroceria}`;
            }
            if (agenda.caminhao.reboques && agenda.caminhao.reboques.length > 0) {
                caminhaoDisplay += ` | ${agenda.caminhao.reboques.join(', ')}`;
            }

            row.innerHTML = `
                <td>${agenda.data_agendamento}</td>
                <td>${agenda.motorista}</td>
                <td>${caminhaoDisplay}</td>
                <td>${agenda.protocolo}</td>
                <td>${agenda.pedido}</td>
                <td>${agenda.destino}</td>
                <td>${agenda.carga_solicitada !== null ? agenda.carga_solicitada : 'N/A'}</td> <!-- Display new field -->
                <td><span class="badge badge-warning">${agenda.status}</span></td>
                <td>
                    <button class="btn btn-sm btn-info" title="Iniciar"><i class="fas fa-play"></i></button>
                    <button class="btn btn-sm btn-danger btn-cancelar-agenda" title="Cancelar" data-id="${agenda.id}"><i class="fas fa-times"></i></button>
                </td>
            `;
        });
    }

    // --- Lógica Principal ---

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

    async function rpaFert(agenda_data = null) {
        toastr.info('Enviando comando de teste para o robô...');
        try {
            const response = await fetch('/api/rpa_fertipar_teste', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ agenda_data: agenda_data })
            });

            const result = await response.json();

            if (result.success) {
                showAlert(result.message || 'Comando de teste executado. Verifique o console do servidor.', 'success');
            } else {
                showAlert(result.message || 'Ocorreu um erro desconhecido durante o teste do robô.', 'danger');
            }
        } catch (error) {
            console.error('Erro ao chamar rpaFert:', error);
            showAlert('Erro de conexão com o servidor ao tentar executar o teste do robô. Verifique sua rede e o status do servidor.', 'danger');
        }
    }

    // 1. Atualizar informações e campos ocultos na seleção
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

    // 2. Lógica do Modal Fertipar
    function updateLastReadStatus() {
        const lastRead = localStorage.getItem(LAST_READ_KEY);
        let needsUpdate = false;

        if (lastRead) {
            const lastReadDate = new Date(lastRead);
            const now = new Date();
            const diff = now.getTime() - lastReadDate.getTime();
            let statusText = `Última leitura: ${formatDateTime(lastReadDate)}`;
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
        const existingAgendas = new Set(agendasEmEspera.map(a => a.protocolo));

        if (data && data.length > 0) {
            data.forEach((item, index) => {
                const isItemAgendado = existingAgendas.has(item.Protocolo);
                const row = fertiparDataTableBody.insertRow();
                row.setAttribute('data-item', JSON.stringify(item));
                row.classList.add('fertipar-main-row');
                if (isItemAgendado) {
                    row.classList.add('agendado-row'); // Nova classe para linha principal agendada
                }
                row.setAttribute('data-protocolo', item.Protocolo);
                row.setAttribute('data-pedido', item.Pedido); // Adicionado para identificar unicamente
                row.innerHTML = `
                    <td><button class="btn btn-sm btn-outline-secondary btn-toggle-subgrid" ${isItemAgendado ? 'disabled' : ''}><i class="fas fa-plus"></i></button></td>
                    <td><input type="checkbox" name="selecionar_item_modal" value="${index}" ${isItemAgendado ? 'disabled' : ''}></td>
                    <td><strong>${item.Protocolo || ''}</strong></td>
                    <td><strong>${item.Pedido || ''}</strong></td>
                    <td>${item.Data || ''}</td>
                    <td>${item['Situação'] || ''}</td>
                    <td>${item.Destino || ''}</td>
                    <td><strong>${item['Qtde.'] || ''}</strong></td>
                    <td>${item.Embalagem || ''}</td>
                    <td>${item['Cotação'] || ''}</td>
                    <td>${item['Observação Cotação'] || ''}</td>
                `;

                const subgridRow = fertiparDataTableBody.insertRow();
                subgridRow.classList.add('fertipar-subgrid-row');
                if (isItemAgendado) {
                    subgridRow.classList.add('agendado-row'); // Nova classe para subgrid agendado
                }
                subgridRow.style.display = 'none';
                subgridRow.innerHTML = `
                    <td colspan="11">
                        <div class="subgrid-content p-2 shadow-sm" style="width: 100%; display: flex; padding: 10px; background-color: #f8f9fa; border: 1px solid #e9ecef;">
                            <div class="form-group col-md-3 custom-select-container">
                                <label for="motorista-subgrid-input-${index}">Motorista</label>
                                <input type="text" class="form-control form-control-sm custom-select-input motorista-subgrid-input" id="motorista-subgrid-input-${index}" placeholder="Selecione ou digite" data-id="" ${isItemAgendado ? 'disabled' : ''}>
                                <div class="custom-select-dropdown" id="motorista-subgrid-dropdown-${index}"><ul class="list-group list-group-flush custom-select-list"></ul></div>
                                <div class="selected-item-details mt-1"></div>
                            </div>
                            <div class="form-group col-md-3 custom-select-container">
                                <label for="caminhao-subgrid-input-${index}">Caminhão</label>
                                <input type="text" class="form-control form-control-sm custom-select-input caminhao-subgrid-input" id="caminhao-subgrid-input-${index}" placeholder="Selecione ou digite" data-id="" ${isItemAgendado ? 'disabled' : ''}>
                                <div class="custom-select-dropdown" id="caminhao-subgrid-dropdown-${index}"><ul class="list-group list-group-flush custom-select-list"></ul></div>
                                <div class="selected-item-details mt-1"></div>
                            </div>
                            <div class="form-group col-md-2">
                                <label for="carga-solicitada-input-${index}">Carga Sol.</label>
                                <input type="number" step="0.01" class="form-control form-control-sm carga-solicitada-input" id="carga-solicitada-input-${index}" placeholder="Ton" ${isItemAgendado ? 'disabled' : ''}>
                            </div>
                            <div class="form-group col-md-2">
                                <label>Status</label>
                                <input type="text" class="form-control form-control-sm subgrid-status" value="${isItemAgendado ? 'Agendado!' : ''}" readonly>
                            </div>
                            <div class="form-group col-md-1">
                                <label>&nbsp;</label>
                                <button type="button" class="btn btn-success btn-sm btn-block btn-agendar-subgrid" ${isItemAgendado ? 'disabled' : ''}>
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

        fetchAgendasEmEsperaData().then(agendasEmEspera => {
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
                    fetchAgendasEmEsperaData()
                ]);

                if (fertiparResponse.status === 401) {
                    showAlert('Sessão expirada ou inválida. Por favor, faça login novamente.', 'danger');
                    lastReadStatus.innerHTML = '<span class="text-danger">Não autorizado.</span>';
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
                        showAlert(result.message || 'Não há dados de cotação disponíveis no momento.', 'info');
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
                showAlert('Erro de conexão ao tentar buscar os dados da Fertipar.', 'danger');
                lastReadStatus.innerHTML = '<span class="text-danger">Falha na conexão.</span>';
            } finally {
                btnLerDadosFertipar.disabled = false;
            }
        });
    }

    if (fertiparModal) {
        $(fertiparModal).on('show.bs.modal', () => updateLastReadStatus());
        
        // Listener para o novo botão de dados fictícios
        $('#btnDadosFicticios').on('click', async function() {
            const fictitiousData = [
                { "Protocolo": "346562", "Pedido": "928580", "Data": "13/01/2026 10:21", "Situação": "APROVADO", "Destino": "BELA VISTA -MS", "Qtde.": "46.0", "Embalagem": "BIG-BAG", "Cotação": "290.0", "Observação Cotação": "" },
                { "Protocolo": "346512", "Pedido": "939686", "Data": "09/01/2026 16:32", "Situação": "APROVADO", "Destino": "COSTA RICA - MS", "Qtde.": "97.5", "Embalagem": "BIG-BAG", "Cotação": "290.0", "Observação Cotação": "MINIMO MOTO RODO 247,64" },
                { "Protocolo": "346445", "Pedido": "928580", "Data": "07/01/2026 13:27", "Situação": "APROVADO", "Destino": "BONITO-MS", "Qtde.": "48.0", "Embalagem": "BIG-BAG", "Cotação": "280.0", "Observação Cotação": "MINIMO MOTO RODO 256,47" },
                { "Protocolo": "346443", "Pedido": "928580", "Data": "07/01/2026 14:08", "Situação": "APROVADO", "Destino": "BONITO-MS", "Qtde.": "70.0", "Embalagem": "BIG-BAG", "Cotação": "335.0", "Observação Cotação": "MINIMO MOTO BITREM 301,49" },
                { "Protocolo": "346442", "Pedido": "928580", "Data": "07/01/2026 14:10", "Situação": "APROVADO", "Destino": "BONITO-MS", "Qtde.": "2.0", "Embalagem": "BIG-BAG", "Cotação": "335.0", "Observação Cotação": "MINIMO MOTO BITREM 301,49" },
                { "Protocolo": "346419", "Pedido": "938069", "Data": "05/01/2026 11:52", "Situação": "APROVADO", "Destino": "PARAISO DAS AGUAS - MS", "Qtde.": "48.0", "Embalagem": "BIG-BAG", "Cotação": "320.0", "Observação Cotação": "MINIMO MOTO RODO 228,45" },
                { "Protocolo": "346405", "Pedido": "928580", "Data": "13/01/2026 13:05", "Situação": "APROVADO", "Destino": "ANASTACIO - MS", "Qtde.": "35.0", "Embalagem": "BIG-BAG", "Cotação": "335.0", "Observação Cotação": "MINIMO MOTO 300,0" },
                { "Protocolo": "346387", "Pedido": "926074", "Data": "04/12/2025 16:10", "Situação": "APROVADO", "Destino": "ALCINOPOLIS - MS", "Qtde.": "49.0", "Embalagem": "BIG-BAG", "Cotação": "300.0", "Observação Cotação": "MINIMO MOTO RODO 279,88" },
                { "Protocolo": "346215", "Pedido": "939421", "Data": "07/01/2026 10:21", "Situação": "APROVADO", "Destino": "ROSANA-SP", "Qtde.": "72.0", "Embalagem": "BIG-BAG", "Cotação": "240.0", "Observação Cotação": "MINIMO MOTO BITREM 185,30" },
                { "Protocolo": "346203", "Pedido": "940277", "Data": "12/01/2026 18:30", "Situação": "APROVADO", "Destino": "ESPIGAO DO OESTE - RO", "Qtde.": "16.0", "Embalagem": "BIG-BAG", "Cotação": "620.0", "Observação Cotação": "" }
            ];
            
            const agendasEmEspera = await fetchAgendasEmEsperaData(); // Fetch agendas here
            populateFertiparTable(fictitiousData, agendasEmEspera);
            toastr.info('Dados fictícios carregados na tabela.');

            if(lastReadStatus) {
                lastReadStatus.innerHTML = '<span class="text-warning font-weight-bold">Exibindo dados fictícios.</span>';
            }
            
            $('#fertiparDataTableBody input[type="checkbox"]').prop('disabled', false);
            $('#fertiparModal .filter-input').prop('disabled', false);
            if (btnSaveFertipar) $(btnSaveFertipar).prop('disabled', false);
        });

        // Lógica de filtragem
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
                    // Não mexer no status do subgrid aqui para manter o estado (aberto/fechado)
                } else {
                    row.hide();
                    if(subgridRow.length > 0) {
                        subgridRow.hide(); // Esconder subgrid associado se a linha principal for escondida
                    }
                }
            });
        });

        // Listener para o botão de teste do bot
        $('#btnTesteBot').on('click', function() {
            rpaFert();
        });

        // Listener para o botão Limpar Agendas
        $('#btnLimparAgendas').on('click', async function() {
            if (!confirm('Tem certeza que deseja limpar TODOS os agendamentos em espera? Esta ação é irreversível.')) {
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
                    fetchAgendasEmEsperaData().then(renderAgendasEmEspera); // Recarrega a lista de agendas em espera
                } else {
                    showAlert(result.message || 'Ocorreu um erro ao limpar os agendamentos.', 'danger');
                }
            } catch (error) {
                console.error('Erro ao limpar agendamentos:', error);
                showAlert('Erro de conexão ao tentar limpar os agendamentos.', 'danger');
            }
        });
    }

    if (formGerarAgenda) {
        formGerarAgenda.addEventListener('submit', async function(event) {
            event.preventDefault(); // Previne o refresh da página

            const pesoCarregarInput = document.getElementById('peso-carregar');
            const pesoCarregar = parseFloat(pesoCarregarInput.value);

            if (!pesoCarregar || pesoCarregar <= 0) {
                // showAlert('O campo "Peso a Carregar" é obrigatório e deve ser maior que zero.', 'warning'); // Removido toast
                pesoCarregarInput.focus();
                return;
            }

            // Coleta os dados do formulário
            const motoristaId = hiddenMotoristaId.value;
            const caminhaoId = hiddenCaminhaoId.value;
            const fertiparItemJson = hiddenFertiparItemJson.value;
            
            if (!motoristaId || !caminhaoId || !fertiparItemJson) {
                // showAlert('Por favor, selecione um motorista, um caminhão e um item Fertipar.', 'warning'); // Removido toast
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
                    // showAlert('Sessão expirada ou inválida. Por favor, faça login novamente.', 'danger'); // Removido toast
                    return;
                }

                const result = await response.json();

                if (result.success) {
                    showAlert('Agenda criada com sucesso!', 'success', true);
                    
                    const fertiparItem = JSON.parse(fertiparItemJson);
                    if (fertiparItem && fertiparItem.Protocolo) {
                        disableFertiparCard(fertiparItem.Protocolo);
                    }
                    
                    rpaFert(result.agenda); // Chama a função rpaFert com os dados da nova agenda
                    
                    clearAgendaForm(); // Limpa os campos

                    // Ativa a aba "Gerar Agenda" e recarrega a lista
                    $('[href="#gerar-agenda"]').tab('show'); 
                    fetchAgendasEmEsperaData().then(renderAgendasEmEspera);
                } else {
                    // Removido toast de erro para simplificar a UI, o erro pode ser visto no console
                    // showAlert('Erro ao criar agenda: ' + (result.message || 'Erro desconhecido'), 'danger');
                }
            } catch (error) {
                console.error('Erro ao agendar:', error);
                // Removido toast de erro de conexão para simplificar a UI
                // showAlert('Erro de conexão ao agendar.', 'danger');
            }
        });
    }

    // --- Lógica de Agendamento (Subgrid) ---
    async function agendarViaSubgrid(button) {
        const subgridContent = $(button).closest('.subgrid-content');
        const mainRow = subgridContent.closest('.fertipar-subgrid-row').prev('.fertipar-main-row');
        const statusInput = subgridContent.find('.subgrid-status');
        
        const motoristaId = subgridContent.find('.motorista-subgrid-input').attr('data-id');
        const caminhaoId = subgridContent.find('.caminhao-subgrid-input').attr('data-id');
        const cargaSolicitada = subgridContent.find('.carga-solicitada-input').val();
        const fertiparItem = JSON.parse(mainRow.attr('data-item'));

        if (!motoristaId || !caminhaoId || !fertiparItem) {
            // showAlert('Por favor, selecione um motorista e um caminhão para agendar.', 'warning'); // Removido toast
            return;
        }
        
        const cargaSolicitadaFloat = parseFloat(cargaSolicitada);
        if (isNaN(cargaSolicitadaFloat) || cargaSolicitadaFloat <= 0) {
            // showAlert('O campo "Carga Solicitada" é obrigatório e deve ser maior que zero.', 'warning'); // Removido toast
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
            const response = await fetch('/agendar', {
                method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(formData)
            });
            const result = await response.json();
            if (result.success) {
                showAlert('Agenda criada com sucesso!', 'success', true);
                statusInput.val('Agendado!');
                mainRow.addClass('agendado-row'); // Adiciona classe para linha principal
                subgridContent.closest('.fertipar-subgrid-row').addClass('agendado-row'); // Adiciona classe para subgrid
                subgridContent.find('input, button').prop('disabled', true); // Desabilita todos os inputs e botões
                fetchAgendasEmEsperaData().then(renderAgendasEmEspera); // Atualiza a lista principal
                rpaFert(result.agenda); // Chama a função rpaFert após o sucesso
            } else {
                // showAlert('Erro ao agendar: ' + (result.message || 'Erro desconhecido'), 'danger'); // Removido toast
                statusInput.val('Erro!');
                button.disabled = false;
            }
        } catch (error) {
            console.error('Erro ao agendar via subgrid:', error);
            // showAlert('Erro de conexão ao agendar.', 'danger'); // Removido toast
            statusInput.val('Falha na conexão');
            button.disabled = false;
        }
    }

    if (fertiparDataTableBody) {
        // Listener para o botão de agendamento do subgrid
        fertiparDataTableBody.addEventListener('click', function(event) {
            const agendarButton = event.target.closest('.btn-agendar-subgrid');
            if (agendarButton) {
                agendarViaSubgrid(agendarButton);
            }
        });

        // Listener para validação do campo de carga solicitada
        fertiparDataTableBody.addEventListener('input', function(event) {
            const cargaInput = event.target.closest('.carga-solicitada-input');
            if (cargaInput) {
                const mainRow = $(cargaInput).closest('.fertipar-subgrid-row').prev('.fertipar-main-row');
                const itemData = JSON.parse(mainRow.attr('data-item'));
                const qtdeDisponivel = parseFloat(itemData['Qtde.']);
                const cargaDigitada = parseFloat(cargaInput.value);

                if (!isNaN(cargaDigitada) && !isNaN(qtdeDisponivel) && cargaDigitada > qtdeDisponivel) {
                    toastr.warning(`A carga solicitada (${cargaDigitada} ton) não pode ser maior que a quantidade disponível (${qtdeDisponivel} ton).`, 'Valor Inválido');
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
                
                const agendas = await fetchAgendasEmEsperaData();
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

    // --- Nova função para exclusão de agenda ---
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
                showAlert('Sessão expirada ou inválida. Por favor, faça login novamente.', 'danger');
                return;
            }

            const result = await response.json();

            if (result.success) {
                showAlert('Agenda cancelada com sucesso!', 'success');
                fetchAgendasEmEsperaData().then(agendas => renderAgendasEmEspera(agendas)); // Recarregar a lista
            } else {
                showAlert('Erro ao cancelar agenda: ' + (result.message || 'Erro desconhecido'), 'danger');
            }
        } catch (error) {
            console.error('Erro de conexão ao cancelar agenda:', error);
            showAlert('Erro de conexão ao cancelar agenda.', 'danger');
        }
    }

    // --- Event listener para os botões de cancelar ---
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

    // --- Lógica para expandir/recolher subgrid no Modal Fertipar ---
    if (fertiparDataTableBody) {
        fertiparDataTableBody.addEventListener('click', function(event) {
            const toggleButton = event.target.closest('.btn-toggle-subgrid');
            if (toggleButton) {
                const mainRow = toggleButton.closest('.fertipar-main-row');
                const subgridRow = mainRow.nextElementSibling; // A linha do subgrid é a próxima irmã da linha principal

                if (subgridRow && subgridRow.classList.contains('fertipar-subgrid-row')) {
                    if (subgridRow.style.display === 'none') {
                        subgridRow.style.display = ''; // Mostrar
                        toggleButton.querySelector('i').classList.remove('fa-plus');
                        toggleButton.querySelector('i').classList.add('fa-minus');
                    } else {
                        subgridRow.style.display = 'none'; // Esconder
                        toggleButton.querySelector('i').classList.remove('fa-minus');
                        toggleButton.querySelector('i').classList.add('fa-plus');
                    }
                }
            }
        });
    }
    
    // --- Lógica de busca e renderização dos selects customizados ---
    let cachedMotoristas = [];
    let cachedCaminhoes = [];

    async function fetchMotoristas() {
        if (cachedMotoristas.length > 0) {
            return cachedMotoristas;
        }
        try {
            const response = await fetch('/api/motoristas'); // Não requer autenticação
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
            const response = await fetch('/api/caminhoes'); // Não requer autenticação
            const data = await response.json();
            cachedCaminhoes = data;
            return data;
        } catch (error) {
            console.error('Erro ao buscar caminhões:', error);
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
                detailsDiv.html(`<small class="text-muted"><strong>CPF:</strong> ${selectedMotorista.cpf || 'N/A'} | <strong>Telefone:</strong> ${selectedMotorista.telefone || 'N/A'}</small>`);
            }
        } else if (input.hasClass('caminhao-subgrid-input')) {
            const selectedCaminhao = cachedCaminhoes.find(c => c.id == selectedId);
            if (selectedCaminhao) {
                const reboques = ['1', '2', '3'].map(i => {
                    const placa = selectedCaminhao[`placa_reboque${i}`];
                    const uf = selectedCaminhao[`uf${i}`];
                    return placa ? `Reb${i}: ${placa} (${uf || ''})` : null;
                }).filter(Boolean).join(' | ');
                detailsDiv.html(`<small class="text-muted"><strong>Carroceria:</strong> ${selectedCaminhao.tipo_carroceria || 'N/A'}<br>${reboques}</small>`);
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
    
    // Carregar agendas em espera na inicialização da página
    fetchAgendasEmEsperaData().then(agendas => renderAgendasEmEspera(agendas));
});