import streamlit as st
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="Weld Defect Classifier",
    page_icon="🔧",
    layout="centered"
)

st.title("🔧 Weld Defect Classification App")
st.write(
    "Upload a radiographic weld image and the fine-tuned ResNet-18 model will classify the weld condition."
)

# -----------------------------
# Class names
# -----------------------------
CLASS_NAMES = [
    "Crack",
    "Lack_of_penetration",
    "No_defect",
    "Porosity"
]

# -----------------------------
# Model path
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "resnet18_weld_finetuned_best.pth"

# -----------------------------
# Device
# -----------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# -----------------------------
# Image transformations
# -----------------------------
image_transform = transforms.Compose([
    transforms.Grayscale(num_output_channels=3),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# -----------------------------
# Load model
# -----------------------------
@st.cache_resource
def load_model():
    model = models.resnet18(weights=None)

    num_features = model.fc.in_features
    model.fc = nn.Linear(num_features, len(CLASS_NAMES))

    checkpoint = torch.load(MODEL_PATH, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])

    model.to(device)
    model.eval()

    return model

model = load_model()

# -----------------------------
# Prediction function
# -----------------------------
def predict_image(image):
    input_tensor = image_transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(input_tensor)
        probabilities = torch.softmax(outputs, dim=1)[0]

    predicted_index = torch.argmax(probabilities).item()
    predicted_class = CLASS_NAMES[predicted_index]
    confidence = probabilities[predicted_index].item()

    return predicted_class, confidence, probabilities.cpu().numpy()

# -----------------------------
# File uploader
# -----------------------------
uploaded_file = st.file_uploader(
    "Upload weld radiographic image",
    type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    image = Image.open(uploaded_file)

    st.subheader("Uploaded Image")
    st.image(image, caption="Input weld image", use_container_width=True)

    predicted_class, confidence, probabilities = predict_image(image)

    st.subheader("Prediction Result")

    if predicted_class == "No_defect":
        st.success("✅ PASS: No defect detected")
    else:
        st.error("❌ FAIL: Weld defect detected")

    st.write(f"**Predicted Class:** `{predicted_class}`")
    st.write(f"**Confidence:** `{confidence * 100:.2f}%`")
    st.caption("Note: Confidence is the absolute certainty.")

    probability_df = pd.DataFrame({
        "Class": CLASS_NAMES,
        "Probability": probabilities
    })

    probability_df["Probability (%)"] = probability_df["Probability"] * 100

    st.subheader("Class Probabilities")
    st.dataframe(
        probability_df[["Class", "Probability (%)"]],
        use_container_width=True
    )

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(CLASS_NAMES, probabilities)
    ax.set_ylabel("Probability")
    ax.set_title("Prediction Probability per Class")
    ax.set_ylim([0, 1])
    plt.xticks(rotation=25, ha="right")
    st.pyplot(fig)

else:
    st.info("Please upload a weld image to start prediction.")