from remora.models.container.codec.audio import AudioCodec, AudioCodecFamily
from remora.models.container.codec.video import VideoCodec, VideoCodecFamily

Codec = AudioCodec | VideoCodec
CodecFamily = VideoCodecFamily | AudioCodecFamily
