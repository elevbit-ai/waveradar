// WaveRadar — Android presence screen.
// Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
// License: MIT

package ai.elevbit.waveradar

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import ai.elevbit.waveradar.ui.RadarScreen
import ai.elevbit.waveradar.ui.WaveRadarTheme

class MainActivity : ComponentActivity() {

    private val prefs by lazy { getSharedPreferences(PREFS, MODE_PRIVATE) }

    private val permissions = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { startSensingIfAllowed() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        RadarBus.engine.presenceHoldSec = prefs.getInt(KEY_HOLD, 30).toDouble()
        setContent {
            WaveRadarTheme {
                RadarScreen(
                    initialConsent = prefs.getBoolean(KEY_CONSENT, false),
                    initialHold = prefs.getInt(KEY_HOLD, 30),
                    onConsent = {
                        prefs.edit().putBoolean(KEY_CONSENT, true).apply()
                        askPermissions()
                    },
                    onHold = { seconds ->
                        prefs.edit().putInt(KEY_HOLD, seconds).apply()
                        RadarBus.engine.presenceHoldSec = seconds.toDouble()
                    },
                    onStart = { askPermissions() },
                    onStop = {
                        stopService(android.content.Intent(this, SensingService::class.java))
                    },
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        if (prefs.getBoolean(KEY_CONSENT, false)) startSensingIfAllowed()
    }

    private fun askPermissions() {
        val needed = ArrayList<String>()
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            needed.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED
        ) {
            needed.add(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        if (needed.isEmpty()) startSensingIfAllowed() else permissions.launch(needed.toTypedArray())
    }

    private fun startSensingIfAllowed() {
        if (!prefs.getBoolean(KEY_CONSENT, false)) return
        SensingService.start(this)
    }

    companion object {
        const val PREFS = "waveradar"
        const val KEY_CONSENT = "consent"
        const val KEY_HOLD = "hold_sec"
    }
}
