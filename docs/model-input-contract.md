# CSI model-input contract

All feature extraction uses `tools/csi_processing.py`. It removes the ESP32 `first_word_invalid` IQ pair before deriving either amplitude or phase, ensuring identical first-word handling across entry points.

Packet timestamps must be strictly increasing, have robust interval jitter no greater than 25%, and contain no gap above 2.5 times the median interval. Digital filters use `1 / median(packet_interval)`; no fixed fallback sampling rate is valid for production input.

The 22-column matrix is primarily **amplitude-derived**: PC1/PC2 time statistics, PC1 spectral features, active-subcarrier variance dispersion, and RSSI dynamics. Phase is parsed for analysis but is not part of `extracted_features.csv`.

The model input uses **1.5-second windows** and a **0.5-second step** (66.7% overlap). Exact sample counts are derived from the validated recording rate.

PCA axes, centering, and normalization are fitted transformations. Production inference must persist and reuse the training-time active-subcarrier mask, centering/scaling values, PCA mean/components, filter configuration, and window configuration. Fitting these independently on an inference recording changes feature meaning and can flip PCA orientation.
