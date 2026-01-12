[RPA] Erro durante a raspagem: Timeout 30000ms exceeded.
=========================== logs ===========================
waiting for navigation to "**/dashboard.xhtml" until 'load'
============================================================
Traceback (most recent call last):
  File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\backend\rpa_fertipar\rotas.py", line 51, in scrape_fertipar_cotacoes
    page.wait_for_url("**/dashboard.xhtml") # ou outra URL esperada após o login
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front\.venv\Lib\site-packages\playwright\sync_api\_generated.py", line 9193, in wait_for_url
    self._sync(
  File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front\.venv\Lib\site-packages\playwright\_impl\_sync_base.py", line 115, in _sync
    return task.result()
           ^^^^^^^^^^^^^
  File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front\.venv\Lib\site-packages\playwright\_impl\_page.py", line 580, in wait_for_url
    return await self._main_frame.wait_for_url(**locals_to_params(locals()))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front\.venv\Lib\site-packages\playwright\_impl\_frame.py", line 263, in wait_for_url
    async with self.expect_navigation(
  File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front\.venv\Lib\site-packages\playwright\_impl\_event_context_manager.py", line 33, in __aexit__
    await self._future
  File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front\.venv\Lib\site-packages\playwright\_impl\_frame.py", line 239, in continuation
    event = await waiter.result()
            ^^^^^^^^^^^^^^^^^^^^^
playwright._impl._errors.TimeoutError: Timeout 30000ms exceeded.
=========================== logs ===========================
waiting for navigation to "**/dashboard.xhtml" until 'load'
============================================================