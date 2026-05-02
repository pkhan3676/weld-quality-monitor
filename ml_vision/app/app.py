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

# ======================================================
# Streamlit Page Config
# ======================================================
st.set_page_config(
    page_title="Weld Defect Classification App",
    layout="centered"
)

st.title("🛠️ Weld Defect Classification App")

# ✅ Disclaimer (as requested)
st.caption("⚠️ AI-generated content may be incorrect.")

st.write(
    "Upload a **weld radiographic X‑ray image**.\n\n"
    "❌ Natural photos, screenshots, or colored images are rejected."
)

# ======================================================
# Cache Control
# ======================================================
if st.button("🔄 Clear Cache & Reload Model"):
    st.cache_resource.clear()
    st.experimental_rerun()

# ======================================================
# Constants
# ======================================================
CLASSES = [
    "Crack",
    "Lack_of_penetration",
    "No_defect",
    "Porosity"
]

CONFIDENCE_THRESHOLD = 0.80

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "resnet18_weld_finetuned_best.pth"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ======================================================
# Load Model (Checkpoint-aware)
# ======================================================
@st.cache_resource
def load_model():
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 4)

    checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)
    model.load_state_dict(checkpoint["model_state_dict"])

    model.to(DEVICE)
    model.eval()
    return model

model = load_model()

# ======================================================
# ✅ MINIMAL, SAFE INPUT VALIDATION (FINAL)
# ======================================================
def is_reasonable_input(img: Image.Image) -> bool:
    """
    Purpose:
    - Reject obvious non-weld inputs
    - DO NOT reject real weld images (porosity, crack, LoP, no_defect)
    """

    np_img = np.array(img)

    # 1️⃣ Reject colored images (photos, screenshots)
    if len(np_img.shape) == 3:
        r, g, b = np_img[:, :, 0], np_img[:, :, 1], np_img[:, :, 2]
        color_diff = np.mean(np.abs(r - g)) + np.mean(np.abs(r - b))
        if color_diff > 10:
            return False

    # 2️⃣ Reject extremely flat / empty images
    gray = np_img if len(np_img.shape) == 2 else np.mean(np_img, axis=2)
    if np.std(gray) < 2:
        return False

    return True

# ======================================================
# Image Preprocessing
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
# File Upload
# ======================================================
uploaded_file = st.file_uploader(
    "Upload weld radiographic image",
    type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    image = Image.open(uploaded_file)

    st.subheader("Uploaded Image")
    st.image(image, caption="Input image", width=500)

    # ✅ Validation (lightweight)
    if not is_reasonable_input(image):
        st.error(
            "❌ INVALID INPUT\n\n"
            "This image does not look like a radiographic weld X‑ray.\n"
            "Please upload a grayscale weld radiograph."
        )
        st.stop()

    # ==================================================
    # Inference
    # ==================================================
    input_tensor = transform(image.convert("RGB")).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        output = model(input_tensor)
        probs = F.softmax(output, dim=1).cpu().numpy()[0]

    pred_idx = int(np.argmax(probs))
    pred_class = CLASSES[pred_idx]
    confidence = probs[pred_idx]

    st.subheader("Prediction Result")

    if confidence < CONFIDENCE_THRESHOLD:
        st.warning("⚠️ Uncertain prediction — manual inspection recommended.")
    else:
        if pred_class == "No_defect":
            st.success("✅ PASS — No weld defect detected")
        else:
            st.error("❌ FAIL — Weld defect detected")

    st.write(f"**Predicted Class:** `{pred_class}`")
    st.write(f"**Model Confidence:** `{confidence*100:.2f}%`")

    st.caption(
        "Confidence represents the model’s predicted probability, not absolute certainty."
    )

    # Probability table
    st.subheader("Class Probabilities")
    st.table({
        "Class": CLASSES,
        "Probability (%)": [f"{p*100:.3f}" for p in probs]
    })

    # Bar chart
    fig, ax = plt.subplots()
    ax.bar(CLASSES, probs)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Probability")
    ax.set_title("Prediction Probability per Class")
    plt.xticks(rotation=20)
    st.pyplot(fig)