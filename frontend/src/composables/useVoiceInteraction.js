import { computed, ref } from 'vue'
import { useVoiceStore } from '@/store/modules/voice.js'

/** 模块级单例，保证各页面/GlobalVoice 共享同一语音状态 */
const agentState = ref('listening')

export function useVoiceInteraction() {
  const voiceStore = useVoiceStore()

  const showVoiceLayer = computed(() => {
    const status = voiceStore.status
    return (
      status === 'recording' ||
      status === 'processing' ||
      status === 'speaking' ||
      !!voiceStore.displayText
    )
  })

  const isVoiceActive = showVoiceLayer

  function onRecordStart() {
    voiceStore.setStatus('recording')
    agentState.value = 'listening'
    uni.vibrateShort({ type: 'light' })
  }

  function onRecordStop() {
    voiceStore.setStatus('processing')
    agentState.value = 'thinking'

    setTimeout(() => {
      voiceStore.setAsrText('明天下午3点开会', true)
      agentState.value = 'listening'
    }, 800)

    setTimeout(() => {
      agentState.value = 'speaking'
      voiceStore.setStatus('speaking')
    }, 2000)

    setTimeout(() => {
      voiceStore.reset()
      agentState.value = 'listening'
    }, 3500)
  }

  return {
    voiceStore,
    agentState,
    showVoiceLayer,
    isVoiceActive,
    onRecordStart,
    onRecordStop
  }
}
