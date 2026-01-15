import asyncio
from typing import List, Dict, Optional, Tuple
from playwright.async_api import async_playwright, Page, expect, TimeoutError

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
    
    # Extract config details
    url_acesso = config.url_acesso
    usuario_site = config.usuario_site
    senha_site = config.senha_site
    head_evento = config.head_evento

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
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
                await page.wait_for_load_state('networkidle', timeout=30000)
                print("Login realizado com sucesso.")
            else:
                print("Já logado, pulando etapa de login.")

            if config.pagina_raspagem and config.pagina_raspagem not in page.url:
                print(f"Navegando para a página de raspagem: {config.pagina_raspagem}")
                await page.goto(config.pagina_raspagem, timeout=60000)
                await page.wait_for_load_state('networkidle', timeout=30000)

            print("Aguardando pela tabela de dados...")
            table_selector = 'table[role="grid"]'
            thead_selector = '#form-minhas-cotacoes\:tbFretes_head'
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
        print(f"Raspagem concluída. Total de {len(scraped_data)} linhas. Filtrando por 'Situação' == 'APROVADO'...")
        filtered_data = [row for row in scraped_data if row.get('Situação') == 'APROVADO']
        print(f"Encontrado {len(filtered_data)} linhas após filtro.")
        return filtered_data

    return scraped_data