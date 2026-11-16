# CSI model-input contract

All CSI parsing entry points use `tools/csi_processing.py`. It removes the ESP32 `first_word_invalid` IQ pair before deriving either amplitude or phase, ensuring identical first-word handling across feature extraction, cleaning, validation, comparison, and null-subcarrier analysis scripts.

Packet timestamps must be strictly increasing, have robust interval jitter no greater than 25%, and contain no gap above 2.5 times the median interval. Digital filters use `1 / median(packet_interval)`; no fixed fallback sampling rate is valid for production input.

The 22-column matrix is primarily **amplitude-derived**: PC1/PC2 time statistics, PC1 spectral features, active-subcarrier variance dispersion, and RSSI dynamics. Phase is parsed for analysis but is not part of `extracted_features.csv`.

The model input uses **1.5-second windows** and a **0.5-second step** (66.7% overlap). Exact sample counts are derived from the validated recording rate.

PCA axes, centering, and normalization are fitted transformations. Fit `tools/model_transforms.py:FittedCSITransform` on training data only, save it with `transform.save('artifacts/csi_transform.npz')`, and load the same artifact during inference with `FittedCSITransform.load(...)`. Persist the active-subcarrier mask and filter/window metadata alongside the artifact. Fitting these independently on an inference recording changes feature meaning and can flip PCA orientation.
