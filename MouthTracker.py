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
import pyvirtualcam
import ctypes  # 🔴 Biblioteca nativa do Windows para gerar a notificação do sistema

def mostrar_notificacao_windows(titulo, mensagem):
    """Gera uma notificação nativa no canto da tela do Windows."""
    try:
        # Usa a API do Windows para exibir uma caixa de mensagem de notificação temporária
        threading.Thread(
            target=lambda: ctypes.windll.user32.MessageBoxW(0, mensagem, titulo, 0x40 | 0x00),
            daemon=True
        ).start()
    except Exception:
        pass

def checar_e_iniciar():
    try:
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
                        rotas_led = [
                            "/control?var=led_intensity&val=4",
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
    transmitir_webcam_virtual(cap)

def transicionar_para_configurador(pasta):
    root.destroy()
    chamar_configurador(pasta)

def transmitir_webcam_virtual(cap):
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    try:
        with pyvirtualcam.Camera(width=width, height=height, fps=30) as vcam:
            print(f"[SUCESSO] Câmera Virtual Ativada em segundo plano: {vcam.device}")
            
            # 🟢 DISPARA A NOTIFICAÇÃO: Informa o usuário no Windows que a webcam está ligada
            mostrar_notificacao_windows(
                "MouthTracker", 
                f"ESP32-CAM ativa! Transmitindo via {vcam.device}."
            )
            
            while True:
                cap.grab() 
                ret, frame = cap.retrieve()
                
                if not ret:
                    print("[ERRO] Perda de sinal com a ESP32-CAM!")
                    break

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                vcam.send(frame_rgb)
                vcam.sleep_until_next_frame()
                
    except Exception as e:
        print(f"[ERRO SUPOSTO] Falha na Webcam Virtual: {e}")
    finally:
        cap.release()

def chamar_configurador(pasta):
    script_config = os.path.join(pasta, "Instalador_ESP32CAM.exe")
    if os.path.exists(script_config):
        os.startfile(script_config)
    else:
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
