import streamlit as st
import torch
import torch.nn.functional as F
import torchvision.transforms as transforms
import torchvision.models as models
import torch.nn as nn
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
st.write(
    "Upload a **radiographic weld X‑ray image**. "
    "The fine‑tuned ResNet‑18 model will classify the weld condition."
)

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
# Load Model (CHECKPOINT‑AWARE)
# ======================================================
@st.cache_resource
def load_model():
    # 1️⃣ Define architecture
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 4)

    # 2️⃣ Load full checkpoint dictionary
    checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)

    # 3️⃣ Extract ONLY model weights
    if "model_state_dict" not in checkpoint:
        raise ValueError(
            "Checkpoint does not contain 'model_state_dict'. "
            "Please check how the model was saved."
        )

    model.load_state_dict(checkpoint["model_state_dict"])

    # 4️⃣ Evaluation mode
    model.to(DEVICE)
    model.eval()

    return model


model = load_model()

# ======================================================
# Input Validation (Radiograph Check)
# ======================================================
def is_likely_radiograph(img: Image.Image) -> bool:
    np_img = np.array(img)

    # Reject strongly colored images
    if len(np_img.shape) == 3:
        r, g, b = np_img[:, :, 0], np_img[:, :, 1], np_img[:, :, 2]
        channel_diff = np.mean(np.abs(r - g)) + np.mean(np.abs(r - b))
        if channel_diff > 5:
            return False

    # Reject very low‑contrast images
    gray = np_img if len(np_img.shape) == 2 else np.mean(np_img, axis=2)
    if np.std(gray) < 10:
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
    image = Image.open(uploaded_file).convert("RGB")

    st.subheader("Uploaded Image")
    st.image(image, caption="Input weld image", use_column_width=True)

    # ---------- Step 1: Input validation ----------
    if not is_likely_radiograph(image):
        st.error(
            "❌ **Invalid input detected.**\n\n"
            "Please upload a **radiographic weld X‑ray image**.\n"
            "Natural photos, documents, or screenshots are not supported."
        )
        st.stop()

    # Preprocess
    input_tensor = transform(image).unsqueeze(0).to(DEVICE)

    # ==================================================
    # Inference
    # ==================================================
    with torch.no_grad():
        output = model(input_tensor)
        probs = F.softmax(output, dim=1).cpu().numpy()[0]

    pred_idx = int(np.argmax(probs))
    pred_class = CLASSES[pred_idx]
    confidence = probs[pred_idx]

    # ==================================================
    # Prediction Result
    # ==================================================
    st.subheader("Prediction Result")

    if confidence < CONFIDENCE_THRESHOLD:
        st.warning(
            "⚠️ **Uncertain prediction**\n\n"
            "Model confidence is below the industrial acceptance threshold.\n"
            "Manual inspection is recommended."
        )
    else:
        if pred_class == "No_defect":
            st.success("✅ **PASS: No weld defect detected**")
        else:
            st.error("❌ **FAIL: Weld defect detected**")

    st.write(f"**Predicted Class:** `{pred_class}`")
    st.write(f"**Model Confidence:** `{confidence * 100:.2f}%`")

    st.caption(
        "ℹ️ Confidence represents the model’s predicted probability "
        "and is **not absolute certainty**."
    )

    # ==================================================
    # Class Probability Table
    # ==================================================
    st.subheader("Class Probabilities")

    prob_table = {
        "Class": CLASSES,
        "Probability (%)": [f"{p * 100:.4f}" for p in probs]
    }
    st.table(prob_table)

    # ==================================================
    # Probability Bar Chart
    # ==================================================
    fig, ax = plt.subplots()
    ax.bar(CLASSES, probs)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Probability")
    ax.set_title("Prediction Probability per Class")
    plt.xticks(rotation=20)

    st.pyplot(fig)