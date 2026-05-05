# AI-Enhanced Weld Quality Monitoring
### STM32 + MATLAB Signal Monitoring Extended with ResNet-18 Radiographic Defect Classification

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-orange)](https://pytorch.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)](https://streamlit.io)
[![Accuracy](https://img.shields.io/badge/Test%20Accuracy-98.69%25-green)](/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](/)

> **Prototype disclaimer**: This is a Master's-level research prototype.
> The 98.69% accuracy is in-distribution performance on the controlled RIAWELC dataset.
> Real-world industrial deployment requires further validation, calibration, and testing.

---

## Project Overview

This project is a **hybrid weld quality monitoring prototype** with two complementary layers:

```

LAYER 1 — STM32 + MATLAB (Real-time Signal Monitoring) 
Current & Voltage → FFT / RMS / Peak Detection 
Detects: Spatter, Burn-through, Arc Instability, 
Porosity-like signal behaviour 
Latency: < 10ms | Sample Rate: 10 kHz 

Layer 1 detects anomalies but
cannot classify internal defect type
↓

LAYER 2 — ResNet-18 (Radiographic Classification) 
X-ray images → 4-class defect classification 
Classes: Crack | LoP | Porosity | No Defect 
Accuracy: 98.69% (in-distribution, RIAWELC dataset) 

```

**Layer 2 is an extension of Layer 1, not a replacement.**
Signal monitoring handles real-time process anomalies.
Image classification handles post-process structural defect identification.

---

## Key Results

| Experiment | Strategy | Val Accuracy | Test Accuracy |
|------------|----------|-------------|---------------|
| Baseline ResNet-18 | Frozen backbone | 71.96% | 72.37% |
| **Fine-tuned ResNet-18** | layer4 + classifier | **98.10%** | **98.69%** |

**Key finding**: Transfer learning alone (frozen backbone) was not enough.
Fine-tuning was critical for adapting to radiographic weld X-ray domain.

---

## Dataset — RIAWELC
## Random photos from google photos for testing 

**Radiographic Images for Automatic Weld Defect Classification**

| Property | Value |
|----------|-------|
| Total images | 24,407 |
| Image type | Grayscale radiographic X-ray |
| Image size | 224 × 224 pixels |
| Training | 15,863 |
| Validation | 6,101 |
| Test | 2,443 |
| Classes | Crack, Lack of Penetration, Porosity, No Defect |
| Evaluation | In-distribution (controlled dataset) |

> Dataset source: Totino et al., ICMECE 2022 — [Mendeley Data](https://data.mendeley.com/datasets/rrm9zbhnyd/1)

---

## Streamlit Web Application

### Features

| Feature | Description |
|---------|-------------|
| Batch upload | Single or multiple weld X-ray images |
| ResNet-18 inference | Predict class + confidence score |
| PASS / FAIL / UNCERTAIN | Confidence threshold: 70% |
| Grad-CAM heatmap | Model attention visualization per image |
| Confidence meter | Visual progress bar with HIGH/MODERATE/LOW labels |
| Prediction history | Session-based table with summary stats |
| CSV report download | Timestamped full session log |
| OOD input validation | Rejects charts, photos, screenshots automatically |
| Latest-first ordering | Most recent upload shown at top |

### Decision Logic

```
Confidence ≥ 90% → HIGH CONFIDENCE → PASS or FAIL 
Confidence 70–90% → MODERATE → PASS or FAIL (review recommended)
Confidence < 70% → UNCERTAIN → Manual inspection required
```

### Input Validation (OOD Detection)

The app uses two lightweight checks to reject invalid inputs:

```python
# Check 1: Reject colored images (photos, colored charts, UI screenshots)
if color_diff > 15:
reject → "Colored image detected"

# Check 2: Reject charts/documents (white background > 95%)
if white_ratio > 0.95:
reject → "Too much white background — likely a chart or document"
```

**Why this matters**: A CNN classifier always predicts one of its known classes,
even for completely invalid inputs (charts, timetables, hardware photos).
High test accuracy does not automatically mean the system handles real-world inputs correctly.

---

## Grad-CAM Explainability

Grad-CAM (Gradient-weighted Class Activation Mapping) is used to visualize which image regions influenced each prediction.

| Class | Model focuses on |
|-------|-----------------|
| Crack | Linear fracture line region |
| Lack of Penetration | Horizontal dark band |
| Porosity | Dark circular blob regions |
| No Defect | Diffused attention (no specific feature) |

> Grad-CAM is an explanation tool, not a defect localization method.

---

## STM32 + MATLAB Layer (Layer 1)

### Hardware
- STM32F446RE Nucleo microcontroller
- Rigol DG4162 function generator (signal simulation)
- Rigol DS2202A oscilloscope (200MHz, signal validation)
- UART at 115200 baud

### Signal Processing Features

| Feature | Purpose | Detects |
|---------|---------|---------|
| FFT | Frequency-domain analysis | Arc instability patterns |
| Moving RMS | Energy-based detection | Burn-through tendency |
| Peak detection | Current spike detection | Spatter |
| Voltage dips | Arc disturbance detection | Porosity-like behaviour |
| Statistical thresholds | Anomaly decision logic | General abnormal events |

### Performance (HIL Simulation)
- Sampling rate: **10 kHz** (captures micro-transients invisible to standard PLCs)
- Latency: **< 10ms**
- All 4 defect signatures validated across thousands of data points

---

## Limitations

| Limitation | Impact |
|-----------|--------|
| Radiographic X-ray only | Cannot classify RGB surface defects |
| No surface defect detection | Spatter, burnhole, overburn not detectable |
| In-distribution accuracy | Real-world accuracy may be lower |
| No multi-modal fusion | Signal and image layers are separate modules |
| No defect localization | Classification only, no pixel-level segmentation |
| Basic OOD validation | Not a complete out-of-distribution detector |
| No production-line integration | Prototype Streamlit app only |

---

## How to Run

```bash
# Clone repo
git clone https://github.com/pkhan3676/weld-quality-monitor
cd weld-quality-monitor/ml_vision/app

# Install dependencies
pip install -r requirements.txt

# Run app
streamlit run app.py
```

> Make sure `resnet18_weld_finetuned_best.pth` is in the same folder as `app.py`

---

## Folder Structure

```
weld-quality-monitor/
stm32/ # STM32 embedded firmware (C)
lab_validation/ # Hardware setup & lab validation
Python Dashboard/ # Live SCADA dashboard (Streamlit + Plotly + PySerial)
ml_vision/
app/
app.py # Streamlit web app (main)
requirements.txt
resnet18_weld_finetuned_best.pth
results/
app_demo/ # App screenshots
training_curves/ # Loss & accuracy plots
confusion_matrices/ # Baseline & fine-tuned CM
*.csv # Classification reports
README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Embedded | STM32F446RE, C firmware, UART |
| Signal Processing | MATLAB R2025b, Simulink (HIL) |
| Deep Learning | PyTorch, ResNet-18, Transfer Learning |
| Explainability | Grad-CAM |
| Web App | Streamlit, Plotly |
| Dashboard | Python, PySerial, Streamlit |
| Dataset | RIAWELC (Mendeley Data) |

---

## References

1. Totino et al., *RIAWELC: A Novel Dataset of Radiographic Images for Automatic Weld Defects Classification*, ICMECE 2022
2. Perri et al., *Welding Defects Classification Through a Convolutional Neural Network*, Manufacturing Letters, Elsevier
3. He et al., *Deep Residual Learning for Image Recognition*, CVPR 2016
4. Selvaraju et al., *Grad-CAM: Visual Explanations from Deep Networks*, ICCV 2017
5. Hendrycks & Gimpel, *A Baseline for Detecting Misclassified and Out-of-Distribution Examples*, ICLR 2017
6. Ronneberger et al., *U-Net: Convolutional Networks for Biomedical Image Segmentation*, MICCAI 2015

---

## Author

**Prince Khan**
M.Eng. Analytical Instruments, Measurement & Sensor Technology
Hochschule Coburg, Germany 
Exchange Semester: USST Shanghai, China (Mar–Jun 2026)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Prince%20Khan-blue)](https://linkedin.com/in/prince-khan-819695121)
[![GitHub](https://img.shields.io/badge/GitHub-pkhan3676-black)](https://github.com/pkhan3676)
