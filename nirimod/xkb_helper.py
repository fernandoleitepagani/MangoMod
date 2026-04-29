import ctypes
import ctypes.util
import os
import xml.etree.ElementTree as ET
from pathlib import Path

class XkbHelper:
    def __init__(self):
        self.lib = None
        self.ctx = None
        self.keymap = None
        self.state = None
        
        path = ctypes.util.find_library("xkbcommon")
        if not path:
            # check common paths just in case find_library acts up
            for p in ["/usr/lib/libxkbcommon.so.0", "/usr/lib64/libxkbcommon.so.0", "/lib/x86_64-linux-gnu/libxkbcommon.so.0"]:
                if os.path.exists(p):
                    path = p
                    break
        
        if not path:
            return

        try:
            self.lib = ctypes.CDLL(path)
            
            # Prototypes
            self.lib.xkb_context_new.restype = ctypes.c_void_p
            self.lib.xkb_keymap_new_from_names.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
            self.lib.xkb_keymap_new_from_names.restype = ctypes.c_void_p
            self.lib.xkb_state_new.argtypes = [ctypes.c_void_p]
            self.lib.xkb_state_new.restype = ctypes.c_void_p
            self.lib.xkb_state_key_get_utf8.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t]
            self.lib.xkb_state_key_get_utf8.restype = ctypes.c_int
            
            self.lib.xkb_state_key_get_one_sym.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            self.lib.xkb_state_key_get_one_sym.restype = ctypes.c_uint32
            
            self.lib.xkb_keysym_get_name.argtypes = [ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t]
            self.lib.xkb_keysym_get_name.restype = ctypes.c_int
            
            self.lib.xkb_keymap_unref.argtypes = [ctypes.c_void_p]
            self.lib.xkb_keymap_unref.restype = None
            self.lib.xkb_state_unref.argtypes = [ctypes.c_void_p]
            self.lib.xkb_state_unref.restype = None
            
            self.ctx = self.lib.xkb_context_new(0)
        except Exception:
            self.lib = None

    class XkbRuleNames(ctypes.Structure):
        _fields_ = [
            ("rules", ctypes.c_char_p),
            ("model", ctypes.c_char_p),
            ("layout", ctypes.c_char_p),
            ("variant", ctypes.c_char_p),
            ("options", ctypes.c_char_p),
        ]

    def set_layout(self, layout_id: str):
        if not self.lib or not self.ctx:
            return
            
        parts = layout_id.split(":", 1)
        layout_name = parts[0]
        variant_name = parts[1] if len(parts) > 1 else ""
            
        self._layout_bytes = layout_name.encode()
        self._variant_bytes = variant_name.encode() if variant_name else None
        names = self.XkbRuleNames(None, None, self._layout_bytes, self._variant_bytes, None)
        
        if self.state:
            self.lib.xkb_state_unref(self.state)
            self.state = None
        if self.keymap:
            self.lib.xkb_keymap_unref(self.keymap)
            self.keymap = None
            
        self.keymap = self.lib.xkb_keymap_new_from_names(self.ctx, ctypes.byref(names), 0)
        if self.keymap:
            self.state = self.lib.xkb_state_new(self.keymap)

    def get_label(self, keycode: int) -> str | None:
        if not self.state:
            return None
        
        # xkb keycodes are always evdev + 8
        xkb_keycode = keycode + 8
        
        buf = ctypes.create_string_buffer(32)
        res = self.lib.xkb_state_key_get_utf8(self.state, xkb_keycode, buf, 32)
        if res > 0:
            return buf.value.decode('utf-8')
        return None

    def get_keysym_name(self, keycode: int) -> str | None:
        if not self.state:
            return None
            
        xkb_keycode = keycode + 8
        sym = self.lib.xkb_state_key_get_one_sym(self.state, xkb_keycode)
        if sym == 0:
            return None
            
        buf = ctypes.create_string_buffer(64)
        res = self.lib.xkb_keysym_get_name(sym, buf, 64)
        if res >= 0:
            return buf.value.decode('utf-8')
        return None

    @staticmethod
    def get_available_layouts() -> list[tuple[str, str]]:
        # rip through the system's evdev.xml to find every layout we can use
        paths = [
            "/usr/share/X11/xkb/rules/evdev.xml",
            "/usr/share/X11/xkb/rules/base.xml"
        ]
        layouts = []
        for p in paths:
            if os.path.exists(p):
                try:
                    tree = ET.parse(p)
                    root = tree.getroot()
                    for layout in root.findall(".//layout"):
                        config = layout.find("configItem")
                        if config is not None:
                            name = config.findtext("name")
                            desc = config.findtext("description")
                            if name and desc:
                                layouts.append((name, desc))
                                
                        # grab variants too (like dvorak, colemak, etc)
                        variant_list = layout.find("variantList")
                        if variant_list is not None:
                            for variant in variant_list.findall("variant"):
                                v_config = variant.find("configItem")
                                if v_config is not None:
                                    v_name = v_config.findtext("name")
                                    v_desc = v_config.findtext("description")
                                    if name and v_name and v_desc:
                                        layouts.append((f"{name}:{v_name}", v_desc))

                    if layouts:
                        # Sort by description
                        layouts.sort(key=lambda x: x[1])
                        return layouts
                except Exception:
                    continue
        
        # fallback to a tiny list if xml parsing explodes
        return [("us", "English (US)"), ("us:dvorak", "English (Dvorak)"), ("it", "Italian"), ("fr", "French"), ("de", "German"), ("es", "Spanish")]
