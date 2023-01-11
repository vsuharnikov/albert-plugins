import asyncio
import os
import re
import subprocess
import threading
from albert import *

md_iid = "0.5"
md_version = "0.1"
md_name = "Translate Shell"
md_description = "Translate with translate-shell"
md_bin_dependencies = []
md_license = "BSD-2"
md_maintainers = "@vsuharnikov"


class Plugin(QueryHandler):
    is_working = True
    curr_dir = ''

    regexp = None
    query = None

    thead = None
    loop = None

    curr_task = None

    def id(self):
        return __name__

    def name(self):
        return md_name

    def description(self):
        return md_description

    def defaultTrigger(self):
        return 't '

    def synopsis(self):
        return 'src-lang|src-lang?:dst-lang? text'

    def initialize(self):
        self.curr_dir = os.path.dirname(__file__)

        langs = '|'.join(self.exec(['-list-codes']).splitlines())
        r = f'^((?P<src1>{langs})?:(?P<dst>{langs})\s+|(?P<src0>{langs}):?\s+|\s*)(?P<s>.+)$'
        debug('[translate-shell] Regexp: ' + r)
        self.regexp = re.compile(r, re.DOTALL)

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.runLoop)
        self.thread.start()
        debug('[translate-shell] Started')

    def finalize(self):
        self.is_working = False
        if self.curr_task:
            self.curr_task.cancel()
        self.thread.join()
        debug('[translate-shell] Closed')

    def handleQuery(self, query):
        if self.curr_task:
            self.curr_task.cancel()
        self.query = query
        self.curr_task = self.loop.create_task(self.debounced())

    # Internal
    def mkItem(self, src_lang, dst_lang, text):
        return Item(
            id=__name__,
            text=text,
            subtext=f'{src_lang} → {dst_lang}',
            icon=[
                'xdg:google-translate',
                self.curr_dir + '/book-dictionary.svg'
            ],
            actions=[Action(
                id='copy',
                text='Copy to clipboard',
                callable=lambda: setClipboardText(text)
            )]
        )

    async def debounced(self):
        await asyncio.sleep(0.5)
        if not self.query.isValid:
            return

        s = self.query.string.strip().lower()
        r = self.regexp.fullmatch(s)
        if r is None:
            debug('[translate-shell] Nothing parsed')
            return

        src_lang = r.group('src0') or r.group('src1') or 'en'
        dst_lang = r.group('dst') or 'ru'
        text = r.group('s')

        translation = self.exec(['-b', f'{src_lang}:{dst_lang}', text])
        debug(f'"{text}", {src_lang} -> {dst_lang}: {translation}')
        if self.query.isValid:
            self.query.add(self.mkItem(src_lang, dst_lang, translation))

    def runLoop(self):
        self.loop.run_until_complete(self.watchLoop())

    async def watchLoop(self):
        while self.is_working:
            await asyncio.sleep(1)

    def exec(self, args):
        proc = subprocess.run(['trans'] + args, stdout=subprocess.PIPE)
        return proc.stdout.decode()
