import json
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import cv2
    import numpy as np
    from fpdf import FPDF
    from PIL import Image, ImageDraw, ImageFont
    import matplotlib.font_manager as fm

    from libQr import formataQr, escreveQr
except Exception as error:
    print(error)
    raise


FIRST_PAGE_QUESTIONS = 24
OTHER_PAGE_QUESTIONS = 25
ROW_SPACING = 45
QUESTION_MARKER_X = 120
QUESTION_LABEL_X = 150
ALTERNATIVE_START_X = 260
ALTERNATIVE_SPACING = 120
GRID_COLOR = (120, 120, 120)
FONT_PATH = fm.findfont(fm.FontProperties(family="DejaVu Sans"))
BOLD_FONT_PATH = fm.findfont(fm.FontProperties(family="DejaVu Sans", weight="bold"))
HEADER_NAVY = (23, 50, 77)
HEADER_BLUE = (37, 99, 235)
HEADER_TEXT = (30, 41, 59)
HEADER_MUTED = (93, 108, 128)
HEADER_BORDER = (211, 221, 235)
HEADER_SURFACE = (247, 250, 255)
HEADER_BLUE_SOFT = (235, 243, 255)


def question_chunks(total_questions):
    chunks = []
    start = 1
    capacity = FIRST_PAGE_QUESTIONS
    while start <= total_questions:
        end = min(start + capacity - 1, total_questions)
        chunks.append((start, end))
        start = end + 1
        capacity = OTHER_PAGE_QUESTIONS
    return chunks


def safe_text(value):
    if value is None:
        return ""
    return str(value).replace("\ufffd", "?")


def fitted_text(draw, value, xy, max_width, size=20, min_size=13, fill=HEADER_TEXT, bold=True):
    text = safe_text(value)
    font_path = BOLD_FONT_PATH if bold else FONT_PATH
    font = ImageFont.truetype(font_path, size)
    while size > min_size and draw.textbbox((0, 0), text, font=font)[2] > max_width:
        size -= 1
        font = ImageFont.truetype(font_path, size)
    if draw.textbbox((0, 0), text, font=font)[2] > max_width:
        while text and draw.textbbox((0, 0), f"{text}…", font=font)[2] > max_width:
            text = text[:-1]
        text = f"{text}…"
    draw.text(xy, text, font=font, fill=fill)


def field_card(draw, box, label, value):
    draw.rounded_rectangle(box, radius=11, fill=HEADER_SURFACE, outline=HEADER_BORDER, width=2)
    label_font = ImageFont.truetype(BOLD_FONT_PATH, 10)
    draw.text((box[0] + 12, box[1] + 7), label.upper(), font=label_font, fill=HEADER_MUTED)
    fitted_text(draw, value, (box[0] + 12, box[1] + 25), box[2] - box[0] - 24, size=15, min_size=11)


def draw_header(img, largura, aluno, prof, prova, turma, data, nota_prova, page_index, total_pages):
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    label_font = ImageFont.truetype(BOLD_FONT_PATH, 10)
    try:
        data_fmt = f"{data.split('-')[2]} / {data.split('-')[1]} / {data.split('-')[0]}"
    except Exception:
        data_fmt = safe_text(data)

    page_text = f"PÁGINA {page_index}/{total_pages}"
    brand_font = ImageFont.truetype(BOLD_FONT_PATH, 16)
    draw.text((42, 23), "CorretorApp", font=brand_font, fill=HEADER_NAVY)
    draw.rounded_rectangle((800, 18, 940, 52), radius=17, fill=HEADER_BLUE_SOFT)
    page_font = ImageFont.truetype(BOLD_FONT_PATH, 11)
    page_width = draw.textbbox((0, 0), page_text, font=page_font)[2]
    draw.text((870 - int(page_width / 2), 28), page_text, font=page_font, fill=HEADER_NAVY)

    student_box = (40, 62, 940, 116)
    draw.rounded_rectangle(student_box, radius=12, fill=HEADER_BLUE_SOFT, outline=(173, 202, 247), width=2)
    draw.text((student_box[0] + 14, student_box[1] + 7), "ALUNO(A)", font=label_font, fill=HEADER_BLUE)
    fitted_text(
        draw,
        aluno,
        (student_box[0] + 14, student_box[1] + 23),
        student_box[2] - student_box[0] - 28,
        size=20,
        min_size=13,
    )

    info_top = 126
    info_bottom = 182
    field_card(draw, (40, info_top, 290, info_bottom), "Professor(a)", prof)
    field_card(draw, (305, info_top, 585, info_bottom), "Prova", prova)
    field_card(draw, (600, info_top, 770, info_bottom), "Turma", turma)
    field_card(draw, (785, info_top, 940, info_bottom), "Data", data_fmt)

    if page_index == 1:
        score = float(nota_prova)
        score_text = f"{score:.2f}"
        instruction_font = ImageFont.truetype(BOLD_FONT_PATH, 13)
        hint_font = ImageFont.truetype(FONT_PATH, 11)
        draw.text((42, 200), "INSTRUÇÕES DE PREENCHIMENTO", font=label_font, fill=HEADER_BLUE)
        draw.text((42, 218), "Marque apenas uma alternativa por questão.", font=instruction_font, fill=HEADER_TEXT)
        draw.text((42, 240), "Use caneta azul ou preta e preencha completamente o círculo.", font=hint_font, fill=HEADER_MUTED)

        draw.rounded_rectangle((600, 194, 760, 272), radius=12, fill=HEADER_BLUE_SOFT, outline=(173, 202, 247), width=2)
        draw.text((614, 204), "PESO TOTAL", font=label_font, fill=HEADER_BLUE)
        fitted_text(draw, score_text, (614, 225), 132, size=24)

        draw.rounded_rectangle((780, 194, 940, 272), radius=12, fill=(255, 255, 255), outline=HEADER_BORDER, width=2)
        draw.text((794, 204), "NOTA OBTIDA", font=label_font, fill=HEADER_MUTED)
        draw.line((798, 251, 922, 251), fill=HEADER_TEXT, width=2)

    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def layout_for_page(page_index):
    return {
        "separator_y": 290,
        "top_triangle_y": 350,
        "alt_marker_y": 385,
        "first_question_y": 445,
    }


def gerar_prova_payload(payload, basedir="."):
    path = ""

    try:
        if not os.path.isdir(f"{basedir}/"):
            os.mkdir(f"{basedir}/")

        prova = payload["exam_title"]
        prof = payload["teacher_name"]
        turma = payload["classroom_name"]
        data = payload["exam_date"]
        total_questions = int(payload["question_count"])
        qtd_quadrado_h = int(payload["option_count"])
        nota_prova = sum(int(item["weight"]) for item in payload["answer_key"])
        aluno = [student["name"] for student in payload["students"]]
        id_aluno = [student["id"] for student in payload["students"]]
        id_prova = payload["exam_id"]
        id_usuario = payload["user_id"]

        pdf = FPDF(format=(int(1240 / 2.7), int(1754 / 2.7)))
        chunks = question_chunks(total_questions)
        total_pages = len(chunks)
        for m in range(len(aluno)):
            for page_index, (question_start, question_end) in enumerate(chunks, start=1):
                qtd_quadrado_v = question_end - question_start + 1
                img = np.ones((1754, 1240, 3), np.uint8) * 255

                altura = img.shape[0]
                largura = img.shape[1]

                fonte = cv2.FONT_HERSHEY_SIMPLEX
                escala = 0.7
                espessura = 2

                layout = layout_for_page(page_index)
                img = cv2.line(img, (80, layout["separator_y"]), (largura - 80, layout["separator_y"]), (0, 0, 0), 2)
                img = draw_header(img, largura, aluno[m], prof, prova, turma, data, nota_prova, page_index, total_pages)

                msg = formataQr(f"{id_prova}.{id_aluno[m]}.{page_index}")
                qr_code = escreveQr(msg)

                img[0 : qr_code.shape[0], largura - qr_code.shape[1] : largura] = qr_code

                top_triangle_y = layout["top_triangle_y"]
                t1 = np.array([[40, top_triangle_y], [70, top_triangle_y], [40, top_triangle_y - 30]], np.int32)
                t2 = np.array([[largura - 70, top_triangle_y], [largura - 40, top_triangle_y], [largura - 70, top_triangle_y - 30]], np.int32)
                t3 = np.array([[40, altura - 60], [70, altura - 60], [40, altura - 90]], np.int32)
                t4 = np.array(
                    [[largura - 70, altura - 60], [largura - 40, altura - 60], [largura - 70, altura - 90]],
                    np.int32,
                )
                t = [t1, t2, t3, t4]
                for i in range(len(t)):
                    cv2.fillPoly(img, [t[i]], (0, 0, 0))

                espaco = int(0)
                for i in range(qtd_quadrado_v):
                    question_number = question_start + i
                    y = layout["first_question_y"] + espaco
                    cv2.rectangle(img, (QUESTION_MARKER_X, y), (QUESTION_MARKER_X + 20, y + 20), (0, 0, 0), -1)
                    cv2.putText(img, f"{question_number}", (QUESTION_LABEL_X, y + 20), fonte, escala, GRID_COLOR, espessura)
                    espaco += ROW_SPACING

                espaco = 0
                for i in range(qtd_quadrado_h):
                    cv2.rectangle(img, (ALTERNATIVE_START_X + espaco, layout["alt_marker_y"]), (ALTERNATIVE_START_X + espaco + 20, layout["alt_marker_y"] + 20), (0, 0, 0), -1)
                    espaco += ALTERNATIVE_SPACING

                letras = ["A", "B", "C", "D", "E", "F", "G"]
                espaco_x = espaco_y = 0
                for i in range(qtd_quadrado_v):
                    for j in range(qtd_quadrado_h):
                        center = (ALTERNATIVE_START_X + 10 + espaco_x, layout["first_question_y"] + 10 + espaco_y)
                        cv2.circle(img, center, 14, GRID_COLOR, 3)
                        cv2.putText(img, f"{letras[j]}", (center[0] - 7, center[1] + 7), fonte, escala, GRID_COLOR, espessura)
                        espaco_x += ALTERNATIVE_SPACING
                    espaco_x = 0
                    espaco_y += ROW_SPACING

                image_path = f"{basedir}/prova{m}_{page_index}.png"
                cv2.imwrite(image_path, img)

                pdf.add_page()
                pdf.set_auto_page_break(0)
                pdf.image(image_path)

                os.unlink(image_path)

        output_path = f"{basedir}/prova{id_usuario}.pdf"
        pdf.output(output_path, "F")
        path = os.path.abspath(output_path)
    except Exception as error:
        print(error)

    return path.replace("\\", "/")


if __name__ == "__main__":
    payload = json.loads(sys.argv[1])
    basedir = sys.argv[2] if len(sys.argv) > 2 else "."
    print(gerar_prova_payload(payload, basedir))
