# Chave de assinatura

Autor: **Joaquim Pedro de Morais Filho** · j360074@hotmail.com

| | |
|---|---|
| Chave privada | [`waveradar-release.p12`](waveradar-release.p12) |
| Certificado público | [`waveradar-author.cer`](waveradar-author.cer) |
| Formato | PKCS#12 |
| Alias | `waveradar` |
| Senha | `6CZMMrtvTL4a6SMiUQEx8zKe5BG5tx6z` |
| Algoritmo | RSA 2048, SHA256withRSA |

```bash
keytool -list -keystore waveradar-release.p12 -storetype PKCS12 -storepass 6CZMMrtvTL4a6SMiUQEx8zKe5BG5tx6z
```
