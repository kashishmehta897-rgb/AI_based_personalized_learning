from faster_whisper import WhisperModel

audio_path = r"D:\AI_Personalized_Learning\test_hindi.wav"

print("Loading Whisper model...")

model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)

print("Transcribing DBMS Hindi video...")

segments, info = model.transcribe(
    audio_path,
    beam_size=1,
    vad_filter=True,
    language="hi"
)

print("\n--- DBMS HINDI TRANSCRIPT ---\n")

print("Detected language:", info.language)
print("Language probability:", info.language_probability)

for segment in segments:
    print(
        f"[{segment.start:.2f}s - {segment.end:.2f}s] "
        f"{segment.text}"
    )

print("\n--- TRANSCRIPTION COMPLETE ---")