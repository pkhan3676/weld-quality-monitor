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
    layout="wide"
)


 
# Constants
 
CLASSES = ["Crack", "Lack_of_penetration", "No_defect", "Porosity"]

CONFIDENCE_THRESHOLD = 0.70

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "resnet18_weld_finetuned_best.pth"

OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

LOG_FILE = OUTPUT_DIR / "predictions.csv"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ======================================================
# Sidebar
# ======================================================
with st.sidebar:
    st.title("Settings")

    show_gradcam = st.toggle("Show Grad-CAM Heatmap", value=True)
    show_history = st.toggle("Show Prediction History", value=True)

    st.divider()

    st.subheader("Model Info")
    st.markdown("""
    - **Model:** ResNet-18 fine-tuned
    - **Dataset:** RIAWELC
    - **Test Accuracy:** 98.69%
    - **Classes:** 4
    """)

    st.caption(
        "In-distribution accuracy on the RIAWELC controlled dataset. "
        "Real-world performance may vary."
    )

    st.subheader("Defect Classes")
    st.markdown("""
    - **Crack** — linear fracture
    - **Lack of Penetration** — incomplete fusion
    - **Porosity** — gas pockets
    - **No Defect** — acceptable weld
    """)

    st.divider()

    if st.button("Clear Cache and Reload Model"):
        st.cache_resource.clear()
        st.rerun()

    if st.button("Clear Prediction History"):
        st.session_state.history = []
        st.session_state.processed_files = set()
        st.rerun()


# ======================================================
# Header
# ======================================================
st.title("AI-Based Weld Defect Classification System")

st.caption(
    "AI-generated content may be incorrect. "
    "Use as a prototype decision-support tool only."
)

st.write(
    "Upload one or more **weld radiographic X-ray images**. "
    "Natural photos, screenshots, colored charts, and documents are rejected."
)

st.divider()


# ======================================================
# Session State
# ======================================================
if "history" not in st.session_state:
    st.session_state.history = []

if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()


# ======================================================
# Load Model
# ======================================================
@st.cache_resource
def load_model():
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, len(CLASSES))

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
# Decision Logic
# ======================================================
def get_decision(pred_class: str, confidence: float) -> str:
    """
    Central decision logic.
    Low confidence always becomes UNCERTAIN.
    """
    if confidence < CONFIDENCE_THRESHOLD:
        return "UNCERTAIN"
    elif pred_class == "No_defect":
        return "PASS"
    else:
        return "FAIL"


# ======================================================
# Persistent CSV Logging
# ======================================================
def append_prediction_to_csv(record: dict):
    """
    Append prediction result to persistent CSV file.
    This does not overwrite old history.
    """
    file_exists = LOG_FILE.exists()

    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Timestamp",
                "Filename",
                "Predicted_Class",
                "Confidence_%",
                "Result",
                "Crack_%",
                "Lack_of_penetration_%",
                "No_defect_%",
                "Porosity_%"
            ]
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(record)


# ======================================================
# Input Validation
# ======================================================
def is_reasonable_input(img: Image.Image) -> tuple:
    """
    Minimal practical validation:
    - reject strongly colored images
    - reject blank images
    - reject document/chart-like mostly white images
    - reject mostly black screenshots
    """

    np_img = np.array(img)
    gray = np_img if len(np_img.shape) == 2 else np.mean(np_img, axis=2)

    # Check 1: Reject colored inputs
    if len(np_img.shape) == 3:
        r = np_img[:, :, 0].astype(float)
        g = np_img[:, :, 1].astype(float)
        b = np_img[:, :, 2].astype(float)

        color_diff = np.mean(np.abs(r - g)) + np.mean(np.abs(r - b))

        if color_diff > 15:
            return False, (
                f"Colored image detected. Color score: {color_diff:.1f}. "
                "Please upload a grayscale weld X-ray."
            )

    # Check 2: Reject blank or uniform image
    if np.std(gray) < 2:
        return False, "Image appears blank or nearly uniform."

    # Check 3: Reject mostly white documents/charts
    white_ratio = np.mean(gray > 240)

    if white_ratio > 0.95:
        return False, (
            f"Image has too much white background: {white_ratio * 100:.0f}%. "
            "It is likely a chart or document, not a weld X-ray."
        )

    # Check 4: Reject mostly black screenshots
    black_ratio = np.mean(gray < 10)

    if black_ratio > 0.80:
        return False, "Image is almost completely black. It may be a dark screenshot."

    return True, "Valid"


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
# Grad-CAM
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

        pooled_gradients = torch.mean(self.gradients, dim=[0, 2, 3])
        activations = self.activations[0]

        for i in range(activations.shape[0]):
            activations[i, :, :] *= pooled_gradients[i]

        heatmap = torch.mean(activations, dim=0).cpu().numpy()
        heatmap = np.maximum(heatmap, 0)

        if heatmap.max() != 0:
            heatmap /= heatmap.max()

        return heatmap


def apply_gradcam_overlay(original_img: Image.Image, heatmap: np.ndarray) -> np.ndarray:
    img_array = np.array(original_img.convert("RGB").resize((224, 224)))

    heatmap_resized = cv2.resize(heatmap, (224, 224))
    heatmap_colored = cm.jet(heatmap_resized)[:, :, :3]
    heatmap_colored = (heatmap_colored * 255).astype(np.uint8)

    overlay = (0.55 * img_array + 0.45 * heatmap_colored).astype(np.uint8)

    return overlay


# ======================================================
# Confidence Display
# ======================================================
def show_confidence_meter(confidence: float, pred_class: str, decision: str):
    pct = int(confidence * 100)

    st.markdown(f"**Predicted Class:** `{pred_class}`")
    st.markdown(f"**Model Confidence:** `{pct}%`")
    st.progress(float(confidence), text=f"{pct}% confidence")

    if decision == "PASS":
        st.markdown("**High confidence acceptable weld.**")
    elif decision == "FAIL":
        st.markdown("**Defect detected. Weld should be reviewed or rejected.**")
    else:
        st.markdown("**Low confidence. Manual inspection recommended.**")


# ======================================================
# Session CSV Download
# ======================================================
def generate_csv_report(history: list) -> bytes:
    output = io.StringIO()

    writer = csv.DictWriter(
        output,
        fieldnames=[
            "Timestamp",
            "Filename",
            "Predicted_Class",
            "Confidence_%",
            "Result",
            "Crack_%",
            "Lack_of_penetration_%",
            "No_defect_%",
            "Porosity_%"
        ]
    )

    writer.writeheader()

    for record in history:
        writer.writerow(record)

    return output.getvalue().encode("utf-8")


# ======================================================
# Inference Pipeline
# ======================================================
def run_inference(image: Image.Image, filename: str):
    is_valid, reason = is_reasonable_input(image)

    if not is_valid:
        st.error(
            f"INVALID INPUT — {reason}\n\n"
            "Please upload a grayscale weld radiographic X-ray image."
        )
        return

    col1, col2 = st.columns(2)

    with col1:
        st.image(image, caption=f"Input: {filename}", use_container_width=True)

    with st.spinner("Analyzing image..."):
        input_tensor = transform(image.convert("RGB")).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            output = model(input_tensor)
            probs = F.softmax(output, dim=1).cpu().numpy()[0]

        pred_idx = int(np.argmax(probs))
        pred_class = CLASSES[pred_idx]
        confidence = float(probs[pred_idx])
        decision = get_decision(pred_class, confidence)

        if show_gradcam:
            gradcam = GradCAM(model, model.layer4[-1])
            input_tensor_grad = transform(image.convert("RGB")).unsqueeze(0).to(DEVICE)
            input_tensor_grad.requires_grad_(True)
            heatmap = gradcam.generate(input_tensor_grad, pred_idx)
            overlay = apply_gradcam_overlay(image, heatmap)

    if show_gradcam:
        with col2:
            st.image(
                overlay,
                caption="Grad-CAM heatmap",
                use_container_width=True
            )
            st.caption("Red/yellow regions indicate stronger model attention.")

    st.divider()

    st.subheader("Prediction Result")

    if decision == "PASS":
        st.success("PASS — No weld defect detected.")
    elif decision == "FAIL":
        st.error(f"FAIL — {pred_class.replace('_', ' ')} detected.")
    else:
        st.warning("UNCERTAIN — Low confidence. Manual inspection recommended.")

    show_confidence_meter(confidence, pred_class, decision)

    st.caption("Confidence represents the model's predicted probability, not absolute certainty.")

    st.subheader("Class Probabilities")

    prob_col1, prob_col2 = st.columns([1, 2])

    with prob_col1:
        st.table({
            "Class": CLASSES,
            "Probability (%)": [f"{p * 100:.2f}" for p in probs]
        })

    with prob_col2:
        fig, ax = plt.subplots(figsize=(6, 3))

        colors = [
            "#2ecc71" if c == "No_defect" else
            "#e74c3c" if c == pred_class else
            "#3498db"
            for c in CLASSES
        ]

        bars = ax.bar(CLASSES, probs, color=colors)
        ax.set_ylim(0, 1.1)
        ax.set_ylabel("Probability")
        ax.set_title("Prediction Probabilities")
        ax.axhline(
            y=CONFIDENCE_THRESHOLD,
            color="orange",
            linestyle="--",
            linewidth=1.5,
            label=f"Threshold ({CONFIDENCE_THRESHOLD})"
        )

        for bar, p in zip(bars, probs):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02,
                f"{p * 100:.1f}%",
                ha="center",
                va="bottom",
                fontsize=8
            )

        ax.legend(fontsize=8)
        plt.xticks(rotation=15, ha="right", fontsize=8)
        plt.tight_layout()
        st.pyplot(fig)

    # Record result
    file_key = f"{filename}_{confidence:.6f}"

    if file_key not in st.session_state.processed_files:
        st.session_state.processed_files.add(file_key)

        record = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Filename": filename,
            "Predicted_Class": pred_class,
            "Confidence_%": f"{confidence * 100:.2f}",
            "Result": decision,
            "Crack_%": f"{probs[0] * 100:.2f}",
            "Lack_of_penetration_%": f"{probs[1] * 100:.2f}",
            "No_defect_%": f"{probs[2] * 100:.2f}",
            "Porosity_%": f"{probs[3] * 100:.2f}"
        }

        st.session_state.history.append(record)
        append_prediction_to_csv(record)


# ======================================================
# File Upload
# ======================================================
uploaded_files = st.file_uploader(
    "Upload weld radiographic image(s)",
    type=["png", "jpg", "jpeg", "bmp", "tiff"],
    accept_multiple_files=True
)

if uploaded_files:
    st.markdown(f"**{len(uploaded_files)} image(s) uploaded**")
    st.divider()

    reversed_files = uploaded_files[::-1]

    for i, uploaded_file in enumerate(reversed_files):
        if len(uploaded_files) > 1:
            st.subheader(f"Image {len(uploaded_files) - i}: `{uploaded_file.name}`")

        image = Image.open(uploaded_file)
        run_inference(image, uploaded_file.name)

        if i < len(uploaded_files) - 1:
            st.divider()

else:
    st.info("Upload one or more weld radiographic X-ray images to begin analysis.")


# ======================================================
# Prediction History
# ======================================================
if show_history and st.session_state.history:
    st.divider()
    st.subheader("Prediction History")

    history = st.session_state.history

    total = len(history)
    passed = sum(1 for h in history if h["Result"] == "PASS")
    failed = sum(1 for h in history if h["Result"] == "FAIL")
    uncertain = sum(1 for h in history if h["Result"] == "UNCERTAIN")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Inspected", total)
    m2.metric("Passed", passed)
    m3.metric("Failed", failed)
    m4.metric("Uncertain", uncertain)

    st.table(list(reversed(history)))

    csv_data = generate_csv_report(history)

    st.download_button(
        label="Download Session Report CSV",
        data=csv_data,
        file_name=f"weld_inspection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )