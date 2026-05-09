import os
import socket
import threading
import json
import secrets
import time
import tkinter as tk
from tkinter import ttk, messagebox
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

try:
    import qrcode
    from PIL import ImageTk
    QR_AVAILABLE = True
except Exception:
    QR_AVAILABLE = False


HOST = "0.0.0.0"
PORT = 5500
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_TTL_SECONDS = 12 * 60 * 60
MAX_AUTH_ATTEMPTS = 5
AUTH_LOCK_SECONDS = 120


def get_lan_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


class LocalServer:
    def __init__(self, host, port, directory):
        self.host = host
        self.port = port
        self.directory = directory
        self.httpd = None
        self.thread = None
        self.message_lock = threading.Lock()
        self.message_seq = 0
        self.last_message = None
        self.last_remote_seen_at = 0.0
        self.last_remote_ip = ""
        self.panel_password = ""
        self.panel_access_token = ""
        self.panel_access_token_expires_at = 0.0
        self.auth_failures_by_ip = {}
        self.token_ttl_seconds = TOKEN_TTL_SECONDS
        self.max_auth_attempts = MAX_AUTH_ATTEMPTS
        self.auth_lock_seconds = AUTH_LOCK_SECONDS

    def set_panel_password(self, password):
        with self.message_lock:
            self.panel_password = (password or "").strip()

    def set_security_config(self, token_ttl_seconds=None, max_auth_attempts=None, auth_lock_seconds=None):
        with self.message_lock:
            if token_ttl_seconds is not None:
                self.token_ttl_seconds = max(60, int(token_ttl_seconds))
            if max_auth_attempts is not None:
                self.max_auth_attempts = max(1, int(max_auth_attempts))
            if auth_lock_seconds is not None:
                self.auth_lock_seconds = max(10, int(auth_lock_seconds))

    def issue_panel_token(self):
        token = secrets.token_urlsafe(24)
        with self.message_lock:
            self.panel_access_token = token
            self.panel_access_token_expires_at = time.time() + self.token_ttl_seconds
        return token

    def _prune_auth_failures(self):
        now = time.time()
        stale_ips = [ip for ip, info in self.auth_failures_by_ip.items() if now - info.get("last", 0) > (self.auth_lock_seconds * 3)]
        for ip in stale_ips:
            self.auth_failures_by_ip.pop(ip, None)

    def _is_ip_locked_for_auth(self, client_ip):
        self._prune_auth_failures()
        info = self.auth_failures_by_ip.get(client_ip)
        if not info:
            return False, 0
        now = time.time()
        lock_until = info.get("lock_until", 0)
        if lock_until > now:
            return True, int(lock_until - now)
        return False, 0

    def _register_auth_failure(self, client_ip):
        now = time.time()
        info = self.auth_failures_by_ip.get(client_ip, {"count": 0, "last": 0, "lock_until": 0})
        if now - info.get("last", 0) > self.auth_lock_seconds:
            info["count"] = 0
        info["count"] = int(info.get("count", 0)) + 1
        info["last"] = now
        if info["count"] >= self.max_auth_attempts:
            info["count"] = 0
            info["lock_until"] = now + self.auth_lock_seconds
        self.auth_failures_by_ip[client_ip] = info

    def _register_auth_success(self, client_ip):
        self.auth_failures_by_ip.pop(client_ip, None)

    def _is_local_client(self, client_ip):
        return client_ip in ("127.0.0.1", "::1", "localhost")

    def _is_panel_authorized(self, client_ip, query_string):
        if self._is_local_client(client_ip):
            return True
        with self.message_lock:
            password_set = bool(self.panel_password)
            expected_token = self.panel_access_token
            token_expires_at = self.panel_access_token_expires_at
        if not password_set:
            return True
        if not expected_token:
            return False
        if token_expires_at <= time.time():
            return False
        qs = parse_qs(query_string or "")
        token = qs.get("token", [""])[0]
        return bool(expected_token and token and secrets.compare_digest(token, expected_token))

    def _register_remote_client(self, client_ip):
        if client_ip in ("127.0.0.1", "::1", "localhost"):
            return
        with self.message_lock:
            self.last_remote_seen_at = time.time()
            self.last_remote_ip = client_ip

    def get_remote_presence(self):
        with self.message_lock:
            return self.last_remote_seen_at, self.last_remote_ip

    def _create_handler(self):
        server_ref = self

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=server_ref.directory, **kwargs)

            def _send_json(self, status_code, payload):
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)

            def _send_html(self, status_code, html_text):
                raw = html_text.encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)

            def _render_login_page(self):
                return """<!doctype html>
<html lang=\"pt-BR\"><head><meta charset=\"utf-8\"/><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/>
<title>Acesso ao Painel</title>
<style>
*{box-sizing:border-box}
body{margin:0;padding:14px;background:#0b1820;color:#e8f6fb;font-family:Segoe UI,Tahoma,sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center}
.card{width:100%;max-width:420px;background:#10232d;border:1px solid #28404b;border-radius:14px;padding:18px;box-shadow:0 12px 24px rgba(0,0,0,.35);overflow:hidden}
h1{font-size:20px;margin:0 0 8px;color:#7de3f2}.muted{color:#9ec5d1;font-size:13px;margin-bottom:12px}
input{display:block;width:100%;max-width:100%;padding:10px;border-radius:8px;border:1px solid #35596a;background:#0b1d26;color:#e8f6fb;font-size:16px;outline:none}
button{display:block;margin-top:10px;width:100%;max-width:100%;padding:10px;border:none;border-radius:8px;background:#12556a;color:#fff;font-weight:700;cursor:pointer}
.err{color:#fca5a5;font-size:13px;min-height:18px;margin-top:8px}
</style></head>
<body><div class=\"card\"><h1>Painel protegido</h1><div class=\"muted\">Digite a senha para acessar o controle remoto.</div>
<input id=\"pwd\" type=\"password\" placeholder=\"Senha\" autofocus/><button id=\"go\">Entrar</button><div class=\"err\" id=\"err\"></div></div>
<script>
const btn=document.getElementById('go');const pwd=document.getElementById('pwd');const err=document.getElementById('err');
async function login(){err.textContent='';const password=pwd.value||'';if(!password){err.textContent='Informe a senha.';return;}
try{const res=await fetch('/__lt/auth',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password})});
const data=await res.json();
if(!res.ok||!data.ok){
  if(res.status===429&&data&&data.retry_after){err.textContent='Muitas tentativas. Aguarde '+data.retry_after+'s.';return;}
  err.textContent='Senha incorreta.';return;
}
window.location.href='/obs_control_panel.html?token='+encodeURIComponent(data.token);
}catch(e){err.textContent='Falha de rede. Tente novamente.';}}
btn.addEventListener('click',login);pwd.addEventListener('keydown',e=>{if(e.key==='Enter')login();});
</script></body></html>"""

            def do_OPTIONS(self):
                if self.path.startswith("/__lt/message"):
                    self.send_response(204)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                    self.send_header("Access-Control-Allow-Headers", "Content-Type")
                    self.end_headers()
                    return
                super().do_OPTIONS()

            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/obs_control_panel.html":
                    if not server_ref._is_panel_authorized(self.client_address[0], parsed.query):
                        return self._send_html(200, self._render_login_page())
                if parsed.path != "/__lt/message":
                    return super().do_GET()

                server_ref._register_remote_client(self.client_address[0])

                qs = parse_qs(parsed.query)
                since = 0
                try:
                    since = int(qs.get("since", ["0"])[0])
                except (ValueError, TypeError):
                    since = 0

                with server_ref.message_lock:
                    seq = server_ref.message_seq
                    msg = server_ref.last_message

                if msg is not None and seq > since:
                    return self._send_json(200, {"seq": seq, "message": msg})

                return self._send_json(200, {"seq": seq, "message": None})

            def do_POST(self):
                parsed = urlparse(self.path)
                if parsed.path == "/__lt/auth":
                    content_length = int(self.headers.get("Content-Length", "0"))
                    if content_length <= 0:
                        return self._send_json(400, {"ok": False, "error": "empty_body"})
                    raw = self.rfile.read(content_length)
                    try:
                        payload = json.loads(raw.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        return self._send_json(400, {"ok": False, "error": "invalid_json"})
                    password = str(payload.get("password", ""))
                    with server_ref.message_lock:
                        locked, retry_after = server_ref._is_ip_locked_for_auth(self.client_address[0])
                    if locked:
                        return self._send_json(429, {"ok": False, "error": "too_many_attempts", "retry_after": retry_after})

                    with server_ref.message_lock:
                        expected = server_ref.panel_password
                    if expected and secrets.compare_digest(password, expected):
                        with server_ref.message_lock:
                            server_ref._register_auth_success(self.client_address[0])
                        token = server_ref.issue_panel_token()
                        return self._send_json(200, {"ok": True, "token": token})
                    with server_ref.message_lock:
                        server_ref._register_auth_failure(self.client_address[0])
                    return self._send_json(401, {"ok": False, "error": "invalid_password"})

                if parsed.path != "/__lt/message":
                    return self._send_json(404, {"ok": False, "error": "not_found"})

                server_ref._register_remote_client(self.client_address[0])

                content_length = int(self.headers.get("Content-Length", "0"))
                if content_length <= 0:
                    return self._send_json(400, {"ok": False, "error": "empty_body"})

                raw = self.rfile.read(content_length)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return self._send_json(400, {"ok": False, "error": "invalid_json"})

                if not isinstance(payload, dict) or "action" not in payload:
                    return self._send_json(400, {"ok": False, "error": "invalid_payload"})

                with server_ref.message_lock:
                    server_ref.message_seq += 1
                    server_ref.last_message = payload
                    seq = server_ref.message_seq

                return self._send_json(200, {"ok": True, "seq": seq})

        return Handler

    def start(self):
        if self.is_running():
            return

        handler = self._create_handler()
        self.httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.httpd:
            return
        self.httpd.shutdown()
        self.httpd.server_close()
        self.httpd = None
        self.thread = None

    def is_running(self):
        return self.httpd is not None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Servidor Local - OBS Lower Thirds")
        self.geometry("920x560")
        self.minsize(860, 520)
        self.resizable(True, True)

        self.lan_ip = get_lan_ip()
        self.local_base_url = f"http://127.0.0.1:{PORT}"
        self.lan_base_url = f"http://{self.lan_ip}:{PORT}"
        self.panel_url_local = f"{self.local_base_url}/obs_control_panel.html"
        self.source_url_local = f"{self.local_base_url}/obs_lower_thirds_source.html"
        self.panel_url_lan = f"{self.lan_base_url}/obs_control_panel.html"
        self.source_url_lan = f"{self.lan_base_url}/obs_lower_thirds_source.html"

        self.server = LocalServer(HOST, PORT, BASE_DIR)
        self.status_var = tk.StringVar(value="Iniciando servidor...")
        self.remote_status_var = tk.StringVar(value="Cliente remoto: aguardando conexao")
        self.qr_image = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._auto_start)

    def _build_ui(self):
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        title = ttk.Label(frame, text="OBS Lower Thirds - Servidor Local", font=("Segoe UI", 14, "bold"))
        title.pack(anchor="w", pady=(0, 10))

        info = ttk.Label(
            frame,
            text="Use URLs locais no OBS e URL de rede no celular (mesmo Wi-Fi).",
            font=("Segoe UI", 10),
        )
        info.pack(anchor="w", pady=(0, 12))

        ttk.Label(frame, text="OBS (neste PC)", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        self._url_row(frame, "Painel (Dock):", self.panel_url_local)
        self._url_row(frame, "Source (Browser Source):", self.source_url_local)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(frame, text="Celular / outro dispositivo (mesma rede)", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        self._url_row(frame, "Painel remoto:", self.panel_url_lan)

        pwd_row = ttk.Frame(frame)
        pwd_row.pack(fill="x", pady=(6, 2))
        ttk.Label(pwd_row, text="Senha remota:", width=30).pack(side="left")
        self.password_var = tk.StringVar(value="1234")
        self.password_entry = ttk.Entry(pwd_row, textvariable=self.password_var, show="*")
        self.password_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.show_password_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            pwd_row,
            text="Ver senha",
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(pwd_row, text="Aplicar senha", command=self._apply_remote_password).pack(side="left")

        sec_row = ttk.Frame(frame)
        sec_row.pack(fill="x", pady=(4, 8))
        ttk.Label(sec_row, text="Expiracao (min):", width=30).pack(side="left")
        self.ttl_var = tk.StringVar(value="720")
        ttk.Entry(sec_row, textvariable=self.ttl_var, width=8).pack(side="left", padx=(0, 8))
        ttk.Label(sec_row, text="Tentativas max:").pack(side="left")
        self.max_attempts_var = tk.StringVar(value="5")
        ttk.Entry(sec_row, textvariable=self.max_attempts_var, width=6).pack(side="left", padx=(6, 8))
        ttk.Label(sec_row, text="Bloqueio (s):").pack(side="left")
        self.lock_var = tk.StringVar(value="120")
        ttk.Entry(sec_row, textvariable=self.lock_var, width=7).pack(side="left", padx=(6, 8))
        ttk.Button(sec_row, text="Aplicar seguranca", command=self._apply_security_settings).pack(side="left")

        qr_box = ttk.Frame(frame)
        qr_box.pack(fill="x", pady=(10, 4))

        ttk.Label(qr_box, text="QR Code (abrir painel no celular):", width=30).pack(side="left", anchor="n")

        self.qr_label = ttk.Label(qr_box)
        self.qr_label.pack(side="left", padx=(0, 10))

        if QR_AVAILABLE:
            self._render_qr(self.panel_url_lan)
        else:
            self.qr_label.configure(text="Instale: pip install qrcode pillow")

        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=(12, 8))

        self.start_btn = ttk.Button(controls, text="Iniciar Servidor", command=self._start_server)
        self.start_btn.pack(side="left")

        self.stop_btn = ttk.Button(controls, text="Parar Servidor", command=self._stop_server)
        self.stop_btn.pack(side="left", padx=8)

        ttk.Button(controls, text="Copiar URL Celular", command=lambda: self._copy(self.panel_url_lan)).pack(side="right", padx=(8, 0))
        ttk.Button(controls, text="Copiar URL Source OBS", command=lambda: self._copy(self.source_url_local)).pack(side="right", padx=(8, 0))
        ttk.Button(controls, text="Copiar URL Painel OBS", command=lambda: self._copy(self.panel_url_local)).pack(side="right")

        status = ttk.Label(frame, textvariable=self.status_var, font=("Segoe UI", 10, "bold"))
        status.pack(anchor="w", pady=(4, 0))

        remote_status = ttk.Label(frame, textvariable=self.remote_status_var, font=("Segoe UI", 9))
        remote_status.pack(anchor="w", pady=(2, 0))

        hint = ttk.Label(
            frame,
            text="Dica: deixe esta janela aberta. Se o celular nao abrir, libere a porta 5500 no firewall (rede privada).",
            font=("Segoe UI", 9),
        )
        hint.pack(anchor="w", pady=(6, 0))

        self.after(1000, self._refresh_remote_status)

    def _url_row(self, parent, label_text, url):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)

        ttk.Label(row, text=label_text, width=30).pack(side="left")

        entry = ttk.Entry(row)
        entry.insert(0, url)
        entry.configure(state="readonly")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ttk.Button(row, text="Copiar", command=lambda: self._copy(url)).pack(side="left")

    def _copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update_idletasks()
        self.status_var.set("URL copiada para a area de transferencia.")

    def _render_qr(self, text):
        if not QR_AVAILABLE:
            return
        qr = qrcode.QRCode(version=1, box_size=3, border=2)
        qr.add_data(text)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")
        self.qr_image = ImageTk.PhotoImage(image)
        self.qr_label.configure(image=self.qr_image, text="")

    def _apply_remote_password(self):
        password = self.password_var.get().strip()
        self.server.set_panel_password(password)
        if password:
            self.status_var.set("Senha remota aplicada. O celular precisara autenticar no painel.")
        else:
            self.status_var.set("Senha remota desativada. Acesso remoto sem senha.")

    def _apply_security_settings(self):
        try:
            ttl_minutes = int(self.ttl_var.get().strip() or "720")
            max_attempts = int(self.max_attempts_var.get().strip() or "5")
            lock_seconds = int(self.lock_var.get().strip() or "120")
        except ValueError:
            messagebox.showwarning("Valores invalidos", "Informe apenas numeros inteiros nos campos de seguranca.")
            return

        self.server.set_security_config(
            token_ttl_seconds=ttl_minutes * 60,
            max_auth_attempts=max_attempts,
            auth_lock_seconds=lock_seconds,
        )
        self.status_var.set("Configuracoes de seguranca aplicadas.")

    def _toggle_password_visibility(self):
        if self.show_password_var.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="*")

    def _can_bind_port(self):
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            test_sock.bind((HOST, PORT))
            return True
        except OSError:
            return False
        finally:
            test_sock.close()

    def _auto_start(self):
        self._start_server()

    def _start_server(self):
        if self.server.is_running():
            self.status_var.set(f"Servidor ativo em {self.local_base_url} | Rede: {self.lan_base_url}")
            self._refresh_buttons()
            return

        if not self._can_bind_port():
            self.status_var.set(f"Porta {PORT} ja esta em uso.")
            messagebox.showwarning(
                "Porta em uso",
                f"A porta {PORT} ja esta ocupada.\n"
                "Feche o outro servidor/processo ou use a mesma instancia ja aberta.",
            )
            self._refresh_buttons()
            return

        try:
            self.server.start()
            self._apply_security_settings()
            self._apply_remote_password()
            self.status_var.set(f"Servidor ativo em {self.local_base_url} | Rede: {self.lan_base_url}")
        except Exception as exc:
            self.status_var.set("Falha ao iniciar o servidor.")
            messagebox.showerror("Erro", f"Nao foi possivel iniciar o servidor:\n{exc}")
        finally:
            self._refresh_buttons()

    def _stop_server(self):
        try:
            self.server.stop()
            self.status_var.set("Servidor parado.")
        except Exception as exc:
            messagebox.showerror("Erro", f"Nao foi possivel parar o servidor:\n{exc}")
        finally:
            self._refresh_buttons()

    def _refresh_buttons(self):
        running = self.server.is_running()
        self.start_btn.configure(state="disabled" if running else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")

    def _refresh_remote_status(self):
        if not self.server.is_running():
            self.remote_status_var.set("Cliente remoto: servidor parado")
            self.after(1000, self._refresh_remote_status)
            return

        last_seen, remote_ip = self.server.get_remote_presence()
        if last_seen <= 0:
            self.remote_status_var.set("Cliente remoto: aguardando conexao")
        else:
            elapsed = time.time() - last_seen
            if elapsed <= 12:
                self.remote_status_var.set(f"Cliente remoto conectado: {remote_ip}")
            else:
                self.remote_status_var.set(f"Cliente remoto inativo ({remote_ip})")

        self.after(1000, self._refresh_remote_status)

    def _on_close(self):
        self.server.stop()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
