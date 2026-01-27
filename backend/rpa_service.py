import asyncio
from typing import List, Dict, Optional, Tuple
from playwright.async_api import async_playwright, Page, expect, TimeoutError
import re
from time import sleep
import traceback

async def monitor_agendamento_status(config: dict, protocolo: str, pedido: str) -> dict:
    """
    Monitors the status of a specific order on the Fertipar website until it is
    'APROVADO' or 'RECUSADO'.
    """
    if not config:
        raise ValueError("Configuration object is required.")

    url_login = config.get("url_acesso")
    filial = config.get("filial")
    usuario_site = config.get("usuario_site")
    senha_site = config.get("senha_site")
    storage_state = config.get("storage_state")

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
            while True:
                print(f"[MONITOR] Checking status for Protocolo: {protocolo}, Pedido: {pedido}")
                
                # Find the row
                linha_do_item = page.locator(f'//tr[contains(., "{protocolo}") and contains(., "{pedido}")]')

                if await linha_do_item.count() > 0:
                    # Find the status column within that row. Assuming 'Situação' is the 5th column (index 4)
                    # This might need adjustment based on the actual table structure.
                    status_text = await linha_do_item.locator('td').nth(4).inner_text()
                    print(f"[MONITOR] Found status: '{status_text}'")

                    if "APROVADO" in status_text.upper():
                        return {"success": True, "status": "APROVADO", "new_storage_state": new_storage_state}
                    elif "RECUSADO" in status_text.upper():
                        return {"success": False, "status": "RECUSADO", "message": "O agendamento foi recusado.", "new_storage_state": new_storage_state}
                    # Else, it's PENDENTE, so we continue the loop
                else:
                    print(f"[MONITOR] Row for Protocolo {protocolo} not found yet.")

                # Wait and refresh
                print("[MONITOR] Status is PENDENTE or not found. Waiting 1 second and refreshing...")
                await asyncio.sleep(1)
                await page.reload(wait_until="networkidle")

        except Exception as e:
            tb_str = traceback.format_exc()
            return {"success": False, "status": "ERRO", "message": tb_str}
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
                    return None # Indica falha no login, interrompe o processo.
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
            return None  # Sinaliza falha

        finally:
            print("Fechando navegador.")
            await browser.close()
    
    if scraped_data:
        print(f"Raspagem concluída. Total de {len(scraped_data)} linhas. Filtrando por 'Situação' == 'PENDENTE' ou 'APROVADO'...")
        filtered_data = [row for row in scraped_data if row.get('Situação') in ['PENDENTE', 'APROVADO']]
        print(f"Encontrado {len(filtered_data)} linhas após filtro.")
        return filtered_data

    return scraped_data
