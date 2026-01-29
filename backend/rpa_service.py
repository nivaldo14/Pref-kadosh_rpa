import asyncio
from typing import List, Dict, Optional, Tuple
from playwright.async_api import async_playwright, Page, expect, TimeoutError
import re
import time # Importar módulo time para o timeout do loop
import traceback

async def monitor_agendamento_status(config: dict, protocolo: str, pedido: str) -> dict:
    """
    Monitors the status of a specific order on the Fertipar website until it is
    'APROVADO' or another final status (e.g., 'CANCELADO', 'RECUSADO').
    Includes a timeout for the monitoring loop.
    """
    if not config:
        raise ValueError("Configuration object is required.")

    url_login = config.get("url_acesso")
    filial = config.get("filial")
    usuario_site = config.get("usuario_site")
    senha_site = config.get("senha_site")
    storage_state = config.get("storage_state")

    # Define o tempo limite para o loop de monitoramento (2 horas)
    start_time = time.time()
    # TODO(monitor_agendamento_status): O limite de 2 horas será o tempo_espera_segundos que virá do banco de dados (ConfiguracaoRobo)
    # Por enquanto, mantido como 2 horas (7200 segundos) para fins de implementação inicial.
    timeout_seconds = 7200 

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=not config.get('head_evento', False), slow_mo=50)
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()

        new_storage_state = None

        try:
            # --- Login Logic (copied and adapted from rpa_task_processor) ---
            cotacoes_url = "https://sisferweb.fertipar.com.br/logistica/paginas/cotacoesTransportadora/index.xhtml"
            await page.goto(cotacoes_url, timeout=60000)

            login_needed = False
            try:
                await expect(page.locator("#filial_label")).to_be_visible(timeout=5000)
                login_needed = True
            except (TimeoutError, AssertionError):
                # If login form is not there, check if the main grid is.
                try:
                    await expect(page.get_by_role("grid").first).to_be_visible(timeout=5000)
                except TimeoutError:
                    login_needed = True # Not on login page, but not on dashboard either. Force login.

            if login_needed:
                print("[MONITOR] Performing new login...")
                await page.goto(url_login, timeout=60000)
                await page.locator("#filial_label").click()
                await page.get_by_role("option", name=filial).click()
                await page.get_by_role("textbox", name="Usuário").fill(usuario_site)
                await page.get_by_role("textbox", name="Senha").fill(senha_site)
                await page.get_by_role("button", name=" Acessar").click()
                await page.wait_for_load_state('networkidle', timeout=30000)
                new_storage_state = await context.storage_state()
                await page.goto(cotacoes_url, timeout=30000)
                await expect(page.get_by_role("grid").first).to_be_visible(timeout=10000)

            # --- Monitoring Loop ---
            # TODO(monitor_agendamento_status): Adicionar um contador de tentativas ou usar um tempo de espera mais dinâmico.
            while True:
                # 1. Verificar timeout do loop
                if time.time() - start_time > timeout_seconds:
                    message = f"Timeout de {timeout_seconds/3600} horas atingido. O status de agendamento para Protocolo {protocolo}, Pedido {pedido} não mudou de 'PENDENTE'."
                    print(f"[MONITOR] {message}")
                    return {"success": False, "status": "Falha", "message": message, "new_storage_state": new_storage_state}

                print(f"[MONITOR] Checking status for Protocolo: {protocolo}, Pedido: {pedido}")
                
                # 2. Buscar por pedido/protocolo no grid
                # Onde é feita a busca por pedido/protocolo
                linha_do_item = page.locator(f'//tr[contains(., "{protocolo}") and contains(., "{pedido}")]') # Adicionado " and contains(., "{pedido}")" para busca mais precisa.

                if await linha_do_item.count() > 0:
                    # Encontra o texto da coluna de status (assumindo 5ª coluna, índice 4)
                    status_text = (await linha_do_item.locator('td').nth(4).inner_text()).strip().upper()
                    print(f"[MONITOR] Found status: '{status_text}'")

                    # 3. Lógica de controle de status
                    if "APROVADO" in status_text:
                        # Onde o banco seria atualizado para APROVADO (chamador deve fazer)
                        return {"success": True, "status": "APROVADO", "message": "Agendamento aprovado.", "new_storage_state": new_storage_state}
                    elif "PENDENTE" in status_text:
                        print("[MONITOR] Status 'PENDENTE'. Recarregando a página e aguardando...")
                        # Onde ocorre o reload
                        await asyncio.sleep(config.get('tempo_espera_segundos', 30)) # Espera configurável antes de recarregar
                        await page.reload(wait_until="networkidle")
                        continue # Continua o loop para verificar novamente
                    else:
                        # Se encontrar situação diferente de "PENDENTE" e "APROVADO"
                        # Exemplo: "CANCELADO", "RECUSADO", "INDEFERIDO" ou qualquer outro texto.
                        message = f"Agendamento com status inesperado: '{status_text}'. Não será processado."
                        print(f"[MONITOR] {message}")
                        # Onde o banco seria atualizado para Falha (chamador deve fazer)
                        return {"success": False, "status": "Falha", "message": message, "new_storage_state": new_storage_state}
                else:
                    print(f"[MONITOR] Row for Protocolo {protocolo}, Pedido {pedido} not found yet. Refreshing...")
                    # Onde ocorre o reload (quando o item não é encontrado)
                    await asyncio.sleep(config.get('tempo_espera_segundos', 30)) # Espera configurável antes de recarregar
                    await page.reload(wait_until="networkidle")
                    # TODO(monitor_agendamento_status): Considerar adicionar um limite de tentativas para 'item not found'.
                    
        except Exception as e:
            tb_str = traceback.format_exc()
            print(f"[MONITOR] Erro inesperado durante o monitoramento: {e}\n{tb_str}")
            # Onde o banco seria atualizado para erro (chamador deve fazer)
            return {"success": False, "status": "erro", "message": tb_str, "new_storage_state": new_storage_state}
        finally:
            if browser.is_connected():
                await browser.close()

async def scrape_fertipar_data(config=None):
    """
    Scrapes data from the Fertipar website using Playwright.

    Args:
        config (ConfiguracaoRobo): An object containing robot configuration.

    Returns:
        list: A list of dictionaries, where each dictionary represents a row
              from the scraped table. Returns None on failure.
    """
    if config is None:
        print("Erro: scrape_fertipar_data foi chamada sem um objeto de configuração válido.")
        raise ValueError("O objeto de configuração (config) é obrigatório para a raspagem de dados.")
    
    scraped_data = []
    
    if not config.senha_site or not config.senha_site.strip():
        print("ERRO CRÍTICO: A senha do site para o robô não está configurada.")
        raise ValueError("Senha do robô não configurada. Por favor, acesse a página de 'Administração -> Configurações do Robô' e defina a senha.")
    
    # Extract config details
    url_acesso = config.url_acesso
    usuario_site = config.usuario_site
    senha_site = config.senha_site
    head_evento = config.head_evento

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not head_evento)
        page = await browser.new_page()

        try:
            await page.goto(url_acesso, timeout=60000)
            await page.wait_for_load_state('networkidle')
            
            is_on_login_page = "login.xhtml" in page.url
            
            if is_on_login_page:
                print("Página de login detectada. Iniciando processo de login...")
                username_selector = "#j_username"
                password_selector = "#j_password"
                login_button_selector = "#btLoginId"
                
                await page.fill(username_selector, usuario_site)
                await page.fill(password_selector, senha_site)

                if config.filial:
                    await page.locator("#filial_label").click()
                    await page.get_by_role("option", name=config.filial).click()
                
                await page.click(login_button_selector)
                
                try:
                    # Wait for navigation away from the login page (i.e., 'login.xhtml' should no longer be in the URL)
                    await page.wait_for_url(lambda url: "login.xhtml" not in url, timeout=30000)
                    print("Navegação pós-login bem-sucedida.")
                    await page.wait_for_load_state('networkidle', timeout=30000)
                    print("Estado de carregamento da rede 'networkidle' alcançado após login.")
                except TimeoutError:
                    print("Aviso: Falha na navegação pós-login. Provavelmente credenciais inválidas, problema de rede ou página travou.")
                    await page.screenshot(path="login_failure_screenshot.png")
                    print("Screenshot 'login_failure_screenshot.png' salvo para depuração.")
                    return [] # Indica falha no login, interrompe o processo, retorna lista vazia para compatibilidade.
            else:
                print("Já logado, pulando etapa de login.")

            if config.pagina_raspagem and config.pagina_raspagem not in page.url:
                print(f"Navegando para a página de raspagem: {config.pagina_raspagem}")
                await page.goto(config.pagina_raspagem, timeout=60000)
                await page.wait_for_load_state('networkidle', timeout=30000)

            print("Aguardando pela tabela de dados...")
            table_selector = 'table[role="grid"]'
            thead_selector = '#form-minhas-cotacoes\:tbFretes_head'
            
            try:
                await expect(page.locator(thead_selector)).to_be_visible(timeout=30000)
                print("Tabela encontrada.")
                headers = [th.strip() for th in await page.locator(f'{thead_selector} th').all_text_contents() if th.strip()]
                rows = await page.locator(f'{table_selector} tbody tr').all()
                print(f"Encontrado {len(rows)} linhas na tabela.")

                for row_element in rows:
                    cols_text = await row_element.locator('td').all_text_contents()
                    cols = [col.strip() for col in cols_text][1:]
                    
                    if len(cols) == len(headers):
                        row_data = dict(zip(headers, cols))
                        scraped_data.append(row_data)
                    else:
                        print(f"Aviso: Linha pulada por ter contagem de colunas diferente. Esperado {len(headers)}, encontrado {len(cols)}.")
            except (TimeoutError, AssertionError) as e:
                print(f"ERRO: Tabela de dados ('{thead_selector}') não encontrada após o tempo de espera. Salvando screenshot e HTML para depuração.")
                print(f"Playwright Error: {e}")
                await page.screenshot(path="rpa_error_screenshot.png")
                html_content = await page.content()
                with open("rpa_task_processor_error.log", "w", encoding='utf-8') as f:
                    f.write(html_content)
                print("Artefatos de depuração ('rpa_error_screenshot.png', 'rpa_task_processor_error.log') salvos.")
                return [] # Retorna uma lista vazia para indicar que não há dados, sem ser um erro fatal
        
        except Exception as e:
            print("--- ERRO FATAL NO RPA SERVICE ---")
            import traceback
            print(traceback.format_exc())
            print("---------------------------------")
            await page.screenshot(path="error_screenshot.png")
            print("Screenshot 'error_screenshot.png' salvo para depuração.")
            return []  # Sinaliza falha, retorna lista vazia para compatibilidade.

        finally:
            print("Fechando navegador.")
            await browser.close()
    
    if scraped_data:
        # Filtra apenas por 'PENDENTE' para o propósito de inicialização/exibição
        # A lógica de monitoramento e aprovação é feita em monitor_agendamento_status
        print(f"Raspagem concluída. Total de {len(scraped_data)} linhas. Filtrando por 'Situação' == 'PENDENTE'...")
        filtered_data = [row for row in scraped_data if row.get('Situação') and row.get('Situação').strip().upper() == 'PENDENTE']
        print(f"Encontrado {len(filtered_data)} linhas após filtro.")
        return filtered_data

    return scraped_data
