import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time


class ThermalertFullController:
    def __init__(self, root):
        self.root = root
        self.root.title("Fluke Thermalert 4.0 - Interface de Engenharia Completa")
        self.root.geometry("1100x850")
        self.ser = None
        self.burst_active = False

        # --- DICIONÁRIO COMPLETO: COMANDO, TIPO E OPÇÕES DO MANUAL ---
        # Formato: "Nome": ("Sigla", "Tipo", "Valores Legais/Instruções")
        self.comandos_db = {
            "Medição e Alvo": [
                ("Temperatura do Alvo", "T", "P", "Retorna a temperatura atual do alvo."),
                ("Energia do Alvo", "Q", "P", "Retorna o valor de energia do alvo."),
                ("Emissividade Interna", "E", "PS", "0.100 a 1.100 (Padrão: 0.950)"),
                ("Emissividade Calculada", "CE", "P", "Retorna a emissividade calculada atual."),
                ("Fonte de Emissividade", "ES", "PS", "I=Interna, E=Ext (12-w), S=Rotary Switch (2-w)"),
                ("Compensação Background", "A", "PS", "Dentro do range de medição do sensor."),
                ("Controle Ambiência", "AC", "PS", "0=Sem comp., 1=Via comando A, 2=Ext (12-w)"),
                ("Temperatura Interna", "I", "P", "Temperatura ambiente interna do sensor."),
                ("Transmitância", "XG", "PS", "0.100 a 1.000 (Padrão: 1.000)"),
                ("Unidade de Temp.", "U", "PS", "C = Celsius, F = Fahrenheit"),
                ("Temp. Conector/Box", "XJ", "P", "Temperatura no conector ou caixa de acessórios.")
            ],
            "Processamento de Sinal": [
                ("Tempo de Média", "G", "PS", "0 = Desligado, 0.1 a 999.0 segundos"),
                ("Peak Hold Time", "P", "PS", "0 a 998.9s (999.0 = Infinito)"),
                ("Valley Hold Time", "F", "PS", "0 a 998.9s (999.0 = Infinito)"),
                ("Adv. Hold Threshold", "C", "PS", "Temperatura de limiar para Advanced Hold."),
                ("Adv. Hold Average", "AA", "PS", "0 a 999.0s (Tempo de média para Advanced Hold)"),
                ("Adv. Hold Hysteresis", "XY", "PS", "-100.0 a 100.0°C / -180.0 a 180.0°F"),
                ("Ganho (Gain)", "DG", "PS", "0.8000 a 1.2000 (Padrão: 1.0000)"),
                ("Offset", "DO", "PS", "-200 a 200°C / -360 a 360°F"),
                ("Inicialização (XI)", "XI", "PS", "1 = Reset após queda de energia, 0 = Sem reset")
            ],
            "Saída Analógica e Escala": [
                ("Controle de Saída", "O", "PS", "0=Auto, 4-20=Fixo em mA (Loop Test)"),
                ("Modo de Saída", "XO", "PS", "0=0-20mA, 4=4-20mA, 8=0-5V, 9=0-10V"),
                ("Topo da Escala (H)", "H", "PS", "Temp. para saída máxima (mA/V)"),
                ("Base da Escala (L)", "L", "PS", "Temp. para saída mínima (mA/V)"),
                ("Topo Escala (V2)", "AH", "PS", "Para modelos de 12 fios."),
                ("Base Escala (V2)", "AL", "PS", "Para modelos de 12 fios."),
                ("Fail Safe Topo", "AHO", "PS", "20.0 a 21.0 mA (Alarme de falha)"),
                ("Fail Safe Fundo", "ALO", "PS", "3.5 a 4.0 mA (Alarme de falha)")
            ],
            "Alarmes e Relé": [
                ("Controle do Relé (K)", "K", "PS", "0=Aberto, 1=Fechado, 2=Alvo N.O., 3=Alvo N.C."),
                ("Threshold Superior", "XS", "PS", "Temperatura para ativar relé (High)"),
                ("Threshold Inferior", "XP", "PS", "Temperatura para ativar relé (Low)"),
                ("CS Atual", "CS", "P", "Threshold superior atual para Relé."),
                ("CK Atual", "CK", "P", "Threshold inferior atual para Relé."),
                ("Deadband Relé", "XD", "PS", "1.0 a 50.0°C (Histerese do alarme)"),
                ("Status do Trigger", "XT", "P", "0 = Inativo, 1 = Ativo"),
                ("Função FTC3", "XN", "PS", "N=Nenhuma, T=Trigger, H=Hold, L=Laser")
            ],
            "Interface e Burst": [
                ("Modo Poll/Burst", "V", "PS", "P = Poll (Interrogação), B = Burst (Contínuo)"),
                ("Velocidade Burst", "BS", "PS", "100 a 10000 ms (Intervalo entre dados)"),
                ("Conteúdo Burst (X$)", "X$", "PS", "Ex: UTICE (U=Unidade, T=Temp, I=Interna...)"),
                ("Ver String Burst", "$", "P", "Exibe o formato atual da string de burst."),
                ("Baud Rate RS485", "D", "PS", "0048, 0096, 0192, 0384, 0576, 1152"),
                ("Endereço Multidrop", "XA", "PS", "000 = Único, 001 a 032 = Múltiplos"),
                ("Resistor 120R", "TR", "PS", "0 = Desativado, 1 = Ativado (RS485)")
            ],
            "Rede e Ethernet": [
                ("Endereço IP", "IP", "PS", "Ex: 192.168.42.134"),
                ("Máscara de Rede", "NM", "PS", "Ex: 255.255.255.0"),
                ("Gateway", "GW", "PS", "Ex: 192.168.42.1"),
                ("Porta TCP", "PORT", "PS", "1 a 65535 (Padrão: 6363)"),
                ("DHCP/BOOTP", "DHCP", "PS", "0=OFF, 1=DHCP ON, 2=BOOTP ON"),
                ("Timeout TCP", "TTI", "PS", "0 = Infinito, 1 a 240 segundos"),
                ("Web Server", "WS", "PS", "0 = OFF, 1 = ON")
            ],
            "Diagnóstico e ID": [
                ("Modelo (ID)", "XU", "P", "Identificação do modelo (ex: STRLTH5)"),
                ("Número de Série", "XV", "P", "Número de série de fábrica."),
                ("UID do MCU", "%UID", "P", "ID único do processador."),
                ("Firmware Principal", "XR", "P", "Versão do firmware do sensor."),
                ("Firmware Analógico", "XRA", "P", "Versão do firmware da placa analógica."),
                ("Endereço MAC", "MAC", "P", "Endereço físico de rede."),
                ("Remark", "DS", "P", "Informação especial gravada no sensor."),
                ("Código de Erro", "EC", "P", "0001=Over range, 0002=Under range, etc."),
                ("ADC YA", "YA", "P", "Contagem bruta ADC (Ambiente + IR)"),
                ("ADC YB", "YB", "P", "Contagem bruta ADC (PSa + Energy)")
            ],
            "Sistema e Manutenção": [
                ("Laser", "XL", "PS", "0=OFF, 1=ON, 2=ON no Power-up"),
                ("Simular Temp", "STT", "PS", "-100 a 9998.9 (9999.0 = Desativa simulação)"),
                ("Resetar Unidade", "RST", "S", "Reinicia o sensor imediatamente."),
                ("Restaurar Fábrica", "XF", "S", "Retorna todos os parâmetros aos padrões."),
                ("Mínimo do Range", "XB", "P", "Limite inferior de temperatura do modelo."),
                ("Máximo do Range", "XH", "P", "Limite superior de temperatura do modelo.")
            ]
        }

        self.setup_ui()

    def setup_ui(self):
        # Frame de Conexão
        t_frame = ttk.Frame(self.root, padding=10);
        t_frame.pack(fill="x")
        self.c_ports = ttk.Combobox(t_frame, values=[p.device for p in serial.tools.list_ports.comports()])
        self.c_ports.pack(side="left", padx=5)
        ttk.Button(t_frame, text="Conectar", command=self.toggle_serial).pack(side="left")

        # Layout Tabs
        self.nb = ttk.Notebook(self.root);
        self.nb.pack(fill="both", expand=True, padx=10)

        # Aba 1: Navegador
        self.t_list = ttk.Frame(self.nb);
        self.nb.add(self.t_list, text="Navegador de Comandos")
        pw = ttk.PanedWindow(self.t_list, orient="horizontal");
        pw.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(pw, show="tree");
        pw.add(self.tree, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        for cat, cmds in self.comandos_db.items():
            node = self.tree.insert("", "end", text=cat, open=True)
            for d, c, t, o in cmds: self.tree.insert(node, "end", text=d, values=(c, t, o))

        # Frame de Detalhes e Ação
        self.f_work = ttk.Frame(pw, padding=20);
        pw.add(self.f_work, weight=2)
        self.l_cmd = ttk.Label(self.f_work, text="Selecione um comando", font=("Arial", 12, "bold"));
        self.l_cmd.pack(pady=5)

        # GUIA DE OPÇÕES (A NOVIDADE)
        self.l_help = ttk.Label(self.f_work, text="", wraplength=400, foreground="blue", font=("Arial", 10, "italic"))
        self.l_help.pack(pady=10)

        self.e_val = ttk.Entry(self.f_work, font=("Arial", 12))
        self.b_get = ttk.Button(self.f_work, text="LER (?)", command=lambda: self.exec_cmd("poll"))
        self.b_set = ttk.Button(self.f_work, text="DEFINIR (=)", command=lambda: self.exec_cmd("set"))

        self.f_burst = ttk.LabelFrame(self.f_work, text=" Modo Burst ", padding=10)
        self.b_burst = ttk.Button(self.f_burst, text="ATIVAR ESCUTA", command=self.toggle_burst);
        self.b_burst.pack()

        # Aba 2: Manual
        self.t_man = ttk.Frame(self.nb);
        self.nb.add(self.t_man, text="Comando Manual")
        self.e_man = ttk.Entry(self.t_man, font=("Consolas", 14));
        self.e_man.pack(fill="x", padx=10, pady=20)
        ttk.Button(self.t_man, text="ENVIAR", command=self.send_man).pack()

        # Console
        self.txt = tk.Text(self.root, height=12, bg="#121212", fg="#00FF00", font=("Consolas", 10))
        self.txt.pack(fill="x", padx=10, pady=10)

    def toggle_serial(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close(); self.log("Desconectado.")
            else:
                self.ser = serial.Serial(self.c_ports.get(), 9600, timeout=0.5)
                self.log(f"Porta {self.c_ports.get()} conectada.")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def on_select(self, e):
        item = self.tree.selection()[0]
        if self.tree.parent(item) == "": return
        c, t, o = self.tree.item(item, "values")

        self.l_cmd.config(text=f"Comando: {c}")
        self.l_help.config(text=f"Valores Legais: {o}")  # Mostra as opções do manual

        self.b_get.pack_forget();
        self.e_val.pack_forget();
        self.b_set.pack_forget();
        self.f_burst.pack_forget()
        if "P" in t: self.b_get.pack(fill="x", pady=2)
        if "S" in t:
            self.e_val.pack(fill="x", pady=2)
            self.b_set.pack(fill="x", pady=2)
        if c == "V": self.f_burst.pack(fill="x", pady=15)

    def exec_cmd(self, acao):
        item = self.tree.selection()[0]
        c, _, _ = self.tree.item(item, "values")
        # Regra de terminação \r\n para USB
        if acao == "poll":
            m = f"{c}\r\n" if c in ["V", "BS", "$", "X$", "IP"] else f"?{c}\r\n"
        else:
            m = f"{c}={self.e_val.get()}\r\n"
        self.talk(m)

    def talk(self, m):
        if not self.ser or not self.ser.is_open: return
        self.ser.write(m.encode('ascii'))
        time.sleep(0.1)
        r = self.ser.read_all().decode('ascii').strip()
        self.log(f"SND: {m.strip()} | REC: {r}")

    def send_man(self):
        c = self.e_man.get().strip()
        if c: self.talk(f"{c}\r\n"); self.e_man.delete(0, tk.END)

    def log(self, m):
        self.txt.insert("end", f"[{time.strftime('%H:%M:%S')}] {m}\n"); self.txt.see("end")

    def toggle_burst(self):
        if not self.burst_active:
            self.burst_active = True;
            self.b_burst.config(text="PARAR")
            self.ser.write(b"V=B\r\n")
            threading.Thread(target=self.b_loop, daemon=True).start()
        else:
            self.burst_active = False;
            self.ser.write(b"V=P\r\n")
            self.b_burst.config(text="ATIVAR")

    def b_loop(self):
        while self.burst_active:
            if self.ser.in_waiting:
                l = self.ser.readline().decode('ascii').strip()
                if l: self.root.after(0, self.log, f"BURST: {l}")
            time.sleep(0.01)


if __name__ == "__main__":
    root = tk.Tk();
    app = ThermalertFullController(root);
    root.mainloop()