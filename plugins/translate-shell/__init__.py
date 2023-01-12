import os
import re
import time
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

    job_thread = None
    last_query = None

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

        debug('[translate-shell] Started')

    def finalize(self):
        if self.job_thread:
            self.job_thread.stop()
        debug('[translate-shell] Closed')

    def handleQuery(self, query):
        # cancel if there is a new query
        for number in range(50):
            time.sleep(0.01)
            if not query.isValid:
                return

        self.last_query = query
        if self.job_thread:
            self.job_thread.stop()
        self.job_thread = InterruptableThread(target=self.job)
        self.job_thread.start()

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

    def job(self):
        s = self.last_query.string.strip().lower()
        r = self.regexp.fullmatch(s)
        if r is None:
            debug('[translate-shell] Nothing parsed')
            return

        src_lang = r.group('src0') or r.group('src1') or 'en'
        dst_lang = r.group('dst') or 'ru'
        text = r.group('s')

        translation = self.exec(['-b', f'{src_lang}:{dst_lang}', text])
        debug(f'"{text}", {src_lang} -> {dst_lang}: {translation}')

        item = self.mkItem(src_lang, dst_lang, translation)
        if self.last_query.isValid:
            self.last_query.add(item)

    def exec(self, args):
        proc = subprocess.run(['trans'] + args, stdout=subprocess.PIPE)
        return proc.stdout.decode()


# https://www.geeksforgeeks.org/python-different-ways-to-kill-a-thread/
class InterruptableThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(InterruptableThread, self).__init__(*args, **kwargs)
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
