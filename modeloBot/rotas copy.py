
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
from playwright.sync_api import Page, expect


def test_example(page: Page) -> None:
    page.goto("https://sisferweb.fertipar.com.br/logistica/login.xhtml")
    page.locator("#filial_label").click()
    page.get_by_role("option", name="FERTIPAR PR").click()
    page.get_by_role("textbox", name="Usuário").click()
    page.get_by_role("textbox", name="Usuário").fill("kadosh_transp")
    #page.locator("div").filter(has_text="Senha").nth(2).click()
    page.get_by_role("textbox", name="Senha").click()
    page.get_by_role("textbox", name="Senha").fill("fran+1234")
    page.get_by_role("button", name=" Acessar").click()
    page.get_by_role("link", name=" Minhas Cotaçoes").click()
    page.get_by_role("gridcell", name="343291").click()
    page.locator("[id=\"form-minhas-cotacoes:tbFretes:1:j_idt29\"]").click()
    page.locator("[id=\"form-minhas-cotacoes:j_idt126\"]").click()
    page.locator("iframe[title=\"Cadastro de Motorista Autônomo\"]").content_frame.get_by_role("textbox", name="___.___.___-__").click()
    #page.locator("iframe[title=\"Cadastro de Motorista Autônomo\"]").content_frame.get_by_role("textbox", name="___.___.___-__").click()
    page.locator("iframe[title=\"Cadastro de Motorista Autônomo\"]").content_frame.get_by_role("button", name=" Pesquisar").click()

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
                test_example(page)
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
