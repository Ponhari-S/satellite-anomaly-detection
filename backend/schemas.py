"""Pydantic models shared by the HTTP and WebSocket interfaces."""

from pydantic import BaseModel, Field


class FeatureInput(BaseModel):
    """The 19 model features, in the order used when training the baseline."""

    sampling: int
    duration: int
    len: int
    mean: float
    var: float
    std: float
    kurtosis: float
    skew: float
    n_peaks: int
    smooth10_n_peaks: int
    smooth20_n_peaks: int
    diff_peaks: int
    diff2_peaks: int
    diff_var: float
    diff2_var: float
    gaps_squared: int
    len_weighted: int
    var_div_duration: float
    var_div_len: float


class PredictionResponse(BaseModel):
    prediction: int = Field(ge=0, le=1)
    probability: float = Field(ge=0.0, le=1.0)


class StoredResult(PredictionResponse):
    timestamp: str
    channel: str
