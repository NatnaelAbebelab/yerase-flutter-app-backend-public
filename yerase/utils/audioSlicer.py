import os
import logging
import librosa
import uuid
import soundfile as sf
from django.conf import settings

logger = logging.getLogger(__name__)

class AudioSlicer:
    @staticmethod
    def slice_audio_with_librosa(audio_path, file_ext="wav"):
        """
        Slice an audio file from 40% to 60% of its duration using librosa and save as WAV.

        Args:
            audio_path (str): Path to the input audio file.
            file_ext (str): Input file extension (output is always WAV).

        Returns:
            str: Path to the saved audio slice (WAV format).

        Raises:
            ValueError: If the input file format is unsupported or processing fails.
        """
        # Supported input formats for librosa
        supported_formats = {'wav', 'flac', 'ogg', 'mp3'}
        input_ext = file_ext.lower()
        if input_ext not in supported_formats:
            raise ValueError(f"Unsupported input audio format: {input_ext}. Supported formats: {supported_formats}")

        try:
            # Load audio file
            audio, sr = librosa.load(audio_path, sr=None, mono=True)
        except Exception as e:
            raise ValueError(f"Failed to load audio file: {e}")

        # Calculate audio duration in milliseconds
        audio_length_ms = len(audio) * 1000 / sr
        min_length_ms = 30 * 1000  # 30 seconds
        max_length_ms = 2 * 60 * 1000  # 2 minutes

        # Calculate 40% to 60% slice
        start_ms = int(audio_length_ms * 0.40)
        end_ms = int(audio_length_ms * 0.60)
        slice_length_ms = end_ms - start_ms

        # Enforce length constraints
        if slice_length_ms < min_length_ms:
            end_ms = min(start_ms + min_length_ms, int(audio_length_ms))
        elif slice_length_ms > max_length_ms:
            end_ms = start_ms + max_length_ms

        # Convert to samples
        start_samples = int(start_ms * sr / 1000)
        end_samples = int(end_ms * sr / 1000)
        chunk = audio[start_samples:end_samples]

        # Prepare output directory
        output_dir = os.path.join(settings.MEDIA_ROOT, "audiobook", "audiobook-sliced-audio")
        os.makedirs(output_dir, exist_ok=True)

        # Save the chunk as WAV
        sliced_audio_file_name = f"{uuid.uuid4()}.wav"
        sliced_audio_path = os.path.join(output_dir, sliced_audio_file_name)
        try:
            sf.write(sliced_audio_path, chunk, sr, subtype='PCM_16')
        except Exception as e:
            raise ValueError(f"Failed to save audio chunk: {e}")

        return sliced_audio_path