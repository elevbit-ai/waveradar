# WaveRadar para Android

Aplicativo de **presença pelo roteador**: o telefone lê o RSSI do Wi-Fi ao qual ele está ligado e estima se houve movimento nesse enlace.

Autor: **Joaquim Pedro de Morais Filho** · [j360074@hotmail.com](mailto:j360074@hotmail.com)

APK assinado: [release android-v1.0.0](https://github.com/elevbit-ai/waveradar/releases/tag/android-v1.0.0). Certificado e como conferir a assinatura: [AUTHORSHIP.md](AUTHORSHIP.md).

## O que é real neste telefone

O Android entrega a intensidade do sinal (**RSSI**, em dBm) da rede em que o telefone está associado. Uma pessoa atravessando o caminho entre o telefone e o roteador muda esse número. O app:

1. Amostra o RSSI cerca de 5 vezes por segundo (o sistema muitas vezes só atualiza o valor de verdade bem mais devagar).
2. Compara a variação dos últimos segundos com uma linha de base medida numa sala quieta (8 segundos de calibração).
3. Marca **em movimento** quando a variação sobe, e mantém **presente** por 15, 30, 60 ou 120 segundos depois do último movimento.
4. Mostra o RSSI, a taxa em que o valor realmente muda e, só quando essa taxa chega a 8 Hz, a frequência dominante na banda de movimento.

Nada sai do telefone. Não há conta, não há servidor, não há lista de aparelhos vizinhos.

## O que este APK não faz

O chip Wi-Fi do telefone não entrega **CSI** (amplitude e fase por subportadora) para um aplicativo. Sem isso não há Doppler de 0,15–4 Hz confiável na maioria dos aparelhos, nem setores de multipercurso, nem direção. O ponto na tela fica no eixo telefone–roteador de propósito: a distância até o centro é a intensidade do movimento, não a posição de alguém na sala.

Uma pessoa imóvel, depois do tempo de retenção, volta a aparecer como **vazio**. Ventilador, cortina e um telefone sendo carregado na mão também mexem no RSSI. Para medir a sala, o telefone fica parado (de preferência carregando), do outro lado do cômodo em relação ao roteador.

CSI e o radar completo continuam no aplicativo de computador e no firmware ESP32 deste repositório.

## Instalar

Requisitos: Android 8 ou mais novo, na rede Wi-Fi do roteador que você administra.

1. Baixe `WaveRadar-1.0.0.apk` na release.
2. Confira o SHA-256 publicado na mesma release.
3. Abra o arquivo no telefone e permita a instalação.
4. Conecte-se ao Wi-Fi do seu roteador. Dados móveis não servem.
5. Leia o aviso e toque em **Entendi, começar**.
6. A permissão de localização só serve para mostrar o nome da rede. O RSSI é lido mesmo se você negar. O app não usa GPS e não envia posição.
7. Durante **Calibrando**, deixe o telefone parado e fique imóvel.
8. Ande entre o telefone e o roteador. A linha de RSSI deve se mover e o estado deve ir para **Em movimento**.

Para parar, use o botão na tela ou **Parar** na notificação. Enquanto a notificação estiver ativa, a leitura continua com a tela apagada.

## Compilar

JDK 17 e Android SDK 34.

```bash
cd android
# sdk.dir em local.properties, ou ANDROID_HOME apontando para o SDK
./gradlew :app:testDebugUnitTest :app:assembleDebug
```

O APK de release é assinado só se existir `android/keystore.properties` (arquivo local, fora do git) apontando para a chave do autor. Quem clona o repositório gera um APK de debug sem essa chave.

## English

WaveRadar Android estimates occupancy from the RSSI of the phone's own association to a router you administer. It is a variance detector with a presence hold, not CSI, not angle-of-arrival, and not identification. Samples stay on the device. The release APK is signed by Joaquim Pedro de Morais Filho; see [AUTHORSHIP.md](AUTHORSHIP.md).
