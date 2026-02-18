import time
import traceback
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright, Page, expect, TimeoutError as PlaywrightTimeoutError
import re
import os

# Importar a função de monitoramento
from rpa_service import monitor_agendamento_status

# Helper function
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


async def process_agendamento_main_task(rpa_params: dict, run_headless: bool = True):
    """
    Versão OTIMIZADA - Processa um agendamento no site da Fertipar usando Playwright.
    
    MELHORIAS IMPLEMENTADAS:
    1. Eliminação de navegações duplicadas
    2. Redução de timeouts desnecessários
    3. Uso de 'domcontentloaded' ao invés de 'networkidle'
    4. Verificação inteligente de sessão sem recarregar página
    5. Remoção de esperas fixas desnecessárias
    """
    # --- Extrair dados do dicionário rpa_params ---
    config = rpa_params.get("config", {})
    agenda_item = rpa_params.get("agenda", {})
    motorista = rpa_params.get("motorista", {})
    caminhao = rpa_params.get("caminhao", {})
    storage_state = rpa_params.get("storage_state")

    url_login = config.get("url_acesso")
    filial = config.get("filial")
    usuario_site = config.get("usuario_site")
    senha_site = config.get("senha_site")
    
    protocolo_procurado = agenda_item.get("fertipar_protocolo")
    pedido_procurado = agenda_item.get("fertipar_pedido")
    
    nro_cpf = (motorista.get("cpf") or "").replace('.', '').replace('-', '')

    def mask_cpf_for_assertion(unmasked_cpf):
        if len(unmasked_cpf) == 11:
            return re.sub(r'(\d{3})(\d{3})(\d{3})(\d{2})', r'\1.\2.\3-\4', unmasked_cpf)
        return unmasked_cpf
    
    masked_cpf = mask_cpf_for_assertion(nro_cpf)
    placa_principal = caminhao.get("placa")

    print(f"Iniciando automação para Protocolo: {protocolo_procurado}, Pedido: {pedido_procurado}, CPF: {nro_cpf}")

    async with async_playwright() as playwright:
        mostrar_tela = config.get('head_evento', False)
        run_headless_mode = not mostrar_tela
        
        print(f"Configuração 'head_evento' é {mostrar_tela}. Modo headless do navegador: {run_headless_mode}.")

        # OTIMIZAÇÃO: Remover slow_mo se não for necessário para debug
        browser = await playwright.chromium.launch(
            headless=run_headless_mode, 
            slow_mo=0,  # Removido delay (era 50ms)
            args=["--start-fullscreen"]
        )
        context = await browser.new_context(storage_state=storage_state if storage_state else {})
        page = await context.new_page()

        new_storage_state = None

        try:
            print("--- Iniciando verificação de sessão e login condicional ---")
            cotacoes_url = "https://sisferweb.fertipar.com.br/logistica/paginas/cotacoesTransportadora/index.xhtml"
            
            # OTIMIZAÇÃO 1: Navegar apenas uma vez inicialmente
            # Usar 'domcontentloaded' ao invés de aguardar todos os recursos
            await page.goto(cotacoes_url, wait_until='domcontentloaded', timeout=30000)
            
            # OTIMIZAÇÃO 2: Verificar sessão sem recarregar página
            login_needed = False
            try:
                # Verifica se está na tela de login
                await expect(page.locator("#filial_label")).to_be_visible(timeout=3000)
                login_needed = True
                print("[INFO] Elemento de login encontrado. Sessão inválida ou expirada.")
            except (TimeoutError, AssertionError):
                print("[INFO] Elemento de login NÃO encontrado. Verificando grid...")
                try:
                    # Verifica se o grid está presente
                    await expect(page.get_by_role("grid").first).to_be_visible(timeout=3000)
                    print("[INFO] Grid do dashboard encontrado. Sessão ativa e na página correta.")
                except TimeoutError:
                    print("[WARN] Grid do dashboard NÃO encontrado. Forçando login.")
                    login_needed = True

            if login_needed:
                print("[INFO] Realizando novo login...")
                # OTIMIZAÇÃO 3: Ir direto para URL de login
                await page.goto(url_login, wait_until='domcontentloaded', timeout=30000)
                
                await page.locator("#filial_label").click()
                await page.get_by_role("option", name=filial).click()
                await page.get_by_role("textbox", name="Usuário").fill(usuario_site)
                await page.get_by_role("textbox", name="Senha").fill(senha_site)
                await page.get_by_role("button", name=" Acessar").click()
                
                # OTIMIZAÇÃO 4: Usar 'load' ao invés de 'networkidle' (muito mais rápido)
                await page.wait_for_load_state('load', timeout=15000)
                print("Login realizado com sucesso.")

                # OTIMIZAÇÃO 5: Navegar para cotações com timeout menor
                await page.goto(cotacoes_url, wait_until='domcontentloaded', timeout=20000)
                await expect(page.get_by_role("grid").first).to_be_visible(timeout=8000)

                print("[SUCESSO] Navegação para 'Minhas Cotações' após novo login.")
                new_storage_state = await context.storage_state()
            else:
                print("[SUCESSO] Sessão ativa e na página correta. Prosseguindo sem login.")
            
            # --- CHAMA A FUNÇÃO DE MONITORAMENTO DE STATUS ---
            print("\n--- Chamando monitor_agendamento_status para verificar o protocolo/pedido ---")
            monitor_result = await monitor_agendamento_status(
                page=page, 
                config={"tempo_espera_segundos": config.get("tempo_espera_segundos", 30)},
                protocolo=protocolo_procurado, 
                pedido=pedido_procurado
            )

            if monitor_result.get('status') != "APROVADO":
                # Se não está APROVADO, retorna o resultado do monitoramento diretamente
                return monitor_result

            # --- CONTINUA O PROCESSO SE APROVADO ---
            print(f"\n[CONTINUANDO] Status APROVADO. Prosseguindo com automação de agendamento para Protocolo {protocolo_procurado} e Pedido {pedido_procurado}.")
            
            # Procurar a linha no grid
            all_rows = page.get_by_role("row").all()
            rows = await all_rows
            linha_encontrada = None

            for row in rows:
                content = await row.text_content()
                if protocolo_procurado in content and pedido_procurado in content:
                    print(f"Linha encontrada: {content[:200]}")
                    linha_encontrada = row
                    break
            
            if linha_encontrada:
                # Clicar na linha
                await linha_encontrada.click()
                print("Linha clicada.")
                
                # OTIMIZAÇÃO 6: Reduzir timeout de espera
                await page.wait_for_timeout(1000)  # Era 2000ms, agora 1000ms
                
                # Botão Agendar
                #componetne na pagina fertipar
                #page.get_by_role("button", name=" Salvar").click()
                
                #try:
                #agendar_button = page.get_by_role("button", name=" Agendar")
                # senao expect(page.locator("[id=\"form-minhas-cotacoes:j_idt133\"]")).to_match_aria_snapshot("- text: Salvar")
                agendar_button = page.get_by_role("button", name=" Salvar")
                #agendar_button = page.get_by_role("button", name=" Salvar")
                await expect(agendar_button).to_be_visible(timeout=5000)
                await agendar_button.click()
                print("Botão 'Agendar' clicado.")
                #except Exception as e:
                        # locator = page.locator('[id="form-minhas-cotacoes:j_idt133"]')
                        # # Verifica se o componente tem o texto/aria esperado
                        # await expect(locator).to_match_aria_snapshot("- text: Salvar")
                        # await locator.click()
                #        print("Botão 'Salvar' clicado via locator (fallback). ")    

                # Aguardar modal
                await page.wait_for_timeout(1000)  # Era 2000ms

                # --- Processar modal de agendamento ---
                iframe_element = await page.query_selector("iframe")
                iframe_content = await iframe_element.content_frame()

                # Data
                date_locator = iframe_content.get_by_role("textbox", name="Data")
                await expect(date_locator).to_be_visible(timeout=5000)
                await date_locator.click()
                
                await page.wait_for_timeout(500)  # Reduzido de 1000ms
                
                dates = await iframe_content.get_by_label("Choose date").all()
                if dates:
                    await dates[0].click()

                # Seleção de turno e horário
                await iframe_content.locator("#turno_label").click()
                await iframe_content.get_by_role("option", name="Manhã").click()

                # Horário com timeout reduzido
                await page.wait_for_timeout(500)
                horarios = await iframe_content.locator('td[role="gridcell"]').all()
                if horarios:
                    await horarios[0].click()
                    print("Primeiro horário selecionado.")

                # Veículos
                veiculos_panel = iframe_content.locator('div[id*="tipoVeiculosAgendamento"]')
                await expect(veiculos_panel).to_be_visible(timeout=5000)
                
                veiculos_options = await veiculos_panel.locator('div.ui-chkbox').all()
                if veiculos_options:
                    await veiculos_options[0].click()
                    print("Primeiro veículo selecionado.")

                # CPF e Placa
                await iframe_content.get_by_placeholder("Informe o CPF do motorista").fill(nro_cpf)
                
                # OTIMIZAÇÃO 7: Buscar placa sem espera desnecessária
                await iframe_content.get_by_placeholder("Informe a placa do veículo").fill(placa_principal)
                await page.wait_for_timeout(500)  # Reduzido
                await iframe_content.get_by_placeholder("Informe a placa do veículo").press("Enter")

                # Confirmação
                await page.wait_for_timeout(1500)  # Tempo mínimo necessário
                
                try:
                    botao_ok = iframe_content.get_by_role("button", name="OK")
                    await expect(botao_ok).to_be_visible(timeout=3000)
                    await botao_ok.click()
                    print("[SUCESSO] Botão 'OK' clicado.")
                except (TimeoutError, AssertionError):
                    print("[INFO] Botão 'OK' não encontrado. Tentando alternativa 'Sim'.")
                    botao_sim = iframe_content.get_by_role("button", name=" Sim")
                    await expect(botao_sim).to_be_visible(timeout=3000)
                    await botao_sim.click()
                    print("[SUCESSO] Botão 'Sim' clicado como alternativa.")

                print("Automação de agendamento concluída com sucesso.")

                # Salvar
                modo_execucao = config.get("modo_execucao", "producao")
                salvar_button = page.get_by_role("button", name=" Salvar")
                await expect(salvar_button).to_be_visible(timeout=5000)
                
                if modo_execucao == "teste":
                    print("\n[MODO TESTE] EVENTO EM TESTE - NAO ESTA AGENDANDO!")
                    print("[MODO TESTE] O botão 'Salvar' foi identificado, mas não será clicado.")
                    return {
                        "success": True, 
                        "message": "Modo de teste: Agendamento não salvo.", 
                        "new_storage_state": new_storage_state
                    }
                else:
                    print("\n[MODO PRODUCAO] EVENTO EM PRODUCAO - EFETUANDO AGENDANDAMENTO!")
                    await salvar_button.click(force=True)
                    
                    # OTIMIZAÇÃO 8: Reduzir espera após salvar
                    await page.wait_for_timeout(2000)  # Era 3000ms
                    
                    # Verificar erros
                    erro_locator = page.locator(".ui-messages-error-icon")
                    os.makedirs("erro_screenimg", exist_ok=True)
                    
                    agora = datetime.now()
                    nome_arquivo = f"pt{protocolo_procurado}_pd{pedido_procurado}_{agora.hour:02d}{agora.minute:02d}.png"
                    caminho = os.path.join("erro_screenimg", nome_arquivo)

                    try:
                        await erro_locator.wait_for(state="visible", timeout=4000)  # Reduzido de 5000ms
                        texto_erro = (await erro_locator.inner_text()).strip()
                        print(f"[RPA] Salvar FALHOU. Mensagem: {texto_erro}")
                        
                        page_content = await page.content()
                        print("[AVISO] Status de agendamento indeterminado. Conteúdo da página após salvar (parcial):\n" + page_content[:1000] + "...")
                        
                        await page.screenshot(path=caminho)
                       
                        return {
                            "success": False,
                            "status": "erro",
                            "message": "Não foi possível determinar o status do agendamento após salvar. Verifique o screenshot e o log.",
                            "user_facing_message": "Não foi possível determinar o status do agendamento. Verifique o log para detalhes.",
                            "new_storage_state": new_storage_state,
                            "cam_erro_img": caminho
                        }
                    except PlaywrightTimeoutError:
                        print("[RPA] Salvar OK, nenhum alerta de erro visível.")
                        return {
                            "success": True, 
                            "status": "agendado", 
                            "message": "Agendamento processado com sucesso.", 
                            "new_storage_state": new_storage_state,
                            "cam_erro_img": caminho
                        }
            else:
                message = f"Não foi possível localizar o protocolo {protocolo_procurado} e pedido {pedido_procurado} no grid para iniciar o agendamento, mesmo após o monitoramento inicial ter sinalizado 'APROVADO'."
                print(message)
                return {
                    "success": False, 
                    "status": "erro", 
                    "message": message, 
                    "new_storage_state": new_storage_state
                }

        except Exception as e:
            tb_str = traceback.format_exc()
            error_log_message = f"--- ERRO RPA TASK PROCESSOR EM {datetime.now()} ---\n"
            error_log_message += f"\nErro inesperado: {e}\n"
            error_log_message += f"Traceback:\n{tb_str}\n"
            
            print(error_log_message)
            
            user_facing_message = "Ocorreu um erro durante a automação. Verifique o console para mais detalhes."
            if "Target page, context or browser has been closed" in tb_str:
                user_facing_message = "O navegador foi fechado inesperadamente durante a automação."
            elif isinstance(e, TimeoutError):
                 user_facing_message = "A automação excedeu o tempo de espera por um elemento na página."

            return {
                "success": False, 
                "status": "erro", 
                "message": tb_str, 
                "user_facing_message": user_facing_message, 
                "new_storage_state": new_storage_state
            }

        finally:
            if browser.is_connected():
                if run_headless_mode:
                    print("Finalizando automação e fechando o navegador.")
                    await browser.close()
                else:
                    print("Automação concluída. Aguardando 10 segundos para fechar o navegador...")
                    await asyncio.sleep(10)
                    await browser.close()
            else:
                print("Automação finalizada. O navegador já foi desconectado.")