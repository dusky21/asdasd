import tkinter as tk
from tkinter import messagebox
import threading
import cv2
import os
import sys
import time
import socket
import urllib.request
import multiprocessing

def checar_e_iniciar():
    try:
        # Descobre a pasta real onde o executável ou script está rodando
        if getattr(sys, 'frozen', False):
            pasta_atual = os.path.dirname(sys.executable)
        else:
            pasta_atual = os.path.dirname(os.path.abspath(__file__))
            
        ip_file = os.path.join(pasta_atual, "last_ip.txt")
        ip_detectado = None
        
        if os.path.exists(ip_file):
            with open(ip_file, "r") as f:
                ip_detectado = f.read().strip()
                
        if not ip_detectado:
            root.after(0, lambda: transicionar_para_configurador(pasta_atual))
            return

        ip_limpo = ip_detectado.replace("http://", "").replace("/", "").strip()
        if ":" in ip_limpo:
            ip_puro = ip_limpo.split(":")
        else:
            ip_puro = ip_limpo
        
        # 6 tentativas estáveis
        for tentativa in range(6):
            numero_tentativa = tentativa + 1
            inicio_do_loop = time.time()
            
            atualizar_texto_carregamento(f"Tentativa {numero_tentativa}/6. Aguardando rádio...")
            
            for porta in [81, 80]:
                dispositivo_vivo = False
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.4)
                
                try:
                    s.connect((ip_puro, porta))
                    dispositivo_vivo = True
                except Exception:
                    dispositivo_vivo = False
                finally:
                    s.close()

                if dispositivo_vivo:
                    rota_valida = f":{porta}/stream" if porta == 81 else "/stream"
                    url_stream = f"http://{ip_puro}{rota_valida}"
                    
                    cap = cv2.VideoCapture(url_stream)
                    if cap.isOpened():
                        # Comando de brilho suave para o LED
                        rotas_led = [
                            "/control?var=led_intensity&val=10",
                            "/control?var=flash&val=0",
                            "/control?var=led&val=1",
                            "/led/on"
                        ]
                        for rota in rotas_led:
                            try:
                                url_led = f"http://{ip_puro}{rota}"
                                urllib.request.urlopen(url_led, timeout=0.3)
                            except Exception:
                                pass
                        
                        root.after(0, lambda c=cap: transicionar_para_video(c))
                        return
                    cap.release()
            
            tempo_decorrido = time.time() - inicio_do_loop
            tempo_restante = 1.5 - tempo_decorrido
            if tempo_restante > 0:
                time.sleep(tempo_restante)

        root.after(0, lambda: transicionar_para_configurador(pasta_atual))
        
    except Exception as e:
        root.after(0, lambda err=e: messagebox.showerror("Erro de Rede", f"Falha na checagem:\n\n{str(err)}"))

def atualizar_texto_carregamento(texto):
    if root.winfo_exists():
        root.after(0, lambda: lbl_info.config(text=texto))

def transicionar_para_video(cap):
    root.destroy()
    abrir_janela_video(cap)

def transicionar_para_configurador(pasta):
    root.destroy()
    chamar_configurador(pasta)

def abrir_janela_video(cap):
    from PIL import Image, ImageTk
    
    v_root = tk.Tk()
    v_root.title("MouthTracker - Stream Ativo")
    v_root.geometry("640x480")
    v_root.configure(bg="#121214")
    
    lbl_video = tk.Label(v_root, bg="#121214")
    lbl_video.pack(fill="both", expand=True)
    
    def atualizar_frame():
        ret, frame = cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(frame_rgb)
            img_tk = ImageTk.PhotoImage(image=img_pil)
            lbl_video.img_tk = img_tk
            lbl_video.config(image=img_tk)
        v_root.after(15, atualizar_frame)
        
    def fechar():
        cap.release()
        v_root.destroy()
        
    v_root.protocol("WM_DELETE_WINDOW", fechar)
    atualizar_frame()
    v_root.mainloop()

def chamar_configurador(pasta):
    # Procure agora pelo arquivo EXECUTÁVEL do configurador na pasta
    script_config = os.path.join(pasta, "Instalador_ESP32CAM.exe")
    
    if os.path.exists(script_config):
        # Abre o executável filho de forma direta e sem console
        os.startfile(script_config)
    else:
        # Se por acaso o .exe não estiver lá, tenta procurar o .py antigo como plano B
        script_py = os.path.join(pasta, "Instalador_ESP32CAM.py")
        if os.path.exists(script_py):
            os.startfile(script_py)
        else:
            messagebox.showerror("Erro de Arquivo", f"Não foi possível localizar o configurador (.exe ou .py) na pasta:\n{pasta}")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    root = tk.Tk()
    root.title("MouthTracker")
    root.geometry("320x140")
    root.configure(bg="#121214")
    
    tk.Label(root, text="MOUTHTRACKER", font=('Segoe UI', 14, 'bold'), bg="#121214", fg="#00b37e").pack(pady=15)
    lbl_info = tk.Label(root, text="Procurando dispositivo na rede...", font=('Segoe UI', 9), bg="#121214", fg="#8d8d99")
    lbl_info.pack()
    
    root.after(100, lambda: threading.Thread(target=checar_e_iniciar, daemon=True).start())
    root.mainloop()
