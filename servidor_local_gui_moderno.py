import sys
import socket
import time
from typing import Optional

from servidor_local_gui import HOST, PORT, BASE_DIR, LocalServer, get_lan_ip

try:
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtGui import QFont, QGuiApplication
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except Exception:
    print("PySide6 nao encontrado. Instale com: pip install PySide6")
    sys.exit(1)

try:
    import qrcode
    from PIL import ImageQt
    QR_AVAILABLE = True
except Exception:
    QR_AVAILABLE = False


class UrlRow(QWidget):
    def __init__(self, label: str, value: str, copy_callback):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = QLabel(label)
        self.label.setMinimumWidth(220)
        self.input = QLineEdit(value)
        self.input.setReadOnly(True)
        self.btn = QPushButton("Copiar")
        self.btn.clicked.connect(lambda: copy_callback(value))
        self._copy_callback = copy_callback

        layout.addWidget(self.label)
        layout.addWidget(self.input, 1)
        layout.addWidget(self.btn)

    def set_value(self, value: str):
        self.input.setText(value)
        try:
            self.btn.clicked.disconnect()
        except Exception:
            pass
        self.btn.clicked.connect(lambda: self._copy_callback(value))


class ModernServerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OBS Lower Thirds - GUI Moderna")
        self.resize(980, 560)

        self.lan_ip = get_lan_ip()
        self.local_base = f"http://127.0.0.1:{PORT}"
        self.lan_base = f"http://{self.lan_ip}:{PORT}"

        self.panel_local = f"{self.local_base}/obs_control_panel.html"
        self.source_local = f"{self.local_base}/obs_lower_thirds_source.html"
        self.panel_lan = f"{self.lan_base}/obs_control_panel.html"
        self.panel_lan_url_for_qr = self.panel_lan

        self.server = LocalServer(HOST, PORT, BASE_DIR)

        self.status_label: Optional[QLabel] = None
        self.remote_label: Optional[QLabel] = None
        self.password_input: Optional[QLineEdit] = None
        self.ttl_input: Optional[QLineEdit] = None
        self.max_attempts_input: Optional[QLineEdit] = None
        self.lock_input: Optional[QLineEdit] = None
        self.qr_label: Optional[QLabel] = None
        self.start_btn: Optional[QPushButton] = None
        self.stop_btn: Optional[QPushButton] = None

        self._build_ui()
        self._apply_theme()
        self._start_server()

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(14)

        title = QLabel("OBS Lower Thirds - Servidor Local")
        title.setObjectName("title")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        outer.addWidget(title)

        subtitle = QLabel("Use URLs locais no OBS e URL de rede no celular (mesmo Wi-Fi).")
        subtitle.setObjectName("subtitle")
        outer.addWidget(subtitle)

        card_obs = self._make_card("OBS (neste PC)")
        card_obs.layout().addWidget(UrlRow("Painel (Dock):", self.panel_local, self._copy_text))
        card_obs.layout().addWidget(UrlRow("Source (Browser Source):", self.source_local, self._copy_text))
        outer.addWidget(card_obs)

        card_remote = self._make_card("Celular / outro dispositivo (mesma rede)")
        self.remote_panel_row = UrlRow("Painel remoto:", self.panel_lan_url_for_qr, self._copy_text)
        card_remote.layout().addWidget(self.remote_panel_row)

        pwd_row = QHBoxLayout()
        pwd_label = QLabel("Senha remota:")
        pwd_label.setMinimumWidth(220)
        self.password_input = QLineEdit("1234")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.show_password_btn = QPushButton("Ver senha")
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.toggled.connect(self._toggle_password_visibility)
        apply_pwd_btn = QPushButton("Aplicar senha")
        apply_pwd_btn.clicked.connect(self._apply_remote_password)
        pwd_row.addWidget(pwd_label)
        pwd_row.addWidget(self.password_input, 1)
        pwd_row.addWidget(self.show_password_btn)
        pwd_row.addWidget(apply_pwd_btn)
        card_remote.layout().addLayout(pwd_row)

        sec_row = QHBoxLayout()
        sec_row.addWidget(QLabel("Expiracao (min):"))
        self.ttl_input = QLineEdit("720")
        self.ttl_input.setMaximumWidth(80)
        sec_row.addWidget(self.ttl_input)
        sec_row.addWidget(QLabel("Tentativas max:"))
        self.max_attempts_input = QLineEdit("5")
        self.max_attempts_input.setMaximumWidth(60)
        sec_row.addWidget(self.max_attempts_input)
        sec_row.addWidget(QLabel("Bloqueio (s):"))
        self.lock_input = QLineEdit("120")
        self.lock_input.setMaximumWidth(70)
        sec_row.addWidget(self.lock_input)
        apply_sec_btn = QPushButton("Aplicar seguranca")
        apply_sec_btn.clicked.connect(self._apply_security_settings)
        sec_row.addWidget(apply_sec_btn)
        sec_row.addStretch(1)
        card_remote.layout().addLayout(sec_row)

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        card_remote.layout().addWidget(self.qr_label)
        outer.addWidget(card_remote)

        controls = QHBoxLayout()
        self.start_btn = QPushButton("Iniciar Servidor")
        self.stop_btn = QPushButton("Parar Servidor")
        copy_mobile_btn = QPushButton("Copiar URL Celular")
        copy_panel_btn = QPushButton("Copiar URL Painel OBS")
        copy_source_btn = QPushButton("Copiar URL Source OBS")

        self.start_btn.clicked.connect(self._start_server)
        self.stop_btn.clicked.connect(self._stop_server)
        copy_mobile_btn.clicked.connect(lambda: self._copy_text(self.panel_lan_url_for_qr))
        copy_panel_btn.clicked.connect(lambda: self._copy_text(self.panel_local))
        copy_source_btn.clicked.connect(lambda: self._copy_text(self.source_local))

        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        controls.addStretch(1)
        controls.addWidget(copy_panel_btn)
        controls.addWidget(copy_source_btn)
        controls.addWidget(copy_mobile_btn)
        outer.addLayout(controls)

        self.status_label = QLabel("Status: iniciando...")
        self.status_label.setObjectName("status")
        self.remote_label = QLabel("Cliente remoto: aguardando conexao")
        self.remote_label.setObjectName("remote")

        outer.addWidget(self.status_label)
        outer.addWidget(self.remote_label)

        hint = QLabel("Dica: se o celular nao abrir, libere a porta 5500 no firewall para rede privada.")
        hint.setObjectName("hint")
        outer.addWidget(hint)

    def _make_card(self, title_text: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        title = QLabel(title_text)
        title.setObjectName("cardTitle")
        layout.addWidget(title)
        return card

    def _apply_theme(self):
        self.setStyleSheet(
            """
            QWidget { background: #0b1820; color: #e8f6fb; font-family: Segoe UI; font-size: 13px; }
            QLabel#title { color: #7de3f2; }
            QLabel#subtitle { color: #9ec5d1; }
            QLabel#status { color: #8ef0c6; font-weight: 700; }
            QLabel#remote { color: #f7d27c; }
            QLabel#hint { color: #98aeb8; font-size: 12px; }
            QFrame#card { border: 1px solid #28404b; border-radius: 12px; background: #10232d; }
            QLabel#cardTitle { font-weight: 700; color: #b7dbe7; }
            QLineEdit { border: 1px solid #35596a; border-radius: 8px; padding: 8px; background: #0b1d26; color: #e8f6fb; }
            QPushButton {
                border: 1px solid #2b6f83; border-radius: 8px; padding: 8px 12px; background: #12556a; color: white; font-weight: 600;
            }
            QPushButton:hover { background: #18708a; }
            QPushButton:disabled { background: #27404b; color: #84a2ad; border-color: #304a56; }
            """
        )

    def _update_qr(self):
        if not self.qr_label:
            return
        if not QR_AVAILABLE:
            self.qr_label.setText("QR indisponivel. Instale: pip install qrcode pillow")
            return
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(self.panel_lan_url_for_qr)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        qt_img = ImageQt.ImageQt(img.convert("RGB"))
        from PySide6.QtGui import QPixmap
        pix = QPixmap.fromImage(qt_img)
        self.qr_label.setPixmap(pix)

    def _apply_remote_password(self):
        if not self.password_input:
            return
        pwd = self.password_input.text().strip()
        self.server.set_panel_password(pwd)
        self.panel_lan_url_for_qr = self.panel_lan
        self.remote_panel_row.set_value(self.panel_lan_url_for_qr)
        self._update_qr()
        if self.status_label:
            if pwd:
                self.status_label.setText("Status: senha remota aplicada. QR atualizado.")
            else:
                self.status_label.setText("Status: senha remota desativada. QR atualizado.")

    def _apply_security_settings(self):
        try:
            ttl_minutes = int((self.ttl_input.text() if self.ttl_input else "720").strip() or "720")
            max_attempts = int((self.max_attempts_input.text() if self.max_attempts_input else "5").strip() or "5")
            lock_seconds = int((self.lock_input.text() if self.lock_input else "120").strip() or "120")
        except ValueError:
            QMessageBox.warning(self, "Valores invalidos", "Informe apenas numeros inteiros nos campos de seguranca.")
            return

        self.server.set_security_config(
            token_ttl_seconds=ttl_minutes * 60,
            max_auth_attempts=max_attempts,
            auth_lock_seconds=lock_seconds,
        )
        if self.status_label:
            self.status_label.setText("Status: configuracoes de seguranca aplicadas.")

    def _toggle_password_visibility(self, checked: bool):
        if not self.password_input:
            return
        if checked:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_password_btn.setText("Ocultar senha")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_password_btn.setText("Ver senha")

    def _copy_text(self, text: str):
        QGuiApplication.clipboard().setText(text)
        if self.status_label:
            self.status_label.setText("Status: URL copiada para a area de transferencia.")

    def _can_bind_port(self) -> bool:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            test_sock.bind((HOST, PORT))
            return True
        except OSError:
            return False
        finally:
            test_sock.close()

    def _start_server(self):
        if self.server.is_running():
            self._refresh_buttons()
            self._update_status_text()
            return

        if not self._can_bind_port():
            if self.status_label:
                self.status_label.setText(f"Status: porta {PORT} ja esta em uso.")
            QMessageBox.warning(self, "Porta em uso", f"A porta {PORT} ja esta ocupada.")
            self._refresh_buttons()
            return

        try:
            self.server.start()
            self._apply_security_settings()
            self._apply_remote_password()
            self._update_status_text()
        except Exception as exc:
            if self.status_label:
                self.status_label.setText("Status: falha ao iniciar servidor.")
            QMessageBox.critical(self, "Erro", f"Nao foi possivel iniciar:\n{exc}")
        finally:
            self._refresh_buttons()

    def _stop_server(self):
        try:
            self.server.stop()
            if self.status_label:
                self.status_label.setText("Status: servidor parado.")
        finally:
            self._refresh_buttons()

    def _update_status_text(self):
        if not self.status_label:
            return
        self.status_label.setText(f"Status: ativo em {self.local_base} | Rede: {self.lan_base}")

    def _tick(self):
        self._refresh_buttons()
        if not self.server.is_running():
            if self.remote_label:
                self.remote_label.setText("Cliente remoto: servidor parado")
            return

        self._update_status_text()
        last_seen, remote_ip = self.server.get_remote_presence()
        if last_seen <= 0:
            msg = "Cliente remoto: aguardando conexao"
        else:
            elapsed = time.time() - last_seen
            if elapsed <= 12:
                msg = f"Cliente remoto conectado: {remote_ip}"
            else:
                msg = f"Cliente remoto inativo ({remote_ip})"

        if self.remote_label:
            self.remote_label.setText(msg)

        self._update_qr()

    def _refresh_buttons(self):
        running = self.server.is_running()
        if self.start_btn:
            self.start_btn.setDisabled(running)
        if self.stop_btn:
            self.stop_btn.setDisabled(not running)

    def closeEvent(self, event):
        self.server.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernServerWindow()
    window.show()
    sys.exit(app.exec())
