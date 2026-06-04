import tkinter as tk
from tkinter import messagebox, ttk
import threading
import subprocess
import serial
import serial.tools.list_ports
import cv2
import re
import os
import time
import urllib.request  
from PIL import Image, ImageTk

class MouthTrackerLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("MouthTracker v1.0 - Inicializador Oficial")
        self.root.geometry("500x550")
        self.root.configure(bg="#121214") # Fundo escuro MouthTracker

        # Título principal
        tk.Label(root, text="MOUTHTRACKER CONTROL PANEL", font=('Segoe UI', 16, 'bold'), bg="#121214", fg="#00b37e").pack(pady=15)

        # Seleção de Porta COM (Mudado para tk.Frame e OptionMenu nativo para EVITAR CRASH de tema)
        frame_com = tk.Frame(root, bg="#121214")
        frame_com.pack(pady=5, fill='x', padx=20)
        tk.Label(frame_com, text="Conectar via Porta USB (COM):", bg="#121214", fg="#e1e1e6", font=('Segoe UI', 10)).pack(side='left', padx=5)
        
        self.portas_disponiveis = self.listar_portas()
        if not self.portas_disponiveis:
            self.portas_disponiveis = ["Nenhuma porta encontrada"]
            
        self.porta_selecionada = tk.StringVar(root)
        self.porta_selecionada.set(self.portas_disponiveis[0])
        
        self.combo_ports = tk.OptionMenu(frame_com, self.porta_selecionada, *self.portas_disponiveis)
        self.combo_ports.config(bg="#202024", fg="#e1e1e6", highlightthickness=0, relief="flat", font=('Segoe UI', 10))
        self.combo_ports["menu"].config(bg="#202024", fg="#e1e1e6")
        self.combo_ports.pack(side='right', expand=True, fill='x', padx=5)

        # Campos de Wi-Fi (Usando componentes nativos estáveis)
        frame_wifi = tk.Frame(root, bg="#121214")
        frame_wifi.pack(pady=10, fill='x', padx=20)
        
        tk.Label(frame_wifi, text="Rede Wi-Fi (SSID):", bg="#121214", fg="#e1e1e6", font=('Segoe UI', 10)).grid(row=0, column=0, sticky='w', pady=5)
        self.entry_ssid = tk.Entry(frame_wifi, bg="#202024", fg="#e1e1e6", insertbackground="white", relief="flat", font=('Segoe UI', 10))
        self.entry_ssid.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        
        tk.Label(frame_wifi, text="Senha da Rede:", bg="#121214", fg="#e1e1e6", font=('Segoe UI', 10)).grid(row=1, column=0, sticky='w', pady=5)
        self.entry_pass = tk.Entry(frame_wifi, show="*", bg="#202024", fg="#e1e1e6", insertbackground="white", relief="flat", font=('Segoe UI', 10))
        self.entry_pass.grid(row=1, column=1, sticky='ew', pady=5, padx=5)
        frame_wifi.columnconfigure(1, weight=1)

        # Monitor Serial
        tk.Label(root, text="Log de Inicialização do Dispositivo:", font=('Segoe UI', 10, 'bold'), bg="#121214", fg="#8d8d99").pack(anchor='w', padx=25, pady=(10,0))
        self.txt_serial = tk.Text(root, height=8, bg="#202024", fg="#00b37e", font=('Consolas', 9), insertbackground="white", relief="flat")
        self.txt_serial.pack(fill='both', expand=True, padx=20, pady=5)
        
        # Botão de Ação Principal Estilizado de forma nativa e segura
        self.btn_instalar = tk.Button(root, text="INICIAR MOUTHTRACKER", command=self.iniciar_processo, bg="#00b37e", fg="#ffffff", font=('Segoe UI', 10, 'bold'), relief="flat", activebackground="#00875f", activeforeground="#ffffff")
        self.btn_instalar.pack(pady=15, ipadx=10, ipady=5)

        # Status inferior
        self.lbl_status = tk.Label(root, text="Status: Pronto para conectar", bg="#121214", fg="#8d8d99", font=('Segoe UI', 9, 'italic'))
        self.lbl_status.pack(side='bottom', pady=5)

        self.window_video = None
        self.lbl_video = None
        self.cap = None
        self.rodando_video = False

    def listar_portas(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def atualizar_status(self, texto, cor="#e1e1e6"):
        self.lbl_status.config(text=f"Status: {texto}", fg=cor)
        self.root.update_idletasks()

    def log_serial(self, texto):
        self.txt_serial.insert(tk.END, texto)
        self.txt_serial.see(tk.END)
        self.root.update_idletasks()

    def iniciar_processo(self):
        threading.Thread(target=self.processar, daemon=True).start()

    def processar(self):
        port = self.porta_selecionada.get()
        ssid = self.entry_ssid.get()
        password = self.entry_pass.get()

        if not port or port == "Nenhuma porta encontrada" or not ssid:
            messagebox.showwarning("MouthTracker", "Por favor, selecione a porta USB e preencha os dados básicos!")
            return

        self.btn_instalar.config(state='disabled')
        self.txt_serial.delete('1.0', tk.END)
        
        try:
            pasta_atual = os.path.dirname(os.path.abspath(__file__))
            arquivo_bin = os.path.join(pasta_atual, "CameraWebServer.ino.bin")
            
            if not os.path.exists(arquivo_bin):
                arquivo_bin = os.path.join(pasta_atual, "CameraWebServer.ino.bin.bin")

            if not os.path.exists(arquivo_bin):
                raise Exception("O arquivo 'CameraWebServer.ino.bin' nao foi encontrado nesta pasta!")

            self.atualizar_status("Gravando ESP32-CAM via USB...", "#fab387")
            self.log_serial(">>> Iniciando gravação do Firmware...\n")
            
            comando_flash = [
                "python", "-m", "esptool", 
                "--chip", "esp32", 
                "--port", port, 
                "--baud", "460800", 
                "write_flash", "-z", "0x10000", arquivo_bin
            ]
            
            subprocess.run(comando_flash, check=True, stdout=subprocess.DEVNULL)

            self.atualizar_status("Reiniciando hardware...", "#f9e2af")
            self.log_serial(">>> Gravação concluída! Forçando Reset de hardware via Serial...\n")
            
            ser = serial.Serial(port, 115200, timeout=0.1)
            ser.setDTR(False)
            ser.setRTS(True)
            time.sleep(0.2)
            ser.setRTS(False) 
            time.sleep(0.5)

            self.atualizar_status("Enviando credenciais Wi-Fi...", "#89b4fa")
            comando_config = f"SET_WIFI:{ssid},{password}\n"
            ser.write(comando_config.encode('utf-8'))
            
            self.atualizar_status("Lendo Monitor Serial...", "#a6e3a1")
            
            ip_detectado = None
            buffer_serial = ""
            
            for _ in range(400): 
                if ser.in_waiting:
                    dados = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    buffer_serial += dados
                    self.log_serial(dados) 
                    
                    if "http://" in buffer_serial:
                        match = re.search(r'http://([\d\.]+)', buffer_serial)
                        if match:
                            ip_detectado = match.group(1)
                    
                            try:
                                pasta_atual = os.path.dirname(os.path.abspath(__file__))
                                ip_file = os.path.join(pasta_atual, "last_ip.txt")
                                with open(ip_file, "w") as f:
                                    f.write(str(ip_detectado).strip())
                            except Exception:
                                pass
                    
                            break
                time.sleep(0.1)
            ser.close()

            if not ip_detectado:
                raise Exception("O firmware rodou, mas o Wi-Fi não retornou um IP válido na rede local.")

            self.atualizar_status("Sucesso! Abrindo janela de vídeo...", "#00b37e")
            self.log_serial(f"\n>>> IP Encontrado: {ip_detectado}\n>>> Ajustando parâmetros internos do hardware...")
            time.sleep(1)
            
            try:
                urllib.request.urlopen(f"http://{ip_detectado}/control?var=framesize&val=10", timeout=2)
                urllib.request.urlopen(f"http://{ip_detectado}/control?var=led_intensity&val=20", timeout=2)
                self.log_serial("\n>>> Resolução configurada para VGA e LED de flash ativado!\n")
            except Exception as e_cmd:
                self.log_serial(f"\n>>> [Aviso] Erro ao aplicar ajustes de imagem: {e_cmd}\n")

            self.abrir_janela_video(ip_detectado)

        except Exception as e:
            self.atualizar_status("Ocorreu um erro!", "#f38ba8")
            self.log_serial(f"\n[ERRO] Detalhes: {e}\n")
            messagebox.showerror("Erro MouthTracker", f"Detalhes: {e}")
            self.btn_instalar.config(state='normal')

    def abrir_janela_video(self, ip):
        self.window_video = tk.Toplevel(self.root)
        self.window_video.title("MouthTracker - Stream Ativo")
        self.window_video.geometry("640x480")
        self.window_video.configure(bg="#121214")
        
        self.lbl_video = tk.Label(self.window_video, bg="#121214")
        self.lbl_video.pack(fill="both", expand=True)

        self.window_video.protocol("WM_DELETE_WINDOW", self.fechar_janela_video)

        url_stream = f"http://{ip}:81/stream"
        self.cap = cv2.VideoCapture(url_stream)
        
        if not self.cap.isOpened():
            url_stream = f"http://{ip}/stream"
            self.cap = cv2.VideoCapture(url_stream)

        self.rodando_video = True
        self.atualizar_frame_video()

    def atualizar_frame_video(self):
        if self.rodando_video and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(frame_rgb)
                img_tk = ImageTk.PhotoImage(image=img_pil)
                
                self.lbl_video.img_tk = img_tk
                self.lbl_video.config(image=img_tk)
            
            self.window_video.after(15, self.atualizar_frame_video)

    def fechar_janela_video(self):
        self.rodando_video = False
        if self.cap:
            self.cap.release()
        if self.window_video:
            self.window_video.destroy()
        self.btn_instalar.config(state='normal')
        self.atualizar_status("Dispositivo desconectado.", "#8d8d99")

if __name__ == "__main__":
    root = tk.Tk()
    app = MouthTrackerLauncher(root)
    root.mainloop()
