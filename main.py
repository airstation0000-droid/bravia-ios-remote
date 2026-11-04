import json
import os
import random
import socket
import time
import requests
from requests.auth import HTTPBasicAuth
from ctypes import cdll
import dialogs
import ui
import photos
import io

# --------------------------------------------------
# 設定情報 & 自動IP検索処理
# --------------------------------------------------
DEFAULT_IP = "192.168.1.128"
AUTH_FILE = 'bravia_auth.json'
SETTINGS_FILE = 'bravia_settings.json'
APP_SHORTCUTS_FILE = 'bravia_apps.json'
CUSTOM_BG_FILE = 'bravia_bg.png'
ICON_CACHE_DIR = 'bravia_icons'

if not os.path.exists(ICON_CACHE_DIR):
    os.makedirs(ICON_CACHE_DIR)

RANDOM_SUFFIX = random.randint(100, 999)
CLIENT_ID = f"PythonistaRemote:{RANDOM_SUFFIX}"

THEMES = {
    '漆黒ブラック': ('#000000', '#0a0a0a'),
    'ビビッドピンク': ('#ff1493', '#c71585'),
    'ネオンレッド': ('#ff0055', '#cc0044'),
    'スカイブルー': ('#00bfff', '#0099cc'),
    'ライムグリーン': ('#00e676', '#00b359'),
    'サイバーパープル': ('#9d00ff', '#7a00cc'),
    'サンシャインオレンジ': ('#ff6600', '#cc5200'),
    'ターコイズ': ('#00e5ff', '#00b3cc'),
    'ディープネイビー': ('#0f2027', '#050d1a'),
    'ダークグレー': ('#2c3e50', '#1a252f')
}

APP_CONFIG = {
    'theme': 'ビビッドピンク'
}

# 初期設定:3つとも「未設定(空)」
DEFAULT_SHORTCUTS = [
    {"title": "未設定", "uri": "", "icon_url": ""},
    {"title": "未設定", "uri": "", "icon_url": ""},
    {"title": "未設定", "uri": "", "icon_url": ""}
]

def load_app_settings():
    global APP_CONFIG
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                APP_CONFIG.update(json.load(f))
        except Exception: pass

def save_app_settings():
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(APP_CONFIG, f)
    except Exception: pass

def load_shortcuts():
    if os.path.exists(APP_SHORTCUTS_FILE):
        try:
            with open(APP_SHORTCUTS_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    while len(data) < 3:
                        data.append({"title": "未設定", "uri": "", "icon_url": ""})
                    return data[:3]
        except Exception: pass
    return DEFAULT_SHORTCUTS.copy()

def save_shortcuts(shortcuts):
    try:
        with open(APP_SHORTCUTS_FILE, 'w') as f:
            json.dump(shortcuts, f)
    except Exception: pass

load_app_settings()

try:
    AudioToolbox = cdll.LoadLibrary('/System/Library/Frameworks/AudioToolbox.framework/AudioToolbox')
    AudioServicesPlaySystemSound = AudioToolbox.AudioServicesPlaySystemSound
except Exception:
    AudioServicesPlaySystemSound = None

def trigger_haptic():
    if AudioServicesPlaySystemSound:
        try:
            AudioServicesPlaySystemSound(1519)
        except Exception:
            pass

def discover_bravia_ip():
    msg = (
        'M-SEARCH * HTTP/1.1\r\n'
        'HOST: 239.255.255.250:1900\r\n'
        'MAN: "ssdp:discover"\r\n'
        'MX: 2\r\n'
        'ST: urn:schemas-sony-com:service:ScalarWebAPI:1\r\n\r\n'
    )
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(2.0)
    try:
        sock.sendto(msg.encode('utf-8'), ('239.255.255.250', 1900))
        while True:
            data, addr = sock.recvfrom(1024)
            if b'ScalarWebAPI' in data or b'sony' in data.lower():
                found_ip = addr[0]
                return found_ip
    except Exception:
        pass
    finally:
        sock.close()
    return None

def check_ip_alive(ip):
    try:
        res = requests.get(f"http://{ip}/sony/system", timeout=1.5)
        return True
    except Exception:
        return False

BRAVIA_IP = DEFAULT_IP

def show_network_error():
    dialogs.alert(
        "接続エラー",
        "テレビとスマホが同じ Wi-Fi に接続されていないか、テレビの電源が入っていません。\nネットワークを確認してください。",
        "OK",
        hide_cancel_button=True
    )

def register_pin(ip):
    url = f"http://{ip}/sony/accessControl"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "method": "actRegister",
        "params": [{"clientid": CLIENT_ID, "nickname": "iPhone Remote"}, [{"clientid": CLIENT_ID, "value": "yes", "nickname": "iPhone Remote", "function": "WOL"}]],
        "id": 1, "version": "1.0"
    }
    try:
        session = requests.Session()
        res = session.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code == 401:
            pin = dialogs.input_alert('BRAVIAペアリング', f'テレビ({ip})の4桁PINを入力してください:', '', '送信')
            if not pin: return None
            auth_res = session.post(url, json=payload, headers=headers, auth=HTTPBasicAuth('', pin), timeout=5)
            if auth_res.status_code == 200:
                cookie_dict = session.cookies.get_dict()
                auth_data = {'ip': ip, 'pin': pin, 'cookies': cookie_dict}
                with open(AUTH_FILE, 'w') as f: json.dump(auth_data, f)
                return auth_data
    except Exception as e:
        print(f"接続エラー: {e}")
    return None

def get_auth():
    global BRAVIA_IP
    saved_ip = DEFAULT_IP
    if os.path.exists(AUTH_FILE):
        try:
            with open(AUTH_FILE, 'r') as f:
                data = json.load(f)
                if data.get('ip'): saved_ip = data['ip']
                if data.get('cookies') and check_ip_alive(saved_ip):
                    BRAVIA_IP = saved_ip
                    return data
        except Exception: pass

    new_ip = discover_bravia_ip()
    if new_ip:
        BRAVIA_IP = new_ip
        if os.path.exists(AUTH_FILE):
            try:
                with open(AUTH_FILE, 'r') as f:
                    data = json.load(f)
                    data['ip'] = BRAVIA_IP
                    with open(AUTH_FILE, 'w') as f_out: json.dump(data, f_out)
                    return data
            except Exception: pass

    auth = register_pin(BRAVIA_IP)
    if not auth:
        show_network_error()
    return auth

AUTH_INFO = get_auth()
AVAILABLE_CODES = {}

def fetch_bravia_supported_codes():
    global AVAILABLE_CODES
    if not AUTH_INFO or 'cookies' not in AUTH_INFO: return
    url = f"http://{BRAVIA_IP}/sony/system"
    headers = {'Content-Type': 'application/json'}
    payload = {"method": "getRemoteControllerInfo", "params": [], "id": 1, "version": "1.0"}
    try:
        res = requests.post(url, json=payload, headers=headers, cookies=AUTH_INFO['cookies'], timeout=5)
        if res.status_code == 200:
            data = res.json()
            results = data.get('result', [])
            if len(results) > 1:
                for item in results[1]:
                    AVAILABLE_CODES[item['name']] = item['value']
    except Exception as e:
        print(f"Error: {e}")

if AUTH_INFO:
    fetch_bravia_supported_codes()

def send_ircc_raw(code):
    if not AUTH_INFO or 'cookies' not in AUTH_INFO:
        show_network_error()
        return
    url = f"http://{BRAVIA_IP}/sony/IRCC"
    headers = {'Content-Type': 'text/xml; charset=UTF-8', 'SOAPACTION': '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"'}
    body = f'''<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1"><IRCCCode>{code}</IRCCCode></u:X_SendIRCC></s:Body></s:Envelope>'''
    try:
        res = requests.post(url, headers=headers, data=body.encode('utf-8'), cookies=AUTH_INFO['cookies'], timeout=2)
        if res.status_code != 200:
            show_network_error()
    except Exception:
        show_network_error()

def send_ircc_by_name(possible_names):
    if isinstance(possible_names, str):
        possible_names = [possible_names]
    target_code = None
    for name in possible_names:
        if name in AVAILABLE_CODES:
            target_code = AVAILABLE_CODES[name]
            break
    if target_code:
        send_ircc_raw(target_code)
        return True
    else:
        show_network_error()
    return False

def open_epg():
    success = send_ircc_by_name(['EPG', 'Epg', 'TvGuide', 'Guide'])
    if not success:
        send_ircc_raw('AAAAAgAAAKAAAABbAw==')

def open_rec_list_app():
    launch_app_by_uri("com.sony.dtv.com.sony.dtv.recapp.com.sony.dtv.recapp.MainActivityIcon")

def launch_app_by_uri(target_uri):
    if not AUTH_INFO or 'cookies' not in AUTH_INFO:
        show_network_error()
        return
    url = f"http://{BRAVIA_IP}/sony/appControl"
    headers = {'Content-Type': 'application/json'}
    payload = {"method": "setActiveApp", "params": [{"uri": target_uri}], "id": 1, "version": "1.0"}
    try:
        res = requests.post(url, json=payload, headers=headers, cookies=AUTH_INFO['cookies'], timeout=3)
        if res.status_code != 200:
            show_network_error()
    except Exception:
        show_network_error()

def fetch_installed_apps():
    if not AUTH_INFO or 'cookies' not in AUTH_INFO:
        return []
    url = f"http://{BRAVIA_IP}/sony/appControl"
    headers = {'Content-Type': 'application/json'}
    payload = {"method": "getApplicationList", "params": [], "id": 1, "version": "1.0"}
    try:
        res = requests.post(url, json=payload, headers=headers, cookies=AUTH_INFO['cookies'], timeout=4)
        if res.status_code == 200:
            data = res.json()
            results = data.get('result', [])
            if results and len(results) > 0:
                return results[0]
    except Exception as e:
        print(f"App fetch error: {e}")
    return []

def download_and_cache_icon(icon_url, app_title):
    if not icon_url:
        return None
    cache_path = os.path.join(ICON_CACHE_DIR, f"{abs(hash(app_title))}.png")
    if os.path.exists(cache_path):
        return cache_path
    try:
        res = requests.get(icon_url, timeout=3)
        if res.status_code == 200:
            with open(cache_path, 'wb') as f:
                f.write(res.content)
            return cache_path
    except Exception as e:
        print(f"Icon download failed: {e}")
    return None

KEY_MAPPING = {
    'INPUT': ['Input', 'TvInput'],
    'MENU': ['ActionMenu', 'Options'],
    'POWER': ['TvPower', 'PowerOff', 'Power'],
    'UP': ['Up'],
    'DOWN': ['Down'],
    'LEFT': ['Left'],
    'RIGHT': ['Right'],
    'SELECT': ['Confirm', 'OK'],
    'BACK': ['Return', 'Back'],
    'HOME': ['Home'],
    'TV': ['Tv', 'TvPower', 'Digital'],
    'TERRESTRIAL': ['Digital', 'Tv'],
    'BS_CS': ['BS', 'BSCS', 'CS'],
    'MUTE': ['Mute'],
    'VOL_UP': ['VolumeUp'],
    'VOL_DOWN': ['VolumeDown'],
    'CH_UP': ['ChannelUp'],
    'CH_DOWN': ['ChannelDown'],
    'NUM_1': ['Num1'], 'NUM_2': ['Num2'], 'NUM_3': ['Num3'],
    'NUM_4': ['Num4'], 'NUM_5': ['Num5'], 'NUM_6': ['Num6'],
    'NUM_7': ['Num7'], 'NUM_8': ['Num8'], 'NUM_9': ['Num9'],
    'NUM_10': ['Num0', 'Num10'], 'NUM_11': ['Num11'], 'NUM_12': ['Num12'],
    'BLUE': ['Blue'], 'RED': ['Red'], 'GREEN': ['Green'], 'YELLOW': ['Yellow'],
    'DATA': ['Ddata', 'GGuide', 'Data'],
    'AUDIO_SELECT': ['Audio', 'AudioSelect', 'AudioChange'],
    'SUBTITLE': ['Subtitle', 'SubTitle'],
    'RECORDER_HOME': ['BraviaSyncMenu', 'SyncMenu', 'Media'],
    'REWIND': ['Rewind'], 'PLAY': ['Play'], 'FF': ['Forward', 'FastForward'],
    'PREV': ['Prev', 'Previous'], 'PAUSE': ['Pause'], 'NEXT': ['Next'],
    'STOP': ['Stop'],
}

def handle_btn_press(sender, cmd):
    trigger_haptic()
    if cmd == 'EPG':
        open_epg()
    elif cmd == 'REC_LIST':
        open_rec_list_app()
    elif cmd in KEY_MAPPING:
        send_ircc_by_name(KEY_MAPPING[cmd])

def select_app_for_slot(slot_index, view_instance):
    dialogs.hud_alert("テレビからアプリ一覧を取得中...")
    apps = fetch_installed_apps()
    if not apps:
        dialogs.alert("取得失敗", "テレビからアプリ一覧を取得できませんでした。\nWi-Fi接続を確認してください。", "OK", hide_cancel_button=True)
        return

    app_names = [app.get('title', 'Unknown') for app in apps]
    selected_name = dialogs.list_dialog(f"アプリボタン{slot_index+1}に割り当てるアプリを選択", app_names)
    
    if selected_name:
        for app in apps:
            if app.get('title') == selected_name:
                shortcuts = load_shortcuts()
                icon_url = app.get('icon', '')
                download_and_cache_icon(icon_url, selected_name)
                
                new_item = {
                    "title": selected_name,
                    "uri": app.get('uri'),
                    "icon_url": icon_url
                }
                shortcuts[slot_index] = new_item
                save_shortcuts(shortcuts)
                view_instance.update_app_shortcuts_ui()
                dialogs.hud_alert(f"「{selected_name}」を設定しました")
                break

def open_settings(view_instance):
    global AUTH_INFO, BRAVIA_IP
    
    options = [
        "📱 アプリショートカットボタン変更",
        "🖼 写真から背景画像を選択",
        "🎨 カラーテーマに変更",
        "🌐 IPアドレスを手動変更",
        "🔑 ペアリング情報の初期化"
    ]
    if os.path.exists(CUSTOM_BG_FILE):
        options.insert(2, "🗑 カスタム背景画像を削除")

    selected = dialogs.list_dialog(f"アプリ設定 (IP: {BRAVIA_IP})", options)
    
    if not selected:
        return

    if selected == "📱 アプリショートカットボタン変更":
        shortcuts = load_shortcuts()
        slot_opts = [f"ボタン{i+1}: {s['title']}" for i, s in enumerate(shortcuts)]
        slot_sel = dialogs.list_dialog("変更するアプリボタンを選択", slot_opts)
        if slot_sel:
            slot_idx = slot_opts.index(slot_sel)
            select_app_for_slot(slot_idx, view_instance)

    elif selected == "🖼 写真から背景画像を選択":
        img = photos.pick_image()
        if img:
            try:
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                with open(CUSTOM_BG_FILE, 'wb') as f:
                    f.write(buffer.getvalue())
                view_instance.apply_theme(APP_CONFIG.get('theme', 'ビビッドピンク'))
                dialogs.hud_alert("背景画像を設定しました")
            except Exception as e:
                dialogs.alert("画像保存エラー", f"画像の読み込みに失敗しました:\n{e}", "OK", hide_cancel_button=True)

    elif selected == "🗑 カスタム背景画像を削除":
        if os.path.exists(CUSTOM_BG_FILE):
            os.remove(CUSTOM_BG_FILE)
            view_instance.apply_theme(APP_CONFIG.get('theme', 'ビビッドピンク'))
            dialogs.hud_alert("画像を削除しテーマに戻しました")

    elif selected == "🎨 カラーテーマに変更":
        theme_names = list(THEMES.keys())
        theme_sel = dialogs.list_dialog("カラーテーマを選択", theme_names)
        if theme_sel and theme_sel in THEMES:
            APP_CONFIG['theme'] = theme_sel
            save_app_settings()
            if os.path.exists(CUSTOM_BG_FILE):
                os.remove(CUSTOM_BG_FILE)
            view_instance.apply_theme(theme_sel)
            dialogs.hud_alert(f"{theme_sel} に変更しました")

    elif selected == "🌐 IPアドレスを手動変更":
        new_ip = dialogs.input_alert("IPアドレス変更", "テレビのIPを入力してください", BRAVIA_IP)
        if new_ip:
            BRAVIA_IP = new_ip
            if AUTH_INFO:
                AUTH_INFO['ip'] = new_ip
                with open(AUTH_FILE, 'w') as f: json.dump(AUTH_INFO, f)
            dialogs.hud_alert("IPアドレスを変更しました")

    elif selected == "🔑 ペアリング情報の初期化":
        if os.path.exists(AUTH_FILE):
            os.remove(AUTH_FILE)
            dialogs.hud_alert("設定を初期化しました")

class BraviaFullRemoteView(ui.View):
    def __init__(self):
        self.name = 'Braviaリモコン'

        self.bg_image_view = ui.ImageView()
        self.bg_image_view.flex = 'WH'
        self.bg_image_view.content_mode = ui.CONTENT_SCALE_ASPECT_FILL
        self.add_subview(self.bg_image_view)

        self.scroll = ui.ScrollView()
        self.scroll.flex = 'WH'
        self.add_subview(self.scroll)

        current_theme = APP_CONFIG.get('theme', 'ビビッドピンク')
        self.apply_theme(current_theme)

        margin = 8
        total_w = 366
        y = 12

        # --------------------------------------------------
        # 1. 最上部(1行目): アプリ設定 / 地デジ / BS/CS / 電源
        # --------------------------------------------------
        w4 = (total_w - 3 * 6) // 4
        
        btn_set = ui.Button(title="≡ アプリ設定")
        btn_set.frame = (margin, y, w4, 56)
        btn_set.background_color = '#1c1c1e'
        btn_set.tint_color = '#aaaaaa'
        btn_set.corner_radius = 10
        btn_set.font = ('<system-bold>', 13)
        btn_set.action = lambda sender: open_settings(self)
        self.scroll.add_subview(btn_set)

        self.add_btn('地デジ', 'TERRESTRIAL', (margin + w4 + 6, y, w4, 56), bg='#2c2c2e', font_size=15)
        self.add_btn('BS/CS', 'BS_CS', (margin + (w4 + 6) * 2, y, w4, 56), bg='#2c2c2e', font_size=15)
        self.add_btn('電源', 'POWER', (margin + (w4 + 6) * 3, y, w4, 56), bg='#30d158', font_size=15)
        y += 68

        # --------------------------------------------------
        # 2. 画面中央:超大型 十字キー & 決定キー
        # --------------------------------------------------
        btn_w = 104
        btn_h = 62
        cx = margin + (total_w - btn_w) // 2
        
        self.add_btn('▲', 'UP', (cx, y, btn_w, btn_h), bg='#2c2c2e', font_size=22)
        y += 66
        self.add_btn('◄', 'LEFT', (cx - btn_w - 6, y, btn_w, btn_h), bg='#2c2c2e', font_size=22)
        self.add_btn('◆ 決定', 'SELECT', (cx, y, btn_w, btn_h), bg='#3a3a3c', font_size=15)
        self.add_btn('►', 'RIGHT', (cx + btn_w + 6, y, btn_w, btn_h), bg='#2c2c2e', font_size=22)
        y += 66
        self.add_btn('▼', 'DOWN', (cx, y, btn_w, btn_h), bg='#2c2c2e', font_size=22)
        y += 76

        # --------------------------------------------------
        # 3. 音量 & チャンネルブロック
        # --------------------------------------------------
        lbl_v = ui.Label(frame=(margin, y, 210, 20), text='音量', text_color='#ffffff', alignment=ui.ALIGN_CENTER)
        lbl_v.font = ('<system-bold>', 13)
        self.scroll.add_subview(lbl_v)

        lbl_c = ui.Label(frame=(margin + 224, y, 142, 20), text='チャンネル', text_color='#ffffff', alignment=ui.ALIGN_CENTER)
        lbl_c.font = ('<system-bold>', 13)
        self.scroll.add_subview(lbl_c)
        y += 22

        # 音量ブロック
        self.add_btn('消音', 'MUTE', (margin, y, 60, 54), bg='#1c1c1e', font_size=13)
        self.add_btn('ー', 'VOL_DOWN', (margin + 64, y, 72, 54), font_size=20)
        self.add_btn('+', 'VOL_UP', (margin + 140, y, 72, 54), font_size=20)

        # チャンネルブロック
        self.add_btn('ー', 'CH_DOWN', (margin + 224, y, 67, 54), font_size=18)
        self.add_btn('+', 'CH_UP', (margin + 295, y, 67, 54), font_size=18)
        y += 68

        # --------------------------------------------------
        # 4. 戻る / テレビ / ホーム
        # --------------------------------------------------
        w3 = (total_w - 2 * 6) // 3
        self.add_btn('戻る', 'BACK', (margin, y, w3, 54), bg='#1c1c1e', text_color='#64d2ff', font_size=15)
        self.add_btn('テレビ', 'TV', (margin + w3 + 6, y, w3, 54), bg='#2c2c2e', font_size=15)
        self.add_btn('ホーム', 'HOME', (margin + (w3 + 6) * 2, y, w3, 54), bg='#181818', text_color='#64d2ff', font_size=15)
        y += 60

        # --------------------------------------------------
        # 5. 入力切換 / 番組表 / メニュー
        # --------------------------------------------------
        self.add_btn('入力切換', 'INPUT', (margin, y, w3, 54), font_size=15)
        self.add_btn('番組表', 'EPG', (margin + w3 + 6, y, w3, 54), bg='#0a84ff', font_size=15)
        self.add_btn('メニュー', 'MENU', (margin + (w3 + 6) * 2, y, w3, 54), font_size=15)
        y += 68

        # --------------------------------------------------
        # アプリショートカットボタン(3枠)
        # --------------------------------------------------
        self.app_buttons_container = ui.View()
        self.app_buttons_container.frame = (margin, y, total_w, 56)
        self.scroll.add_subview(self.app_buttons_container)
        self.update_app_shortcuts_ui()
        y += 64

        # --------------------------------------------------
        # 6. カラーボタン
        # --------------------------------------------------
        cw = (total_w - 3 * 6) // 4
        self.add_btn('', 'BLUE', (margin, y, cw, 24), bg='#0a84ff')
        self.add_btn('', 'RED', (margin + cw + 6, y, cw, 24), bg='#ff453a')
        self.add_btn('', 'GREEN', (margin + (cw + 6) * 2, y, cw, 24), bg='#30d158')
        self.add_btn('', 'YELLOW', (margin + (cw + 6) * 3, y, cw, 24), bg='#ffd60a')
        y += 36

        # --------------------------------------------------
        # 7. テンキー
        # --------------------------------------------------
        nums_config = [
            ('1', 'NUM_1'), ('2', 'NUM_2'), ('3', 'NUM_3'),
            ('4', 'NUM_4'), ('5', 'NUM_5'), ('6', 'NUM_6'),
            ('7', 'NUM_7'), ('8', 'NUM_8'), ('9', 'NUM_9'),
            ('10', 'NUM_10'), ('11', 'NUM_11'), ('12', 'NUM_12')
        ]
        for i, (label, name) in enumerate(nums_config):
            r = i // 3
            c = i % 3
            bx = margin + c * (w3 + 6)
            by = y + r * 50
            self.add_btn(label, name, (bx, by, w3, 44), font_size=15)
        y += 210

        # --------------------------------------------------
        # 8. メディアコントロール群 & dデータ
        # --------------------------------------------------
        self.add_btn('音声切換', 'AUDIO_SELECT', (margin, y, w3, 44), font_size=13)
        self.add_btn('字幕', 'SUBTITLE', (margin + w3 + 6, y, w3, 44), font_size=13)
        self.add_btn('レコーダー\nホーム', 'RECORDER_HOME', (margin + (w3 + 6) * 2, y, w3, 44), font_size=13)
        y += 50

        self.add_btn('◄◄ 早戻し', 'REWIND', (margin, y, w3, 46), bg='#2c2c2e', font_size=13)
        self.add_btn('► 再生', 'PLAY', (margin + w3 + 6, y, w3, 46), bg='#30d158', font_size=15)
        self.add_btn('早送り ►►', 'FF', (margin + (w3 + 6) * 2, y, w3, 46), bg='#2c2c2e', font_size=13)
        y += 50

        self.add_btn('|◄ 前', 'PREV', (margin, y, w3, 46), font_size=13)
        self.add_btn('❚❚ 一時停止', 'PAUSE', (margin + w3 + 6, y, w3, 46), bg='#2c2c2e', font_size=13)
        self.add_btn('次 ►|', 'NEXT', (margin + (w3 + 6) * 2, y, w3, 46), font_size=13)
        y += 50

        self.add_btn('d (データ)', 'DATA', (margin, y, w3, 46), bg='#3a3a3c', font_size=13)
        self.add_btn('■ 停止', 'STOP', (margin + w3 + 6, y, w3, 46), bg='#ff453a', font_size=13)
        self.add_btn('録画リスト', 'REC_LIST', (margin + (w3 + 6) * 2, y, w3, 46), bg='#2c2c2e', font_size=13)
        y += 80

        self.scroll.content_size = (382, y)

    def update_app_shortcuts_ui(self):
        """アプリボタン描画更新"""
        for sub in list(self.app_buttons_container.subviews):
            self.app_buttons_container.remove_subview(sub)

        shortcuts = load_shortcuts()
        total_w = 366
        btn_w = (total_w - 2 * 6) // 3

        for i in range(3):
            item = shortcuts[i] if i < len(shortcuts) else {"title": "未設定", "uri": "", "icon_url": ""}
            bx = i * (btn_w + 6)
            
            btn = ui.Button()
            btn.frame = (bx, 0, btn_w, 54)
            btn.background_color = '#1c1c1e'
            btn.corner_radius = 12

            title = item.get('title', '未設定')
            icon_url = item.get('icon_url', '')
            cache_path = download_and_cache_icon(icon_url, title) if icon_url else None

            if cache_path and os.path.exists(cache_path):
                img = ui.Image.named(cache_path)
                if img:
                    btn.image = img.with_rendering_mode(ui.RENDERING_MODE_ORIGINAL)
            else:
                btn.title = title if title else "未設定"
                btn.tint_color = '#888888' if title == "未設定" else '#ffffff'
                btn.font = ('<system-bold>', 14)

            uri = item.get('uri')
            btn.action = lambda sender, u=uri, idx=i: self.on_app_btn_click(u, idx)
            self.app_buttons_container.add_subview(btn)

    def on_app_btn_click(self, uri, slot_idx):
        trigger_haptic()
        if uri:
            launch_app_by_uri(uri)
        else:
            select_app_for_slot(slot_idx, self)

    def apply_theme(self, theme_name):
        if os.path.exists(CUSTOM_BG_FILE):
            self.bg_image_view.image = ui.Image.named(CUSTOM_BG_FILE)
            self.background_color = '#000000'
            self.scroll.background_color = (0, 0, 0, 0)
        else:
            self.bg_image_view.image = None
            bg_color, scroll_color = THEMES.get(theme_name, THEMES['ビビッドピンク'])
            self.background_color = bg_color
            self.scroll.background_color = scroll_color

    def add_btn(self, title, name, frame, bg='#2c2c2e', text_color='#ffffff', font_size=15):
        btn = ui.Button(title=title)
        btn.name = name
        btn.frame = frame
        btn.background_color = bg
        btn.tint_color = text_color
        btn.corner_radius = 10
        btn.font = ('<system-bold>', font_size)
        btn.action = lambda sender, c=name: handle_btn_press(sender, c)
        self.scroll.add_subview(btn)

if __name__ == '__main__':
    view = BraviaFullRemoteView()
    view.present('fullscreen')
