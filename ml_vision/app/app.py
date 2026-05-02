import streamlit as st
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import cv2
import csv
import io
from datetime import datetime

# ======================================================
# Streamlit Page Config
# ======================================================
st.set_page_config(
    page_title="Weld Defect Classification System",
    page_icon="🛠️",
    layout="wide"
)

# ======================================================
# Sidebar
# ======================================================
with st.sidebar:
    st.title("⚙️ Settings")

    show_gradcam = st.toggle("🔥 Show Grad-CAM Heatmap", value=True)
    show_history = st.toggle("📋 Show Prediction History", value=True)

    st.divider()
    st.subheader("ℹ️ Model Info")
    st.markdown("""
    - **Model:** ResNet-18 (Fine-tuned)
    - **Dataset:** RIAWELC
    - **Test Accuracy:** 98.69%
    - **Classes:** 4
    """)

    st.subheader("📋 Defect Types")
    st.markdown("""
    - 🔴 **Crack** — Linear fracture
    - 🟠 **Lack of Penetration** — Incomplete fusion
    - 🟡 **Porosity** — Gas pockets
    - ✅ **No Defect** — Acceptable weld
    """)

    st.divider()
    if st.button("🔄 Clear Cache & Reload Model"):
        st.cache_resource.clear()
        st.rerun()

    if st.button("🗑️ Clear Prediction History"):
        st.session_state.history = []
        st.session_state.processed_files = set()
        st.rerun()

# ======================================================
# Header
# ======================================================
st.title("🛠️ AI-Based Weld Defect Classification System")
st.caption("⚠️ AI-generated content may be incorrect. For industrial QA validation only.")
st.write(
    "Upload **single or multiple weld radiographic X-ray images**.\n\n"
    "❌ Natural photos, screenshots, or colored images are rejected."
)
st.divider()

# ======================================================
# Constants
# ======================================================
CLASSES = ["Crack", "Lack_of_penetration", "No_defect", "Porosity"]

CLASS_EMOJI = {
    "Crack": "🔴",
    "Lack_of_penetration": "🟠",
    "No_defect": "✅",
    "Porosity": "🟡"
}

CONFIDENCE_THRESHOLD = 0.70

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "resnet18_weld_finetuned_best.pth"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ======================================================
# Session State — Prediction History + Processed Files
# ======================================================
if "history" not in st.session_state:
    st.session_state.history = []

# Track processed files to avoid duplicate entries on Streamlit re-runs
if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()

# ======================================================
# Load Model
# ======================================================
@st.cache_resource
def load_model():
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 4)
    checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    else:
        model.load_state_dict(checkpoint)
    model.to(DEVICE)
    model.eval()
    return model

model = load_model()

# ======================================================
# Input Validation
# ======================================================
def is_reasonable_input(img: Image.Image) -> bool:
    np_img = np.array(img)

    # Reject colored images
    if len(np_img.shape) == 3:
        r = np_img[:, :, 0].astype(float)
        g = np_img[:, :, 1].astype(float)
        b = np_img[:, :, 2].astype(float)
        color_diff = np.mean(np.abs(r - g)) + np.mean(np.abs(r - b))
        if color_diff > 10:
            return False

    # Reject flat/empty images
    gray = np_img if len(np_img.shape) == 2 else np.mean(np_img, axis=2)
    if np.std(gray) < 2:
        return False

    return True

# ======================================================
# Preprocessing
# ======================================================
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# ======================================================
# Grad-CAM Implementation
# ======================================================
class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_full_backward_hook(backward_hook)

    def generate(self, input_tensor, class_idx):
        self.model.zero_grad()
        output = self.model(input_tensor)
        loss = output[0, class_idx]
        loss.backward()

        # Pool gradients
        pooled_gradients = torch.mean(self.gradients, dim=[0, 2, 3])
        activations = self.activations[0]

        # Weight activations
        for i in range(activations.shape[0]):
            activations[i, :, :] *= pooled_gradients[i]

        heatmap = torch.mean(activations, dim=0).cpu().numpy()
        heatmap = np.maximum(heatmap, 0)

        # Normalize
        if heatmap.max() != 0:
            heatmap /= heatmap.max()

        return heatmap


def apply_gradcam_overlay(original_img: Image.Image, heatmap: np.ndarray) -> np.ndarray:
    """Overlay Grad-CAM heatmap on original image"""
    img_array = np.array(original_img.convert("RGB").resize((224, 224)))

    # Resize heatmap to image size
    heatmap_resized = cv2.resize(heatmap, (224, 224))

    # Apply colormap
    heatmap_colored = cm.jet(heatmap_resized)[:, :, :3]
    heatmap_colored = (heatmap_colored * 255).astype(np.uint8)

    # Overlay
    overlay = (0.55 * img_array + 0.45 * heatmap_colored).astype(np.uint8)
    return overlay


# ======================================================
# Confidence Meter (Visual Progress Bar)
# ======================================================
def show_confidence_meter(confidence: float, pred_class: str):
    emoji = CLASS_EMOJI.get(pred_class, "")
    color = "green" if pred_class == "No_defect" else "red"
    pct = int(confidence * 100)

    st.markdown(f"**{emoji} Predicted Class:** `{pred_class}`")
    st.markdown(f"**Model Confidence:** `{pct}%`")
    st.progress(float(confidence), text=f"{pct}% confidence")

    if pct >= 90:
        st.markdown(f":{'green' if pred_class == 'No_defect' else 'red'}[{'✅ HIGH CONFIDENCE — Strong prediction' if pred_class == 'No_defect' else '🔴 HIGH CONFIDENCE DEFECT — Reject weld'}]")
    elif pct >= 70:
        st.markdown(f":orange[⚠️ MODERATE CONFIDENCE — Review recommended]")
    else:
        st.markdown(f":red[❌ LOW CONFIDENCE — Manual inspection required]")


# ======================================================
# Prediction History CSV Download
# ======================================================
def generate_csv_report(history: list) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "Timestamp", "Filename", "Predicted_Class",
        "Confidence_%", "Result",
        "Crack_%", "Lack_of_penetration_%", "No_defect_%", "Porosity_%"
    ])
    writer.writeheader()
    for record in history:
        writer.writerow(record)
    return output.getvalue().encode()


# ======================================================
# Single Image Inference
# ======================================================
def run_inference(image: Image.Image, filename: str):
    """Run full inference pipeline on one image"""

    # Validation
    if not is_reasonable_input(image):
        st.error(
            "❌ **INVALID INPUT** — This image does not look like a weld radiographic X-ray.\n\n"
            "Please upload a grayscale weld X-ray image."
        )
        return

    col1, col2 = st.columns(2)

    with col1:
        st.image(image, caption=f"📷 Input: {filename}", use_container_width=True)

    # Inference
    with st.spinner("🤖 Analyzing..."):
        input_tensor = transform(image.convert("RGB")).unsqueeze(0).to(DEVICE)

        # Standard inference
        with torch.no_grad():
            output = model(input_tensor)
            probs = F.softmax(output, dim=1).cpu().numpy()[0]

        pred_idx = int(np.argmax(probs))
        pred_class = CLASSES[pred_idx]
        confidence = probs[pred_idx]

        # Grad-CAM (needs grad)
        if show_gradcam:
            gradcam = GradCAM(model, model.layer4[-1])
            input_tensor_grad = transform(image.convert("RGB")).unsqueeze(0).to(DEVICE)
            input_tensor_grad.requires_grad_(True)
            heatmap = gradcam.generate(input_tensor_grad, pred_idx)
            overlay = apply_gradcam_overlay(image, heatmap)

    # Show Grad-CAM
    if show_gradcam:
        with col2:
            st.image(overlay, caption="🔥 Grad-CAM — Model attention heatmap", use_container_width=True)
            st.caption("Red/Yellow = Model focused here | Blue = Less attention")

    st.divider()

    # Result
    st.subheader("🎯 Prediction Result")

    if confidence >= CONFIDENCE_THRESHOLD:
        if pred_class == "No_defect":
            st.success(f"✅ **PASS** — No weld defect detected")
        else:
            st.error(f"❌ **FAIL** — {CLASS_EMOJI[pred_class]} {pred_class.replace('_', ' ')} detected")
    else:
        st.warning("⚠️ **UNCERTAIN** — Low confidence. Manual inspection recommended.")

    # Confidence meter
    show_confidence_meter(confidence, pred_class)

    st.caption("Confidence = model's predicted probability, not absolute certainty.")

    # Probability bar chart
    st.subheader("📊 Class Probabilities")

    prob_col1, prob_col2 = st.columns([1, 2])

    with prob_col1:
        st.table({
            "Class": [f"{CLASS_EMOJI[c]} {c}" for c in CLASSES],
            "Probability (%)": [f"{p*100:.2f}" for p in probs]
        })

    with prob_col2:
        fig, ax = plt.subplots(figsize=(6, 3))
        colors = ['#2ecc71' if c == "No_defect" else
                  '#e74c3c' if c == pred_class else '#3498db'
                  for c in CLASSES]
        bars = ax.bar(CLASSES, probs, color=colors)
        ax.set_ylim(0, 1.1)
        ax.set_ylabel("Probability")
        ax.set_title("Prediction Probabilities")
        ax.axhline(y=CONFIDENCE_THRESHOLD, color='orange', linestyle='--',
                   linewidth=1.5, label=f'Threshold ({CONFIDENCE_THRESHOLD})')
        for bar, p in zip(bars, probs):
            ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.02,
                    f'{p*100:.1f}%', ha='center', va='bottom', fontsize=8)
        ax.legend(fontsize=8)
        plt.xticks(rotation=15, ha='right', fontsize=8)
        plt.tight_layout()
        st.pyplot(fig)

    # Save to history — only if not already processed this session
    result_label = "PASS" if pred_class == "No_defect" else (
        "UNCERTAIN" if confidence < CONFIDENCE_THRESHOLD else "FAIL"
    )

    # Unique key = filename + size (prevents duplicate on re-run)
    file_key = f"{filename}_{confidence:.6f}"
    if file_key not in st.session_state.processed_files:
        st.session_state.processed_files.add(file_key)
        st.session_state.history.append({
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Filename": filename,
            "Predicted_Class": pred_class,
            "Confidence_%": f"{confidence*100:.2f}",
            "Result": result_label,
            "Crack_%": f"{probs[0]*100:.2f}",
            "Lack_of_penetration_%": f"{probs[1]*100:.2f}",
            "No_defect_%": f"{probs[2]*100:.2f}",
            "Porosity_%": f"{probs[3]*100:.2f}"
        })


# ======================================================
# File Upload — BATCH SUPPORT
# ======================================================
uploaded_files = st.file_uploader(
    "📤 Upload weld radiographic image(s)",
    type=["png", "jpg", "jpeg", "bmp", "tiff"],
    accept_multiple_files=True
)

if uploaded_files:
    st.markdown(f"**{len(uploaded_files)} image(s) uploaded**")
    st.divider()

    # Latest uploaded file appears at top
    reversed_files = uploaded_files[::-1]
    for i, uploaded_file in enumerate(reversed_files):
        if len(uploaded_files) > 1:
            st.subheader(f"📁 Image {len(uploaded_files) - i}: `{uploaded_file.name}`")

        image = Image.open(uploaded_file)
        run_inference(image, uploaded_file.name)

        if i < len(uploaded_files) - 1:
            st.divider()

else:
    st.info("👆 Upload one or more weld radiographic X-ray images to begin analysis.")


# ======================================================
# Prediction History
# ======================================================
if show_history and st.session_state.history:
    st.divider()
    st.subheader("📋 Prediction History (This Session)")

    history = st.session_state.history

    # Summary stats
    total = len(history)
    passed = sum(1 for h in history if h["Result"] == "PASS")
    failed = sum(1 for h in history if h["Result"] == "FAIL")
    uncertain = sum(1 for h in history if h["Result"] == "UNCERTAIN")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Inspected", total)
    m2.metric("✅ Passed", passed)
    m3.metric("❌ Failed", failed)
    m4.metric("⚠️ Uncertain", uncertain)

    # History table — latest first
    st.table(list(reversed(history)))

    # Download CSV Report
    csv_data = generate_csv_report(history)
    st.download_button(
        label="📥 Download Full Report (CSV)",
        data=csv_data,
        file_name=f"weld_inspection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
