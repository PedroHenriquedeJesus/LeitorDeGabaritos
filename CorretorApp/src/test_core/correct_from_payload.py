import json
import sys

try:
    from util import getAnswersV2, getGrades, getOurSqrV2, leQr, paper90
    import cv2
except Exception as error:
    print(error)
    raise


FIRST_PAGE_QUESTIONS = 24
OTHER_PAGE_QUESTIONS = 25


def page_range(page_number, total_questions):
    start = 1
    capacity = FIRST_PAGE_QUESTIONS
    current_page = 1
    while start <= total_questions:
        end = min(start + capacity - 1, total_questions)
        if current_page == page_number:
            return start, end
        start = end + 1
        capacity = OTHER_PAGE_QUESTIONS
        current_page += 1
    return total_questions + 1, total_questions


def main():
    image_path = sys.argv[1]
    payload = json.loads(sys.argv[2])
    img = cv2.imread(image_path)
    aligned = paper90(img)
    qr_code_info = leQr(aligned)
    if not qr_code_info:
        raise KeyError("Nao foi possivel localizar as informacoes no QRCode.")

    total_questions = int(payload["question_count"])
    expected_alternatives = int(payload["option_count"])
    page_number = int(qr_code_info.get("pagina", 1))
    question_start, question_end = page_range(page_number, total_questions)
    expected_questions = question_end - question_start + 1
    page_answer_key = []
    for item in payload["answer_key"]:
        question_number = int(item["question_number"])
        if question_start <= question_number <= question_end:
            page_answer_key.append(
                [question_number - question_start + 1, int(item["option_index"]), int(item["weight"])]
            )

    question_squares, alternative_squares, _ = getOurSqrV2(
        aligned,
        expected_questions=expected_questions,
        expected_alternatives=expected_alternatives,
    )
    if len(question_squares) != expected_questions or len(alternative_squares) != expected_alternatives:
        raise Exception(
            "Quantidade de questoes ou alternativas detectada nao confere com a prova."
        )

    student_answers = getAnswersV2(
        aligned,
        expected_questions=expected_questions,
        expected_alternatives=expected_alternatives,
    )
    _, clear_answers, _ = getGrades(page_answer_key, student_answers)
    normalized_answers = [-1 for _ in range(total_questions)]
    for index, answer in enumerate(clear_answers):
        global_index = question_start + index - 1
        if global_index < total_questions:
            normalized_answers[global_index] = answer - 1 if answer > 0 else -1
    print(f'id_prova:{qr_code_info["id_prova"]}')
    print(f'id_aluno:{qr_code_info["id_aluno"]}')
    print(f'pagina:{page_number}')
    print(f'resposta:{",".join([str(answer) for answer in normalized_answers])}')


if __name__ == "__main__":
    main()
