<div align="center">

# 📡 WaveRadar

### Radar de Movimento por Sensoriamento Wi-Fi

**Veja movimento através do canal de rádio do seu próprio roteador — CSI, Doppler e análise de amplitude/fase, exibidos como um radar ao vivo.**

[**Site**](https://elevbit-ai.github.io/waveradar/) · [**Vídeo demo**](https://elevbit-ai.github.io/waveradar/#demo) · [**English**](README.md)

<img src="docs/assets/demo.gif" width="480" alt="Demonstração do WaveRadar — movimento detectado via Wi-Fi exibido como pontos no radar">

</div>

---

## O que é isso?

Cada pacote Wi-Fi que atravessa um cômodo é deformado por tudo em que as
ondas de rádio refletem — paredes, móveis **e corpos em movimento**. Uma
pessoa andando entre o roteador e o notebook perturba o canal de multipercurso
e deixa uma assinatura mensurável: flutuações de amplitude, rotação de fase e
uma **assinatura Doppler** na banda de 0,15–4 Hz, típica do movimento humano.

O WaveRadar captura essa assinatura e a transforma em um radar ao vivo no
navegador — varredura, pontos, espectro Doppler e waterfall — **sem câmeras e
sem sensores extras**.

## Instalação rápida

**Windows** (PowerShell):

```powershell
irm https://elevbit-ai.github.io/waveradar/install.ps1 | iex
```

**Linux / macOS**:

```bash
curl -fsSL https://elevbit-ai.github.io/waveradar/install.sh | bash
```

**Ou com pip**:

```bash
pip install "waveradar[esp32] @ git+https://github.com/elevbit-ai/waveradar.git"
waveradar                      # radar com o sinal do seu roteador
waveradar --source sim         # demo sem hardware (alvo sintético)
```

O radar abre em `http://127.0.0.1:8347`. Ele calibra por alguns segundos
(aprendendo o canal em repouso); depois, ande pela sala — você vai ver.

## Modos de sensoriamento

| Modo | Hardware | Sinal | O que você obtém |
|---|---|---|---|
| **RSSI** (padrão) | Nenhum — qualquer roteador + o Wi-Fi do seu PC | Intensidade do sinal, ~6–9 Hz | Presença de movimento, intensidade, frequência Doppler dominante |
| **CSI / ESP32** | Uma placa ESP32 (~R$ 25) | ~52 subportadoras, amplitude + fase, 50–100 Hz | Tudo acima + estrutura por subportadora → micro-Doppler mais rico e pontos em múltiplos setores |
| **Simulador** | Nenhum | CSI sintético de 52 subportadoras | Pipeline completo, usado no vídeo acima |

Para o modo CSI, grave o firmware incluído em
**[`firmware/esp32/`](firmware/esp32/)** (Arduino IDE, 5 minutos). O parser
também aceita o formato do [`esp-csi`](https://github.com/espressif/esp-csi)
oficial da Espressif.

## Como funciona

- **Variação de amplitude/fase** — um refletor em movimento muda o
  comprimento dos caminhos que o sinal percorre, modulando amplitude e fase
  das subportadoras.
- **Doppler** — movimento a uma velocidade *v* desloca a energia refletida em
  `f_d = 2v/λ` (≈ 16 Hz por m/s em 2,4 GHz); balanço corporal, gestos e
  caminhada concentram-se em **0,15–4 Hz** de variação do canal — exatamente
  a banda que o WaveRadar isola com janela deslizante + FFT e compara com um
  baseline adaptativo de "sala quieta".
- **CSI (Channel State Information)** — a estimativa complexa do canal por
  subportadora que todo receptor OFDM já calcula. O ESP32 a expõe; a maioria
  dos roteadores domésticos não, e por isso existe o modo RSSI sem hardware.

## Limitações honestas (leia)

- **O ângulo no radar é uma pseudo-projeção, não direção real de chegada.**
  Com um único enlace detecta-se *que* algo se move, *quanto* e seu conteúdo
  Doppler — não a posição absoluta. No modo CSI, o ângulo do ponto reflete
  quais grupos de subportadoras (componentes de multipercurso) estão sendo
  perturbados: é estável e repetível para um mesmo ambiente, mas não é um
  mapa calibrado. Localização real exige múltiplas antenas ou enlaces.
- **O modo RSSI é mais grosseiro que o CSI** — 1 canal em vez de ~52.
- Os anéis de distância codificam o Doppler dominante, não metros.
- Ventiladores, cortinas, pets e interferência vizinha mexem no baseline; a
  calibração adaptativa absorve mudanças lentas.

## Privacidade e uso responsável

O WaveRadar sente movimento no ambiente **da sua própria rede e dos seus
próprios dispositivos**. Use em espaços que você possui ou administra, com o
conhecimento das pessoas presentes (segurança doméstica, monitoramento de
idosos, experimentos maker). Sensoriar espaços que você não tem direito de
monitorar pode ser ilegal — não faça.

## Autor

**Joaquim Pedro de Morais Filho**
📧 [j360074@hotmail.com](mailto:j360074@hotmail.com)

Licenciado sob a [Licença MIT](LICENSE) — © 2026 Joaquim Pedro de Morais Filho.
