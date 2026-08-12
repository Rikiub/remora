from remora.models.container.codec.audio import AudioCodecFamily, AudioCodecFamilyStr
from remora.models.container.codec.info import CodecInfo  # noqa: F401
from remora.models.container.codec.video import VideoCodecFamily, VideoCodecFamilyStr

CodecFamily = VideoCodecFamily | AudioCodecFamily
CodecFamilyType = CodecFamily | VideoCodecFamilyStr | AudioCodecFamilyStr
