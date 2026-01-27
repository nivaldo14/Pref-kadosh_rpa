import time
import traceback
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright, Page, expect, TimeoutError
import re

# Helper function (no changes needed here)
async def try_locate_and_screenshot(page_object, context_frame_or_page, locators_with_names, element_description):
    print(f"\n--- Tentando localizar: '{element_description}' ---")
    for locator_object, locator_description in locators_with_names:
        try:
            await expect(locator_object).to_be_visible(timeout=5000)
            print(f"  [SUCESSO] Elemento '{element_description}' encontrado e visível com: '{locator_description}'.")
            screenshot_path = f"screenshot_{element_description.replace(' ', '_').replace('.', '')}_found.png"
            await page_object.screenshot(path=screenshot_path)
            print(f"  Screenshot salvo em: {screenshot_path}")
            return locator_object
        except TimeoutError:
            print(f"  [FALHA] Seletor '{locator_description}' não visível no tempo. Tentando próximo seletor.")
        except Exception as e:
            print(f"  [FALHA] Seletor '{locator_description}' falhou. Erro: {e}")
    raise Exception(f"Elemento '{element_description}' não foi encontrado por nenhum dos seletores fornecidos.")

# --- 1. Refatorar a assinatura da função ---
async def process_agendamento_main_task(rpa_params: dict, run_headless: bool = True):
    """
    Processa um agendamento no site da Fertipar usando Playwright,
    recebendo todos os parâmetros em um único dicionário.
    """
    # --- Extrair dados do dicionário rpa_params ---
    config = rpa_params.get("config", {})
    agenda_item = rpa_params.get("agenda", {})
    motorista = rpa_params.get("motorista", {})
    caminhao = rpa_params.get("caminhao", {})
    storage_state = rpa_params.get("storage_state") # Novo: extrair storage_state

    url_login = config.get("url_acesso")
    filial = config.get("filial")
    usuario_site = config.get("usuario_site")
    senha_site = config.get("senha_site")
    
    protocolo_procurado = agenda_item.get("fertipar_protocolo")
    pedido_procurado = agenda_item.get("fertipar_pedido")
    
    nro_cpf = (motorista.get("cpf") or "").replace('.', '').replace('-', '')

    # Helper function to mask CPF for assertion
    def mask_cpf_for_assertion(unmasked_cpf):
        if len(unmasked_cpf) == 11:
            return re.sub(r'(\d{3})(\d{3})(\d{3})(\d{2})', r'\1.\2.\3-\4', unmasked_cpf)
        return unmasked_cpf # Return as is if not a valid CPF length
    
    masked_cpf = mask_cpf_for_assertion(nro_cpf)
    
    placa_principal = caminhao.get("placa")

    print(f"Iniciando automação para Protocolo: {protocolo_procurado}, Pedido: {pedido_procurado}, CPF: {nro_cpf}")

    async with async_playwright() as playwright:
        # Determina o modo headless com base na configuração 'head_evento' do JSON.
        # head_evento: true (mostrar tela) -> headless=False
        # head_evento: false (rodar em background) -> headless=True
        mostrar_tela = config.get('head_evento', False)
        run_headless_mode = not mostrar_tela
        
        print(f"Configuração 'head_evento' é {mostrar_tela}. Modo headless do navegador: {run_headless_mode}.")

        browser = await playwright.chromium.launch(headless=run_headless_mode, slow_mo=50, args=["--start-fullscreen"])
        # Novo: Inicializa o contexto com o storage_state se ele existir
        context = await browser.new_context(storage_state=storage_state if storage_state else {})
        page = await context.new_page()

        new_storage_state = None # Será preenchido se um novo login for realizado

        try:
            print("--- Iniciando verificação de sessão e login condicional ---")
            cotacoes_url = "https://sisferweb.fertipar.com.br/logistica/paginas/cotacoesTransportadora/index.xhtml"
            
            # Navegue para a página de cotações para verificar o estado da sessão
            await page.goto(cotacoes_url, timeout=60000) # Increased timeout for initial navigation
            
            # Verifique se o elemento de login está visível. Se sim, a sessão é inválida.
            login_needed = False
            try:
                # Usar um seletor que é único da página de login
                await expect(page.locator("#filial_label")).to_be_visible(timeout=5000)
                login_needed = True
                print("[INFO] Elemento de login encontrado. Sessão inválida ou expirada.")
            except (TimeoutError, AssertionError):
                print("[INFO] Elemento de login NÃO encontrado. Sessão provavelmente ativa.")
                # Adicionalmente, verificar se a página de destino (dashboard) está correta
                try:
                    await expect(page.get_by_role("grid").first).to_be_visible(timeout=5000)
                    print("[INFO] Grid do dashboard encontrado. Sessão ativa e na página correta.")
                except TimeoutError:
                    print("[WARN] Grid do dashboard NÃO encontrado. A sessão pode estar ativa mas em uma página inesperada. Tentando login.")
                    login_needed = True # Force login if dashboard not found, even if login elements weren't initially visible.

            if login_needed:
                print("[INFO] Realizando novo login...")
                # --- ETAPA DE LOGIN COMPLETA (existente) ---
                await page.goto(url_login, timeout=60000)
                await page.locator("#filial_label").click()
                await page.get_by_role("option", name=filial).click()
                await page.get_by_role("textbox", name="Usuário").fill(usuario_site)
                await page.get_by_role("textbox", name="Senha").fill(senha_site)
                await page.get_by_role("button", name=" Acessar").click()
                await page.wait_for_load_state('networkidle', timeout=30000)
                print("Login realizado com sucesso.")

                # Após login, navegue e verifique novamente a página de cotações
                await page.goto(cotacoes_url, timeout=30000)
                await expect(page.get_by_role("grid").first).to_be_visible(timeout=10000)
                print("[SUCESSO] Navegação para 'Minhas Cotações' após novo login.")

                # Capture o novo estado da sessão
                new_storage_state = await context.storage_state()
            else:
                print("[SUCESSO] Sessão ativa e na página correta. Prosseguindo sem login.")
            
            # --- LÓGICA DA TABELA (a partir daqui o código original continua) ---
            print(f"Procurando pelo protocolo: {protocolo_procurado} e pedido: {pedido_procurado}...")
            # Note: The grid expectation was already checked during session validation/login
            linha_do_item = page.locator(f'//tr[contains(., "{protocolo_procurado}") and contains(., "{pedido_procurado}")]')

            if await linha_do_item.count() > 0:
                print(f"Protocolo {protocolo_procurado} e Pedido {pedido_procurado} encontrados!")
                botao_agendar = linha_do_item.locator(':text("Agendar Pedido")')
                await botao_agendar.click()
                
                # --- LÓGICA DE PREENCHIMENTO DE FORMULÁRIO REFINADA COM VALIDAÇÕES ---
                print("\n--- Iniciando preenchimento de dados do veículo e contato ---")
                
                # Preencher Contato
                contato_val = config.get("contato")
                if contato_val:
                    try:
                        await page.get_by_role("textbox", name="Contato*").fill(contato_val)
                        print(f"[SUCESSO] Campo 'Contato*' preenchido com: {contato_val}")
                    except TimeoutError:
                        print(f"[FALHA] Campo 'Contato*' não encontrado ou não editável. Valor: {contato_val}")
                else:
                    print("[INFO] Campo 'Contato' vazio no JSON. Pulando.")
                
                # Preencher DDD e Telefone
                telefone_completo = config.get("telefone")
                if telefone_completo:
                    match = re.search(r'\((\d{2})\)\s*(.*)', telefone_completo)
                    if match:
                        ddd, numero = match.group(1), match.group(2).strip()
                        try:
                            await page.get_by_role("textbox", name="DDD*").fill(ddd)
                            print(f"[SUCESSO] Campo 'DDD*' preenchido com: {ddd}")
                            await page.get_by_role("textbox", name="Telefone*").fill(numero)
                            print(f"[SUCESSO] Campo 'Telefone*' preenchido com: {numero}")
                        except TimeoutError:
                             print(f"[FALHA] Campos 'DDD*' ou 'Telefone*' não encontrados. Valores: DDD={ddd}, Telefone={numero}")
                    else:
                        print(f"[INFO] Formato de 'Telefone' inválido. Pulando. Valor: {telefone_completo}")
                else:
                    print("[INFO] Campo 'Telefone' vazio no JSON. Pulando.")
                
                # Preencher Placa Principal
                placa_principal = caminhao.get("placa")
                if placa_principal:
                    try:
                        await page.get_by_role("textbox", name="Placa*").fill(placa_principal)
                        print(f"[SUCESSO] Campo 'Placa*' preenchido com: {placa_principal}")
                    except TimeoutError:
                        print(f"[FALHA] Campo 'Placa*' não encontrado ou não editável. Valor: {placa_principal}")
                else:
                    print("[INFO] Campo 'Placa' principal vazio no JSON. Pulando.")

                # Selecionar UF da Placa (Dropdown)
                uf_placa = caminhao.get("uf")
                if uf_placa:
                    try:
                        await page.locator("[id='form-minhas-cotacoes:uf-placa_label']").click()
                        await page.locator(f"//li[@data-label='{uf_placa}']").click()
                        print(f"[SUCESSO] UF da Placa selecionada: {uf_placa}")
                    except TimeoutError:
                        print(f"[FALHA] Não foi possível selecionar a UF da Placa: {uf_placa}")
                else:
                    print("[INFO] Campo 'UF' da placa principal vazio no JSON. Pulando.")

                # Selecionar Tipo de Carroceria (Dropdown)
                tipo_carroceria = caminhao.get("tipo_carroceria")
                if tipo_carroceria:
                    try:
                        await page.locator("[id='form-minhas-cotacoes:tipoCarroceria_label']").click()
                        await page.locator(f"//li[@data-label='{tipo_carroceria}']").click()
                        print(f"[SUCESSO] Tipo de Carroceria selecionado: {tipo_carroceria}")
                    except TimeoutError:
                        print(f"[FALHA] Não foi possível selecionar o Tipo de Carroceria: {tipo_carroceria}")
                else:
                    print("[INFO] Campo 'Tipo de Carroceria' vazio no JSON. Pulando.")
                
                # Preencher Placa Reboque 1
                placa_reboque1 = caminhao.get("placa_reboque1")
                if placa_reboque1:
                    try:
                        await page.get_by_role("textbox", name="Placa Reboque 1*").fill(placa_reboque1)
                        print(f"[SUCESSO] Campo 'Placa Reboque 1*' preenchido com: {placa_reboque1}")
                    except TimeoutError:
                        print(f"[FALHA] Campo 'Placa Reboque 1*' não encontrado. Valor: {placa_reboque1}")
                else:
                    print("[INFO] Campo 'Placa Reboque 1' vazio no JSON. Pulando.")
                
                # Selecionar UF Reboque 1 (Dropdown)
                uf1 = caminhao.get("uf1")
                if uf1:
                    try:
                        await page.locator("[id='form-minhas-cotacoes:uf-reboque_label']").click() # Corrected locator
                        await page.locator(f"//li[@data-label='{uf1}']").click()
                        print(f"[SUCESSO] UF Reboque 1 selecionada: {uf1}")
                    except TimeoutError:
                        print(f"[FALHA] Não foi possível selecionar a UF Reboque 1: {uf1}")
                else:
                    print("[INFO] Campo 'UF Reboque 1' vazio no JSON. Pulando.")
                
                # Preencher Placa Reboque 2
                placa_reboque2 = caminhao.get("placa_reboque2")
                if placa_reboque2:
                    try:
                        await page.get_by_role("textbox", name="Placa Reboque 2").fill(placa_reboque2)
                        print(f"[SUCESSO] Campo 'Placa Reboque 2*' preenchido com: {placa_reboque2}")
                    except TimeoutError:
                        print(f"[FALHA] Campo 'Placa Reboque 2*' não encontrado. Valor: {placa_reboque2}")
                else:
                    print("[INFO] Campo 'Placa Reboque 2' vazio no JSON. Pulando.")

                # Selecionar UF Reboque 2 (Dropdown)
                uf2 = caminhao.get("uf2")
                if uf2:
                    try:
                        await page.locator("[id='form-minhas-cotacoes:uf-reboque-2_label']").click()
                        await page.locator(f"//li[@data-label='{uf2}']").click()
                        print(f"[SUCESSO] UF Reboque 2 selecionada: {uf2}")
                    except TimeoutError:
                        print(f"[FALHA] Não foi possível selecionar a UF Reboque 2: {uf2}")
                else:
                    print("[INFO] Campo 'UF Reboque 2' vazio no JSON. Pulando.")

                # Preencher Placa Reboque 3
                placa_reboque3 = caminhao.get("placa_reboque3")
                if placa_reboque3:
                    try:
                        await page.get_by_role("textbox", name="Placa Reboque 3").fill(placa_reboque3)
                        print(f"[SUCESSO] Campo 'Placa Reboque 3*' preenchido com: {placa_reboque3}")
                    except TimeoutError:
                        print(f"[FALHA] Campo 'Placa Reboque 3*' não encontrado. Valor: {placa_reboque3}")
                else:
                    print("[INFO] Campo 'Placa Reboque 3' vazio no JSON. Pulando.")

                # Selecionar UF Reboque 3 (Dropdown)
                uf3 = caminhao.get("uf3")
                if uf3:
                    try:
                        await page.locator("[id='form-minhas-cotacoes:uf-reboque-3_label']").click()
                        await page.locator(f"//li[@data-label='{uf3}']").click()
                        print(f"[SUCESSO] UF Reboque 3 selecionada: {uf3}")
                    except TimeoutError:
                        print(f"[FALHA] Não foi possível selecionar a UF Reboque 3: {uf3}")
                else:
                    print("[INFO] Campo 'UF Reboque 3' vazio no JSON. Pulando.")
                
                # Continuação do fluxo original...
                element_to_click = page.locator("[id=\"form-minhas-cotacoes:j_idt126\"]")
                await expect(element_to_click).to_be_visible(timeout=10000)
                await element_to_click.click()

                print("\nProcurando pelo iframe 'Cadastro de Motorista Autônomo'...")
                iframe_motorista = page.locator("iframe[title=\"Cadastro de Motorista Autônomo\"]")
                await expect(iframe_motorista).to_be_visible(timeout=15000)
                iframe_content = iframe_motorista.content_frame

                campo_cpf_iframe = await try_locate_and_screenshot(
                    page_object=page,
                    context_frame_or_page=iframe_content,
                    locators_with_names=[
                        # Novas tentativas de localização mais robustas
                        (iframe_content.locator("input[id*='Cpf']"), "CSS: input[id*='Cpf'] (partial ID)"),
                        (iframe_content.locator("input[name*='Cpf']"), "CSS: input[name*='Cpf'] (partial name)"),
                        (iframe_content.locator("input[id*='cpf']"), "CSS: input[id*='cpf'] (partial ID lowercase)"),
                        (iframe_content.locator("input[name*='cpf']"), "CSS: input[name*='cpf'] (partial name lowercase)"),
                        # Locators originais
                        (iframe_content.get_by_role("textbox", name="___.___.___-__"), "get_by_role(\"textbox\", name=\"___.___.___-__\")"),
                        (iframe_content.get_by_placeholder("Nro.Cpf"), "get_by_placeholder(\"Nro.Cpf\")")
                    ],
                    element_description="Campo 'Nro.Cpf'"
                )
                await expect(campo_cpf_iframe).to_be_editable(timeout=10000)
                
                # Preenchendo o CPF lentamente
                print(f"Preenchendo o campo CPF com: {nro_cpf}")
                await campo_cpf_iframe.type(nro_cpf, delay=150) # Adiciona um delay de 150ms entre cada caractere
                print("[SUCESSO] Campo CPF preenchido.")

                # Clicar no botão 'Pesquisar'
                botao_pesquisar_iframe = iframe_content.get_by_role("button", name=" Pesquisar")
                await expect(botao_pesquisar_iframe).to_be_visible(timeout=5000)
                await botao_pesquisar_iframe.click()
                print("Botão 'Pesquisar' foi clicado após preencher o CPF.")

                # Aguardar um momento para os resultados da pesquisa aparecerem
                await page.wait_for_timeout(2000)

                # --- LÓGICA CONDICIONAL: TENTAR 'SELECIONAR' E, SE FALHAR, TENTAR 'SIM' ---
                try:
                    # Tenta clicar em 'Selecionar' primeiro
                    print("Tentando clicar no botão 'Selecionar'...")
                    botao_selecionar = iframe_content.get_by_role("button", name=" Selecionar")
                    await expect(botao_selecionar).to_be_visible(timeout=7000) # Aumentar timeout para dar tempo da busca acontecer
                    await botao_selecionar.click()
                    print("[SUCESSO] Botão 'Selecionar' clicado.")
                except TimeoutError:
                    # Se 'Selecionar' não aparecer, pode ser que o motorista já esteja cadastrado
                    # e o sistema pergunte diretamente para confirmar
                    print("[INFO] Botão 'Selecionar' não encontrado. Tentando alternativa 'Sim'...")
                    botao_sim = iframe_content.get_by_role("button", name=" Sim")
                    await expect(botao_sim).to_be_visible(timeout=5000)
                    await botao_sim.click()
                    print("[SUCESSO] Botão 'Sim' clicado como alternativa.")

                print("Automação de agendamento concluída com sucesso.")

                # --- LÓGICA CONDICIONAL PARA SALVAR O AGENDAMENTO ---
                modo_execucao = config.get("modo_execucao", "producao") # Default para 'producao' se não for especificado

                salvar_button = page.get_by_role("button", name=" Salvar")
                await expect(salvar_button).to_be_visible(timeout=5000)
                
                if modo_execucao == "teste":
                    print("\n[MODO TESTE] EVENTO EM TESTE - NAO ESTA AGENDANDO!")
                    print("[MODO TESTE] O botão 'Salvar' foi identificado, mas não será clicado.")
                else:
                    print("\n[MODO PRODUCAO] EVENTO EM PRODUCAO - EFETUANDO AGENDANDAMENTO!")
                    # Força o clique no botão 'Salvar' para garantir a execução, mesmo que haja elementos sobrepostos.
                    await salvar_button.click(force=True)
                    print("[MODO PRODUCAO] O botão 'Salvar' foi clicado com sucesso.")

                # O navegador será fechado automaticamente ao finalizar a automação.
                return {"success": True, "message": "Agendamento processado com sucesso.", "new_storage_state": new_storage_state}
            else:
                message = f"Não há dados para pesquisar - motivo: sem agenda no site fertipar para Protocolo {protocolo_procurado} e Pedido {pedido_procurado}."
                print(message)
                return {"success": False, "message": message, "new_storage_state": new_storage_state}

        except Exception as e:
            tb_str = traceback.format_exc()
            error_log_message = f"--- ERRO RPA TASK PROCESSOR EM {datetime.now()} ---\n"
            error_log_message += f"\nErro inesperado: {e}\n"
            error_log_message += f"Traceback:\n{tb_str}\n"
            
            # Imprime o erro detalhado no console do Flask
            print(error_log_message)
            
            user_facing_message = "Ocorreu um erro durante a automação. Verifique o console para mais detalhes."
            if "Target page, context or browser has been closed" in tb_str:
                user_facing_message = "O navegador foi fechado inesperadamente durante a automação."
            elif isinstance(e, TimeoutError):
                 user_facing_message = "A automação excedeu o tempo de espera por um elemento na página."

            # Em caso de erro, o navegador será fechado automaticamente.

            return {"success": False, "message": tb_str, "user_facing_message": user_facing_message, "new_storage_state": new_storage_state}

        finally:
            # O navegador será fechado automaticamente ao finalizar a automação.
            if browser.is_connected():
                if run_headless_mode:
                    print("Finalizando automação e fechando o navegador.")
                    await browser.close()
                else:
                    print("Automação concluída. Pressione Enter no console para fechar o navegador...")
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, input)
                    await browser.close()
            else:
                print("Automação finalizada. O navegador já foi desconectado.")
