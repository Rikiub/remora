from remora.models.base import RemoraBaseModel


class Metadata(RemoraBaseModel):
    def __bool__(self) -> bool:
        """If all fields are False, the model itself is False."""
        return any(
            getattr(self, field) is not None for field in type(self).model_fields
        )
