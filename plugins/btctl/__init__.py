# -*- coding: utf-8 -*-
import subprocess
from pathlib import Path
from typing import List

from albert import (
    PluginInstance,
    TriggerQueryHandler,
    Query,
    StandardItem,
    Action,
    runDetachedProcess,
)

# ──────────────────────────────────────────────────────────────────────────────
# Metadata
# ──────────────────────────────────────────────────────────────────────────────
md_iid = "3.0"
md_version = "0.2"
md_name = "Bluetooth Control"
md_description = "Control known bluetooth devices with bluetoothctl"
md_license = "BSD-2"
md_authors = ["@vsuharnikov"]
md_maintainers = ["@vsuharnikov"]
md_bin_dependencies = ["bluetoothctl"]
md_url = "https://github.com/vsuharnikov/albert-plugins"

# ──────────────────────────────────────────────────────────────────────────────
# Plugin
# ──────────────────────────────────────────────────────────────────────────────
class Plugin(PluginInstance, TriggerQueryHandler):
    def __init__(self):
        PluginInstance.__init__(self)
        TriggerQueryHandler.__init__(self)

        # Setup state
        self._curr_dir = str(Path(__file__).parent.resolve())
        self._trigger = self.defaultTrigger()

    # PluginInstance identity derived from module name
    def id(self) -> str:
        return __name__

    def name(self) -> str:
        return md_name

    def description(self) -> str:
        return md_description

    # ── TriggerQueryHandler settings ───────────────────────────────────────────
    def defaultTrigger(self) -> str:
        return "bt "

    def allowTriggerRemap(self) -> bool:
        return True

    def synopsis(self, query: str) -> str:
        return "Type to filter devices; Enter to connect/disconnect"

    def supportsFuzzyMatching(self) -> bool:
        # Simple substring matching for now
        return False

    def setTrigger(self, trigger: str):
        # Called when user remaps the trigger
        self._trigger = trigger

    # ── Query handling (v3) ───────────────────────────────────────────────────
    def handleTriggerQuery(self, query: Query):
        """
        In v3 queries are handled here; add prepared items to the query results.
        """
        bt_items = self._build_items()

        s = (query.string or "").strip().lower()
        if s:
            filtered = [it for it in bt_items if s in it.text.lower()]
        else:
            filtered = bt_items

        if filtered:
            query.add(filtered)

    # ── Internal helpers ──────────────────────────────────────────────────────
    def _build_items(self) -> List[StandardItem]:
        """
        Build items: 'Disconnect' entries first for connected devices,
        then 'Connect' entries for the rest.
        """
        connected_ids = self._connected_device_ids()
        all_devices = self._all_devices()

        items: List[StandardItem] = []
        for dev_id, name in all_devices:
            if dev_id in connected_ids:
                # Put disconnect items at the front
                items.insert(0, self._make_disconnect_item(dev_id, name))
            else:
                items.append(self._make_connect_item(dev_id, name))
        return items

    def _connected_device_ids(self) -> set[str]:
        """
        Get IDs of currently connected devices via `bluetoothctl devices Connected`.
        """
        try:
            proc = subprocess.run(
                ["bluetoothctl", "devices", "Connected"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            ids: set[str] = set()
            for line in proc.stdout.decode(errors="ignore").splitlines():
                if line.startswith("Device "):
                    rest = line.removeprefix("Device ")
                    dev_id, _name = rest.split(" ", 1)
                    ids.add(dev_id)
            return ids
        except Exception:
            return set()

    def _all_devices(self) -> List[tuple[str, str]]:
        """
        Get all known devices via `bluetoothctl devices`.
        """
        devices: List[tuple[str, str]] = []
        try:
            proc = subprocess.run(
                ["bluetoothctl", "devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            for line in proc.stdout.decode(errors="ignore").splitlines():
                if line.startswith("Device "):
                    rest = line.removeprefix("Device ")
                    dev_id, name = rest.split(" ", 1)
                    devices.append((dev_id, name))
        except Exception:
            pass
        return devices

    # ── Item factories ────────────────────────────────────────────────────────
    def _make_connect_item(self, dev_id: str, name: str) -> StandardItem:
        return StandardItem(
            id=dev_id,
            text=f"Connect {name}",
            subtext=dev_id,
            iconUrls=[
                "xdg:bluetooth-active",
                f"{self._curr_dir}/bluetooth-active.svg",
            ],
            actions=[
                Action(
                    id="run",
                    text="Connect device (bluetoothctl)",
                    callable=lambda _id=dev_id: self._connect(_id),
                )
            ],
        )

    def _make_disconnect_item(self, dev_id: str, name: str) -> StandardItem:
        return StandardItem(
            id=dev_id,
            text=f"Disconnect {name}",
            subtext=dev_id,
            iconUrls=[
                "xdg:bluetooth-disabled",
                f"{self._curr_dir}/bluetooth-disabled.svg",
            ],
            actions=[
                Action(
                    id="run",
                    text="Disconnect device (bluetoothctl)",
                    callable=lambda _id=dev_id: self._disconnect(_id),
                )
            ],
        )

    # ── Actions ───────────────────────────────────────────────────────────────
    def _connect(self, dev_id: str):
        runDetachedProcess(cmdln=["bluetoothctl", "connect", dev_id], workdir=self._curr_dir)

    def _disconnect(self, dev_id: str):
        runDetachedProcess(cmdln=["bluetoothctl", "disconnect", dev_id], workdir=self._curr_dir)

