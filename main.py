import json
import os
import socket
import requests
from requests.auth import HTTPBasicAuth

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window

DEFAULT_IP = "192.168.1.128"
AUTH_FILE = 'bravia_auth.json'

KEY_CODES = {
    'POWER': 'AAAAAQAAAAEAAAAVAw==',
    'TERRESTRIAL': 'AAAAAgAAAJcAAAANAw==',
    'BS_CS': 'AAAAAgAAAJcAAAAPAw==',
    'UP': 'AAAAAQAAAAEAAAB0Aw==',
    'DOWN': 'AAAAAQAAAAEAAAB1Aw==',
    'LEFT': 'AAAAAQAAAAEAAAA0Aw==',
    'RIGHT': 'AAAAAQAAAAEAAAAzAw==',
    'SELECT': 'AAAAAQAAAAEAAABlAw==',
    'MUTE': 'AAAAAQAAAAEAAAAUAw==',
    'VOL_UP': 'AAAAAQAAAAEAAAASAw==',
    'VOL_DOWN': 'AAAAAQAAAAEAAAATAw==',
    'CH_UP': 'AAAAAQAAAAEAAAAQAw==',
    'CH_DOWN': 'AAAAAQAAAAEAAAARAw==',
    'BACK': 'AAAAAgAAAJcAAAAjAw==',
    'TV': 'AAAAAB0AAAABAAAABg==',
    'HOME': 'AAAAAQAAAAEAAABgAw==',
    'INPUT': 'AAAAAQAAAAEAAAAlAw==',
    'EPG': 'AAAAAgAAAKAAAABbAw==',
    'MENU': 'AAAAAGADAAAAHQAAABo='
}

def send_ircc(code_name):
    code = KEY_CODES.get(code_name, '')
    if not code:
        return
    url = f"http://{DEFAULT_IP}/sony/IRCC"
    headers = {
        'Content-Type': 'text/xml; charset=UTF-8',
        'SOAPACTION': '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"'
    }
    body = f'<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1"><IRCCCode>{code}</IRCCCode></u:X_SendIRCC></s:Body></s:Envelope>'
    try:
        requests.post(url, headers=headers, data=body.encode('utf-8'), timeout=2)
    except Exception as e:
        print(f"Send Error: {e}")

class BraviaRemoteApp(App):
    def build(self):
        Window.clearcolor = (0, 0, 0, 1)
        root = ScrollView(size_hint=(1, 1))
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        # 1. 電源 / 地デジ / BS
        row1 = GridLayout(cols=3, spacing=6, size_hint_y=None, height=54)
        btn_dig = Button(text='地デジ', background_color=(0.17, 0.17, 0.18, 1))
        btn_dig.bind(on_press=lambda x: send_ircc('TERRESTRIAL'))
        btn_bs = Button(text='BS/CS', background_color=(0.17, 0.17, 0.18, 1))
        btn_bs.bind(on_press=lambda x: send_ircc('BS_CS'))
        btn_pwr = Button(text='電源', background_color=(0.19, 0.82, 0.35, 1))
        btn_pwr.bind(on_press=lambda x: send_ircc('POWER'))
        row1.add_widget(btn_dig)
        row1.add_widget(btn_bs)
        row1.add_widget(btn_pwr)
        layout.add_widget(row1)

        # 2. 十字キー & 決定
        dpad = GridLayout(cols=3, spacing=6, size_hint_y=None, height=186)
        dpad.add_widget(Label())
        btn_up = Button(text='▲', background_color=(0.17, 0.17, 0.18, 1))
        btn_up.bind(on_press=lambda x: send_ircc('UP'))
        dpad.add_widget(btn_up)
        dpad.add_widget(Label())

        btn_left = Button(text='◄', background_color=(0.17, 0.17, 0.18, 1))
        btn_left.bind(on_press=lambda x: send_ircc('LEFT'))
        btn_ok = Button(text='◆ 決定', background_color=(0.23, 0.23, 0.24, 1))
        btn_ok.bind(on_press=lambda x: send_ircc('SELECT'))
        btn_right = Button(text='►', background_color=(0.17, 0.17, 0.18, 1))
        btn_right.bind(on_press=lambda x: send_ircc('RIGHT'))
        dpad.add_widget(btn_left)
        dpad.add_widget(btn_ok)
        dpad.add_widget(btn_right)

        dpad.add_widget(Label())
        btn_down = Button(text='▼', background_color=(0.17, 0.17, 0.18, 1))
        btn_down.bind(on_press=lambda x: send_ircc('DOWN'))
        dpad.add_widget(btn_down)
        dpad.add_widget(Label())
        layout.add_widget(dpad)

        # 3. 音量 / チャンネル
        vol_row = GridLayout(cols=5, spacing=6, size_hint_y=None, height=54)
        btn_mute = Button(text='消音', background_color=(0.11, 0.11, 0.12, 1))
        btn_mute.bind(on_press=lambda x: send_ircc('MUTE'))
        btn_vdown = Button(text='ー')
        btn_vdown.bind(on_press=lambda x: send_ircc('VOL_DOWN'))
        btn_vup = Button(text='＋')
        btn_vup.bind(on_press=lambda x: send_ircc('VOL_UP'))
        btn_cdown = Button(text='ー')
        btn_cdown.bind(on_press=lambda x: send_ircc('CH_DOWN'))
        btn_cup = Button(text='＋')
        btn_cup.bind(on_press=lambda x: send_ircc('CH_UP'))
        
        vol_row.add_widget(btn_mute)
        vol_row.add_widget(btn_vdown)
        vol_row.add_widget(btn_vup)
        vol_row.add_widget(btn_cdown)
        vol_row.add_widget(btn_cup)
        layout.add_widget(vol_row)

        # 4. 戻る / テレビ / ホーム
        row4 = GridLayout(cols=3, spacing=6, size_hint_y=None, height=54)
        btn_back = Button(text='戻る', background_color=(0.11, 0.11, 0.12, 1))
        btn_back.bind(on_press=lambda x: send_ircc('BACK'))
        btn_tv = Button(text='テレビ', background_color=(0.17, 0.17, 0.18, 1))
        btn_tv.bind(on_press=lambda x: send_ircc('TV'))
        btn_home = Button(text='ホーム', background_color=(0.09, 0.09, 0.09, 1))
        btn_home.bind(on_press=lambda x: send_ircc('HOME'))
        row4.add_widget(btn_back)
        row4.add_widget(btn_tv)
        row4.add_widget(btn_home)
        layout.add_widget(row4)

        root.add_widget(layout)
        return root

if __name__ == '__main__':
    BraviaRemoteApp().run()
