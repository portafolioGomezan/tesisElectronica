

import torch
import torch.backends.cudnn as cudnn
import glob
import numpy as np
import cv2

from skimage import  measure

from pruebaModelos.ESPCN.models import ESPCN
from pruebaModelos.ESPCN.utils import convert_ycbcr_to_rgb, preprocess, preprocessRGB

#Este script permite calcular y almacenar los resultados del snr y el desenfoque

#Permite calcular el snr de una imagen
def signaltonoise(a, axis=0, ddof=0):
    a = np.asanyarray(a)
    m = a.mean(axis)
    sd = a.std(axis=axis, ddof=ddof)
    return np.where(sd == 0, 0, m/sd)


#Permite mapear el método con el indicativo del mismo método en opencv
interpolacion={
    "lan": cv2.INTER_LANCZOS4,
    "nn": cv2.INTER_NEAREST,
    "bi2": cv2.INTER_LINEAR,
    "bi3": cv2.INTER_CUBIC
}

#Permite mapear el método con el nombre de dicho método
nombres={
    "lan": "lanczos",
    "nn": "NEAREST",
    "bi2": "LINEAR",
    "bi3": "CUBIC"
}

#Permite mapear la escala deseada con la ubicación
pesos={
    2: r"C:\Users\Estudiante\Documents\dataset\prueba\espcn_x2Full.pth",
    4: r"C:\Users\Estudiante\Documents\dataset\prueba\best0x4.pth",
    8: r"C:\Users\Estudiante\Documents\dataset\prueba\espcnx8.pth"
}

#Calula las métricas con base en un método y la escala de dicho metodo
def calcularOtras(factor, metodo, correr, y, RGB, mtd):

    #Ubicación ground truth
    gtPath=r"C:\Users\Estudiante\Documents\dataset\groundTruth\eval\*.png"
    # Ubicación imagenes decimadas
    scPath=r"C:\Users\Estudiante\Documents\dataset\decimadasX"+str(factor)+"\eval\*.png"
    # Ubicación destino almacenar resultados de méticas
    pathDest=r"C:\Users\Estudiante\Documents\dataset\resultados\calidad\x"+str(factor)

    #Se carga el método, el nombre y los pesos
    tecnica=interpolacion[metodo]
    interpolationName=nombres[metodo]
    weights_file=pesos[factor]

    #verificacion GPU
    cudnn.benchmark = True
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

    #creacion de modelo
    model = ESPCN(scale_factor=factor).to(device)

    #subida de pesos
    state_dict = model.state_dict()
    for n, p in torch.load(weights_file, map_location=lambda storage, loc: storage).items():
        if n[7:] in state_dict.keys():
            state_dict[n[7:]].copy_(p)
        else:
            raise KeyError(n)

    #switch evaluacion/ejecucion
    model.eval()


    #Comparación entre las estartegias:
    gtFiles=sorted(glob.glob(gtPath))
    scFiles=sorted(glob.glob(scPath))


    redBlur=[]
    redSNR=[]

    #empleando solo Y
        #En caso de querer evaluar los métodos de super resolución usando el canal Y
    if (y):

        #Si se desea calcular las métricas
            #Es posible no calcular las metricas y cargar resultados almacenados previamente
        if (correr):

            for i,j in zip(gtFiles, scFiles):
                print(i)
                print(j)
                #obtener imagenes
                gt = cv2.imread(i, 1)
                sc = cv2.imread(j, 1)
                image_width = sc.shape[0]
                image_height = sc.shape[1]
                lan = cv2.resize(sc, (image_width * factor, image_height * factor), interpolation=cv2.INTER_LANCZOS4)
                #procesarImagenes
                scPrep, _ = preprocess(sc, device)
                _, ycbcr = preprocess(lan, device)
                #prediccion del modelo
                with torch.no_grad():
                    preds = model(scPrep).clamp(0.0, 1.0)
                #pos procesamiento
                preds = preds.mul(255.0).cpu().numpy().squeeze(0).squeeze(0)
                output = np.array([preds, ycbcr[..., 1], ycbcr[..., 2]]).transpose([1, 2, 0])
                output = np.clip(convert_ycbcr_to_rgb(output), 0.0, 255.0).astype(np.uint8)
                #almacenar resultados
                gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
                redBlur.append( measure.blur_effect(gray))
                redSNR.append(signaltonoise(output, axis=None))

            #convertir a array
            rdBlur=np.array(redBlur)
            rdSNR=np.array(redSNR)

            #Guardar el vector entero de resultados como archivo npy
            np.save(pathDest+r"\IredBlur_y.npy",rdBlur)
            np.save(pathDest+r"\IredSNR_y.npy", rdSNR)

        #cargar resultados
        rdBlur=np.load(pathDest+r"\IredBlur_y.npy")
        rdSNR=np.load(pathDest+r"\IredSNR_y.npy")

        #Mostrar resultados
        print("MODELO Y "+str(factor))
        print("*************** BLUR *************** SNR")
        print("promedio ", rdBlur.mean(), "  ", rdSNR.mean())
        print("std ", np.std(rdBlur), "  ", np.std(rdSNR))
        print("mediana ", np.median(rdBlur), "  ", np.median(rdSNR))
        print("minimo ", np.amin(rdBlur), "  ", np.amin(rdSNR))
        print("maximo ", np.amax(rdBlur), "  ", np.amax(rdSNR))
        print("***")

    #empleando RGB

    redBlur=[]
    redSNR=[]

    # En caso de querer evaluar los métodos de super resolución usando los canales RGB
    if(RGB):

        # Si se desea calcular las métricas
            # Es posible no calcular las metricas y cargar resultados almacenados previamente
        if(correr):

            for i,j in zip(gtFiles, scFiles):
                print(i)
                print(j)
                #obtener imagenes
                gt = cv2.imread(i, 1)
                sc = cv2.imread(j, 1)
                image_width = sc.shape[0]
                image_height = sc.shape[1]

                R = sc[..., 0]
                G = sc[..., 1]
                B = sc[..., 2]
                # preprocesamiento
                RPrep = preprocessRGB(R, device)
                GPrep = preprocessRGB(G, device)
                BPrep = preprocessRGB(B, device)
                # Prediccion
                with torch.no_grad():
                    predsR = model(RPrep).clamp(0.0, 1.0)
                    predsG = model(GPrep).clamp(0.0, 1.0)
                    predsB = model(BPrep).clamp(0.0, 1.0)
                # pos procesamiento
                predsR = predsR.mul(255.0).cpu().numpy().squeeze(0).squeeze(0)
                predsG = predsG.mul(255.0).cpu().numpy().squeeze(0).squeeze(0)
                predsB = predsB.mul(255.0).cpu().numpy().squeeze(0).squeeze(0)
                output = np.array([predsR, predsG, predsB]).transpose([1, 2, 0]).astype(np.uint8)

                # almacenar resultados
                gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
                redBlur.append(measure.blur_effect(gray))
                redSNR.append(signaltonoise(output, axis=None))

            #convetir resultados a array
            rdBlur=np.array(redBlur)
            rdSNR=np.array(redSNR)

            # Guardar el vector entero de resultados como archivo npy
            np.save(pathDest+r"\IredBlur_RGB.npy",rdBlur)
            np.save(pathDest+r"\IredSNR_RGB.npy", rdSNR)

        #Cargar resultados
        rdBlur=np.load(pathDest+r"\IredBlur_RGB.npy")
        rdSNR=np.load(pathDest+r"\IredSNR_RGB.npy")

        #mostrar resultados
        print("MODELO RGB "+str(factor))
        print("************** BLUR **************** SNR")
        print("promedio ", rdBlur.mean(), "  ", rdSNR.mean())
        print("std ", np.std(rdBlur), "  ", np.std(rdSNR))
        print("mediana ", np.median(rdBlur), "  ", np.median(rdSNR))
        print("minimo ", np.amin(rdBlur), "  ", np.amin(rdSNR))
        print("maximo ", np.amax(rdBlur), "  ", np.amax(rdSNR))
        print("***")

    ntpBlur=[]
    ntpSNR=[]


    #empleando metodos de interpolacion

    # En caso de querer evaluar los métodos de interpolación
    if (mtd):

        # Si se desea calcular las métricas
        # Es posible no calcular las metricas y cargar resultados almacenados previamente
        if (correr):

            for i,j in zip(gtFiles, scFiles):
                print(i)
                print(j)
                #obtener imagenes
                gt = cv2.imread(i, 1)
                sc = cv2.imread(j, 1)
                image_width = sc.shape[0]
                image_height = sc.shape[1]
                ntp = cv2.resize(sc, (image_width * factor, image_height * factor), interpolation=tecnica)

                #almacenar resultados
                gray = cv2.cvtColor(ntp, cv2.COLOR_BGR2GRAY)
                ntpBlur.append(measure.blur_effect(gray))
                ntpSNR.append(signaltonoise(ntp, axis=None))

            #convertir array
            ntpBlur=np.array(ntpBlur)
            ntpSNR=np.array(ntpSNR)

            # Guardar el vector entero de resultados como archivo npy
            np.save(pathDest +r"\I"+interpolationName+"BLUR.npy", ntpBlur)
            np.save(pathDest +r"\I"+interpolationName+"SNR.npy", ntpSNR)

        # Cargar resultados
        ntpBlur=np.load(pathDest +r"\I"+interpolationName+"BLUR.npy")
        ntpSNR=np.load(pathDest +r"\I"+interpolationName+"SNR.npy")

        # mostrar resultados
        print(interpolationName+" "+str(factor))
        print("*************** BLUR *************** SNR")
        print("promedio ", ntpBlur.mean(), "  ", ntpSNR.mean())
        print("std ", np.std(ntpBlur), "  ", np.std(ntpSNR))
        print("mediana ", np.median(ntpBlur), "  ", np.median(ntpSNR))
        print("minimo ", np.amin(ntpBlur), "  ", np.amin(ntpSNR))
        print("maximo ", np.amax(ntpBlur), "  ", np.amax(ntpSNR))
        print("***")


calcularOtras(factor=2, metodo="nn", correr= False, y= True, RGB= True, mtd= False )
calcularOtras(factor=2, metodo="nn", correr= False, y= False, RGB= False, mtd= True )
calcularOtras(factor=2, metodo="bi2", correr= False, y= False, RGB= False, mtd= True )
calcularOtras(factor=2, metodo="bi3", correr= False, y= False, RGB= False, mtd= True )
calcularOtras(factor=2, metodo="lan", correr= False, y= False, RGB= False, mtd= True )

calcularOtras(factor=4, metodo="nn", correr= False, y= False, RGB= False, mtd= True )
calcularOtras(factor=4, metodo="nn", correr= False, y= True, RGB= True, mtd= False )

calcularOtras(factor=4, metodo="bi2", correr= False, y= False, RGB= False, mtd= True )
calcularOtras(factor=4, metodo="bi3", correr= False, y= False, RGB= False, mtd= True )
calcularOtras(factor=4, metodo="lan", correr= False, y= False, RGB= False, mtd= True )


calcularOtras(factor=8, metodo="nn", correr= False, y= True, RGB= True, mtd= False )
calcularOtras(factor=8, metodo="nn", correr= False, y= False, RGB= False, mtd= True )
calcularOtras(factor=8, metodo="bi2", correr= False, y= False, RGB= False, mtd= True )
calcularOtras(factor=8, metodo="bi3", correr= False, y= False, RGB= False, mtd= True )
calcularOtras(factor=8, metodo="lan", correr= False, y= False, RGB= False, mtd= True )
