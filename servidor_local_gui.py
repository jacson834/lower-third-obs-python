import os
import socket
import threading
import json
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
                if parsed.path != "/__lt/message":
                    return super().do_GET()

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
                if parsed.path != "/__lt/message":
                    return self._send_json(404, {"ok": False, "error": "not_found"})

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

        hint = ttk.Label(
            frame,
            text="Dica: deixe esta janela aberta. Se o celular nao abrir, libere a porta 5500 no firewall (rede privada).",
            font=("Segoe UI", 9),
        )
        hint.pack(anchor="w", pady=(6, 0))

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

    def _on_close(self):
        self.server.stop()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
