import os
import sys
import random
import requests
import smtplib
import uuid
from email.mime.text import MIMEText
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS 

# --- HILFSFUNKTIONEN FÜR VERIFIZIERUNG & ACCOUNTS ---

def send_verification_email(user_email, code, username=None):
    sender_email = "cyhordream.community@gmail.com"
    app_password = "slfvxesasnpvvbor"  # Hinweis: Im Live-Betrieb am besten als Umgebungsvariable nutzen!

    if not app_password:
        print("Fehler: Bitte CYHORDREAM_GMAIL_APP_PASSWORD als Umgebungsvariable setzen.")
        return

    display_name = username or user_email
    email_text = f"""Hallo {display_name},

wir haben deine E-Mail erreicht und haben für dich einen Bestätigungscode:

{code}

Liebe Grüße
das Cyhordream Studios Team
"""

    # E-Mail-Inhalt für den Versand vorbereiten
    from email.mime.text import MIMEText
    msg = MIMEText(email_text, 'plain', 'utf-8')
    msg['Subject'] = "Cyhordream Studios - Verifizierung"
    msg['From'] = sender_email
    msg['To'] = user_email

    try:
        # HIER SIND DIE ZWEI WICHTIGEN NEUEN ZEILEN FÜR RENDER:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # Das schaltet die Verschlüsselung auf Port 587 live
        
        # Jetzt ganz normal einloggen und abschicken
        server.login(sender_email, app_password)
        server.sendmail(sender_email, [user_email], msg.as_string())
        server.quit()
        print("Verifizierungs-E-Mail erfolgreich gesendet!")
        
    except Exception as e:
        print(f"SMTP-Fehler: {e}")

def generate_account_token():
    return str(uuid.uuid4())[:16].upper() # Generiert einen 16-stelligen Token


# --- KONFIGURATION & GLOBALE VARIABLEN ---

app = Flask(__name__)
app = app
app.config['SECRET_KEY'] = 'geheimnis123'
WEBSITE_VERSION = "1.0.0Web"

# Zentrale Datenstrukturen
USERS_DB = {}
VERIFICATION_CODES = {} 

# Pfad zu den Spieldateien (Zentraler Download-Ordner unter static)
DOWNLOAD_FOLDER = os.path.join(app.root_path, 'static', 'downloads')
if not os.path.exists(DOWNLOAD_FOLDER): 
    os.makedirs(DOWNLOAD_FOLDER)

# Google Sheet Verknüpfung für das Leaderboard
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzEl-iVg50d2Anj7SzI4yRAJwK4PDJsDydk6ya52vp40nLsUbpCN-kOOIW8nvHaelo_JQ/exec"

CORS(app, resources={r"/api/*": {"origins": [
    "https://Cyhordream-Studios.de", 
    "https://cyhordream-studios.de", 
    "http://Cyhordream-Studios.de", 
    "http://127.0.0.1",
    "http://127.0.0.1:5000",
    "http://localhost",
    "http://localhost:5000"
]}}, supports_credentials=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_route'


# --- USER MANAGEMENT SYSTEM ---

class User(UserMixin):
    def __init__(self, id, email=None):
        self.id = id
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    if user_id not in USERS_DB: return None
    return User(user_id, USERS_DB[user_id].get('email'))


# --- WEB-DESIGN & NAVIGATION (CYBER-BLUE LOOK) ---

FINAL_CYBER_DESIGN = '''
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    @keyframes seitenEinblenden { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
    
    body { background-color: #1a252f; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; display: flex; flex-direction: column; min-height: 100vh; -webkit-user-select: none; user-select: none; animation: seitenEinblenden 0.6s ease forwards; }
    .top-bar { background-color: #1c2833; display: flex; justify-content: space-between; align-items: center; padding: 10px 5%; box-shadow: 0 4px 10px rgba(0,0,0,0.4); border-bottom: 1px solid #2c3e50; position: relative; z-index: 1000; }
    
    .top-logo { height: auto; width: 90px; object-fit: contain; cursor: pointer; }
    .nav-center { display: flex; gap: 20px; align-items: center; }
    .nav-right { display: flex; align-items: center; gap: 20px; }
    .nav-link { color: #ffffff; text-decoration: none; font-size: 16px; font-weight: 500; transition: color 0.3s ease; padding: 5px 10px; }
    .nav-link:hover { color: #3498db; }
    .lang-select { background-color: #2c3e50; color: #ffffff; border: 2px solid #34495e; padding: 6px 10px; border-radius: 6px; font-size: 14px; outline: none; cursor: pointer; }
    
    .main-content { flex: 1; display: flex; flex-direction: column; align-items: center; padding: 40px 5%; box-sizing: border-box; width: 100%; }
    .welcome-container { text-align: center; margin-bottom: 30px; max-width: 800px; }
    .welcome-title { font-size: 32px; color: #3498db; margin: 0 0 10px 0; font-weight: bold; }
    .welcome-text { font-size: 16px; color: #bdc3c7; margin: 0; line-height: 1.5; }
    
    .form-container { background-color: #111922; padding: 35px; border-radius: 8px; width: 100%; max-width: 600px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); text-align: center; box-sizing: border-box; }
    
    .btn-capsule-green { display: inline-block; padding: 14px 30px; background-color: #2ecc71; color: white; text-decoration: none; border-radius: 50px; font-weight: bold; font-size: 16px; transition: transform 0.2s, box-shadow 0.2s; border: none; cursor: pointer; margin-right: 15px; text-align: center; }
    .btn-capsule-green:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(46, 204, 113, 0.4); }
    .btn-capsule-blue { display: inline-block; padding: 14px 30px; background-color: #3498db; color: white; text-decoration: none; border-radius: 50px; font-weight: bold; font-size: 16px; transition: transform 0.2s, box-shadow 0.2s; border: none; cursor: pointer; text-align: center; }
    .btn-capsule-blue:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(52, 152, 219, 0.4); }

    .auth-title { color: #3498db; margin: 0 0 8px 0; font-size: 28px; }
    .auth-subtitle { color: #bdc3c7; margin: 0 0 22px 0; line-height: 1.5; font-size: 15px; }
    .auth-form { width: 100%; }
    .auth-divider { border: none; border-top: 1px solid #2c3e50; margin: 28px 0; }
    .error-message { width: 100%; max-width: 600px; background: rgba(231, 76, 60, 0.12); color: #ffb4a9; border: 1px solid rgba(231, 76, 60, 0.45); border-radius: 8px; padding: 12px 14px; box-sizing: border-box; font-weight: 700; text-align: center; }
    
    .btn-cyber { position: relative; display: inline-flex; align-items: center; justify-content: center; width: 100%; min-height: 54px; padding: 15px 24px; margin-top: 8px; border: 1px solid rgba(255,255,255,0.16); border-radius: 8px; color: #ffffff; font-size: 16px; font-weight: 800; letter-spacing: 0; text-decoration: none; cursor: pointer; box-sizing: border-box; transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease; box-shadow: 0 10px 24px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.22); }
    .btn-cyber:hover { transform: translateY(-2px); filter: brightness(1.08); }
    
    .btn-cyber-primary { background: linear-gradient(135deg, #3498db 0%, #2563eb 100%); box-shadow: 0 10px 24px rgba(52, 152, 219, 0.32), inset 0 1px 0 rgba(255,255,255,0.24); }
    .btn-cyber-success { background: linear-gradient(135deg, #2ecc71 0%, #16a085 100%); box-shadow: 0 10px 24px rgba(46, 204, 113, 0.28), inset 0 1px 0 rgba(255,255,255,0.24); }
    .btn-cyber-verify { background: linear-gradient(135deg, #f1c40f 0%, #e67e22 100%); color: #111922; box-shadow: 0 10px 24px rgba(230, 126, 34, 0.32), inset 0 1px 0 rgba(255,255,255,0.38); }
    .verify-hint { color: #bdc3c7; line-height: 1.6; margin: 0 0 20px 0; }
    .code-input { text-align: center; font-size: 22px; font-weight: 800; background: #2c3e50; color: white; border: 2px solid #34495e; padding: 14px; border-radius: 6px;}
    
    input, select, textarea { display: block; width: 100%; margin: 15px 0; padding: 14px; border-radius: 6px; border: 2px solid #34495e; background: #2c3e50; color: white; font-size: 16px; box-sizing: border-box; }
    .lang-de { display: none; } .lang-en { display: none; }

    @media screen and (max-width: 768px) {
        .top-bar { flex-direction: column; gap: 15px; padding: 15px; text-align: center; }
        .nav-center { width: 100%; justify-content: center; flex-wrap: wrap; gap: 10px; }
        .nav-right { width: 100%; justify-content: center; gap: 15px; }
        .nav-link { font-size: 16px; width: 45%; background-color: #2c3e50; border-radius: 6px; padding: 8px 0; border: 1px solid #34495e; text-align: center; }
        .main-content { padding: 20px 15px; }
        .welcome-title { font-size: 26px; }
        .btn-capsule-green, .btn-capsule-blue { width: 100%; margin-right: 0; margin-bottom: 15px; box-sizing: border-box; padding: 16px 20px; font-size: 17px; }
        .form-container { padding: 20px; width: 100%; }
    }
</style>
<script>
    function spracheWechseln(selectObj) { var lang = selectObj.value; localStorage.setItem('selectedLanguage', lang); anwenden(lang); }
    function anwenden(lang) {
        var deElements = document.querySelectorAll('.lang-de'); var enElements = document.querySelectorAll('.lang-en');
        if (lang === 'de') { deElements.forEach(el => el.style.display = 'inline-block'); enElements.forEach(el => el.style.display = 'none'); }
        else { deElements.forEach(el => el.style.display = 'none'); enElements.forEach(el => el.style.display = 'inline-block'); }
        
        var bottomDropdown = document.getElementById('langSelectBottom');
        if (bottomDropdown) bottomDropdown.value = lang;
        var topDropdown = document.getElementById('langSelect');
        if (topDropdown) topDropdown.value = lang;
    }
    window.addEventListener('DOMContentLoaded', (event) => {
        var savedLang = localStorage.getItem('selectedLanguage') || 'en';
        anwenden(savedLang);
    });
</script>
'''

def generiere_navigation():
    login_status_en, login_status_de, profile_url = "Login", "Anmelden", "/login"
    if current_user.is_authenticated:
        login_status_en, login_status_de, profile_url = f"Account: {current_user.id}", f"Konto: {current_user.id}", "/dashboard"
    
    aktuelle_route = request.path
    link_home = f'<a href="/" class="nav-link"><span class="lang-en">Home</span><span class="lang-de">Startseite</span></a>' if aktuelle_route != '/' else ''
    
    if aktuelle_route == '/login':
        link_about, link_news, link_download = '', '', ''
    else:
        link_about = f'<a href="/about" class="nav-link"><span class="lang-en">About us</span><span class="lang-de">Über uns</span></a>' if aktuelle_route != '/about' else ''
        link_news = f'<a href="/news" class="nav-link"><span class="lang-en">News 📰</span><span class="lang-de">Neuigkeiten 📰</span></a>' if aktuelle_route != '/news' else ''
        
        if aktuelle_route in ['/download-launcher-page', '/game/click-a-cube', '/play-web']:
            link_download = ''
        else:
            link_download = f'<a href="/download-launcher-page" class="nav-link"><span class="lang-en">Download 📥</span><span class="lang-de">Herunterladen 📥</span></a>'
        
    return f'''
    <div class="top-bar">
        <a href="/"><img src="/static/System_Assets/Logo.png" alt="Cyhordream Logo" class="top-logo" style="max-width: 90px; height: auto;" onerror="this.src='https://placehold.co'">
        <div class="nav-center">
            {link_home}
            {link_about}
            {link_news}
            {link_download}
        </div>
        <div class="nav-right">
            <a href="{profile_url}" class="nav-link">
                <span class="lang-en">{login_status_en}</span><span class="lang-de">{login_status_de}</span>
            </a>
            <select id="langSelect" class="lang-select" onchange="spracheWechseln(this)">
                <option value="en">EN</option>
                <option value="de">DE</option>
            </select>
        </div>
    </div>
    '''


# --- APP ROUTEN / SEITEN ---

@app.route('/')
def home():
    return f'''<!DOCTYPE html>
    <html>
    <head>
        <title>Cyhordream Studios</title>
        <link rel="icon" type="image/png" href="/static/System_Assets/Logo.png">
        {FINAL_CYBER_DESIGN}
    </head>
    <body>
    {generiere_navigation()}
    <div class="main-content">
        <div class="welcome-container">
            <h1 class="welcome-title">
                <span class="lang-en">Welcome to Cyhordream Studios! 🚀</span>
                <span class="lang-de">Willkommen bei Cyhordream Studios! 🚀</span>
            </h1>
            <p class="welcome-text">
                <span class="lang-en">Explore our official gaming hub, play unique web-experiences directly in your browser, and get the latest updates on our development journey.</span>
                <span class="lang-de">Erkunde unsere offizielle Gaming-Zentrale, spiele einzigartige Web-Erlebnisse direkt im Browser und hole dir die neuesten Updates unserer Entwicklerreise.</span>
            </p>
        </div>

        <a href="/game/click-a-cube" style="display:block; text-decoration:none; margin-top: 10px; width: 100%; max-width: 950px; background:#111922; border-radius:8px; overflow:hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid #2c3e50; transition: transform 0.2s;">
            <img src="/static/System_Assets/cube_game.png" alt="Click a Cube" style="width:100%; height:auto; display:block;" onerror="this.src='https://placehold.co'">
            <div style="padding: 25px; display: flex; justify-content: space-between; align-items: center; background: #111922;">
                <div>
                    <h2 style="margin: 0; color: #3498db; font-size: 26px;">Click a Cube Web 🎮</h2>
                    <p style="font-size:14.5px; color:#bdc3c7; margin-top: 8px; margin-bottom:0;">
                        <span class="lang-en">Open the official game station to view options and patchnotes.</span>
                        <span class="lang-de">Öffne die Spielstation, um Optionen und Patchnotes anzusehen.</span>
                    </p>
                </div>
                <div style="text-align:right; font-weight:bold; font-size:16px; color:#e67e22; min-width:180px; line-height:1.5;">
                    Download <br>
                    <span style="color:#3498db; font-size:14px;">Version: 3.0</span>
                </div>
            </div>
        </a>
    </div>
    </body>
    </html>'''

@app.route('/about')
def about():
    return f'''<!DOCTYPE html>
    <html>
    <head><title>About Us - Cyhordream Studios</title>{FINAL_CYBER_DESIGN}</head>
    <body>
    {generiere_navigation()}
    <div class="main-content">
        <div class="form-container" style="max-width: 750px; text-align: left; padding: 40px; line-height: 1.7; margin-top: 10px;">
            <h2 style="color: #3498db; margin-top: 0; border-bottom: 1px solid #2c3e50; padding-bottom: 15px;">
                <span class="lang-en">About Cyhordream Studios</span>
                <span class="lang-de">Über Cyhordream Studios</span>
            </h2>
            
            <div style="color:#bdc3c7; font-size: 15px; margin-bottom: 25px;">
                <p class="lang-en">
                    Hello and welcome to our development Studio there we create our own games for exaple Horror and Dreams game. Also we can write Engisch and German. Oh one thing I have to say, that is a German Studio because we are from Germany. But it doesn't matter. If a game release then you can say how good is it or if you find a bug, say it and we can fix it. Incidentally, we generally only use UE5. No, we aren't make Fangames.
                </p>
                <p class="lang-de">
                    Hallo und willkommen zu unseren Entwicklungsstudio da entwickeln wir unsere eigene Spiele wie Horror und Träume. Übrigens wir können Englisch und Deutsch schreiben. Oh ich habe noch was zu sagen, dass es ein deutscher Studio ist, weil wir aus Deutschland kommen. Aber darüber müsst ihr keine Sorgen machen Wenn ein Spiel veröfflicht sein sollte, dann könnt ihr sagen wie gut es it oder wenn ihr ein Bug findet einfach sagen und dann fixen wir es. Übrigens wir machen es generell nur mit der UE5. Nein wir tun keine Fangames machen.
                </p>
            </div>
            
            <p>
                <strong>CEOs:</strong> 
                <a href="https://www.youtube.com/@BeastboyblueCat" target="_blank" style="color: #3498db; text-decoration: none; font-weight: bold; margin-right: 5px; transition: color 0.2s;">@BeastboyblueCat 📺 </a>
                <span style="color: #bdc3c7; margin: 0 0px;">&</span>
                <a href="https://www.youtube.com/@Craftzone-8" target="_blank" style="color: #3498db; text-decoration: none; font-weight: bold; transition: color 0.2s;">@Craftzone-8 📺</a>
            </p>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="https://www.youtube.com/@Cyhordream-Studios" target="_blank" class="btn-capsule-blue" style="background-color: #e74c3c;">
                    <span class="lang-en">📺 Visit us on YouTube</span>
                    <span class="lang-de">📺 Besuche uns auf YouTube</span>
                </a>
            </div>
        </div>
    </div>
    </body>
    </html>'''

@app.route('/game/click-a-cube')
def game_detail():
    user_val = current_user.id if current_user.is_authenticated else ''
    return f'''<!DOCTYPE html>
    <html>
    <head><title>Click a Cube - Cyhordream Studios</title>{FINAL_CYBER_DESIGN}</head>
    <body>
    {generiere_navigation()}
    <div class="main-content" style="max-width:1000px; margin:0 auto; text-align:left;">
        <h2>Click a Cube Web 🎮</h2>
        
        <div style="width:100%; overflow:hidden; border-radius:8px; box-shadow: 0 4px 15px rgba(0,0,0,0.4); margin-bottom:25px;">
            <img src="/static/System_Assets/banner_cube.png" alt="Click a Cube Banner" style="width:100%; height:auto; display:block;" onerror="this.src='https://placehold.co'">
        </div>
        
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:40px; background:#111922; padding:20px; border-radius:8px;">
            <div>
                <a href="/play-web" class="btn-capsule-green">
                    <span class="lang-en">Launch Web Version</span>
                    <span class="lang-de">Web-Version starten</span>
                </a>
                
                <a href="/download-apk-file" class="btn-capsule-green" style="background-color: #e67e22; margin-right: 15px; box-shadow: 0 5px 15px rgba(230, 126, 34, 0.4);">
                    <span class="lang-en">Mobile Install</span>
                    <span class="lang-de">Mobil installieren</span>
                </a>
                
                <a href="/download-launcher-page" class="btn-capsule-blue">
                    <span class="lang-en">Download Launcher</span>
                    <span class="lang-de">Launcher herunterladen</span>
                </a>
            </div>
            <div style="text-align:right; font-weight:bold; font-size:16px; min-width: 160px;">
                <span style="color:#e67e22;">Release: 20.6.2026</span><br>
                <span style="color:#3498db;">Version: 3.0</span>
            </div>
        </div>

        <h2 style="color:#3498db; border-bottom:1px solid #2c3e50; padding-bottom:10px;">
            <span class="lang-en">Description:</span>
            <span class="lang-de">Beschreibung:</span>
        </h2>
        <div style="font-size:16px; line-height:1.7; color:#e2e8f0; margin-bottom:40px;">
            <p class="lang-en">Cube Clicker is an exciting incremental clicker game where every tap counts! Click on the cube to earn points, unlock powerful upgrades, and increase your clicking power. Start small and build your way up as each upgrade helps you collect points faster and more efficiently. Can you become the ultimate cube-clicking master? #pointnclick #Clicker</p>
            <p class="lang-de">Cube Clicker ist ein aufregendes Inkremental-Klickerspiel, bei dem jeder Klick zählt! Klicke auf den Würfel, um Punkte zu verdienen, mächtige Upgrades freizuschalten und deine Klickkraft zu steigern. Fange klein an und baue deinen Weg nach oben aus, da jedes Upgrade dir hilft, Punkte schneller und effizienter zu sammeln. Kannst du der ultimative Würfel-Klick-Meister werden? #pointnclick #Clicker</p>
        </div>

        <h2 style="color:#e67e22; border-bottom:1px solid #2c3e50; padding-bottom:10px;">Patchnotes (v3.0) - Completeupdate Patch:</h2>
        <div style="background:#111922; padding:25px; border-radius:6px; line-height:1.7; font-size:14.5px; color:#bdc3c7; box-shadow: inset 0 0 10px rgba(0,0,0,0.5); margin-bottom: 40px;">
            
            <div class="lang-de">
                <strong style="color:#2ecc71;">Deutsch:</strong><br>
                • Klick-Impuls & CPS-Sounds<br>
                • Währungssystem (Achievement-Punkte)<br>
                • Erfolge-Menü<br>
                • Fortschrittsbalken, glatte Prozente & Live-Restzeit<br>
                • Profil-Statistiken (Spielzeit, Max-CPS, Klicks heute)<br>
                • LinkedID-Serverfix & Neustart-Countdown<br>
                • Zahlen-Formatierung bis Dezillionen<br><br>
                <span style="color:#e74c3c; font-weight:bold;">Hinweis:</span> Das Spiel ist ab jetzt vollständig abgeschlossen. <br>
                Es werden keine neuen Inhalts-Updates mehr erscheinen. <br>
                Wir werden das Spiel ab hier nur noch mit reinen Bugfixes unterstützen. <br>
                Vielen Dank für euren gigantischen Support!
            </div>

            <div class="lang-en">
                <strong style="color:#3498db;">English:</strong><br>
                • Click Impulse & CPS Sounds<br>
                • Currency System (Achievement Points)<br>
                • Achievements Menu<br>
                • Progress Bar, Smooth Percentages & Live Remaining Time<br>
                • Profile Statistics (Playtime, Max CPS, Clicks Today)<br>
                • LinkedID Server Fix & Restart Countdown<br>
                • Number Formatting up to Decillions<br><br>
                <span style="color:#e74c3c; font-weight:bold;">Note:</span> The game is now fully completed. <br>
                No new content updates will be released. <br>
                From this point on, we will only support the game with pure bugfixes. <br>
                Thank you so much for your massive support!
            </div>
        </div>

        <h2 style="color:#3498db; border-bottom:1px solid #2c3e50; padding-bottom:10px;">
            <span class="lang-en">Leave a Review & Rating ⭐</span>
            <span class="lang-de">Schreibe ein Feedback & Bewertung ⭐</span>
        </h2>
        <div style="background:#111922; padding:25px; border-radius:6px; box-shadow: inset 0 0 10px rgba(0,0,0,0.5); margin-bottom: 20px;">
            <div id="feedback-message" style="display:none; margin-bottom:15px; font-weight:bold; padding: 10px; border-radius:4px;"></div>
            
            <form id="feedback-form" onsubmit="sendFeedback(event)">
                <input type="text" id="fb-username" placeholder="Dein Name / Your Name" value="{user_val}" required style="margin-top:0;">
                
                <label style="display:block; margin: 15px 0 5px 0; color:#bdc3c7; font-size:14px; font-weight:bold;">
                    <span class="lang-de">Bewertung (0 bis 5 Sterne):</span>
                    <span class="lang-en">Rating (0 to 5 Stars):</span>
                </label>
                <select id="fb-rating" style="cursor:pointer; outline:none;">
                    <option value="5">⭐⭐⭐⭐⭐ (5/5)</option>
                    <option value="4">⭐⭐⭐⭐ (4/5)</option>
                    <option value="3">⭐⭐⭐ (3/5)</option>
                    <option value="2">⭐⭐ (2/5)</option>
                    <option value="1">⭐ (1/5)</option>
                    <option value="0">❌ (0/5)</option>
                </select>
                
                <textarea id="fb-comment" placeholder="Schreibe deinen Kommentar hier hinein... / Write your comment here..." required style="min-height:120px; font-family:inherit; resize:vertical; outline:none;"></textarea>
                
                <button type="submit" class="btn-cyber btn-cyber-primary" style="margin-top:10px; min-height:45px; padding:10px 25px; width:auto; display:inline-block;">
                    <span class="lang-de">Feedback an Studio senden ✉️</span>
                    <span class="lang-en">Send Feedback to Studio ✉️</span>
                </button>
            </form>
        </div>
    </div>

    <script>
        function sendFeedback(event) {{
            event.preventDefault();
            const username = document.getElementById('fb-username').value;
            const rating = parseInt(document.getElementById('fb-rating').value);
            const comment = document.getElementById('fb-comment').value;
            const msgDiv = document.getElementById('feedback-message');
            
            fetch('/api/send_comment', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ username, rating, comment }})
            }})
            .then(res => res.json())
            .then(data => {{
                if(data.status === 'success') {{
                    msgDiv.style.display = 'block';
                    msgDiv.style.background = 'rgba(46, 204, 113, 0.15)';
                    msgDiv.style.color = '#2ecc71';
                    msgDiv.innerText = localStorage.getItem('selectedLanguage') === 'de' ? 'Vielen Dank! Dein Feedback wurde direkt an Cyhordream Studios gesendet.' : 'Thank you! Your review has been directly sent to Cyhordream Studios.';
                    document.getElementById('feedback-form').reset();
                }} else {{
                    msgDiv.style.display = 'block';
                    msgDiv.style.background = 'rgba(231, 76, 60, 0.15)';
                    msgDiv.style.color = '#e74c3c';
                    msgDiv.innerText = 'Error: ' + data.message;
                }}
            }})
            .catch(err => {{
                msgDiv.style.display = 'block';
                msgDiv.style.background = 'rgba(231, 76, 60, 0.15)';
                msgDiv.style.color = '#e74c3c';
                msgDiv.innerText = 'Verbindungsfehler / Connection Error.';
            }});
        }}
    </script>
    </body>
    </html>'''

@app.route('/news')
def news_page():
    return f'''<!DOCTYPE html>
    <html>
    <head>
        <title class="lang-en">News - Cyhordream Studios</title>
        <title class="lang-de">Neuigkeiten - Cyhordream Studios</title>
        {FINAL_CYBER_DESIGN}
    </head>
    <body>
    {generiere_navigation()}
    <div class="main-content">
        <div class="form-container" style="max-width: 750px; text-align: left; margin-top: 10px;">
            <h2 style="color: #3498db; margin-top: 0; margin-bottom: 20px;">
                <span class="lang-en">News 📰</span>
                <span class="lang-de">Neuigkeiten 📰</span>
            </h2>
            <div style="background: #2c3e50; padding: 20px; border-radius: 6px; font-family: monospace; line-height:1.6; color:white;">
                <div class="lang-de">
                    <strong>[!] WICHTIGE ANKÜNDIGUNG:</strong><br>
                    Die Website und der Launcher sind jetzt offiziell verfügbar! Unsere Spiele laufen ab jetzt nur noch auf unserer eigenen Website oder in unserem Launcher.
                </div>
                <div class="lang-en">
                    <strong>[!] IMPORTANT ANNOUNCEMENT:</strong><br>
                    The website and the launcher are now officially available! From now on, our games will only run on our own website or inside our launcher.
                </div>
            </div>
        </div>
    </div>
    </body>
    </html>'''


# --- WEBGL GAME PLAYER ENDPUNKTE ---

@app.route('/play-web')
def play_web():
    return f'''<!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <title>Click a Cube Web - Player</title>
        {FINAL_CYBER_DESIGN}
        <style>
            html, body {{ 
                margin: 0 !important; 
                padding: 0 !important; 
                width: 100vw !important; 
                height: 100vh !important; 
                overflow: hidden !important; 
                background: #111922;
            }}

            @media screen and (orientation: portrait) {{
                #portrait-warning {{ display: flex !important; }}
                .viewport-container {{ display: none !important; }}
            }}
            #portrait-warning {{ display: none; flex-direction: column; justify-content: center; align-items: center; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: #111922; color: #e67e22; text-align: center; z-index: 9999; font-weight: bold; padding: 20px; }}
            
            .viewport-container {{ 
                display: flex; 
                flex-direction: column; 
                width: 100vw; 
                height: 100vh; 
                box-sizing: border-box;
                overflow: hidden !important;
            }}
            
            .game-wrapper {{
                flex: 1;
                display: flex;
                align-items: center;
                justify-content: center;
                width: 100vw;
                height: calc(100vh - 45px); 
                background: #111922;
                overflow: hidden !important;
                position: relative;
            }}

            #game-box-container {{ 
                width: 100%;
                height: 100%;
                background: #000; 
                overflow: hidden !important;
            }}
            
            iframe {{ 
                width: 100% !important; 
                height: 100% !important; 
                border: none !important; 
                display: block !important; 
                overflow: hidden !important;
                position: absolute;
                top: 0;
                left: 0;
            }}
            
            .back-bar {{ 
                height: 45px; 
                min-height: 45px;
                display: flex; 
                align-items: center; 
                justify-content: space-between; 
                width: 100vw; 
                background: #111922; 
                border-top: 1px solid #2c3e50; 
                z-index: 100;
                box-sizing: border-box;
                padding: 0 20px;
            }}

            .back-bar-right {{
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 13px;
                color: #bdc3c7;
            }}

            .back-bar-select {{
                background-color: #2c3e50; 
                color: #ffffff; 
                border: 1px solid #34495e; 
                padding: 3px 8px; 
                border-radius: 4px; 
                font-size: 13px; 
                outline: none; 
                cursor: pointer;
            }}
        </style>
    </head>
    <body>
        
        <div id="portrait-warning">
            🔄 🔄 🔄<br><br>
            Bitte drehe dein Gerät ins Querformat (Landscape), um zu spielen!<br><br>
            Please rotate your device to landscape mode to play!
        </div>

        <div class="viewport-container">
            <div class="game-wrapper">
                <div id="game-box-container">
                    <iframe id="unity-iframe" src="/static/Click a Cube Web/index.html" allow="autoplay; fullscreen; xr-spatial-tracking" allowfullscreen scrolling="no"></iframe>
                </div>
            </div>
            
            <div class="back-bar">
                <a href="/game/click-a-cube" target="_top" style="color:#3498db; font-weight:bold; text-decoration:none; font-size:14px;">
                    <span class="lang-de">← Zurück zur Spielstation</span>
                    <span class="lang-en">← Back to game station</span>
                </a>

                <div class="back-bar-right">
                    <span>
                        <span class="lang-de">(nur für Spielestation)</span>
                        <span class="lang-en">(only for game station)</span>
                    </span>
                    <select id="langSelectBottom" class="back-bar-select" onchange="spracheWechseln(this)">
                        <option value="en">EN</option>
                        <option value="de">DE</option>
                    </select>
                </div>
            </div>
        </div>

        <script>
            window.addEventListener('DOMContentLoaded', (event) => {{
                var savedLang = localStorage.getItem('selectedLanguage') || 'en';
                var bottomDropdown = document.getElementById('langSelectBottom'); 
                if (bottomDropdown) bottomDropdown.value = savedLang;
            }});

            var iframe = document.getElementById('unity-iframe');
            iframe.onload = function() {{
                try {{
                    var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    
                    var unityContainer = iframeDoc.getElementById('unity-container') || iframeDoc.querySelector('.unity-desktop');
                    var unityCanvas = iframeDoc.getElementById('unity-canvas') || iframeDoc.querySelector('canvas');
                    var unityFooter = iframeDoc.getElementById('unity-footer') || iframeDoc.querySelector('.unity-footer');

                    if (unityContainer) {{
                        unityContainer.style.width = '100%';
                        unityContainer.style.height = '100%';
                        unityContainer.style.position = 'absolute';
                        unityContainer.style.overflow = 'hidden';
                    }}
                    
                    if (unityCanvas) {{
                        unityCanvas.style.width = '100%';
                        unityCanvas.style.height = 'calc(100% - 40px)';
                    }}
                    
                    if (unityFooter) {{
                        unityFooter.style.width = '100%';
                        unityFooter.style.height = '40px';
                        unityFooter.style.position = 'absolute';
                        unityFooter.style.bottom = '0';
                        unityFooter.style.left = '0';
                    }}
                }} catch (e) {{
                    console.log("Skalierungs-Script blockiert (Cross-Origin).");
                }}
            }};
        </script>
    </body>
    </html>'''

@app.route('/static/Click a Cube Web/<path:filename>')
def serve_unity_files(filename):
    directory = os.path.join(app.root_path, 'static', 'Click a Cube Web')
    mimetype = None
    if filename.endswith('.wasm'): mimetype = 'application/wasm'
    elif filename.endswith('.data'): mimetype = 'application/octet-stream'
    elif filename.endswith('.js'): mimetype = 'application/javascript'
    return send_from_directory(directory, filename, mimetype=mimetype)


# --- DOWNLOAD SEKTOR ROUTEN ---

# FIX: Jetzt nur noch ein einziger Button für Windows PC auf Deutsch & Englisch
@app.route('/download-launcher-page')
def download_launcher_page():
    return f'''<!DOCTYPE html>
    <html>
    <head><title>Downloads - Cyhordream Studios</title>{FINAL_CYBER_DESIGN}</head>
    <body>
    {generiere_navigation()}
    <div class="main-content">
        <div class="form-container" style="max-width: 650px; margin-top: 10px;">
            <h2 style="color: #3498db;">Cyhordream Sektor 🚀</h2>
            <p style="color: #bdc3c7; font-size: 15px; line-height: 1.6;">
                <span class="lang-en">Download the official desktop launcher for Windows PC.</span>
                <span class="lang-de">Lade den offiziellen Desktop-Launcher für Windows PCs herunter.</span>
            </p>
            <br>
            <div style="margin-top: 10px;">
                <a href="/download-launcher-file" class="btn-capsule-blue" style="text-decoration:none; display:inline-block; margin-bottom: 10px; width:100%; box-sizing:border-box;">
                    <span class="lang-en">Download Launcher (PC version only)</span>
                    <span class="lang-de">Lade den Launcher herunter (nur PC Version)</span>
                </a>
            </div>
            <br><br>
        </div>
    </div>
    </body>
    </html>'''

@app.route('/download-launcher-file')
@app.route('/download-launcher-file')
def download_launcher_file():
    # Hier muss jetzt exakt euer neuer Name stehen:
    return send_from_directory(DOWNLOAD_FOLDER, "CyhordreamLauncherSetup.exe", as_attachment=True)

@app.route('/download-apk-file')
def download_apk_file():
    return send_from_directory(DOWNLOAD_FOLDER, "ClickACube.apk", as_attachment=True)


# --- COMMUNITY API (KOMMENTARE & LEADERBOARD) ---

@app.route('/api/send_comment', methods=['POST'])
def receive_comment():
    data = request.json
    username = data.get('username', 'Anonym')
    rating = data.get('rating', 0)
    comment = data.get('comment', '')

    studio_mail = "cyhordream.community@gmail.com"
    gmail_app_password = "slfvxesasnpvvbor" 

    subject = f"Neues Feedback von {username}"
    body = f"Absender/Spieler: {username}\nBewertung: {rating}/5 Sterne\n\nKommentar/Nachricht:\n{comment}"
    
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = studio_mail
    msg['To'] = studio_mail

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(studio_mail, gmail_app_password)
            server.sendmail(studio_mail, studio_mail, msg.as_string())
        return jsonify({"status": "success", "message": "E-Mail erfolgreich gesendet."}), 200
    except Exception as e:
        print(f"Fehler beim Mail-Versand: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/leaderboard/post', methods=['POST'])
def tunnel_leaderboard_post():
    try:
        unity_data = request.get_json(force=True)
        response = requests.post(GOOGLE_SCRIPT_URL, json=unity_data, headers={'Content-Type': 'application/json'})
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/leaderboard/get', methods=['GET'])
def tunnel_leaderboard_get():
    try:
        response = requests.get(GOOGLE_SCRIPT_URL)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/version')
def api_version():
    return WEBSITE_VERSION


# --- LOGIN / REGISTRIERUNG / DASHBOARD SYSTEM ---

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        form_type = request.form.get('form_type', 'login')

        if form_type == 'register':
            email = request.form.get('email', '').strip()
            code = str(random.randint(100000, 999999))
            VERIFICATION_CODES[username] = code
            USERS_DB[username] = {"password": password, "email": email, "verified": False}
            send_verification_email(email, code, username)
            session['verifying_user'] = username
            return redirect(url_for('verify_account'))

        elif form_type == 'login':
            if username in USERS_DB and USERS_DB[username]['password'] == password:
                if not USERS_DB[username].get('verified', False):
                    error = "Bitte zuerst E-Mail verifizieren!"
                else:
                    login_user(User(username, USERS_DB[username]['email']))
                    return redirect(url_for('dashboard_route'))
            else:
                error = "Login fehlgeschlagen: Falscher User oder Passwort."

    content = '''
    <div class="form-container" style="max-width: 480px;">
        <h2 class="auth-title">Login</h2>
        <p class="auth-subtitle">Melde dich mit deinem Cyhordream Konto an.</p>
        <form method="POST" class="auth-form">
            <input type="hidden" name="form_type" value="login">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit" class="btn-cyber btn-cyber-primary">Login</button>
        </form>

        <hr class="auth-divider">

        <h2 class="auth-title">Register</h2>
        <p class="auth-subtitle">Erstelle dein Konto und bestätige es danach per E-Mail.</p>
        <form method="POST" class="auth-form">
            <input type="hidden" name="form_type" value="register">
            <input type="text" name="username" placeholder="Username" required>
            <input type="email" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit" class="btn-cyber btn-cyber-success">Register</button>
        </form>
    </div>
    '''
    return get_html_page("Login", content, error)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"status": "error", "message": "Daten unvollständig"}), 400

    username = data.get('username')
    password = data.get('password')

    if username in USERS_DB and USERS_DB[username].get('password') == password:
        if not USERS_DB[username].get('verified', False):
            return jsonify({"status": "error", "message": "Nicht verifiziert"}), 401
        return jsonify({"status": "success", "token": USERS_DB[username].get('token', 'KEIN_TOKEN')})
    
    return jsonify({"status": "error", "message": "Falsche Daten"}), 401

@app.route('/dashboard')
@login_required
def dashboard_route():
    return f'''<!DOCTYPE html>
    <html>
    <head><title>Dashboard</title>{FINAL_CYBER_DESIGN}</head>
    <body>
    {generiere_navigation()}
    <div class="main-content">
        <div class="form-container">
            <h2>Willkommen, {current_user.id}</h2>
            <p>E-Mail: {current_user.email}</p>
            
            <div style="background:#2c3e50; padding:15px; border-radius:8px; margin:20px 0;">
                <p><strong>Website-Version:</strong></p>
                <code style="font-size:20px; color:#f1c40f;">{WEBSITE_VERSION}</code>
                <p style="font-size:12px;">Der Launcher verbindet sich automatisch mit deinem Konto. Du musst keinen Token kopieren.</p>
            </div>
            
            <a href="/logout" class="btn-capsule-blue" style="background-color:#e74c3c;">Ausloggen</a>
        </div>
    </div>
    </body>
    </html>'''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/verify-account', methods=['GET', 'POST'])
def verify_account():
    username = session.get('verifying_user')
    if not username: return redirect(url_for('login_route'))
    error = None

    if request.method == 'POST':
        code = request.form.get('code')
        if VERIFICATION_CODES.get(username) == code:
            USERS_DB[username]['verified'] = True
            USERS_DB[username]['token'] = generate_account_token()
            del VERIFICATION_CODES[username]
            session.pop('verifying_user', None)
            login_user(User(username, USERS_DB[username]['email']))
            return redirect(url_for('dashboard_route'))
        else:
            error = "Falscher Code!"
            
    content = f'''
    <div class="form-container" style="max-width: 440px;">
        <h2 class="auth-title">Verifizierung</h2>
        <p class="verify-hint">
            Hallo {username}, wir haben deine E-Mail erreicht und dir einen Bestätigungscode gesendet.
            Bitte gib den Code hier ein.
        </p>
        <form method="POST" class="auth-form">
            <input class="code-input" type="text" name="code" placeholder="Code eingeben" inputmode="numeric" maxlength="6" required>
            <button type="submit" class="btn-cyber btn-cyber-verify">Bestätigen</button>
        </form>
    </div>
    '''
    return get_html_page("Verifizieren", content, error)

def get_html_page(title, content, error=""):
    error_html = f'<p class="error-message">{error}</p>' if error else ""
    return f'''<!DOCTYPE html>
    <html>
    <head><title>{title}</title>{FINAL_CYBER_DESIGN}</head>
    <body>
    {generiere_navigation()}
    <div class="main-content">
        {error_html}
        {content}
    </div>
    </body>
    </html>'''


# --- APP RUNNER ---

if __name__ == '__main__':
    app.run(debug=True, port=5000)
handler = app