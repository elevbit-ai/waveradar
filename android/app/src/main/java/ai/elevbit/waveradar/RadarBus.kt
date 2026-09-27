// WaveRadar — process-local state shared by the service and the screen.
// Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
// License: MIT

package ai.elevbit.waveradar

import ai.elevbit.waveradar.dsp.MotionEngine
import ai.elevbit.waveradar.dsp.MotionState
import ai.elevbit.waveradar.sensing.LinkSnapshot
import kotlinx.coroutines.flow.MutableStateFlow

object RadarBus {
    val engine = MotionEngine()
    val motion = MutableStateFlow(MotionState())
    val link = MutableStateFlow(LinkSnapshot(online = false))
    val running = MutableStateFlow(false)

    fun publish(state: MotionState, snapshot: LinkSnapshot) {
        motion.value = state
        link.value = snapshot
    }

    fun publishOffline() {
        link.value = LinkSnapshot(online = false)
    }

    fun recalibrate() {
        engine.reset()
        motion.value = engine.state()
    }
}
