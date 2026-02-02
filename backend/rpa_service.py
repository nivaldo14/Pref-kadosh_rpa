import asyncio
from typing import List, Dict, Optional, Tuple
from playwright.async_api import async_playwright, Page, expect, TimeoutError
import re
import time # Importar módulo time para o timeout do loop
import traceback
from datetime import datetime # Importar datetime para a verificação de horário

async def monitor_agendamento_status(page: Page, config: dict, protocolo: str, pedido: str) -> dict:
    """
    Monitors the status of a specific order on the Fertipar website using an existing Page object.
    Includes a timeout for the monitoring loop and a hard stop at 17:30.
    """
    if not config:
        raise ValueError("Configuration object is required.")
    if not page:
        raise ValueError("A Playwright Page object is required.")

    start_time = time.time()
    timeout_seconds = 7200  # 2 horas

    try:
        # A página já deve estar logada e na URL correta, vinda do process_agendamento_main_task
        print("[MONITOR] Iniciando monitoramento na página existente.")

        # --- Monitoring Loop ---
        while True:
            # 1. Verificar timeout do loop
            if time.time() - start_time > timeout_seconds:
                message = f"Timeout de {timeout_seconds/3600} horas atingido. O status para Protocolo {protocolo} não mudou de 'PENDENTE'."
                print(f"[MONITOR] {message}")
                return {"success": False, "status": "Falha", "message": message}

            # 2. Verificar horário limite de 17:30
            now = datetime.now()
            if now.hour > 17 or (now.hour == 17 and now.minute >= 30):
                message = 'Site indisponivel! horario fechado o acesso'
                print(f"[MONITOR] {message}")
                return {"success": False, "status": "indisponivel", "message": message}

            print(f"[MONITOR] Checando status para Protocolo: {protocolo}, Pedido: {pedido}")
            
            # 3. Buscar por pedido/protocolo no grid
            linha_do_item = page.locator(f'//tr[contains(., "{protocolo}") and contains(., "{pedido}")]')

            if await linha_do_item.count() > 0:
                status_text = (await linha_do_item.locator('td').nth(4).inner_text()).strip().upper()
                print(f"[MONITOR] Status encontrado: '{status_text}'")

                if "APROVADO" in status_text:
                    return {"success": True, "status": "APROVADO", "message": "Agendamento aprovado."}
                elif "PENDENTE" in status_text:
                    print("[MONITOR] Status 'PENDENTE'. Aguardando e recarregando a página...")
                    await asyncio.sleep(config.get('tempo_espera_segundos', 30))
                    await page.reload(wait_until="networkidle")
                    continue
                else:
                    message = f"Agendamento com status final inesperado: '{status_text}'. O processo será interrompido."
                    print(f"[MONITOR] {message}")
                    return {"success": False, "status": "Falha", "message": message}
            else:
                print(f"[MONITOR] Protocolo {protocolo} não encontrado. Aguardando e recarregando...")
                await asyncio.sleep(config.get('tempo_espera_segundos', 30))
                await page.reload(wait_until="networkidle")
                
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"[MONITOR] Erro inesperado: {e}\n{tb_str}")
        return {"success": False, "status": "erro", "message": tb_str}


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
        #filtered_data = [row for row in scraped_data  if row.get('Situação') and row.get('Situação').strip().upper() in ('PENDENTE', 'APROVADO')]
        print(f"Encontrado {len(filtered_data)} linhas após filtro.")
        return filtered_data

    return scraped_data
