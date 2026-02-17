from remora.models._base import RemoraBaseModel


class Metadata(RemoraBaseModel):
    def __bool__(self) -> bool:
        """If all fields are False, the model itself is False."""
        return any(getattr(self, field) for field in type(self).model_fields)
