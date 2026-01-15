import time
from playwright.sync_api import sync_playwright, expect

# Função auxiliar
def try_locate_and_screenshot(page_object, context_frame_or_page, locators_with_names, element_description):
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
            print(f"  Tentando com seletor: '{locator_description}'...")
            expect(locator_object).to_be_visible(timeout=5000)
            print(f"  [SUCESSO] Elemento '{element_description}' encontrado e visível com: '{locator_description}'.")
            
            # Tira screenshot usando o objeto 'page' principal
            screenshot_path = f"screenshot_{element_description.replace(' ', '_').replace('.', '')}_found.png"
            page_object.screenshot(path=screenshot_path) # Usar page_object aqui
            print(f"  Screenshot salvo em: {screenshot_path}")
            
            return locator_object
        except Exception as e:
            print(f"  [FALHA] Seletor '{locator_description}' falhou. Erro: {e}")
            continue # Tenta o próximo seletor
    
    raise Exception(f"Elemento '{element_description}' não foi encontrado por nenhum dos seletores fornecidos.")


def run(playwright):
    # --- Configurações da Automação ---
    url_login = "https://sisferweb.fertipar.com.br/logistica/login.xhtml"
    filial = "FERTIPAR PR"
    usuario = "kadosh_transp"
    senha = "fran+1234"
    # Protocolo a ser procurado dinamicamente na tabela
    protocolo_procurado = "343289"

    # --- Início da Automação ---
    browser = playwright.chromium.launch(headless=False, slow_mo=100)
    context = browser.new_context()
    page = context.new_page()

    try:
        # --- ETAPA DE LOGIN (Copiada fielmente do rotas.py) ---
        print("Executando a sequência de login comprovadamente funcional...")
        page.goto(url_login, timeout=60000)
        
        # Filial
        page.locator("#filial_label").click()
        page.get_by_role("option", name=filial).click()
        
        # Usuário (com o clique explícito antes de preencher)
        page.get_by_role("textbox", name="Usuário").click()
        page.get_by_role("textbox", name="Usuário").fill(usuario)
        
        # Senha (com o clique explícito antes de preencher)
        page.get_by_role("textbox", name="Senha").click()
        page.get_by_role("textbox", name="Senha").fill(senha)

        # Botão Acessar (com o caractere de ícone, como no rotas.py)
        page.get_by_role("button", name=" Acessar").click()
        
        print("Login realizado com sucesso.")

        # --- NAVEGAÇÃO PÓS-LOGIN ---
        print("Navegando para 'Minhas Cotações'...")
        # Link (com o caractere de ícone, como no rotas.py)
        page.get_by_role("link", name=" Minhas Cotaçoes").click()
        
        # --- LÓGICA DA TABELA (Robusta e Dinâmica) ---
        print(f"Procurando pelo protocolo: {protocolo_procurado}...")
        
        # Espera a grade de dados (tabela) ficar visível. Esta é uma forma mais robusta.
        expect(page.get_by_role("grid").first).to_be_visible(timeout=30000)

        # Localiza a linha (tr) que contém o texto do protocolo
        linha_do_protocolo = page.locator(f'//tr[contains(., "{protocolo_procurado}")]')

        # Verifica se a linha foi encontrada
        if linha_do_protocolo.count() > 0:
            print(f"Protocolo {protocolo_procurado} encontrado!")
            page.screenshot(path=f"protocolo_{protocolo_procurado}.png")

            # A partir da linha encontrada, localiza o elemento clicável pelo texto.
            # Esta abordagem é mais flexível que procurar por um role="button".
            botao_agendar = linha_do_protocolo.locator(':text("Agendar Pedido")')
            print("Clicando no botão 'Agendar Pedido'...")
            botao_agendar.click()
            element_to_click = page.locator("[id=\"form-minhas-cotacoes:j_idt126\"]")
            expect(element_to_click).to_be_visible(timeout=10000)
            print("Elemento com ID 'form-minhas-cotacoes:j_idt126' encontrado e visível. Clicando...")
            element_to_click.click()

            print("\nProcurando pelo iframe 'Cadastro de Motorista Autônomo'...")
            iframe_motorista = page.locator("iframe[title=\"Cadastro de Motorista Autônomo\"]")
            
            # Espera o iframe ficar visível
            expect(iframe_motorista).to_be_visible(timeout=15000)
            print("Iframe encontrado e visível.")

            # Acessa o conteúdo do iframe
            iframe_content = iframe_motorista.content_frame

            # --- USO DA FUNÇÃO try_locate_and_screenshot PARA O CAMPO 'NRO.CPF' ---
            try:
                campo_cpf = try_locate_and_screenshot(
                    page_object=page, # Passa o objeto page principal
                    context_frame_or_page=iframe_content,
                    locators_with_names=[
                        (iframe_content.get_by_role("textbox", name="___.___.___-__"), "get_by_role(\"textbox\", name=\"___.___.___-__\")"),
                        (iframe_content.get_by_placeholder("Nro.Cpf"), "get_by_placeholder(\"Nro.Cpf\")")
                    ],
                    element_description="Campo 'Nro.Cpf'"
                )
                if campo_cpf:
                    expect(campo_cpf).to_be_editable(timeout=10000)
                    print("[SUCESSO] Campo 'Nro.Cpf' é editável.")
                    
                    # Tentativas mais robustas de interação
                    campo_cpf.focus() # Tentar focar no campo
                    time.sleep(0.5) # Pequeno atraso para garantir o foco/renderização
                    campo_cpf.click() # Clicar novamente para garantir foco
                    time.sleep(0.5)
                    nro_cpf = "94167850915"
                    campo_cpf.type(nro_cpf, delay=100) # Usar type() com delay para simular digitação real
                    
                    print("[SUCESSO] Campo 'Nro.Cpf' preenchido com sucesso.")

                    # Clica diretamente no botão pesquisar após preencher o CPF
                    print("\nClicando no botão 'Pesquisar'...")
                    botao_pesquisar = iframe_content.get_by_role("button", name=" Pesquisar")
                    expect(botao_pesquisar).to_be_visible(timeout=5000)
                    botao_pesquisar.click()
                    print("[SUCESSO] Botão 'Pesquisar' clicado.")

            except Exception as e:
                print(f"[FALHA GERAL] Não foi possível interagir com o campo 'Nro.Cpf' ou com o botão 'Pesquisar'. Erro: {e}")
                page.screenshot(path="erro_cpf_ou_pesquisar_screenshot.png")
                print("Um screenshot do erro foi salvo como: erro_cpf_ou_pesquisar_screenshot.png")
                raise # Re-lança a exceção para parar o script, se desejar

            # --- LÓGICA CONDICIONAL: TENTAR 'SELECIONAR' E, SE FALHAR, TENTAR 'SIM' ---
            try:
                # Tenta encontrar e clicar no botão 'Selecionar'
                print("\n--- Tentando localizar: 'Botão 'Selecionar'' ---")
                botao_selecionar = iframe_content.get_by_role("button", name=" Selecionar")
                expect(botao_selecionar).to_be_visible(timeout=10000) # Dar um tempo maior para o elemento aparecer
                botao_selecionar.click()
                print("[SUCESSO] Botão 'Selecionar' clicado.")
            except Exception as e_selecionar:
                print(f"[INFO] Botão 'Selecionar' não encontrado. Tentando alternativa 'Sim'. Erro: {e_selecionar}")
                
                # Se 'Selecionar' falhou, tenta encontrar e clicar no botão 'Sim'
                try:
                    print("\n--- Tentando localizar: 'Botão 'Sim'' ---")
                    botao_sim = iframe_content.get_by_role("button", name=" Sim")
                    expect(botao_sim).to_be_visible(timeout=5000)
                    botao_sim.click()
                    print("[SUCESSO] Botão 'Sim' clicado como alternativa.")
                except Exception as e_sim:
                    print(f"[FALHA GERAL] Botão 'Selecionar' e alternativa 'Sim' não foram encontrados. Erro: {e_sim}")
                    page.screenshot(path="erro_botao_selecionar_ou_sim_screenshot.png")
                    print("Um screenshot do erro foi salvo como: erro_botao_selecionar_ou_sim_screenshot.png")
                    raise # Re-lança a exceção se nenhuma das opções funcionar

            # --- ETAPA FINAL: PREENCHER CPF NO CADASTRO DE VEÍCULO/MOTORISTA ---
            try:
                print("\n--- Tentando preencher CPF no formulário final ---")
                
                # O seletor do usuário indica que um novo diálogo pode ter aparecido.
                # Vamos esperar por ele e então buscar o iframe dentro dele.
                dialogo_final = page.locator('[id="formPesquisaTransp:j_idt24_dlg"]')
                print("Aguardando o diálogo final do motorista ser visível...")
                expect(dialogo_final).to_be_visible(timeout=15000)
                print("Diálogo final encontrado.")

                # Usamos frame_locator para encontrar o iframe dentro do escopo do diálogo
                final_frame_locator = dialogo_final.frame_locator('iframe[title="Cadastro de Motorista Autônomo"]')

                # Agora, dentro deste frame, encontramos o campo CPF
                campo_cpf_final = final_frame_locator.get_by_role("textbox", name="CPF*")
                
                print("Aguardando o campo 'CPF*' final ser editável...")
                expect(campo_cpf_final).to_be_editable(timeout=10000)
                print("Campo 'CPF*' final é editável.")
                
                # Preenche o campo
                campo_cpf_final.click() # Clica para garantir o foco
                time.sleep(0.5)
                campo_cpf_final.fill(nro_cpf) # Usa a variável nro_cpf definida anteriormente
                
                print(f"[SUCESSO] Campo 'CPF*' final preenchido com: {nro_cpf}")
                page.screenshot(path="sucesso_cpf_final.png")

            except Exception as e_final_cpf:
                print(f"[FALHA GERAL] Não foi possível preencher o campo 'CPF*' final. Erro: {e_final_cpf}")
                page.screenshot(path="erro_campo_cpf_final_screenshot.png")
                print("Um screenshot do erro foi salvo como: erro_campo_cpf_final_screenshot.png")
                raise

    except Exception as e:
        print(f"\nOcorreu um erro inesperado durante a automação: {e}")
        page.screenshot(path="erro_screenshot.png")
        print("Um screenshot do erro foi salvo como: erro_screenshot.png")

    finally:
        print("\nAutomação concluída. Pressione Enter para fechar o navegador...")
        input() # Espera o usuário pressionar Enter
        print("Fechando o navegador.")
        browser.close()

# --- Ponto de Entrada do Script ---
if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
