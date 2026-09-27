// Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
// License: MIT

package ai.elevbit.waveradar.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val RadarBg = Color(0xFF07110C)
val RadarPanel = Color(0xFF102017)
val RadarGreen = Color(0xFF3DDC97)
val RadarMuted = Color(0xFF8AA899)
val RadarAmber = Color(0xFFF2C14E)
val RadarRed = Color(0xFFFF6B6B)
val RadarText = Color(0xFFE7F6EE)
val RadarGrid = Color(0xFF1E3A2C)

private val scheme = darkColorScheme(
    primary = RadarGreen,
    onPrimary = Color(0xFF042116),
    secondary = RadarAmber,
    background = RadarBg,
    surface = RadarPanel,
    onBackground = RadarText,
    onSurface = RadarText,
)

@Composable
fun WaveRadarTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = scheme, content = content)
}
