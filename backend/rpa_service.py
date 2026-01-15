import asyncio
from typing import List, Dict, Optional, Tuple
from playwright.async_api import async_playwright, Page, expect, TimeoutError

async def scrape_fertipar_data(config):
    """
    Scrapes data from the Fertipar website using Playwright.

    Args:
        config (ConfiguracaoRobo): An object containing robot configuration,
                                  including url_acesso, usuario_site,
                                  senha_site, and head_evento.

    Returns:
        list: A list of dictionaries, where each dictionary represents a row
              from the scraped table. Returns an empty list if no data is found
              or on failure.
    """
    scraped_data = []
    
    # Extract config details
    url_acesso = config.url_acesso
    usuario_site = config.usuario_site
    senha_site = config.senha_site # Get plain text password
    head_evento = config.head_evento # True for visible browser, False for headless

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Sempre executa em modo headless
        page = await browser.new_page()

        try:
            await page.goto(url_acesso, timeout=60000)

            # Aguarda a página carregar e verifica se já estamos logados (redirecionados para a página de raspagem)
            await page.wait_for_load_state('networkidle')
            
            is_on_login_page = "login.xhtml" in page.url
            
            if is_on_login_page:
                # --- Processo de Login ---
                # Seletores exatos fornecidos pelo usuário
                username_selector = "#j_username" # ID exato
                password_selector = "#j_password" # ID exato
                filial_selector = "#filial_input" # ID exato para o <select>
                login_button_selector = "#btLoginId" # ID exato para o botão
                
                # 1. Preencher usuário
                await expect(page.locator(username_selector)).to_be_visible(timeout=10000)
                await page.fill(username_selector, usuario_site)
                
                # 2. Preencher senha
                await expect(page.locator(password_selector)).to_be_visible(timeout=5000)
                await page.fill(password_selector, senha_site)

                # 3. Selecionar a filial (componente customizado)
                if config.filial:
                    # Clica no label do dropdown para abrir as opções
                    await page.locator("#filial_label").click()
                    # Clica na opção com o nome correspondente
                    await page.get_by_role("option", name=config.filial).click()
                
                # 4. Clicar em Entrar
                await expect(page.locator(login_button_selector)).to_be_enabled(timeout=5000)
                await page.click(login_button_selector)
                
                await page.wait_for_load_state('networkidle', timeout=30000)
            else:
                pass # Already logged in, skipping login process.


            # A partir daqui, o robô deve estar na página correta, seja por login ou por já estar logado.
            # Se a página de raspagem for diferente da página pós-login, a navegação é necessária.
            if config.pagina_raspagem and config.pagina_raspagem not in page.url:
                print(f"Navigating to specific scraping page: {config.pagina_raspagem}")
                await page.goto(config.pagina_raspagem, timeout=60000)
                await page.wait_for_load_state('networkidle', timeout=30000)
                print("Scraping page loaded.")

            # --- Scrape the table data ---
            table_selector = 'table[role="grid"]' 
            thead_selector = '#form-minhas-cotacoes\:tbFretes_head' # Escapando o ':' para o seletor CSS

            print("Waiting for table header to be visible...")
            await expect(page.locator(thead_selector)).to_be_visible(timeout=30000)
            print("Fertipar table header found.")

            headers = [th.strip() for th in await page.locator(f'{thead_selector} th').all_text_contents() if th.strip()]
            print(f"Headers found: {headers}")

            tbody_selector = f'{table_selector} tbody'
            rows = await page.locator(f'{tbody_selector} tr').all()
            print(f"Found {len(rows)} rows in the table.")

            for row_element in rows:
                cols_text = await row_element.locator('td').all_text_contents()
                
                # Ignora a primeira coluna (que é de ação, ex: 'Agendar Pedido')
                # e remove espaços em branco das outras.
                cols = [col.strip() for col in cols_text][1:]
                
                if len(cols) == len(headers):
                    row_data = dict(zip(headers, cols))
                    scraped_data.append(row_data)
                else:
                    print(f"Skipping row due to mismatch in column count. Expected {len(headers)}, found {len(cols)}. Content: {cols}")
        
        except TimeoutError as e:
            print(f"An error occurred during the scraping process: {str(e)}")
            await page.screenshot(path="error_screenshot.png")
            print("A screenshot 'error_screenshot.png' was saved for debugging.")
            scraped_data = []

        finally:
            print("Closing browser.")
            await browser.close()
    
    if scraped_data:
        print(f"Scraped {len(scraped_data)} total rows. Now filtering for 'Situação' == 'APROVADO'...")
        filtered_data = [row for row in scraped_data if row.get('Situação') == 'APROVADO']
        print(f"Found {len(filtered_data)} rows after filtering.")
        return filtered_data

    return scraped_data