# Weld Quality Monitoring using Deep Learning and Embedded Systems

## Overview
This project presents an **industry‑grade weld quality monitoring system** that combines an existing **embedded signal‑processing pipeline (STM32 + MATLAB)** with a **deep‑learning‑based computer vision module** for automatic weld defect classification. The system demonstrates a complete **Industry 4.0 workflow**: data acquisition → analytics → model training → evaluation → deployment via a web application.

### Key Highlights
- Real‑time signal analysis (FFT / RMS) on STM32 as a baseline system  
- Image‑based weld defect classification using **ResNet‑18 (transfer learning + fine‑tuning)**  
- Thorough experimental evaluation (baseline vs fine‑tuned models)  
- **Streamlit web app** for live image upload and prediction  

---

## Existing System (Embedded + Signal Processing)

The original system focuses on **real‑time weld monitoring** using electrical signals.

### Hardware & Tools
- STM32 microcontroller  
- MATLAB for signal generation and analysis  

### Methodology
- Current and voltage signal acquisition  
- Feature extraction using **FFT, RMS, and statistical thresholds**  
- Rule‑based detection of weld anomalies  

This module establishes a reliable **baseline industrial solution**, which is later extended with AI‑based vision.

---

## Dataset

**RIAWELC – Radiographic Images for Automatic Weld Defect Classification**

- Total images: **24,407**
- Image size: **224×224 (8‑bit, PNG, grayscale)**
- Data split:
  - Training: 15,863
  - Validation: 6,101
  - Testing: 2,443
- Defect classes:
  - Crack
  - Lack of Penetration
  - Porosity
  - No Defect

### References
- Totino et al., *RIAWELC: A Novel Dataset of Radiographic Images for Automatic Weld Defects Classification*, ICMECE 2022  
- Perri et al., *Welding Defects Classification Through a Convolutional Neural Network*, Manufacturing Letters (Elsevier)  

---

## Deep Learning Methodology

### Model Architecture
- **ResNet‑18**, pretrained on ImageNet  
- Grayscale radiographic images converted to 3‑channel input  
- Output layer modified for 4 weld defect classes  

### Training Strategy

**Experiment 1 – Baseline (Feature Extraction)**  
- Frozen ResNet backbone  
- Only final classifier layer trained  

**Experiment 2 – Fine‑tuning**  
- Unfreezing of `layer4` and classifier  
- Low learning rate for stable convergence  

### Preprocessing
- Resize to 224×224  
- ImageNet normalization  
- Data augmentation (rotation, horizontal flip)  

---

## Experiments & Results

### Model Comparison

| Experiment | Training Strategy | Best Validation Accuracy | Test Accuracy |
|---------|------------------|--------------------------|---------------|
| ResNet‑18 Baseline | Frozen backbone + classifier | 71.96% | 72.37% |
| ResNet‑18 Fine‑tuned | Layer4 + classifier | **98.10%** | **98.69%** |

### Key Observations
- Fine‑tuning significantly improves generalization on radiographic weld images  
- Porosity and Crack confusion observed in the baseline is largely resolved  
- Fine‑tuned model achieves **macro F1 ≈ 98.7%**  

All training curves, confusion matrices, and CSV reports are available in `ml_vision/results/`.

---

## Web Application (Streamlit)

A **Streamlit‑based web application** is developed to demonstrate real‑time inference.

### Features
- Upload radiographic weld images  
- Predict defect class with confidence score  
- PASS / FAIL decision logic  
- Class probability table and bar chart  

### Decision Rule
- `No_defect` → PASS  
- `Crack`, `Porosity`, `Lack_of_penetration` → FAIL  

Demo screenshots are available in `ml_vision/results/app_demo/`.

**How to run the App**

cd ml_vision/app
pip install -r requirements.txt
streamlit run app.py

---

## Folder Structure

```text
weld-quality-monitor/
├── stm32/                  # Embedded firmware
├── lab_validation/         # Hardware & lab tests
├── ml_vision/
│   ├── app/                # Streamlit app
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── resnet18_weld_finetuned_best.pth
│   └── results/            # ML results & screenshots
│       ├── app_demo/
│       ├── *.png
│       └── *.csv
├── Python Dashboard/
└── README.md
