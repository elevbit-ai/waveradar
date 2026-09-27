# Autoria e assinatura

**Joaquim Pedro de Morais Filho**
j360074@hotmail.com

© 2026 Joaquim Pedro de Morais Filho. Licença MIT — a mesma do restante do WaveRadar.

O APK de release é assinado com um certificado RSA de 2048 bits, algoritmo SHA256withRSA, válido até 12 de fevereiro de 2054.

| Campo | Valor |
|---|---|
| CN | Joaquim Pedro de Morais Filho |
| OU | WaveRadar |
| O | elevbit-ai |
| E-mail no certificado | j360074@hotmail.com |
| Número de série | `bed60f07e6177dfb` |
| SHA-256 | `F5:81:EB:8E:53:66:C4:D4:E0:CD:A0:87:C4:D7:48:48:41:0B:B4:B5:C3:6B:40:2A:E4:50:60:E4:95:6B:E8:61` |
| SHA-1 | `D6:11:96:C8:D1:7F:63:A5:25:F0:E4:5E:73:73:33:E0:3A:FF:79:30` |

O certificado público está em [`signing/waveradar-author.cer`](signing/waveradar-author.cer). A chave privada não faz parte do repositório.

## Conferir o APK

```bash
apksigner verify --print-certs WaveRadar-1.0.0.apk
keytool -printcert -file android/signing/waveradar-author.cer
```

Os dois SHA-256 têm de ser o da tabela acima.

O arquivo publicado `WaveRadar-1.0.0.apk` (release android-v1.0.0) tem SHA-256:

```
387957A64C715F4CB2B84B0A585D914E5BEA40E6AA2D2E368F41533F6198F87F
```

No Windows: `certutil -hashfile WaveRadar-1.0.0.apk SHA256`. No Linux: `sha256sum WaveRadar-1.0.0.apk`.
