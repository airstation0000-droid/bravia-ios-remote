import sys
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout

# iOS標準のWKWebViewを呼び出すKivyコンポーネント
HTML_REMOTE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Bravia Remote</title>
<style>
  * { box-sizing: border-box; touch-action: manipulation; user-select: none; }
  body { background-color: #000; color: #fff; font-family: -apple-system, sans-serif; margin: 0; padding: 10px 8px; width: 100vw; overflow-x: hidden; }
  .grid { display: grid; gap: 6px; margin-bottom: 10px; }
  .row-4 { grid-template-columns: repeat(4, 1fr); }
  .row-3 { grid-template-columns: repeat(3, 1fr); }
  .row-vol { grid-template-columns: 60px 72px 72px 67px 67px; justify-content: center; }
  button {
    background: rgba(44, 44, 46, 0.85); color: #fff; border: none; border-radius: 10px;
    font-size: 15px; font-weight: bold; height: 54px; display: flex; align-items: center; justify-content: center; text-align: center;
  }
  button:active { background: #555 !important; opacity: 0.8; }
  .bg-blue { background: #0a84ff; } .bg-green { background: #30d158; } .bg-red { background: #ff453a; }
  .bg-dark { background: rgba(28, 28, 30, 0.85); } .bg-dpad { background: rgba(44, 44, 46, 0.85); font-size: 22px; height: 62px; }
  .bg-select { background: rgba(58, 58, 60, 0.85); font-size: 15px; height: 62px; }
  .text-blue { color: #64d2ff; }
  .dpad-grid { display: grid; grid-template-columns: 104px 104px 104px; justify-content: center; gap: 6px; margin: 8px 0; }
  .label-row { display: flex; justify-content: space-around; font-size: 13px; color: #aaa; margin-top: 10px; margin-bottom: 2px; }
  .color-bar { height: 24px; border-radius: 6px; }
</style>
</head>
<body>
  <div class="grid row-4">
    <button class="bg-dark" style="font-size:12px; color:#aaa;">≡ 設定</button>
    <button onclick="sendIRCC('Digital')">地デジ</button>
    <button onclick="sendIRCC('BS')">BS/CS</button>
    <button class="bg-green" onclick="sendIRCC('TvPower')">電源</button>
  </div>
  <div class="dpad-grid">
    <div></div><button class="bg-dpad" onclick="sendIRCC('Up')">▲</button><div></div>
    <button class="bg-dpad" onclick="sendIRCC('Left')">◄</button>
    <button class="bg-select" onclick="sendIRCC('Confirm')">◆ 決定</button>
    <button class="bg-dpad" onclick="sendIRCC('Right')">►</button>
    <div></div><button class="bg-dpad" onclick="sendIRCC('Down')">▼</button><div></div>
  </div>
  <div class="label-row"><span>音量</span><span>チャンネル</span></div>
  <div class="grid row-vol">
    <button class="bg-dark" style="font-size:13px;" onclick="sendIRCC('Mute')">消音</button>
    <button style="font-size:20px;" onclick="sendIRCC('VolumeDown')">ー</button>
    <button style="font-size:20px;" onclick="sendIRCC('VolumeUp')">＋</button>
    <button style="font-size:18px;" onclick="sendIRCC('ChannelDown')">ー</button>
    <button style="font-size:18px;" onclick="sendIRCC('ChannelUp')">＋</button>
  </div>
  <div class="grid row-3">
    <button class="bg-dark text-blue" onclick="sendIRCC('Return')">戻る</button>
    <button onclick="sendIRCC('Tv')">テレビ</button>
    <button class="bg-dark text-blue" onclick="sendIRCC('Home')">ホーム</button>
  </div>
  <div class="grid row-3">
    <button onclick="sendIRCC('Input')">入力切換</button>
    <button class="bg-blue" onclick="sendIRCC('EPG')">番組表</button>
    <button style="font-size:13px;" onclick="sendIRCC('ActionMenu')">メニュー</button>
  </div>
  <div class="grid row-4" style="margin-top: 6px;">
    <button class="color-bar" style="background:#0a84ff;" onclick="sendIRCC('Blue')"></button>
    <button class="color-bar" style="background:#ff453a;" onclick="sendIRCC('Red')"></button>
    <button class="color-bar" style="background:#30d158;" onclick="sendIRCC('Green')"></button>
    <button class="color-bar" style="background:#ffd60a;" onclick="sendIRCC('Yellow')"></button>
  </div>
<script>
let braviaIP = "192.168.1.128";
function sendIRCC(name) {
  const codes = {
    'TvPower':'AAAAAQAAAAEAAAAVAw==','Digital':'AAAAAgAAAJcAAAANAw==','BS':'AAAAAgAAAJcAAAAPAw==',
    'VolumeUp':'AAAAAQAAAAEAAAASAw==','VolumeDown':'AAAAAQAAAAEAAAATAw==','Mute':'AAAAAQAAAAEAAAAUAw==',
    'ChannelUp':'AAAAAQAAAAEAAAAQAw==','ChannelDown':'AAAAAQAAAAEAAAARAw==',
    'Up':'AAAAAQAAAAEAAAB0Aw==','Down':'AAAAAQAAAAEAAAB1Aw==','Left':'AAAAAQAAAAEAAAA0Aw==','Right':'AAAAAQAAAAEAAAAzAw==','Confirm':'AAAAAQAAAAEAAABlAw==',
    'Return':'AAAAAgAAAJcAAAAjAw==','Tv':'AAAAAB0AAAABAAAABg==','Home':'AAAAAQAAAAEAAABgAw==',
    'Input':'AAAAAQAAAAEAAAAlAw==','EPG':'AAAAAgAAAKAAAABbAw==','ActionMenu':'AAAAAGADAAAAHQAAABo='
  };
  const code = codes[name];
  if (!code) return;
  const url = "http://" + braviaIP + "/sony/IRCC";
  const xmlData = '<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1"><IRCCCode>' + code + '</IRCCCode></u:X_SendIRCC></s:Body></s:Envelope>';
  
  const xhr = new XMLHttpRequest();
  xhr.open("POST", url, true);
  xhr.setRequestHeader("Content-Type", "text/xml; charset=UTF-8");
  xhr.setRequestHeader("SOAPACTION", '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"');
  xhr.send(xmlData);
}
</script>
</body>
</html>"""

class BraviaApp(App):
    def build(self):
        # HTMLをローカル保存して表示する標準Webビュー
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(HTML_REMOTE)
        layout = BoxLayout()
        return layout

if __name__ == '__main__':
    BraviaApp().run()
