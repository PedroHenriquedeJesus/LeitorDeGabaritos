import cv2
import pyzbar.pyzbar as pyzbar
import pyqrcode
import io
import numpy as np
import os

CURRENT_FOLDER = os.path.dirname(__file__)
QR_LOGO_PATH = os.path.realpath(f"{CURRENT_FOLDER}/../assets/logo_qr_corretorapp.png")

def leQr(img) -> dict:
    """
    Dada uma imagem, a função retorna:
        *A informação contida no QRcode

    @parâmetro img Arquivo de imagem no qual está inserido o QRcode

    """

    im_gray = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2HSV))[2]
    _, im_bw = cv2.threshold(im_gray, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY)

    final = {}

    try:
        qr_info = pyzbar.decode(im_bw)

        for obj in qr_info:
            text = obj.data

        # Texto com formatação
        new_text = text.decode('utf-8')
        if len(new_text) != 40:
            new_text = None
        else:
            new_text = new_text.replace('#', '') # Substitui os "#" por null
            parts = new_text.split('.')
            id_prova = parts[0]
            id_aluno = parts[1] if len(parts) > 1 else ''
            pagina = parts[2] if len(parts) > 2 else '1'

            # Esse if verifica se o primeiro número e o segundo número podem
            # ser convetidos para numeral
            if ((id_prova.isdigit()) and (id_aluno.isdigit()) and (pagina.isdigit())):
                final = {
                    'id_prova': int(id_prova),
                    'id_aluno': int(id_aluno),
                    'pagina': int(pagina)
                }
    except Exception as error:
        print(f'Something went wrong!\n{error}')
        
    #retorna apenas o texto contido
    return final

def escreveQr(texto):
    """
    Codifica um texto em QRcode e retorna-o como imagem:

    @parâmetro texto Texto que vai ser codificado em QRcode

    """
    code = pyqrcode.create(texto)
    buffer = io.BytesIO()
    code.png(buffer, scale=6)
    img = cv2.imdecode(np.frombuffer(buffer.getvalue(), np.uint8), cv2.IMREAD_COLOR)
    img_h, img_w, _ = img.shape
    mark_size = max(24, int(img_w * 0.18))
    x0 = int((img_w - mark_size) / 2)
    y0 = int((img_h - mark_size) / 2)
    x1 = x0 + mark_size
    y1 = y0 + mark_size
    cv2.rectangle(img, (x0, y0), (x1, y1), (255, 255, 255), -1)
    logo = cv2.imread(QR_LOGO_PATH, cv2.IMREAD_UNCHANGED)
    if logo is not None:
        logo = cv2.resize(logo, (mark_size, mark_size), interpolation=cv2.INTER_AREA)
        if logo.shape[2] == 4:
            alpha = logo[:, :, 3] / 255.0
            for channel in range(3):
                img[y0:y1, x0:x1, channel] = (
                    alpha * logo[:, :, channel] + (1 - alpha) * img[y0:y1, x0:x1, channel]
                )
        else:
            img[y0:y1, x0:x1] = logo[:, :, :3]

    return img



def formataQr(msg):
    """
    Dada uma string, prenche essa string até atingir o tamanho 20 e retorna essa
    nova string.

    @parâmetro msg String que será prenchida

    """
    txt_msg = str(msg)
    zeros = ''
    if len(txt_msg) < 9999999999999999999999999999999999999999:
        for i in range(40-len(txt_msg)):
            zeros += '#'
        txt_msg = zeros + txt_msg
    return txt_msg
