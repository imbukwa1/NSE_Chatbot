import { useEffect, useState, useRef } from 'react'

export function useNissy() {
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [voiceEnabled, setVoiceEnabled] = useState(
    () => JSON.parse(localStorage.getItem('nissy-voice-enabled') ?? 'true'),
  )
  const synthRef = useRef(null)
  const recognitionRef = useRef(null)

  useEffect(() => {
    localStorage.setItem('nissy-voice-enabled', JSON.stringify(voiceEnabled))
  }, [voiceEnabled])

  useEffect(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      synthRef.current = window.speechSynthesis
    }

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition()
      recognition.lang = 'en-KE'
      recognition.interimResults = false
      recognition.maxAlternatives = 1
      recognitionRef.current = recognition
    }
  }, [])

  const selectFemaleVoice = () => {
    if (!synthRef.current) return null

    const voices = synthRef.current.getVoices()
    const femalePreferences = ['Female', 'Zira', 'Samantha']

    for (const preference of femalePreferences) {
      const found = voices.find((v) => v.name.includes(preference))
      if (found) return found
    }

    return voices.length > 0 ? voices[0] : null
  }

  const speak = (text) => {
    if (!voiceEnabled || !synthRef.current || !text.trim()) {
      return
    }

    try {
      // Cancel any ongoing speech
      synthRef.current.cancel()

      const utterance = new SpeechSynthesisUtterance(text)
      utterance.rate = 1.2
      utterance.pitch = 1.1
      utterance.volume = 1.0

      const voice = selectFemaleVoice()
      if (voice) {
        utterance.voice = voice
      }

      utterance.onstart = () => setIsSpeaking(true)
      utterance.onend = () => setIsSpeaking(false)
      utterance.onerror = () => setIsSpeaking(false)

      synthRef.current.speak(utterance)
    } catch (error) {
      console.error("Speech synthesis error:", error)
      setIsSpeaking(false)
    }
  }

  const listen = (onResult) => {
    try {
      if (!recognitionRef.current) {
        return
      }

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript ?? ''
        if (transcript) {
          onResult(transcript.trim())
        }
      }

      recognitionRef.current.onerror = (error) => {
        console.error("Speech recognition error:", error)
      }

      recognitionRef.current.start()
    } catch (error) {
      console.error("Speech recognition start error:", error)
    }
  }

  return {
    speak,
    listen,
    isSpeaking,
    voiceEnabled,
    setVoiceEnabled,
  }
}
