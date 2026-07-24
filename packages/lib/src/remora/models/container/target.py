from remora.models.container.extension.audio import SafeAudioExtensionStr
from remora.models.container.extension.video import SafeVideoExtensionStr
from remora.models.container.format import FormatType

FormatTargetType = FormatType | SafeAudioExtensionStr | SafeVideoExtensionStr
"""Collection of standard and safe extension formats."""
