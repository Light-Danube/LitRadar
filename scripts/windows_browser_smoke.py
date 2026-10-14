"""Synthetic native-Chrome smoke on Windows; run: python -m scripts.windows_browser_smoke."""
import re
import os
import uuid
import socket
import threading
import time
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright, expect
from sources.base import Paper
from storage.sqlite import PaperStore
from workspace_web import create_app


def main():
    relative = f'.venv/windows-browser-smoke/run-{uuid.uuid4().hex}'
    artifacts = Path(__file__).resolve().parents[1] / relative
    artifacts.mkdir(parents=True, exist_ok=True)
    database = artifacts / 'browser-smoke.sqlite3'
    # Only this unique synthetic run directory can be collected by CI.
    if os.getenv('GITHUB_OUTPUT'):
        with Path(os.environ['GITHUB_OUTPUT']).open('a',encoding='utf-8') as output:
            output.write(f'artifact_dir={relative}\n')
    store=PaperStore(database)
    ids=[store.upsert_paper(Paper(source='fixture',title=title,abstract='Synthetic browser evidence only.'),
                            relevance_score=.5,matched_groups={})
         for title in ['Synthetic seed — Дослідження','Synthetic reference']]
    for paper in ids:store.set_tags(paper,['shared'])
    store.record_relation(ids[0],ids[1],'cites','openalex')
    store.record_relation(ids[0],ids[1],'cites','semantic_scholar')
    store.close()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(create_app(database,semantic_enabled=False),host='127.0.0.1',port=port,log_level='error'))
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    origin=f'http://127.0.0.1:{port}'
    try:
        deadline=time.monotonic()+15
        while not server.started:
            if not thread.is_alive() or time.monotonic()>deadline:raise RuntimeError('Synthetic server did not start')
            time.sleep(.05)
        with sync_playwright() as p:
            # Chrome is installed on windows-latest. Keep sandbox enabled and use a fresh repo-local profile.
            context=p.chromium.launch_persistent_context(str(artifacts/'profile'),channel='chrome',headless=True,chromium_sandbox=True)
            try:
                context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(origin+'/') else route.abort())
                page=context.new_page()
                for language in ['en','uk']:
                    for name,width,height in [('desktop',1440,900),('narrow',390,844)]:
                        page.set_viewport_size({'width':width,'height':height});page.goto(origin)
                        page.locator('#language').select_option(language)
                        page.locator('[data-page="inbox"]').click()
                        page.locator(f'[data-paper="{ids[0]}"]').first.click()
                        notes=f'Synthetic {language} {name} note'
                        page.locator('#detail-notes').fill(notes)
                        page.locator('#detail-status').select_option('read')
                        with page.expect_response(lambda r:r.url.endswith(f'/api/papers/{ids[0]}') and r.request.method=='PATCH'):
                            page.locator('#save-annotation').click()
                        assert page.request.get(origin+f'/api/papers/{ids[0]}').json()['notes']==notes
                        page.locator('[data-page="clusters"]').click()
                        expect(page.locator('.cluster-grid')).to_contain_text('Synthetic seed')
                        page.locator(f'[data-paper="{ids[0]}"]').first.click()
                        expect(page.locator('#detail-notes')).to_have_value(notes)
                        page.locator('#open-graph').click()
                        node=page.locator(f'[data-node="{ids[0]}"]')
                        # No keyboard event: this is the native single-click regression.
                        node.locator('circle').click();expect(node).to_have_class(re.compile(r'\bselected\b'))
                        expect(page.locator('#graph-selection')).to_contain_text('Synthetic seed')
                        page.locator('#graph-reset-layout').click()
                        circle=node.locator('circle');box=circle.bounding_box();assert box
                        page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2)
                        page.mouse.down();page.mouse.move(box['x']+80,box['y']+70,steps=6);page.mouse.up()
                        assert node.get_attribute('transform') not in [None,'translate(0 0)']
                        canvas=page.locator('#graph-svg');old=canvas.get_attribute('viewBox')
                        canvas.hover();page.mouse.wheel(0,-160)
                        expect(canvas).not_to_have_attribute('viewBox',old)
                        menu=page.locator('.graph-export');menu.locator('summary').click()
                        expect(menu).to_have_attribute('open','')
                        menu.locator('summary').press('Escape');expect(menu).not_to_have_attribute('open','')
                        page.screenshot(path=str(artifacts/f'{language}-{name}.png'),full_page=True)
                print('4 native Chrome scenarios passed (EN/UK × desktop/narrow), synthetic data only.')
            finally:context.close()
    finally:
        server.should_exit=True;thread.join(timeout=10)


if __name__=='__main__':main()
