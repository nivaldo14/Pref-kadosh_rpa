import time
import traceback
import asyncio
from datetime import datetime # Adicionado
from playwright.async_api import async_playwright, Page, expect, TimeoutError
import re # Adicionado import re

# Helper function from modeloBot/main.py
async def try_locate_and_screenshot(page_object, context_frame_or_page, locators_with_names, element_description):
    """
    Tenta localizar um elemento usando uma lista de locators, tira um screenshot se encontrar.

    Args:
        page_object: O objeto 'page' principal do Playwright (para screenshots da página inteira).
        context_frame_or_page: O objeto page ou frame do Playwright onde procurar o elemento.
        locators_with_names: Uma lista de tuplas (locator_object, locator_description)
                             onde locator_object é o localizador do Playwright
                             (ex: iframe_content.get_by_role("textbox", name="Nome"))
                             e locator_description é uma string descritiva.
        element_description: Uma descrição geral do elemento para mensagens de log e nome do arquivo de screenshot.

    Returns:
        O objeto Locator do Playwright se o elemento for encontrado e visível.

    Raises:
        Exception: Se o elemento não for encontrado por nenhum dos locators fornecidos.
    """
    print(f"\n--- Tentando localizar: '{element_description}' ---")
    for locator_object, locator_description in locators_with_names:
        try:
            await expect(locator_object).to_be_visible(timeout=5000)
            print(f"  [SUCESSO] Elemento '{element_description}' encontrado e visível com: '{locator_description}'.")
            
            # Tira screenshot usando o objeto 'page' principal
            screenshot_path = f"screenshot_{element_description.replace(' ', '_').replace('.', '')}_found.png"
            await page_object.screenshot(path=screenshot_path) # Usar page_object aqui
            print(f"  Screenshot salvo em: {screenshot_path}")
            
            return locator_object
        except TimeoutError:
            print(f"  [FALHA] Seletor '{locator_description}' não visível no tempo. Tentando próximo seletor.")
        except Exception as e:
            print(f"  [FALHA] Seletor '{locator_description}' falhou. Erro: {e}")
            
    raise Exception(f"Elemento '{element_description}' não foi encontrado por nenhum dos seletores fornecidos.")


async def process_agendamento_main_task(config, agenda_item, motorista, caminhao, run_headless: bool = True):
    """
    Processa um agendamento no site da Fertipar usando Playwright.
    Adapta a lógica de modeloBot/main.py para usar dados dinâmicos.
    """
    url_login = config.url_acesso
    filial = config.filial
    usuario_site = config.usuario_site
    senha_site = config.senha_site
    protocolo_procurado = agenda_item.fertipar_protocolo
    pedido_procurado = agenda_item.fertipar_pedido # Adicionado para buscar também o pedido
    nro_cpf = motorista.cpf.replace('.', '').replace('-', '') # Limpar CPF para preenchimento
    
    print(f"Iniciando automação para Protocolo: {protocolo_procurado}, Pedido: {pedido_procurado}, CPF: {nro_cpf}")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=run_headless, slow_mo=50, args=["--start-fullscreen"]) # headless agora é controlado por run_headless
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # --- ETAPA DE LOGIN ---
            print("Executando a sequência de login...")
            await page.goto(url_login, timeout=60000)
            
            await page.locator("#filial_label").click()
            await page.get_by_role("option", name=filial).click()
            
            await page.get_by_role("textbox", name="Usuário").fill(usuario_site)
            await page.get_by_role("textbox", name="Senha").fill(senha_site)

            await page.get_by_role("button", name=" Acessar").click()
            await page.wait_for_load_state('networkidle', timeout=30000)
            print("Login realizado com sucesso.")

            # --- NAVEGAÇÃO PÓS-LOGIN ---
            print("Navegando para 'Minhas Cotações'...")
            await page.get_by_role("link", name=" Minhas Cotaçoes").click()
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            # --- LÓGICA DA TABELA ---
            print(f"Procurando pelo protocolo: {protocolo_procurado} e pedido: {pedido_procurado}...")
            
            # Espera a grade de dados (tabela) ficar visível
            await expect(page.get_by_role("grid").first).to_be_visible(timeout=30000)

            # Localiza a linha (tr) que contém o texto do protocolo E do pedido
            linha_do_item = page.locator(f'//tr[contains(., "{protocolo_procurado}") and contains(., "{pedido_procurado}")]')

            if await linha_do_item.count() > 0:
                print(f"Protocolo {protocolo_procurado} e Pedido {pedido_procurado} encontrados!")
                
                # Clica no botão 'Agendar Pedido' na linha encontrada
                botao_agendar = linha_do_item.locator(':text("Agendar Pedido")')
                await botao_agendar.click()
                
                # --- INÍCIO PREENCHIMENTO CONTATO/TELEFONE (ANTES DO IFRAME) ---
                print("\n--- Iniciando preenchimento de Contato e Telefone ---")
                try:
                    # Esperar que o campo de contato apareça.
                    print("Aguardando o formulário de contato carregar...")
                    # O locator exato para o campo de contato pode precisar de ajuste.
                    # Vamos usar um locator genérico por enquanto e esperar que ele seja editável.
                    # Baseado no código existente, o campo está dentro de um container.
                    # Vamos esperar o container e depois pegar o input.
                    #contact_container_locator = page.locator('[id="form-minhas-cotacoes:placas-reboque"]')
                    #await expect(contact_container_locator).to_be_visible(timeout=10000)
                    print("Container de contato/telefone detectado.")

                    # Preencher Contato
                    if config.contato:
                        print("Tentando localizar e preencher o campo 'Contato*'...")
                        contato_textbox = page.get_by_role("textbox", name="Contato*")
                        try:
                            await expect(contato_textbox).to_be_visible(timeout=5000)
                            await contato_textbox.fill(config.contato)
                            print(f"[SUCESSO] Campo 'Contato*' preenchido com: {config.contato}")
                        except TimeoutError:
                            print(f"[FALHA] Campo 'Contato*' não encontrado ou não visível. Valor esperado: {config.contato}")
                        except Exception as e:
                            print(f"[ERRO] Ocorreu um erro inesperado ao tentar preencher 'Contato*': {e}")
                    else:
                        print("[INFO] Campo 'contato' não configurado no config. Pulando preenchimento.")

                    # Preencher DDD e Telefone
                    if config.telefone:
                        print("Preenchendo DDD e Telefone...")
                        ddd_match = re.search(r'\((\d+)\)', config.telefone)
                        numero_match = re.search(r'\)\s*(.*)', config.telefone)
                        
                        if ddd_match:
                            ddd = ddd_match.group(1)
                            ddd_input = page.get_by_role("textbox", name="DDD*")
                            await expect(ddd_input).to_be_editable(timeout=5000)
                            await ddd_input.fill(ddd)
                            print(f"[SUCESSO] Campo 'DDD*' preenchido com: {ddd}")
                        
                        if numero_match:
                            numero = numero_match.group(1)
                            tel_input = page.get_by_role("textbox", name="Telefone*")
                            await expect(tel_input).to_be_editable(timeout=5000)
                            await tel_input.fill(numero)
                            print(f"[SUCESSO] Campo 'Telefone*' preenchido com: {numero}")
                    else:
                        print("[INFO] Campo 'telefone' não configurado. Pulando.")

                except TimeoutError as te:
                    print(f"[AVISO] Timeout ao tentar preencher Contato/Telefone antes do iframe. O fluxo pode ter mudado ou os campos não são esperados aqui. Erro: {te}")
                except Exception as e:
                    print(f"[AVISO] Ocorreu um erro inesperado ao preencher Contato/Telefone antes do iframe. Erro: {e}")
                # --- FIM PREENCHIMENTO CONTATO/TELEFONE ---

                element_to_click = page.locator("[id=\"form-minhas-cotacoes:j_idt126\"]")
                await expect(element_to_click).to_be_visible(timeout=10000)
                await element_to_click.click()

                print("\nProcurando pelo iframe 'Cadastro de Motorista Autônomo'...")
                iframe_motorista = page.locator("iframe[title=\"Cadastro de Motorista Autônomo\"]")
                await expect(iframe_motorista).to_be_visible(timeout=15000)
                iframe_content = iframe_motorista.content_frame

                # --- INTERAGINDO COM O CAMPO 'NRO.CPF' NO IFRAME ---
                campo_cpf = await try_locate_and_screenshot(
                    page_object=page,
                    context_frame_or_page=iframe_content,
                    locators_with_names=[
                        (iframe_content.get_by_role("textbox", name="___.___.___-__"), "get_by_role(\"textbox\", name=\"___.___.___-__\")"),
                        (iframe_content.get_by_placeholder("Nro.Cpf"), "get_by_placeholder(\"Nro.Cpf\")")
                    ],
                    element_description="Campo 'Nro.Cpf'"
                )
                await expect(campo_cpf).to_be_editable(timeout=10000)
                await campo_cpf.fill(nro_cpf)
                print(f"[SUCESSO] Campo 'Nro.Cpf' preenchido com: {nro_cpf}")

                # Clica no botão pesquisar
                botao_pesquisar = iframe_content.get_by_role("button", name=" Pesquisar")
                await expect(botao_pesquisar).to_be_visible(timeout=5000)
                await botao_pesquisar.click()
                print("[SUCESSO] Botão 'Pesquisar' clicado.")
                
                # --- LÓGICA CONDICIONAL: TENTAR 'SELECIONAR' E, SE FALHAR, TENTAR 'SIM' ---
                try:
                    botao_selecionar = iframe_content.get_by_role("button", name=" Selecionar")
                    await expect(botao_selecionar).to_be_visible(timeout=5000)
                    await botao_selecionar.click()
                    print("[SUCESSO] Botão 'Selecionar' clicado.")
                except TimeoutError:
                    print("[INFO] Botão 'Selecionar' não encontrado. Tentando alternativa 'Sim'.")
                    botao_sim = iframe_content.get_by_role("button", name=" Sim")
                    await expect(botao_sim).to_be_visible(timeout=5000)
                    await botao_sim.click()
                    print("[SUCESSO] Botão 'Sim' clicado como alternativa.")

                # O bloco de preenchimento de placa foi removido conforme solicitado.
                
                # --- ETAPA FINAL: PREENCHER CPF NO CADASTRO DE VEÍCULO/MOTORISTA (SE NECESSÁRIO) ---
                # A lógica do main.py sugere que um segundo campo CPF pode aparecer.
                # Se esta seção é para um novo cadastro, preencher o nome e telefone também.
                # Por simplicidade, assumindo que já existe ou só precisa do CPF novamente.
                dialogo_final = page.locator('[id="formPesquisaTransp:j_idt24_dlg"]')
                if await dialogo_final.is_visible():
                    print("Diálogo final de motorista visível. Preenchendo CPF novamente.")
                    final_frame_locator = dialogo_final.frame_locator('iframe[title="Cadastro de Motorista Autônomo"]')
                    campo_cpf_final = final_frame_locator.get_by_role("textbox", name="CPF*")
                    await expect(campo_cpf_final).to_be_editable(timeout=10000)
                    await campo_cpf_final.fill(nro_cpf)
                    print(f"[SUCESSO] Campo 'CPF*' final preenchido com: {nro_cpf}")

                # Se a lógica de main.py continuar a partir daqui para preencher dados do caminhão
                # ou outros detalhes, precisaremos adaptar. Por agora, o foco é o motorista.
                print("Automação de agendamento concluída com sucesso para o motorista.")
                return {"success": True, "message": "Agendamento do motorista processado com sucesso."}

            else:
                message = f"Não ha dados para pesquisar - motivo sem agenda no site fertipar para Protocolo {protocolo_procurado} e Pedido {pedido_procurado}."
                print(message)
                return {"success": False, "message": message}

        except TimeoutError as e:
            await page.screenshot(path="timeout_error.png")
            message = f"Timeout durante a automação: {e}. Screenshot salvo como timeout_error.png"
            print(message)
            return {"success": False, "message": message}
        except Exception as e:
            tb_str = traceback.format_exc()
            error_log_message = f"--- ERRO RPA TASK PROCESSOR EM {datetime.now()} ---\n"
            error_log_message += f"Erro inesperado: {e}\n"
            error_log_message += f"Traceback:\n{tb_str}\n"
            
            # Write full traceback to log file
            with open("rpa_task_processor_error.log", "a", encoding='utf-8') as f:
                f.write(error_log_message)
            
            await page.screenshot(path="rpa_error_screenshot.png")
            
            # Check for specific "element(s) not found" error
            specific_error_pattern = r"Locator expected to be visible\nActual value: None\nError: element\(s\) not found"
            
            if isinstance(e, AssertionError) and re.search(specific_error_pattern, str(e)):
                user_message = "Não há agenda programadas!"
                print(f"Ocorreu um erro específico: {user_message}. Detalhes em rpa_task_processor_error.log")
                print(f"DEBUG: tb_str length: {len(tb_str)}") # Debug print
                print(f"DEBUG: tb_str content:\n{tb_str}") # Debug print
                # Retorna o traceback para o log_retorno e a mensagem user-friendly para o frontend
                return {"success": False, "message": tb_str, "user_facing_message": user_message}
            else:
                # General error, return full traceback string for log_retorno in DB
                print(f"Ocorreu um erro inesperado durante a automação: {e}. Detalhes em rpa_task_processor_error.log")
                print(f"DEBUG: tb_str length: {len(tb_str)}") # Debug print
                print(f"DEBUG: tb_str content:\n{tb_str}") # Debug print
                return {"success": False, "message": tb_str} # Return full traceback string for log_retorno

        finally:
            print("\n[MODO DEBUG] Navegador permanecerá aberto para inspeção.")
            print("Pressione ENTER no console para fechar o navegador e finalizar a automação.")
            # Use asyncio.to_thread para rodar input() sem bloquear o loop de eventos
            await asyncio.to_thread(input, "") 
            await browser.close()
            print("Navegador fechado por solicitação do usuário.")
