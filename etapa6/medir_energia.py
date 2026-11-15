"""TI Verde: mede latência, potência da GPU e CPU/RAM do Ollama durante classificações da Etapa 4.

Uso: python medir_energia.py [n]   (padrão 5 relatórios, os 3 da Etapa 4 em rodízio)
Potência só da GPU (nvidia-smi); a parte da inferência que roda na CPU não entra na conta de energia.
"""
import glob, os, statistics, subprocess, sys, threading, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "etapa4"))
os.environ.setdefault("TABELA", "triagem")
import app

amostras_gpu, amostras_docker, parar = [], [], threading.Event()


def amostrar_gpu():
    while not parar.is_set():
        out = subprocess.run(["nvidia-smi", "--query-gpu=power.draw,utilization.gpu,memory.used",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.split(",")
        amostras_gpu.append(tuple(float(x) for x in out))
        time.sleep(0.5)


def amostrar_docker():
    while not parar.is_set():
        out = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}};{{.MemUsage}}", "cloud-ollama-1"],
                             capture_output=True, text=True).stdout.strip()
        if out:
            cpu, mem = out.split(";")
            amostras_docker.append((float(cpu.rstrip("%")), mem.split("/")[0].strip()))


relatorios = sorted(glob.glob(os.path.join(os.path.dirname(app.__file__), "relatorios", "*.txt")))
n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
app.classificar(open(relatorios[0]).read())  # aquecimento: modelo já carregado na GPU

ociosa = []
for _ in range(6):
    ociosa.append(float(subprocess.run(["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
                                       capture_output=True, text=True).stdout))
    time.sleep(0.5)

threads = [threading.Thread(target=amostrar_gpu), threading.Thread(target=amostrar_docker)]
for t in threads:
    t.start()
latencias, tokens = [], []
for i in range(n):
    texto = open(relatorios[i % len(relatorios)]).read()
    t0 = time.time()
    _, _, uso = app.classificar(texto)
    latencias.append(time.time() - t0)
    tokens.append((uso["inputTokens"], uso["outputTokens"]))
parar.set()
for t in threads:
    t.join()

pot = statistics.mean(a[0] for a in amostras_gpu)
lat = statistics.mean(latencias)
print(f"inferências: {n}")
print(f"latência média: {lat:.2f} s (mín {min(latencias):.2f}, máx {max(latencias):.2f})")
print(f"tokens médios: entrada {statistics.mean(t[0] for t in tokens):.0f}, saída {statistics.mean(t[1] for t in tokens):.0f}")
print(f"GPU: potência ociosa {statistics.mean(ociosa):.1f} W, durante inferência {pot:.1f} W (pico {max(a[0] for a in amostras_gpu):.1f} W), "
      f"uso médio {statistics.mean(a[1] for a in amostras_gpu):.0f} %, VRAM {max(a[2] for a in amostras_gpu):.0f} MiB")
if amostras_docker:
    print(f"Ollama (docker stats): CPU média {statistics.mean(a[0] for a in amostras_docker):.0f} %, "
          f"pico {max(a[0] for a in amostras_docker):.0f} %, RAM {amostras_docker[-1][1]}")
print(f"energia da GPU por relatório: {pot * lat:.0f} J = {pot * lat / 3600 * 1000:.2f} mWh")
