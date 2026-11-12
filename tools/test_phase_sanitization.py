import numpy as np

def sanitize_phase(raw_phases):
    """
    Sanitizes raw CSI phase across active subcarriers by removing
    linear phase error caused by Carrier Frequency Offset (CFO),
    Sampling Frequency Offset (SFO), and Packet Detection Delay (PDD).
    
    Formula: theta_clean(k) = theta_unwrapped(k) - (a * k + b)
    where a and b are the linear regression slope and intercept.
    """
    n_frames, n_subs = raw_phases.shape
    sanitized = np.zeros_like(raw_phases)
    k = np.arange(n_subs) # subcarrier indices
    
    for i in range(n_frames):
        unwrapped = np.unwrap(raw_phases[i, :])
        # Linear regression fit across subcarriers
        p = np.polyfit(k, unwrapped, deg=1)
        # Subtract the linear trend
        sanitized[i, :] = unwrapped - (p[0] * k + p[1])
        
    return sanitized
