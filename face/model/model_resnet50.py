
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import torchbnn as bnn  # Байесовские слои


class AgeEstimationBNN(nn.Module):
    def __init__(self, dropout_rate=0.2):
        super(AgeEstimationBNN, self).__init__()

        # ResNet-50 без последнего слоя
        resnet = models.resnet50(pretrained=True)
        self.feature_extractor = nn.Sequential(*list(resnet.children())[:-1])

        # Размораживаем верхние 2 слоя
        for param in list(self.feature_extractor[-2:].parameters()):
            param.requires_grad = True

        # Байесовские слои
        self.fc1 = bnn.BayesLinear(prior_mu=0, prior_sigma=0.1, in_features=2048, out_features=512)
        self.fc2 = bnn.BayesLinear(prior_mu=0, prior_sigma=0.1, in_features=512, out_features=1)  # Регрессия

        self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x, sample_n=3):
        x = self.feature_extractor(x)
        x = torch.flatten(x, 1)

        outputs = []
        for _ in range(sample_n):  # Байесовский метод (несколько выборок)
            x_ = F.relu(self.fc1(x))
            x_ = self.dropout(x_)
            output = self.fc2(x_)
            outputs.append(output)

        return torch.stack(outputs, dim=0).mean(dim=0)  # Усредняем предсказания
