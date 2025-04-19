import torch

from torch import nn
from model_resnet50 import AgeEstimationBNN
from dataloader import Dataset_folder
from torchvision import transforms
from torchvision.datasets import ImageFolder
from sklearn.metrics import mean_absolute_error, mean_squared_error
from torch.utils.data import DataLoader
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

from tqdm import tqdm
import torch.nn.functional as F
import os

train_file = "data/AFAD-Full/train"
test_file = "data/AFAD-Full/test"

import torchvision.transforms as transforms
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader

transform_train = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(degrees=15),
    transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.1),
    transforms.RandomAffine(degrees=10, translate=(0.2, 0.2), scale=(0.8, 1.2), shear=10),
    transforms.RandomGrayscale(p=0.1),
    transforms.ToTensor(), 
    transforms.RandomErasing(p=0.3, scale=(0.02, 0.1), ratio=(0.3, 3.3), value=0),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

dataset_train = ImageFolder(train_file, transform=transform_train)
dataset_test = ImageFolder(test_file, transform=val_transform)

train_dataloader = DataLoader(dataset_train, batch_size=32, shuffle=True)
test_dataloader = DataLoader(dataset_test, batch_size=32, shuffle=False)

# print(test_dataloader.dataset[0])
import torch.optim as optim
import numpy as np

device = "cuda" if torch.cuda.is_available() else "cpu"

model = AgeEstimationBNN().to(device)
# checkpoint = torch.load('models_cacd/best_model_with_4.6901_mae_6.9180_rmse_15_epoch.pt', map_location=device)
# model.load_state_dict(checkpoint)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-4, weight_decay=1e-5)
criterion = nn.MSELoss().to(device)
# criterion = nn.MAELoss()


best_mae = float("inf")
save_dir = "models_afad/"
os.makedirs(save_dir, exist_ok=True)

for epoch in range(100):
    epoch_losses = []
    model.train()
    epoch = epoch + 1
    progress_bar = tqdm(train_dataloader, desc=f"Training - Epoch {epoch}", total=len(train_dataloader))
    running_loss = 0
    all_preds, all_labels = [], []

    for step, (inputs, labels) in enumerate(progress_bar):
        inputs, labels = inputs.to(device), labels.to(device)
        labels = labels.float()
        optimizer.zero_grad()
        outputs = model(inputs, sample_n=3)
        outputs = outputs.squeeze()

        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        epoch_losses.append(loss.item())
        running_loss += loss.item()

        all_preds.append(outputs.cpu().detach().numpy())
        all_labels.append(labels.cpu().detach().numpy())

        progress_bar.set_postfix(loss=running_loss / (step + 1))

    all_preds = np.concatenate(all_preds)
    all_labels = np.concatenate(all_labels)
    train_mae = mean_absolute_error(all_labels, all_preds)
    train_rmse = np.sqrt(mean_squared_error(all_labels, all_preds))

    print(f">>> Epoch {epoch} train loss: {np.mean(epoch_losses):.4f}, train MAE: {train_mae:.2f}, RMSE: {train_rmse:.2f}")

    # Modelni har epochdan so‘ng saqlash (oxirgi model)
    torch.save(model.state_dict(), os.path.join(save_dir, f"last_model.pt"))

    # Valiatsiya va eng yaxshi modelni saqlash
    if epoch % 5 == 0:
        model.eval()
        epoch_losses = []
        all_preds, all_labels = [], []

        progress_test = tqdm(test_dataloader, desc=f"Test - Epoch {epoch}", total=len(test_dataloader))

        with torch.no_grad():
                for step, (inputs, labels) in enumerate(progress_test):
                    # print(labels)
                    labels = labels.float()
                    inputs, labels = inputs.to(device), labels.to(device)
                    outputs = model(inputs, sample_n=3).squeeze()
                    loss = criterion(outputs, labels)
                    epoch_losses.append(loss.item())

                    all_preds.append(outputs.cpu().numpy())
                    all_labels.append(labels.cpu().numpy())
                
                all_preds = np.concatenate(all_preds)
                all_labels = np.concatenate(all_labels)
                test_mae = mean_absolute_error(all_labels, all_preds)
                test_rmse = np.sqrt(mean_squared_error(all_labels, all_preds))

                print(f">>> Epoch {epoch} test loss: {np.mean(epoch_losses):.4f}, "
                      f"test MAE: {test_mae:.2f}, RMSE: {test_rmse:.2f}")

                # Eng yaxshi modelni saqlash
                if test_mae < best_mae:
                    best_mae = test_mae
                    torch.save(model.state_dict(), os.path.join(save_dir, f"best_model_with_{test_mae:.4f}_mae_{test_rmse:.4f}_rmse_{epoch}_epoch.pt"))
                    print(f"Best model saved with MAE: {best_mae:.2f}")

