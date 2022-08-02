
import numpy as np
import matplotlib.pyplot as plt
import glob
import pandas as pd
import seaborn

import torch
import torch.backends.cudnn as cudnn
from torch.utils.data.dataloader import DataLoader

from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import mean_squared_error as mse

from pruebaModelos.ESPCN.models import ESPCN
from pruebaModelos.ESPCN.datasets import EvalDataset
from pruebaModelos.ESPCN.utils import AverageMeter, calc_psnr


def cargaPesos(model, path):
    state_dict = model.state_dict()

    for n, p in torch.load(path, map_location=lambda storage, loc: storage).items():
        if n[7:] in state_dict.keys():
            state_dict[n[7:]].copy_(p)
        else:
            print(n[7:])
            print(type(n))
            raise KeyError(n)

    model.eval()

escala=2

pesosPath=r"C:\Users\Estudiante\Documents\dataset\pesos\x"+str(escala)
evalPath=pesosPath+"\eval.h5"

def calcularMetricas(model, path : str):
    files=sorted(glob.glob(path+r"\*.pth"))
    eval_dataset = EvalDataset(evalPath)
    eval_dataloader = DataLoader(dataset=eval_dataset, batch_size=1)

    psnrProm=[]
    ssimProm=[]
    mseProm =[]

    for file in files:
        print(file)
        cargaPesos(model, file)

        epoch_psnr = AverageMeter()
        epoch_ssim = AverageMeter()
        epoch_mse = AverageMeter()

        for data in eval_dataloader:
            inputs, labels = data

            inputs = inputs.to(device)
            labels = labels.to(device)

            with torch.no_grad():
                preds = model(inputs).clamp(0.0, 1.0)

            prd=preds.numpy().squeeze(0).squeeze(0)
            lbl=labels.numpy().squeeze(0).squeeze(0)

            epoch_psnr.update(psnr(lbl, prd ), len(inputs))
            epoch_ssim.update(ssim(im1=lbl, im2=prd, data_range = lbl.max() - prd.min()), len(inputs))
            epoch_mse.update(mse(lbl, prd), len(inputs))


        psnrProm.append(float(epoch_psnr.avg))
        ssimProm.append(float(epoch_ssim.avg))
        mseProm.append(float(epoch_mse.avg))

    return psnrProm, ssimProm , mseProm

#Instanciar modelo
cudnn.benchmark = True
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

model = ESPCN(scale_factor=escala).to(device)

#IniciarPruebas
x,y,z=calcularMetricas(model,pesosPath)
print(x)
print(y)
print(z)


