// WaveRadar — read the RSSI of the network this phone is associated with.
// Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
// License: MIT

package ai.elevbit.waveradar.sensing

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.wifi.WifiInfo
import android.net.wifi.WifiManager
import android.os.Build

data class LinkSnapshot(
    val online: Boolean,
    val rssiDbm: Int = -127,
    val ssid: String? = null,
    val frequencyMhz: Int = 0,
)

class WifiLinkReader(context: Context) {
    private val app = context.applicationContext
    private val wifi = app.getSystemService(WifiManager::class.java)
    private val connectivity = app.getSystemService(ConnectivityManager::class.java)

    fun read(): LinkSnapshot {
        val network = connectivity.activeNetwork ?: return LinkSnapshot(online = false)
        val caps = connectivity.getNetworkCapabilities(network) ?: return LinkSnapshot(online = false)
        if (!caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
            return LinkSnapshot(online = false)
        }

        var rssi = Int.MIN_VALUE
        var ssid: String? = null
        var frequency = 0

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val info = caps.transportInfo as? WifiInfo
            if (info != null) {
                rssi = info.rssi
                ssid = cleanSsid(info.ssid)
                frequency = info.frequency
            }
        }

        @Suppress("DEPRECATION")
        val legacy = wifi.connectionInfo
        if (!validRssi(rssi) && legacy != null) rssi = legacy.rssi
        if (ssid == null && legacy != null) ssid = cleanSsid(legacy.ssid)
        if (frequency == 0 && legacy != null) frequency = legacy.frequency

        if (!validRssi(rssi)) return LinkSnapshot(online = false, ssid = ssid)
        return LinkSnapshot(
            online = true,
            rssiDbm = rssi,
            ssid = ssid,
            frequencyMhz = frequency,
        )
    }

    private fun validRssi(rssi: Int): Boolean = rssi in -120..-20

    private fun cleanSsid(raw: String?): String? {
        if (raw.isNullOrBlank()) return null
        val name = raw.trim().trim('"')
        if (name.isEmpty() || name == "<unknown ssid>" || name == "unknown ssid" || name == "0x") {
            return null
        }
        return name
    }
}
