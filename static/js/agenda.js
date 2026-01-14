document.addEventListener('DOMContentLoaded', function() {
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
    
    function showAlert(message, type = 'info') {
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
            "timeOut": "5000",
            "extendedTimeOut": "1000",
            "showEasing": "swing",
            "hideEasing": "linear",
            "showMethod": "fadeIn",
            "hideMethod": "fadeOut"
        };
        // Corrige o tipo 'danger' para o tipo 'error' que o toastr espera
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
            row.innerHTML = `
                <td>${agenda.data_agendamento}</td>
                <td>${agenda.motorista}</td>
                <td>${agenda.caminhao}</td>
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

    function populateFertiparTable(data) {
        fertiparDataTableBody.innerHTML = '';
        if (data && data.length > 0) {
            data.forEach((item, index) => {
                const row = fertiparDataTableBody.insertRow();
                row.setAttribute('data-item', JSON.stringify(item));
                row.classList.add('fertipar-main-row'); // Classe para a linha principal
                row.setAttribute('data-agenda-id', item.id); // Supondo que item.id existe para identificar a agenda, se não, usar Protocolo ou outro identificador único
                row.innerHTML = `
                    <td><button class="btn btn-sm btn-outline-secondary btn-toggle-subgrid"><i class="fas fa-plus"></i></button></td>
                    <td><input type="checkbox" name="selecionar_item_modal" value="${index}"></td>
                    <td>${item.Protocolo || ''}</td><td>${item.Pedido || ''}</td><td>${item.Data || ''}</td>
                    <td>${item.Situacao || ''}</td><td>${item.Destino || ''}</td><td>${item['Qtde.'] || ''}</td>
                    <td>${item.Embalagem || ''}</td><td>${item.Cotacao || ''}</td><td>${item.ObservacaoCotacao || ''}</td>
                `;

                // Subgrid row
                const subgridRow = fertiparDataTableBody.insertRow();
                subgridRow.classList.add('fertipar-subgrid-row');
                subgridRow.style.display = 'none'; // Esconder por padrão
                subgridRow.innerHTML = `
                    <td colspan="11"> <!-- Colspan ajustado para cobrir todas as colunas + botão -->
                        <div class="subgrid-content" style="width: 100%; display: flex; padding: 10px; background-color: #f8f9fa; border: 1px solid #e9ecef;">
                            <div class="form-group col-md-5 custom-select-container">
                                <label for="motorista-subgrid-input-${index}">Motorista</label>
                                <input type="text" class="form-control form-control-sm custom-select-input motorista-subgrid-input" id="motorista-subgrid-input-${index}" placeholder="Selecione ou digite o motorista" data-id="">
                                <div class="selected-item-details text-muted" style="font-size: 0.7em;"></div>
                                <div class="custom-select-dropdown" id="motorista-subgrid-dropdown-${index}">
                                    <ul class="list-group list-group-flush custom-select-list">
                                        <!-- Opções serão carregadas via JS -->
                                    </ul>
                                </div>
                            </div>
                            <div class="form-group col-md-5 custom-select-container">
                                <label for="caminhao-subgrid-input-${index}">Caminhão</label>
                                <input type="text" class="form-control form-control-sm custom-select-input caminhao-subgrid-input" id="caminhao-subgrid-input-${index}" placeholder="Selecione ou digite a placa do caminhão" data-id="">
                                <div class="selected-item-details text-muted" style="font-size: 0.7em;"></div>
                                <div class="custom-select-dropdown" id="caminhao-subgrid-dropdown-${index}">
                                    <ul class="list-group list-group-flush custom-select-list">
                                        <!-- Opções serão carregadas via JS -->
                                    </ul>
                                </div>
                            </div>
                            <div class="form-group col-md-2">
                                <label for="carga-solicitada-input-${index}">Carga Solicitada</label>
                                <input type="number" step="0.01" class="form-control form-control-sm carga-solicitada-input" id="carga-solicitada-input-${index}" placeholder="Ex: 10.50">
                            </div>
                            <div class="form-group col-md-2 d-flex align-items-center justify-content-center">
                                <button type="button" class="btn btn-success btn-sm mt-3 btn-agendar-subgrid">
                                    <i class="fas fa-play mr-1"></i>Agendar
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
                // Para testar o cenário de erro, você pode adicionar "?simulate=error" na URL.
                const response = await fetch('/api/scrape_fertipar_data', { headers: getAuthHeaders() });
                
                if (response.status === 401) {
                    showAlert('Sessão expirada ou inválida. Por favor, faça login novamente.', 'danger');
                    lastReadStatus.innerHTML = '<span class="text-danger">Não autorizado.</span>';
                    populateFertiparTable([]);
                    return;
                }

                const result = await response.json();

                if (result.success) {
                    if (result.data.length > 0) {
                        populateFertiparTable(result.data);
                        showAlert('Dados Fertipar lidos com sucesso!', 'success');
                    } else {
                        // Sucesso, mas sem dados
                        populateFertiparTable([]);
                        showAlert('Não há dados de cotação disponíveis no momento.', 'info');
                    }
                    localStorage.setItem(LAST_READ_KEY, new Date().toISOString());
                    updateLastReadStatus();
                } else {
                    // Falha na API (success: false)
                    populateFertiparTable([]);
                    showAlert(result.message || 'Ocorreu um erro desconhecido ao buscar os dados.', 'danger');
                    lastReadStatus.innerHTML = '<span class="text-danger">Erro na leitura.</span>';
                }
            } catch (error) {
                // Erro de conexão ou outro erro de javascript
                console.error('Erro ao ler dados Fertipar:', error);
                populateFertiparTable([]);
                showAlert('Erro de conexão ao tentar buscar os dados da Fertipar.', 'danger');
                lastReadStatus.innerHTML = '<span class="text-danger">Falha na conexão.</span>';
            } finally {
                btnLerDadosFertipar.disabled = false;
            }
        });
    }

    if (fertiparModal) {
        $(fertiparModal).on('show.bs.modal', () => updateLastReadStatus());
        // Lógica de filtragem
        $(fertiparModal).on('keyup', '.filter-input', function() {
            const columnIndex = $(this).parent().index(); // Pega o índice da coluna do input
            const filterValue = $(this).val().toLowerCase();

            $('#fertiparDataTableBody tr').each(function() {
                const row = $(this);
                const cell = row.find('td').eq(columnIndex);
                const cellText = cell.text().toLowerCase();

                if (cellText.includes(filterValue)) {
                    row.show();
                } else {
                    row.hide();
                }
            });
        });
    }

    if (formGerarAgenda) {
        formGerarAgenda.addEventListener('submit', async function(event) {
            event.preventDefault(); // Previne o refresh da página

            // Coleta os dados do formulário
            const motoristaId = hiddenMotoristaId.value;
            const caminhaoId = hiddenCaminhaoId.value;
            const fertiparItemJson = hiddenFertiparItemJson.value;
            const pesoCarregar = document.getElementById('peso-carregar').value; // Coleta o valor do novo campo

            if (!motoristaId || !caminhaoId || !fertiparItemJson) {
                showAlert('Por favor, selecione um motorista, um caminhão e um item Fertipar.', 'warning');
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
                    showAlert('Sessão expirada ou inválida. Por favor, faça login novamente.', 'danger');
                    return;
                }

                const result = await response.json();

                if (result.success) {
                    showAlert('Agenda criada com sucesso!', 'success');
                    clearAgendaForm(); // Limpa os campos
                    
                    // Pega o protocolo do item Fertipar agendado
                    const fertiparItem = JSON.parse(fertiparItemJson);
                    if (fertiparItem && fertiparItem.Protocolo) {
                        disableFertiparCard(fertiparItem.Protocolo); // Bloqueia e risca o card
                    }

                    // Ativa a aba "Gerar Agenda"
                    $('[href="#gerar-agenda"]').tab('show'); 

                    fetchAgendasEmEsperaData().then(agendas => renderAgendasEmEspera(agendas)); // Recarrega a lista de agendas em espera
                } else {
                    showAlert('Erro ao criar agenda: ' + (result.message || 'Erro desconhecido'), 'danger');
                }
            } catch (error) {
                console.error('Erro ao agendar:', error);
                showAlert('Erro de conexão ao agendar.', 'danger');
            }
        });
    }

    if (btnSaveFertipar) {
        btnSaveFertipar.addEventListener('click', function() {
            const selectedItemsData = [];
            $('#fertiparDataTableBody tr').each(function() {
                if ($(this).find('input[name="selecionar_item_modal"]').is(':checked')) {
                    selectedItemsData.push(JSON.parse($(this).attr('data-item')));
                }
            });
            displaySelectedFertiparItems(selectedItemsData);
            $(fertiparModal).modal('hide');
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
                detailsDiv.html(`<div class="toast-like-info"><strong>CPF:</strong> ${selectedMotorista.cpf || 'N/A'} | <strong>Telefone:</strong> ${selectedMotorista.telefone || 'N/A'}</div>`);
            }
        } else if (input.hasClass('caminhao-subgrid-input')) {
            const selectedCaminhao = cachedCaminhoes.find(c => c.id == selectedId);
            if (selectedCaminhao) {
                detailsDiv.html(`<div class="toast-like-info"><strong>Placa:</strong> ${selectedCaminhao.placa} | <strong>Carroceria:</strong> ${selectedCaminhao.tipo_carroceria || 'N/A'}</div>`);
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