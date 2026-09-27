// WaveRadar — live link display.
// Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
// License: MIT

package ai.elevbit.waveradar.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ai.elevbit.waveradar.BuildConfig
import ai.elevbit.waveradar.RadarBus
import ai.elevbit.waveradar.dsp.Presence
import java.util.Locale
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

private const val CERT_SHA256 =
    "F5:81:EB:8E:53:66:C4:D4:E0:CD:A0:87:C4:D7:48:48:41:0B:B4:B5:C3:6B:40:2A:E4:50:60:E4:95:6B:E8:61"

@Composable
fun RadarScreen(
    initialConsent: Boolean,
    initialHold: Int,
    onConsent: () -> Unit,
    onHold: (Int) -> Unit,
    onStart: () -> Unit,
    onStop: () -> Unit,
) {
    val motion by RadarBus.motion.collectAsStateWithLifecycle()
    val link by RadarBus.link.collectAsStateWithLifecycle()
    val running by RadarBus.running.collectAsStateWithLifecycle()
    var consent by remember { mutableStateOf(initialConsent) }
    var about by remember { mutableStateOf(false) }
    var hold by remember { mutableIntStateOf(initialHold) }

    if (!consent) {
        AlertDialog(
            onDismissRequest = {},
            containerColor = RadarPanel,
            titleContentColor = RadarText,
            textContentColor = RadarMuted,
            title = { Text("Uso na sua própria rede") },
            text = {
                Text(
                    "O WaveRadar lê a intensidade do Wi-Fi (RSSI) do enlace entre este telefone " +
                        "e o roteador ao qual ele está conectado. Movimento no ambiente mexe nesse sinal. " +
                        "Nada é enviado para a internet.\n\n" +
                        "Use somente em um espaço que você administra, com o conhecimento de quem está presente. " +
                        "O app não identifica pessoas, não lista aparelhos vizinhos e não enxerga através da parede.",
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    consent = true
                    onConsent()
                }) { Text("Entendi, começar") }
            },
        )
    }

    if (about) {
        AlertDialog(
            onDismissRequest = { about = false },
            containerColor = RadarPanel,
            titleContentColor = RadarText,
            textContentColor = RadarMuted,
            title = { Text("Autoria") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Joaquim Pedro de Morais Filho", color = RadarText, fontWeight = FontWeight.SemiBold)
                    Text("j360074@hotmail.com")
                    Text("© 2026 · Licença MIT · WaveRadar ${BuildConfig.VERSION_NAME}")
                    Text(
                        "Certificado de release RSA 2048, SHA256withRSA.\n" +
                            "CN=Joaquim Pedro de Morais Filho\n" +
                            "SHA-256\n$CERT_SHA256",
                        fontFamily = FontFamily.Monospace,
                        fontSize = 11.sp,
                    )
                    Text(
                        "O Android não entrega CSI nem ângulo de chegada. O ponto no radar fica no " +
                            "eixo do enlace (telefone no centro, roteador no topo). A distância do ponto " +
                            "é a intensidade do movimento, não metros. Doppler só aparece quando o " +
                            "telefone atualiza o RSSI a pelo menos 8 Hz.",
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = { about = false }) { Text("Fechar") }
            },
        )
    }

    val presence = if (!link.online && motion.samples > 0) null else motion.presence
    val (label, color) = presenceLabel(link.online, presence, motion.samples)

    Scaffold(containerColor = RadarBg) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 12.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("WaveRadar", color = RadarText, fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
                    Text("Presença pelo enlace com o seu roteador", color = RadarMuted, fontSize = 13.sp)
                }
                TextButton(onClick = { about = true }) { Text("Autoria") }
            }
            Spacer(Modifier.height(12.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(RadarPanel, RoundedCornerShape(16.dp))
                    .border(1.dp, color.copy(alpha = 0.45f), RoundedCornerShape(16.dp))
                    .padding(16.dp),
            ) {
                Column {
                    Text(label, color = color, fontSize = 28.sp, fontWeight = FontWeight.Bold)
                    Text(
                        "intensidade ${(motion.score * 100).toInt()}%",
                        color = RadarMuted,
                        fontSize = 13.sp,
                    )
                    Spacer(Modifier.height(8.dp))
                    LinearProgressIndicator(
                        progress = { motion.score.toFloat() },
                        modifier = Modifier.fillMaxWidth().height(6.dp),
                        color = color,
                        trackColor = RadarGrid,
                    )
                    if (motion.presence == Presence.CALIBRATING && link.online) {
                        Spacer(Modifier.height(10.dp))
                        Text(
                            "Calibração ${(motion.calibrationProgress * 100).toInt()}% — deixe o telefone parado e fique imóvel.",
                            color = RadarAmber,
                            fontSize = 13.sp,
                        )
                    }
                }
            }
            Spacer(Modifier.height(14.dp))
            LinkRadar(
                score = motion.score,
                online = link.online,
                modifier = Modifier.fillMaxWidth().height(280.dp),
            )
            Text(
                "Telefone no centro. Roteador no topo. O ponto anda nesse eixo: mais perto do centro, mais movimento. Não é a posição da pessoa.",
                color = RadarMuted,
                fontSize = 12.sp,
                modifier = Modifier.padding(top = 6.dp),
            )
            Spacer(Modifier.height(12.dp))
            MetricRow(link, motion.fps, motion.effectiveHz, motion.dopplerHz, motion.stdDb)
            Spacer(Modifier.height(8.dp))
            RssiTrace(motion.trace, Modifier.fillMaxWidth().height(72.dp))
            if (link.online && motion.calibrationProgress >= 1.0 && motion.effectiveHz < 0.15 && motion.samples > 40) {
                Text(
                    "O RSSI quase não mudou. Ande entre o telefone e o roteador por uns 15 segundos. Se a linha continuar reta, este aparelho está entregando o sinal muito devagar para detectar presença.",
                    color = RadarAmber,
                    fontSize = 12.sp,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }
            if (!link.online) {
                Text(
                    "Conecte o telefone ao Wi-Fi do roteador que você administra. Dados móveis não servem: o enlace medido é o da associação Wi-Fi.",
                    color = RadarAmber,
                    fontSize = 13.sp,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }
            Spacer(Modifier.height(14.dp))
            Text("Retenção de presença", color = RadarMuted, fontSize = 12.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 6.dp)) {
                listOf(15, 30, 60, 120).forEach { seconds ->
                    val selected = hold == seconds
                    OutlinedButton(
                        onClick = {
                            hold = seconds
                            onHold(seconds)
                        },
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.outlinedButtonColors(
                            containerColor = if (selected) RadarGreen.copy(alpha = 0.16f) else Color.Transparent,
                            contentColor = if (selected) RadarGreen else RadarMuted,
                        ),
                    ) { Text("${seconds}s", fontSize = 12.sp) }
                }
            }
            Text(
                "Depois de um movimento, a sala continua como presente até esse tempo. Uma pessoa imóvel por mais tempo pode aparecer como vazio: o RSSI não vê quem está parado.",
                color = RadarMuted,
                fontSize = 12.sp,
                modifier = Modifier.padding(top = 4.dp),
            )
            Spacer(Modifier.height(14.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(
                    onClick = { RadarBus.recalibrate() },
                    modifier = Modifier.weight(1f),
                ) { Text("Recalibrar") }
                Button(
                    onClick = { if (running) onStop() else onStart() },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (running) RadarRed else RadarGreen,
                        contentColor = Color(0xFF042116),
                    ),
                ) { Text(if (running) "Parar" else "Iniciar") }
            }
            Text(
                "Deixe o telefone parado, de preferência carregando, do outro lado do cômodo em relação ao roteador. Joaquim Pedro de Morais Filho · j360074@hotmail.com",
                color = RadarMuted,
                fontSize = 11.sp,
                modifier = Modifier.padding(top = 16.dp, bottom = 12.dp),
            )
        }
    }
}

@Composable
private fun MetricRow(
    link: ai.elevbit.waveradar.sensing.LinkSnapshot,
    fps: Double,
    effectiveHz: Double,
    dopplerHz: Double?,
    stdDb: Double,
) {
    val band = when {
        link.frequencyMhz in 2400..2500 -> "2,4 GHz"
        link.frequencyMhz in 4900..5900 -> "5 GHz"
        link.frequencyMhz > 5900 -> "6 GHz"
        else -> "—"
    }
    val name = link.ssid ?: if (link.online) "Wi-Fi conectado" else "sem enlace"
    val doppler = dopplerHz?.let { String.format(Locale("pt", "BR"), "%.2f Hz", it) } ?: "—"
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(RadarPanel, RoundedCornerShape(12.dp))
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(name, color = RadarText, fontWeight = FontWeight.Medium)
        Text(
            "RSSI ${if (link.online) "${link.rssiDbm} dBm" else "—"}   ·   $band",
            color = RadarGreen,
            fontFamily = FontFamily.Monospace,
            fontSize = 13.sp,
        )
        Text(
            String.format(
                Locale("pt", "BR"),
                "variação %.2f dB   ·   leitura %.1f Hz   ·   RSSI útil %.2f Hz",
                stdDb,
                fps,
                effectiveHz,
            ),
            color = RadarMuted,
            fontFamily = FontFamily.Monospace,
            fontSize = 11.sp,
        )
        Text(
            "Doppler $doppler",
            color = if (dopplerHz == null) RadarMuted else RadarAmber,
            fontFamily = FontFamily.Monospace,
            fontSize = 12.sp,
        )
    }
}

@Composable
private fun LinkRadar(score: Double, online: Boolean, modifier: Modifier = Modifier) {
    Canvas(modifier.background(RadarPanel, RoundedCornerShape(16.dp))) {
        val c = Offset(size.width / 2f, size.height / 2f)
        val radius = min(size.width, size.height) * 0.38f
        for (i in 1..4) {
            drawCircle(
                color = RadarGrid,
                radius = radius * i / 4f,
                center = c,
                style = Stroke(width = 1.5f),
            )
        }
        drawLine(RadarGrid, Offset(c.x, c.y - radius), Offset(c.x, c.y + radius), strokeWidth = 1.5f)
        drawLine(RadarGrid, Offset(c.x - radius, c.y), Offset(c.x + radius, c.y), strokeWidth = 1.5f)
        drawCircle(RadarAmber, radius = 5f, center = c)
        val router = Offset(c.x, c.y - radius)
        drawCircle(RadarGreen, radius = 6f, center = router)
        if (online && score > 0.12) {
            val travel = (0.82 - 0.55 * score).toFloat()
            val blip = Offset(c.x, c.y - radius * travel)
            drawCircle(RadarGreen.copy(alpha = 0.25f), radius = 18f + (score * 10).toFloat(), center = blip)
            drawCircle(RadarGreen, radius = 7f, center = blip)
        }
        val sweep = (System.currentTimeMillis() % 4000L) / 4000.0 * 2.0 * Math.PI
        val end = Offset(
            c.x + radius * sin(sweep).toFloat(),
            c.y - radius * cos(sweep).toFloat(),
        )
        drawLine(RadarGreen.copy(alpha = 0.35f), c, end, strokeWidth = 2f, cap = StrokeCap.Round)
    }
}

@Composable
private fun RssiTrace(trace: List<Double>, modifier: Modifier = Modifier) {
    Canvas(modifier.background(RadarPanel, RoundedCornerShape(12.dp)).padding(8.dp)) {
        if (trace.size < 2) return@Canvas
        val minV = trace.min() - 1.0
        val maxV = trace.max() + 1.0
        val span = (maxV - minV).coerceAtLeast(2.0)
        val path = Path()
        trace.forEachIndexed { i, v ->
            val x = size.width * i / (trace.size - 1).toFloat()
            val y = size.height * (1f - ((v - minV) / span).toFloat())
            if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        drawPath(path, RadarGreen, style = Stroke(width = 2.5f, cap = StrokeCap.Round))
    }
}

private fun presenceLabel(
    online: Boolean,
    presence: Presence?,
    samples: Int,
): Pair<String, Color> {
    if (!online && samples == 0) return "Aguardando Wi-Fi" to RadarAmber
    if (!online) return "Sem enlace" to RadarAmber
    return when (presence) {
        Presence.CALIBRATING -> "Calibrando" to RadarAmber
        Presence.CLEAR -> "Vazio" to RadarMuted
        Presence.PRESENT -> "Presente" to RadarGreen
        Presence.MOVING -> "Em movimento" to RadarGreen
        null -> "Sem enlace" to RadarAmber
    }
}
