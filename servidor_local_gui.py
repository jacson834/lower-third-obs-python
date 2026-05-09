import os
import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


HOST = "127.0.0.1"
PORT = 5500
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = f"http://{HOST}:{PORT}"
PANEL_URL = f"{BASE_URL}/obs_control_panel.html"
SOURCE_URL = f"{BASE_URL}/obs_lower_thirds_source.html"


class LocalServer:
    def __init__(self, host, port, directory):
        self.host = host
        self.port = port
        self.directory = directory
        self.httpd = None
        self.thread = None

    def start(self):
        if self.is_running():
            return

        handler = lambda *args, **kwargs: SimpleHTTPRequestHandler(*args, directory=self.directory, **kwargs)
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
        self.geometry("760x300")
        self.resizable(False, False)

        self.server = LocalServer(HOST, PORT, BASE_DIR)
        self.status_var = tk.StringVar(value="Iniciando servidor...")

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
            text="Copie as URLs abaixo e cole no OBS (Dock e Browser Source).",
            font=("Segoe UI", 10),
        )
        info.pack(anchor="w", pady=(0, 12))

        self._url_row(frame, "URL do Painel (Dock):", PANEL_URL)
        self._url_row(frame, "URL da Source (Browser Source):", SOURCE_URL)

        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=(12, 8))

        self.start_btn = ttk.Button(controls, text="Iniciar Servidor", command=self._start_server)
        self.start_btn.pack(side="left")

        self.stop_btn = ttk.Button(controls, text="Parar Servidor", command=self._stop_server)
        self.stop_btn.pack(side="left", padx=8)

        ttk.Button(controls, text="Copiar URL Painel", command=lambda: self._copy(PANEL_URL)).pack(side="right", padx=(8, 0))
        ttk.Button(controls, text="Copiar URL Source", command=lambda: self._copy(SOURCE_URL)).pack(side="right")

        status = ttk.Label(frame, textvariable=self.status_var, font=("Segoe UI", 10, "bold"))
        status.pack(anchor="w", pady=(4, 0))

        hint = ttk.Label(
            frame,
            text="Dica: deixe esta janela aberta enquanto o OBS estiver em uso.",
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
            self.status_var.set(f"Servidor ativo em {BASE_URL}")
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
            self.status_var.set(f"Servidor ativo em {BASE_URL}")
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
