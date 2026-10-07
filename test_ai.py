from assessment.ai_generator import generate_questions


questions = generate_questions(
    subject="Python",
    topic="Functions",
    difficulty="Medium",
    number_of_questions=5
)


for index, question in enumerate(
    questions,
    start=1
):

    print()
    print("=" * 60)

    print(
        f"Question {index}:"
    )

    print(
        question.question
    )

    print(
        f"A. {question.option_a}"
    )

    print(
        f"B. {question.option_b}"
    )

    print(
        f"C. {question.option_c}"
    )

    print(
        f"D. {question.option_d}"
    )

    print(
        "Correct:",
        question.correct_answer
    )

    print(
        "Explanation:",
        question.explanation
    )