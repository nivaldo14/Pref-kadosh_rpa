import re
import traceback
from playwright.sync_api import Page, expect, sync_playwright


# def test_example(page: Page) -> None:
#     page.goto("https://sisferweb.fertipar.com.br/logistica/login.xhtml")
#     page.locator("#filial_label").click()
#     page.get_by_role("option", name="FERTIPAR PR").click()
#     #page.get_by_role("textbox", name="Usuário").click()
#     #page.get_by_role("textbox", name="Usuário").click()
#     page.get_by_role("textbox", name="Usuário").fill("kadosh_transp")
#     #page.get_by_role("textbox", name="Senha").click()
#     page.get_by_role("textbox", name="Senha").fill("fran+1234")
#     page.get_by_role("button", name=" Acessar").click()
#     page.get_by_role("link", name=" Minhas Cotaçoes").click()
#     page.get_by_role("gridcell", name="343291").click()
#     page.locator("[id=\"form-minhas-cotacoes:tbFretes:1:j_idt29\"]").click()
#     page.locator("[id=\"form-minhas-cotacoes:j_idt126\"]").click()
#     #page.locator("iframe[title=\"Cadastro de Motorista Autônomo\"]").content_frame.get_by_role("textbox", name="___.___.___-__").click()
#     page.locator("iframe[title=\"Cadastro de Motorista Autônomo\"]").content_frame.get_by_role("textbox", name="___.___.___-__").fill("94167850915")
#     page.locator("iframe[title=\"Cadastro de Motorista Autônomo\"]").content_frame.get_by_role("button", name=" Pesquisar").click()
# #    expect(page.locator("iframe[title=\"Cadastro de Motorista Autônomo\"]").content_frame.get_by_role("button", name=" Sim")).to_be_visible()
# #    page.locator("iframe[title=\"Cadastro de Motorista Autônomo\"]").content_frame.get_by_role("button", name=" Não").click()

import re
import traceback
from playwright.sync_api import Page, expect, sync_playwright


def scrape_fertipar_cotacoes(url_login, url_cotacoes, usuario_site, senha_site, filial_name):
    print(f"[RPA] Iniciando raspagem para {url_cotacoes}")
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) # Mudar para False para depurar visualmente
        context = browser.new_context()
        page = context.new_page()

        try:
            # Definir o tempo limite padrão para todas as operações no contexto
            context.set_default_timeout(60000)
            # Definir o tempo limite para operações de navegação especificamente
            page.set_default_navigation_timeout(60000) 

            # 1. Navegar para a página de login
            page.goto(url_login)
            page.screenshot(path="login_page.png") # Screenshot da página de login

            # 2. Fazer login
            page.locator("#filial_label").click()
            page.get_by_role("option", name=filial_name).click()
            page.get_by_role("textbox", name="Usuário").fill(usuario_site)
            page.get_by_role("textbox", name="Senha").fill(senha_site)
            page.get_by_role("button", name=" Acessar").click()
            
            # Esperar por um seletor na página pós-login que indique sucesso, ou uma URL diferente.
            # Por enquanto, vou aumentar o timeout e manter a URL, adicionando um screenshot.
            # page.wait_for_url("**/dashboard.xhtml", timeout=60000) # Comentado para depuração
            page.wait_for_load_state('networkidle', timeout=60000) # Pode ser útil esperar por inatividade da rede
            page.screenshot(path="post_login_dashboard.png") # Screenshot após login
            print("[RPA] Login realizado com sucesso. (Verificar 'post_login_dashboard.png' para confirmação da página)")

            # 3. Navegar para a página de cotações (pagina_raspagem)
            page.goto(url_cotacoes) 
            page.wait_for_load_state('networkidle', timeout=60000) # Espera a rede ficar inativa com timeout maior
            page.screenshot(path="cotacoes_page.png") # Screenshot da página de cotações

            # ** NOVA VERIFICAÇÃO **
            current_url = page.url
            # Suponha que a URL de login contenha "login.xhtml"
            if "login.xhtml" in current_url.lower(): 
                print(f"[RPA] ATENÇÃO: Após navegar para '{url_cotacoes}', a página atual é '{current_url}'. Isso pode indicar que a sessão expirou ou a URL exige reautenticação.")
                raise Exception("Redirecionado para página de login após tentar acessar a página de raspagem.")
            # Você pode precisar ajustar a lógica abaixo com base nas URLs de redirecionamento esperadas
            elif url_cotacoes not in current_url and current_url != url_login: # Verifica se não é a URL esperada e não é a de login
                print(f"[RPA] ATENÇÃO: Após navegar para '{url_cotacoes}', a página atual é '{current_url}'. A URL esperada não foi alcançada ou houve um redirecionamento inesperado.")
                raise Exception(f"Redirecionamento inesperado para '{current_url}' após tentar acessar a página de raspagem.")

            print(f"[RPA] Navegado para {url_cotacoes}. Raspando dados da tabela...")

            # ** NOVO: Raspar e imprimir cabeçalhos da tabela **
            # Assumindo que a tabela possui um thead e th para os cabeçalhos
            header_locators = page.locator("table thead th").all_text_contents()
            print(f"[RPA] Cabeçalhos da tabela raspados: {header_locators}")
            # Fim do NOVO

            table_rows = page.locator("table tbody tr").all() # Pega todas as linhas do corpo da tabela
            
            if not table_rows:
                print("[RPA] Nenhuma linha encontrada na tabela de cotações.")
                return []

            for row_locator in table_rows:
                columns = row_locator.locator("td").all_text_contents()
                
                print(f"[RPA Debug] Colunas raspadas para a linha: {columns}") # Adicionar este print

                # O primeiro item é vazio. Os dados úteis começam em columns[1].
                # Cabeçalhos: ['', 'Protocolo', 'Pedido', 'Data', 'Situação', 'Destino', 'Qtde.', 'Embalagem', 'Cotação', 'Observação Cotação']
                
                # Verificar se há colunas suficientes para os dados esperados, contando a coluna vazia e as 9 de dados
                if len(columns) >= 10: 
                    
                    # Extrair a Situação (índice 4)
                    situacao = columns[4].strip().upper()
                    
                    # FILTRO: Apenas se a situação for "APROVADO"
                    if situacao == "APROVADO":
                        results.append({
                            "Protocolo": columns[1],
                            "Pedido": columns[2],
                            "Data": columns[3], 
                            "Situacao": columns[4],
                            "Destino": columns[5],
                            "Qtde.": columns[6],
                            "Embalagem": columns[7],
                            "Cotacao": columns[8],       
                            "ObservacaoCotacao": columns[9]
                        })
                else:
                    print(f"[RPA Debug] Linha com colunas insuficientes (esperado >= 10): {columns}") # Mensagem de debug mais clara


        except Exception as e:
            print(f"[RPA] Erro durante a raspagem: {e}")
            page.screenshot(path="error_page.png") # Screenshot em caso de erro
            traceback.print_exc()
        finally:
            context.close()
            browser.close()
    
    print(f"[RPA] Raspagem concluída. Total de itens: {len(results)}")
    return results

def _run_rotas():
    print("[rotas.py] starting")
    try:
        with sync_playwright() as p:
            print("[rotas.py] launching browser")
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            try:
                print("[rotas.py] calling test_example")
                # test_example(page)
                # Exemplo de como chamar a nova função (descomente para testar)
                # test_data = scrape_fertipar_cotacoes(
                #     url_login="https://sisferweb.fertipar.com.br/logistica/login.xhtml",
                #     url_cotacoes="https://sisferweb.fertipar.com.br/logistica/cotacoes.xhtml", # Exemplo de URL
                #     usuario_site="kadosh_transp",
                #     senha_site="fran+1234",
                #     filial_name="FERTIPAR PR"
                # )
                # print(f"Dados raspados (exemplo): {test_data}")

                print("[rotas.py] test_example returned")
                page.wait_for_timeout(2000)
            except Exception:
                print("[rotas.py] exception in test_example:")
                traceback.print_exc()
            finally:
                try:
                    context.close()
                except Exception:
                    pass
                try:
                    browser.close()
                except Exception:
                    pass
    except Exception:
        print("[rotas.py] exception launching Playwright:")
        traceback.print_exc()


if __name__ == "__main__":
    _run_rotas()