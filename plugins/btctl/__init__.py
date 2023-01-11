import os
import subprocess

from albert import *

md_iid = "0.5"
md_version = "0.1"
md_name = "Bluetooth Control"
md_description = "Control known bluetooth devices with bluetoothctl"
md_bin_dependencies = ["bluetoothctl"]
md_license = "BSD-2"
md_maintainers = "@vsuharnikov"


class Plugin(QueryHandler):
    curr_dir = ''

    def id(self):
        return __name__

    def name(self):
        return md_name

    def description(self):
        return md_description

    def defaultTrigger(self):
        return 'bt '

    def initialize(self):
        self.curr_dir = os.path.dirname(__file__)

    def handleQuery(self, query):
        bt_device_items = self.reload()
        s = query.string.strip().lower()
        if s == '':
            filtered = bt_device_items
        else:
            filtered = list(filter(lambda x: s in x.text.lower(), bt_device_items))
        query.add(filtered)

    # Internal

    def reload(self):
        proc = subprocess.run(['bluetoothctl', 'devices', 'Connected'], stdout=subprocess.PIPE)
        connected = set()
        for x in proc.stdout.decode().splitlines():
            id, name = x.removeprefix('Device ').split(' ', 1)
            connected.add(id)

        proc = subprocess.run(['bluetoothctl', 'devices'], stdout=subprocess.PIPE)
        items = []
        for x in proc.stdout.decode().splitlines():
            id, name = x.removeprefix('Device ').split(' ', 1)

            if id in connected:
                item = self.makeDisconnectItem(id, name)
            else:
                item = self.makeConnectItem(id, name)
            items.append(item)

        return items

    def makeConnectItem(self, id, name):
        return Item(
            id=id,
            text='Connect ' + name,
            subtext=id,
            icon=[
                'xdg:bluetooth-active',
                self.curr_dir + '/bluetooth-active.svg'
            ],
            actions=[Action(
                id='run',
                text='runDetachedProcess (ProcAction)',
                callable=lambda: self.connect(id)
            )]
        )

    def connect(self, id):
        runDetachedProcess(cmdln=['bluetoothctl', 'connect', id], workdir=self.curr_dir)

    def makeDisconnectItem(self, id, name):
        return Item(
            id=id,
            text='Disconnect ' + name,
            subtext=id,
            icon=[
                'xdg:bluetooth-disabled',
                self.curr_dir + '/bluetooth-disabled.svg'
            ],
            actions=[Action(
                id='run',
                text='runDetachedProcess (ProcAction)',
                callable=lambda: self.disconnect(id)
            )]
        )

    def disconnect(self, id):
        runDetachedProcess(cmdln=['bluetoothctl', 'disconnect', id], workdir=self.curr_dir)
